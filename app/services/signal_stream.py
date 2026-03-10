"""
Signal Stream Service
Real-time signal pipeline using Redis Pub/Sub

Architecture:
    Scrapers ──► Signal Stream (Redis) ──► Processors ──► Leads
                    │
                    ▼
              WebSocket Clients
"""
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
import redis.asyncio as aioredis
import redis

from app.core.celery_config import get_redis_url


@dataclass
class Signal:
    """Raw signal from any source"""
    id: str
    text: str
    platform: str
    url: str
    author: str
    timestamp: str
    query: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Signal':
        return cls(**data)


class SignalStream:
    """
    Signal Stream using Redis Pub/Sub
    
    Channels:
    - signals:raw - All raw signals from scrapers
    - signals:high_intent - Signals with intent_score > 0.5
    - signals:processed - Signals after processing
    - signals:leads - Converted leads
    """
    
    CHANNELS = {
        'raw': 'signals:raw',
        'high_intent': 'signals:high_intent',
        'processed': 'signals:processed',
        'leads': 'signals:leads',
    }
    
    def __init__(self):
        self.redis_url = get_redis_url()
        self._sync_redis = None
        self._async_redis = None
        self._subscribers: List[Callable] = []
    
    def _get_sync_redis(self) -> redis.Redis:
        """Get synchronous Redis connection"""
        if self._sync_redis is None:
            self._sync_redis = redis.from_url(self.redis_url)
        return self._sync_redis
    
    async def _get_async_redis(self) -> aioredis.Redis:
        """Get asynchronous Redis connection"""
        if self._async_redis is None:
            self._async_redis = aioredis.from_url(self.redis_url)
        return self._async_redis
    
    def publish_signal(self, signal: Signal, channel: str = 'raw') -> bool:
        """
        Publish a signal to the stream (synchronous)
        
        Args:
            signal: The signal to publish
            channel: Channel to publish to (raw, high_intent, processed, leads)
            
        Returns:
            bool: True if published successfully
        """
        try:
            r = self._get_sync_redis()
            channel_name = self.CHANNELS.get(channel, self.CHANNELS['raw'])
            
            # Add to stream with timestamp
            signal_data = signal.to_dict()
            signal_data['streamed_at'] = datetime.utcnow().isoformat()
            
            # Publish to Pub/Sub
            r.publish(channel_name, json.dumps(signal_data))
            
            # Also add to stream for persistence (keep last 10000 signals)
            r.xadd(
                f"stream:{channel_name}",
                signal_data,
                maxlen=10000,
                approximate=True
            )
            
            return True
            
        except Exception as e:
            print(f"[SignalStream] Publish error: {e}")
            return False
    
    async def publish_signal_async(self, signal: Signal, channel: str = 'raw') -> bool:
        """Publish a signal asynchronously"""
        try:
            r = await self._get_async_redis()
            channel_name = self.CHANNELS.get(channel, self.CHANNELS['raw'])
            
            signal_data = signal.to_dict()
            signal_data['streamed_at'] = datetime.utcnow().isoformat()
            
            await r.publish(channel_name, json.dumps(signal_data))
            await r.xadd(
                f"stream:{channel_name}",
                signal_data,
                maxlen=10000,
                approximate=True
            )
            
            return True
            
        except Exception as e:
            print(f"[SignalStream] Async publish error: {e}")
            return False
    
    def get_recent_signals(self, channel: str = 'raw', count: int = 50) -> List[Dict]:
        """Get recent signals from stream (for replay)"""
        try:
            r = self._get_sync_redis()
            channel_name = self.CHANNELS.get(channel, self.CHANNELS['raw'])
            stream_key = f"stream:{channel_name}"
            
            # Read last N signals
            messages = r.xrevrange(stream_key, count=count)
            
            signals = []
            for msg_id, data in messages:
                # Convert bytes to strings
                decoded = {k.decode() if isinstance(k, bytes) else k: 
                          v.decode() if isinstance(v, bytes) else v 
                          for k, v in data.items()}
                decoded['stream_id'] = msg_id.decode() if isinstance(msg_id, bytes) else msg_id
                signals.append(decoded)
            
            return signals
            
        except Exception as e:
            print(f"[SignalStream] Get recent error: {e}")
            return []
    
    def get_signal_stats(self) -> Dict:
        """Get signal stream statistics"""
        try:
            r = self._get_sync_redis()
            
            stats = {}
            for name, channel in self.CHANNELS.items():
                stream_key = f"stream:{channel}"
                length = r.xlen(stream_key)
                stats[name] = length
            
            return {
                'channels': stats,
                'total': sum(stats.values()),
                'timestamp': datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            print(f"[SignalStream] Stats error: {e}")
            return {'error': str(e)}
    
    async def subscribe(self, channel: str = 'raw'):
        """
        Subscribe to signal stream (async generator)
        
        Usage:
            async for signal in stream.subscribe('raw'):
                process(signal)
        """
        r = await self._get_async_redis()
        channel_name = self.CHANNELS.get(channel, self.CHANNELS['raw'])
        
        pubsub = r.pubsub()
        await pubsub.subscribe(channel_name)
        
        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    yield data
        finally:
            await pubsub.unsubscribe(channel_name)
    
    def clear_stream(self, channel: str = None) -> bool:
        """Clear signal stream (use with caution)"""
        try:
            r = self._get_sync_redis()
            
            if channel:
                channel_name = self.CHANNELS.get(channel, channel)
                r.delete(f"stream:{channel_name}")
            else:
                # Clear all
                for name, channel in self.CHANNELS.items():
                    r.delete(f"stream:{channel}")
            
            return True
            
        except Exception as e:
            print(f"[SignalStream] Clear error: {e}")
            return False


class SignalProducer:
    """
    Producer class for scrapers to publish signals
    
    Usage:
        producer = SignalProducer()
        producer.send_signal(text="...", platform="reddit", ...)
    """
    
    def __init__(self):
        self.stream = SignalStream()
        self._signal_count = 0
    
    def send_signal(
        self,
        text: str,
        platform: str,
        url: str,
        author: str,
        query: str,
        metadata: Dict = None,
        signal_id: str = None,
    ) -> bool:
        """
        Send a signal to the stream
        
        Args:
            text: Signal content/text
            platform: Source platform (reddit, twitter, forum)
            url: Source URL
            author: Author username
            query: The search query that found this
            metadata: Additional metadata
            signal_id: Optional ID (auto-generated if not provided)
            
        Returns:
            bool: Success status
        """
        self._signal_count += 1
        
        signal = Signal(
            id=signal_id or f"{platform}_{self._signal_count}_{int(datetime.utcnow().timestamp())}",
            text=text,
            platform=platform,
            url=url,
            author=author,
            timestamp=datetime.utcnow().isoformat(),
            query=query,
            metadata=metadata or {},
        )
        
        return self.stream.publish_signal(signal, channel='raw')
    
    def get_count(self) -> int:
        """Get number of signals sent"""
        return self._signal_count


class SignalConsumer:
    """
    Consumer class for processing signals from the stream
    
    Usage:
        consumer = SignalConsumer()
        consumer.start_processing(process_function)
    """
    
    def __init__(self, channel: str = 'raw'):
        self.stream = SignalStream()
        self.channel = channel
        self._running = False
        self._processor: Optional[Callable] = None
    
    def register_processor(self, processor: Callable[[Signal], None]):
        """Register a function to process signals"""
        self._processor = processor
    
    async def start(self):
        """Start consuming signals"""
        if not self._processor:
            raise ValueError("No processor registered. Call register_processor first.")
        
        self._running = True
        print(f"[SignalConsumer] Started consuming from '{self.channel}'")
        
        try:
            async for signal_data in self.stream.subscribe(self.channel):
                if not self._running:
                    break
                
                try:
                    signal = Signal.from_dict(signal_data)
                    self._processor(signal)
                except Exception as e:
                    print(f"[SignalConsumer] Processing error: {e}")
                    
        except Exception as e:
            print(f"[SignalConsumer] Consumer error: {e}")
    
    def stop(self):
        """Stop consuming"""
        self._running = False
        print("[SignalConsumer] Stopped")


# Singleton instances
_signal_stream = None
_signal_producer = None


def get_signal_stream() -> SignalStream:
    """Get or create SignalStream singleton"""
    global _signal_stream
    if _signal_stream is None:
        _signal_stream = SignalStream()
    return _signal_stream


def get_signal_producer() -> SignalProducer:
    """Get or create SignalProducer singleton"""
    global _signal_producer
    if _signal_producer is None:
        _signal_producer = SignalProducer()
    return _signal_producer
