import warnings
from datetime import timedelta
from typing import Optional, Dict, Any

# Import from shared package
from shared.auth.jwt import create_access_token as shared_create_access_token
from shared.auth.jwt import decode_token, get_token_payload
from shared.auth.password import hash_password as shared_hash_password, verify_password as shared_verify_password


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None, 
                       secret_key: str = None, algorithm: str = None) -> str:
    ""Create a new JWT token""
    warnings.warn(
        "This function is deprecated. Use shared.auth.jwt.create_access_token instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return shared_create_access_token(data=data, secret_key=secret_key, algorithm=algorithm, expires_delta=expires_delta)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    ""Verify a password against a hash""
    warnings.warn(
        "This function is deprecated. Use shared.auth.password.verify_password instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return shared_verify_password(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    ""Generate password hash""
    warnings.warn(
        "This function is deprecated. Use shared.auth.password.hash_password instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return shared_hash_password(password)

