# Delta 9 - Railway Deployment
# Web process serves the API
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1

# Worker processes for distributed scraping
worker: celery -A app.core.celery_config.celery_app worker -Q default,scrapers,high_priority -n worker@%h --loglevel=info --concurrency=2

# Beat process for scheduled tasks
beat: celery -A app.core.celery_config.celery_app beat --loglevel=info
