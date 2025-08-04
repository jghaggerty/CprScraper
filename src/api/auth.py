"""
Authentication API endpoints for user management and role-based access control.
"""

from datetime import timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import joinedload

from src.auth.user_service import UserService
from src.database.models import User, Role, UserRole

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()
user_service = UserService()


# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str
    email: str
    first_name: str
    last_name: str
    roles: List[str]
    permissions: List[str]


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    password: str
    role_names: Optional[List[str]] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    roles: List[str]
    last_login: Optional[str] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: Optional[str] = None
    permissions: List[str]


class UserRoleAssignmentRequest(BaseModel):
    user_id: int
    role_name: str


class DashboardPreferenceRequest(BaseModel):
    preference_key: str
    preference_value: dict


class NotificationPreferenceRequest(BaseModel):
    notification_type: str
    change_severity: Optional[str] = None
    frequency: str = "daily"
    is_enabled: bool = True


# Dependency to get current user from token
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get the current authenticated user from JWT token."""
    token = credentials.credentials
    payload = user_service.verify_token(token)
    
    if not payload or "user_id" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = user_service.get_user_by_id(payload["user_id"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Dependency to check permissions
def require_permission(permission: str):
    """Decorator to require a specific permission."""
    def permission_checker(current_user: User = Depends(get_current_user)):
        if not user_service.has_permission(current_user.id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required"
            )
        return current_user
    return permission_checker


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = user_service.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user roles and permissions
    roles = [user_role.role.name for user_role in user.user_roles if user_role.is_active]
    permissions = user_service.get_user_permissions(user.id)
    
    # Create access token
    access_token = user_service.create_access_token(
        data={"user_id": user.id, "username": user.username}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        roles=roles,
        permissions=permissions
    )


@router.get("/me", response_model=LoginResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    roles = [user_role.role.name for user_role in current_user.user_roles if user_role.is_active]
    permissions = user_service.get_user_permissions(current_user.id)
    
    # Create a new token (refresh)
    access_token = user_service.create_access_token(
        data={"user_id": current_user.id, "username": current_user.username}
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        roles=roles,
        permissions=permissions
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    request: UserCreateRequest,
    current_user: User = Depends(require_permission("users:write"))
):
    """Create a new user (requires users:write permission)."""
    try:
        user = user_service.create_user(
            username=request.username,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            password=request.password,
            role_names=request.role_names
        )
        
        roles = [user_role.role.name for user_role in user.user_roles if user_role.is_active]
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            roles=roles,
            last_login=user.last_login.isoformat() if user.last_login else None
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/users", response_model=List[UserResponse])
async def get_users(current_user: User = Depends(require_permission("users:read"))):
    """Get all users (requires users:read permission)."""
    with user_service.get_db_session() as session:
        users = session.query(User).options(
            joinedload(User.user_roles).joinedload(UserRole.role)
        ).all()
        
        return [
            UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                is_active=user.is_active,
                roles=[user_role.role.name for user_role in user.user_roles if user_role.is_active],
                last_login=user.last_login.isoformat() if user.last_login else None
            )
            for user in users
        ]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_permission("users:read"))
):
    """Get a specific user by ID (requires users:read permission)."""
    user = user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    roles = [user_role.role.name for user_role in user.user_roles if user_role.is_active]
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        roles=roles,
        last_login=user.last_login.isoformat() if user.last_login else None
    )


@router.get("/roles", response_model=List[RoleResponse])
async def get_roles(current_user: User = Depends(require_permission("roles:read"))):
    """Get all available roles (requires roles:read permission)."""
    roles = user_service.get_all_roles()
    
    return [
        RoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=role.permissions or []
        )
        for role in roles
    ]


@router.post("/users/{user_id}/roles")
async def assign_role_to_user(
    user_id: int,
    request: UserRoleAssignmentRequest,
    current_user: User = Depends(require_permission("users:write"))
):
    """Assign a role to a user (requires users:write permission)."""
    success = user_service.assign_role_to_user(
        user_id=user_id,
        role_name=request.role_name,
        assigned_by=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign role. User or role may not exist, or role already assigned."
        )
    
    return {"message": f"Role '{request.role_name}' assigned to user {user_id}"}


@router.delete("/users/{user_id}/roles/{role_name}")
async def remove_role_from_user(
    user_id: int,
    role_name: str,
    current_user: User = Depends(require_permission("users:write"))
):
    """Remove a role from a user (requires users:write permission)."""
    success = user_service.remove_role_from_user(user_id=user_id, role_name=role_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove role. User or role may not exist, or role not assigned."
        )
    
    return {"message": f"Role '{role_name}' removed from user {user_id}"}


@router.get("/users/role/{role_name}", response_model=List[UserResponse])
async def get_users_by_role(
    role_name: str,
    current_user: User = Depends(require_permission("users:read"))
):
    """Get all users with a specific role (requires users:read permission)."""
    users = user_service.get_users_by_role(role_name)
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            roles=[user_role.role.name for user_role in user.user_roles if user_role.is_active],
            last_login=user.last_login.isoformat() if user.last_login else None
        )
        for user in users
    ]


@router.post("/users/{user_id}/dashboard-preferences")
async def update_dashboard_preference(
    user_id: int,
    request: DashboardPreferenceRequest,
    current_user: User = Depends(get_current_user)
):
    """Update user's dashboard preference (users can only update their own preferences)."""
    if current_user.id != user_id and not user_service.has_permission(current_user.id, "users:write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own preferences"
        )
    
    success = user_service.update_user_dashboard_preference(
        user_id=user_id,
        preference_key=request.preference_key,
        preference_value=request.preference_value
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update dashboard preference"
        )
    
    return {"message": "Dashboard preference updated successfully"}


@router.get("/users/{user_id}/dashboard-preferences")
async def get_dashboard_preferences(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user's dashboard preferences (users can only view their own preferences)."""
    if current_user.id != user_id and not user_service.has_permission(current_user.id, "users:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own preferences"
        )
    
    preferences = user_service.get_user_dashboard_preferences(user_id)
    return preferences


@router.post("/users/{user_id}/notification-preferences")
async def update_notification_preference(
    user_id: int,
    request: NotificationPreferenceRequest,
    current_user: User = Depends(get_current_user)
):
    """Update user's notification preference (users can only update their own preferences)."""
    if current_user.id != user_id and not user_service.has_permission(current_user.id, "users:write"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own preferences"
        )
    
    success = user_service.update_user_notification_preference(
        user_id=user_id,
        notification_type=request.notification_type,
        change_severity=request.change_severity,
        frequency=request.frequency,
        is_enabled=request.is_enabled
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update notification preference"
        )
    
    return {"message": "Notification preference updated successfully"}


@router.get("/users/{user_id}/notification-preferences")
async def get_notification_preferences(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user's notification preferences (users can only view their own preferences)."""
    if current_user.id != user_id and not user_service.has_permission(current_user.id, "users:read"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only view your own preferences"
        )
    
    preferences = user_service.get_user_notification_preferences(user_id)
    return preferences 