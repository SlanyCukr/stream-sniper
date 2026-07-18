"""
Self-service authentication endpoints: registration, login, and the
current user's profile and password.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ....application.identity.user_creation import (
    UserAlreadyExistsError,
    UserCreationError,
    create_user,
)
from ....database.gateways.identity.user_table_gateway import (
    select_user_by_id_db,
    update_user_db,
    update_user_password_db,
)
from ....identity import USER_ROLE
from ....logging_config import get_logger, sanitize_log_value
from ...security.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter
from ...transport.models import ErrorResponse, MessageResponse, RateLimitErrorResponse
from .user_models import (
    PasswordChange,
    SelfUserUpdate,
    Token,
    UserCreateExtended,
    UserLogin,
    UserResponse,
    convert_user_to_response,
)

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""Requirements:
    - Username: 3-50 characters, alphanumeric with hyphens and underscores only
    - Email: Valid email address format
    - Password: 8-128 characters, must contain at least one letter and one number
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data or user already exists"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("5/minute")
def register_user(user_data: UserCreateExtended, request: Request, response: Response) -> UserResponse:
    try:
        user = create_user(user_data.username, user_data.email, user_data.password, role=USER_ROLE)
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="That username or email is already taken. Try a different one."
        ) from None
    except UserCreationError:
        logger.exception("Self-service registration failed for username %s", sanitize_log_value(user_data.username))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create the account because of a server problem. Try again in a moment.") from None

    logger.info("User registered successfully: %s", sanitize_log_value(user_data.username))
    return convert_user_to_response(user)


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Use the returned token in the Authorization header as `Bearer <token>`.",
    responses={
        200: {"description": "Login successful, token returned"},
        401: {"description": "Invalid credentials"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("10/minute")
def login(user_credentials: UserLogin, request: Request, response: Response) -> Token:
    user = authenticate_user(user_credentials.username, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_config = request.app.state.config.auth
    access_token_expires = timedelta(minutes=auth_config.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username},
        config=auth_config,
        expires_delta=access_token_expires,
    )

    logger.info("User logged in successfully: %s", sanitize_log_value(user.username))
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    responses={
        200: {"description": "Current user information"},
        401: {"description": "Authentication required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("60/minute")
def get_current_user_info(
    request: Request, response: Response, current_user: UserInDB = Depends(get_current_user)
) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user",
    description="Self-service updates are limited to the account email address.",
    responses={
        200: {"description": "User updated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid input data"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "User persistence failed"},
    },
)
@limiter.limit("10/minute")
def update_current_user(
    user_update: SelfUserUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
) -> UserResponse:
    if not user_update.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to save — change at least one field first.")

    success = update_user_db(
        current_user.id,
        email=user_update.email or None,
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save the changes because of a server problem. Try again in a moment.")

    updated_user = select_user_by_id_db(current_user.id)
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The changes may not have been saved because of a server problem. Refresh and try again.")

    logger.info("User updated successfully: %s", sanitize_log_value(current_user.username))
    return convert_user_to_response(updated_user)


@router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="Change password",
    description="The current password must be verified before replacement.",
    responses={
        200: {"description": "Password changed successfully"},
        400: {"model": ErrorResponse, "description": "Invalid current password or new password format"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Password persistence failed"},
    },
)
@limiter.limit("5/minute")
def change_password(
    password_change: PasswordChange,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_user),
) -> MessageResponse:
    if not verify_password(password_change.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    new_password_hash = hash_password(password_change.new_password)
    success = update_user_password_db(current_user.id, new_password_hash)

    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not change the password because of a server problem. Try again in a moment.")

    logger.info("Account access updated successfully for user id %s", sanitize_log_value(current_user.id))
    return MessageResponse(message="Password changed successfully")
