"""
Tests for Notification Management API

This module contains comprehensive tests for the notification management API endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.notifications.history_manager import NotificationHistoryManager
from src.database.models import User, Notification, FormChange, Form, Agency


class TestNotificationManagementAPI:
    """Test cases for notification management API endpoints."""
    
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
        notification.sent_at = datetime.now(timezone.utc)
        notification.status = "delivered"
        notification.error_message = None
        notification.retry_count = 0
        notification.delivery_time = 2.5
        notification.response_data = {"status": "success"}
        notification.created_at = datetime.now(timezone.utc)
        notification.updated_at = datetime.now(timezone.utc)
        return notification
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_notification_history_success(self, mock_manager_class, test_client, mock_user, mock_notification):
        """Test successful retrieval of notification history."""
        # Mock history manager
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
        response = test_client.get("/api/notification-management/history")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]["notifications"]) == 1
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_notification_history_with_filters(self, mock_manager_class, test_client, mock_user):
        """Test notification history retrieval with filters."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
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
        response = test_client.get("/api/notification-management/history?status=delivered&notification_type=email")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_search_notifications_success(self, mock_manager_class, test_client, mock_user):
        """Test successful notification search."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.search_notifications = AsyncMock(return_value={
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
        response = test_client.get("/api/notification-management/search?search_term=test")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert len(data["data"]["notifications"]) == 1
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_notification_analytics_success(self, mock_manager_class, test_client, mock_user):
        """Test successful retrieval of notification analytics."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.get_analytics = AsyncMock(return_value={
            "delivery_rate": 0.95,
            "total_notifications": 100,
            "delivered": 95,
            "failed": 5,
            "avg_delivery_time": 2.5
        })
        
        # Test
        response = test_client.get("/api/notification-management/analytics")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "delivery_rate" in data["data"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_resend_notification_success(self, mock_manager_class, test_client, mock_user):
        """Test successful notification resend."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.resend_notification = AsyncMock(return_value=True)
        
        # Test
        response = test_client.post("/api/notification-management/resend/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_resend_notification_invalid_status(self, mock_manager_class, test_client, mock_user):
        """Test resend notification with invalid status."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method to raise an exception
        mock_manager.resend_notification = AsyncMock(side_effect=ValueError("Cannot resend delivered notification"))
        
        # Test
        response = test_client.post("/api/notification-management/resend/1")
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Cannot resend delivered notification" in data["detail"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_cancel_notification_success(self, mock_manager_class, test_client, mock_user):
        """Test successful notification cancellation."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.cancel_notification = AsyncMock(return_value=True)
        
        # Test
        response = test_client.post("/api/notification-management/cancel/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_bulk_operations_success(self, mock_manager_class, test_client, mock_user):
        """Test successful bulk operations."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.perform_bulk_operation = AsyncMock(return_value={
            "success_count": 5,
            "failed_count": 0,
            "results": []
        })
        
        # Test
        response = test_client.post(
            "/api/notification-management/bulk-operations",
            json={
                "operation": "resend",
                "notification_ids": [1, 2, 3, 4, 5]
            }
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success_count"] == 5
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_bulk_operations_invalid_operation(self, mock_manager_class, test_client, mock_user):
        """Test bulk operations with invalid operation."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method to raise an exception
        mock_manager.perform_bulk_operation = AsyncMock(side_effect=ValueError("Invalid operation"))
        
        # Test
        response = test_client.post(
            "/api/notification-management/bulk-operations",
            json={
                "operation": "invalid",
                "notification_ids": [1, 2, 3]
            }
        )
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Invalid operation" in data["detail"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_user_notification_preferences_success(self, mock_manager_class, test_client, mock_user):
        """Test successful retrieval of user notification preferences."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.get_user_preferences = AsyncMock(return_value={
            "email_enabled": True,
            "slack_enabled": False,
            "frequency": "immediate",
            "severity_filter": ["high", "critical"]
        })
        
        # Test
        response = test_client.get("/api/notification-management/user-preferences/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["email_enabled"] is True
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_user_notification_preferences_insufficient_permissions(self, mock_manager_class, test_client, mock_user):
        """Test getting user preferences with insufficient permissions."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method to raise an exception
        mock_manager.get_user_preferences = AsyncMock(side_effect=PermissionError("Insufficient permissions"))
        
        # Test
        response = test_client.get("/api/notification-management/user-preferences/2")
        
        # Assertions
        assert response.status_code == 403
        data = response.json()
        assert "Insufficient permissions" in data["detail"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_export_notification_history_csv(self, mock_manager_class, test_client, mock_user):
        """Test successful CSV export of notification history."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.export_history = AsyncMock(return_value="csv_data")
        
        # Test
        response = test_client.get("/api/notification-management/export?format=csv")
        
        # Assertions
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv"
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_export_notification_history_invalid_format(self, mock_manager_class, test_client, mock_user):
        """Test export with invalid format."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method to raise an exception
        mock_manager.export_history = AsyncMock(side_effect=ValueError("Unsupported format"))
        
        # Test
        response = test_client.get("/api/notification-management/export?format=invalid")
        
        # Assertions
        assert response.status_code == 400
        data = response.json()
        assert "Unsupported format" in data["detail"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_filter_options_success(self, mock_manager_class, test_client, mock_user):
        """Test successful retrieval of filter options."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.get_filter_options = AsyncMock(return_value={
            "statuses": ["delivered", "failed", "pending"],
            "notification_types": ["email", "slack", "sms"],
            "agencies": ["Agency 1", "Agency 2"],
            "forms": ["Form 1", "Form 2"]
        })
        
        # Test
        response = test_client.get("/api/notification-management/filters/options")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "statuses" in data["data"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_management_stats_summary_success(self, mock_manager_class, test_client, mock_user):
        """Test successful retrieval of management stats summary."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.get_stats_summary = AsyncMock(return_value={
            "total_notifications": 1000,
            "delivery_rate": 0.95,
            "avg_response_time": 2.5,
            "top_recipients": ["user1@example.com", "user2@example.com"]
        })
        
        # Test
        response = test_client.get("/api/notification-management/stats/summary")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "total_notifications" in data["data"]
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_notification_details_success(self, mock_manager_class, test_client, mock_user):
        """Test successful retrieval of notification details."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method
        mock_manager.get_notification_details = AsyncMock(return_value={
            "id": 1,
            "notification_type": "email",
            "recipient": "test@example.com",
            "subject": "Test Notification",
            "message": "Test message",
            "status": "delivered",
            "sent_at": "2023-01-01T12:00:00Z",
            "delivery_time": 2.5,
            "retry_count": 0,
            "error_message": None,
            "response_data": {"status": "success"},
            "form_change": {
                "id": 1,
                "form_name": "Test Form",
                "agency_name": "Test Agency",
                "change_type": "update",
                "change_description": "Test change"
            }
        })
        
        # Test
        response = test_client.get("/api/notification-management/notifications/1/details")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["id"] == 1
        assert data["data"]["notification_type"] == "email"
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_get_notification_details_not_found(self, mock_manager_class, test_client, mock_user):
        """Test getting notification details for non-existent notification."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method to raise an exception
        mock_manager.get_notification_details = AsyncMock(side_effect=ValueError("Notification not found"))
        
        # Test
        response = test_client.get("/api/notification-management/notifications/999/details")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Notification not found" in data["detail"]


class TestNotificationManagementAPIIntegration:
    """Integration tests for notification management API."""
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_full_notification_management_workflow(self, mock_manager_class, test_client, mock_user):
        """Test full notification management workflow."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock all async methods
        mock_manager.get_notification_history = AsyncMock(return_value={
            "notifications": [{"id": 1, "status": "delivered"}],
            "pagination": {"page": 1, "total_count": 1}
        })
        mock_manager.search_notifications = AsyncMock(return_value={
            "notifications": [{"id": 1, "status": "delivered"}],
            "pagination": {"page": 1, "total_count": 1}
        })
        mock_manager.get_analytics = AsyncMock(return_value={
            "delivery_rate": 0.95,
            "total_notifications": 100
        })
        mock_manager.resend_notification = AsyncMock(return_value=True)
        mock_manager.cancel_notification = AsyncMock(return_value=True)
        mock_manager.perform_bulk_operation = AsyncMock(return_value={
            "success_count": 1,
            "failed_count": 0
        })
        
        # Test workflow
        # 1. Get history
        response1 = test_client.get("/api/notification-management/history")
        assert response1.status_code == 200
        
        # 2. Search notifications
        response2 = test_client.get("/api/notification-management/search?search_term=test")
        assert response2.status_code == 200
        
        # 3. Get analytics
        response3 = test_client.get("/api/notification-management/analytics")
        assert response3.status_code == 200
        
        # 4. Resend notification
        response4 = test_client.post("/api/notification-management/resend/1")
        assert response4.status_code == 200
        
        # 5. Cancel notification
        response5 = test_client.post("/api/notification-management/cancel/1")
        assert response5.status_code == 200
        
        # 6. Bulk operations
        response6 = test_client.post(
            "/api/notification-management/bulk-operations",
            json={"operation": "resend", "notification_ids": [1]}
        )
        assert response6.status_code == 200
    
    @patch('src.api.notification_management.NotificationHistoryManager')
    def test_error_handling(self, mock_manager_class, test_client, mock_user):
        """Test error handling in notification management API."""
        # Mock history manager
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        
        # Mock the async method to raise an exception
        mock_manager.get_notification_history = AsyncMock(side_effect=Exception("Database error"))
        
        # Test
        response = test_client.get("/api/notification-management/history")
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"] 