"""
Unit and integration tests for notification batching and throttling API endpoints.

This module contains comprehensive tests for the FastAPI endpoints that manage
notification batching and throttling functionality.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from src.database.models import User, Notification
from src.notifications.batching_manager import (
    NotificationBatchingThrottlingManager, BatchConfig, ThrottleConfig
)


class TestNotificationBatchingThrottlingAPI:
    """Test cases for notification batching and throttling API endpoints."""
    
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
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_system_status(self, mock_manager, test_client, mock_user):
        """Test getting system status endpoint."""
        # Mock the async get_metrics method
        mock_manager.get_metrics = AsyncMock(return_value={
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
        })
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/status")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["batching"]["enabled"] is True
        assert data["data"]["batching"]["active_batches"] == 2
        assert data["data"]["throttling"]["enabled"] is True
        assert data["data"]["throttling"]["active_metrics"] == 5
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_active_batches(self, mock_manager, test_client, mock_user):
        """Test getting active batches endpoint."""
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
        
        mock_manager.batching_manager.active_batches = {"batch_1": mock_batch1}
        mock_manager.batching_manager.config.max_batch_delay_minutes = 30
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/batches")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["data"]["active_batches"]) == 1
        assert data["data"]["active_batches"][0]["id"] == "batch_1"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_batch_details(self, mock_manager, test_client, mock_user):
        """Test getting batch details endpoint."""
        # Mock batch
        mock_batch = Mock()
        mock_batch.id = "batch_1"
        mock_batch.user_id = 1
        mock_batch.channel = "email"
        mock_batch.severity = "medium"
        mock_batch.status.value = "pending"
        mock_batch.notifications = [{"id": 1}, {"id": 2}]
        mock_batch.priority_score = 5.0
        mock_batch.created_at = datetime.now()
        mock_batch.scheduled_for = None
        
        mock_manager.batching_manager.active_batches = {"batch_1": mock_batch}
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/batches/batch_1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["id"] == "batch_1"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_batch_details_not_found(self, mock_manager, test_client, mock_user):
        """Test getting batch details for non-existent batch."""
        mock_manager.batching_manager.active_batches = {}
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/batches/nonexistent")
        
        # Assertions
        assert response.status_code == 404
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_send_batch_immediately(self, mock_manager, test_client, mock_user):
        """Test sending batch immediately endpoint."""
        # Mock batch
        mock_batch = Mock()
        mock_batch.id = "batch_1"
        mock_batch.status.value = "pending"
        mock_manager.batching_manager.active_batches = {"batch_1": mock_batch}
        mock_manager.batching_manager.send_batch_immediately = AsyncMock(return_value=True)
        
        # Test the endpoint
        response = test_client.post("/api/notification-batching-throttling/batches/batch_1/send")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_cancel_batch(self, mock_manager, test_client, mock_user):
        """Test canceling batch endpoint."""
        # Mock batch
        mock_batch = Mock()
        mock_batch.id = "batch_1"
        mock_batch.status.value = "pending"
        mock_manager.batching_manager.active_batches = {"batch_1": mock_batch}
        mock_manager.batching_manager.cancel_batch = AsyncMock(return_value=True)
        
        # Test the endpoint
        response = test_client.delete("/api/notification-batching-throttling/batches/batch_1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_throttling_metrics(self, mock_manager, test_client, mock_user):
        """Test getting throttling metrics endpoint."""
        # Mock throttling metrics
        mock_manager.throttling_manager.get_throttle_metrics = AsyncMock(return_value={
            "user_1_email": {
                "user_id": 1,
                "channel": "email",
                "notifications_sent": 5,
                "hourly_count": 2,
                "daily_count": 10
            }
        })
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/throttling/metrics")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "metrics" in data["data"]
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_user_throttling_metrics(self, mock_manager, test_client, mock_user):
        """Test getting user-specific throttling metrics endpoint."""
        # Mock user throttling metrics
        mock_manager.throttling_manager.get_throttle_metrics = AsyncMock(return_value={
            "user_1_email": {
                "user_id": 1,
                "channel": "email",
                "notifications_sent": 5,
                "hourly_count": 2,
                "daily_count": 10
            }
        })
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/throttling/metrics/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "metrics" in data["data"]
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_reset_user_throttling(self, mock_manager, test_client, mock_user):
        """Test resetting user throttling endpoint."""
        # Mock reset method
        mock_manager.throttling_manager.reset_user_throttling = AsyncMock(return_value=True)
        
        # Test the endpoint
        response = test_client.post("/api/notification-batching-throttling/throttling/reset/1")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_batching_config(self, mock_manager, test_client, mock_user):
        """Test getting batching configuration endpoint."""
        # Mock config
        mock_manager.batching_manager.config.enabled = True
        mock_manager.batching_manager.config.max_batch_size = 10
        mock_manager.batching_manager.config.max_batch_delay_minutes = 30
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/config/batching")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["enabled"] is True
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_update_batching_config(self, mock_manager, test_client, mock_user):
        """Test updating batching configuration endpoint."""
        # Mock update method
        mock_manager.batching_manager.update_config = AsyncMock(return_value=True)
        
        # Test data
        config_data = {
            "enabled": True,
            "max_batch_size": 15,
            "max_batch_delay_minutes": 45
        }
        
        # Test the endpoint
        response = test_client.put(
            "/api/notification-batching-throttling/config/batching",
            json=config_data
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_throttling_config(self, mock_manager, test_client, mock_user):
        """Test getting throttling configuration endpoint."""
        # Mock config
        mock_manager.throttling_manager.config.enabled = True
        mock_manager.throttling_manager.config.rate_limit_per_hour = 50
        mock_manager.throttling_manager.config.rate_limit_per_day = 200
        mock_manager.throttling_manager.config.cooldown_minutes = 5
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/config/throttling")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["enabled"] is True
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_update_throttling_config(self, mock_manager, test_client, mock_user):
        """Test updating throttling configuration endpoint."""
        # Mock update method
        mock_manager.throttling_manager.update_config = AsyncMock(return_value=True)
        
        # Test data
        config_data = {
            "enabled": True,
            "rate_limit_per_hour": 60,
            "rate_limit_per_day": 250,
            "cooldown_minutes": 10
        }
        
        # Test the endpoint
        response = test_client.put(
            "/api/notification-batching-throttling/config/throttling",
            json=config_data
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_test_notification_processing(self, mock_manager, test_client, mock_user, mock_db_session):
        """Test notification processing test endpoint."""
        # Mock processing
        mock_manager.process_notification = AsyncMock(return_value={
            "status": "processed",
            "batch_id": "test_batch_1",
            "throttled": False
        })
        
        # Test data
        notification_data = {
            "user_id": 1,
            "channel": "email",
            "subject": "Test Notification",
            "message": "Test message",
            "severity": "medium"
        }
        
        # Test the endpoint
        response = test_client.post(
            "/api/notification-batching-throttling/test/notification",
            json=notification_data
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_analytics_summary(self, mock_manager, test_client, mock_user, mock_db_session):
        """Test getting analytics summary endpoint."""
        # Mock analytics data
        mock_manager.get_analytics_summary = AsyncMock(return_value={
            "total_notifications": 100,
            "batched_notifications": 80,
            "throttled_notifications": 10,
            "delivery_rate": 0.95
        })
        
        # Test the endpoint
        response = test_client.get("/api/notification-batching-throttling/analytics/summary")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "analytics" in data["data"]


class TestNotificationBatchingThrottlingAPIEndpoints:
    """Integration tests for notification batching and throttling API endpoints."""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        return {
            "Authorization": "Bearer test_token",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_system_status_endpoint(self, mock_manager, test_client, auth_headers):
        """Test system status endpoint integration."""
        # Mock metrics
        mock_manager.get_metrics = AsyncMock(return_value={
            "batching": {
                "active_batches": 2,
                "batch_config": {"enabled": True, "max_batch_size": 10}
            },
            "throttling": {
                "active_metrics": 5,
                "throttle_config": {"enabled": True, "rate_limit_per_hour": 50}
            }
        })
        
        # Test endpoint
        response = test_client.get("/api/notification-batching-throttling/status")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "batching" in data["data"]
        assert "throttling" in data["data"]
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_batches_endpoint(self, mock_manager, test_client, auth_headers):
        """Test get batches endpoint integration."""
        # Mock batches
        mock_batch = Mock()
        mock_batch.id = "batch_1"
        mock_batch.user_id = 1
        mock_batch.channel = "email"
        mock_batch.severity = "medium"
        mock_batch.status.value = "pending"
        mock_batch.notifications = []
        mock_batch.priority_score = 5.0
        mock_batch.created_at = datetime.now()
        mock_batch.scheduled_for = None
        
        mock_manager.batching_manager.active_batches = {"batch_1": mock_batch}
        mock_manager.batching_manager.config.max_batch_delay_minutes = 30
        
        # Test endpoint
        response = test_client.get("/api/notification-batching-throttling/batches")
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "active_batches" in data["data"]
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_update_batching_config_endpoint(self, mock_manager, test_client, auth_headers):
        """Test update batching config endpoint integration."""
        # Mock update
        mock_manager.batching_manager.update_config = AsyncMock(return_value=True)
        
        # Test data
        config_data = {
            "enabled": True,
            "max_batch_size": 15,
            "max_batch_delay_minutes": 45
        }
        
        # Test endpoint
        response = test_client.put(
            "/api/notification-batching-throttling/config/batching",
            json=config_data
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_update_throttling_config_endpoint(self, mock_manager, test_client, auth_headers):
        """Test update throttling config endpoint integration."""
        # Mock update
        mock_manager.throttling_manager.update_config = AsyncMock(return_value=True)
        
        # Test data
        config_data = {
            "enabled": True,
            "rate_limit_per_hour": 60,
            "rate_limit_per_day": 250,
            "cooldown_minutes": 10
        }
        
        # Test endpoint
        response = test_client.put(
            "/api/notification-batching-throttling/config/throttling",
            json=config_data
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_test_notification_endpoint(self, mock_manager, test_client, auth_headers):
        """Test notification test endpoint integration."""
        # Mock processing
        mock_manager.process_notification = AsyncMock(return_value={
            "status": "processed",
            "batch_id": "test_batch_1",
            "throttled": False
        })
        
        # Test data
        notification_data = {
            "user_id": 1,
            "channel": "email",
            "subject": "Test Notification",
            "message": "Test message",
            "severity": "medium"
        }
        
        # Test endpoint
        response = test_client.post(
            "/api/notification-batching-throttling/test/notification",
            json=notification_data
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_system_status_error(self, mock_manager, test_client):
        """Test error handling in system status endpoint."""
        # Mock error
        mock_manager.get_metrics = AsyncMock(side_effect=Exception("Test error"))
        
        # Test endpoint
        response = test_client.get("/api/notification-batching-throttling/status")
        
        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to get system status" in data["detail"]
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_get_batch_details_not_found_error(self, mock_manager, test_client):
        """Test error handling for non-existent batch."""
        # Mock empty batches
        mock_manager.batching_manager.active_batches = {}
        
        # Test endpoint
        response = test_client.get("/api/notification-batching-throttling/batches/nonexistent")
        
        # Assertions
        assert response.status_code == 404
        data = response.json()
        assert "Batch not found" in data["detail"]
    
    @patch('src.api.notification_batching_throttling.batching_throttling_manager')
    def test_update_config_validation_error(self, mock_manager, test_client):
        """Test validation error handling in config update."""
        # Mock validation error
        mock_manager.batching_manager.update_config = AsyncMock(side_effect=ValueError("Invalid config"))
        
        # Test data with invalid values
        config_data = {
            "enabled": True,
            "max_batch_size": -1,  # Invalid value
            "max_batch_delay_minutes": 0  # Invalid value
        }
        
        # Test endpoint
        response = test_client.put(
            "/api/notification-batching-throttling/config/batching",
            json=config_data
        )
        
        # Assertions
        assert response.status_code == 500 