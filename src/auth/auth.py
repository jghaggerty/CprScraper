"""
Authentication and authorization module for API endpoints.
Provides decorators and functions for securing API endpoints.
"""

from typing import Optional
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .user_service import UserService
from ..database.connection import get_db
from ..database.models import User

# Security scheme for JWT token authentication
security = HTTPBearer()
user_service = UserService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: The HTTP authorization credentials containing the JWT token
        db: Database session
        
    Returns:
        User: The authenticated user object
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Extract token from credentials
    token = credentials.credentials
    
    try:
        # Decode and validate the JWT token
        user_data = user_service.decode_access_token(token)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = user_service.get_user_by_id(db, user_data.get("user_id"))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Get the current active user, ensuring they are not disabled.
    
    Args:
        current_user: The current user from get_current_user
        
    Returns:
        User: The active user object
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def require_role(required_role: str):
    """
    Decorator factory to require a specific role for accessing an endpoint.
    
    Args:
        required_role: The role required to access the endpoint
        
    Returns:
        A dependency function that checks user role
    """
    async def check_role(current_user: User = Depends(get_current_active_user)) -> User:
        if not user_service.user_has_role(current_user.id, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return check_role


def require_permission(required_permission: str):
    """
    Decorator factory to require a specific permission for accessing an endpoint.
    
    Args:
        required_permission: The permission required to access the endpoint
        
    Returns:
        A dependency function that checks user permission
    """
    async def check_permission(current_user: User = Depends(get_current_active_user)) -> User:
        if not user_service.user_has_permission(current_user.id, required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user
    
    return check_permission


# Common role-based dependencies
require_product_manager = require_role("Product Manager")
require_business_analyst = require_role("Business Analyst")
require_admin = require_role("Admin")
