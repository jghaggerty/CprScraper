"""
Unit tests for NotificationHistoryManager

This module contains comprehensive tests for the notification history and management functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from ..notifications.history_manager import NotificationHistoryManager
from ..database.models import (
    Notification, FormChange, User, UserRole, Role, 
    Agency, Form, UserNotificationPreference
)


class TestNotificationHistoryManager:
    """Test cases for NotificationHistoryManager."""
    
    @pytest.fixture
    def history_manager(self):
        """Create a NotificationHistoryManager instance for testing."""
        return NotificationHistoryManager()
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification for testing."""
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
    def sample_form_change(self):
        """Create a sample form change for testing."""
        form_change = Mock(spec=FormChange)
        form_change.id = 1
        form_change.change_type = "content"
        form_change.change_description = "Test change"
        form_change.severity = "medium"
        form_change.detected_at = datetime.utcnow()
        return form_change
    
    @pytest.fixture
    def sample_form(self):
        """Create a sample form for testing."""
        form = Mock(spec=Form)
        form.id = 1
        form.name = "WH-347"
        form.title = "Statement of Compliance"
        return form
    
    @pytest.fixture
    def sample_agency(self):
        """Create a sample agency for testing."""
        agency = Mock(spec=Agency)
        agency.id = 1
        agency.name = "Department of Labor"
        agency.abbreviation = "DOL"
        return agency
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        return user
    
    @pytest.mark.asyncio
    async def test_get_notification_history_success(self, history_manager, mock_db, sample_notification):
        """Test successful retrieval of notification history."""
        # Mock database query
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_notification]
        
        mock_db.query.return_value = mock_query
        
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [None, None, None]
        
        # Test
        result = await history_manager.get_notification_history(
            db=mock_db,
            page=1,
            page_size=50
        )
        
        # Assertions
        assert result is not None
        assert "notifications" in result
        assert "pagination" in result
        assert len(result["notifications"]) == 1
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["total_count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_notification_history_with_filters(self, history_manager, mock_db, sample_notification):
        """Test notification history retrieval with filters."""
        # Mock database query
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_notification]
        
        mock_db.query.return_value = mock_query
        
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [None, None, None]
        
        # Test with filters
        filters = {
            "status": "delivered",
            "notification_type": "email",
            "recipient": "test@example.com"
        }
        
        result = await history_manager.get_notification_history(
            db=mock_db,
            filters=filters,
            page=1,
            page_size=50
        )
        
        # Assertions
        assert result is not None
        assert len(result["notifications"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_notifications_success(self, history_manager, mock_db, sample_notification):
        """Test successful notification search."""
        # Mock database query
        mock_query = Mock()
        mock_query.count.return_value = 1
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [sample_notification]
        
        mock_db.query.return_value = mock_query
        
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [None, None, None]
        
        # Test
        result = await history_manager.search_notifications(
            db=mock_db,
            search_term="test",
            page=1,
            page_size=50
        )
        
        # Assertions
        assert result is not None
        assert "notifications" in result
        assert "search_term" in result
        assert result["search_term"] == "test"
    
    @pytest.mark.asyncio
    async def test_get_notification_analytics_success(self, history_manager, mock_db):
        """Test successful retrieval of notification analytics."""
        # Mock database queries
        mock_query = Mock()
        mock_query.count.return_value = 100
        mock_query.filter.return_value = mock_query
        
        mock_db.query.return_value = mock_query
        
        # Mock aggregation queries
        mock_db.query().filter().group_by().all.side_effect = [
            [("delivered", 80), ("failed", 20)],  # status_distribution
            [("email", 60), ("slack", 40)],       # channel_distribution
            [("2024-01-01", 10), ("2024-01-02", 15)],  # time_trends
            [("user1@example.com", 25), ("user2@example.com", 20)]  # top_recipients
        ]
        
        mock_db.query().filter().scalar.return_value = 2.5  # avg_delivery_time
        
        # Test
        result = await history_manager.get_notification_analytics(
            db=mock_db,
            start_date=datetime.utcnow() - timedelta(days=7),
            end_date=datetime.utcnow()
        )
        
        # Assertions
        assert result is not None
        assert "overview" in result
        assert "status_distribution" in result
        assert "channel_distribution" in result
        assert "time_trends" in result
        assert "top_recipients" in result
        assert result["overview"]["total_notifications"] == 100
        assert result["overview"]["success_rate"] == 80.0
    
    @pytest.mark.asyncio
    async def test_resend_notification_success(self, history_manager, mock_db, sample_notification, sample_user):
        """Test successful notification resend."""
        # Mock original notification
        mock_db.query().filter().first.return_value = sample_notification
        
        # Mock new notification creation
        new_notification = Mock(spec=Notification)
        new_notification.id = 2
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock delivery tracker
        history_manager.delivery_tracker.track_notification_delivery = AsyncMock(return_value=True)
        
        # Test
        result = await history_manager.resend_notification(
            db=mock_db,
            notification_id=1,
            user=sample_user
        )
        
        # Assertions
        assert result is not None
        assert result["success"] is True
        assert result["original_notification_id"] == 1
        assert result["new_notification_id"] == 2
    
    @pytest.mark.asyncio
    async def test_resend_notification_invalid_status(self, history_manager, mock_db, sample_user):
        """Test resend notification with invalid status."""
        # Mock notification with invalid status
        notification = Mock(spec=Notification)
        notification.status = "delivered"  # Cannot resend delivered notifications
        
        mock_db.query().filter().first.return_value = notification
        
        # Test
        with pytest.raises(ValueError, match="Cannot resend notification with status 'delivered'"):
            await history_manager.resend_notification(
                db=mock_db,
                notification_id=1,
                user=sample_user
            )
    
    @pytest.mark.asyncio
    async def test_cancel_notification_success(self, history_manager, mock_db, sample_user):
        """Test successful notification cancellation."""
        # Mock notification
        notification = Mock(spec=Notification)
        notification.status = "pending"
        
        mock_db.query().filter().first.return_value = notification
        mock_db.commit.return_value = None
        
        # Test
        result = await history_manager.cancel_notification(
            db=mock_db,
            notification_id=1,
            user=sample_user,
            reason="Test cancellation"
        )
        
        # Assertions
        assert result is not None
        assert result["success"] is True
        assert result["notification_id"] == 1
        assert result["status"] == "cancelled"
        assert result["cancelled_by"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_cancel_notification_invalid_status(self, history_manager, mock_db, sample_user):
        """Test cancel notification with invalid status."""
        # Mock notification with invalid status
        notification = Mock(spec=Notification)
        notification.status = "delivered"  # Cannot cancel delivered notifications
        
        mock_db.query().filter().first.return_value = notification
        
        # Test
        with pytest.raises(ValueError, match="Cannot cancel notification with status 'delivered'"):
            await history_manager.cancel_notification(
                db=mock_db,
                notification_id=1,
                user=sample_user
            )
    
    @pytest.mark.asyncio
    async def test_bulk_operations_success(self, history_manager, mock_db, sample_user):
        """Test successful bulk operations."""
        # Mock notifications for bulk operations
        notifications = []
        for i in range(3):
            notification = Mock(spec=Notification)
            notification.id = i + 1
            notification.status = "failed"
            notifications.append(notification)
        
        mock_db.query().filter().first.side_effect = notifications
        mock_db.commit.return_value = None
        
        # Mock delivery tracker
        history_manager.delivery_tracker.track_notification_delivery = AsyncMock(return_value=True)
        
        # Test bulk resend
        result = await history_manager.bulk_operations(
            db=mock_db,
            operation="resend",
            notification_ids=[1, 2, 3],
            user=sample_user
        )
        
        # Assertions
        assert result is not None
        assert result["operation"] == "resend"
        assert result["total_requested"] == 3
        assert result["successful"] == 3
        assert result["failed"] == 0
    
    @pytest.mark.asyncio
    async def test_get_user_notification_preferences_success(self, history_manager, mock_db, sample_user):
        """Test successful retrieval of user notification preferences."""
        # Mock user
        mock_db.query().filter().first.return_value = sample_user
        
        # Mock user roles
        user_role = Mock(spec=UserRole)
        user_role.role = Mock(spec=Role)
        user_role.role.id = 1
        user_role.role.name = "product_manager"
        user_role.role.display_name = "Product Manager"
        
        mock_db.query().join().filter().all.return_value = [user_role]
        
        # Mock notification preferences
        preference = Mock(spec=UserNotificationPreference)
        preference.id = 1
        preference.notification_type = "email"
        preference.change_severity = "high"
        preference.frequency = "immediate"
        preference.is_enabled = True
        
        mock_db.query().filter().all.return_value = [preference]
        
        # Test
        result = await history_manager.get_user_notification_preferences(
            db=mock_db,
            user_id=1
        )
        
        # Assertions
        assert result is not None
        assert "user" in result
        assert "roles" in result
        assert "notification_preferences" in result
        assert result["user"]["id"] == 1
        assert len(result["roles"]) == 1
        assert len(result["notification_preferences"]) == 1
    
    @pytest.mark.asyncio
    async def test_export_notification_history_csv(self, history_manager, mock_db, sample_notification):
        """Test CSV export of notification history."""
        # Mock database query
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_notification]
        
        mock_db.query.return_value = mock_query
        
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [None, None, None]
        
        # Test
        result = await history_manager.export_notification_history(
            db=mock_db,
            format="csv"
        )
        
        # Assertions
        assert result is not None
        assert result["format"] == "csv"
        assert "data" in result
        assert "filename" in result
        assert result["filename"].endswith(".csv")
    
    @pytest.mark.asyncio
    async def test_export_notification_history_json(self, history_manager, mock_db, sample_notification):
        """Test JSON export of notification history."""
        # Mock database query
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_notification]
        
        mock_db.query.return_value = mock_query
        
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [None, None, None]
        
        # Test
        result = await history_manager.export_notification_history(
            db=mock_db,
            format="json"
        )
        
        # Assertions
        assert result is not None
        assert result["format"] == "json"
        assert "data" in result
        assert "filename" in result
        assert result["filename"].endswith(".json")
    
    @pytest.mark.asyncio
    async def test_export_notification_history_excel(self, history_manager, mock_db, sample_notification):
        """Test Excel export of notification history."""
        # Mock database query
        mock_query = Mock()
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [sample_notification]
        
        mock_db.query.return_value = mock_query
        
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [None, None, None]
        
        # Test
        result = await history_manager.export_notification_history(
            db=mock_db,
            format="excel"
        )
        
        # Assertions
        assert result is not None
        assert result["format"] == "excel"
        assert "data" in result
        assert "filename" in result
        assert result["filename"].endswith(".xlsx")
    
    @pytest.mark.asyncio
    async def test_export_notification_history_invalid_format(self, history_manager, mock_db):
        """Test export with invalid format."""
        # Test
        with pytest.raises(ValueError, match="Unsupported export format: invalid"):
            await history_manager.export_notification_history(
                db=mock_db,
                format="invalid"
            )
    
    @pytest.mark.asyncio
    async def test_format_notification_data_with_related_data(self, history_manager, mock_db, 
                                                             sample_notification, sample_form_change, 
                                                             sample_form, sample_agency):
        """Test formatting notification data with related data."""
        # Mock related data queries
        mock_db.query().filter().first.side_effect = [
            sample_form_change,  # form_change
            sample_form,         # form
            sample_agency        # agency
        ]
        
        # Test
        result = await history_manager._format_notification_data(sample_notification, mock_db)
        
        # Assertions
        assert result is not None
        assert result["id"] == 1
        assert result["notification_type"] == "email"
        assert result["recipient"] == "test@example.com"
        assert result["form_change"] is not None
        assert result["form"] is not None
        assert result["agency"] is not None
        assert result["form_change"]["change_type"] == "content"
        assert result["form"]["name"] == "WH-347"
        assert result["agency"]["name"] == "Department of Labor"
    
    @pytest.mark.asyncio
    async def test_format_notification_data_without_related_data(self, history_manager, mock_db, sample_notification):
        """Test formatting notification data without related data."""
        # Mock no related data
        mock_db.query().filter().first.return_value = None
        
        # Test
        result = await history_manager._format_notification_data(sample_notification, mock_db)
        
        # Assertions
        assert result is not None
        assert result["id"] == 1
        assert result["form_change"] is None
        assert result["form"] is None
        assert result["agency"] is None
    
    def test_apply_filters_status(self, history_manager):
        """Test applying status filter."""
        # Mock query
        mock_query = Mock()
        
        # Test
        result = history_manager._apply_filters(mock_query, {"status": "delivered"})
        
        # Assertions
        assert result == mock_query
        mock_query.filter.assert_called()
    
    def test_apply_filters_multiple_statuses(self, history_manager):
        """Test applying multiple status filters."""
        # Mock query
        mock_query = Mock()
        
        # Test
        result = history_manager._apply_filters(mock_query, {"status": ["delivered", "failed"]})
        
        # Assertions
        assert result == mock_query
        mock_query.filter.assert_called()
    
    def test_apply_filters_recipient(self, history_manager):
        """Test applying recipient filter."""
        # Mock query
        mock_query = Mock()
        
        # Test
        result = history_manager._apply_filters(mock_query, {"recipient": "test@example.com"})
        
        # Assertions
        assert result == mock_query
        mock_query.filter.assert_called()
    
    def test_apply_filters_date_range(self, history_manager):
        """Test applying date range filters."""
        # Mock query
        mock_query = Mock()
        
        # Test
        filters = {
            "start_date": datetime.utcnow() - timedelta(days=7),
            "end_date": datetime.utcnow()
        }
        result = history_manager._apply_filters(mock_query, filters)
        
        # Assertions
        assert result == mock_query
        assert mock_query.filter.call_count == 2  # Two date filters
    
    def test_apply_filters_agency_and_form(self, history_manager):
        """Test applying agency and form filters."""
        # Mock query
        mock_query = Mock()
        mock_query.join.return_value = mock_query
        
        # Test
        filters = {
            "agency_id": 1,
            "form_id": 1
        }
        result = history_manager._apply_filters(mock_query, filters)
        
        # Assertions
        assert result == mock_query
        mock_query.join.assert_called()
        mock_query.filter.assert_called()
    
    def test_apply_filters_retry_count(self, history_manager):
        """Test applying retry count filters."""
        # Mock query
        mock_query = Mock()
        
        # Test
        filters = {
            "retry_count_min": 1,
            "retry_count_max": 5
        }
        result = history_manager._apply_filters(mock_query, filters)
        
        # Assertions
        assert result == mock_query
        assert mock_query.filter.call_count == 2  # Two retry count filters


class TestNotificationHistoryManagerIntegration:
    """Integration tests for NotificationHistoryManager."""
    
    @pytest.mark.asyncio
    async def test_full_notification_lifecycle(self, history_manager, mock_db, sample_user):
        """Test full notification lifecycle from creation to management."""
        # Create a notification
        notification = Mock(spec=Notification)
        notification.id = 1
        notification.status = "failed"
        notification.form_change_id = 1
        notification.notification_type = "email"
        notification.recipient = "test@example.com"
        notification.subject = "Test"
        notification.message = "Test message"
        
        # Mock database operations
        mock_db.query().filter().first.return_value = notification
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Mock delivery tracker
        history_manager.delivery_tracker.track_notification_delivery = AsyncMock(return_value=True)
        
        # Test resend
        resend_result = await history_manager.resend_notification(
            db=mock_db,
            notification_id=1,
            user=sample_user
        )
        
        assert resend_result["success"] is True
        
        # Test cancellation of a pending notification
        pending_notification = Mock(spec=Notification)
        pending_notification.status = "pending"
        mock_db.query().filter().first.return_value = pending_notification
        
        cancel_result = await history_manager.cancel_notification(
            db=mock_db,
            notification_id=2,
            user=sample_user,
            reason="Test cancellation"
        )
        
        assert cancel_result["success"] is True
        assert cancel_result["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_bulk_operations_with_mixed_statuses(self, history_manager, mock_db, sample_user):
        """Test bulk operations with notifications in different statuses."""
        # Create notifications with different statuses
        failed_notification = Mock(spec=Notification)
        failed_notification.id = 1
        failed_notification.status = "failed"
        failed_notification.form_change_id = 1
        failed_notification.notification_type = "email"
        failed_notification.recipient = "test1@example.com"
        failed_notification.subject = "Test 1"
        failed_notification.message = "Test message 1"
        
        pending_notification = Mock(spec=Notification)
        pending_notification.id = 2
        pending_notification.status = "pending"
        
        mock_db.query().filter().first.side_effect = [failed_notification, pending_notification]
        mock_db.commit.return_value = None
        
        # Mock delivery tracker
        history_manager.delivery_tracker.track_notification_delivery = AsyncMock(return_value=True)
        
        # Test bulk resend (should only work for failed notifications)
        result = await history_manager.bulk_operations(
            db=mock_db,
            operation="resend",
            notification_ids=[1, 2],
            user=sample_user
        )
        
        assert result["successful"] == 1  # Only failed notification can be resent
        assert result["failed"] == 1      # Pending notification cannot be resent
    
    @pytest.mark.asyncio
    async def test_analytics_with_realistic_data(self, history_manager, mock_db):
        """Test analytics with realistic notification data."""
        # Mock realistic analytics data
        mock_query = Mock()
        mock_query.count.return_value = 1000
        mock_query.filter.return_value = mock_query
        
        mock_db.query.return_value = mock_query
        
        # Mock status distribution
        status_distribution = [
            ("delivered", 850),
            ("failed", 100),
            ("pending", 30),
            ("retrying", 20)
        ]
        
        # Mock channel distribution
        channel_distribution = [
            ("email", 700),
            ("slack", 200),
            ("teams", 100)
        ]
        
        # Mock time trends
        time_trends = [
            ("2024-01-01", 50),
            ("2024-01-02", 75),
            ("2024-01-03", 60)
        ]
        
        # Mock top recipients
        top_recipients = [
            ("user1@example.com", 150),
            ("user2@example.com", 120),
            ("user3@example.com", 100)
        ]
        
        mock_db.query().filter().group_by().all.side_effect = [
            status_distribution,
            channel_distribution,
            time_trends,
            top_recipients
        ]
        
        mock_db.query().filter().scalar.return_value = 3.2  # avg_delivery_time
        
        # Test analytics
        result = await history_manager.get_notification_analytics(
            db=mock_db,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow()
        )
        
        # Assertions
        assert result["overview"]["total_notifications"] == 1000
        assert result["overview"]["success_rate"] == 85.0  # 850/1000 * 100
        assert result["overview"]["average_delivery_time_seconds"] == 3.2
        assert len(result["status_distribution"]) == 4
        assert len(result["channel_distribution"]) == 3
        assert len(result["time_trends"]) == 3
        assert len(result["top_recipients"]) == 3 