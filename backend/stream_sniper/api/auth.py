"""
Authentication utilities and dependencies for the Stream Sniper API.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ..database.user_table_gateway import select_user_by_id_db, select_user_by_username_db
from ..logging_config import get_logger

load_dotenv()

logger = get_logger(__name__)

# JWT Configuration
# Read the signing secret from JWT_SECRET_KEY, falling back to SECRET_KEY
# (production compose/deploy sets SECRET_KEY). Fail fast if neither is set.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY")
if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT signing secret is not configured. Set JWT_SECRET_KEY (or SECRET_KEY) in the environment."
    )
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Security scheme
security = HTTPBearer()


class Token(BaseModel):
    """JWT Token response model"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(..., description="Token type (bearer)")


class TokenData(BaseModel):
    """Token data extracted from JWT"""
    username: Optional[str] = None


class User(BaseModel):
    """User model for responses"""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role (user/admin)")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: str = Field(..., description="User creation timestamp")


class UserInDB(User):
    """User model with password hash for database operations"""
    password_hash: str


class UserCreate(BaseModel):
    """User creation model"""
    username: str = Field(..., description="Username (3-50 characters)", min_length=3, max_length=50)
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., description="Password (8-128 characters)", min_length=8, max_length=128)


class UserLogin(BaseModel):
    """User login model"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise AuthenticationError()
        return TokenData(username=username)
    except jwt.PyJWTError:
        raise AuthenticationError()


def get_user_by_username(username: str) -> Optional[UserInDB]:
    """Get user by username from database"""
    try:
        user_data = select_user_by_username_db(username)
        if user_data:
            return UserInDB(
                id=user_data[0],
                username=user_data[1],
                email=user_data[2],
                password_hash=user_data[3],
                role=user_data[4],
                is_active=user_data[5],
                created_at=user_data[6].isoformat() if user_data[6] else None
            )
        return None
    except Exception as e:
        logger.error(f"Error fetching user by username: {e}")
        return None


def get_user_by_id(user_id: int) -> Optional[UserInDB]:
    """Get user by ID from database"""
    try:
        user_data = select_user_by_id_db(user_id)
        if user_data:
            return UserInDB(
                id=user_data[0],
                username=user_data[1],
                email=user_data[2],
                password_hash=user_data[3],
                role=user_data[4],
                is_active=user_data[5],
                created_at=user_data[6].isoformat() if user_data[6] else None
            )
        return None
    except Exception as e:
        logger.error(f"Error fetching user by ID: {e}")
        return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    token_data = verify_token(token)
    user = get_user_by_username(token_data.username)
    if user is None:
        raise AuthenticationError()
    if not user.is_active:
        raise AuthenticationError("User account is disabled")
    return user


async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get current active user (alias for get_current_user)"""
    return current_user


async def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get current user and verify they have admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user


def is_admin(user: UserInDB) -> bool:
    """Check if user has admin role"""
    return user.role == "admin"


def is_active(user: UserInDB) -> bool:
    """Check if user is active"""
    return user.is_active