import os
import re
from typing import Dict, Union
from datetime import datetime
from app.services.ai_client import ai_client as AIClient  # Import the unified AIClient

class AIContentService:
    def __init__(self):
        self.ai_client = AIClient

    @staticmethod
    def clean_caption(text: str) -> str:
        """Clean and format social media captions"""
        text = re.sub(r'\n+', ' ', text).strip()  # Remove extra new lines
        hashtags = re.findall(r"#\w+", text)      # Extract hashtags
        text = re.sub(r"#\w+", '', text).strip()  # Remove hashtags from main text
        text += " " + " ".join(hashtags[:5])      # Append only first 5 hashtags
        return text

    def generate_content(self, prompt: str) -> Dict[str, Union[str, Dict]]:
        """Generate general content using the unified AI client"""
        return self.ai_client.generate_content(prompt)

    def generate_caption(self, topic: str) -> str:
        """Generate social media caption with proper formatting using the unified AI client"""
        prompt = f"Generate an engaging social media post about {topic} with 4-5 relevant hashtags."
        
        result = self.ai_client.generate_caption(topic)
        
        if result and not result.startswith("❌"):
            cleaned = self.clean_caption(result)
            self.save_to_history(topic, cleaned)
            return cleaned
        return result

    def save_to_history(self, topic: str, caption: str):
        """Save generated caption to history log file"""
        try:
            with open("caption_history.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now().isoformat()} | {topic} | {caption}\n")
        except Exception as e:
            print(f"Error saving to history: {e}")

# Example usage
if __name__ == "__main__":
    ai_service = AIContentService()
    
    # Test general content generation
    content_result = ai_service.generate_content("Explain blockchain in simple words")
    print("Generated Content:", content_result.get("generated", "Error"))

    # Test social media caption generation (also logs the result)
    caption = ai_service.generate_caption("Crypto trading strategies")
    print("Generated Caption:", caption)

