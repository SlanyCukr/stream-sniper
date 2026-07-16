"""Framework-neutral user creation workflow."""

import bcrypt

from stream_sniper.database.gateways.identity.records import UserRow

from ...database.gateways.identity.user_table_gateway import (
    deactivate_user_db,
    insert_user_db,
    select_user_by_id_db,
    user_exists_db,
)
from ...identity import USER_ROLE, UserRole


class UserAlreadyExistsError(ValueError):
    """Raised when a username or email is already registered."""


class UserCreationError(RuntimeError):
    """Raised when persistence cannot complete user creation."""


def create_user(
    username: str,
    email: str,
    password: str,
    role: UserRole = USER_ROLE,
    is_active: bool = True,
) -> UserRow:
    """Create and reload one user using the shared persistence sequence."""
    if user_exists_db(username=username, email=email):
        raise UserAlreadyExistsError

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = insert_user_db(username=username, email=email, password_hash=password_hash, role=role)
    if user_id is None:
        raise UserCreationError("User insert returned no identifier")

    if not is_active and not deactivate_user_db(user_id):
        raise UserCreationError("Created user could not be deactivated")

    user = select_user_by_id_db(user_id)
    if user is None:
        raise UserCreationError("Created user could not be reloaded")
    return user
