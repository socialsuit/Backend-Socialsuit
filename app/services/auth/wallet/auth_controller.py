from datetime import datetime, timedelta
from jose import jwt
import secrets

from app.services.models.user_model import User as WalletUserModel
from app.services.auth.wallet.auth_schema import (
    WalletNonceRequest,
    WalletSignatureVerifyRequest,
    WalletAuthResponse,
    WalletNetwork,
)
from app.services.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
)
from app.services.database.database import get_db # Your DB session

# In-memory nonce store (should use Redis or DB in production)
NONCE_STORE = {}

# Generate a nonce for wallet login
async def generate_wallet_nonce(payload: WalletNonceRequest):
    nonce = secrets.token_hex(16)
    key = f"{payload.network}:{payload.address}"
    NONCE_STORE[key] = nonce
    return {"nonce": nonce}


# Verify the signature and issue tokens
async def verify_wallet_signature_controller(payload: WalletSignatureVerifyRequest):
    # ⛔ FIX: Lazy import to avoid circular import
    from app.services.auth.wallet.auth_controller import verify_wallet_signature

    key = f"{payload.network}:{payload.address}"
    expected_nonce = NONCE_STORE.get(key)

    if not expected_nonce or payload.nonce != expected_nonce:
        raise ValueError("Invalid or expired nonce")

    # Signature Verification
    is_valid = await verify_wallet_signature(
        address=payload.address,
        signature=payload.signature,
        message=expected_nonce,
        network=payload.network
    )
    if not is_valid:
        raise ValueError("Signature verification failed")

    # Save or update user in DB
    user = await get_db.get_wallet_user(payload.address, payload.network)
    now = datetime.utcnow()
    if not user:
        user = WalletUserModel(
            wallet_address=payload.address,
            network=payload.network,
            first_auth_date=now,
            last_login=now,
            is_verified=True
        )
        await get_db.save_wallet_user(user)
    else:
        user.last_login = now
        await get_db.update_wallet_user(user)

    # Token generation
    access_token = create_access_token(
        user_id=str(user.id),
        wallet_address=payload.address
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    return WalletAuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=3600,
        wallet_address=payload.address
    )
