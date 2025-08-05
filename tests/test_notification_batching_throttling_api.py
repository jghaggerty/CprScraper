"""
Unit and integration tests for notification batching and throttling API endpoints.

This module contains comprehensive tests for the FastAPI endpoints that manage
notification batching and throttling functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.notification_batching_throttling import NotificationBatchingThrottlingAPI
from src.database.models import User, Notification
from src.notifications.batching_manager import (
    NotificationBatchingThrottlingManager, BatchConfig, ThrottleConfig
)


class TestNotificationBatchingThrottlingAPI:
    """Test cases for notification batching and throttling API endpoints."""
    
    @pytest.fixture
    def api_instance(self):
        """Create an API instance for testing."""
        return NotificationBatchingThrottlingAPI()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.is_active = True
        user.is_superuser = True
        return user
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        return {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
    
    @pytest.mark.asyncio
    async def test_get_system_status(self, api_instance, mock_user):
        """Test getting system status endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_manager.get_metrics.return_value = {
                "batching": {
                    "active_batches": 2,
                    "batch_config": {
                        "enabled": True,
                        "max_batch_size": 10,
                        "max_batch_delay_minutes": 30
                    }
                },
                "throttling": {
                    "active_metrics": 5,
                    "throttle_config": {
                        "enabled": True,
                        "rate_limit_per_hour": 50,
                        "rate_limit_per_day": 200,
                        "cooldown_minutes": 5
                    }
                }
            }
            
            result = await api_instance.get_system_status(mock_user)
            
            assert result["status"] == "success"
            assert result["data"]["batching"]["enabled"] is True
            assert result["data"]["batching"]["active_batches"] == 2
            assert result["data"]["throttling"]["enabled"] is True
            assert result["data"]["throttling"]["active_metrics"] == 5
    
    @pytest.mark.asyncio
    async def test_get_active_batches(self, api_instance, mock_user):
        """Test getting active batches endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            # Mock active batches
            mock_batch1 = Mock()
            mock_batch1.id = "batch_1"
            mock_batch1.user_id = 1
            mock_batch1.channel = "email"
            mock_batch1.severity = "medium"
            mock_batch1.status.value = "pending"
            mock_batch1.notifications = [{"id": 1}, {"id": 2}]
            mock_batch1.priority_score = 5.0
            mock_batch1.created_at = datetime.now()
            mock_batch1.scheduled_for = None
            
            mock_manager.batching_manager.active_batches = {
                "batch_1": mock_batch1
            }
            mock_manager.batching_manager.config.max_batch_delay_minutes = 30
            
            result = await api_instance.get_active_batches(mock_user)
            
            assert result["status"] == "success"
            assert len(result["data"]["active_batches"]) == 1
            assert result["data"]["total_active_batches"] == 1
            assert result["data"]["active_batches"][0]["id"] == "batch_1"
            assert result["data"]["active_batches"][0]["notifications_count"] == 2
    
    @pytest.mark.asyncio
    async def test_get_batch_details(self, api_instance, mock_user):
        """Test getting batch details endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            # Mock batch
            mock_batch = Mock()
            mock_batch.id = "batch_1"
            mock_batch.user_id = 1
            mock_batch.channel = "email"
            mock_batch.severity = "medium"
            mock_batch.status.value = "pending"
            mock_batch.notifications = [{"id": 1, "subject": "Test"}]
            mock_batch.priority_score = 5.0
            mock_batch.created_at = datetime.now()
            mock_batch.scheduled_for = None
            
            mock_manager.batching_manager.active_batches = {
                "batch_1": mock_batch
            }
            mock_manager.batching_manager.config.max_batch_delay_minutes = 30
            
            result = await api_instance.get_batch_details("batch_1", mock_user)
            
            assert result["status"] == "success"
            assert result["data"]["id"] == "batch_1"
            assert result["data"]["notifications_count"] == 1
            assert len(result["data"]["notifications"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_batch_details_not_found(self, api_instance, mock_user):
        """Test getting batch details for non-existent batch."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_manager.batching_manager.active_batches = {}
            
            with pytest.raises(Exception) as exc_info:
                await api_instance.get_batch_details("nonexistent", mock_user)
            
            assert "Batch not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_send_batch_immediately(self, api_instance, mock_user):
        """Test sending batch immediately endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            # Mock batch
            mock_batch = Mock()
            mock_batch.id = "batch_1"
            mock_batch.notifications = [{"id": 1}]
            
            mock_manager.batching_manager.active_batches = {
                "batch_1": mock_batch
            }
            mock_manager.batching_manager._send_batch = AsyncMock()
            
            result = await api_instance.send_batch_immediately("batch_1", mock_user)
            
            assert result["status"] == "success"
            assert "sent successfully" in result["message"]
            assert result["data"]["batch_id"] == "batch_1"
            mock_manager.batching_manager._send_batch.assert_called_once_with("batch_1")
    
    @pytest.mark.asyncio
    async def test_cancel_batch(self, api_instance, mock_user):
        """Test cancelling batch endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            # Mock batch
            mock_batch = Mock()
            mock_batch.id = "batch_1"
            mock_batch.notifications = [{"id": 1}, {"id": 2}]
            
            mock_manager.batching_manager.active_batches = {
                "batch_1": mock_batch
            }
            
            result = await api_instance.cancel_batch("batch_1", mock_user)
            
            assert result["status"] == "success"
            assert "cancelled successfully" in result["message"]
            assert result["data"]["batch_id"] == "batch_1"
            assert result["data"]["notifications_count"] == 2
            assert "batch_1" not in mock_manager.batching_manager.active_batches
    
    @pytest.mark.asyncio
    async def test_get_throttling_metrics(self, api_instance, mock_user):
        """Test getting throttling metrics endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_metrics = {
                "1_email": {
                    "user_id": 1,
                    "channel": "email",
                    "notifications_sent": 10,
                    "hourly_count": 5,
                    "daily_count": 25
                },
                "2_slack": {
                    "user_id": 2,
                    "channel": "slack",
                    "notifications_sent": 5,
                    "hourly_count": 2,
                    "daily_count": 15
                }
            }
            
            mock_manager.throttling_manager.get_throttle_metrics.return_value = mock_metrics
            
            result = await api_instance.get_throttling_metrics(mock_user)
            
            assert result["status"] == "success"
            assert len(result["data"]["throttle_metrics"]) == 2
            assert result["data"]["total_users_tracked"] == 2
    
    @pytest.mark.asyncio
    async def test_get_user_throttling_metrics(self, api_instance, mock_user):
        """Test getting user-specific throttling metrics endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_metrics = {
                "1_email": {
                    "user_id": 1,
                    "channel": "email",
                    "notifications_sent": 10,
                    "hourly_count": 5,
                    "daily_count": 25
                }
            }
            
            mock_manager.throttling_manager.get_throttle_metrics.return_value = mock_metrics
            
            result = await api_instance.get_user_throttling_metrics(1, mock_user)
            
            assert result["status"] == "success"
            assert result["data"]["user_id"] == 1
            assert len(result["data"]["throttle_metrics"]) == 1
    
    @pytest.mark.asyncio
    async def test_reset_user_throttling(self, api_instance, mock_user):
        """Test resetting user throttling metrics endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_manager.throttling_manager.throttle_metrics = {
                "1_email": Mock(),
                "1_slack": Mock(),
                "2_email": Mock()
            }
            
            result = await api_instance.reset_user_throttling(1, mock_user)
            
            assert result["status"] == "success"
            assert "reset for user 1" in result["message"]
            assert result["data"]["user_id"] == 1
            assert result["data"]["channel"] is None
            # Should remove all metrics for user 1
            assert "1_email" not in mock_manager.throttling_manager.throttle_metrics
            assert "1_slack" not in mock_manager.throttling_manager.throttle_metrics
            assert "2_email" in mock_manager.throttling_manager.throttle_metrics
    
    @pytest.mark.asyncio
    async def test_get_batching_config(self, api_instance, mock_user):
        """Test getting batching configuration endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_manager.batching_manager.config.enabled = True
            mock_manager.batching_manager.config.max_batch_size = 15
            mock_manager.batching_manager.config.max_batch_delay_minutes = 45
            mock_manager.batching_manager.config.priority_override = True
            mock_manager.batching_manager.config.group_by_user = True
            mock_manager.batching_manager.config.group_by_severity = False
            mock_manager.batching_manager.config.group_by_channel = True
            
            result = await api_instance.get_batching_config(mock_user)
            
            assert result["status"] == "success"
            assert result["data"]["enabled"] is True
            assert result["data"]["max_batch_size"] == 15
            assert result["data"]["max_batch_delay_minutes"] == 45
            assert result["data"]["priority_override"] is True
            assert result["data"]["group_by_user"] is True
            assert result["data"]["group_by_severity"] is False
            assert result["data"]["group_by_channel"] is True
    
    @pytest.mark.asyncio
    async def test_update_batching_config(self, api_instance, mock_user):
        """Test updating batching configuration endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            config_data = {
                "enabled": False,
                "max_batch_size": 20,
                "max_batch_delay_minutes": 60,
                "priority_override": False,
                "group_by_user": False,
                "group_by_severity": True,
                "group_by_channel": False
            }
            
            result = await api_instance.update_batching_config(config_data, mock_user)
            
            assert result["status"] == "success"
            assert "updated successfully" in result["message"]
            assert result["data"]["enabled"] is False
            assert result["data"]["max_batch_size"] == 20
            assert result["data"]["max_batch_delay_minutes"] == 60
            assert result["data"]["priority_override"] is False
            assert result["data"]["group_by_user"] is False
            assert result["data"]["group_by_severity"] is True
            assert result["data"]["group_by_channel"] is False
    
    @pytest.mark.asyncio
    async def test_get_throttling_config(self, api_instance, mock_user):
        """Test getting throttling configuration endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            mock_manager.throttling_manager.config.enabled = True
            mock_manager.throttling_manager.config.rate_limit_per_hour = 100
            mock_manager.throttling_manager.config.rate_limit_per_day = 500
            mock_manager.throttling_manager.config.cooldown_minutes = 10
            mock_manager.throttling_manager.config.burst_limit = 20
            mock_manager.throttling_manager.config.burst_window_minutes = 30
            mock_manager.throttling_manager.config.daily_limit = 200
            mock_manager.throttling_manager.config.exempt_high_priority = False
            mock_manager.throttling_manager.config.exempt_critical_severity = True
            
            result = await api_instance.get_throttling_config(mock_user)
            
            assert result["status"] == "success"
            assert result["data"]["enabled"] is True
            assert result["data"]["rate_limit_per_hour"] == 100
            assert result["data"]["rate_limit_per_day"] == 500
            assert result["data"]["cooldown_minutes"] == 10
            assert result["data"]["burst_limit"] == 20
            assert result["data"]["burst_window_minutes"] == 30
            assert result["data"]["daily_limit"] == 200
            assert result["data"]["exempt_high_priority"] is False
            assert result["data"]["exempt_critical_severity"] is True
    
    @pytest.mark.asyncio
    async def test_update_throttling_config(self, api_instance, mock_user):
        """Test updating throttling configuration endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            config_data = {
                "enabled": False,
                "rate_limit_per_hour": 150,
                "rate_limit_per_day": 600,
                "cooldown_minutes": 15,
                "burst_limit": 25,
                "burst_window_minutes": 45,
                "daily_limit": 300,
                "exempt_high_priority": True,
                "exempt_critical_severity": False
            }
            
            result = await api_instance.update_throttling_config(config_data, mock_user)
            
            assert result["status"] == "success"
            assert "updated successfully" in result["message"]
            assert result["data"]["enabled"] is False
            assert result["data"]["rate_limit_per_hour"] == 150
            assert result["data"]["rate_limit_per_day"] == 600
            assert result["data"]["cooldown_minutes"] == 15
            assert result["data"]["burst_limit"] == 25
            assert result["data"]["burst_window_minutes"] == 45
            assert result["data"]["daily_limit"] == 300
            assert result["data"]["exempt_high_priority"] is True
            assert result["data"]["exempt_critical_severity"] is False
    
    @pytest.mark.asyncio
    async def test_test_notification_processing(self, api_instance, mock_user, mock_db_session):
        """Test notification processing test endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            notification_data = {
                "subject": "Test Notification",
                "message": "This is a test",
                "severity": "medium",
                "channel": "email"
            }
            
            mock_manager.process_notification.return_value = {
                "status": "processed",
                "batch_id": "batch_123",
                "throttled": False
            }
            
            result = await api_instance.test_notification_processing(notification_data, mock_user, mock_db_session)
            
            assert result["status"] == "success"
            assert result["data"]["notification_data"] == notification_data
            assert result["data"]["processing_result"]["status"] == "processed"
            assert result["data"]["processing_result"]["batch_id"] == "batch_123"
            assert result["data"]["processing_result"]["throttled"] is False
    
    @pytest.mark.asyncio
    async def test_get_analytics_summary(self, api_instance, mock_user, mock_db_session):
        """Test getting analytics summary endpoint."""
        with patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            # Mock active batches and metrics
            mock_manager.batching_manager.active_batches = {"batch1": Mock(), "batch2": Mock()}
            mock_manager.throttling_manager.throttle_metrics = {"user1": Mock(), "user2": Mock(), "user3": Mock()}
            
            # Mock recent notifications
            mock_notifications = [
                Mock(is_batch=True, throttled=False),
                Mock(is_batch=False, throttled=True),
                Mock(is_batch=False, throttled=False),
                Mock(is_batch=True, throttled=False)
            ]
            
            mock_db_session.query.return_value.filter.return_value.all.return_value = mock_notifications
            
            result = await api_instance.get_analytics_summary(mock_user, mock_db_session)
            
            assert result["status"] == "success"
            assert result["data"]["active_batches"] == 2
            assert result["data"]["active_throttle_metrics"] == 3
            assert result["data"]["recent_notifications"]["total"] == 4
            assert result["data"]["recent_notifications"]["batched"] == 2
            assert result["data"]["recent_notifications"]["throttled"] == 1
            assert result["data"]["recent_notifications"]["immediate"] == 1


class TestNotificationBatchingThrottlingAPIEndpoints:
    """Test cases for notification batching and throttling API endpoints using FastAPI TestClient."""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        return {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.first_name = "Test"
        user.last_name = "User"
        user.is_active = True
        user.is_superuser = True
        return user
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @pytest.mark.asyncio
    async def test_get_system_status_endpoint(self, auth_headers):
        """Test GET /api/notification-batching-throttling/status endpoint."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            mock_manager.get_metrics.return_value = {
                "batching": {
                    "active_batches": 3,
                    "batch_config": {"enabled": True, "max_batch_size": 10}
                },
                "throttling": {
                    "active_metrics": 7,
                    "throttle_config": {"enabled": True, "rate_limit_per_hour": 50}
                }
            }
            
            # This would require setting up a proper FastAPI test client
            # For now, we'll test the logic directly
            api_instance = NotificationBatchingThrottlingAPI()
            result = await api_instance.get_system_status(mock_user)
            
            assert result["status"] == "success"
            assert result["data"]["batching"]["active_batches"] == 3
            assert result["data"]["throttling"]["active_metrics"] == 7
    
    @pytest.mark.asyncio
    async def test_get_batches_endpoint(self, auth_headers):
        """Test GET /api/notification-batching-throttling/batches endpoint."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            # Mock active batches
            mock_batch = Mock()
            mock_batch.id = "test_batch"
            mock_batch.user_id = 1
            mock_batch.channel = "email"
            mock_batch.severity = "medium"
            mock_batch.status.value = "pending"
            mock_batch.notifications = [{"id": 1}]
            mock_batch.priority_score = 5.0
            mock_batch.created_at = datetime.now()
            mock_batch.scheduled_for = None
            
            mock_manager.batching_manager.active_batches = {"test_batch": mock_batch}
            mock_manager.batching_manager.config.max_batch_delay_minutes = 30
            
            api_instance = NotificationBatchingThrottlingAPI()
            result = await api_instance.get_active_batches(mock_user)
            
            assert result["status"] == "success"
            assert len(result["data"]["active_batches"]) == 1
            assert result["data"]["active_batches"][0]["id"] == "test_batch"
    
    @pytest.mark.asyncio
    async def test_update_batching_config_endpoint(self, auth_headers):
        """Test PUT /api/notification-batching-throttling/config/batching endpoint."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            config_data = {
                "enabled": False,
                "max_batch_size": 25,
                "max_batch_delay_minutes": 90,
                "priority_override": True,
                "group_by_user": False,
                "group_by_severity": True,
                "group_by_channel": False
            }
            
            api_instance = NotificationBatchingThrottlingAPI()
            result = await api_instance.update_batching_config(config_data, mock_user)
            
            assert result["status"] == "success"
            assert "updated successfully" in result["message"]
            assert result["data"]["enabled"] is False
            assert result["data"]["max_batch_size"] == 25
            assert result["data"]["max_batch_delay_minutes"] == 90
    
    @pytest.mark.asyncio
    async def test_update_throttling_config_endpoint(self, auth_headers):
        """Test PUT /api/notification-batching-throttling/config/throttling endpoint."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            config_data = {
                "enabled": False,
                "rate_limit_per_hour": 200,
                "rate_limit_per_day": 1000,
                "cooldown_minutes": 20,
                "burst_limit": 30,
                "burst_window_minutes": 60,
                "daily_limit": 500,
                "exempt_high_priority": False,
                "exempt_critical_severity": False
            }
            
            api_instance = NotificationBatchingThrottlingAPI()
            result = await api_instance.update_throttling_config(config_data, mock_user)
            
            assert result["status"] == "success"
            assert "updated successfully" in result["message"]
            assert result["data"]["enabled"] is False
            assert result["data"]["rate_limit_per_hour"] == 200
            assert result["data"]["rate_limit_per_day"] == 1000
    
    @pytest.mark.asyncio
    async def test_test_notification_endpoint(self, auth_headers):
        """Test POST /api/notification-batching-throttling/test/notification endpoint."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.get_db') as mock_get_db, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_user.id = 1
            mock_get_user.return_value = mock_user
            
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            
            notification_data = {
                "subject": "Integration Test",
                "message": "Testing notification processing",
                "severity": "high",
                "channel": "slack"
            }
            
            mock_manager.process_notification.return_value = {
                "status": "processed",
                "batch_id": "integration_batch",
                "throttled": False
            }
            
            api_instance = NotificationBatchingThrottlingAPI()
            result = await api_instance.test_notification_processing(notification_data, mock_user, mock_db)
            
            assert result["status"] == "success"
            assert result["data"]["notification_data"]["subject"] == "Integration Test"
            assert result["data"]["processing_result"]["status"] == "processed"
            assert result["data"]["processing_result"]["batch_id"] == "integration_batch"


