import requests
from app.services.utils.logger_config import logger  # ✅ Reuse main logger

def call_farcaster_post(user_token: dict, post_payload: dict) -> dict:
    """
    Post a cast to Farcaster using Neynar API or your own signer infra.
    """
    address = user_token.get("wallet_address")
    signer_token = user_token.get("signer_token")
    signer_uuid = user_token.get("signer_uuid")

    if not signer_token or not signer_uuid:
        logger.error(f"[Farcaster] Missing signer credentials for address: {address}")
        return {"error": "Missing signer_token or signer_uuid"}

    text = post_payload.get("text", "")
    media_url = post_payload.get("media_url")
    channel_id = post_payload.get("channel_id")

    # If media URL is present, append to text body
    body = text.strip()
    if media_url:
        body += f"\n{media_url}"

    payload = {
        "signer_uuid": signer_uuid,
        "text": body
    }
    if channel_id:
        payload["channel_id"] = channel_id

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {signer_token}"
    }

    farcaster_api = "https://api.neynar.com/v2/farcaster/cast"

    logger.info(
        f"[Farcaster] Sending cast | Address: {address} | Channel: {channel_id or 'N/A'} | Text length: {len(body)}"
    )

    try:
        response = requests.post(
            farcaster_api,
            json=payload,
            headers=headers,
            timeout=15  # ⏱️ Good practice: prevent hanging requests
        )

        response.raise_for_status()  # Raises HTTPError for bad codes

        data = response.json()
        logger.info(f"[Farcaster] Cast posted successfully: {data}")
        return data

    except requests.HTTPError as http_err:
        logger.error(
            f"[Farcaster] HTTP error: {response.status_code} | {response.text}"
        )
        return {"error": f"HTTP error: {str(http_err)}"}

    except Exception as e:
        logger.exception(f"[Farcaster] Cast failed: {str(e)}")
        return {"error": str(e)}