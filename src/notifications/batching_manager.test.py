"""
Unit tests for notification batching and throttling functionality.

This module contains comprehensive tests for the batching and throttling
managers to ensure proper functionality and edge case handling.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from .batching_manager import (
    NotificationBatchingManager, NotificationThrottlingManager,
    NotificationBatchingThrottlingManager, BatchConfig, ThrottleConfig,
    NotificationBatch, ThrottleMetrics, BatchStatus, ThrottleType
)


class TestBatchConfig:
    """Test cases for BatchConfig dataclass."""
    
    def test_default_config(self):
        """Test default batch configuration values."""
        config = BatchConfig()
        
        assert config.enabled is True
        assert config.max_batch_size == 10
        assert config.max_batch_delay_minutes == 30
        assert config.priority_override is False
        assert config.group_by_user is True
        assert config.group_by_severity is True
        assert config.group_by_channel is True
    
    def test_custom_config(self):
        """Test custom batch configuration values."""
        config = BatchConfig(
            enabled=False,
            max_batch_size=20,
            max_batch_delay_minutes=60,
            priority_override=True,
            group_by_user=False,
            group_by_severity=False,
            group_by_channel=False
        )
        
        assert config.enabled is False
        assert config.max_batch_size == 20
        assert config.max_batch_delay_minutes == 60
        assert config.priority_override is True
        assert config.group_by_user is False
        assert config.group_by_severity is False
        assert config.group_by_channel is False


class TestThrottleConfig:
    """Test cases for ThrottleConfig dataclass."""
    
    def test_default_config(self):
        """Test default throttling configuration values."""
        config = ThrottleConfig()
        
        assert config.enabled is True
        assert config.rate_limit_per_hour == 50
        assert config.rate_limit_per_day == 200
        assert config.cooldown_minutes == 5
        assert config.burst_limit == 10
        assert config.burst_window_minutes == 15
        assert config.daily_limit == 100
        assert config.exempt_high_priority is True
        assert config.exempt_critical_severity is True
    
    def test_custom_config(self):
        """Test custom throttling configuration values."""
        config = ThrottleConfig(
            enabled=False,
            rate_limit_per_hour=100,
            rate_limit_per_day=500,
            cooldown_minutes=10,
            burst_limit=20,
            burst_window_minutes=30,
            daily_limit=200,
            exempt_high_priority=False,
            exempt_critical_severity=False
        )
        
        assert config.enabled is False
        assert config.rate_limit_per_hour == 100
        assert config.rate_limit_per_day == 500
        assert config.cooldown_minutes == 10
        assert config.burst_limit == 20
        assert config.burst_window_minutes == 30
        assert config.daily_limit == 200
        assert config.exempt_high_priority is False
        assert config.exempt_critical_severity is False


class TestNotificationBatch:
    """Test cases for NotificationBatch dataclass."""
    
    def test_batch_creation(self):
        """Test creating a notification batch."""
        batch = NotificationBatch(
            id="test_batch_1",
            user_id=123,
            channel="email",
            severity="medium"
        )
        
        assert batch.id == "test_batch_1"
        assert batch.user_id == 123
        assert batch.channel == "email"
        assert batch.severity == "medium"
        assert len(batch.notifications) == 0
        assert batch.status == BatchStatus.PENDING
        assert batch.priority_score == 0.0
    
    def test_add_notification(self):
        """Test adding notifications to a batch."""
        batch = NotificationBatch(
            id="test_batch_1",
            user_id=123,
            channel="email",
            severity="medium"
        )
        
        # Add low priority notification
        notification1 = {"severity": "low", "form_change_id": 1}
        batch.add_notification(notification1)
        
        assert len(batch.notifications) == 1
        assert batch.priority_score == 1.0
        
        # Add high priority notification
        notification2 = {"severity": "high", "form_change_id": 2}
        batch.add_notification(notification2)
        
        assert len(batch.notifications) == 2
        assert batch.priority_score == 7.0  # Should be max of 1.0 and 7.0
        
        # Add critical notification
        notification3 = {"severity": "critical", "form_change_id": 3}
        batch.add_notification(notification3)
        
        assert len(batch.notifications) == 3
        assert batch.priority_score == 10.0  # Should be max of all


class TestThrottleMetrics:
    """Test cases for ThrottleMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating throttle metrics."""
        metrics = ThrottleMetrics(
            user_id=123,
            channel="email"
        )
        
        assert metrics.user_id == 123
        assert metrics.channel == "email"
        assert metrics.notifications_sent == 0
        assert metrics.last_notification_time is None
        assert metrics.hourly_count == 0
        assert metrics.daily_count == 0
        assert metrics.burst_count == 0
        assert metrics.burst_start_time is None


class TestNotificationBatchingManager:
    """Test cases for NotificationBatchingManager class."""
    
    @pytest.fixture
    def batching_manager(self):
        """Create a batching manager instance for testing."""
        config = BatchConfig(
            enabled=True,
            max_batch_size=5,
            max_batch_delay_minutes=10,
            priority_override=True
        )
        return NotificationBatchingManager(config)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, batching_manager):
        """Test batching manager initialization."""
        assert batching_manager.config.enabled is True
        assert batching_manager.config.max_batch_size == 5
        assert len(batching_manager.active_batches) == 0
    
    @pytest.mark.asyncio
    async def test_add_notification_to_batch_disabled(self, mock_db_session):
        """Test adding notification when batching is disabled."""
        config = BatchConfig(enabled=False)
        manager = NotificationBatchingManager(config)
        
        notification = {
            "user_id": 123,
            "channel": "email",
            "severity": "medium",
            "subject": "Test",
            "message": "Test message"
        }
        
        result = await manager.add_notification_to_batch(notification, mock_db_session)
        
        assert result == "no_batching"
        assert len(manager.active_batches) == 0
    
    @pytest.mark.asyncio
    async def test_add_notification_immediate_priority(self, batching_manager, mock_db_session):
        """Test adding high priority notification for immediate sending."""
        notification = {
            "user_id": 123,
            "channel": "email",
            "severity": "critical",
            "subject": "Test",
            "message": "Test message"
        }
        
        result = await batching_manager.add_notification_to_batch(notification, mock_db_session)
        
        assert result == "immediate"
        assert len(batching_manager.active_batches) == 0
    
    @pytest.mark.asyncio
    async def test_add_notification_to_batch(self, batching_manager, mock_db_session):
        """Test adding notification to a batch."""
        notification = {
            "user_id": 123,
            "channel": "email",
            "severity": "medium",
            "subject": "Test",
            "message": "Test message"
        }
        
        result = await batching_manager.add_notification_to_batch(notification, mock_db_session)
        
        assert result == "user_123_channel_email_severity_medium"
        assert len(batching_manager.active_batches) == 1
        
        batch = batching_manager.active_batches[result]
        assert batch.user_id == 123
        assert batch.channel == "email"
        assert batch.severity == "medium"
        assert len(batch.notifications) == 1
    
    @pytest.mark.asyncio
    async def test_batch_full_send(self, batching_manager, mock_db_session):
        """Test sending batch when it reaches maximum size."""
        # Add notifications until batch is full
        for i in range(5):
            notification = {
                "user_id": 123,
                "channel": "email",
                "severity": "medium",
                "subject": f"Test {i}",
                "message": f"Test message {i}"
            }
            
            result = await batching_manager.add_notification_to_batch(notification, mock_db_session)
        
        # Batch should be sent automatically when full
        assert len(batching_manager.active_batches) == 0
    
    def test_generate_batch_key(self, batching_manager):
        """Test batch key generation."""
        notification = {
            "user_id": 123,
            "channel": "email",
            "severity": "medium"
        }
        
        key = batching_manager._generate_batch_key(notification)
        assert key == "user_123_channel_email_severity_medium"
    
    def test_should_send_immediately(self, batching_manager):
        """Test immediate sending logic."""
        # High priority should be sent immediately
        high_priority = {"severity": "high"}
        assert batching_manager._should_send_immediately(high_priority) is True
        
        # Critical should be sent immediately
        critical = {"severity": "critical"}
        assert batching_manager._should_send_immediately(critical) is True
        
        # Medium priority should not be sent immediately
        medium_priority = {"severity": "medium"}
        assert batching_manager._should_send_immediately(medium_priority) is False
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, batching_manager):
        """Test starting and stopping the batching manager."""
        await batching_manager.start()
        assert batching_manager.batch_scheduler_task is not None
        
        await batching_manager.stop()
        assert batching_manager.batch_scheduler_task is None


class TestNotificationThrottlingManager:
    """Test cases for NotificationThrottlingManager class."""
    
    @pytest.fixture
    def throttling_manager(self):
        """Create a throttling manager instance for testing."""
        config = ThrottleConfig(
            enabled=True,
            rate_limit_per_hour=10,
            rate_limit_per_day=50,
            cooldown_minutes=5
        )
        return NotificationThrottlingManager(config)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, throttling_manager):
        """Test throttling manager initialization."""
        assert throttling_manager.config.enabled is True
        assert throttling_manager.config.rate_limit_per_hour == 10
        assert len(throttling_manager.throttle_metrics) == 0
    
    @pytest.mark.asyncio
    async def test_check_throttle_disabled(self):
        """Test throttling when disabled."""
        config = ThrottleConfig(enabled=False)
        manager = NotificationThrottlingManager(config)
        
        result = await manager.check_throttle(123, "email", "medium")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_throttle_exempt_high_priority(self, throttling_manager):
        """Test that high priority notifications are exempt from throttling."""
        result = await throttling_manager.check_throttle(123, "email", "high")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_throttle_exempt_critical(self, throttling_manager):
        """Test that critical notifications are exempt from throttling."""
        result = await throttling_manager.check_throttle(123, "email", "critical")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_throttle_rate_limit_exceeded(self, throttling_manager):
        """Test throttling when rate limit is exceeded."""
        # Send notifications up to the hourly limit
        for i in range(10):
            result = await throttling_manager.check_throttle(123, "email", "medium")
            assert result is True
        
        # Next notification should be throttled
        result = await throttling_manager.check_throttle(123, "email", "medium")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_throttle_cooldown(self, throttling_manager):
        """Test throttling during cooldown period."""
        # Send first notification
        result = await throttling_manager.check_throttle(123, "email", "medium")
        assert result is True
        
        # Second notification should be throttled due to cooldown
        result = await throttling_manager.check_throttle(123, "email", "medium")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_throttle_metrics(self, throttling_manager):
        """Test getting throttle metrics."""
        # Send some notifications
        await throttling_manager.check_throttle(123, "email", "medium")
        await throttling_manager.check_throttle(456, "slack", "medium")
        
        # Get metrics for specific user
        metrics = await throttling_manager.get_throttle_metrics(123)
        assert len(metrics) == 1
        assert "123_email" in metrics
        
        # Get metrics for all users
        all_metrics = await throttling_manager.get_throttle_metrics()
        assert len(all_metrics) == 2
        assert "123_email" in all_metrics
        assert "456_slack" in all_metrics
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, throttling_manager):
        """Test starting and stopping the throttling manager."""
        await throttling_manager.start()
        assert throttling_manager.cleanup_task is not None
        
        await throttling_manager.stop()
        assert throttling_manager.cleanup_task is None


class TestNotificationBatchingThrottlingManager:
    """Test cases for NotificationBatchingThrottlingManager class."""
    
    @pytest.fixture
    def combined_manager(self):
        """Create a combined manager instance for testing."""
        batch_config = BatchConfig(enabled=True, max_batch_size=5)
        throttle_config = ThrottleConfig(enabled=True, rate_limit_per_hour=10)
        return NotificationBatchingThrottlingManager(batch_config, throttle_config)
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self, combined_manager):
        """Test combined manager initialization."""
        assert combined_manager.batching_manager is not None
        assert combined_manager.throttling_manager is not None
    
    @pytest.mark.asyncio
    async def test_process_notification_throttled(self, combined_manager, mock_db_session):
        """Test processing notification that gets throttled."""
        # Send notifications up to the limit
        for i in range(10):
            notification = {
                "user_id": 123,
                "channel": "email",
                "severity": "medium",
                "subject": f"Test {i}",
                "message": f"Test message {i}"
            }
            result = await combined_manager.process_notification(notification, mock_db_session)
            assert result["status"] == "processed"
        
        # Next notification should be throttled
        notification = {
            "user_id": 123,
            "channel": "email",
            "severity": "medium",
            "subject": "Test throttled",
            "message": "This should be throttled"
        }
        result = await combined_manager.process_notification(notification, mock_db_session)
        
        assert result["status"] == "throttled"
        assert result["throttled"] is True
        assert "Rate limit" in result["reason"]
    
    @pytest.mark.asyncio
    async def test_process_notification_batched(self, combined_manager, mock_db_session):
        """Test processing notification that gets batched."""
        notification = {
            "user_id": 123,
            "channel": "email",
            "severity": "medium",
            "subject": "Test",
            "message": "Test message"
        }
        
        result = await combined_manager.process_notification(notification, mock_db_session)
        
        assert result["status"] == "processed"
        assert result["throttled"] is False
        assert result["batch_id"] is not None
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, combined_manager):
        """Test getting combined metrics."""
        metrics = await combined_manager.get_metrics()
        
        assert "batching" in metrics
        assert "throttling" in metrics
        assert "active_batches" in metrics["batching"]
        assert "active_metrics" in metrics["throttling"]
    
    @pytest.mark.asyncio
    async def test_start_stop_manager(self, combined_manager):
        """Test starting and stopping the combined manager."""
        await combined_manager.start()
        
        # Check that both managers are started
        assert combined_manager.batching_manager.batch_scheduler_task is not None
        assert combined_manager.throttling_manager.cleanup_task is not None
        
        await combined_manager.stop()
        
        # Check that both managers are stopped
        assert combined_manager.batching_manager.batch_scheduler_task is None
        assert combined_manager.throttling_manager.cleanup_task is None


class TestIntegration:
    """Integration tests for batching and throttling functionality."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test the complete batching and throttling workflow."""
        # Create managers
        batch_config = BatchConfig(enabled=True, max_batch_size=3, max_batch_delay_minutes=1)
        throttle_config = ThrottleConfig(enabled=True, rate_limit_per_hour=5, cooldown_minutes=1)
        manager = NotificationBatchingThrottlingManager(batch_config, throttle_config)
        
        mock_db = Mock(spec=Session)
        
        # Start managers
        await manager.start()
        
        try:
            # Send notifications
            notifications = []
            for i in range(5):
                notification = {
                    "user_id": 123,
                    "channel": "email",
                    "severity": "medium",
                    "subject": f"Test {i}",
                    "message": f"Test message {i}"
                }
                result = await manager.process_notification(notification, mock_db)
                notifications.append(result)
            
            # Check results
            processed_count = sum(1 for r in notifications if r["status"] == "processed")
            throttled_count = sum(1 for r in notifications if r["status"] == "throttled")
            
            assert processed_count > 0
            assert throttled_count > 0
            
            # Check metrics
            metrics = await manager.get_metrics()
            assert metrics["batching"]["active_batches"] >= 0
            assert metrics["throttling"]["active_metrics"] > 0
            
        finally:
            await manager.stop()


# Test the global instance
def test_global_instance():
    """Test that the global batching_throttling_manager instance exists."""
    from .batching_manager import batching_throttling_manager
    
    assert batching_throttling_manager is not None
    assert isinstance(batching_throttling_manager, NotificationBatchingThrottlingManager) 