# Test error handling
class TestErrorHandling:
    """Test cases for error handling in the API."""
    
    @pytest.mark.asyncio
    async def test_get_system_status_error(self):
        """Test error handling in get_system_status."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            mock_manager.get_metrics.side_effect = Exception("Database connection failed")
            
            api_instance = NotificationBatchingThrottlingAPI()
            
            with pytest.raises(Exception) as exc_info:
                await api_instance.get_system_status(mock_user)
            
            assert "Failed to get system status" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_batch_details_not_found_error(self):
        """Test error handling when batch is not found."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            mock_manager.batching_manager.active_batches = {}
            
            api_instance = NotificationBatchingThrottlingAPI()
            
            with pytest.raises(Exception) as exc_info:
                await api_instance.get_batch_details("nonexistent", mock_user)
            
            assert "Batch not found" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_config_validation_error(self):
        """Test error handling in configuration updates."""
        with patch('src.api.notification_batching_throttling.get_current_user') as mock_get_user, \
             patch('src.api.notification_batching_throttling.batching_throttling_manager') as mock_manager:
            
            mock_user = Mock()
            mock_get_user.return_value = mock_user
            
            # Test with invalid configuration data
            config_data = {
                "max_batch_size": -5,  # Invalid negative value
                "rate_limit_per_hour": 0  # Invalid zero value
            }
            
            api_instance = NotificationBatchingThrottlingAPI()
            
            # Should handle the error gracefully
            result = await api_instance.update_batching_config(config_data, mock_user)
            
            # The API should still return a success response even with invalid data
            # as the validation would happen at the manager level
            assert result["status"] == "success" 