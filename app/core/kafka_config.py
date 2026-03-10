"""
Kafka Configuration for Delta-9 Scaling Layer

Architecture at Scale:
    Scrapers → Kafka → AI Filters → Database
    
This is how ZoomInfo, Apollo, and other large-scale lead gen platforms work.
"""
import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Kafka client
try:
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
    from kafka.admin import NewTopic
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("⚠️  Kafka not installed. Run: pip install kafka-python")


# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS", 
    "localhost:9092"
).split(",")

KAFKA_TOPICS = {
    # Raw signals from scrapers (high volume)
    "signals.raw": {
        "partitions": 12,  # High parallelism for scraping
        "replication": 2,
        "retention_ms": 86400000,  # 24 hours
    },
    
    # After verification layer (filtered)
    "signals.verified": {
        "partitions": 6,
        "replication": 2,
        "retention_ms": 86400000,
    },
    
    # After intent detection (high intent only)
    "signals.high_intent": {
        "partitions": 3,
        "replication": 2,
        "retention_ms": 604800000,  # 7 days
    },
    
    # Final leads to database
    "leads.created": {
        "partitions": 3,
        "replication": 2,
        "retention_ms": 2592000000,  # 30 days
    },
    
    # Analytics events
    "analytics.events": {
        "partitions": 6,
        "replication": 2,
        "retention_ms": 2592000000,  # 30 days
    },
}


@dataclass
class KafkaMessage:
    """Standardized Kafka message format"""
    event_type: str  # signal_created, lead_verified, etc.
    timestamp: str   # ISO format
    payload: Dict[str, Any]  # Event data
    metadata: Optional[Dict[str, Any]] = None  # Trace info, source, etc.
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> 'KafkaMessage':
        return cls(**json.loads(data))


class KafkaClient:
    """
    Kafka Client for Delta-9
    
    Handles producer/consumer setup and topic management
    """
    
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.consumer: Optional[KafkaConsumer] = None
        self.admin: Optional[KafkaAdminClient] = None
        self._connected = False
    
    def connect(self) -> bool:
        """Initialize Kafka connections"""
        if not KAFKA_AVAILABLE:
            print("❌ Kafka not available")
            return False
        
        try:
            # Create producer
            self.producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                retry_backoff_ms=1000,
                compression_type='gzip',  # Compress messages
                batch_size=16384,  # Batch messages
                linger_ms=100,  # Wait up to 100ms to batch
            )
            
            # Create admin client
            self.admin = KafkaAdminClient(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                client_id='delta9-admin'
            )
            
            self._connected = True
            print(f"✅ Kafka connected: {KAFKA_BOOTSTRAP_SERVERS}")
            return True
            
        except Exception as e:
            print(f"❌ Kafka connection failed: {e}")
            return False
    
    def create_topics(self) -> bool:
        """Create Kafka topics if they don't exist"""
        if not self.admin:
            print("❌ Kafka admin not connected")
            return False
        
        try:
            existing_topics = self.admin.list_topics()
            
            new_topics = []
            for topic_name, config in KAFKA_TOPICS.items():
                if topic_name not in existing_topics:
                    new_topics.append(NewTopic(
                        name=topic_name,
                        num_partitions=config["partitions"],
                        replication_factor=config["replication"],
                        topic_configs={
                            "retention.ms": str(config["retention_ms"]),
                            "cleanup.policy": "delete",
                        }
                    ))
            
            if new_topics:
                self.admin.create_topics(new_topics)
                print(f"✅ Created {len(new_topics)} Kafka topics")
            else:
                print("✅ All Kafka topics exist")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Topic creation error: {e}")
            return False
    
    def send(self, topic: str, message: Dict, key: Optional[str] = None) -> bool:
        """
        Send message to Kafka topic
        
        Args:
            topic: Target topic
            message: Message payload (dict)
            key: Optional partition key (e.g., user_id for ordering)
        """
        if not self.producer:
            print("❌ Kafka producer not connected")
            return False
        
        try:
            future = self.producer.send(topic, key=key, value=message)
            # Don't wait for confirmation (async)
            return True
        except Exception as e:
            print(f"❌ Failed to send to {topic}: {e}")
            return False
    
    def create_consumer(self, topic: str, group_id: str) -> Optional[KafkaConsumer]:
        """
        Create a Kafka consumer
        
        Args:
            topic: Topic to consume
            group_id: Consumer group for load balancing
        """
        if not KAFKA_AVAILABLE:
            return None
        
        try:
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                auto_offset_reset='latest',  # Start from latest
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                max_poll_records=100,  # Batch size
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
            )
            return consumer
        except Exception as e:
            print(f"❌ Failed to create consumer: {e}")
            return None
    
    def close(self):
        """Close all connections"""
        if self.producer:
            self.producer.close()
        if self.admin:
            self.admin.close()
        self._connected = False
        print("👋 Kafka connections closed")


