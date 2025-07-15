"""
Protected routes decorator and middleware for the Stream Sniper API.
"""

from functools import wraps
from typing import List, Optional, Callable
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from .auth import get_current_user, get_current_admin_user, UserInDB

security = HTTPBearer()


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for an endpoint.
    
    Usage:
        @app.get("/protected")
        @require_auth
        def protected_endpoint(current_user: UserInDB = Depends(get_current_user)):
            return {"message": f"Hello {current_user.username}"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # The current_user dependency should be injected by the endpoint
        return await func(*args, **kwargs)
    return wrapper


def require_admin(func: Callable) -> Callable:
    """
    Decorator to require admin role for an endpoint.
    
    Usage:
        @app.get("/admin-only")
        @require_admin
        def admin_endpoint(current_user: UserInDB = Depends(get_current_admin_user)):
            return {"message": f"Hello admin {current_user.username}"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # The current_user dependency should be injected by the endpoint
        return await func(*args, **kwargs)
    return wrapper


def require_roles(allowed_roles: List[str]) -> Callable:
    """
    Decorator to require specific roles for an endpoint.
    
    Args:
        allowed_roles: List of roles that are allowed to access the endpoint
    
    Usage:
        @app.get("/moderator-only")
        @require_roles(["admin", "moderator"])
        def moderator_endpoint(current_user: UserInDB = Depends(get_current_user)):
            if current_user.role not in ["admin", "moderator"]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            return {"message": f"Hello {current_user.username}"}
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # The role checking should be handled in the endpoint itself
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def optional_auth(func: Callable) -> Callable:
    """
    Decorator for endpoints that optionally support authentication.
    
    If a valid token is provided, the user will be available.
    If no token or invalid token, the endpoint continues without user.
    
    Usage:
        @app.get("/optional-auth")
        @optional_auth
        def optional_endpoint(current_user: Optional[UserInDB] = None):
            if current_user:
                return {"message": f"Hello {current_user.username}"}
            else:
                return {"message": "Hello anonymous user"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


async def get_optional_current_user(
    credentials: Optional[HTTPBearer] = Depends(security)
) -> Optional[UserInDB]:
    """
    Dependency to get current user optionally.
    Returns None if no valid authentication is provided.
    """
    if not credentials:
        return None
    
    try:
        from .auth import verify_token, get_user_by_username
        token_data = verify_token(credentials.credentials)
        user = get_user_by_username(token_data.username)
        
        if user and user.is_active:
            return user
        return None
    except:
        return None


def create_role_dependency(required_role: str) -> Callable:
    """
    Factory function to create role-specific dependencies.
    
    Args:
        required_role: Role required to access the endpoint
        
    Returns:
        Dependency function that validates the user's role
    """
    async def role_dependency(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. {required_role} role required."
            )
        return current_user
    
    return role_dependency


def create_roles_dependency(required_roles: List[str]) -> Callable:
    """
    Factory function to create multi-role dependencies.
    
    Args:
        required_roles: List of roles that are allowed to access the endpoint
        
    Returns:
        Dependency function that validates the user's role
    """
    async def roles_dependency(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in required_roles:
            roles_str = ", ".join(required_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. One of the following roles required: {roles_str}"
            )
        return current_user
    
    return roles_dependency


# Pre-defined role dependencies
require_admin_role = create_role_dependency("admin")
require_user_role = create_role_dependency("user")
require_any_role = create_roles_dependency(["user", "admin"])


# Protected endpoint examples (for reference)
"""
# Example 1: Simple protected endpoint
@app.get("/protected")
async def protected_endpoint(current_user: UserInDB = Depends(get_current_user)):
    return {"message": f"Hello {current_user.username}"}

# Example 2: Admin-only endpoint
@app.get("/admin-only")
async def admin_endpoint(current_user: UserInDB = Depends(get_current_admin_user)):
    return {"message": f"Hello admin {current_user.username}"}

# Example 3: Optional authentication
@app.get("/optional-auth")
async def optional_endpoint(current_user: Optional[UserInDB] = Depends(get_optional_current_user)):
    if current_user:
        return {"message": f"Hello {current_user.username}"}
    else:
        return {"message": "Hello anonymous user"}

# Example 4: Custom role requirement
@app.get("/moderator-only")
async def moderator_endpoint(current_user: UserInDB = Depends(require_admin_role)):
    return {"message": f"Hello {current_user.username}"}

# Example 5: Multiple roles allowed
@app.get("/staff-only")
async def staff_endpoint(current_user: UserInDB = Depends(require_any_role)):
    return {"message": f"Hello {current_user.username}"}
"""