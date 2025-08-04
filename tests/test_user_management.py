"""
Unit and integration tests for user management system.
Tests authentication, authorization, and role-based access control.
"""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.auth.user_service import UserService
from src.database.models import User, Role, UserRole, UserDashboardPreference, UserNotificationPreference
from src.api.auth import router as auth_router
from fastapi.testclient import TestClient
from fastapi import FastAPI


class TestUserService:
    """Test cases for UserService class."""
    
    @pytest.fixture
    def user_service(self):
        return UserService()
    
    @pytest.fixture
    def mock_session(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_user(self):
        user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password_hash="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",  # "123"
            is_active=True,
            is_superuser=False
        )
        return user
    
    @pytest.fixture
    def sample_role(self):
        role = Role(
            id=1,
            name="product_manager",
            display_name="Product Manager",
            description="Product Manager role",
            permissions=["dashboard:read", "dashboard:write", "users:read"],
            is_active=True
        )
        return role
    
    def test_hash_password(self, user_service):
        """Test password hashing functionality."""
        password = "testpassword"
        hashed = user_service.hash_password(password)
        
        assert hashed != password
        assert len(hashed) == 64  # SHA-256 hash length
        assert user_service.verify_password(password, hashed)
        assert not user_service.verify_password("wrongpassword", hashed)
    
    def test_create_access_token(self, user_service):
        """Test JWT token creation."""
        data = {"user_id": 1, "username": "testuser"}
        token = user_service.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = user_service.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
        assert payload["username"] == "testuser"
    
    def test_verify_token_valid(self, user_service):
        """Test valid token verification."""
        data = {"user_id": 1, "username": "testuser"}
        token = user_service.create_access_token(data)
        
        payload = user_service.verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 1
    
    def test_verify_token_invalid(self, user_service):
        """Test invalid token verification."""
        invalid_token = "invalid.token.here"
        payload = user_service.verify_token(invalid_token)
        assert payload is None
    
    def test_verify_token_expired(self, user_service):
        """Test expired token verification."""
        data = {"user_id": 1, "username": "testuser"}
        token = user_service.create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        payload = user_service.verify_token(token)
        assert payload is None
    
    @patch('src.auth.user_service.get_db_session')
    def test_authenticate_user_success(self, mock_get_session, user_service, sample_user, mock_session):
        """Test successful user authentication."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = sample_user
        
        user = user_service.authenticate_user("testuser", "123")
        
        assert user is not None
        assert user.username == "testuser"
        mock_session.commit.assert_called_once()
    
    @patch('src.auth.user_service.get_db_session')
    def test_authenticate_user_invalid_password(self, mock_get_session, user_service, sample_user, mock_session):
        """Test authentication with invalid password."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = sample_user
        
        user = user_service.authenticate_user("testuser", "wrongpassword")
        
        assert user is None
    
    @patch('src.auth.user_service.get_db_session')
    def test_authenticate_user_inactive(self, mock_get_session, user_service, mock_session):
        """Test authentication with inactive user."""
        inactive_user = User(
            id=1,
            username="inactiveuser",
            email="inactive@example.com",
            first_name="Inactive",
            last_name="User",
            password_hash="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            is_active=False
        )
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = inactive_user
        
        user = user_service.authenticate_user("inactiveuser", "123")
        
        assert user is None
    
    @patch('src.auth.user_service.get_db_session')
    def test_get_user_permissions(self, mock_get_session, user_service, mock_session, sample_role):
        """Test getting user permissions."""
        user_role = UserRole(
            id=1,
            user_id=1,
            role_id=1,
            is_active=True
        )
        user_role.role = sample_role
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = [user_role]
        
        permissions = user_service.get_user_permissions(1)
        
        assert "dashboard:read" in permissions
        assert "dashboard:write" in permissions
        assert "users:read" in permissions
    
    def test_has_permission(self, user_service):
        """Test permission checking."""
        with patch.object(user_service, 'get_user_permissions', return_value=["dashboard:read", "users:write"]):
            assert user_service.has_permission(1, "dashboard:read")
            assert user_service.has_permission(1, "users:write")
            assert not user_service.has_permission(1, "admin:read")
    
    def test_has_any_permission(self, user_service):
        """Test checking for any permission."""
        with patch.object(user_service, 'get_user_permissions', return_value=["dashboard:read", "users:write"]):
            assert user_service.has_any_permission(1, ["dashboard:read", "admin:read"])
            assert user_service.has_any_permission(1, ["users:write", "admin:read"])
            assert not user_service.has_any_permission(1, ["admin:read", "admin:write"])
    
    def test_has_all_permissions(self, user_service):
        """Test checking for all permissions."""
        with patch.object(user_service, 'get_user_permissions', return_value=["dashboard:read", "users:write"]):
            assert user_service.has_all_permissions(1, ["dashboard:read", "users:write"])
            assert not user_service.has_all_permissions(1, ["dashboard:read", "admin:read"])
    
    @patch('src.auth.user_service.get_db_session')
    def test_create_user_success(self, mock_get_session, user_service, mock_session):
        """Test successful user creation."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        user = user_service.create_user(
            username="newuser",
            email="new@example.com",
            first_name="New",
            last_name="User",
            password="password123",
            role_names=["product_manager"]
        )
        
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('src.auth.user_service.get_db_session')
    def test_create_user_duplicate(self, mock_get_session, user_service, mock_session, sample_user):
        """Test user creation with duplicate username."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = sample_user
        
        with pytest.raises(ValueError, match="User with this username or email already exists"):
            user_service.create_user(
                username="testuser",
                email="test@example.com",
                first_name="Test",
                last_name="User",
                password="password123"
            )
    
    @patch('src.auth.user_service.get_db_session')
    def test_assign_role_to_user(self, mock_get_session, user_service, mock_session, sample_role):
        """Test assigning role to user."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = sample_role
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing role assignment
        
        success = user_service.assign_role_to_user(1, "product_manager", assigned_by=2)
        
        assert success
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('src.auth.user_service.get_db_session')
    def test_remove_role_from_user(self, mock_get_session, user_service, mock_session):
        """Test removing role from user."""
        user_role = UserRole(
            id=1,
            user_id=1,
            role_id=1,
            is_active=True
        )
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = user_role
        
        success = user_service.remove_role_from_user(1, "product_manager")
        
        assert success
        assert not user_role.is_active
        mock_session.commit.assert_called()
    
    @patch('src.auth.user_service.get_db_session')
    def test_update_user_dashboard_preference(self, mock_get_session, user_service, mock_session):
        """Test updating user dashboard preference."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None  # No existing preference
        
        success = user_service.update_user_dashboard_preference(
            user_id=1,
            preference_key="layout",
            preference_value={"theme": "dark", "sidebar": "collapsed"}
        )
        
        assert success
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('src.auth.user_service.get_db_session')
    def test_get_user_dashboard_preferences(self, mock_get_session, user_service, mock_session):
        """Test getting user dashboard preferences."""
        pref1 = UserDashboardPreference(
            id=1,
            user_id=1,
            preference_key="layout",
            preference_value={"theme": "dark"}
        )
        pref2 = UserDashboardPreference(
            id=2,
            user_id=1,
            preference_key="widgets",
            preference_value={"show_charts": True}
        )
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = [pref1, pref2]
        
        preferences = user_service.get_user_dashboard_preferences(1)
        
        assert preferences["layout"] == {"theme": "dark"}
        assert preferences["widgets"] == {"show_charts": True}


