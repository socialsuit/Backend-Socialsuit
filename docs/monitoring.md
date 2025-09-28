# Monitoring Configuration

This document describes the monitoring setup for the Social Suit project, including Sentry for error tracking and Prometheus for metrics collection.

## Environment Variables

### Sentry Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|--------|
| `SENTRY_DSN` | Sentry Data Source Name (DSN) | None | `https://abcdef123456@o123456.ingest.sentry.io/123456` |
| `SENTRY_TRACES_SAMPLE_RATE` | Percentage of transactions to sample for performance monitoring | `0.1` | `0.5` |
| `SENTRY_PROFILES_SAMPLE_RATE` | Percentage of sampled transactions to profile | `0.1` | `0.1` |
| `ENVIRONMENT` | Environment name (development, staging, production) | `development` | `production` |

### Prometheus Configuration

| Variable | Description | Default | Example |
|----------|-------------|---------|--------|
| `PROMETHEUS_METRICS_ENABLED` | Enable or disable Prometheus metrics collection | `true` | `true` or `false` |
| `PROMETHEUS_METRICS_PATH` | Path for the Prometheus metrics endpoint | `/metrics` | `/prometheus/metrics` |

## Metrics Collected

### Common Metrics

- **HTTP Request Metrics**:
  - `http_requests_total` - Total number of HTTP requests (labels: method, endpoint, status_code)
  - `http_request_duration_seconds` - HTTP request duration in seconds (labels: method, endpoint)
  - `http_requests_active` - Number of active HTTP requests

- **Database Metrics**:
  - `db_query_duration_seconds` - Database query duration in seconds (labels: query_type)

- **Rate Limiting Metrics**:
  - `api_rate_limit_hits_total` - Number of times rate limits were hit (labels: endpoint)

- **User Metrics**:
  - `users_total` - Total number of registered users
  - `active_sessions` - Number of active user sessions

### Social Suit Specific Metrics

- **Social Media Integration Metrics**:
  - `social_api_requests_total` - Number of requests to social media APIs (labels: platform, endpoint, status)
  - `social_api_request_duration_seconds` - Social media API request duration (labels: platform, endpoint)
  - `scheduled_posts_total` - Number of scheduled posts (labels: platform, status)

## Accessing Metrics

### Prometheus Endpoint

Metrics are exposed at the `/metrics` endpoint (or the path specified in `PROMETHEUS_METRICS_PATH`) in Prometheus format. This endpoint can be scraped by a Prometheus server.

### Sentry Dashboard

Errors and performance data are available in the Sentry dashboard. You'll need to create a Sentry account and project to access this data.