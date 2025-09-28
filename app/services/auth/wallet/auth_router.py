from fastapi import APIRouter, HTTPException, status, Depends
from app.services.auth.wallet.auth_schema import (
    WalletNonceRequest,
    WalletSignatureVerifyRequest,
    WalletAuthResponse
)
from app.services.auth.wallet.auth_controller import (
    generate_wallet_nonce,
    verify_wallet_signature_controller
)
from app.services.auth.email.auth_schema import RefreshTokenRequest, AuthResponse
from app.services.auth.email.auth_controller import refresh_access_token

router = APIRouter(prefix="/wallet-auth", tags=["Wallet Auth"])

@router.post("/nonce", summary="Generate a nonce for wallet signature")
async def get_nonce(payload: WalletNonceRequest):
    """Generate a nonce that the wallet must sign to authenticate."""
    try:
        return await generate_wallet_nonce(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify", response_model=WalletAuthResponse, summary="Verify wallet signature")
async def verify_signature(payload: WalletSignatureVerifyRequest):
    """Verify a wallet signature and issue authentication tokens."""
    try:
        return await verify_wallet_signature_controller(payload)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=AuthResponse, summary="Refresh access token")
async def refresh(request: RefreshTokenRequest):
    """Get a new access token using a refresh token."""
    try:
        return await refresh_access_token(request)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )
