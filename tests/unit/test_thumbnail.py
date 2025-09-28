from app.services.thumbnail import ThumbnailGenerator

thumb = ThumbnailGenerator()
result = thumb.fetch_thumbnail("nature", platform="instagram_post")

print("Thumbnail Result:")
print(result)
