import requests

def call_youtube_post(user_token: dict, post_payload: dict):
    access_token = user_token.get("access_token")

    video_file_path = post_payload.get("video_file_path")
    title = post_payload.get("title")
    description = post_payload.get("description")

    # NOTE: Google APIs often need resumable upload or client libraries.
    # This is a simple example (should use Google API Client for real).

    upload_url = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    body = {
        "snippet": {
            "title": title,
            "description": description
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    # 1) Start resumable upload
    init_res = requests.post(upload_url, headers=headers, json=body)
    upload_location = init_res.headers.get("Location")

    if not upload_location:
        return {"error": "Failed to get upload URL"}

    # 2) Upload video binary
    with open(video_file_path, "rb") as video_file:
        upload_res = requests.put(upload_location, data=video_file.read())
        return upload_res.json()