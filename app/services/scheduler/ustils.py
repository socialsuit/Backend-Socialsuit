import requests

class RateLimitError(Exception):
    pass

def call_meta_api(access_token: str, post_payload: dict) -> dict:
    url = "https://graph.facebook.com/v19.0/me/feed"
    headers = {"Authorization": f"Bearer {access_token}"}

    payload = {
        "message": post_payload.get("caption", "Default Post"),
        "link": post_payload.get("link"),
        "access_token": access_token
    }

    response = requests.post(url, data=payload)
    data = response.json()

    if "error" in data and data["error"]["code"] == 4:
        raise RateLimitError(data["error"]["message"])

    return data