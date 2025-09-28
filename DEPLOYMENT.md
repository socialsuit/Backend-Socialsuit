# Production Deployment Guide for Social Suit

## Deploying on Render.com

This guide provides step-by-step instructions for deploying the Social Suit application on Render.com with zero errors.

### Prerequisites

1. A Render.com account
2. Your codebase pushed to a Git repository (GitHub, GitLab, etc.)
3. API keys and credentials for all required services (see the .env files)

### Deployment Steps

#### 1. Prepare Your Repository

1. Ensure your codebase is in a Git repository (GitHub, GitLab, etc.)
2. Verify that all files are committed, including:
   - Dockerfiles (optimized for production with Gunicorn + Uvicorn)
   - render.yaml (with proper service configurations)
   - .env files (with placeholders for sensitive information)

#### 2. Connect Your Repository to Render

1. Log in to your Render dashboard at https://dashboard.render.com
2. Click on "New" and select "Blueprint"
3. Connect your Git repository by selecting the appropriate provider
4. Select the repository containing the Social Suit code
5. Choose the branch you want to deploy (default: main)

#### 3. Configure Environment Variables

1. After connecting your repository, Render will detect the `render.yaml` file
2. For each service, you'll need to configure environment variables
3. Use the values from your .env files, replacing placeholders with actual values:
   - For database URLs, use the values provided by Render for managed databases
   - For Redis URLs, use the values provided by Render for managed Redis
   - For sensitive information (API keys, secrets), enter your actual values

**Important:** Generate secure values for the following:
   - `JWT_SECRET` (use a secure random string generator)
   - `SECRET_KEY` (use a secure random string generator)
   - `SECURITY_PASSWORD_SALT` (use a secure random string generator)

#### 4. Deploy the Blueprint

1. Review all service configurations to ensure they match your requirements
2. Click "Apply Blueprint" to start the deployment process
3. Render will automatically create all services defined in `render.yaml`:
   - Social Suit web service (with autoscaling)
   - Social Suit worker service (with autoscaling)
   - PostgreSQL databases (social-suit-db)
   - Redis instances (social-suit-redis)

#### 5. Verify the Deployment

1. Monitor the build and deployment logs for each service
2. Check the health endpoints for web services:
   - Social Suit: https://social-suit.onrender.com/health
3. Verify database connections by checking application logs
4. Test worker functionality by triggering background tasks

### Scaling Services

#### Autoscaling Configuration

Both web and worker services are configured with autoscaling in the `render.yaml` file:
- Minimum instances: 2
- Maximum instances: 6

This ensures your application can handle varying loads efficiently while optimizing costs.

#### Manual Scaling Adjustments

If you need to adjust the autoscaling parameters:

1. Navigate to the service in your Render dashboard
2. Click on "Settings"
3. Under "Autoscaling", adjust the minimum and maximum instances
4. Save changes

#### Scaling Databases

1. Navigate to the database in your Render dashboard
2. Click on "Settings"
3. Choose a higher plan with more resources
4. Confirm the upgrade

#### Performance Monitoring

1. Use Render's built-in metrics to monitor CPU and memory usage
2. Set up alerts for high resource utilization
3. Consider implementing application-level metrics with Prometheus or similar tools

### Troubleshooting

#### Common Issues and Solutions

1. **Build Failures**
   - Check the build logs for specific error messages
   - Verify that all dependencies are correctly specified in requirements.txt
   - Ensure Dockerfiles are correctly configured for your application
   - Check for syntax errors in your code

2. **Database Connection Errors**
   - Verify the `POSTGRES_URL` environment variable is correctly set with the Render-provided connection string
   - Check if the database service is running in your Render dashboard
   - Ensure your application's database models match the schema
   - Check for firewall or network issues between services

3. **Redis Connection Errors**
   - Verify the `REDIS_URL` environment variable is correctly set with the Render-provided connection string
   - Check if the Redis service is running in your Render dashboard
   - Ensure Redis password is correctly configured if authentication is enabled
   - Check for firewall or network issues between services

4. **Worker Not Processing Tasks**
   - Check worker logs for specific error messages
   - Verify Redis connection is working (Celery uses Redis as a broker)
   - Ensure Celery is configured correctly with the right queue names
   - Check that task definitions are properly imported and registered
   - Verify that the worker service has the correct environment variables

5. **Web Service Errors**
   - Check application logs for specific error messages
   - Verify that the health endpoint is correctly implemented
   - Ensure all required environment variables are set
   - Check for memory or CPU constraints that might be causing crashes

#### Effective Log Analysis

1. Navigate to the service in your Render dashboard
2. Click on "Logs" to view real-time logs
3. Use the search functionality to filter logs by:
   - Error level (ERROR, WARNING)
   - Service name
   - Timestamp
   - Specific keywords related to your issue
4. Set up log alerts for critical errors
5. Consider implementing structured logging in your application for better debugging

### Maintenance

#### Updating the Application

1. Push changes to your Git repository
2. Render will automatically detect changes and rebuild/redeploy

#### Database Backups

1. Navigate to the database in your Render dashboard
2. Click on "Backups"
3. Configure automatic backup schedule or create manual backups

### Security Considerations

1. Ensure all sensitive environment variables are properly set
2. Use strong, unique passwords for all services
3. Regularly update dependencies to patch security vulnerabilities
4. Enable HTTPS for all web services (Render provides this by default)

### Monitoring

1. Set up health checks for all services
2. Configure alerts for service outages
3. Monitor resource usage to optimize costs

By following this guide, you should have a fully functional deployment of Social Suit on Render.com with minimal manual configuration required.