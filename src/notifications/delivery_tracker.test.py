"""
Unit tests for notification delivery tracking and retry mechanisms.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

from src.notifications.delivery_tracker import (
    NotificationDeliveryTracker, 
    NotificationDeliveryAnalytics,
    DeliveryStatus, 
    RetryStrategy, 
    RetryConfig, 
    DeliveryMetrics
)
from src.notifications.channel_integration import NotificationResult
from src.database.models import Notification, FormChange, User


class TestDeliveryStatus:
    """Test delivery status enumeration."""
    
    def test_delivery_status_values(self):
        """Test that delivery status values are correct."""
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.SENDING.value == "sending"
        assert DeliveryStatus.DELIVERED.value == "delivered"
        assert DeliveryStatus.FAILED.value == "failed"
        assert DeliveryStatus.BOUNCED.value == "bounced"
        assert DeliveryStatus.RETRYING.value == "retrying"
        assert DeliveryStatus.EXPIRED.value == "expired"
        assert DeliveryStatus.CANCELLED.value == "cancelled"


class TestRetryConfig:
    """Test retry configuration."""
    
    def test_default_retry_config(self):
        """Test default retry configuration values."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.initial_delay_seconds == 60
        assert config.max_delay_seconds == 3600
        assert config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert config.backoff_multiplier == 2.0
    
    def test_custom_retry_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            initial_delay_seconds=30,
            max_delay_seconds=1800,
            strategy=RetryStrategy.LINEAR_BACKOFF,
            backoff_multiplier=1.5
        )
        
        assert config.max_retries == 5
        assert config.initial_delay_seconds == 30
        assert config.max_delay_seconds == 1800
        assert config.strategy == RetryStrategy.LINEAR_BACKOFF
        assert config.backoff_multiplier == 1.5


