# Social Suit Developer Documentation

## Overview

Social Suit is a comprehensive social media management tool built with FastAPI (Python). It provides features for content generation, post scheduling, auto-engagement, A/B testing, and analytics across multiple social media platforms.

## Key Features

- **AI Content Generation**: Uses DeepSeek via OpenRouter for creating captions, post ideas, and content suggestions
- **Post Scheduling**: Schedule posts across multiple platforms with flexible timing options
- **Auto-Engagement**: Automated responses to common queries with sentiment analysis and intent detection
- **A/B Testing**: Test different content variations to optimize engagement metrics
- **Analytics**: Track performance metrics across different social media platforms

## Project Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- MongoDB database
- Redis server

### Environment Setup

1. Clone the repository

```bash
git clone https://github.com/your-org/social_suit.git
cd social_suit
```

2. Create a virtual environment

```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following variables:

```
# Database URLs
DATABASE_URL=postgresql://username:password@localhost:5432/social_suit
MONGO_URL=mongodb://localhost:27017/social_suit
REDIS_URL=redis://localhost:6379/0

# JWT Authentication
JWT_SECRET=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# AI API Key
DEEPSEEK_OPENROUTER_API_KEY=your_deepseek_openrouter_api_key

# Cloudinary (for media uploads)
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Environment
ENVIRONMENT=development
```

5. Initialize the database

```bash
python -m scripts.init_db
```

### Running the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

API documentation will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Background Tasks

Social Suit uses background tasks for several features:

### Post Scheduling

The post scheduling system uses a worker process to publish posts at their scheduled times.

1. Start the scheduler worker:

```bash
python -m workers.scheduler_worker
```

This worker:
- Polls the database for posts that are due to be published
- Handles publishing to the appropriate social media platforms
- Updates post status in the database
- Handles retries for failed posts

### Analytics Collection

The analytics collection system periodically fetches data from social media platforms.

1. Start the analytics worker:

```bash
python -m workers.analytics_worker
```

This worker:
- Collects engagement metrics from connected platforms
- Processes and stores analytics data
- Updates A/B test results

## API Authentication

Social Suit uses JWT (JSON Web Tokens) for authentication.

### Authentication Flow

1. **Login**: User provides credentials and receives access and refresh tokens
   - Endpoint: `POST /api/v1/auth/login`
   - Response includes `access_token` and `refresh_token`

2. **Using the Access Token**: Include the token in the Authorization header
   - Format: `Authorization: Bearer {access_token}`

3. **Token Refresh**: Use the refresh token to get a new access token when it expires
   - Endpoint: `POST /api/v1/auth/refresh`
   - Request body: `{"refresh_token": "your_refresh_token"}`

4. **Logout**: Invalidate the refresh token
   - Endpoint: `POST /api/v1/auth/logout`
   - Request body: `{"refresh_token": "your_refresh_token"}`

## Integration with DeepSeek via OpenRouter

Social Suit uses DeepSeek through the OpenRouter API for AI content generation.

### Configuration

The integration is configured in `services/ai_client.py` through the unified `AIClient` class.

### Example Usage

```python
from app.services.ai_client import ai_client

# Generate content
caption = ai_client.generate_caption(
    topic="Tech innovation and future trends",
    style="casual",
    hashtag_count=5
)

print(caption)
# Example output: "Exciting news! Our new multi-platform scheduling feature is now live. 
# Streamline your social media workflow with just a few clicks. #SocialSuit #Productivity #SocialMediaManagement"
```

### Available Methods

- `generate_caption(prompt, style, hashtags)`: Generate social media captions
- `generate_content(prompt, content_type, length)`: Generate general content
- `clean_caption(caption)`: Clean and format generated captions

## A/B Testing

The A/B testing system allows users to test different content variations.

### Creating an A/B Test

```python
from services.ab_testing import run_ab_test

# Create an A/B test
test_result = run_ab_test(
    user_id="user123",
    test_name="Caption Style Test",
    variations=[
        {"content": "Check out our new feature!", "type": "casual"},
        {"content": "Introducing our latest innovation in social media management.", "type": "professional"}
    ],
    target_metric="engagement_rate",
    audience_percentage=50,
    platforms=["twitter", "linkedin"]
)

print(test_result)
# Example output: {"test_id": "ab123", "status": "running", "estimated_completion": "2023-06-20T14:30:00Z"}
```

### Retrieving A/B Test Results

Results are automatically collected by the analytics worker and can be accessed through the API.

## Auto-Engagement

The auto-engagement system processes incoming messages and generates appropriate responses.

### Example Usage

```python
from services.auto_engagement import auto_engage

# Process a message
response = auto_engage(
    message="What are the pricing options for Social Suit?",
    platform="twitter",
    context={"user_tier": "premium"},
    user_id="user123"
)

print(response)
# Example output: {
#   "reply": "Thanks for your interest in Social Suit! Our Premium plan starts at $29/month and includes all core features plus advanced analytics. Would you like me to send you our full pricing guide?",
#   "intent": "pricing",
#   "sentiment": "neutral",
#   "confidence": 0.92,
#   "suggested_actions": ["send_pricing_pdf", "offer_demo"]
# }
```

## API Endpoints

Social Suit's API is organized into the following groups:

### Authentication

- `POST /api/v1/auth/register`: Register a new user
- `POST /api/v1/auth/login`: Login and get tokens
- `POST /api/v1/auth/refresh`: Refresh access token
- `POST /api/v1/auth/logout`: Logout and invalidate tokens

### AI Content

- `POST /api/v1/content/generate`: Generate AI content for social media

### Scheduling

- `POST /api/v1/scheduled-posts`: Create a scheduled post
- `GET /api/v1/scheduled-posts`: Get all scheduled posts
- `GET /api/v1/scheduled-posts/{post_id}`: Get a specific scheduled post
- `PUT /api/v1/scheduled-posts/{post_id}`: Update a scheduled post
- `DELETE /api/v1/scheduled-posts/{post_id}`: Delete a scheduled post
- `POST /api/v1/scheduled-posts/{post_id}/publish`: Publish a post immediately

### Engagement

- `POST /api/v1/engage/reply`: Generate an auto-reply to a message

### A/B Testing

- `POST /api/v1/ab-test/create`: Create a new A/B test

### Analytics

- `GET /api/v1/analytics/insights`: Get analytics insights

## Error Handling

The API uses standard HTTP status codes for error responses:

- `400 Bad Request`: Invalid input or parameters
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

Error responses follow this format:

```json
{
  "detail": "Error message describing the issue"
}
```

## Best Practices

1. **Rate Limiting**: The API implements rate limiting to prevent abuse. Be mindful of request frequency.

2. **Pagination**: For endpoints that return lists, use the `limit` and `offset` query parameters to paginate results.

3. **Error Handling**: Always handle error responses in your client applications.

4. **Authentication**: Keep access tokens secure and implement proper token refresh logic.

5. **Background Processing**: For operations that may take time (like publishing to multiple platforms), use the background task endpoints.

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Check that your JWT token is valid and not expired
   - Ensure you're using the correct format in the Authorization header

2. **Database Connection Issues**:
   - Verify your database connection strings in the `.env` file
   - Ensure the database servers are running

3. **OpenRouter API Errors**:
   - Check your API key is valid
   - Verify you have sufficient credits in your OpenRouter account

### Logging

The application uses structured logging. Check the logs for detailed error information:

```bash
tail -f logs/app.log
```

## Contributing

Please see the `CONTRIBUTING.md` file for guidelines on how to contribute to the project.

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.