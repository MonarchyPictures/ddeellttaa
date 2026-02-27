web: bash start.sh
worker: celery -A app.core.celery_worker.celery_app worker --loglevel=info --concurrency=2
beat: celery -A app.core.celery_worker.celery_app beat --loglevel=info
