from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Load Redis broker URL from environment variables
REDIS_BROKER = os.getenv("REDIS_BROKER") or os.getenv("REDIS_URL")

if not REDIS_BROKER:
    raise ValueError("Neither REDIS_BROKER nor REDIS_URL is set!")

celery_app = Celery(
    "socialsuit",
    broker=REDIS_BROKER,
    backend=REDIS_BROKER,
    include=[
        "services.scheduler.tasks"
    ]
)

# Celery configuration with SSL for Upstash Redis
celery_app.conf.update(
    broker_use_ssl={
        "ssl_cert_reqs": 0  # 0 = CERT_NONE (no certificate verification)
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": 0
    },
    task_track_started=True,
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='UTC',
    enable_utc=True,
    beat_schedule={
        "refresh-tokens-every-2-hours": {
            "task": "services.scheduler.tasks.auto_refresh_tokens",
            "schedule": 7200,
        },
        "dispatch-scheduled-posts-every-1-minute": {
            "task": "services.scheduler.tasks.scheduled_post_dispatcher",
            "schedule": 60,
        },
    }
)