"""Models used by the authentication boundary."""

from pydantic import BaseModel

from ...identity import UserRole


class TokenData(BaseModel):
    username: str | None = None


class UserInDB(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: str
    password_hash: str