class KafkaSignalProducer:
    """
    Producer for sending signals to Kafka
    
    Replaces Redis Signal Stream at scale
    """
    
    def __init__(self):
        self.client = KafkaClient()
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize Kafka connection and topics"""
        if self._initialized:
            return True
        
        if self.client.connect():
            self.client.create_topics()
            self._initialized = True
            return True
        return False
    
    def send_signal(self, signal_data: Dict, topic: str = "signals.raw") -> bool:
        """
        Send a signal to Kafka
        
        Args:
            signal_data: Signal dictionary
            topic: Target topic (signals.raw, signals.verified, etc.)
        """
        if not self._initialized:
            # Fallback to Redis if Kafka not available
            from app.services.signal_stream import get_signal_producer
            redis_producer = get_signal_producer()
            return redis_producer.send_signal(
                text=signal_data.get('text', ''),
                platform=signal_data.get('platform', ''),
                url=signal_data.get('url', ''),
                author=signal_data.get('author', ''),
                query=signal_data.get('query', ''),
                metadata=signal_data.get('metadata', {}),
                signal_id=signal_data.get('id')
            )
        
        # Add metadata
        from datetime import datetime
        message = {
            "event_type": "signal_created",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": signal_data,
            "metadata": {
                "source": signal_data.get('platform'),
                "version": "2.0",
            }
        }
        
        # Use author as key for partition ordering
        key = signal_data.get('author')
        
        return self.client.send(topic, message, key)
    
    def send_verified_signal(self, signal_data: Dict, verification_result: Dict) -> bool:
        """Send signal after verification layer"""
        signal_data['verification'] = verification_result
        return self.send_signal(signal_data, topic="signals.verified")
    
    def send_high_intent_signal(self, signal_data: Dict, intent_result: Dict) -> bool:
        """Send high-intent signal"""
        signal_data['intent'] = intent_result
        return self.send_signal(signal_data, topic="signals.high_intent")
    
    def send_lead(self, lead_data: Dict) -> bool:
        """Send final lead to database consumers"""
        from datetime import datetime
        message = {
            "event_type": "lead_created",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": lead_data,
            "metadata": {
                "version": "2.0",
            }
        }
        return self.client.send("leads.created", message, key=str(lead_data.get('id')))


# Singleton
_kafka_client = None
_kafka_producer = None


def get_kafka_client() -> KafkaClient:
    """Get or create Kafka client"""
    global _kafka_client
    if _kafka_client is None:
        _kafka_client = KafkaClient()
    return _kafka_client


def get_kafka_producer() -> KafkaSignalProducer:
    """Get or create Kafka producer"""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaSignalProducer()
    return _kafka_producer


def check_kafka_health() -> Dict:
    """Check Kafka connection health"""
    if not KAFKA_AVAILABLE:
        return {"status": "unavailable", "message": "kafka-python not installed"}
    
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            client_id='health-check'
        )
        topics = admin.list_topics()
        admin.close()
        
        return {
            "status": "connected",
            "bootstrap_servers": KAFKA_BOOTSTRAP_SERVERS,
            "topics": len(topics),
            "configured_topics": list(KAFKA_TOPICS.keys()),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
