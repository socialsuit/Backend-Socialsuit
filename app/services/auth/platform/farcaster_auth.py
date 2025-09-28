# services/auth/farcaster_auth.py

from fastapi import Request
from app.services.database.database import get_db
from app.services.models.token_model import PlatformToken
import time
import hashlib

# 👇 This can be used to generate and validate nonces.
NONCE_VALIDITY_SECONDS = 300  # 5 minutes

def get_farcaster_login_url() -> str:
    """
    Farcaster uses wallet connect. 
    Show modal on frontend, sign a message:
    "Sign this message to authenticate. Nonce: {nonce}"
    """
    return "Handled on frontend. Use WalletConnect modal."


def handle_farcaster_callback(request: Request) -> dict:
    """
    Farcaster callback. Frontend sends:
      - signature: signed message
      - address: wallet address
      - nonce: nonce used
    """
    signature = request.query_params.get("signature")
    user_address = request.query_params.get("address")
    nonce = request.query_params.get("nonce")

    if not signature or not user_address or not nonce:
        return {"error": "Missing signature, address, or nonce"}

    # ⚡️ Example: Basic nonce check (in production use DB to prevent reuse!)
    nonce_parts = nonce.split(":")
    if len(nonce_parts) != 2:
        return {"error": "Invalid nonce format"}

    issued_at = int(nonce_parts[1])
    if time.time() - issued_at > NONCE_VALIDITY_SECONDS:
        return {"error": "Nonce expired"}

    # ✔️ Ideally: verify signature properly using a library like eth_account
    # Here we store it directly for demo
    db = next(get_db())
    new_token = PlatformToken(
        user_id="PLACEHOLDER",
        platform="farcaster",
        access_token=signature,  # Store signature for session validation
    )
    db.add(new_token)
    db.commit()

    return {
        "msg": "Farcaster connected!",
        "address": user_address,
        "signature": signature,
    }