class TestNotificationDeliveryTracker:
    """Test notification delivery tracking functionality."""
    
    @pytest.fixture
    def tracker(self):
        """Create a delivery tracker instance."""
        config = RetryConfig(max_retries=2, initial_delay_seconds=1)
        return NotificationDeliveryTracker(config)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = Mock()
        session.query.return_value.filter.return_value.first.return_value = None
        session.commit.return_value = None
        return session
    
    @pytest.fixture
    def sample_notification(self):
        """Create a sample notification object."""
        notification = Mock(spec=Notification)
        notification.id = 123
        notification.status = DeliveryStatus.PENDING.value
        notification.retry_count = 0
        notification.error_message = None
        notification.subject = "Test Subject"
        notification.message = "Test Message"
        notification.notification_type = "email"
        notification.recipient = "test@example.com"
        return notification
    
    @pytest.fixture
    def sample_content(self):
        """Create sample notification content."""
        return {
            'subject': 'Test Notification',
            'message': 'This is a test notification',
            'recipient': 'test@example.com',
            'template_type': 'product_manager'
        }
    
    def test_tracker_initialization(self, tracker):
        """Test that tracker initializes correctly."""
        assert tracker is not None
        assert tracker.retry_config.max_retries == 2
        assert tracker.retry_config.initial_delay_seconds == 1
        assert len(tracker._active_retries) == 0
    
    @patch('src.notifications.delivery_tracker.get_db')
    @patch('src.notifications.delivery_tracker.NotificationDeliveryTracker._attempt_delivery')
    @patch('src.notifications.delivery_tracker.NotificationDeliveryTracker._update_notification_status')
    async def test_successful_delivery_tracking(self, mock_update_status, mock_attempt_delivery, 
                                             mock_get_db, tracker, mock_db_session, sample_content):
        """Test successful notification delivery tracking."""
        # Setup mocks
        mock_get_db.return_value = iter([mock_db_session])
        mock_attempt_delivery.return_value = NotificationResult(
            success=True,
            error_message=None,
            delivery_time=2.5,
            response_data={'message_id': 'test-123'}
        )
        
        # Execute
        result = await tracker.track_notification_delivery(
            notification_id=123,
            channel_type='email',
            recipient='test@example.com',
            content=sample_content
        )
        
        # Verify
        assert result.success is True
        assert result.delivery_time == 2.5
        assert result.response_data == {'message_id': 'test-123'}
        
        # Verify status updates were called
        assert mock_update_status.call_count >= 2  # SENDING and DELIVERED
    
    @patch('src.notifications.delivery_tracker.get_db')
    @patch('src.notifications.delivery_tracker.NotificationDeliveryTracker._attempt_delivery')
    @patch('src.notifications.delivery_tracker.NotificationDeliveryTracker._handle_delivery_failure')
    async def test_failed_delivery_tracking(self, mock_handle_failure, mock_attempt_delivery, 
                                          mock_get_db, tracker, mock_db_session, sample_content):
        """Test failed notification delivery tracking."""
        # Setup mocks
        mock_get_db.return_value = iter([mock_db_session])
        mock_attempt_delivery.return_value = NotificationResult(
            success=False,
            error_message='SMTP connection failed',
            delivery_time=None,
            response_data=None
        )
        
        # Execute
        result = await tracker.track_notification_delivery(
            notification_id=123,
            channel_type='email',
            recipient='test@example.com',
            content=sample_content
        )
        
        # Verify
        assert result.success is False
        assert result.error_message == 'SMTP connection failed'
        
        # Verify failure handling was called
        mock_handle_failure.assert_called_once()
    
    def test_retry_delay_calculation_immediate(self, tracker):
        """Test immediate retry delay calculation."""
        tracker.retry_config.strategy = RetryStrategy.IMMEDIATE
        delay = tracker._calculate_retry_delay(1)
        assert delay == 0
    
    def test_retry_delay_calculation_exponential(self, tracker):
        """Test exponential backoff retry delay calculation."""
        tracker.retry_config.strategy = RetryStrategy.EXPONENTIAL_BACKOFF
        tracker.retry_config.initial_delay_seconds = 60
        tracker.retry_config.backoff_multiplier = 2.0
        
        delay1 = tracker._calculate_retry_delay(1)
        delay2 = tracker._calculate_retry_delay(2)
        delay3 = tracker._calculate_retry_delay(3)
        
        assert delay1 == 60  # 60 * 2^0
        assert delay2 == 120  # 60 * 2^1
        assert delay3 == 240  # 60 * 2^2
    
    def test_retry_delay_calculation_linear(self, tracker):
        """Test linear backoff retry delay calculation."""
        tracker.retry_config.strategy = RetryStrategy.LINEAR_BACKOFF
        tracker.retry_config.initial_delay_seconds = 30
        
        delay1 = tracker._calculate_retry_delay(1)
        delay2 = tracker._calculate_retry_delay(2)
        delay3 = tracker._calculate_retry_delay(3)
        
        assert delay1 == 30  # 30 * 1
        assert delay2 == 60  # 30 * 2
        assert delay3 == 90  # 30 * 3
    
    def test_retry_delay_calculation_fixed_interval(self, tracker):
        """Test fixed interval retry delay calculation."""
        tracker.retry_config.strategy = RetryStrategy.FIXED_INTERVAL
        tracker.retry_config.initial_delay_seconds = 45
        
        delay1 = tracker._calculate_retry_delay(1)
        delay2 = tracker._calculate_retry_delay(2)
        delay3 = tracker._calculate_retry_delay(3)
        
        assert delay1 == 45
        assert delay2 == 45
        assert delay3 == 45
    
    def test_retry_delay_max_limit(self, tracker):
        """Test that retry delay respects maximum limit."""
        tracker.retry_config.strategy = RetryStrategy.EXPONENTIAL_BACKOFF
        tracker.retry_config.initial_delay_seconds = 1000
        tracker.retry_config.max_delay_seconds = 100
        
        delay = tracker._calculate_retry_delay(5)
        assert delay == 100  # Should be capped at max_delay_seconds
    
    @patch('src.notifications.delivery_tracker.get_db')
    async def test_get_delivery_metrics(self, mock_get_db, tracker, mock_db_session):
        """Test delivery metrics calculation."""
        # Create mock notifications
        notifications = []
        for i in range(10):
            notification = Mock(spec=Notification)
            notification.status = DeliveryStatus.DELIVERED.value if i < 8 else DeliveryStatus.FAILED.value
            notification.delivery_time = 2.0 if i < 8 else None
            notification.retry_count = 1 if i % 3 == 0 else 0
            notifications.append(notification)
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = notifications
        mock_get_db.return_value = iter([mock_db_session])
        
        # Execute
        metrics = await tracker.get_delivery_metrics()
        
        # Verify
        assert metrics.total_sent == 10
        assert metrics.total_delivered == 8
        assert metrics.total_failed == 2
        assert metrics.total_retried == 4  # Every 3rd notification
        assert metrics.success_rate == 80.0
        assert metrics.retry_rate == 40.0
        assert metrics.average_delivery_time_seconds == 2.0
    
    @patch('src.notifications.delivery_tracker.get_db')
    async def test_get_pending_retries(self, mock_get_db, tracker, mock_db_session, sample_notification):
        """Test getting pending retries."""
        sample_notification.status = DeliveryStatus.RETRYING.value
        mock_db_session.query.return_value.filter.return_value.all.return_value = [sample_notification]
        mock_get_db.return_value = iter([mock_db_session])
        
        # Execute
        pending_retries = await tracker.get_pending_retries()
        
        # Verify
        assert len(pending_retries) == 1
        assert pending_retries[0].id == 123
    
    @patch('src.notifications.delivery_tracker.get_db')
    async def test_cancel_retry(self, mock_get_db, tracker, mock_db_session):
        """Test cancelling a retry."""
        # Setup active retry
        mock_task = Mock()
        tracker._active_retries[123] = mock_task
        
        mock_get_db.return_value = iter([mock_db_session])
        
        # Execute
        result = await tracker.cancel_retry(123)
        
        # Verify
        assert result is True
        mock_task.cancel.assert_called_once()
        assert 123 not in tracker._active_retries
    
    @patch('src.notifications.delivery_tracker.get_db')
    async def test_cleanup_expired_notifications(self, mock_get_db, tracker, mock_db_session):
        """Test cleanup of expired notifications."""
        # Create expired notifications
        expired_notification = Mock(spec=Notification)
        expired_notification.id = 123
        expired_notification.status = DeliveryStatus.PENDING.value
        expired_notification.sent_at = datetime.utcnow() - timedelta(hours=25)
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = [expired_notification]
        mock_get_db.return_value = iter([mock_db_session])
        
        # Execute
        await tracker.cleanup_expired_notifications(max_age_hours=24)
        
        # Verify status update was called
        assert mock_db_session.commit.called


