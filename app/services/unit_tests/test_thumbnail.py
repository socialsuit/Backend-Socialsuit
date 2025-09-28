import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.thumbnail import ThumbnailGenerator

thumb = ThumbnailGenerator()
result = thumb.fetch_thumbnail("nature", platform="instagram_post")

print("Thumbnail Result:")
print(result)
