"""
Kafka Consumers for AI Filter Pipeline

Consumers process messages from Kafka topics:
    signals.raw → Verification Layer → signals.verified
    signals.verified → Intent Detection → signals.high_intent
    signals.high_intent → Lead Creation → leads.created

Run multiple consumer instances for horizontal scaling.
"""
import json
import signal
import sys
from typing import Callable, Dict, Any
from datetime import datetime

from app.core.kafka_config import get_kafka_client, KAFKA_TOPICS
from app.services.lead_verification import get_verification_service
from app.services.intent_detection import get_intent_service
from app.tasks.lead_tasks import create_lead_from_signals
from app.models.lead import SessionLocal, Lead, Signal


class KafkaConsumerManager:
    """
    Manages Kafka consumers for the AI filter pipeline
    
    Each consumer group can have multiple instances for load balancing.
    """
    
    def __init__(self):
        self.client = get_kafka_client()
        self.consumers = []
        self._running = False
    
    def start_verification_consumer(self, group_id: str = "verification-workers"):
        """
        Consumer for signals.raw → signals.verified
        
        Runs the Lead Verification Layer on each signal.
        """
        print(f"🚀 Starting Verification Consumer (group: {group_id})")
        
        consumer = self.client.create_consumer("signals.raw", group_id)
        if not consumer:
            print("❌ Failed to create verification consumer")
            return
        
        verification_service = get_verification_service()
        
        try:
            for message in consumer:
                if not self._running:
                    break
                
                try:
                    data = message.value
                    signal_data = data.get('payload', {})
                    
                    print(f"[Verification] Processing signal: {signal_data.get('id')}")
                    
                    # Run verification layer
                    verification = verification_service.verify(signal_data)
                    
                    if verification.is_verified:
                        # Send to verified topic
                        self.client.send("signals.verified", {
                            "event_type": "signal_verified",
                            "timestamp": datetime.utcnow().isoformat(),
                            "payload": signal_data,
                            "verification": {
                                "score": verification.verification_score,
                                "status": verification.status.value,
                                "checks": verification.checks_passed,
                            }
                        })
                        print(f"  ✅ Verified (score: {verification.verification_score})")
                    else:
                        print(f"  ❌ Rejected: {[r.value for r in verification.rejection_reasons]}")
                    
                    # Commit offset
                    consumer.commit_async()
                    
                except Exception as e:
                    print(f"  ❌ Error processing message: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Verification consumer stopped")
        finally:
            consumer.close()
    
    def start_intent_consumer(self, group_id: str = "intent-workers"):
        """
        Consumer for signals.verified → signals.high_intent
        
        Runs Intent Detection AI on verified signals.
        """
        print(f"🚀 Starting Intent Consumer (group: {group_id})")
        
        consumer = self.client.create_consumer("signals.verified", group_id)
        if not consumer:
            print("❌ Failed to create intent consumer")
            return
        
        intent_service = get_intent_service()
        
        try:
            for message in consumer:
                if not self._running:
                    break
                
                try:
                    data = message.value
                    signal_data = data.get('payload', {})
                    
                    print(f"[Intent] Processing signal: {signal_data.get('id')}")
                    
                    # Run intent detection
                    text = signal_data.get('text', '')
                    query = signal_data.get('query', '')
                    intent = intent_service.analyze(text, query)
                    
                    # Always send to processed topic with intent data
                    self.client.send("signals.processed", {
                        "event_type": "signal_processed",
                        "timestamp": datetime.utcnow().isoformat(),
                        "payload": signal_data,
                        "intent": {
                            "score": intent.intent_score,
                            "category": intent.intent_category,
                            "urgency": intent.buying_urgency,
                            "is_buyer": intent.is_buyer,
                        }
                    })
                    
                    # If high intent, send to high_intent topic
                    if intent.is_buyer and intent.intent_score >= 0.5:
                        self.client.send("signals.high_intent", {
                            "event_type": "high_intent_detected",
                            "timestamp": datetime.utcnow().isoformat(),
                            "payload": signal_data,
                            "intent": {
                                "score": intent.intent_score,
                                "category": intent.intent_category,
                                "urgency": intent.buying_urgency,
                                "keywords": intent.keywords_matched,
                            }
                        })
                        print(f"  🎯 High intent detected: {intent.intent_score}")
                    else:
                        print(f"  ℹ️  Low intent: {intent.intent_score}")
                    
                    consumer.commit_async()
                    
                except Exception as e:
                    print(f"  ❌ Error processing message: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Intent consumer stopped")
        finally:
            consumer.close()
    
    def start_lead_creation_consumer(self, group_id: str = "lead-workers"):
        """
        Consumer for signals.high_intent → leads.created
        
        Creates leads from high-intent signals.
        """
        print(f"🚀 Starting Lead Creation Consumer (group: {group_id})")
        
        consumer = self.client.create_consumer("signals.high_intent", group_id)
        if not consumer:
            print("❌ Failed to create lead consumer")
            return
        
        try:
            for message in consumer:
                if not self._running:
                    break
                
                try:
                    data = message.value
                    signal_data = data.get('payload', {})
                    intent_data = data.get('intent', {})
                    
                    print(f"[Lead Creation] Creating lead from signal: {signal_data.get('id')}")
                    
                    # Create lead in database
                    db = SessionLocal()
                    try:
                        lead = Lead(
                            username=signal_data.get('author'),
                            sources=[signal_data.get('platform')],
                            intent_score=intent_data.get('score', 0),
                            intent_category=intent_data.get('category'),
                            buying_urgency=intent_data.get('urgency'),
                            profile_urls={signal_data.get('platform'): signal_data.get('url')},
                            intent_signals=[signal_data.get('text', '')[:300]],
                            status="new",
                            first_seen=datetime.utcnow(),
                            last_active=datetime.utcnow(),
                        )
                        
                        db.add(lead)
                        db.commit()
                        
                        # Send to leads topic
                        self.client.send("leads.created", {
                            "event_type": "lead_created",
                            "timestamp": datetime.utcnow().isoformat(),
                            "payload": {
                                "id": lead.id,
                                "username": lead.username,
                                "intent_score": lead.intent_score,
                                "sources": lead.sources,
                            }
                        })
                        
                        print(f"  ✅ Lead created: ID {lead.id}")
                        
                    finally:
                        db.close()
                    
                    consumer.commit_async()
                    
                except Exception as e:
                    print(f"  ❌ Error creating lead: {e}")
                    
        except KeyboardInterrupt:
            print("\n🛑 Lead creation consumer stopped")
        finally:
            consumer.close()
    
    def start_analytics_consumer(self, group_id: str = "analytics-workers"):
        """
        Consumer for analytics events
        
        Processes analytics data for reporting.
        """
        print(f"🚀 Starting Analytics Consumer (group: {group_id})")
        
        consumer = self.client.create_consumer("analytics.events", group_id)
        if not consumer:
            print("❌ Failed to create analytics consumer")
            return
        
        try:
            for message in consumer:
                if not self._running:
                    break
                
                data = message.value
                event_type = data.get('event_type')
                
                # Process analytics event
                print(f"[Analytics] {event_type}")
                
                # TODO: Send to ClickHouse or analytics DB
                
                consumer.commit_async()
                
        except KeyboardInterrupt:
            print("\n🛑 Analytics consumer stopped")
        finally:
            consumer.close()
    
    def stop_all(self):
        """Stop all consumers"""
        print("\n🛑 Stopping all consumers...")
        self._running = False


