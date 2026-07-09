"""
User administration endpoints (admin only): user listing and CRUD, role and
active-status management, admin user creation, and system statistics.
"""

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..database.connection_pool import get_pool
from ..database.user_table_gateway import (
    activate_user_db,
    count_users_db,
    deactivate_user_db,
    delete_user_db,
    insert_user_db,
    select_all_users_db,
    select_user_by_id_db,
    update_user_role_db,
    user_exists_db,
)
from ..logging_config import get_logger
from .auth import UserInDB, get_current_admin_user, hash_password
from .rate_limiter import limiter
from .user_models import (
    SystemStats,
    UserCreateAdmin,
    UserResponse,
    UsersResponse,
    UserUpdate,
    convert_user_to_response,
)

logger = get_logger(__name__)

# Mounted under /auth by auth_router.py.
router = APIRouter()


@router.get(
    "/users",
    response_model=UsersResponse,
    summary="Get all users (Admin only)",
    description="""
    Get list of all users with pagination.

    Requires admin role.

    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "List of users"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
def get_all_users(
    request: Request,
    response: Response,
    offset: int = 0,
    limit: int = 100,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get all users (admin only)"""
    try:
        users_tuple = select_all_users_db(limit=limit, offset=offset)
        total = count_users_db()

        users = [convert_user_to_response(user_tuple) for user_tuple in users_tuple]

        return UsersResponse(
            users=users,
            total=total,
            offset=offset,
            limit=limit
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/users/{user_id}/role",
    summary="Update user role (Admin only)",
    description="""
    Update a user's role.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "User role updated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def update_user_role(
    user_id: int,
    new_role: str,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Update user role (admin only)"""
    try:
        if new_role not in ["user", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role must be either 'user' or 'admin'"
            )

        success = update_user_role_db(user_id, new_role)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User role updated by admin {current_user.username}: user_id={user_id}, new_role={new_role}")
        return {"message": f"User role updated to {new_role}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/users/{user_id}/activate",
    summary="Activate user (Admin only)",
    description="""
    Activate a user account.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "User activated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def activate_user(
    user_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Activate user account (admin only)"""
    try:
        success = activate_user_db(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User activated by admin {current_user.username}: user_id={user_id}")
        return {"message": "User activated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/users/{user_id}/deactivate",
    summary="Deactivate user (Admin only)",
    description="""
    Deactivate a user account.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "User deactivated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def deactivate_user(
    user_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Deactivate user account (admin only)"""
    try:
        success = deactivate_user_db(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User deactivated by admin {current_user.username}: user_id={user_id}")
        return {"message": "User deactivated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/users/{user_id}",
    summary="Delete user (Admin only)",
    description="""
    Permanently delete a user account.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "User deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
def delete_user(
    user_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Delete user account (admin only)"""
    try:
        # Prevent admin from deleting themselves
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        success = delete_user_db(user_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User deleted by admin {current_user.username}: user_id={user_id}")
        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID (Admin only)",
    description="""
    Get detailed information about a specific user.

    Requires admin role.

    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "User information"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
def get_user_by_id(
    user_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get user by ID (admin only)"""
    try:
        user_tuple = select_user_by_id_db(user_id)

        if not user_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return convert_user_to_response(user_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user (Admin only)",
    description="""
    Update user information including email, role, and active status.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def update_user_by_id(
    user_id: int,
    user_update: UserUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Update user information (admin only)"""
    try:
        # Check if user exists
        user_tuple = select_user_by_id_db(user_id)
        if not user_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updates = {}

        # Email validation and update
        if user_update.email:
            try:
                validate_email(user_update.email)
                updates['email'] = user_update.email
            except EmailNotValidError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email format"
                )

        # Role update
        if user_update.role is not None:
            if user_update.role not in ["user", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be either 'user' or 'admin'"
                )
            updates['role'] = user_update.role

        # Active status update
        if user_update.is_active is not None:
            updates['is_active'] = user_update.is_active

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Update user in database
        from ..database.user_table_gateway import update_user_db
        success = update_user_db(user_id, **updates)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )

        # Fetch updated user
        updated_user_tuple = select_user_by_id_db(user_id)
        if not updated_user_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated user"
            )

        logger.info(f"User updated by admin {current_user.username}: user_id={user_id}")
        return convert_user_to_response(updated_user_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/admin/stats",
    response_model=SystemStats,
    summary="Get system statistics (Admin only)",
    description="""
    Get comprehensive system statistics including user counts and activity metrics.

    Requires admin role.

    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "System statistics"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
def get_system_stats(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get system statistics (admin only)"""
    try:
        # Get user statistics
        pool = get_pool()

        with pool.get_cursor() as cursor:
            # Total users
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            # Active users
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
            active_users = cursor.fetchone()[0]

            # Admin users
            cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
            admin_users = cursor.fetchone()[0]

            # Recent registrations (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) FROM users
                WHERE created_at >= NOW() - INTERVAL '24 hours'
            """)
            recent_registrations = cursor.fetchone()[0]

        return SystemStats(
            total_users=total_users,
            active_users=active_users,
            admin_users=admin_users,
            recent_registrations=recent_registrations
        )

    except Exception as e:
        logger.error(f"Error fetching system stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/admin/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user (Admin only)",
    description="""
    Create a new user account with admin privileges.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data or user already exists"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def create_user_admin(
    user_data: UserCreateAdmin,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Create user (admin only)"""
    try:
        # Check if user already exists
        if user_exists_db(username=user_data.username, email=user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this username or email already exists"
            )

        # Hash password
        password_hash = hash_password(user_data.password)

        # Create user in database
        user_id = insert_user_db(
            username=user_data.username,
            email=user_data.email,
            password_hash=password_hash,
            role=user_data.role
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # Set active status if specified
        if not user_data.is_active:
            deactivate_user_db(user_id)

        # Fetch created user
        user_tuple = select_user_by_id_db(user_id)
        if not user_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created user"
            )

        logger.info(f"User created by admin {current_user.username}: {user_data.username}")
        return convert_user_to_response(user_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
