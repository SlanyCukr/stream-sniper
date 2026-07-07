"""
Authentication endpoints for user registration, login, and user management.
"""

import re
from datetime import timedelta
from typing import List, Optional

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator

from ..database.connection_pool import get_pool
from ..database.user_table_gateway import (
    activate_user_db,
    count_users_db,
    deactivate_user_db,
    delete_user_db,
    insert_user_db,
    select_all_users_db,
    select_user_by_id_db,
    update_user_password_db,
    update_user_role_db,
    user_exists_db,
)
from ..logging_config import get_logger
from .auth import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    Token,
    UserCreate,
    UserInDB,
    UserLogin,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    get_current_admin_user,
    hash_password,
)
from .rate_limiter import limiter

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


class UserResponse(BaseModel):
    """User response model (no password hash)"""
    id: int = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    role: str = Field(..., description="User role (user/admin)")
    is_active: bool = Field(..., description="Whether user is active")
    created_at: str = Field(..., description="User creation timestamp")


class UserCreateExtended(UserCreate):
    """Extended user creation with validation"""
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        try:
            validate_email(v)
            return v
        except EmailNotValidError:
            raise ValueError('Invalid email format')
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be less than 128 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[str] = Field(None, description="New email address")
    role: Optional[str] = Field(None, description="New role (admin only)")
    is_active: Optional[bool] = Field(None, description="Active status (admin only)")


class PasswordChange(BaseModel):
    """Password change model"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., description="New password", min_length=8, max_length=128)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v):
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v


class UsersResponse(BaseModel):
    """Paginated users response"""
    users: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., description="Total number of users")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")


def convert_user_to_response(user_tuple) -> UserResponse:
    """Convert database user tuple to UserResponse"""
    return UserResponse(
        id=user_tuple[0],
        username=user_tuple[1],
        email=user_tuple[2],
        role=user_tuple[3] if len(user_tuple) > 3 else "user",
        is_active=user_tuple[4] if len(user_tuple) > 4 else True,
        created_at=user_tuple[5].isoformat() if len(user_tuple) > 5 and user_tuple[5] else None
    )


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


# Admin endpoints
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


class SystemStats(BaseModel):
    """System statistics model"""
    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Number of active users")
    admin_users: int = Field(..., description="Number of admin users")
    recent_registrations: int = Field(..., description="Registrations in last 24 hours")


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


class UserCreateAdmin(BaseModel):
    """Admin user creation model"""
    username: str = Field(..., description="Username (3-50 characters)", min_length=3, max_length=50)
    email: str = Field(..., description="Valid email address")
    password: str = Field(..., description="Password (8-128 characters)", min_length=8, max_length=128)
    role: str = Field(default="user", description="User role (user/admin)")
    is_active: bool = Field(default=True, description="Whether user is active")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if len(v) > 50:
            raise ValueError('Username must be less than 50 characters')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        try:
            validate_email(v)
            return v
        except EmailNotValidError:
            raise ValueError('Invalid email format')
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v) > 128:
            raise ValueError('Password must be less than 128 characters')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v
    
    @field_validator('role')
    @classmethod
    def validate_role(cls, v):
        if v not in ["user", "admin"]:
            raise ValueError('Role must be either "user" or "admin"')
        return v


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
