# Database Optimization Guide

This guide documents the comprehensive database optimization system implemented across MongoDB, PostgreSQL (Supabase), and Redis for the Social Suit application.

## Overview

The optimization system includes:
- **MongoDB**: Optimized indexes, aggregation pipelines, and data cleanup
- **PostgreSQL**: Advanced indexing, materialized views, and query optimization
- **Redis**: Intelligent caching with TTL strategies and memory optimization
- **Performance Monitoring**: Query tracking and performance analytics

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    MongoDB      │    │   PostgreSQL    │    │     Redis       │
│   (Analytics)   │    │  (Core Data)    │    │   (Caching)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Indexes       │    │ • Indexes       │    │ • Cache Layers  │
│ • Aggregations  │    │ • Mat. Views    │    │ • TTL Policies  │
│ • Cleanup       │    │ • Optimization  │    │ • Memory Mgmt   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Optimization    │
                    │ Coordinator     │
                    └─────────────────┘
```

## Components

### 1. Query Optimizer (`query_optimizer.py`)
Central coordination service that manages optimization across all databases.

**Key Features:**
- Performance monitoring and tracking
- Intelligent caching strategies
- Cross-database optimization coordination
- Automated recommendation system

### 2. MongoDB Optimizer (`mongodb_optimizer.py`)
Specialized service for MongoDB optimization.

**Optimizations:**
- **Compound Indexes**: Multi-field indexes for complex queries
- **Text Indexes**: Full-text search capabilities
- **TTL Indexes**: Automatic data expiration
- **Sparse Indexes**: Efficient storage for optional fields
- **Aggregation Pipeline Optimization**: Reordered stages for performance

**Collections Optimized:**
- `analytics_data`: User engagement and interaction data
- `user_engagements`: Platform-specific engagement metrics
- `content_performance`: Content effectiveness tracking
- `ab_tests`: A/B testing data and results
- `scheduled_posts`: Social media post scheduling
- `user_activity`: User behavior tracking

### 3. PostgreSQL Optimizer (`postgresql_optimizer.py`)
Advanced PostgreSQL optimization service.

**Optimizations:**
- **Composite Indexes**: Multi-column indexes for complex queries
- **Partial Indexes**: Conditional indexes for filtered data
- **Expression Indexes**: Indexes on computed values
- **Full-text Search**: GIN indexes for text search
- **Materialized Views**: Pre-computed aggregations

**Tables Optimized:**
- `users`: User account and profile data
- `scheduled_posts`: Post scheduling and status
- `post_engagement`: Engagement metrics and analytics
- `user_metrics`: User performance statistics
- `content_performance`: Content effectiveness data
- `query_performance`: Performance monitoring data
- `system_metrics`: System health and performance
- `ab_tests`: A/B testing configurations

**Materialized Views:**
- `daily_user_engagement`: Daily engagement summaries
- `weekly_content_performance`: Weekly content metrics
- `monthly_user_metrics`: Monthly user statistics

### 4. Repository Optimizations

#### User Repository (`user_repository.py`)
- Performance tracking on all queries
- Caching for frequently accessed user data
- Pagination for large result sets
- Aggregated user statistics
- Enhanced search capabilities

#### Scheduled Post Repository (`scheduled_post_repository.py`)
- Comprehensive caching strategy
- Bulk operations for efficiency
- Advanced filtering and search
- Performance monitoring
- Automated cache invalidation

#### Analytics Repository (`analytics_repository.py`)
- Multi-level caching (Redis + in-memory)
- Optimized aggregation queries
- Performance trend analysis
- Platform-specific optimizations
- Real-time data processing

### 5. Service Layer Optimizations

#### Scheduled Post Service (`scheduled_post_service.py`)
- Performance tracking decorators
- Intelligent caching with TTL strategies
- Bulk operations for multiple posts
- Advanced analytics and reporting
- Platform performance metrics
- Automated cache management

#### Analytics Services
- **Data Collector**: Batch processing and caching
- **Data Analyzer**: Advanced aggregations and insights
- **Cache Services**: Specialized caching for different data types

## Caching Strategy

### TTL Policies
```python
CACHE_TTL = {
    "user_data": 1800,        # 30 minutes
    "analytics_overview": 3600, # 1 hour
    "platform_insights": 1800, # 30 minutes
    "scheduled_posts": 300,    # 5 minutes
    "real_time_data": 60,     # 1 minute
    "historical_data": 7200,  # 2 hours
}
```

### Cache Invalidation
- **Event-driven**: Automatic invalidation on data changes
- **Pattern-based**: Bulk invalidation using Redis patterns
- **Time-based**: TTL expiration for stale data
- **Manual**: Administrative cache clearing

## Performance Monitoring

### Query Performance Tracking
```python
@query_performance_tracker("postgresql", "operation_name")
def database_operation():
    # Automatically tracks:
    # - Execution time
    # - Query complexity
    # - Cache hit/miss rates
    # - Error rates
```

### Metrics Collected
- Query execution times
- Cache hit/miss ratios
- Database connection pool usage
- Memory consumption
- Index usage statistics
- Slow query identification

## Installation and Setup

### 1. Initialize Optimizations
```python
from services.database.init_optimizations import initialize_database_optimizations

