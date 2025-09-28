# Monitoring Dashboard Setup

This guide explains how to set up monitoring dashboards for the Social Suit project using Grafana with Prometheus and Sentry.

## Prerequisites

- Docker and Docker Compose installed
- Prometheus metrics endpoints configured in the application
- Sentry instrumentation configured in the application

## Prometheus and Grafana Setup

### 1. Create a Docker Compose Configuration

Create a file named `docker-compose-monitoring.yml` in the project root:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped
    depends_on:
      - prometheus

  alertmanager:
    image: prom/alertmanager:latest
    container_name: alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager:/etc/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
```

### 2. Configure Prometheus

Create a directory structure and configuration files:

```
mkdir -p prometheus alertmanager grafana/provisioning/datasources grafana/provisioning/dashboards
```

Create `prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'social-suit'
    metrics_path: /metrics  # Adjust if you've changed PROMETHEUS_METRICS_PATH
    static_configs:
      - targets: ['host.docker.internal:8000']  # Adjust port as needed
        labels:
          service: 'social-suit'
```

### 3. Configure AlertManager

Create `alertmanager/alertmanager.yml`:

```yaml
global:
  resolve_timeout: 5m

route:
  group_by: ['alertname', 'service']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 1h
  receiver: 'email-notifications'

receivers:
  - name: 'email-notifications'
    email_configs:
      - to: 'alerts@example.com'  # Replace with your email
        from: 'alertmanager@example.com'  # Replace with sender email
        smarthost: 'smtp.example.com:587'  # Replace with your SMTP server
        auth_username: 'alertmanager@example.com'  # Replace with your username
        auth_password: 'password'  # Replace with your password
        send_resolved: true
```

### 4. Copy Alert Rules

Copy the alert rules from `docs/prometheus-alerts.yml` to `prometheus/alert_rules.yml`.

### 5. Configure Grafana Datasource

Create `grafana/provisioning/datasources/datasource.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### 6. Start the Monitoring Stack

```bash
docker-compose -f docker-compose-monitoring.yml up -d
```

## Accessing the Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (login with admin/admin)
- **AlertManager**: http://localhost:9093

## Setting Up Grafana Dashboards

### 1. Log in to Grafana

Access http://localhost:3000 and log in with the default credentials (admin/admin).

### 2. Import Dashboards

You can import pre-built dashboards or create custom ones:

#### For FastAPI Applications

1. Go to Dashboards > Import
2. Enter dashboard ID `14282` (FastAPI dashboard by mldeng) or upload the JSON file
3. Select the Prometheus data source and click Import

### 3. Create Custom Dashboards

Create a dashboard for Social Suit with the following panels:

#### Social Suit Dashboard

1. **HTTP Request Overview**:
   - Graph of request rate by endpoint
   - Graph of error rate
   - Heatmap of request duration

2. **Social Media API Metrics**:
   - Graph of social API requests by platform
   - Graph of social API error rate by platform
   - Graph of social API request duration

3. **Scheduled Posts**:
   - Graph of scheduled posts by status and platform

4. **System Resources**:
   - CPU and memory usage
   - Active requests

## Sentry Dashboard

### 1. Access Sentry

Log in to your Sentry account at https://sentry.io and navigate to your project.

### 2. Configure Alerts

Set up alert rules in Sentry:

1. Go to Alerts > Rules
2. Create rules for:
   - Error frequency (e.g., more than 100 errors in 1 hour)
   - New issues
   - Performance issues (e.g., transactions taking longer than 1 second)

### 3. Set Up Sentry Dashboards

Create custom dashboards in Sentry to monitor:

1. Error trends over time
2. Most frequent errors
3. Performance metrics
4. User impact

## Integration with Slack/Teams

### AlertManager Integration

Update the `alertmanager.yml` file to include Slack or Microsoft Teams webhooks:

```yaml
receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#monitoring-alerts'
        send_resolved: true
```

### Sentry Integration

1. In Sentry, go to Settings > Integrations
2. Find and configure the Slack or Microsoft Teams integration
3. Select which projects and alert types to forward to your chat platform

## Maintenance

- Regularly update the monitoring stack components
- Review and adjust alert thresholds based on application performance
- Archive or delete old data to manage storage
- Backup Grafana dashboards and Prometheus configuration