# services/auth/telegram_auth.py

import requests
from fastapi import Request
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/getMe"
TELEGRAM_CHAT_URL = "https://api.telegram.org/bot{token}/getChat?chat_id={chat_id}"


def get_telegram_connect_instructions() -> str:
    """
    Step-by-step for user to connect their Telegram Channel.
    """
    return (
        "1️⃣ Create a bot via BotFather.\n"
        "2️⃣ Copy the Bot Token.\n"
        "3️⃣ Add the bot as admin to your Channel.\n"
        "4️⃣ Copy your Channel ID or @username.\n"
        "5️⃣ Submit bot_token + channel_id to SocialSuit."
    )


def handle_telegram_callback(request: Request) -> dict:
    """
    Receives: bot_token & channel_id
    1️⃣ Verifies bot is valid.
    2️⃣ Verifies bot has access to the channel.
    3️⃣ Stores credentials.
    """
    bot_token = request.query_params.get("bot_token")
    channel_id = request.query_params.get("channel_id")

    if not bot_token or not channel_id:
        return {"error": "Bot token or channel ID missing."}

    # ✅ Verify bot token
    verify_bot = requests.get(TELEGRAM_API_URL.format(token=bot_token)).json()
    if not verify_bot.get("ok"):
        return {"error": "Invalid Bot Token."}

    # ✅ Verify bot can access the channel
    verify_chat = requests.get(
        TELEGRAM_CHAT_URL.format(token=bot_token, chat_id=channel_id)
    ).json()

    if not verify_chat.get("ok"):
        return {"error": "Invalid Channel ID or bot has no access. Add bot as admin!"}

    # ✅ Save to DB
    db = next(get_db())
    new_token = PlatformToken(
        user_id="PLACEHOLDER",
        platform="telegram",
        access_token=bot_token,
        channel_id=channel_id
    )
    db.add(new_token)
    db.commit()

    return {
        "msg": "✅ Telegram Bot connected successfully!",
        "bot_name": verify_bot["result"]["username"],
        "channel_id": channel_id
    }