"""
Authentication utilities and dependencies for the Stream Sniper API.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...database.gateways.identity.records import UserRow
from ...database.gateways.identity.user_table_gateway import select_user_by_id_db, select_user_by_username_db
from ...identity import ADMIN_ROLE
from ...logging_config import get_logger
from ..config import AuthConfig
from .auth_models import TokenData, UserInDB

logger = get_logger(__name__)


def validate_auth_config(config: AuthConfig) -> None:
    """Reject an unusable JWT configuration at the composition boundary."""
    if not config.secret_key:
        raise RuntimeError(
            "JWT signing secret is not configured. Set JWT_SECRET_KEY (or SECRET_KEY) in the environment."
        )


# Security scheme
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom authentication error"""

    def __init__(self, detail: str = "Your session is invalid or has expired. Please log in again."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def _user_row_to_auth_user(user_row: UserRow) -> UserInDB:
    """Translate a credential-bearing persistence row at the auth boundary."""
    return UserInDB(
        id=user_row.id,
        username=user_row.username,
        email=user_row.email,
        password_hash=user_row.password_hash,
        role=user_row.role,
        is_active=user_row.is_active,
        created_at=user_row.created_at.isoformat(),
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    data: dict[str, Any],
    config: AuthConfig,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=config.access_token_expire_minutes)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.secret_key, algorithm=config.algorithm)
    return encoded_jwt


def verify_token(token: str, config: AuthConfig) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, config.secret_key, algorithms=[config.algorithm])
        username = payload.get("sub")
        if not isinstance(username, str) or not username:
            raise AuthenticationError()
        return TokenData(username=username)
    except jwt.PyJWTError:
        raise AuthenticationError()


def get_user_by_username(username: str) -> UserInDB | None:
    user_row = select_user_by_username_db(username)
    return _user_row_to_auth_user(user_row) if user_row else None


def get_user_by_id(user_id: int) -> UserInDB | None:
    user_row = select_user_by_id_db(user_id)
    return _user_row_to_auth_user(user_row) if user_row else None


def authenticate_user(username: str, password: str) -> UserInDB | None:
    """Authenticate user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserInDB:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    token_data = verify_token(token, request.app.state.config.auth)
    if token_data.username is None:
        raise AuthenticationError()
    user = get_user_by_username(token_data.username)
    if user is None:
        raise AuthenticationError()
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated. Contact an administrator to restore access.")
    return user


def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get current user and verify they have admin role"""
    if current_user.role != ADMIN_ROLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You need administrator access to do this."
        )
    return current_user
