import requests

def call_tiktok_post(user_token: dict, post_payload: dict):
    access_token = user_token.get("access_token")
    video_file_path = post_payload.get("video_file_path")
    caption = post_payload.get("caption")

    # TikTok API typically needs an upload URL obtained first
    upload_url = "https://open-api.tiktok.com/share/video/upload/"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    files = {
        "video": open(video_file_path, "rb")
    }

    payload = {
        "caption": caption
    }

    res = requests.post(upload_url, headers=headers, files=files, data=payload)
    return res.json()