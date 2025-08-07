"""
Unit tests for enhanced notification preference manager.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from typing import Dict, List, Any

from src.notifications.preference_manager import (
    EnhancedNotificationPreferenceManager,
    NotificationFrequency,
    NotificationSeverity,
    NotificationChannel,
    RoleBasedDefaults,
    get_preference_manager,
    initialize_user_preferences,
    update_user_preference,
    get_user_preferences,
    should_send_notification
)
from src.database.models import (
    User, Role, UserRole, UserNotificationPreference
)


class TestNotificationConstants:
    """Test notification constants and utility functions."""
    
    def test_notification_frequency_constants(self):
        """Test notification frequency constants."""
        assert NotificationFrequency.IMMEDIATE == "immediate"
        assert NotificationFrequency.HOURLY == "hourly"
        assert NotificationFrequency.DAILY == "daily"
        assert NotificationFrequency.WEEKLY == "weekly"
        assert NotificationFrequency.BUSINESS_HOURS == "business_hours"
        assert NotificationFrequency.CUSTOM == "custom"
    
    def test_get_all_frequencies(self):
        """Test getting all frequencies."""
        frequencies = NotificationFrequency.get_all_frequencies()
        expected = ["immediate", "hourly", "daily", "weekly", "business_hours", "custom"]
        assert frequencies == expected
    
    def test_frequency_display_names(self):
        """Test frequency display names."""
        assert NotificationFrequency.get_frequency_display_name("immediate") == "Immediate"
        assert NotificationFrequency.get_frequency_display_name("hourly") == "Hourly"
        assert NotificationFrequency.get_frequency_display_name("daily") == "Daily"
        assert NotificationFrequency.get_frequency_display_name("weekly") == "Weekly"
        assert NotificationFrequency.get_frequency_display_name("business_hours") == "Business Hours Only"
        assert NotificationFrequency.get_frequency_display_name("custom") == "Custom Schedule"
        assert NotificationFrequency.get_frequency_display_name("unknown") == "Unknown"
    
    def test_notification_severity_constants(self):
        """Test notification severity constants."""
        assert NotificationSeverity.CRITICAL == "critical"
        assert NotificationSeverity.HIGH == "high"
        assert NotificationSeverity.MEDIUM == "medium"
        assert NotificationSeverity.LOW == "low"
        assert NotificationSeverity.ALL == "all"
    
    def test_get_all_severities(self):
        """Test getting all severities."""
        severities = NotificationSeverity.get_all_severities()
        expected = ["critical", "high", "medium", "low", "all"]
        assert severities == expected
    
    def test_severity_display_names(self):
        """Test severity display names."""
        assert NotificationSeverity.get_severity_display_name("critical") == "Critical"
        assert NotificationSeverity.get_severity_display_name("high") == "High"
        assert NotificationSeverity.get_severity_display_name("medium") == "Medium"
        assert NotificationSeverity.get_severity_display_name("low") == "Low"
        assert NotificationSeverity.get_severity_display_name("all") == "All Severities"
        assert NotificationSeverity.get_severity_display_name("unknown") == "Unknown"
    
    def test_notification_channel_constants(self):
        """Test notification channel constants."""
        assert NotificationChannel.EMAIL == "email"
        assert NotificationChannel.SLACK == "slack"
        assert NotificationChannel.TEAMS == "teams"
        assert NotificationChannel.WEBHOOK == "webhook"
        assert NotificationChannel.SMS == "sms"
        assert NotificationChannel.PUSH == "push"
    
    def test_get_all_channels(self):
        """Test getting all channels."""
        channels = NotificationChannel.get_all_channels()
        expected = ["email", "slack", "teams", "webhook", "sms", "push"]
        assert channels == expected
    
    def test_channel_display_names(self):
        """Test channel display names."""
        assert NotificationChannel.get_channel_display_name("email") == "Email"
        assert NotificationChannel.get_channel_display_name("slack") == "Slack"
        assert NotificationChannel.get_channel_display_name("teams") == "Microsoft Teams"
        assert NotificationChannel.get_channel_display_name("webhook") == "Webhook"
        assert NotificationChannel.get_channel_display_name("sms") == "SMS"
        assert NotificationChannel.get_channel_display_name("push") == "Push Notification"
        assert NotificationChannel.get_channel_display_name("unknown") == "Unknown"


class TestRoleBasedDefaults:
    """Test role-based default preferences."""
    
    def test_product_manager_defaults(self):
        """Test product manager default preferences."""
        defaults = RoleBasedDefaults.get_product_manager_defaults()
        assert len(defaults) == 2
        
        # Check email preference
        email_pref = next((p for p in defaults if p['notification_type'] == 'email'), None)
        assert email_pref is not None
        assert email_pref['change_severity'] == 'all'
        assert email_pref['frequency'] == 'immediate'
        assert email_pref['is_enabled'] is True
        
        # Check slack preference
        slack_pref = next((p for p in defaults if p['notification_type'] == 'slack'), None)
        assert slack_pref is not None
        assert slack_pref['change_severity'] == 'high'
        assert slack_pref['frequency'] == 'immediate'
        assert slack_pref['is_enabled'] is True
        assert slack_pref['business_hours_only'] is True
    
    def test_business_analyst_defaults(self):
        """Test business analyst default preferences."""
        defaults = RoleBasedDefaults.get_business_analyst_defaults()
        assert len(defaults) == 3
        
        # Check email preference
        email_pref = next((p for p in defaults if p['notification_type'] == 'email'), None)
        assert email_pref is not None
        assert email_pref['change_severity'] == 'all'
        assert email_pref['frequency'] == 'daily'
        assert email_pref['is_enabled'] is True
        assert email_pref['business_hours_only'] is True
        assert email_pref['batch_notifications'] is True
        assert email_pref['batch_size'] == 10
        
        # Check slack preference
        slack_pref = next((p for p in defaults if p['notification_type'] == 'slack'), None)
        assert slack_pref is not None
        assert slack_pref['change_severity'] == 'medium'
        assert slack_pref['frequency'] == 'hourly'
        assert slack_pref['batch_notifications'] is True
        assert slack_pref['batch_size'] == 5
        
        # Check teams preference
        teams_pref = next((p for p in defaults if p['notification_type'] == 'teams'), None)
        assert teams_pref is not None
        assert teams_pref['change_severity'] == 'critical'
        assert teams_pref['frequency'] == 'immediate'
        assert teams_pref['batch_notifications'] is False
    
    def test_admin_defaults(self):
        """Test admin default preferences."""
        defaults = RoleBasedDefaults.get_admin_defaults()
        assert len(defaults) == 1
        
        email_pref = defaults[0]
        assert email_pref['notification_type'] == 'email'
        assert email_pref['change_severity'] == 'all'
        assert email_pref['frequency'] == 'immediate'
        assert email_pref['is_enabled'] is True
        assert email_pref['business_hours_only'] is False


class TestEnhancedNotificationPreferenceManager:
    """Test the enhanced notification preference manager."""
    
    @pytest.fixture
    def preference_manager(self):
        """Create a preference manager instance."""
        return EnhancedNotificationPreferenceManager()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = 'test_user'
        user.email = 'test@example.com'
        user.first_name = 'Test'
        user.last_name = 'User'
        user.is_active = True
        return user
    
    @pytest.fixture
    def mock_role(self):
        """Create a mock role."""
        role = Mock(spec=Role)
        role.id = 1
        role.name = 'product_manager'
        role.display_name = 'Product Manager'
        role.is_active = True
        return role
    
    @patch('src.notifications.preference_manager.get_db_session')
    def test_initialize_user_preferences(self, mock_get_session, preference_manager, mock_user, mock_role):
        """Test initializing user preferences."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock user roles query
        mock_user_role = Mock()
        mock_user_role.role = mock_role
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_user_role]
        
        # Mock existing preferences query (none exist)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock add and commit
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        result = preference_manager.initialize_user_preferences(1)
        
        assert result is True
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('src.notifications.preference_manager.get_db_session')
    def test_update_user_notification_preference(self, mock_get_session, preference_manager):
        """Test updating user notification preference."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock existing preference query (none exist)
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock add and commit
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        result = preference_manager.update_user_notification_preference(
            user_id=1,
            notification_type='email',
            change_severity='all',
            frequency='immediate',
            is_enabled=True
        )
        
        assert result is True
        mock_session.add.assert_called()
        mock_session.commit.assert_called()
    
    @patch('src.notifications.preference_manager.get_db_session')
    def test_get_user_notification_preferences(self, mock_get_session, preference_manager):
        """Test getting user notification preferences."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock preference objects
        mock_pref1 = Mock()
        mock_pref1.id = 1
        mock_pref1.notification_type = 'email'
        mock_pref1.change_severity = 'all'
        mock_pref1.frequency = 'immediate'
        mock_pref1.is_enabled = True
        mock_pref1.created_at = datetime.now(timezone.utc)
        mock_pref1.updated_at = datetime.now(timezone.utc)
        
        mock_pref2 = Mock()
        mock_pref2.id = 2
        mock_pref2.notification_type = 'slack'
        mock_pref2.change_severity = 'high'
        mock_pref2.frequency = 'daily'
        mock_pref2.is_enabled = False
        mock_pref2.created_at = datetime.now(timezone.utc)
        mock_pref2.updated_at = datetime.now(timezone.utc)
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_pref1, mock_pref2]
        
        result = preference_manager.get_user_notification_preferences(1)
        
        assert len(result) == 2
        assert result[0]['notification_type'] == 'email'
        assert result[0]['notification_type_display'] == 'Email'
        assert result[0]['change_severity'] == 'all'
        assert result[0]['change_severity_display'] == 'All Severities'
        assert result[0]['frequency'] == 'immediate'
        assert result[0]['frequency_display'] == 'Immediate'
        assert result[0]['is_enabled'] is True
        
        assert result[1]['notification_type'] == 'slack'
        assert result[1]['notification_type_display'] == 'Slack'
        assert result[1]['is_enabled'] is False
    
    def test_get_user_preferences_summary(self, preference_manager):
        """Test getting user preferences summary."""
        # Mock get_user_notification_preferences
        mock_preferences = [
            {
                'notification_type': 'email',
                'notification_type_display': 'Email',
                'change_severity': 'all',
                'change_severity_display': 'All Severities',
                'frequency': 'immediate',
                'frequency_display': 'Immediate',
                'is_enabled': True
            },
            {
                'notification_type': 'slack',
                'notification_type_display': 'Slack',
                'change_severity': 'high',
                'change_severity_display': 'High',
                'frequency': 'daily',
                'frequency_display': 'Daily',
                'is_enabled': False
            }
        ]
        
        with patch.object(preference_manager, 'get_user_notification_preferences', return_value=mock_preferences):
            summary = preference_manager.get_user_preferences_summary(1)
            
            assert summary['total_preferences'] == 2
            assert summary['enabled_preferences'] == 1
            assert 'email' in summary['channels']
            assert 'slack' in summary['channels']
            assert summary['channels']['email']['enabled'] == 1
            assert summary['channels']['slack']['enabled'] == 0
    
    @patch('src.notifications.preference_manager.get_db_session')
    def test_should_send_notification(self, mock_get_session, preference_manager):
        """Test should send notification logic."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock preference
        mock_pref = Mock()
        mock_pref.change_severity = 'all'
        mock_pref.frequency = 'immediate'
        mock_pref.is_enabled = True
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pref
        
        result = preference_manager.should_send_notification(1, 'email', 'high')
        assert result is True
    
    @patch('src.notifications.preference_manager.get_db_session')
    def test_should_send_notification_severity_mismatch(self, mock_get_session, preference_manager):
        """Test should send notification with severity mismatch."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock preference
        mock_pref = Mock()
        mock_pref.change_severity = 'critical'
        mock_pref.frequency = 'immediate'
        mock_pref.is_enabled = True
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pref
        
        result = preference_manager.should_send_notification(1, 'email', 'low')
        assert result is False
    
    def test_check_frequency_timing_immediate(self, preference_manager):
        """Test frequency timing check for immediate."""
        change_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = preference_manager._check_frequency_timing('immediate', change_time)
        assert result is True
    
    def test_check_frequency_timing_hourly(self, preference_manager):
        """Test frequency timing check for hourly."""
        # Test within same hour
        change_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        result = preference_manager._check_frequency_timing('hourly', change_time)
        assert result is False
        
        # Test after an hour
        change_time = datetime.now(timezone.utc) - timedelta(hours=2)
        result = preference_manager._check_frequency_timing('hourly', change_time)
        assert result is True
    
    def test_check_frequency_timing_daily(self, preference_manager):
        """Test frequency timing check for daily."""
        # Test within same day
        change_time = datetime.now(timezone.utc) - timedelta(hours=12)
        result = preference_manager._check_frequency_timing('daily', change_time)
        assert result is False
        
        # Test after a day
        change_time = datetime.now(timezone.utc) - timedelta(days=2)
        result = preference_manager._check_frequency_timing('daily', change_time)
        assert result is True
    
    def test_check_frequency_timing_weekly(self, preference_manager):
        """Test frequency timing check for weekly."""
        # Test within same week
        change_time = datetime.now(timezone.utc) - timedelta(days=3)
        result = preference_manager._check_frequency_timing('weekly', change_time)
        assert result is False
        
        # Test after a week
        change_time = datetime.now(timezone.utc) - timedelta(days=10)
        result = preference_manager._check_frequency_timing('weekly', change_time)
        assert result is True
    
    def test_check_frequency_timing_business_hours(self, preference_manager):
        """Test frequency timing check for business hours."""
        # Mock current time to be during business hours (Monday 10 AM)
        with patch('src.notifications.preference_manager.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 15, 10, 0, 0)  # Monday 10 AM
            change_time = datetime(2024, 1, 15, 9, 0, 0)  # Same day 9 AM
            result = preference_manager._check_frequency_timing('business_hours', change_time)
            assert result is True
        
        # Mock current time to be outside business hours (Sunday 10 AM)
        with patch('src.notifications.preference_manager.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 14, 10, 0, 0)  # Sunday 10 AM
            change_time = datetime(2024, 1, 13, 9, 0, 0)  # Saturday 9 AM
            result = preference_manager._check_frequency_timing('business_hours', change_time)
            assert result is False
    
    def test_get_available_options(self, preference_manager):
        """Test getting available options."""
        options = preference_manager.get_available_options()
        
        assert 'frequencies' in options
        assert 'severities' in options
        assert 'channels' in options
        
        # Check frequencies
        freq_values = [f['value'] for f in options['frequencies']]
        expected_freqs = ['immediate', 'hourly', 'daily', 'weekly', 'business_hours', 'custom']
        assert freq_values == expected_freqs
        
        # Check severities
        sev_values = [s['value'] for s in options['severities']]
        expected_sevs = ['critical', 'high', 'medium', 'low', 'all']
        assert sev_values == expected_sevs
        
        # Check channels
        chan_values = [c['value'] for c in options['channels']]
        expected_chans = ['email', 'slack', 'teams', 'webhook', 'sms', 'push']
        assert chan_values == expected_chans
    
    def test_get_role_based_preferences(self, preference_manager):
        """Test getting role-based preferences."""
        # Test product manager
        pm_prefs = preference_manager.get_role_based_preferences('product_manager')
        assert len(pm_prefs) == 2
        assert any(p['notification_type'] == 'email' for p in pm_prefs)
        assert any(p['notification_type'] == 'slack' for p in pm_prefs)
        
        # Test business analyst
        ba_prefs = preference_manager.get_role_based_preferences('business_analyst')
        assert len(ba_prefs) == 3
        assert any(p['notification_type'] == 'email' for p in ba_prefs)
        assert any(p['notification_type'] == 'slack' for p in ba_prefs)
        assert any(p['notification_type'] == 'teams' for p in ba_prefs)
        
        # Test admin
        admin_prefs = preference_manager.get_role_based_preferences('admin')
        assert len(admin_prefs) == 1
        assert admin_prefs[0]['notification_type'] == 'email'
        
        # Test unknown role
        unknown_prefs = preference_manager.get_role_based_preferences('unknown_role')
        assert len(unknown_prefs) == 0


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_preference_manager(self):
        """Test getting preference manager instance."""
        manager = get_preference_manager()
        assert isinstance(manager, EnhancedNotificationPreferenceManager)
    
    @patch('src.notifications.preference_manager.get_preference_manager')
    def test_initialize_user_preferences(self, mock_get_manager):
        """Test initialize user preferences convenience function."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.initialize_user_preferences.return_value = True
        
        result = initialize_user_preferences(1, ['product_manager'])
        
        assert result is True
        mock_manager.initialize_user_preferences.assert_called_with(1, ['product_manager'])
    
    @patch('src.notifications.preference_manager.get_preference_manager')
    def test_update_user_preference(self, mock_get_manager):
        """Test update user preference convenience function."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.update_user_notification_preference.return_value = True
        
        result = update_user_preference(1, 'email', change_severity='all', frequency='immediate')
        
        assert result is True
        mock_manager.update_user_notification_preference.assert_called_with(
            1, 'email', change_severity='all', frequency='immediate'
        )
    
    @patch('src.notifications.preference_manager.get_preference_manager')
    def test_get_user_preferences(self, mock_get_manager):
        """Test get user preferences convenience function."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_preferences = [{'notification_type': 'email', 'is_enabled': True}]
        mock_manager.get_user_notification_preferences.return_value = mock_preferences
        
        result = get_user_preferences(1)
        
        assert result == mock_preferences
        mock_manager.get_user_notification_preferences.assert_called_with(1)
    
    @patch('src.notifications.preference_manager.get_preference_manager')
    def test_should_send_notification(self, mock_get_manager):
        """Test should send notification convenience function."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.should_send_notification.return_value = True
        
        result = should_send_notification(1, 'email', 'high')
        
        assert result is True
        mock_manager.should_send_notification.assert_called_with(1, 'email', 'high', None)


class TestPreferenceManagerIntegration:
    """Integration tests for preference manager."""
    
    @patch('src.notifications.preference_manager.get_db_session')
    def test_full_preference_workflow(self, mock_get_session):
        """Test full preference workflow."""
        # Mock database session
        mock_session = Mock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        
        # Mock user roles
        mock_role = Mock()
        mock_role.name = 'product_manager'
        mock_user_role = Mock()
        mock_user_role.role = mock_role
        
        # Mock queries
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_user_role]
        mock_session.query.return_value.filter.return_value.first.return_value = None
        
        # Mock add and commit
        mock_session.add = Mock()
        mock_session.commit = Mock()
        
        manager = EnhancedNotificationPreferenceManager()
        
        # Initialize preferences
        result = manager.initialize_user_preferences(1)
        assert result is True
        
        # Get preferences
        mock_pref = Mock()
        mock_pref.id = 1
        mock_pref.notification_type = 'email'
        mock_pref.change_severity = 'all'
        mock_pref.frequency = 'immediate'
        mock_pref.is_enabled = True
        mock_pref.created_at = datetime.now(timezone.utc)
        mock_pref.updated_at = datetime.now(timezone.utc)
        
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_pref]
        
        preferences = manager.get_user_notification_preferences(1)
        assert len(preferences) == 1
        assert preferences[0]['notification_type'] == 'email'
        assert preferences[0]['is_enabled'] is True
        
        # Check should send notification
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pref
        should_send = manager.should_send_notification(1, 'email', 'high')
        assert should_send is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 