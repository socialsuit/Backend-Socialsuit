# Analytics System Documentation

## Overview

The analytics system is a comprehensive solution for collecting, analyzing, and visualizing social media engagement data across multiple platforms. It provides valuable insights into content performance, audience demographics, and engagement patterns, enabling users to make data-driven decisions for their social media strategy.

## Architecture

The analytics system consists of the following components:

1. **Database Models**: SQLAlchemy models for storing analytics data
2. **Data Collection**: Services for collecting data from various social media platforms
3. **Data Analysis**: Services for analyzing and generating insights from collected data
4. **Visualization**: Services for formatting data for frontend visualization
5. **API Endpoints**: FastAPI endpoints for accessing analytics data

## Database Models

### PostEngagement

Stores individual engagement events for posts.

```python
class PostEngagement(Base):
    __tablename__ = "post_engagements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    post_id = Column(String, nullable=False)
    engagement_type = Column(Enum(EngagementType), nullable=False)
    engagement_time = Column(DateTime, default=func.now())
    source_country = Column(String, nullable=True)
    source_device = Column(String, nullable=True)
    metadata = Column(JSON, nullable=True)
```

### UserMetrics

Stores daily aggregated user metrics per platform.

```python
class UserMetrics(Base):
    __tablename__ = "user_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    posts_count = Column(Integer, default=0)
    profile_views = Column(Integer, default=0)
    website_clicks = Column(Integer, default=0)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    audience_demographics = Column(JSON, nullable=True)
```

### ContentPerformance

Stores performance metrics for individual content pieces.

```python
class ContentPerformance(Base):
    __tablename__ = "content_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    post_id = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    posted_at = Column(DateTime, nullable=False)
    reach = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    video_views = Column(Integer, default=0)
    video_completion_rate = Column(Float, default=0.0)
    metadata = Column(JSON, nullable=True)
```

## Data Collection

The `AnalyticsCollector` class in `services/analytics/data_collector.py` is responsible for collecting data from various social media platforms. It provides methods for:

- Collecting data from specific platforms (Facebook, Instagram, Twitter, LinkedIn, TikTok)
- Processing and storing collected data in the database
- Generating sample data for testing purposes

```python
async def collect_platform_data(self, user_id: str, platform: str, days_back: int = 7):
    """Collect data for a specific platform"""
    # Platform-specific collection logic
    if platform == "facebook":
        return await self._collect_facebook_data(user_id, days_back)
    elif platform == "instagram":
        return await self._collect_instagram_data(user_id, days_back)
    # ... other platforms
```

## Data Analysis

The `AnalyticsAnalyzer` class in `services/analytics/data_analyzer.py` is responsible for analyzing collected data and generating insights. It provides methods for:

- Generating user overview analytics
- Analyzing platform-specific insights
- Analyzing content performance
- Generating recommendations based on analytics
- Providing comparative analytics across platforms

```python
async def get_user_overview(self, user_id: str):
    """Get overview analytics for a user"""
    # Get user platforms
    platforms = await self._get_user_platforms(user_id)
    
    # Get metrics for each platform
    platform_metrics = {}
    total_followers = 0
    total_engagement = 0
    
    for platform in platforms:
        metrics = await self._get_platform_metrics(user_id, platform)
        platform_metrics[platform] = metrics
        total_followers += metrics.get("followers", 0)
        total_engagement += metrics.get("total_engagement", 0)
    
    # Calculate growth rate
    growth_rate = await self._calculate_growth_rate(user_id, platforms)
    
    # Return overview data
    return {
        "platforms": platforms,
        "platform_metrics": platform_metrics,
        "total_followers": total_followers,
        "total_engagement": total_engagement,
        "growth_rate": growth_rate,
        "avg_engagement_rate": await self._calculate_avg_engagement_rate(user_id, platforms)
    }
```

## Visualization

The `ChartGenerator` class in `services/analytics/chart_generator.py` is responsible for formatting data for frontend visualization. It provides methods for generating various types of chart data:

- Time series charts for engagement metrics over time
- Platform comparison charts for comparing metrics across platforms
- Engagement breakdown charts for analyzing engagement types
- Content performance charts for analyzing content types
- Best posting times charts for optimizing posting schedule
- Content type performance charts for analyzing content effectiveness