class TestAuthAPI:
    """Test cases for authentication API endpoints."""
    
    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.include_router(auth_router)
        return app
    
    @pytest.fixture
    def client(self, app):
        return TestClient(app)
    
    @pytest.fixture
    def mock_user_service(self):
        with patch('src.api.auth.user_service') as mock:
            yield mock
    
    def test_login_success(self, client, mock_user_service):
        """Test successful login."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.user_roles = []
        
        mock_user_service.authenticate_user.return_value = mock_user
        mock_user_service.get_user_permissions.return_value = ["dashboard:read"]
        mock_user_service.create_access_token.return_value = "mock.jwt.token"
        
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["access_token"] == "mock.jwt.token"
        assert data["username"] == "testuser"
        assert data["user_id"] == 1
    
    def test_login_invalid_credentials(self, client, mock_user_service):
        """Test login with invalid credentials."""
        mock_user_service.authenticate_user.return_value = None
        
        response = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_get_current_user_info(self, client, mock_user_service):
        """Test getting current user information."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.first_name = "Test"
        mock_user.last_name = "User"
        mock_user.user_roles = []
        
        mock_user_service.verify_token.return_value = {"user_id": 1, "username": "testuser"}
        mock_user_service.get_user_by_id.return_value = mock_user
        mock_user_service.get_user_permissions.return_value = ["dashboard:read"]
        mock_user_service.create_access_token.return_value = "new.mock.jwt.token"
        
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer mock.jwt.token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testuser"
        assert data["user_id"] == 1
    
    def test_get_current_user_invalid_token(self, client, mock_user_service):
        """Test getting current user with invalid token."""
        mock_user_service.verify_token.return_value = None
        
        response = client.get("/api/auth/me", headers={
            "Authorization": "Bearer invalid.token"
        })
        
        assert response.status_code == 401
    
    def test_create_user_success(self, client, mock_user_service):
        """Test successful user creation."""
        # Mock user data
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "newuser"
        mock_user.email = "new@example.com"
        mock_user.first_name = "New"
        mock_user.last_name = "User"
        mock_user.is_active = True
        mock_user.user_roles = []
        
        mock_user_service.create_user.return_value = mock_user
        
        response = client.post("/api/auth/users", json={
            "username": "newuser",
            "email": "new@example.com",
            "first_name": "New",
            "last_name": "User",
            "password": "password123",
            "role_names": ["product_manager"]
        }, headers={
            "Authorization": "Bearer admin.token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
    
    def test_create_user_duplicate(self, client, mock_user_service):
        """Test user creation with duplicate username."""
        mock_user_service.create_user.side_effect = ValueError("User with this username or email already exists")
        
        response = client.post("/api/auth/users", json={
            "username": "existinguser",
            "email": "existing@example.com",
            "first_name": "Existing",
            "last_name": "User",
            "password": "password123"
        }, headers={
            "Authorization": "Bearer admin.token"
        })
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_get_users(self, client, mock_user_service):
        """Test getting all users."""
        # Mock users data
        mock_user1 = Mock()
        mock_user1.id = 1
        mock_user1.username = "user1"
        mock_user1.email = "user1@example.com"
        mock_user1.first_name = "User"
        mock_user1.last_name = "One"
        mock_user1.is_active = True
        mock_user1.user_roles = []
        
        mock_user2 = Mock()
        mock_user2.id = 2
        mock_user2.username = "user2"
        mock_user2.email = "user2@example.com"
        mock_user2.first_name = "User"
        mock_user2.last_name = "Two"
        mock_user2.is_active = True
        mock_user2.user_roles = []
        
        mock_user_service.get_db_session.return_value.__enter__.return_value.query.return_value.options.return_value.all.return_value = [mock_user1, mock_user2]
        
        response = client.get("/api/auth/users", headers={
            "Authorization": "Bearer admin.token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["username"] == "user1"
        assert data[1]["username"] == "user2"
    
    def test_assign_role_to_user(self, client, mock_user_service):
        """Test assigning role to user."""
        mock_user_service.assign_role_to_user.return_value = True
        
        response = client.post("/api/auth/users/1/roles", json={
            "user_id": 1,
            "role_name": "product_manager"
        }, headers={
            "Authorization": "Bearer admin.token"
        })
        
        assert response.status_code == 200
        assert "assigned" in response.json()["message"]
    
    def test_remove_role_from_user(self, client, mock_user_service):
        """Test removing role from user."""
        mock_user_service.remove_role_from_user.return_value = True
        
        response = client.delete("/api/auth/users/1/roles/product_manager", headers={
            "Authorization": "Bearer admin.token"
        })
        
        assert response.status_code == 200
        assert "removed" in response.json()["message"]
    
    def test_get_roles(self, client, mock_user_service):
        """Test getting all roles."""
        # Mock roles data
        mock_role1 = Mock()
        mock_role1.id = 1
        mock_role1.name = "product_manager"
        mock_role1.display_name = "Product Manager"
        mock_role1.description = "Product Manager role"
        mock_role1.permissions = ["dashboard:read", "users:read"]
        
        mock_role2 = Mock()
        mock_role2.id = 2
        mock_role2.name = "business_analyst"
        mock_role2.display_name = "Business Analyst"
        mock_role2.description = "Business Analyst role"
        mock_role2.permissions = ["dashboard:read", "reports:read"]
        
        mock_user_service.get_all_roles.return_value = [mock_role1, mock_role2]
        
        response = client.get("/api/auth/roles", headers={
            "Authorization": "Bearer admin.token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "product_manager"
        assert data[1]["name"] == "business_analyst"
    
    def test_update_dashboard_preference(self, client, mock_user_service):
        """Test updating dashboard preference."""
        mock_user_service.update_user_dashboard_preference.return_value = True
        
        response = client.post("/api/auth/users/1/dashboard-preferences", json={
            "preference_key": "layout",
            "preference_value": {"theme": "dark", "sidebar": "collapsed"}
        }, headers={
            "Authorization": "Bearer user.token"
        })
        
        assert response.status_code == 200
        assert "updated" in response.json()["message"]
    
    def test_get_dashboard_preferences(self, client, mock_user_service):
        """Test getting dashboard preferences."""
        mock_user_service.get_user_dashboard_preferences.return_value = {
            "layout": {"theme": "dark"},
            "widgets": {"show_charts": True}
        }
        
        response = client.get("/api/auth/users/1/dashboard-preferences", headers={
            "Authorization": "Bearer user.token"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["layout"]["theme"] == "dark"
        assert data["widgets"]["show_charts"] is True


class TestRoleBasedAccessControl:
    """Test cases for role-based access control functionality."""
    
    @pytest.fixture
    def user_service(self):
        return UserService()
    
    def test_product_manager_permissions(self, user_service):
        """Test Product Manager role permissions."""
        with patch.object(user_service, 'get_user_permissions', return_value=[
            "dashboard:read", "dashboard:write", "users:read", "users:write",
            "reports:read", "reports:write", "notifications:read", "notifications:write", "export:read"
        ]):
            # Product Manager should have access to dashboard and user management
            assert user_service.has_permission(1, "dashboard:read")
            assert user_service.has_permission(1, "dashboard:write")
            assert user_service.has_permission(1, "users:read")
            assert user_service.has_permission(1, "users:write")
            assert user_service.has_permission(1, "reports:read")
            assert user_service.has_permission(1, "reports:write")
            
            # Product Manager should not have admin permissions
            assert not user_service.has_permission(1, "roles:write")
    
    def test_business_analyst_permissions(self, user_service):
        """Test Business Analyst role permissions."""
        with patch.object(user_service, 'get_user_permissions', return_value=[
            "dashboard:read", "reports:read", "notifications:read", "export:read"
        ]):
            # Business Analyst should have read access to dashboard and reports
            assert user_service.has_permission(1, "dashboard:read")
            assert user_service.has_permission(1, "reports:read")
            assert user_service.has_permission(1, "notifications:read")
            assert user_service.has_permission(1, "export:read")
            
            # Business Analyst should not have write permissions
            assert not user_service.has_permission(1, "dashboard:write")
            assert not user_service.has_permission(1, "users:write")
            assert not user_service.has_permission(1, "reports:write")
    
    def test_admin_permissions(self, user_service):
        """Test Administrator role permissions."""
        with patch.object(user_service, 'get_user_permissions', return_value=[
            "dashboard:read", "dashboard:write", "users:read", "users:write",
            "roles:read", "roles:write", "reports:read", "reports:write",
            "notifications:read", "notifications:write", "export:read", "export:write"
        ]):
            # Admin should have all permissions
            assert user_service.has_permission(1, "dashboard:read")
            assert user_service.has_permission(1, "dashboard:write")
            assert user_service.has_permission(1, "users:read")
            assert user_service.has_permission(1, "users:write")
            assert user_service.has_permission(1, "roles:read")
            assert user_service.has_permission(1, "roles:write")
            assert user_service.has_permission(1, "export:read")
            assert user_service.has_permission(1, "export:write")
    
    def test_permission_combinations(self, user_service):
        """Test permission combination checks."""
        with patch.object(user_service, 'get_user_permissions', return_value=[
            "dashboard:read", "users:read", "reports:read"
        ]):
            # Test has_any_permission
            assert user_service.has_any_permission(1, ["dashboard:read", "admin:write"])
            assert user_service.has_any_permission(1, ["users:read", "reports:read"])
            assert not user_service.has_any_permission(1, ["admin:write", "roles:write"])
            
            # Test has_all_permissions
            assert user_service.has_all_permissions(1, ["dashboard:read", "users:read"])
            assert not user_service.has_all_permissions(1, ["dashboard:read", "admin:write"])


class TestUserPreferences:
    """Test cases for user preferences functionality."""
    
    @pytest.fixture
    def user_service(self):
        return UserService()
    
    @patch('src.auth.user_service.get_db_session')
    def test_notification_preferences(self, mock_get_session, user_service, mock_session):
        """Test notification preferences management."""
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Test creating notification preference
        success = user_service.update_user_notification_preference(
            user_id=1,
            notification_type="email",
            change_severity="critical",
            frequency="immediate",
            is_enabled=True
        )
        
        assert success
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
        
        # Test getting notification preferences
        mock_pref = UserNotificationPreference(
            id=1,
            user_id=1,
            notification_type="email",
            change_severity="critical",
            frequency="immediate",
            is_enabled=True
        )
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_pref]
        
        prefs = user_service.get_user_notification_preferences(1)
        
        assert len(prefs) == 1
        assert prefs[0]["notification_type"] == "email"
        assert prefs[0]["change_severity"] == "critical"
        assert prefs[0]["frequency"] == "immediate"
        assert prefs[0]["is_enabled"] is True
    
    @patch('src.auth.user_service.get_db_session')
    def test_get_users_for_notification(self, mock_get_session, user_service, mock_session):
        """Test getting users for specific notifications."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_user]
        
        users = user_service.get_users_for_notification("email", "critical")
        
        assert len(users) == 1
        assert users[0].username == "testuser"
        assert users[0].email == "test@example.com"


if __name__ == "__main__":
    pytest.main([__file__]) 