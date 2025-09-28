# celery_worker.py
from os import name
from celery_app import celery_app

if name == 'main':
    celery_app.start()