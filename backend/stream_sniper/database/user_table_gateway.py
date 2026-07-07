"""
Database gateway for user table operations.
"""

from typing import List, Optional, Tuple

from ..logging_config import get_logger
from .connection_pool import get_pool
from .decorators import log_database_operation

logger = get_logger(__name__)


@log_database_operation
def insert_user_db(username: str, email: str, password_hash: str, role: str = "user") -> Optional[int]:
    """
    Insert a new user into the database.
    
    Args:
        username: Unique username
        email: User's email address
        password_hash: Hashed password
        role: User role (default: 'user')
    
    Returns:
        User ID if successful, None otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (username, email, password_hash, role)
            )
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error inserting user: {e}")
        return None


@log_database_operation
def select_user_by_username_db(username: str) -> Optional[Tuple]:
    """
    Select user by username.
    
    Args:
        username: Username to search for
    
    Returns:
        User tuple (id, username, email, password_hash, role, is_active, created_at) or None
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, password_hash, role, is_active, created_at
                FROM users
                WHERE username = %s
                """,
                (username,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error selecting user by username: {e}")
        return None


@log_database_operation
def select_user_by_email_db(email: str) -> Optional[Tuple]:
    """
    Select user by email.
    
    Args:
        email: Email to search for
    
    Returns:
        User tuple (id, username, email, password_hash, role, is_active, created_at) or None
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, password_hash, role, is_active, created_at
                FROM users
                WHERE email = %s
                """,
                (email,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error selecting user by email: {e}")
        return None


@log_database_operation
def select_user_by_id_db(user_id: int) -> Optional[Tuple]:
    """
    Select user by ID.
    
    Args:
        user_id: User ID to search for
    
    Returns:
        User tuple (id, username, email, password_hash, role, is_active, created_at) or None
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, password_hash, role, is_active, created_at
                FROM users
                WHERE id = %s
                """,
                (user_id,)
            )
            return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error selecting user by ID: {e}")
        return None


@log_database_operation
def update_user_db(user_id: int, **kwargs) -> bool:
    """
    Update user information.
    
    Args:
        user_id: User ID to update
        **kwargs: Fields to update (username, email, password_hash, role, is_active)
    
    Returns:
        True if successful, False otherwise
    """
    pool = get_pool()
    
    if not kwargs:
        return False
    
    # Build dynamic update query
    set_clauses = []
    params = []
    
    for field, value in kwargs.items():
        if field in ['username', 'email', 'password_hash', 'role', 'is_active']:
            set_clauses.append(f"{field} = %s")
            params.append(value)
    
    if not set_clauses:
        return False
    
    # Always update the updated_at field
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            query = f"""
                UPDATE users 
                SET {', '.join(set_clauses)}
                WHERE id = %s
            """
            cursor.execute(query, params)
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False


@log_database_operation
def delete_user_db(user_id: int) -> bool:
    """
    Delete a user from the database.
    
    Args:
        user_id: User ID to delete
    
    Returns:
        True if successful, False otherwise
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False


@log_database_operation
def select_all_users_db(limit: int = 100, offset: int = 0) -> List[Tuple]:
    """
    Select all users with pagination.
    
    Args:
        limit: Number of users to return
        offset: Number of users to skip
    
    Returns:
        List of user tuples
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, email, role, is_active, created_at
                FROM users
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error selecting all users: {e}")
        return []


@log_database_operation
def count_users_db() -> int:
    """
    Count total number of users.
    
    Returns:
        Total number of users
    """
    pool = get_pool()
    
    try:
        with pool.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM users")
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error counting users: {e}")
        return 0


@log_database_operation
def user_exists_db(username: str = None, email: str = None) -> bool:
    """
    Check if a user exists by username or email.
    
    Args:
        username: Username to check
        email: Email to check
    
    Returns:
        True if user exists, False otherwise
    """
    pool = get_pool()
    
    if not username and not email:
        return False
    
    try:
        with pool.get_cursor() as cursor:
            if username and email:
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = %s OR email = %s",
                    (username, email)
                )
            elif username:
                cursor.execute(
                    "SELECT 1 FROM users WHERE username = %s",
                    (username,)
                )
            else:
                cursor.execute(
                    "SELECT 1 FROM users WHERE email = %s",
                    (email,)
                )
            
            return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking user existence: {e}")
        return False


@log_database_operation
def deactivate_user_db(user_id: int) -> bool:
    """
    Deactivate a user account.
    
    Args:
        user_id: User ID to deactivate
    
    Returns:
        True if successful, False otherwise
    """
    return update_user_db(user_id, is_active=False)


@log_database_operation
def activate_user_db(user_id: int) -> bool:
    """
    Activate a user account.
    
    Args:
        user_id: User ID to activate
    
    Returns:
        True if successful, False otherwise
    """
    return update_user_db(user_id, is_active=True)


@log_database_operation
def update_user_password_db(user_id: int, new_password_hash: str) -> bool:
    """
    Update a user's password.
    
    Args:
        user_id: User ID
        new_password_hash: New hashed password
    
    Returns:
        True if successful, False otherwise
    """
    return update_user_db(user_id, password_hash=new_password_hash)


@log_database_operation
def update_user_role_db(user_id: int, new_role: str) -> bool:
    """
    Update a user's role.
    
    Args:
        user_id: User ID
        new_role: New role (user/admin)
    
    Returns:
        True if successful, False otherwise
    """
    return update_user_db(user_id, role=new_role)