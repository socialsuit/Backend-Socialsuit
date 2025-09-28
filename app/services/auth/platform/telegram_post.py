import requests

def call_telegram_api(user_token: dict, post_payload: dict):
    bot_token = user_token.get("access_token")
    channel_id = user_token.get("channel_id")
    message = post_payload.get("message")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": channel_id,
        "text": message
    }

    res = requests.post(url, data=payload)
    return res.json()