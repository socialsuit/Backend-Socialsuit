import os
import time
import requests
import base64
import tempfile
from typing import Dict, Optional
from urllib.parse import quote
from services.cloudinary_helper import cloudinary_helper


class SDXLThumbnailGenerator:
    def __init__(self):
        self.SDXL_API_KEY = os.getenv("SDXL_API_KEY")
        self.SDXL_ENDPOINT = "https://api.stability.ai/v1/generation/sdxl-512x512/text-to-image"
        self.CACHE = {}

    def _get_platform_size(self, platform: str):
        sizes = {
            "universal": (1024, 1024),
            "instagram_post": (1080, 1350),
            "instagram_story": (1080, 1920),
            "twitter": (1200, 675),
            "linkedin": (1200, 627),
            "pinterest": (1000, 1500),
            "facebook": (1200, 630),
            "youtube_thumbnail": (1280, 720)
        }
        return sizes.get(platform, sizes["universal"])

    def generate_thumbnail(
        self,
        prompt: str,
        platform: str = "universal",
        logo_base64: Optional[str] = None,
        cache_timeout: int = 3600
    ) -> Dict[str, Optional[str]]:
        """
        Generates image based on prompt and optional logo.
        Returns base64 image for direct frontend use.
        """
        cache_key = f"{platform}_{quote(prompt)}_{hash(logo_base64)}"
        now = time.time()

        # Return cached image if available
        if cache_key in self.CACHE:
            timestamp, cached_result = self.CACHE[cache_key]
            if now - timestamp < cache_timeout:
                return cached_result

        width, height = self._get_platform_size(platform)

        headers = {
            "Authorization": f"Bearer {self.SDXL_API_KEY}",
            "Content-Type": "application/json"
        }

        body = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30
        }

        # Include logo as init_image if needed (future extension)
        if logo_base64:
            body["init_image"] = logo_base64
            body["image_strength"] = 0.35  # how much to preserve from logo (0.0 = use logo fully, 1.0 = ignore)

        try:
            response = requests.post(self.SDXL_ENDPOINT, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

            image_base64 = data["artifacts"][0]["base64"]
            
            # Upload to Cloudinary for optimized delivery
            try:
                # Create temporary file from base64 data
                image_data = base64.b64decode(image_base64)
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(image_data)
                    temp_file.flush()
                    
                    # Upload to Cloudinary with optimizations
                    cloudinary_result = cloudinary_helper.upload_image(
                        file_path_or_url=temp_file.name,
                        folder="social_suit/thumbnails",
                        tags=["thumbnail", platform, "ai_generated"],
                        context={
                            "prompt": prompt,
                            "platform": platform,
                            "generator": "sdxl"
                        }
                    )
                    
                    # Clean up temporary file
                    os.unlink(temp_file.name)
                    
                    result = {
                        "image_base64": image_base64,  # Keep for backward compatibility
                        "cloudinary_url": cloudinary_result["secure_url"],
                        "optimized_urls": cloudinary_result["optimized_urls"],
                        "public_id": cloudinary_result["public_id"],
                        "platform": platform,
                        "prompt": prompt
                    }
                    
            except Exception as cloudinary_error:
                # Fallback to base64 if Cloudinary upload fails
                result = {
                    "image_base64": image_base64,
                    "platform": platform,
                    "prompt": prompt,
                    "cloudinary_error": str(cloudinary_error)
                }

            self.CACHE[cache_key] = (now, result)
            return result

        except requests.exceptions.RequestException as e:
            return {"error": str(e), "platform": platform}
        except Exception as e:
            return {"error": f"Unexpected Error: {str(e)}", "platform": platform}
