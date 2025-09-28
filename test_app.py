from fastapi import FastAPI
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="Social Suit API - Test",
    description="Test application for Social Suit API",
    version="1.0.0"
)

# Root endpoint
@app.get("/")
def home():
    return {"msg": "🚀 Social Suit Backend Running"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "ok"}