# CLI for running consumers
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Delta-9 Kafka Consumers")
    parser.add_argument(
        "consumer",
        choices=["verification", "intent", "lead", "analytics", "all"],
        help="Which consumer to start"
    )
    parser.add_argument(
        "--instances", 
        type=int, 
        default=1,
        help="Number of consumer instances (for scaling)"
    )
    parser.add_argument(
        "--group-id",
        help="Consumer group ID (auto-generated if not provided)"
    )
    
    args = parser.parse_args()
    
    manager = KafkaConsumerManager()
    manager._running = True
    
    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        manager.stop_all()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Generate group ID if not provided
    group_id = args.group_id or f"{args.consumer}-workers"
    
    # Start requested consumer
    if args.consumer == "verification":
        manager.start_verification_consumer(group_id)
    elif args.consumer == "intent":
        manager.start_intent_consumer(group_id)
    elif args.consumer == "lead":
        manager.start_lead_creation_consumer(group_id)
    elif args.consumer == "analytics":
        manager.start_analytics_consumer(group_id)
    elif args.consumer == "all":
        # Start all consumers (for local development)
        import threading
        
        threads = [
            threading.Thread(target=manager.start_verification_consumer, args=(f"{group_id}-v",)),
            threading.Thread(target=manager.start_intent_consumer, args=(f"{group_id}-i",)),
            threading.Thread(target=manager.start_lead_creation_consumer, args=(f"{group_id}-l",)),
        ]
        
        for t in threads:
            t.daemon = True
            t.start()
        
        # Keep main thread alive
        try:
            while True:
                signal.pause()
        except KeyboardInterrupt:
            manager.stop_all()