class TestNotificationDeliveryAnalytics:
    """Test notification delivery analytics functionality."""
    
    @pytest.fixture
    def analytics(self):
        """Create an analytics instance."""
        return NotificationDeliveryAnalytics()
    
    @pytest.fixture
    def sample_metrics(self):
        """Create sample delivery metrics."""
        return DeliveryMetrics(
            total_sent=100,
            total_delivered=95,
            total_failed=5,
            total_retried=10,
            average_delivery_time_seconds=2.5,
            success_rate=95.0,
            retry_rate=10.0
        )
    
    @patch('src.notifications.delivery_tracker.NotificationDeliveryTracker.get_delivery_metrics')
    async def test_generate_delivery_report(self, mock_get_metrics, analytics, sample_metrics):
        """Test delivery report generation."""
        # Setup
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        mock_get_metrics.return_value = sample_metrics
        
        # Execute
        report = await analytics.generate_delivery_report(start_date, end_date)
        
        # Verify
        assert report['period']['start_date'] == '2024-01-01T00:00:00'
        assert report['period']['end_date'] == '2024-01-31T00:00:00'
        assert report['metrics']['total_sent'] == 100
        assert report['metrics']['total_delivered'] == 95
        assert report['metrics']['success_rate'] == '95.00%'
        assert report['performance_grade'] == 'A'
        assert len(report['recommendations']) >= 0
    
    def test_performance_grade_calculation(self, analytics):
        """Test performance grade calculation."""
        # Test grade A
        metrics_a = DeliveryMetrics(success_rate=95.0)
        assert analytics._calculate_performance_grade(metrics_a) == 'A'
        
        # Test grade B
        metrics_b = DeliveryMetrics(success_rate=85.0)
        assert analytics._calculate_performance_grade(metrics_b) == 'B'
        
        # Test grade C
        metrics_c = DeliveryMetrics(success_rate=75.0)
        assert analytics._calculate_performance_grade(metrics_c) == 'C'
        
        # Test grade D
        metrics_d = DeliveryMetrics(success_rate=60.0)
        assert analytics._calculate_performance_grade(metrics_d) == 'D'
        
        # Test grade F
        metrics_f = DeliveryMetrics(success_rate=50.0)
        assert analytics._calculate_performance_grade(metrics_f) == 'F'
    
    def test_recommendations_generation(self, analytics):
        """Test recommendations generation."""
        # Test low success rate
        metrics_low_success = DeliveryMetrics(success_rate=85.0)
        recommendations = analytics._generate_recommendations(metrics_low_success)
        assert any('retry configuration' in rec.lower() for rec in recommendations)
        
        # Test high retry rate
        metrics_high_retry = DeliveryMetrics(retry_rate=25.0)
        recommendations = analytics._generate_recommendations(metrics_high_retry)
        assert any('high retry rate' in rec.lower() for rec in recommendations)
        
        # Test slow delivery
        metrics_slow_delivery = DeliveryMetrics(average_delivery_time_seconds=35.0)
        recommendations = analytics._generate_recommendations(metrics_slow_delivery)
        assert any('slow delivery' in rec.lower() for rec in recommendations)
        
        # Test failed notifications
        metrics_failed = DeliveryMetrics(total_failed=5)
        recommendations = analytics._generate_recommendations(metrics_failed)
        assert any('failed notifications' in rec.lower() for rec in recommendations)


