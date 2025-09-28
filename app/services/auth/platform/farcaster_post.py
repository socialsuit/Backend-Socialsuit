import requests

def call_farcaster_post(user_token: dict, post_payload: dict):
    # Farcaster often uses signed messages or 3rd party relayers
    api_url = "https://api.farcaster.xyz/v1/cast"

    signature = user_token.get("access_token")
    message = post_payload.get("message")

    payload = {
        "signature": signature,
        "content": message
    }

    res = requests.post(api_url, json=payload)
    return res.json()