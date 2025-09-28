from flask import Flask, jsonify, request
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set default environment variables if not present
default_env = {
    'DATABASE_URL': 'postgresql://postgres:postgres@localhost:5432/social_suit',
    'REDIS_URL': 'redis://localhost:6379/0',
    'SECRET_KEY': 'dummy_secret_key_for_development',
    'ALGORITHM': 'HS256',
    'ACCESS_TOKEN_EXPIRE_MINUTES': '30',
    'CLOUDINARY_URL': 'cloudinary://dummy_api_key:dummy_api_secret@dummy_cloud_name',
    'ENVIRONMENT': 'development',
    'DEBUG': 'True',
    'TESTING': 'False',
    'RATE_LIMIT_DEFAULT': '100/minute',
    'RATE_LIMIT_BURST': '200/minute',
}

# Set default environment variables if not present
for key, value in default_env.items():
    if not os.environ.get(key):
        os.environ[key] = value
        logger.info(f"Setting default environment variable: {key}")

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        "message": "Welcome to Social Suit API",
        "version": "1.0.0",
        "environment": os.environ.get('ENVIRONMENT', 'development')
    })

@app.route('/health')
def health_check():
    # Check if essential services are available
    services_status = {
        "api": "ok",
        "database": "simulated",  # In a real app, we would check the database connection
        "redis": "simulated",     # In a real app, we would check the Redis connection
    }
    
    return jsonify({
        "status": "ok",
        "services": services_status,
        "environment": os.environ.get('ENVIRONMENT', 'development')
    })

@app.route('/api/v1/config')
def get_config():
    # Return non-sensitive configuration
    return jsonify({
        "environment": os.environ.get('ENVIRONMENT', 'development'),
        "debug": os.environ.get('DEBUG', 'True') == 'True',
        "testing": os.environ.get('TESTING', 'False') == 'True',
        "rate_limit_default": os.environ.get('RATE_LIMIT_DEFAULT', '100/minute'),
        "rate_limit_burst": os.environ.get('RATE_LIMIT_BURST', '200/minute'),
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    debug = os.environ.get('DEBUG', 'True') == 'True'
    
    logger.info(f"Starting application on port {port} with debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)