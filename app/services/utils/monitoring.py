from prometheus_client import Counter, Gauge, Histogram, Summary
import time
from functools import wraps

# Initialize Prometheus metrics

# Counters - track how many times something happens
POST_ATTEMPTS = Counter('socialsuit_post_attempts_total', 'Total number of post attempts', ['platform'])
POST_SUCCESSES = Counter('socialsuit_post_successes_total', 'Total number of successful posts', ['platform'])
POST_FAILURES = Counter('socialsuit_post_failures_total', 'Total number of failed posts', ['platform'])
POST_RETRIES = Counter('socialsuit_post_retries_total', 'Total number of post retries', ['platform'])
TOKEN_REFRESH_ATTEMPTS = Counter('socialsuit_token_refresh_attempts_total', 'Total number of token refresh attempts', ['platform'])
TOKEN_REFRESH_SUCCESSES = Counter('socialsuit_token_refresh_successes_total', 'Total number of successful token refreshes', ['platform'])
TOKEN_REFRESH_FAILURES = Counter('socialsuit_token_refresh_failures_total', 'Total number of failed token refreshes', ['platform'])

# Gauges - track current values
SCHEDULED_POSTS_PENDING = Gauge('socialsuit_scheduled_posts_pending', 'Number of pending scheduled posts')
SCHEDULED_POSTS_RETRY = Gauge('socialsuit_scheduled_posts_retry', 'Number of scheduled posts in retry state')
SCHEDULED_POSTS_FAILED = Gauge('socialsuit_scheduled_posts_failed', 'Number of failed scheduled posts')
SCHEDULED_POSTS_COMPLETED = Gauge('socialsuit_scheduled_posts_completed', 'Number of completed scheduled posts')

# Histograms - track distribution of values
POST_DURATION = Histogram('socialsuit_post_duration_seconds', 'Time taken to post to platform', ['platform'])
TOKEN_REFRESH_DURATION = Histogram('socialsuit_token_refresh_duration_seconds', 'Time taken to refresh tokens', ['platform'])

# Summaries - similar to histograms but with quantiles
POST_LATENCY = Summary('socialsuit_post_latency_seconds', 'Latency of posting to platform', ['platform'])


# Define metrics at module level to avoid duplicate registration
ANALYTICS_COLLECTION_ATTEMPTS = Counter('socialsuit_analytics_collection_attempts_total', 'Total number of analytics collection attempts', ['platform'])

def track_analytics_collection(platform):
    """Track analytics collection metrics"""
    # Increment the counter for analytics collection attempts
    ANALYTICS_COLLECTION_ATTEMPTS.labels(platform=platform).inc()
    
    # Use as a context manager to track duration
    return POST_DURATION.labels(platform=platform).time()


def track_post_metrics(platform):
    """
    Decorator to track post metrics for a function.
    
    Args:
        platform: The platform name (e.g., 'facebook', 'twitter')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Increment attempt counter
            POST_ATTEMPTS.labels(platform=platform).inc()
            
            # Track duration
            start_time = time.time()
            
            try:
                # Call the original function
                result = func(*args, **kwargs)
                
                # Track success/failure/retry based on result
                if result.get('success', False):
                    POST_SUCCESSES.labels(platform=platform).inc()
                else:
                    POST_FAILURES.labels(platform=platform).inc()
                    
                if result.get('retry', False):
                    POST_RETRIES.labels(platform=platform).inc()
                
                return result
            finally:
                # Record duration
                duration = time.time() - start_time
                POST_DURATION.labels(platform=platform).observe(duration)
                POST_LATENCY.labels(platform=platform).observe(duration)
        
        return wrapper
    return decorator


def track_token_refresh(platform):
    """
    Decorator to track token refresh metrics for a function.
    
    Args:
        platform: The platform name (e.g., 'facebook', 'twitter')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Increment attempt counter
            TOKEN_REFRESH_ATTEMPTS.labels(platform=platform).inc()
            
            # Track duration
            start_time = time.time()
            
            try:
                # Call the original function
                result = func(*args, **kwargs)
                
                # Track success/failure based on result
                if result:
                    TOKEN_REFRESH_SUCCESSES.labels(platform=platform).inc()
                else:
                    TOKEN_REFRESH_FAILURES.labels(platform=platform).inc()
                
                return result
            finally:
                # Record duration
                duration = time.time() - start_time
                TOKEN_REFRESH_DURATION.labels(platform=platform).observe(duration)
        
        return wrapper
    return decorator


def update_scheduled_post_gauges(pending_count, retry_count, failed_count, completed_count):
    """
    Update the gauges for scheduled post counts.
    
    Args:
        pending_count: Number of pending posts
        retry_count: Number of posts in retry state
        failed_count: Number of failed posts
        completed_count: Number of completed posts
    """
    SCHEDULED_POSTS_PENDING.set(pending_count)
    SCHEDULED_POSTS_RETRY.set(retry_count)
    SCHEDULED_POSTS_FAILED.set(failed_count)
    SCHEDULED_POSTS_COMPLETED.set(completed_count)