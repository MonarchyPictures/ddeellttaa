# Railway Multi-Service Procfile
# Each service runs as a separate Railway process

# Service 1: FastAPI (Public API only - no scraping)
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT

# Service 2: Celery Worker (Heavy scraping + Playwright)
worker: celery -A app.core.celery_app worker --loglevel=info --concurrency=2 --pool=prefork

# Service 3: Celery Beat (Scheduler - triggers agents)
scheduler: celery -A app.core.celery_app beat --loglevel=info

# Service 4: Flower (Optional - Celery monitoring)
flower: celery -A app.core.celery_app flower --port=$PORT
