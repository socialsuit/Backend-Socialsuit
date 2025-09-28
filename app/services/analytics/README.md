# Analytics System Documentation

## Overview

The analytics system provides comprehensive data collection, analysis, and visualization capabilities for social media engagement metrics. It enables users to track performance across multiple platforms, analyze content effectiveness, and make data-driven decisions for their social media strategy.

## Components

### Database Models

- **PostEngagement**: Tracks individual engagement events (likes, comments, shares, etc.)
- **UserMetrics**: Stores daily aggregated user metrics per platform (followers, reach, impressions, etc.)
- **ContentPerformance**: Captures performance metrics for individual content pieces

### Core Modules

- **data_collector.py**: Collects analytics data from various social media platforms
- **data_analyzer.py**: Analyzes collected data to generate insights and recommendations
- **chart_generator.py**: Formats data for frontend visualization
- **init_analytics_db.py**: Initializes the database with sample data for testing

### API Endpoints

All endpoints are available under the `/api/v1/analytics` prefix.

#### Data Collection

- `POST /collect/{user_id}`: Triggers data collection for a user
  - Query parameters:
    - `days_back`: Number of days to collect data for (default: 7)
    - `background`: Whether to run collection in background (default: true)

#### Data Retrieval

- `GET /overview/{user_id}`: Get user's analytics overview
- `GET /platform/{user_id}/{platform}`: Get platform-specific insights
- `GET /content/{user_id}/{platform}/{post_id}`: Get analytics for a specific content piece
- `GET /recommendations/{user_id}`: Get content and posting recommendations
- `GET /comparative/{user_id}`: Get comparative analytics across platforms

#### Visualization Data

- `GET /chart/{user_id}/{metric}`: Get raw chart data for a specific metric
- `GET /visualization/{user_id}/{chart_type}`: Get formatted visualization data
  - Available chart types:
    - `time_series`: Engagement metrics over time
    - `platform_comparison`: Compare metrics across platforms
    - `engagement_breakdown`: Breakdown of engagement types
    - `content_performance`: Performance by content type
    - `best_times`: Best posting times analysis
    - `content_type`: Performance by content type
    - `dashboard`: Complete dashboard data

## Usage

### Initializing Sample Data

To initialize the database with sample analytics data:

```bash
python init_analytics.py
```

To generate data for a specific user:

```bash
python init_analytics.py <user_id> [days_back]
```

### Collecting Real Data

Real data collection is triggered via the API endpoint:

```
POST /api/v1/analytics/collect/{user_id}?days_back=7&background=true
```

### Accessing Analytics

Access analytics data through the API endpoints listed above. For example:

```
GET /api/v1/analytics/overview/{user_id}
```

### Visualization

The system provides formatted data for various chart types that can be directly used with Chart.js or similar visualization libraries:

```
GET /api/v1/analytics/visualization/{user_id}/platform_comparison
```

## Integration with Frontend

The analytics system provides data in formats compatible with popular charting libraries like Chart.js. Frontend applications can fetch data from the visualization endpoints and render charts without additional data transformation.

## Future Enhancements

- Real-time analytics with WebSocket support
- AI-powered content optimization recommendations
- Custom report generation and scheduling
- Advanced segmentation and filtering options