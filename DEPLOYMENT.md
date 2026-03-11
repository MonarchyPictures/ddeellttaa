# DELTA-9 DEPLOYMENT GUIDE

Complete deployment instructions for all environments.

---

## Quick Start Options

| Method | Best For | Time |
|--------|----------|------|
| [SQLite Quick](#sqlite-quick-start) | Immediate testing | 2 min |
| [Docker Compose](#docker-compose) | Local development | 5 min |
| [Railway](#railway-deployment) | Production hosting | 10 min |
| [Manual Setup](#manual-setup) | Advanced users | 20 min |

---

## SQLite Quick Start

**Best for**: Immediate testing without PostgreSQL/Redis

```bash
# Run the quick deployment script
python deploy-sqlite.py
```

This will:
1. Create a Python virtual environment
2. Install core dependencies
3. Initialize SQLite database
4. Start the server at http://localhost:8000

**Access URLs:**
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/guardian/health

**⚠️ Warning**: SQLite mode is for testing only. Use PostgreSQL for production.

---

## Docker Compose

**Best for**: Full local development with PostgreSQL + Redis

### Prerequisites
- Docker Desktop installed: https://www.docker.com/products/docker-desktop
- Docker Compose (included with Docker Desktop)

### Deploy

```bash
# Run the Docker deployment script
python deploy-docker.py
```

Or manually:

```bash
# Start all services
docker-compose -f docker-compose.local.yml up -d

# View logs
docker-compose -f docker-compose.local.yml logs -f

# Stop services
docker-compose -f docker-compose.local.yml down
```

**Access URLs:**
- API: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Docker Commands

```bash
# View all containers
docker-compose ps

# Restart backend
docker-compose restart backend

# Access database shell
docker-compose exec postgres psql -U delta9 -d delta9

# View backend logs
docker-compose logs -f backend

# Rebuild after code changes
docker-compose up -d --build
```

---

## Railway Deployment

**Best for**: Production cloud hosting

### 1. Install Railway CLI

```bash
npm install -g @railway/cli
```

### 2. Deploy

```bash
# Login to Railway
railway login

# Initialize project
railway init

# Deploy
railway up
```

### 3. Add Environment Variables

In Railway Dashboard, add these variables:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
APP_ENV=production
DEBUG=false
SECRET_KEY=your-secret-key-here
TELEGRAM_API_ID=your_id
TELEGRAM_API_HASH=your_hash
SERPAPI_KEY=your_key
```

### 4. Add PostgreSQL and Redis

```bash
# Add PostgreSQL
railway add --plugin postgresql

# Add Redis
railway add --plugin redis
```

### 5. Domain (Optional)

```bash
# Generate domain
railway domain
```

---

## Manual Setup

**Best for**: Advanced users who want full control

### 1. Install Prerequisites

**PostgreSQL:**
```bash
# Mac
brew install postgresql@15
brew services start postgresql@15

# Ubuntu
sudo apt-get install postgresql-15
sudo service postgresql start

# Create database
psql -U postgres
c CREATE DATABASE delta9;
c CREATE USER delta9 WITH PASSWORD 'delta9_secret';
c GRANT ALL PRIVILEGES ON DATABASE delta9 TO delta9;
c \\q
```

**Redis:**
```bash
# Mac
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo service redis-server start
```

**Python 3.11+:**
```bash
# Check version
python --version

# Install if needed (Mac)
brew install python@3.11

# Install if needed (Ubuntu)
sudo apt-get install python3.11 python3.11-venv python3.11-pip
```

### 2. Setup Application

```bash
# Create virtual environment
python -m venv .venv

# Activate
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env .env.local

# Edit .env.local with your settings
```

### 3. Initialize Database

```bash
# Run migrations (if using Alembic)
alembic upgrade head

# Or create tables automatically on first run
```

### 4. Start Services

```bash
# Terminal 1: Start backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend (optional)
cd frontend
npm install
npm run dev
```

---

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost/delta9` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `SECRET_KEY` | Application secret key | `change-me-in-production` |
| `APP_ENV` | Environment name | `development` or `production` |

### Optional

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `PORT` | API server port | `8000` |
| `TELEGRAM_API_ID` | Telegram API ID | - |
| `TELEGRAM_API_HASH` | Telegram API Hash | - |
| `SERPAPI_KEY` | SerpAPI key | - |
| `GUARDIAN_ENABLED` | Enable guardian | `true` |
| `GUARDIAN_INTERVAL` | Guardian check interval (seconds) | `60` |
| `SCRAPER_INTERVAL` | Scraper run interval (seconds) | `300` |
| `MAX_LEADS_PER_RUN` | Max leads per scraper run | `100` |

---

## Verification

### Check Installation

```bash
# Run verification script
python verify_installation.py
```

### Test API

```bash
# Health check
curl http://localhost:8000/api/guardian/health

# Pipeline stats
curl http://localhost:8000/api/guardian/pipeline/stats

# List scrapers
curl http://localhost:8000/api/guardian/scrapers
```

### Test Pipeline

```python
from app.pipeline.lead_pipeline import get_pipeline

pipeline = get_pipeline()

result = pipeline.process({
    'text': 'Looking for Toyota Vitz in Nairobi. Call 0712345678',
    'source_platform': 'telegram',
    'source_name': 'Kenya Cars',
    'source_url': 'https://t.me/kenya_cars/123',
    'timestamp': '2026-03-11T10:00:00',
    'location': 'Nairobi',
    'query': 'toyota vitz'
})

print(f"Success: {result.success}")
if result.lead:
    print(f"Lead: {result.lead.phone}")
else:
    print(f"Rejected: {result.rejection_reason}")
```

---

## Troubleshooting

### PostgreSQL Connection Failed

```bash
# Check if PostgreSQL is running
pg_isready -h localhost

# If not running:
brew services start postgresql@15  # Mac
sudo service postgresql start       # Linux

# Check database exists
psql -U postgres -l | grep delta9
```

### Redis Connection Failed

```bash
# Check if Redis is running
redis-cli ping

# If not running:
brew services start redis   # Mac
redis-server                # Manual
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
uvicorn app.main:app --port 8001
```

### Permission Denied

```bash
# Fix permissions
chmod +x deploy-sqlite.py
chmod +x deploy-docker.py
```

### Import Errors

```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## Production Checklist

Before deploying to production:

- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong SECRET_KEY
- [ ] Set APP_ENV=production
- [ ] Set DEBUG=false
- [ ] Configure API keys (Telegram, SerpAPI)
- [ ] Enable SSL/HTTPS
- [ ] Set up monitoring/alerting
- [ ] Configure log rotation
- [ ] Test backup/restore
- [ ] Review security settings

---

## Monitoring

### Logs

```bash
# View application logs
tail -f logs/delta9.log

# View error logs
tail -f logs/errors.log

# Docker logs
docker-compose logs -f backend
```

### Health Checks

```bash
# System health
curl http://localhost:8000/api/guardian/health

# Pipeline stats
curl http://localhost:8000/api/guardian/pipeline/stats

# Scraper status
curl http://localhost:8000/api/guardian/scrapers
```

### Metrics

```bash
# Pipeline statistics
curl http://localhost:8000/api/guardian/pipeline/stats

# Recent errors
curl http://localhost:8000/api/guardian/errors

# Search logs
curl "http://localhost:8000/api/guardian/logs/search?q=error"
```

---

## Support

- **Documentation**: ARCHITECTURE.md, IMPLEMENTATION_SUMMARY.md
- **Issues**: Check logs with `python verify_installation.py`
- **API Docs**: http://localhost:8000/docs (when running)

---

## Summary

| Method | Command | Best For |
|--------|---------|----------|
| SQLite | `python deploy-sqlite.py` | Quick testing |
| Docker | `python deploy-docker.py` | Full local dev |
| Railway | `railway up` | Production |
| Manual | See Manual Setup section | Advanced users |
