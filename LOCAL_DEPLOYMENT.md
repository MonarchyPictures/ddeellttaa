# Delta 9 - Local Deployment Guide

## Quick Start

### Option 1: Python Script (Cross-Platform)
```bash
cd delta-9-main
python start_local.py
```

### Option 2: PowerShell (Windows)
```powershell
cd delta-9-main
.\start-local.ps1
```

### Option 3: Command Prompt (Windows)
```cmd
cd delta-9-main
start-local.bat
```

## Manual Setup

### 1. Create Virtual Environment
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt

# Optional: Install Playwright browsers (for heavy scrapers)
playwright install chromium
```

### 3. Configure Environment
```bash
# Copy local environment template
cp .env.local .env

# Or create minimal .env
echo "DATABASE_URL=sqlite:///./intent_radar_local.db" > .env
echo "PORT=8001" >> .env
```

### 4. Start Server
```bash
python main.py
```

## Access Points

| Endpoint | URL | Description |
|----------|-----|-------------|
| API | http://localhost:8001 | Main API server |
| Docs | http://localhost:8001/docs | Swagger/OpenAPI docs |
| Health | http://localhost:8001/health | Health check |
| API v1 | http://localhost:8001/api/v1 | API routes |

## Configuration

### Environment Variables

Edit `.env` file to customize:

```env
# Database (SQLite for local dev)
DATABASE_URL=sqlite:///./intent_radar_local.db

# Scraper Concurrency (reduce for local dev)
LIGHT_SCRAPER_CONCURRENCY=2
HEAVY_SCRAPER_CONCURRENCY=1
DOMAIN_COOLDOWN_SECONDS=5

# Kenya Scoring
KENYA_INTENT_THRESHOLD=0.18
SCORE_WEIGHT_INTENT=0.40
```

### Optional API Keys

For full functionality, add API keys to `.env`:

```env
# Search APIs
SERPAPI_KEY=your_key_here
GOOGLE_CSE_API_KEY=your_key_here
GOOGLE_CSE_ID=your_cse_id

# Telegram (optional)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token
```

## Testing the API

### Health Check
```bash
curl http://localhost:8001/health
```

### Test Scoring
```bash
curl -X POST "http://localhost:8001/api/v1/leads/score" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Natafuta pipes budget 50k Westlands urgently",
    "source": "telegram"
  }'
```

### Test Query Expansion
```bash
curl "http://localhost:8001/api/v1/search/expand?product=toyota%20axio&location=Nairobi"
```

## Frontend (Optional)

To build and serve the frontend:

```bash
cd frontend
npm install
npm run build
cd ..
python main.py
```

The frontend will be available at http://localhost:8001

## Troubleshooting

### Port Already in Use
```bash
# Find process using port 8001
# Windows
netstat -ano | findstr :8001

# Kill process or use different port
set PORT=8002
python main.py
```

### Database Issues
```bash
# Delete local database to start fresh
del intent_radar_local.db
# or
rm intent_radar_local.db
```

### Import Errors
```bash
# Ensure you're in the virtual environment
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Playwright Not Found
```bash
playwright install chromium
```

## Development Mode

### Enable Hot Reload
Already enabled in `main.py` via `reload=True`

### Debug Logging
Set in `.env`:
```env
DEBUG=true
LOG_LEVEL=debug
```

### Disable Scrapers (for API testing)
```env
WORKER_MODE=false
ENABLE_SCRAPERS=false
```

## Production Considerations

⚠️ **Local deployment is for development only.**

For production:
- Use PostgreSQL (not SQLite)
- Use Redis for caching
- Set strong secrets
- Enable HTTPS
- Use proper process manager (systemd, supervisor)
- See `RAILWAY_DEPLOYMENT.md` for production guide

## File Structure After Setup

```
delta-9-main/
├── .venv/                  # Virtual environment
├── .env                    # Local environment config
├── intent_radar_local.db   # SQLite database
├── app/
│   ├── main.py            # FastAPI app
│   ├── services/          # Business logic
│   │   ├── scoring/       # Kenya-optimized scoring
│   │   └── pipeline/      # Lead pipeline
│   └── ...
├── frontend/dist/         # Built frontend (optional)
└── start_local.py         # Startup script
```

## Next Steps

1. ✅ API is running at http://localhost:8001
2. 📖 View API docs at http://localhost:8001/docs
3. 🔍 Test search endpoints
4. 📊 Build frontend (optional)
5. 🚀 Deploy to production (see RAILWAY_DEPLOYMENT.md)