```python
async def generate_time_series_chart(self, user_id: str, days: int = 30):
    """Generate time series chart data for engagement metrics over time"""
    # Get data from analyzer
    data = await self.analyzer.get_time_series_data(user_id, days)
    
    # Format data for Chart.js
    return {
        "labels": data["dates"],
        "datasets": [
            {
                "label": "Likes",
                "data": data["likes"],
                "borderColor": "#4361ee",
                "backgroundColor": "rgba(67, 97, 238, 0.1)",
                "fill": True
            },
            {
                "label": "Comments",
                "data": data["comments"],
                "borderColor": "#3a0ca3",
                "backgroundColor": "rgba(58, 12, 163, 0.1)",
                "fill": True
            },
            # ... other metrics
        ]
    }
```

## API Endpoints

The analytics system provides the following API endpoints:

### Data Collection

- `POST /api/v1/analytics/collect/{user_id}`: Trigger data collection for a user

### Data Retrieval

- `GET /api/v1/analytics/overview/{user_id}`: Get user's analytics overview
- `GET /api/v1/analytics/platform/{user_id}/{platform}`: Get platform-specific insights
- `GET /api/v1/analytics/content/{user_id}/{platform}/{post_id}`: Get analytics for a specific content piece
- `GET /api/v1/analytics/recommendations/{user_id}`: Get content and posting recommendations
- `GET /api/v1/analytics/comparative/{user_id}`: Get comparative analytics across platforms

### Visualization Data

- `GET /api/v1/analytics/chart/{user_id}/{metric}`: Get raw chart data for a specific metric
- `GET /api/v1/analytics/visualization/{user_id}/{chart_type}`: Get formatted visualization data

## Usage Examples

### Initializing the Analytics Database

```bash
# Initialize for all users
python init_analytics.py

# Initialize for a specific user
python init_analytics.py <user_id> [days_back]
```

### Collecting Analytics Data

```python
# Collect data for a user
from services.analytics.data_collector import AnalyticsCollector

async def collect_user_data(user_id: str):
    collector = AnalyticsCollector(db)
    await collector.collect_all_platform_data(user_id)
```

### Analyzing Analytics Data

```python
# Get user overview
from services.analytics.data_analyzer import AnalyticsAnalyzer

async def get_user_analytics(user_id: str):
    analyzer = AnalyticsAnalyzer(db)
    overview = await analyzer.get_user_overview(user_id)
    return overview
```

### Generating Chart Data

```python
# Generate chart data for frontend
from services.analytics.chart_generator import ChartGenerator

async def get_chart_data(user_id: str, chart_type: str):
    chart_generator = ChartGenerator(db)
    
    if chart_type == "time_series":
        return await chart_generator.generate_time_series_chart(user_id)
    elif chart_type == "platform_comparison":
        return await chart_generator.generate_platform_comparison_chart(user_id)
    # ... other chart types
```

## Frontend Integration

The analytics system provides data in formats compatible with popular charting libraries like Chart.js. The `frontend_examples/analytics_dashboard.html` file demonstrates how to integrate the analytics API with a frontend application.

```javascript
// Load chart data
function loadChartData(userId, chartType, chartElementId) {
    fetch(`${API_BASE_URL}/visualization/${userId}/${chartType}`)
        .then(response => response.json())
        .then(data => {
            renderChart(chartType, chartElementId, data);
        })
        .catch(error => {
            console.error(`Error loading ${chartType} chart data:`, error);
        });
}

// Render chart based on type
function renderChart(chartType, chartElementId, data) {
    const ctx = document.getElementById(chartElementId).getContext('2d');
    
    // Create chart
    new Chart(ctx, {
        type: getChartType(chartType),
        data: data,
        options: getChartOptions(chartType)
    });
}
```

## Future Enhancements

1. **Real-time Analytics**: Implement WebSocket support for real-time analytics updates
2. **AI-powered Recommendations**: Enhance recommendation engine with machine learning models
3. **Custom Reports**: Add support for custom report generation and scheduling
4. **Advanced Segmentation**: Implement advanced segmentation and filtering options for analytics data

## Troubleshooting

### Common Issues

1. **Missing Data**: If analytics data is missing, check if the data collection process completed successfully
2. **Performance Issues**: If the analytics system is slow, consider optimizing database queries or implementing caching
3. **API Errors**: Check the logs for detailed error messages and ensure the database connection is working properly

### Logging

The analytics system uses the application's logging system for debugging and monitoring. Check the logs for detailed information about data collection, analysis, and API requests.

```python
# Set up logger
logger = setup_logger("analytics")

# Log messages
logger.info("Collecting analytics data for user %s", user_id)
logger.error("Error collecting analytics data: %s", str(error))
```

## Conclusion

The analytics system provides a comprehensive solution for collecting, analyzing, and visualizing social media engagement data. It enables users to make data-driven decisions for their social media strategy and optimize their content for maximum engagement.