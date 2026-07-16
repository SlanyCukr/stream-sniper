"""
Request/response contracts shared by the authentication and user
administration routers.
"""

import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from stream_sniper.database.gateways.identity.records import (
    PublicUserRow,
    UserRow,
)

from ....identity import USER_ROLE, UserRole


def _validate_username(value: str) -> str:
    if not value or len(value) < 3:
        raise ValueError("Username must be at least 3 characters long")
    if len(value) > 50:
        raise ValueError("Username must be less than 50 characters")
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
    return value


def _validate_email(value: str) -> str:
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError as error:
        raise ValueError("Invalid email format") from error
    return value


def _validate_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(value) > 128:
        raise ValueError("Password must be less than 128 characters")
    if not re.search(r"[A-Za-z]", value):
        raise ValueError("Password must contain at least one letter")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password must contain at least one number")
    return value


ValidatedUsername = Annotated[
    str,
    StringConstraints(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$"),
    AfterValidator(_validate_username),
]
ValidatedEmail = Annotated[
    str,
    Field(json_schema_extra={"format": "email"}),
    AfterValidator(_validate_email),
]
ValidatedPassword = Annotated[
    str,
    StringConstraints(
        min_length=8,
        max_length=128,
        pattern=r"^(?:.*[A-Za-z].*[0-9]|.*[0-9].*[A-Za-z]).*$",
    ),
    AfterValidator(_validate_password),
]


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    """Public user fields; intentionally excludes the password hash."""

    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: str


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreateExtended(UserCreate):
    username: ValidatedUsername
    email: ValidatedEmail
    password: ValidatedPassword


class SelfUserUpdate(BaseModel):
    """Fields a signed-in user may change on their own account."""

    model_config = ConfigDict(extra="forbid")

    email: ValidatedEmail | None = Field(None, description="New email address")


class AdminUserUpdate(BaseModel):
    """Fields an administrator may change on another user account."""

    model_config = ConfigDict(extra="forbid")

    email: ValidatedEmail | None = Field(None, description="New email address")
    role: UserRole | None = Field(None, description="New role")
    is_active: bool | None = Field(None, description="Active status")


class PasswordChange(BaseModel):
    current_password: str
    new_password: ValidatedPassword


class UsersResponse(BaseModel):
    users: list[UserResponse]
    total: int
    offset: int
    limit: int


class SystemStats(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    recent_registrations: int


class UserCreateAdmin(BaseModel):
    username: ValidatedUsername
    email: ValidatedEmail
    password: ValidatedPassword
    role: UserRole = USER_ROLE
    is_active: bool = True


def convert_user_to_response(user: UserRow | PublicUserRow) -> UserResponse:
    """Convert either public or credential-bearing database rows to a response.

    List queries omit ``password_hash`` while lookups by user ID include it for
    authentication helpers. API responses must never expose that column, and
    must read the remaining fields at their respective positions.
    """
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )
