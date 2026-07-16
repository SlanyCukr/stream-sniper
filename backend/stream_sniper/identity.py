"""Dependency-neutral identity policy shared across application layers."""

from typing import Literal

UserRole = Literal["user", "admin"]

USER_ROLE: UserRole = "user"
ADMIN_ROLE: UserRole = "admin"
USER_ROLES: frozenset[UserRole] = frozenset({USER_ROLE, ADMIN_ROLE})
