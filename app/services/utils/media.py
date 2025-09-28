import requests

def download_cloudinary_media(media_url: str) -> bytes:
    """
    Downloads file from Cloudinary public URL.
    Returns raw bytes.
    """
    response = requests.get(media_url)
    response.raise_for_status()
    return response.content