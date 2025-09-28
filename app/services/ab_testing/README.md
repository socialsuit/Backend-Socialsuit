# AB Testing Service

The AB Testing service provides comprehensive A/B testing functionality for the Social Suit platform, allowing users to create, manage, and analyze split tests for their content and campaigns.

## Features

- ✅ **Test Creation**: Create multi-variant A/B tests with custom configurations
- ✅ **Real-time Metrics**: Track impressions, engagements, clicks, and conversions
- ✅ **Intelligent Caching**: Redis-based caching for optimal performance
- ✅ **Winner Determination**: Automatic winner calculation based on target metrics
- ✅ **User Management**: User-specific test isolation and access control
- ✅ **Performance Monitoring**: Built-in performance tracking and optimization

## Architecture

### Core Components

1. **`ab_test_service.py`** - Main business logic for AB testing operations
2. **`cache_service.py`** - Redis caching layer for performance optimization
3. **`__init__.py`** - Package initialization and exports

### API Endpoints

The AB testing functionality is exposed through REST API endpoints in `services/endpoint/ab_test.py`:

- `POST /api/v1/ab-tests` - Create a new AB test
- `GET /api/v1/ab-tests/{test_id}` - Get test details and results
- `GET /api/v1/user/tests` - Get all tests for authenticated user
- `POST /api/v1/ab-tests/{test_id}/metrics/{variation}` - Update test metrics
- `POST /api/v1/ab-tests/{test_id}/complete` - Complete a test and determine winner

## Usage

### Creating an AB Test

```python
from services.ab_testing import run_ab_test

test_config = {
    "name": "Button Color Test",
    "description": "Testing different button colors",
    "variations": [
        {
            "name": "Control",
            "content": {"button_color": "blue"}
        },
        {
            "name": "Variant",
            "content": {"button_color": "red"}
        }
    ],
    "target_metric": "conversion_rate",
    "duration_days": 7,
    "traffic_split": 50
}

result = await run_ab_test("user_id", test_config)
```

### Updating Test Metrics

```python
from services.ab_testing.ab_test_service import update_test_metrics

metrics = {
    "impressions": 1000,
    "engagements": 150,
    "clicks": 75,
    "conversions": 25
}

await update_test_metrics("test_id", "user_id", "control", metrics)
```

### Getting Test Results

```python
from services.ab_testing.ab_test_service import get_test_details

test_details = await get_test_details("test_id", "user_id")
print(f"Test status: {test_details['status']}")
print(f"Winner: {test_details.get('winner', 'TBD')}")
```

## API Reference

### Test Configuration Schema

```json
{
  "name": "string",
  "description": "string",
  "variations": [
    {
      "name": "string",
      "content": {}
    }
  ],
  "target_metric": "conversion_rate|click_through_rate|engagement_rate",
  "duration_days": "integer",
  "traffic_split": "integer (1-100)"
}
```

### Metrics Update Schema

```json
{
  "impressions": "integer",
  "engagements": "integer", 
  "clicks": "integer",
  "conversions": "integer"
}
```

## Caching Strategy

The AB testing service uses Redis for caching with the following TTL settings:

- **Test Details**: 30 minutes
- **Test Results**: 15 minutes  
- **User Tests**: 1 hour
- **Active Tests**: 5 minutes

Cache keys follow the pattern: `ab_test:{test_id}:{operation}`

## Performance Considerations

1. **Caching**: All frequently accessed data is cached in Redis
2. **Aggregation**: MongoDB aggregation pipelines for efficient data processing
3. **Indexing**: Proper database indexing for optimal query performance
4. **Batch Operations**: Bulk operations for metrics updates

## Error Handling

The service includes comprehensive error handling for:

- Invalid test configurations
- Unauthorized access attempts
- Database connection issues
- Cache failures
- Metric calculation errors

## Testing

Run the test suite:

```bash
pytest tests/test_ab_testing.py -v
```

## Example Usage

See `examples/ab_testing_example.py` for a complete demonstration of the AB testing functionality.

## Dependencies

- **FastAPI**: Web framework
- **MongoDB**: Primary data storage
- **Redis**: Caching layer
- **Pydantic**: Data validation
- **asyncio**: Asynchronous operations

## Configuration

Ensure the following environment variables are set:

```env
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
```

## Monitoring

The service includes built-in performance monitoring through:

- MongoDB performance decorators
- Redis operation tracking
- Cache hit/miss statistics
- Response time measurements