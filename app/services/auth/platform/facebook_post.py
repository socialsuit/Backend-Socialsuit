import requests

def call_facebook_post(user_token: dict, post_payload: dict):
    page_id = user_token.get("page_id")
    access_token = user_token.get("access_token")

    message = post_payload.get("message")
    image_url = post_payload.get("image_url")

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"

    payload = {
        "url": image_url,
        "caption": message,
        "access_token": access_token
    }

    res = requests.post(url, data=payload)
    return res.json()