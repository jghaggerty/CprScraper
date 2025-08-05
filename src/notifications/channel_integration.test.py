"""
Unit tests for notification channel integration module.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, List

from src.notifications.channel_integration import (
    ChannelIntegrationManager, 
    NotificationResult, 
    NotificationBatching,
    NotificationChannel
)
from src.database.models import User, UserNotificationPreference


class TestNotificationResult:
    """Test the NotificationResult dataclass."""
    
    def test_notification_result_creation(self):
        """Test creating a NotificationResult instance."""
        result = NotificationResult(
            channel="email",
            success=True,
            recipient="test@example.com",
            message_id="msg_123",
            sent_at=datetime.now()
        )
        
        assert result.channel == "email"
        assert result.success is True
        assert result.recipient == "test@example.com"
        assert result.message_id == "msg_123"
        assert result.retry_count == 0
    
    def test_notification_result_with_error(self):
        """Test creating a NotificationResult with error information."""
        result = NotificationResult(
            channel="slack",
            success=False,
            recipient="test@example.com",
            error_message="Connection failed",
            retry_count=3
        )
        
        assert result.channel == "slack"
        assert result.success is False
        assert result.error_message == "Connection failed"
        assert result.retry_count == 3


class TestChannelIntegrationManager:
    """Test the ChannelIntegrationManager class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock notification configuration."""
        return {
            'email': {
                'enabled': True,
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'password123',
                'from_address': 'alerts@example.com'
            },
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/test'
            },
            'teams': {
                'enabled': True,
                'webhook_url': 'https://webhook.office.com/test'
            }
        }
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = 'testuser'
        user.email = 'test@example.com'
        user.first_name = 'Test'
        user.last_name = 'User'
        return user
    
    @pytest.fixture
    def mock_preferences(self):
        """Create mock user notification preferences."""
        return [
            {
                'notification_type': 'email',
                'change_severity': 'all',
                'frequency': 'immediate',
                'is_enabled': True,
                'business_hours_only': False
            },
            {
                'notification_type': 'slack',
                'change_severity': 'high',
                'frequency': 'immediate',
                'is_enabled': True,
                'business_hours_only': True
            },
            {
                'notification_type': 'teams',
                'change_severity': 'critical',
                'frequency': 'immediate',
                'is_enabled': True,
                'business_hours_only': False
            }
        ]
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    def test_initialization(self, mock_get_settings, mock_config):
        """Test ChannelIntegrationManager initialization."""
        mock_get_settings.return_value = mock_config
        
        manager = ChannelIntegrationManager()
        
        assert manager.config == mock_config
        assert 'email' in manager.notifiers
        assert 'slack' in manager.notifiers
        assert 'teams' in manager.notifiers
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    def test_initialization_disabled_channels(self, mock_get_settings):
        """Test initialization with disabled channels."""
        config = {
            'email': {'enabled': False},
            'slack': {'enabled': False},
            'teams': {'enabled': False}
        }
        mock_get_settings.return_value = config
        
        manager = ChannelIntegrationManager()
        
        assert len(manager.notifiers) == 0
    
    def test_should_send_notification_severity_filter(self, mock_config):
        """Test severity-based notification filtering."""
        with patch('src.notifications.channel_integration.get_notification_settings', return_value=mock_config):
            manager = ChannelIntegrationManager()
            
            # Test high severity preference with medium change
            preference = {'change_severity': 'high', 'business_hours_only': False}
            change_data = {'severity': 'medium'}
            
            should_send = manager._should_send_notification(preference, change_data)
            assert should_send is False
            
            # Test high severity preference with high change
            change_data = {'severity': 'high'}
            should_send = manager._should_send_notification(preference, change_data)
            assert should_send is True
    
    def test_should_send_notification_business_hours(self, mock_config):
        """Test business hours filtering."""
        with patch('src.notifications.channel_integration.get_notification_settings', return_value=mock_config):
            manager = ChannelIntegrationManager()
            
            preference = {'change_severity': 'all', 'business_hours_only': True}
            change_data = {'severity': 'medium'}
            
            # Mock weekend
            with patch('src.notifications.channel_integration.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.weekday.return_value = 6  # Sunday
                mock_now.hour = 10
                mock_datetime.now.return_value = mock_now
                
                should_send = manager._should_send_notification(preference, change_data)
                assert should_send is False
            
            # Mock business hours
            with patch('src.notifications.channel_integration.datetime') as mock_datetime:
                mock_now = Mock()
                mock_now.weekday.return_value = 1  # Tuesday
                mock_now.hour = 14  # 2 PM
                mock_datetime.now.return_value = mock_now
                
                should_send = manager._should_send_notification(preference, change_data)
                assert should_send is True
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    async def test_send_multi_channel_notification(self, mock_get_settings, mock_config, mock_user, mock_preferences):
        """Test sending notifications through multiple channels."""
        mock_get_settings.return_value = mock_config
        
        manager = ChannelIntegrationManager()
        
        # Mock the notifiers
        mock_email_notifier = AsyncMock()
        mock_email_notifier.send_notification.return_value = True
        manager.notifiers['email'] = mock_email_notifier
        
        mock_slack_notifier = AsyncMock()
        mock_slack_notifier.send_notification.return_value = True
        manager.notifiers['slack'] = mock_slack_notifier
        
        change_data = {
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'severity': 'high',
            'change_description': 'Test change'
        }
        
        results = await manager.send_multi_channel_notification(
            change_data, mock_preferences, mock_user
        )
        
        assert len(results) == 3  # email, slack, teams
        assert all(result.success for result in results)
        assert any(result.channel == 'email' for result in results)
        assert any(result.channel == 'slack' for result in results)
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    async def test_send_notification_with_retry(self, mock_get_settings, mock_config, mock_user):
        """Test notification sending with retry logic."""
        mock_get_settings.return_value = mock_config
        
        manager = ChannelIntegrationManager()
        
        # Mock notifier that fails first, then succeeds
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.side_effect = [False, True]
        manager.notifiers['email'] = mock_notifier
        
        change_data = {'severity': 'medium'}
        preference = {'change_severity': 'all'}
        
        result = await manager._send_notification_with_retry(
            'email', change_data, mock_user, preference
        )
        
        assert result.success is True
        assert result.retry_count == 1
        assert result.channel == 'email'
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    async def test_send_notification_max_retries_exceeded(self, mock_get_settings, mock_config, mock_user):
        """Test notification sending when max retries are exceeded."""
        mock_get_settings.return_value = mock_config
        
        manager = ChannelIntegrationManager()
        
        # Mock notifier that always fails
        mock_notifier = AsyncMock()
        mock_notifier.send_notification.return_value = False
        manager.notifiers['email'] = mock_notifier
        
        change_data = {'severity': 'medium'}
        preference = {'change_severity': 'all'}
        
        result = await manager._send_notification_with_retry(
            'email', change_data, mock_user, preference
        )
        
        assert result.success is False
        assert result.retry_count == 3
        assert result.error_message == "Max retries exceeded"
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    async def test_test_channel_connectivity(self, mock_get_settings, mock_config):
        """Test channel connectivity testing."""
        mock_get_settings.return_value = mock_config
        
        manager = ChannelIntegrationManager()
        
        # Mock notifiers
        mock_email = AsyncMock()
        mock_email.send_notification.return_value = True
        manager.notifiers['email'] = mock_email
        
        mock_slack = AsyncMock()
        mock_slack.send_notification.return_value = True
        manager.notifiers['slack'] = mock_slack
        
        results = await manager.test_channel_connectivity()
        
        assert results['email'] is True
        assert results['slack'] is True
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    def test_get_channel_status(self, mock_get_settings, mock_config):
        """Test getting channel status."""
        mock_get_settings.return_value = mock_config
        
        manager = ChannelIntegrationManager()
        
        status = manager.get_channel_status()
        
        assert status['email']['enabled'] is True
        assert status['email']['configured'] is True
        assert status['email']['available'] is True
        
        assert status['slack']['enabled'] is True
        assert status['slack']['configured'] is True
        assert status['slack']['available'] is True


class TestNotificationBatching:
    """Test the NotificationBatching class."""
    
    def test_should_batch_notification(self):
        """Test notification batching logic."""
        batching = NotificationBatching(batch_size=3, batch_window=300)
        
        # First notification should not be batched
        should_batch = batching.should_batch_notification(1, 'email')
        assert should_batch is False
        
        # Add more notifications
        batching.should_batch_notification(1, 'email')
        batching.should_batch_notification(1, 'email')
        
        # Fourth notification should be batched
        should_batch = batching.should_batch_notification(1, 'email')
        assert should_batch is True
    
    def test_get_batched_notifications(self):
        """Test getting batched notifications."""
        batching = NotificationBatching()
        
        # Add some notifications
        batching.should_batch_notification(1, 'email')
        batching.should_batch_notification(1, 'email')
        
        notifications = batching.get_batched_notifications(1, 'email')
        assert len(notifications) == 2
    
    def test_clear_batch(self):
        """Test clearing batched notifications."""
        batching = NotificationBatching()
        
        # Add notifications
        batching.should_batch_notification(1, 'email')
        
        # Clear batch
        batching.clear_batch(1, 'email')
        
        notifications = batching.get_batched_notifications(1, 'email')
        assert len(notifications) == 0


class TestNotificationChannel:
    """Test the NotificationChannel enum."""
    
    def test_notification_channel_values(self):
        """Test notification channel enum values."""
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SLACK.value == "slack"
        assert NotificationChannel.TEAMS.value == "teams"
    
    def test_notification_channel_names(self):
        """Test notification channel enum names."""
        assert NotificationChannel.EMAIL.name == "EMAIL"
        assert NotificationChannel.SLACK.name == "SLACK"
        assert NotificationChannel.TEAMS.name == "TEAMS"


class TestIntegrationScenarios:
    """Test integration scenarios for notification channels."""
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    async def test_full_notification_flow(self, mock_get_settings):
        """Test the full notification flow with multiple channels."""
        config = {
            'email': {'enabled': True, 'smtp_server': 'smtp.example.com'},
            'slack': {'enabled': True, 'webhook_url': 'https://hooks.slack.com/test'},
            'teams': {'enabled': True, 'webhook_url': 'https://webhook.office.com/test'}
        }
        mock_get_settings.return_value = config
        
        manager = ChannelIntegrationManager()
        
        # Mock notifiers
        for channel in ['email', 'slack', 'teams']:
            mock_notifier = AsyncMock()
            mock_notifier.send_notification.return_value = True
            manager.notifiers[channel] = mock_notifier
        
        # Mock user
        user = Mock(spec=User)
        user.id = 1
        user.username = 'testuser'
        user.email = 'test@example.com'
        user.first_name = 'Test'
        user.last_name = 'User'
        
        # Mock preferences
        preferences = [
            {'notification_type': 'email', 'is_enabled': True, 'change_severity': 'all'},
            {'notification_type': 'slack', 'is_enabled': True, 'change_severity': 'high'},
            {'notification_type': 'teams', 'is_enabled': True, 'change_severity': 'critical'}
        ]
        
        # Test data
        change_data = {
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'severity': 'high',
            'change_description': 'Test change',
            'form_change_id': 1
        }
        
        # Send notifications
        results = await manager.send_multi_channel_notification(
            change_data, preferences, user
        )
        
        # Verify results
        assert len(results) == 3
        assert all(result.success for result in results)
        
        # Verify notifiers were called
        for channel in ['email', 'slack', 'teams']:
            assert manager.notifiers[channel].send_notification.called
    
    @patch('src.notifications.channel_integration.get_notification_settings')
    async def test_partial_failure_scenario(self, mock_get_settings):
        """Test scenario where some channels fail."""
        config = {
            'email': {'enabled': True, 'smtp_server': 'smtp.example.com'},
            'slack': {'enabled': True, 'webhook_url': 'https://hooks.slack.com/test'},
            'teams': {'enabled': True, 'webhook_url': 'https://webhook.office.com/test'}
        }
        mock_get_settings.return_value = config
        
        manager = ChannelIntegrationManager()
        
        # Mock notifiers with mixed success/failure
        mock_email = AsyncMock()
        mock_email.send_notification.return_value = True
        manager.notifiers['email'] = mock_email
        
        mock_slack = AsyncMock()
        mock_slack.send_notification.return_value = False
        manager.notifiers['slack'] = mock_slack
        
        mock_teams = AsyncMock()
        mock_teams.send_notification.return_value = True
        manager.notifiers['teams'] = mock_teams
        
        # Mock user and preferences
        user = Mock(spec=User)
        user.email = 'test@example.com'
        
        preferences = [
            {'notification_type': 'email', 'is_enabled': True, 'change_severity': 'all'},
            {'notification_type': 'slack', 'is_enabled': True, 'change_severity': 'all'},
            {'notification_type': 'teams', 'is_enabled': True, 'change_severity': 'all'}
        ]
        
        change_data = {'severity': 'medium', 'form_change_id': 1}
        
        # Send notifications
        results = await manager.send_multi_channel_notification(
            change_data, preferences, user
        )
        
        # Verify mixed results
        success_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        assert len(success_results) == 2  # email and teams
        assert len(failed_results) == 1   # slack


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 