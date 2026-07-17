"""
User administration endpoints (admin only): user listing and CRUD, role and
active-status management, admin user creation, and system statistics.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ....application.identity.user_creation import UserAlreadyExistsError, UserCreationError, create_user
from ....database.core.connection_pool import get_active_pool
from ....database.gateways.identity.user_table_gateway import (
    activate_user_db,
    count_users_db,
    deactivate_user_db,
    delete_user_db,
    select_user_by_id_db,
    select_user_page_db,
    update_user_db,
    update_user_role_db,
)
from ....identity import ADMIN_ROLE, UserRole
from ....logging_config import get_logger, sanitize_log_value
from ...security.auth import get_current_admin_user
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter
from ...transport.models import ErrorResponse, RateLimitErrorResponse
from .user_models import (
    AdminUserUpdate,
    SystemStats,
    UserCreateAdmin,
    UserResponse,
    UsersResponse,
    convert_user_to_response,
)

logger = get_logger(__name__)

router = APIRouter(dependencies=[Depends(get_current_admin_user)])


def _reject_self_lockout(
    user_id: int,
    current_user: UserInDB,
    *,
    role: UserRole | None = None,
    is_active: bool | None = None,
) -> None:
    if user_id != current_user.id:
        return
    if role is not None and role != ADMIN_ROLE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove your own admin role")
    if is_active is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account")


def _load_user_response(user_id: int) -> UserResponse:
    user = select_user_by_id_db(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve updated user")
    return convert_user_to_response(user)


@router.get(
    "/users",
    response_model=UsersResponse,
    summary="List a page of users",
    responses={
        200: {"description": "List of users"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
def list_users(
    request: Request,
    response: Response,
    offset: int = 0,
    limit: int = 100,
) -> UsersResponse:
    user_records = select_user_page_db(limit=limit, offset=offset)
    total = count_users_db()

    users = [convert_user_to_response(user) for user in user_records]

    return UsersResponse(users=users, total=total, offset=offset, limit=limit)


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role",
    responses={
        200: {"description": "User role updated successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("10/minute")
def update_user_role(
    user_id: int,
    new_role: UserRole,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user),
) -> UserResponse:
    _reject_self_lockout(user_id, current_user, role=new_role)
    success = update_user_role_db(user_id, new_role)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info(
        "User role updated by admin %s: user_id=%s, new_role=%s",
        sanitize_log_value(current_user.username),
        user_id,
        sanitize_log_value(new_role),
    )
    return _load_user_response(user_id)


@router.put(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    summary="Activate user",
    responses={
        200: {"description": "User activated successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("10/minute")
def activate_user(
    user_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> UserResponse:
    success = activate_user_db(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info("User activated by admin %s: user_id=%s", sanitize_log_value(current_user.username), user_id)
    return _load_user_response(user_id)


@router.put(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    summary="Deactivate user",
    responses={
        200: {"description": "User deactivated successfully"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("10/minute")
def deactivate_user(
    user_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> UserResponse:
    _reject_self_lockout(user_id, current_user, is_active=False)
    success = deactivate_user_db(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info("User deactivated by admin %s: user_id=%s", sanitize_log_value(current_user.username), user_id)
    return _load_user_response(user_id)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user",
    description="Permanently removes the account; administrators cannot delete themselves.",
    responses={
        204: {"description": "User deleted successfully"},
        400: {"model": ErrorResponse, "description": "Administrators cannot delete themselves"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("5/minute")
def delete_user(
    user_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> None:
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    success = delete_user_db(user_id)

    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.info("User deleted by admin %s: user_id=%s", sanitize_log_value(current_user.username), user_id)
    return None


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    responses={
        200: {"description": "User information"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
def get_user_by_id(user_id: int, request: Request, response: Response) -> UserResponse:
    user = select_user_by_id_db(user_id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return convert_user_to_response(user)


@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update user",
    description="Updates email, role, or active status; administrators cannot lock out their own account.",
    responses={
        200: {"description": "User updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "User not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("10/minute")
def update_user_by_id(
    user_id: int,
    user_update: AdminUserUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user),
) -> UserResponse:
    user = select_user_by_id_db(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    _reject_self_lockout(
        user_id,
        current_user,
        role=user_update.role,
        is_active=user_update.is_active,
    )

    if not user_update.email and user_update.role is None and user_update.is_active is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")

    success = update_user_db(
        user_id,
        email=user_update.email or None,
        role=user_update.role,
        is_active=user_update.is_active,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")

    logger.info("User updated by admin %s: user_id=%s", sanitize_log_value(current_user.username), user_id)
    return _load_user_response(user_id)


@router.get(
    "/admin/stats",
    response_model=SystemStats,
    summary="Get system statistics",
    responses={
        200: {"description": "System statistics"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
def get_system_stats(request: Request, response: Response) -> SystemStats:
    pool = get_active_pool()

    with pool.get_cursor() as cursor:

        def scalar_count() -> int:
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError("COUNT query returned no row")
            return int(row[0])

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = scalar_count()

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
        active_users = scalar_count()

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = %s", (ADMIN_ROLE,))
        admin_users = scalar_count()

        cursor.execute("""
            SELECT COUNT(*) FROM users
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        recent_registrations = scalar_count()

    return SystemStats(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        recent_registrations=recent_registrations,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    responses={
        201: {"description": "User created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data or user already exists"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("10/minute")
def create_user_admin(
    user_data: UserCreateAdmin,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user),
) -> UserResponse:
    try:
        user = create_user(
            user_data.username,
            user_data.email,
            user_data.password,
            role=user_data.role,
            is_active=user_data.is_active,
        )
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User with this username or email already exists"
        ) from None
    except UserCreationError:
        logger.exception("Admin user creation failed for username %s", sanitize_log_value(user_data.username))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user") from None

    logger.info(
        "User created by admin %s: %s",
        sanitize_log_value(current_user.username),
        sanitize_log_value(user_data.username),
    )
    return convert_user_to_response(user)
