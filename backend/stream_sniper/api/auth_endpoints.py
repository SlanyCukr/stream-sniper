"""
Self-service authentication endpoints: registration, login, and the
current user's profile and password.
"""

from datetime import timedelta

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..database.user_table_gateway import (
    insert_user_db,
    select_user_by_id_db,
    update_user_password_db,
    user_exists_db,
)
from ..logging_config import get_logger
from .auth import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    UserInDB,
    UserLogin,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    hash_password,
)
from .rate_limiter import limiter
from .user_models import (
    PasswordChange,
    UserCreateExtended,
    UserResponse,
    UserUpdate,
    convert_user_to_response,
)

logger = get_logger(__name__)

# Mounted under /auth by auth_router.py.
router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
    Register a new user account.

    Requirements:
    - Username: 3-50 characters, alphanumeric with hyphens and underscores only
    - Email: Valid email address format
    - Password: 8-128 characters, must contain at least one letter and one number

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Invalid input data or user already exists"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
def register_user(
    user_data: UserCreateExtended,
    request: Request,
    response: Response
):
    """Register a new user"""
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
            role="user"
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # Fetch created user
        user_tuple = select_user_by_id_db(user_id)
        if not user_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created user"
            )

        logger.info(f"User registered successfully: {user_data.username}")
        return convert_user_to_response(user_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="""
    Authenticate user and receive JWT access token.

    Use the returned token in the Authorization header: `Bearer <token>`

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "Login successful, token returned"},
        401: {"description": "Invalid credentials"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def login(
    user_credentials: UserLogin,
    request: Request,
    response: Response
):
    """Authenticate user and return JWT token"""
    try:
        # Authenticate user
        user = authenticate_user(user_credentials.username, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create access token
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username},
            expires_delta=access_token_expires
        )

        logger.info(f"User logged in successfully: {user.username}")
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="""
    Get information about the currently authenticated user.

    Requires valid JWT token in Authorization header.

    **Rate Limit**: 60 requests per minute
    """,
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("60/minute")
def get_current_user_info(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="""
    Update current user's information.

    Users can update their own email address.
    Only admins can update role and active status.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
def update_current_user(
    user_update: UserUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Update current user information"""
    try:
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

        # Role and active status can only be updated by admins
        if user_update.role is not None:
            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can update user roles"
                )
            updates['role'] = user_update.role

        if user_update.is_active is not None:
            if current_user.role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can update user active status"
                )
            updates['is_active'] = user_update.is_active

        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )

        # Update user in database
        from ..database.user_table_gateway import update_user_db
        success = update_user_db(current_user.id, **updates)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )

        # Fetch updated user
        updated_user_tuple = select_user_by_id_db(current_user.id)
        if not updated_user_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated user"
            )

        logger.info(f"User updated successfully: {current_user.username}")
        return convert_user_to_response(updated_user_tuple)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/me/password",
    summary="Change password",
    description="""
    Change current user's password.

    Requires current password for verification.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Invalid current password or new password format"},
        401: {"description": "Authentication required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
def change_password(
    password_change: PasswordChange,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Change current user's password"""
    try:
        # Verify current password
        from .auth import verify_password
        if not verify_password(password_change.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash new password
        new_password_hash = hash_password(password_change.new_password)

        # Update password in database
        success = update_user_password_db(current_user.id, new_password_hash)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )

        logger.info(f"Password changed successfully for user: {current_user.username}")
        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
