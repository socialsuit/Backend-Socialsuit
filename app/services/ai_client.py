"""
Unified AI Client for Social Suit Backend

This module provides a single interface for all AI operations using DeepSeek via OpenRouter.
It consolidates all AI API calls and provides consistent error handling and logging.
"""

import os
import re
import requests
from dotenv import load_dotenv
from typing import Dict, Union, Optional
from datetime import datetime
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class AIClient:
    """
    Unified AI client for handling all AI requests through DeepSeek via OpenRouter.
    
    This class provides a single interface for:
    - Content generation
    - Caption generation
    - Social media post creation
    - General AI assistance
    """
    
    def __init__(self):
        """Initialize the AI client with unified configuration."""
        self.api_key = os.getenv("DEEPSEEK_OPENROUTER_API_KEY")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "deepseek/deepseek-chat:free"  # Default model
        
        if not self.api_key:
            logger.warning("DEEPSEEK_OPENROUTER_API_KEY not found in environment variables")
            
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://social-suit.com",  # Optional: for OpenRouter analytics
            "X-Title": "Social Suit Backend"  # Optional: for OpenRouter analytics
        }
    
    @staticmethod
    def clean_caption(text: str) -> str:
        """
        Clean and format social media captions.
        
        Args:
            text (str): Raw caption text
            
        Returns:
            str: Cleaned and formatted caption
        """
        # Remove extra newlines and normalize whitespace
        text = re.sub(r'\n+', ' ', text).strip()
        
        # Extract hashtags
        hashtags = re.findall(r"#\w+", text)
        
        # Remove hashtags from main text
        text = re.sub(r"#\w+", '', text).strip()
        
        # Append only first 5 hashtags to avoid clutter
        if hashtags:
            text += " " + " ".join(hashtags[:5])
            
        return text.strip()
    
    def _make_request(self, messages: list, temperature: float = 0.7, model: Optional[str] = None) -> Dict[str, Union[str, Dict]]:
        """
        Make a request to the AI API.
        
        Args:
            messages (list): List of message objects for the conversation
            temperature (float): Creativity level (0.0 to 1.0)
            model (str, optional): Model to use, defaults to self.model
            
        Returns:
            dict: Response containing generated content or error
        """
        if not self.api_key:
            return {"error": "AI API key not configured"}
            
        data = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000  # Reasonable limit for most use cases
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=30  # 30 second timeout
            )
            
            response.raise_for_status()  # Raise exception for HTTP errors
            result = response.json()
            
            if "choices" in result and result["choices"]:
                return {
                    "generated": result["choices"][0]["message"]["content"],
                    "raw_response": result,
                    "success": True
                }
            else:
                return {"error": "No valid response from AI API", "success": False}
                
        except requests.exceptions.Timeout:
            logger.error("AI API request timed out")
            return {"error": "AI API request timed out", "success": False}
        except requests.exceptions.RequestException as e:
            logger.error(f"AI API request failed: {str(e)}")
            return {"error": f"AI API request failed: {str(e)}", "success": False}
        except Exception as e:
            logger.error(f"Unexpected error in AI request: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}", "success": False}
    
    def generate_content(self, prompt: str, system_message: str = "You are a helpful AI assistant.", temperature: float = 0.7) -> Dict[str, Union[str, Dict]]:
        """
        Generate general content using the AI API.
        
        Args:
            prompt (str): The user prompt
            system_message (str): System message to set AI behavior
            temperature (float): Creativity level
            
        Returns:
            dict: Generated content or error message
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]
        
        return self._make_request(messages, temperature)
    
    def generate_caption(self, topic: str, style: str = "engaging", hashtag_count: int = 5) -> str:
        """
        Generate a social media caption with proper formatting.
        
        Args:
            topic (str): The topic for the caption
            style (str): Style of the caption (engaging, professional, casual, etc.)
            hashtag_count (int): Number of hashtags to include
            
        Returns:
            str: Generated and cleaned caption
        """
        prompt = f"""Generate a {style} social media post about {topic}. 
        Include {hashtag_count} relevant hashtags. 
        Keep it concise and engaging for social media platforms."""
        
        messages = [
            {"role": "system", "content": "You are a social media content expert. Create engaging, platform-appropriate posts."},
            {"role": "user", "content": prompt}
        ]
        
        result = self._make_request(messages, temperature=0.8)
        
        if result.get("success"):
            raw_caption = result["generated"].strip()
            cleaned_caption = self.clean_caption(raw_caption)
            self._save_to_history(topic, cleaned_caption)
            return cleaned_caption
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Caption generation failed: {error_msg}")
            return f"❌ Error generating caption: {error_msg}"
    
    def generate_post_ideas(self, topic: str, count: int = 3) -> list:
        """
        Generate multiple post ideas for a given topic.
        
        Args:
            topic (str): The topic for post ideas
            count (int): Number of ideas to generate
            
        Returns:
            list: List of post ideas
        """
        prompt = f"""Generate {count} different social media post ideas about {topic}. 
        Each idea should be unique and engaging. 
        Format as a numbered list."""
        
        result = self.generate_content(prompt, "You are a creative social media strategist.")
        
        if result.get("success"):
            ideas_text = result["generated"]
            # Split by lines and filter out empty lines
            ideas = [line.strip() for line in ideas_text.split('\n') if line.strip()]
            return ideas[:count]  # Ensure we don't return more than requested
        else:
            return [f"❌ Error generating ideas: {result.get('error', 'Unknown error')}"]
    
    def _save_to_history(self, topic: str, content: str):
        """
        Save generated content to history log file.
        
        Args:
            topic (str): The topic that was used
            content (str): The generated content
        """
        try:
            with open("ai_content_history.log", "a", encoding="utf-8") as f:
                timestamp = datetime.now().isoformat()
                f.write(f"{timestamp} | {topic} | {content}\n")
        except Exception as e:
            logger.error(f"Failed to save content to history: {str(e)}")
    
    def health_check(self) -> Dict[str, Union[str, bool]]:
        """
        Check if the AI service is available and configured properly.
        
        Returns:
            dict: Health status information
        """
        if not self.api_key:
            return {
                "status": "error",
                "message": "API key not configured",
                "configured": False
            }
        
        # Simple test request
        test_result = self.generate_content("Hello", temperature=0.1)
        
        if test_result.get("success"):
            return {
                "status": "healthy",
                "message": "AI service is operational",
                "configured": True
            }
        else:
            return {
                "status": "error", 
                "message": f"AI service unavailable: {test_result.get('error')}",
                "configured": True
            }


# Global instance for easy importing
ai_client = AIClient()

# Backward compatibility aliases
OpenRouterAI = AIClient  # For existing code that imports OpenRouterAI

# Example usage
if __name__ == "__main__":
    # Test the unified AI client
    client = AIClient()
    
    # Health check
    health = client.health_check()
    print("Health Check:", health)
    
    if health["status"] == "healthy":
        # Test content generation
        content_result = client.generate_content("Explain blockchain in simple words")
        print("Generated Content:", content_result.get("generated", "Error"))
        
        # Test caption generation
        caption = client.generate_caption("sustainable technology")
        print("Generated Caption:", caption)
        
        # Test post ideas
        ideas = client.generate_post_ideas("artificial intelligence", 3)
        print("Post Ideas:", ideas)