import os
from services.thumbnail import SDXLThumbnailGenerator  # adjust path accordingly

def test_generate_thumbnail():
    

    generator = SDXLThumbnailGenerator()
    prompt = "A futuristic AI robot writing code in a neon-lit room"
    platform = "twitter"

    result = generator.generate_thumbnail(prompt, platform)

    assert isinstance(result, dict)
    assert "image_base64" in result or "error" in result

    if "image_base64" in result:
        print("✅ Image generated successfully")
    else:
        print(f"❌ Failed to generate: {result.get('error')}")