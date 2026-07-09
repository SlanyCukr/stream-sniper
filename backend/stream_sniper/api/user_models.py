"""
Request/response contracts shared by the authentication and user
administration routers.
"""

import re
from typing import List, Optional

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator

from .auth import UserCreate


class UserResponse(BaseModel):
    """User response model (no password hash)"""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role (user/admin)")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: str = Field(..., description="User creation timestamp")


class UserCreateExtended(UserCreate):
    """Extended user creation with validation"""

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        try:
            validate_email(v)
            return v
        except EmailNotValidError:
            raise ValueError('Invalid email format')

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be less than 128 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[str] = Field(None, description="New email address")
    role: Optional[str] = Field(None, description="New role (admin only)")
    is_active: Optional[bool] = Field(None, description="Active status (admin only)")


class PasswordChange(BaseModel):
    """Password change model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password", min_length=8, max_length=128)

    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class UsersResponse(BaseModel):
    """Paginated users response"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")


class SystemStats(BaseModel):
    """System statistics model"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    admin_users: int = Field(..., description="Number of admin users")
    recent_registrations: int = Field(..., description="Registrations in last 24 hours")


class UserCreateAdmin(BaseModel):
    """Admin user creation model"""
    username: str = Field(..., description="Username (3-50 characters)", min_length=3, max_length=50)
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., description="Password (8-128 characters)", min_length=8, max_length=128)
    role: str = Field(default="user", description="User role (user/admin)")
    is_active: bool = Field(default=True, description="Whether user is active")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v

    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        try:
            validate_email(v)
            return v
        except EmailNotValidError:
            raise ValueError('Invalid email format')

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be less than 128 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ["user", "admin"]:
            raise ValueError('Role must be either "user" or "admin"')
        return v


def convert_user_to_response(user_tuple) -> UserResponse:
    """Convert either public or credential-bearing database rows to a response.

    List queries omit ``password_hash`` while lookups by user ID include it for
    authentication helpers. API responses must never expose that column, and
    must read the remaining fields at their respective positions.
    """
    if len(user_tuple) == 7:
        (
            user_id,
            username,
            email,
            _password_hash,
            role,
            is_active,
            created_at,
        ) = user_tuple
    else:
        user_id, username, email, role, is_active, created_at = user_tuple

    return UserResponse(
        id=user_id,
        username=username,
        email=email,
        role=role,
        is_active=is_active,
        created_at=created_at.isoformat() if created_at else None,
    )
