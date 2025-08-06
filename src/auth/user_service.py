"""
User Management Service for role-based access control.
Handles authentication, authorization, and user preferences for Product Managers and Business Analysts.
"""

import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from src.database.models import User, Role, UserRole, UserDashboardPreference, UserNotificationPreference
from src.database.connection import get_db_session

# Alias for compatibility with existing imports
get_current_user = None  # Will be set by auth.py to avoid circular imports


class UserService:
    """Service for managing users, roles, and permissions."""
    
    def __init__(self):
        self.secret_key = "your-secret-key-here"  # In production, use environment variable
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 30
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return self.hash_password(password) == hashed
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password."""
        with get_db_session() as session:
            user = session.query(User).filter(
                and_(
                    User.username == username,
                    User.is_active == True
                )
            ).first()
            
            if not user or not self.verify_password(password, user.password_hash):
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            session.commit()
            
            return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get a user by ID with their roles."""
        with get_db_session() as session:
            return session.query(User).options(
                joinedload(User.user_roles).joinedload(UserRole.role)
            ).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username with their roles."""
        with get_db_session() as session:
            return session.query(User).options(
                joinedload(User.user_roles).joinedload(UserRole.role)
            ).filter(User.username == username).first()
    
    def get_user_permissions(self, user_id: int) -> List[str]:
        """Get all permissions for a user based on their roles."""
        with get_db_session() as session:
            user_roles = session.query(UserRole).options(
                joinedload(UserRole.role)
            ).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True,
                    UserRole.role.has(Role.is_active == True)
                )
            ).all()
            
            permissions = set()
            for user_role in user_roles:
                if user_role.role.permissions:
                    permissions.update(user_role.role.permissions)
            
            return list(permissions)
    
    def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if a user has a specific permission."""
        permissions = self.get_user_permissions(user_id)
        return permission in permissions
    
    def has_any_permission(self, user_id: int, permissions: List[str]) -> bool:
        """Check if a user has any of the specified permissions."""
        user_permissions = self.get_user_permissions(user_id)
        return any(perm in user_permissions for perm in permissions)
    
    def has_all_permissions(self, user_id: int, permissions: List[str]) -> bool:
        """Check if a user has all of the specified permissions."""
        user_permissions = self.get_user_permissions(user_id)
        return all(perm in user_permissions for perm in permissions)
    
    def create_user(self, username: str, email: str, first_name: str, last_name: str, 
                   password: str, role_names: List[str] = None) -> User:
        """Create a new user with specified roles."""
        with get_db_session() as session:
            # Check if user already exists
            existing_user = session.query(User).filter(
                or_(User.username == username, User.email == email)
            ).first()
            
            if existing_user:
                raise ValueError("User with this username or email already exists")
            
            # Create user
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash=self.hash_password(password),
                is_active=True
            )
            session.add(user)
            session.flush()  # Get the user ID
            
            # Assign roles
            if role_names:
                for role_name in role_names:
                    role = session.query(Role).filter(Role.name == role_name).first()
                    if role:
                        user_role = UserRole(
                            user_id=user.id,
                            role_id=role.id,
                            is_active=True
                        )
                        session.add(user_role)
            
            session.commit()
            return user
    
    def assign_role_to_user(self, user_id: int, role_name: str, assigned_by: int = None) -> bool:
        """Assign a role to a user."""
        with get_db_session() as session:
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                return False
            
            # Check if role is already assigned
            existing_role = session.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.id,
                    UserRole.is_active == True
                )
            ).first()
            
            if existing_role:
                return False
            
            user_role = UserRole(
                user_id=user_id,
                role_id=role.id,
                assigned_by=assigned_by,
                is_active=True
            )
            session.add(user_role)
            session.commit()
            return True
    
    def remove_role_from_user(self, user_id: int, role_name: str) -> bool:
        """Remove a role from a user."""
        with get_db_session() as session:
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                return False
            
            user_role = session.query(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.role_id == role.id,
                    UserRole.is_active == True
                )
            ).first()
            
            if not user_role:
                return False
            
            user_role.is_active = False
            session.commit()
            return True
    
    def get_users_by_role(self, role_name: str) -> List[User]:
        """Get all users with a specific role."""
        with get_db_session() as session:
            return session.query(User).join(UserRole).join(Role).filter(
                and_(
                    Role.name == role_name,
                    UserRole.is_active == True,
                    Role.is_active == True,
                    User.is_active == True
                )
            ).all()
    
    def get_all_roles(self) -> List[Role]:
        """Get all available roles."""
        with get_db_session() as session:
            return session.query(Role).filter(Role.is_active == True).all()
    
    def update_user_dashboard_preference(self, user_id: int, preference_key: str, 
                                       preference_value: Dict[str, Any]) -> bool:
        """Update a user's dashboard preference."""
        with get_db_session() as session:
            existing_pref = session.query(UserDashboardPreference).filter(
                and_(
                    UserDashboardPreference.user_id == user_id,
                    UserDashboardPreference.preference_key == preference_key
                )
            ).first()
            
            if existing_pref:
                existing_pref.preference_value = preference_value
                existing_pref.updated_at = datetime.utcnow()
            else:
                new_pref = UserDashboardPreference(
                    user_id=user_id,
                    preference_key=preference_key,
                    preference_value=preference_value
                )
                session.add(new_pref)
            
            session.commit()
            return True
    
    def get_user_dashboard_preferences(self, user_id: int) -> Dict[str, Any]:
        """Get all dashboard preferences for a user."""
        with get_db_session() as session:
            prefs = session.query(UserDashboardPreference).filter(
                UserDashboardPreference.user_id == user_id
            ).all()
            
            return {pref.preference_key: pref.preference_value for pref in prefs}
    
    def update_user_notification_preference(self, user_id: int, notification_type: str,
                                          change_severity: str = None, frequency: str = "daily",
                                          is_enabled: bool = True) -> bool:
        """Update a user's notification preference."""
        with get_db_session() as session:
            existing_pref = session.query(UserNotificationPreference).filter(
                and_(
                    UserNotificationPreference.user_id == user_id,
                    UserNotificationPreference.notification_type == notification_type
                )
            ).first()
            
            if existing_pref:
                existing_pref.change_severity = change_severity
                existing_pref.frequency = frequency
                existing_pref.is_enabled = is_enabled
                existing_pref.updated_at = datetime.utcnow()
            else:
                new_pref = UserNotificationPreference(
                    user_id=user_id,
                    notification_type=notification_type,
                    change_severity=change_severity,
                    frequency=frequency,
                    is_enabled=is_enabled
                )
                session.add(new_pref)
            
            session.commit()
            return True
    
    def get_user_notification_preferences(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all notification preferences for a user."""
        with get_db_session() as session:
            prefs = session.query(UserNotificationPreference).filter(
                UserNotificationPreference.user_id == user_id
            ).all()
            
            return [
                {
                    "notification_type": pref.notification_type,
                    "change_severity": pref.change_severity,
                    "frequency": pref.frequency,
                    "is_enabled": pref.is_enabled
                }
                for pref in prefs
            ]
    
    def get_users_for_notification(self, notification_type: str, change_severity: str = None) -> List[User]:
        """Get users who should receive a specific type of notification."""
        with get_db_session() as session:
            query = session.query(User).join(UserNotificationPreference).filter(
                and_(
                    UserNotificationPreference.notification_type == notification_type,
                    UserNotificationPreference.is_enabled == True,
                    User.is_active == True
                )
            )
            
            if change_severity:
                query = query.filter(
                    or_(
                        UserNotificationPreference.change_severity == change_severity,
                        UserNotificationPreference.change_severity == "all"
                    )
                )
            
            return query.all()
    
    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT access token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        """Get a user by their ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    def user_has_role(self, user_id: int, role_name: str) -> bool:
        """Check if a user has a specific role."""
        with get_db_session() as session:
            user_role = session.query(UserRole).join(Role).filter(
                and_(
                    UserRole.user_id == user_id,
                    Role.name == role_name,
                    UserRole.is_active == True
                )
            ).first()
            return user_role is not None
    
    def user_has_permission(self, user_id: int, permission_name: str) -> bool:
        """Check if a user has a specific permission through their roles."""
        # For now, we'll implement basic permission checking
        # You can extend this to have a more complex permission system
        role_permissions = {
            "Admin": ["read", "write", "delete", "manage_users", "manage_reports", "manage_settings"],
            "Product Manager": ["read", "write", "manage_reports", "export_data"],
            "Business Analyst": ["read", "export_data", "view_reports"]
        }
        
        with get_db_session() as session:
            user_roles = session.query(Role).join(UserRole).filter(
                and_(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True
                )
            ).all()
            
            for role in user_roles:
                if permission_name in role_permissions.get(role.name, []):
                    return True
            
            return False 