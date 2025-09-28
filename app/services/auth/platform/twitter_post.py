import requests

def call_twitter_post(user_token: dict, post_payload: dict):
    access_token = user_token.get("access_token")
    message = post_payload.get("message")

    url = "https://api.twitter.com/2/tweets"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "text": message
    }

    res = requests.post(url, headers=headers, json=payload)
    return res.json()