import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest, CONTENT_TYPE_LATEST

# Define metrics
HTTP_REQUEST_COUNTER = Counter(
    'http_requests_total', 
    'Total number of HTTP requests', 
    ['method', 'endpoint', 'status_code']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds', 
    'HTTP request duration in seconds', 
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active', 
    'Number of active HTTP requests'
)

DB_QUERY_DURATION = Histogram(
    'db_query_duration_seconds', 
    'Database query duration in seconds', 
    ['query_type']
)

API_RATE_LIMIT_HITS = Counter(
    'api_rate_limit_hits_total', 
    'Number of times rate limits were hit', 
    ['endpoint']
)

SOCIAL_API_REQUESTS = Counter(
    'social_api_requests_total', 
    'Number of requests to social media APIs', 
    ['platform', 'endpoint', 'status']
)

SOCIAL_API_DURATION = Histogram(
    'social_api_request_duration_seconds', 
    'Social media API request duration in seconds', 
    ['platform', 'endpoint']
)

SCHEDULED_POSTS_TOTAL = Counter(
    'scheduled_posts_total', 
    'Number of scheduled posts', 
    ['platform', 'status']
)

USER_COUNT = Gauge(
    'users_total', 
    'Total number of registered users'
)

ACTIVE_SESSIONS = Gauge(
    'active_sessions', 
    'Number of active user sessions'
)


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to track request metrics"""
    ACTIVE_REQUESTS.inc()
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as e:
        status_code = 500
        raise e
    finally:
        duration = time.time() - start_time
        endpoint = request.url.path
        method = request.method
        
        HTTP_REQUEST_COUNTER.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        ACTIVE_REQUESTS.dec()


async def metrics_endpoint() -> Response:
    """Endpoint to expose Prometheus metrics"""
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


def setup_metrics(app: FastAPI) -> None:
    """Setup metrics collection and endpoint"""
    # Add middleware for tracking request metrics
    app.middleware("http")(metrics_middleware)
    
    # Add metrics endpoint
    app.add_route("/metrics", metrics_endpoint)
    
    # Log setup
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Prometheus metrics initialized")