class TestIntegration:
    """Integration tests for delivery tracking."""
    
    @pytest.fixture
    def tracker(self):
        """Create a delivery tracker with minimal retry config for testing."""
        config = RetryConfig(max_retries=1, initial_delay_seconds=0.1)
        return NotificationDeliveryTracker(config)
    
    @patch('src.notifications.delivery_tracker.ChannelIntegrationManager.send_email_notification')
    @patch('src.notifications.delivery_tracker.get_db')
    async def test_end_to_end_delivery_tracking(self, mock_get_db, mock_send_email, tracker):
        """Test end-to-end delivery tracking with retry."""
        # Setup mocks
        mock_session = Mock()
        mock_notification = Mock(spec=Notification)
        mock_notification.id = 123
        mock_notification.status = DeliveryStatus.PENDING.value
        mock_notification.retry_count = 0
        mock_notification.error_message = None
        mock_notification.subject = "Test"
        mock_notification.message = "Test message"
        mock_notification.notification_type = "email"
        mock_notification.recipient = "test@example.com"
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_notification
        mock_get_db.return_value = iter([mock_session])
        
        # First attempt fails, retry succeeds
        mock_send_email.side_effect = [
            NotificationResult(success=False, error_message="Temporary failure"),
            NotificationResult(success=True, delivery_time=1.5)
        ]
        
        # Execute
        result = await tracker.track_notification_delivery(
            notification_id=123,
            channel_type='email',
            recipient='test@example.com',
            content={'subject': 'Test', 'message': 'Test message'}
        )
        
        # Verify
        assert result.success is True
        assert result.delivery_time == 1.5
        assert mock_send_email.call_count == 2  # Initial attempt + retry


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 