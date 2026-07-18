"""
Database gateway for user table operations.
"""

from stream_sniper.database.gateways.identity.records import (
    PublicUserRow,
    UserRow,
)

from ....identity import USER_ROLE, UserRole
from ...core.decorators import read_cursor, write_cursor


def insert_user_db(username: str, email: str, password_hash: str, role: UserRole = USER_ROLE) -> int | None:

    with write_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (username, email, password_hash, role),
        )
        result = cursor.fetchone()
        return result[0] if result else None


def select_user_by_username_db(username: str) -> UserRow | None:

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, password_hash, role, is_active, created_at
            FROM users
            WHERE username = %s
            """,
            (username,),
        )
        row = cursor.fetchone()
        return UserRow(*row) if row else None


def select_user_by_id_db(user_id: int) -> UserRow | None:

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, password_hash, role, is_active, created_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cursor.fetchone()
        return UserRow(*row) if row else None


def update_user_db(
    user_id: int,
    *,
    username: str | None = None,
    email: str | None = None,
    password_hash: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> bool:
    """Update non-null fields and return whether a user row changed."""

    set_clauses: list[str] = []
    params: list[object] = []

    values = {
        "username": username,
        "email": email,
        "password_hash": password_hash,
        "role": role,
        "is_active": is_active,
    }
    for field, value in values.items():
        if value is not None:
            set_clauses.append(f"{field} = %s")
            params.append(value)

    if not set_clauses:
        return False

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)

    with write_cursor() as cursor:
        query = f"""
            UPDATE users
            SET {", ".join(set_clauses)}
            WHERE id = %s
        """
        cursor.execute(query, params)
        return bool(cursor.rowcount > 0)


def delete_user_db(user_id: int) -> bool:

    with write_cursor() as cursor:
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        return bool(cursor.rowcount > 0)


def select_user_page_db(limit: int = 100, offset: int = 0) -> list[PublicUserRow]:

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT id, username, email, role, is_active, created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        )
        return [PublicUserRow(*row) for row in cursor.fetchall()]


def count_users_db() -> int:

    with read_cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()
        return result[0] if result else 0


def user_exists_db(username: str | None = None, email: str | None = None) -> bool:

    if not username and not email:
        return False

    with read_cursor() as cursor:
        if username and email:
            cursor.execute("SELECT 1 FROM users WHERE username = %s OR email = %s", (username, email))
        elif username:
            cursor.execute("SELECT 1 FROM users WHERE username = %s", (username,))
        else:
            cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))

        return cursor.fetchone() is not None


def deactivate_user_db(user_id: int) -> bool:
    return update_user_db(user_id, is_active=False)


def activate_user_db(user_id: int) -> bool:
    return update_user_db(user_id, is_active=True)


def update_user_password_db(user_id: int, new_password_hash: str) -> bool:
    return update_user_db(user_id, password_hash=new_password_hash)


def update_user_role_db(user_id: int, new_role: UserRole) -> bool:
    return update_user_db(user_id, role=new_role)
