from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # PostgreSQL
    DATABASE_URL: str

    # MongoDB
    MONGO_URI: str

    # Redis
    REDIS_URL: str

    # Cloudinary
    CLOUDINARY_URL: str

    # JWT Secret
    JWT_SECRET: str
    
    # Unified AI API configuration for DeepSeek via OpenRouter
    DEEPSEEK_OPENROUTER_API_KEY: str
    DEEPSEEK_OPENROUTER_MODEL: str = "deepseek/deepseek-r1-distill-llama-70b"

    # Optional: Environment Mode
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"
        extra = "allow"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()