# Run full optimization setup
results = await initialize_database_optimizations()
```

### 2. Check Optimization Status
```python
from services.database.init_optimizations import check_optimization_status

# Get current optimization status
status = await check_optimization_status()
```

### 3. Run Maintenance
```python
from services.database.init_optimizations import run_database_maintenance

# Perform maintenance tasks
maintenance_results = await run_database_maintenance()
```

## Configuration

### Environment Variables
```bash
# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017/social_suit
MONGODB_MAX_POOL_SIZE=100

# PostgreSQL Configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/social_suit
POSTGRES_MAX_CONNECTIONS=20

# Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=50
REDIS_DEFAULT_TTL=3600
```

### Performance Tuning
```python
# MongoDB Settings
MONGODB_SETTINGS = {
    "maxPoolSize": 100,
    "minPoolSize": 10,
    "maxIdleTimeMS": 30000,
    "serverSelectionTimeoutMS": 5000
}

# PostgreSQL Settings
POSTGRESQL_SETTINGS = {
    "pool_size": 20,
    "max_overflow": 30,
    "pool_timeout": 30,
    "pool_recycle": 3600
}

# Redis Settings
REDIS_SETTINGS = {
    "max_connections": 50,
    "retry_on_timeout": True,
    "socket_timeout": 5,
    "socket_connect_timeout": 5
}
```

## Usage Examples

### 1. Optimized User Queries
```python
# Get user with caching
user = user_repository.get_by_email("user@example.com")

# Get user statistics with aggregation
stats = user_repository.get_user_statistics(days=30)

# Search users with pagination
users = user_repository.search_users("john", limit=20, offset=0)
```

### 2. Scheduled Post Operations
```python
# Create post with cache invalidation
post = scheduled_post_service.create_scheduled_post(
    user_id="123",
    platform="twitter",
    post_payload={"content": "Hello World!"},
    scheduled_time=datetime.now() + timedelta(hours=1)
)

# Get posts with caching and pagination
posts = scheduled_post_service.get_user_scheduled_posts(
    user_id="123",
    platform="twitter",
    limit=50,
    offset=0
)

# Bulk operations
success = scheduled_post_service.bulk_update_status(
    post_ids=[1, 2, 3],
    status="published"
)
```

### 3. Analytics Queries
```python
# Get cached analytics overview
overview = analytics_analyzer.get_user_overview(
    user_id="123",
    days=30
)

# Get platform insights with caching
insights = analytics_analyzer.get_platform_insights(
    user_id="123",
    platform="twitter",
    days=30
)
```

## Monitoring and Maintenance

### Performance Metrics Dashboard
The system provides comprehensive metrics for monitoring:

1. **Query Performance**
   - Average execution times
   - Slow query identification
   - Query frequency analysis

2. **Cache Performance**
   - Hit/miss ratios
   - Memory usage
   - Eviction rates

3. **Database Health**
   - Connection pool usage
   - Index effectiveness
   - Table sizes and growth

### Automated Maintenance
- **Daily**: Cache cleanup and optimization
- **Weekly**: Index maintenance and statistics updates
- **Monthly**: Data archival and cleanup

### Alerts and Notifications
- Slow query detection (>1 second)
- Low cache hit ratios (<80%)
- High memory usage (>90%)
- Connection pool exhaustion

## Best Practices

### 1. Query Optimization
- Use appropriate indexes for query patterns
- Implement pagination for large result sets
- Cache frequently accessed data
- Monitor and optimize slow queries

### 2. Caching Strategy
- Set appropriate TTL values based on data volatility
- Implement cache invalidation on data changes
- Use cache warming for critical data
- Monitor cache hit ratios

### 3. Database Design
- Normalize data appropriately
- Use materialized views for complex aggregations
- Implement proper indexing strategies
- Regular maintenance and cleanup

### 4. Performance Monitoring
- Track query performance metrics
- Monitor cache effectiveness
- Set up alerting for performance issues
- Regular performance reviews

## Troubleshooting

### Common Issues

1. **Slow Queries**
   - Check index usage
   - Analyze query execution plans
   - Consider query rewriting
   - Add missing indexes

2. **Low Cache Hit Ratios**
   - Review TTL settings
   - Check cache invalidation logic
   - Monitor cache memory usage
   - Optimize cache keys

3. **High Memory Usage**
   - Review cache sizes
   - Implement cache eviction policies
   - Monitor memory leaks
   - Optimize data structures

4. **Connection Pool Issues**
   - Monitor connection usage
   - Adjust pool sizes
   - Check for connection leaks
   - Implement connection timeouts

## Future Enhancements

1. **Advanced Analytics**
   - Machine learning-based query optimization
   - Predictive caching
   - Automated index recommendations

2. **Scaling Improvements**
   - Database sharding strategies
   - Read replica optimization
   - Distributed caching

3. **Monitoring Enhancements**
   - Real-time performance dashboards
   - Advanced alerting rules
   - Performance trend analysis

## Support and Maintenance

For issues or questions regarding the database optimization system:

1. Check the performance monitoring dashboard
2. Review the logs for error messages
3. Run the optimization status check
4. Consult this documentation
5. Contact the development team

---

*This optimization system is designed to provide high-performance, scalable database operations for the Social Suit application. Regular monitoring and maintenance ensure optimal performance as the application grows.*