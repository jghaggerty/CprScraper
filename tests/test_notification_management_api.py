"""
Tests for Notification Management API

This module contains comprehensive tests for the notification management API endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.notifications.history_manager import NotificationHistoryManager
from src.database.models import User, Notification, FormChange, Form, Agency

client = TestClient(app)


class TestNotificationManagementAPI:
    """Test cases for notification management API endpoints."""
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.is_superuser = True
        return user
    
    @pytest.fixture
    def mock_notification(self):
        """Create a mock notification for testing."""
        notification = Mock(spec=Notification)
        notification.id = 1
        notification.form_change_id = 1
        notification.notification_type = "email"
        notification.recipient = "test@example.com"
        notification.subject = "Test Notification"
        notification.message = "Test message"
        notification.sent_at = datetime.utcnow()
        notification.status = "delivered"
        notification.error_message = None
        notification.retry_count = 0
        notification.delivery_time = 2.5
        notification.response_data = {"status": "success"}
        notification.created_at = datetime.utcnow()
        notification.updated_at = datetime.utcnow()
        return notification
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_notification_history_success(self, mock_get_db, mock_get_current_user, mock_user, mock_notification):
        """Test successful retrieval of notification history."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock the async method
            mock_manager.get_notification_history = AsyncMock(return_value={
                "notifications": [{
                    "id": 1,
                    "notification_type": "email",
                    "recipient": "test@example.com",
                    "status": "delivered"
                }],
                "pagination": {
                    "page": 1,
                    "page_size": 50,
                    "total_count": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False
                }
            })
            
            # Test
            response = client.get("/api/notification-management/history")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
            assert len(data["data"]["notifications"]) == 1
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_notification_history_with_filters(self, mock_get_db, mock_get_current_user, mock_user):
        """Test notification history retrieval with filters."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_notification_history = AsyncMock(return_value={
                "notifications": [],
                "pagination": {
                    "page": 1,
                    "page_size": 50,
                    "total_count": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            })
            
            # Test with filters
            response = client.get("/api/notification-management/history?status=delivered&notification_type=email")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_search_notifications_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful notification search."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.search_notifications = AsyncMock(return_value={
                "notifications": [{
                    "id": 1,
                    "notification_type": "email",
                    "recipient": "test@example.com",
                    "status": "delivered"
                }],
                "search_term": "test",
                "search_fields": ["recipient", "subject", "message", "error_message"],
                "pagination": {
                    "page": 1,
                    "page_size": 50,
                    "total_count": 1,
                    "total_pages": 1,
                    "has_next": False,
                    "has_prev": False
                }
            })
            
            # Test
            response = client.get("/api/notification-management/search?search_term=test")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["search_term"] == "test"
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_notification_analytics_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful retrieval of notification analytics."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_notification_analytics = AsyncMock(return_value={
                "overview": {
                    "total_notifications": 100,
                    "delivered_count": 80,
                    "failed_count": 20,
                    "success_rate": 80.0,
                    "average_delivery_time_seconds": 2.5
                },
                "status_distribution": [
                    {"status": "delivered", "count": 80},
                    {"status": "failed", "count": 20}
                ],
                "channel_distribution": [
                    {"channel": "email", "count": 60},
                    {"channel": "slack", "count": 40}
                ],
                "time_trends": [
                    {"time_period": "2024-01-01", "count": 10},
                    {"time_period": "2024-01-02", "count": 15}
                ],
                "top_recipients": [
                    {"recipient": "user1@example.com", "count": 25},
                    {"recipient": "user2@example.com", "count": 20}
                ]
            })
            
            # Test
            response = client.get("/api/notification-management/analytics")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "overview" in data["data"]
            assert data["data"]["overview"]["total_notifications"] == 100
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_resend_notification_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful notification resend."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.resend_notification = AsyncMock(return_value={
                "success": True,
                "original_notification_id": 1,
                "new_notification_id": 2,
                "resend_success": True
            })
            
            # Test
            response = client.post("/api/notification-management/resend/1")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["original_notification_id"] == 1
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_resend_notification_invalid_status(self, mock_get_db, mock_get_current_user, mock_user):
        """Test resend notification with invalid status."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.resend_notification = AsyncMock(side_effect=ValueError("Cannot resend notification with status 'delivered'"))
            
            # Test
            response = client.post("/api/notification-management/resend/1")
            
            # Assertions
            assert response.status_code == 400
            data = response.json()
            assert "Cannot resend notification" in data["detail"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_cancel_notification_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful notification cancellation."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.cancel_notification = AsyncMock(return_value={
                "success": True,
                "notification_id": 1,
                "status": "cancelled",
                "cancelled_by": "testuser",
                "cancelled_at": datetime.utcnow().isoformat()
            })
            
            # Test
            response = client.post("/api/notification-management/cancel/1", json={"reason": "Test cancellation"})
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "cancelled"
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_bulk_operations_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful bulk operations."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.bulk_operations = AsyncMock(return_value={
                "operation": "resend",
                "total_requested": 3,
                "successful": 2,
                "failed": 1,
                "errors": ["Failed to resend notification 3"]
            })
            
            # Test
            response = client.post("/api/notification-management/bulk-operations", json={
                "operation": "resend",
                "notification_ids": [1, 2, 3]
            })
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["operation"] == "resend"
            assert data["data"]["successful"] == 2
            assert data["data"]["failed"] == 1
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_bulk_operations_invalid_operation(self, mock_get_db, mock_get_current_user, mock_user):
        """Test bulk operations with invalid operation."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Test
        response = client.post("/api/notification-management/bulk-operations", json={
            "operation": "invalid",
            "notification_ids": [1, 2, 3]
        })
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid operation" in data["detail"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_user_notification_preferences_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful retrieval of user notification preferences."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_user_notification_preferences = AsyncMock(return_value={
                "user": {
                    "id": 1,
                    "username": "testuser",
                    "email": "test@example.com",
                    "first_name": "Test",
                    "last_name": "User"
                },
                "roles": [
                    {
                        "id": 1,
                        "name": "product_manager",
                        "display_name": "Product Manager"
                    }
                ],
                "notification_preferences": [
                    {
                        "id": 1,
                        "notification_type": "email",
                        "change_severity": "high",
                        "frequency": "immediate",
                        "is_enabled": True
                    }
                ]
            })
            
            # Test
            response = client.get("/api/notification-management/user-preferences/1")
            
            # Assertions
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "user" in data["data"]
            assert "roles" in data["data"]
            assert "notification_preferences" in data["data"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_user_notification_preferences_insufficient_permissions(self, mock_get_db, mock_get_current_user, mock_user):
        """Test user notification preferences with insufficient permissions."""
        # Mock user without superuser privileges
        mock_user.is_superuser = False
        mock_user.id = 2  # Different user ID
        
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Test accessing another user's preferences
        response = client.get("/api/notification-management/user-preferences/1")
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient permissions" in data["detail"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_export_notification_history_csv(self, mock_get_db, mock_get_current_user, mock_user):
        """Test CSV export of notification history."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.export_notification_history = AsyncMock(return_value={
                "format": "csv",
                "data": "id,notification_type,recipient,status\n1,email,test@example.com,delivered",
                "filename": "notification_history_20240101_120000.csv"
            })
            
            # Test
            response = client.get("/api/notification-management/export?format=csv")
            
            # Assertions
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/csv"
            assert "attachment" in response.headers["content-disposition"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_export_notification_history_invalid_format(self, mock_get_db, mock_get_current_user, mock_user):
        """Test export with invalid format."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Test
        response = client.get("/api/notification-management/export?format=invalid")
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid format" in data["detail"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_filter_options_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful retrieval of filter options."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock database queries
        mock_agency = Mock(spec=Agency)
        mock_agency.id = 1
        mock_agency.name = "Department of Labor"
        mock_agency.abbreviation = "DOL"
        
        mock_form = Mock(spec=Form)
        mock_form.id = 1
        mock_form.name = "WH-347"
        mock_form.title = "Statement of Compliance"
        
        mock_db.query().filter().all.side_effect = [
            [mock_agency],  # agencies
            [mock_form]     # forms
        ]
        
        # Test
        response = client.get("/api/notification-management/filters/options")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "statuses" in data["data"]
        assert "notification_types" in data["data"]
        assert "agencies" in data["data"]
        assert "forms" in data["data"]
        assert "severities" in data["data"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_management_stats_summary_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful retrieval of management stats summary."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock database queries
        mock_db.query().scalar.side_effect = [
            1000,  # total_notifications
            50,    # pending_count
            100,   # failed_count
            25,    # retrying_count
            200,   # recent_count
            2.5    # avg_delivery_time
        ]
        
        # Test
        response = client.get("/api/notification-management/stats/summary")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_notifications" in data["data"]
        assert "pending_count" in data["data"]
        assert "failed_count" in data["data"]
        assert "retrying_count" in data["data"]
        assert "recent_24h_count" in data["data"]
        assert "average_delivery_time_seconds" in data["data"]
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_notification_details_success(self, mock_get_db, mock_get_current_user, mock_user):
        """Test successful retrieval of notification details."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock notification
        mock_notification = Mock(spec=Notification)
        mock_notification.id = 1
        mock_notification.form_change_id = 1
        mock_notification.notification_type = "email"
        mock_notification.recipient = "test@example.com"
        mock_notification.subject = "Test"
        mock_notification.message = "Test message"
        mock_notification.sent_at = datetime.utcnow()
        mock_notification.status = "delivered"
        mock_notification.error_message = None
        mock_notification.retry_count = 0
        mock_notification.delivery_time = 2.5
        mock_notification.response_data = {"status": "success"}
        mock_notification.created_at = datetime.utcnow()
        mock_notification.updated_at = datetime.utcnow()
        
        # Mock form change
        mock_form_change = Mock(spec=FormChange)
        mock_form_change.id = 1
        mock_form_change.change_type = "content"
        mock_form_change.change_description = "Test change"
        mock_form_change.old_value = "old"
        mock_form_change.new_value = "new"
        mock_form_change.severity = "medium"
        mock_form_change.detected_at = datetime.utcnow()
        mock_form_change.ai_confidence_score = 85
        mock_form_change.ai_change_category = "form_update"
        
        # Mock form
        mock_form = Mock(spec=Form)
        mock_form.id = 1
        mock_form.name = "WH-347"
        mock_form.title = "Statement of Compliance"
        mock_form.form_url = "https://example.com/form"
        
        # Mock agency
        mock_agency = Mock(spec=Agency)
        mock_agency.id = 1
        mock_agency.name = "Department of Labor"
        mock_agency.abbreviation = "DOL"
        mock_agency.agency_type = "federal"
        
        # Mock database queries
        mock_db.query().filter().first.side_effect = [
            mock_notification,  # notification
            mock_form_change,   # form_change
            mock_form,          # form
            mock_agency         # agency
        ]
        
        # Test
        response = client.get("/api/notification-management/notifications/1/details")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "notification" in data["data"]
        assert "form_change" in data["data"]
        assert "form" in data["data"]
        assert "agency" in data["data"]
        assert data["data"]["notification"]["id"] == 1
        assert data["data"]["notification"]["notification_type"] == "email"
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_get_notification_details_not_found(self, mock_get_db, mock_get_current_user, mock_user):
        """Test notification details when notification not found."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock no notification found
        mock_db.query().filter().first.return_value = None
        
        # Test
        response = client.get("/api/notification-management/notifications/999/details")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Notification not found" in data["detail"]


class TestNotificationManagementAPIIntegration:
    """Integration tests for notification management API."""
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_full_notification_management_workflow(self, mock_get_db, mock_get_current_user, mock_user):
        """Test full notification management workflow."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_db = Mock()
        mock_get_db.return_value = mock_db
        
        # Mock history manager for all operations
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock all async methods
            mock_manager.get_notification_history = AsyncMock(return_value={
                "notifications": [{"id": 1, "status": "failed"}],
                "pagination": {"page": 1, "total_count": 1}
            })
            
            mock_manager.resend_notification = AsyncMock(return_value={
                "success": True,
                "original_notification_id": 1,
                "new_notification_id": 2
            })
            
            mock_manager.cancel_notification = AsyncMock(return_value={
                "success": True,
                "notification_id": 3,
                "status": "cancelled"
            })
            
            mock_manager.bulk_operations = AsyncMock(return_value={
                "operation": "resend",
                "total_requested": 2,
                "successful": 2,
                "failed": 0
            })
            
            mock_manager.get_notification_analytics = AsyncMock(return_value={
                "overview": {"total_notifications": 100, "success_rate": 85.0}
            })
            
            # Test workflow
            # 1. Get notification history
            response1 = client.get("/api/notification-management/history")
            assert response1.status_code == 200
            
            # 2. Resend a failed notification
            response2 = client.post("/api/notification-management/resend/1")
            assert response2.status_code == 200
            
            # 3. Cancel a pending notification
            response3 = client.post("/api/notification-management/cancel/3", json={"reason": "Test"})
            assert response3.status_code == 200
            
            # 4. Perform bulk operations
            response4 = client.post("/api/notification-management/bulk-operations", json={
                "operation": "resend",
                "notification_ids": [1, 2]
            })
            assert response4.status_code == 200
            
            # 5. Get analytics
            response5 = client.get("/api/notification-management/analytics")
            assert response5.status_code == 200
    
    @patch('src.api.notification_management.get_current_user')
    @patch('src.api.notification_management.get_db')
    def test_error_handling(self, mock_get_db, mock_get_current_user, mock_user):
        """Test error handling in notification management API."""
        # Mock dependencies
        mock_get_current_user.return_value = mock_user
        mock_get_db.return_value = Mock()
        
        # Mock history manager with error
        with patch('src.api.notification_management.NotificationHistoryManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.get_notification_history = AsyncMock(side_effect=Exception("Database error"))
            
            # Test
            response = client.get("/api/notification-management/history")
            
            # Assertions
            assert response.status_code == 500
            data = response.json()
            assert "Error retrieving notification history" in data["detail"] 