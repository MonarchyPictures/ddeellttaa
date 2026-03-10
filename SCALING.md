# Delta-9 Scaling Architecture

## Overview

As Delta-9 grows from hundreds to millions of signals per day, the architecture evolves from simple to enterprise-scale.

## Architecture Evolution

### Phase 1: MVP (Current)
```
Scrapers → Redis → Processors → PostgreSQL
```
**Good for**: < 10k signals/day

### Phase 2: Distributed (Implemented)
```
Scrapers → Redis + Celery Workers → PostgreSQL
```
**Good for**: 10k - 100k signals/day

### Phase 3: Kafka Scale (Next)
```
Scrapers → Kafka → AI Filters → PostgreSQL + ClickHouse
```
**Good for**: 100k+ signals/day (ZoomInfo scale)

---

## Why Kafka?

### Problems with Redis at Scale:
- ❌ Single-threaded processing
- ❌ Limited message retention
- ❌ No replay capability
- ❌ Memory constraints

### Kafka Advantages:
- ✅ Horizontally scalable (add brokers)
- ✅ Persistent storage (replay any time)
- ✅ High throughput (millions/sec)
- ✅ Consumer groups (parallel processing)
- ✅ Exactly-once semantics

---

## Kafka Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        PRODUCERS                            │
│  Reddit Scraper │ Twitter Scraper │ Forum Scraper │ etc.   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                     KAFKA CLUSTER                           │
│  ┌────────────────┬────────────────┬────────────────┐      │
│  │  signals.raw   │ signals.verified│ signals.high_  │      │
│  │   (12 parts)   │   (6 parts)    │  intent (3)    │      │
│  └────────────────┴────────────────┴────────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Verification │  │   Intent     │  │    Lead      │
│   Workers    │  │   Workers    │  │   Workers    │
│  (Group A)   │  │  (Group B)   │  │  (Group C)   │
└──────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              ┌─────────────────────┐
              │    PostgreSQL       │
              │   (Transactional)   │
              └─────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │    ClickHouse       │
              │    (Analytics)      │
              └─────────────────────┘
```

---

## Kafka Topics

| Topic | Partitions | Retention | Purpose |
|-------|-----------|-----------|---------|
| `signals.raw` | 12 | 24h | All scraped signals |
| `signals.verified` | 6 | 24h | After spam/bot filter |
| `signals.high_intent` | 3 | 7d | Buyer intent detected |
| `leads.created` | 3 | 30d | Final leads |
| `analytics.events` | 6 | 30d | Metrics & tracking |

---

## Consumer Groups

Each AI filter runs as a consumer group with multiple instances:

```
Consumer Group: verification-workers
├─ Instance 1 (processes partitions 0-3)
├─ Instance 2 (processes partitions 4-7)
└─ Instance 3 (processes partitions 8-11)

Consumer Group: intent-workers
├─ Instance 1 (processes partitions 0-2)
└─ Instance 2 (processes partitions 3-5)
```

**Scale by adding more instances to the group.**

---

## Message Flow

### 1. Signal Created
```json
{
  "event_type": "signal_created",
  "timestamp": "2026-03-10T14:30:00Z",
  "payload": {
    "id": "reddit_t3_abc123",
    "text": "Looking for plumber in Nairobi",
    "platform": "reddit",
    "author": "homeowner_ke",
    ...
  },
  "metadata": {
    "source": "reddit",
    "version": "2.0"
  }
}
```

### 2. After Verification
```json
{
  "event_type": "signal_verified",
  "verification": {
    "score": 0.92,
    "status": "verified",
    "checks": ["spam_check", "bot_check"]
  }
}
```

### 3. After Intent Detection
```json
{
  "event_type": "high_intent_detected",
  "intent": {
    "score": 0.85,
    "category": "buying",
    "urgency": "immediate"
  }
}
```

### 4. Lead Created
```json
{
  "event_type": "lead_created",
  "payload": {
    "id": 12345,
    "username": "homeowner_ke",
    "intent_score": 0.85,
    ...
  }
}
```

---

## Local Development with Kafka

### Start Kafka Stack
```bash
# Start all services
docker-compose -f docker-compose.kafka.yml up -d

# View Kafka UI (topics, consumers, messages)
open http://localhost:8080
```

### Run Consumers
```bash
# Start verification workers
python -m app.workers.kafka_consumer verification

# Start intent detection workers
python -m app.workers.kafka_consumer intent

# Start lead creation workers
python -m app.workers.kafka_consumer lead

# Start all (for development)
python -m app.workers.kafka_consumer all
```

### Scale Consumers
```bash
# Run multiple instances (terminal 1)
python -m app.workers.kafka_consumer verification --group-id v1

