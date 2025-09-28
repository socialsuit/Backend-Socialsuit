from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional
import re
from datetime import datetime
from enum import Enum

class WalletNetwork(str, Enum):
    ETHEREUM = "ethereum"
    POLYGON = "polygon"
    SOLANA = "solana"

class WalletNonceRequest(BaseModel):
    """
    Request to generate a nonce for wallet signature challenge.
    """
    address: str = Field(
        ...,
        example="0x71C7656EC7ab88b098defB751B7401B5f6d8976F",
        description="EVM-compatible wallet address (0x...)",
        min_length=42,
        max_length=44
    )
    network: WalletNetwork = Field(
        default=WalletNetwork.ETHEREUM,
        description="Blockchain network of the wallet"
    )

    @validator("address")
    def validate_evm_address(cls, v):
        if not re.match(r"^0x[a-fA-F0-9]{40}$", v):
            raise ValueError("Invalid EVM address format")
        return v.lower()  # Standardize to lowercase

class WalletSignatureVerifyRequest(BaseModel):
    """
    Request to verify a signed message for wallet authentication.
    """
    address: str = Field(..., description="Wallet address that signed the message")
    signature: str = Field(
        ...,
        example="0x1234abc...",
        description="ECDSA signature of the nonce",
        min_length=132,
        max_length=132
    )
    nonce: str = Field(
        ...,
        description="Server-generated nonce that was signed",
        min_length=16,
        max_length=64
    )
    network: WalletNetwork

    @validator("signature")
    def validate_signature_format(cls, v):
        if not re.match(r"^0x[a-fA-F0-9]{130}$", v):
            raise ValueError("Invalid signature format")
        return v

class WalletAuthResponse(BaseModel):
    """
    Successful authentication response with tokens.
    """
    access_token: str = Field(
        ...,
        example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        description="JWT access token"
    )
    refresh_token: Optional[str] = Field(
        None,
        description="Refresh token for obtaining new access tokens"
    )
    token_type: str = Field(
        default="bearer",
        example="bearer",
        description="Type of token returned"
    )
    expires_in: int = Field(
        default=3600,
        example=3600,
        description="Access token lifetime in seconds"
    )
    wallet_address: str = Field(
        ...,
        description="Authenticated wallet address"
    )

class WalletUserProfile(BaseModel):
    """
    Wallet-linked user profile data.
    """
    wallet_address: str
    first_auth_date: datetime
    last_login: datetime
    network: WalletNetwork
    is_verified: bool = False