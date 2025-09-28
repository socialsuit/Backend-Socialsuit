web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
worker: celery -A services.scheduler.tasks worker --loglevel=info
beat: celery -A services.scheduler.tasks beat --loglevel=info