# Run multiple instances (terminal 2)
python -m app.workers.kafka_consumer verification --group-id v2

# With Docker Compose
docker-compose -f docker-compose.kafka.yml up --scale verification-worker-1=5 -d
```

---

## Production Deployment

### Managed Kafka Options

| Provider | Service | Best For |
|----------|---------|----------|
| **Confluent** | Confluent Cloud | Enterprise, fully managed |
| **AWS** | MSK | AWS-native workloads |
| **Google** | Pub/Sub | GCP-native workloads |
| **Azure** | Event Hubs | Azure-native workloads |
| **Upstash** | Serverless Kafka | Startups, low volume |

### Environment Variables
```bash
# Required
KAFKA_BOOTSTRAP_SERVERS=pkc-xxx.us-east-1.aws.confluent.cloud:9092
KAFKA_USERNAME=YOUR_API_KEY
KAFKA_PASSWORD=YOUR_API_SECRET

# Optional
KAFKA_SECURITY_PROTOCOL=SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: verification-workers
spec:
  replicas: 10  # Scale as needed
  selector:
    matchLabels:
      app: verification-worker
  template:
    spec:
      containers:
      - name: worker
        image: delta9:latest
        command: ["python", "-m", "app.workers.kafka_consumer", "verification"]
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka:9092"
```

---

## Scaling Guide

### When to Add Kafka?

| Metric | Use Redis | Use Kafka |
|--------|-----------|-----------|
| Signals/day | < 100k | > 100k |
| Concurrent scrapers | < 10 | > 10 |
| Message retention | Hours | Days/Weeks |
| Replay needed | No | Yes |
| Team size | 1-2 devs | 3+ devs |

### Scaling Steps

1. **Monitor current load**
   ```bash
   # Check Redis queue depth
   redis-cli LLEN celery
   
   # Check processing lag
   # If growing → time to scale
   ```

2. **Deploy Kafka**
   ```bash
   # Update docker-compose
   docker-compose -f docker-compose.kafka.yml up -d
   ```

3. **Switch producers**
   ```python
   # In scrapers, change from:
   redis_producer.send_signal(...)
   
   # To:
   kafka_producer.send_signal(...)
   ```

4. **Deploy consumers**
   ```bash
   # Start with 2 instances per filter
   docker-compose -f docker-compose.kafka.yml up -d verification-worker-1
   docker-compose -f docker-compose.kafka.yml up -d intent-worker-1
   ```

5. **Monitor and scale**
   ```bash
   # View consumer lag in Kafka UI
   # If lag grows → add more consumers
   ```

---

## Performance Benchmarks

### Single Kafka Broker
- **Throughput**: 100k+ messages/second
- **Latency**: < 10ms (p99)
- **Storage**: TBs per broker

### Delta-9 at Scale
- **100k signals/day**: 1 Kafka broker, 3 consumer instances
- **1M signals/day**: 3 Kafka brokers, 10 consumer instances
- **10M signals/day**: 9 Kafka brokers, 50+ consumer instances

---

## Monitoring

### Key Metrics

| Metric | Alert If | Check With |
|--------|----------|------------|
| Consumer Lag | > 1000 | Kafka UI, Burrow |
| Broker Disk | > 80% | Prometheus |
| Message Rate | Drop > 50% | Grafana |
| Error Rate | > 1% | Sentry |

### Tools
- **Kafka UI**: Visual topic/consumer management
- **Prometheus + Grafana**: Metrics and dashboards
- **Burrow**: Consumer lag monitoring
- **Sentry**: Error tracking

---

## Migration Path

### From Redis to Kafka

1. **Dual-write phase** (1 week)
   ```python
   # Write to both
   redis_producer.send_signal(data)
   kafka_producer.send_signal(data)
   ```

2. **Shadow traffic** (1 week)
   ```python
   # Read from Redis, also read from Kafka (don't process)
   ```

3. **Cutover** (1 day)
   ```python
   # Stop Redis consumers, start Kafka consumers
   ```

4. **Cleanup** (1 week later)
   ```python
   # Remove Redis code
   ```

---

## Cost Comparison

| Scale | Redis | Kafka | Difference |
|-------|-------|-------|------------|
| 10k/day | $50/mo | $200/mo | 4x |
| 100k/day | $100/mo | $200/mo | 2x |
| 1M/day | $500/mo | $400/mo | 0.8x |
| 10M/day | $2000/mo | $1000/mo | 0.5x |

**Kafka becomes cost-effective at 100k+ signals/day.**

---

## Summary

Start with Redis. Migrate to Kafka when:
- You're processing > 100k signals/day
- You need message replay
- You have a team to manage it
- Cost at scale matters

This is exactly how ZoomInfo, Apollo, and Clay scale their data pipelines.
