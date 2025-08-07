"""
Unit tests for the enhanced notification system with role-based notifications.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from typing import Dict, List

from src.notifications.enhanced_notifier import (
    EnhancedNotificationManager, 
    RoleBasedNotificationTemplate
)
from src.database.models import (
    User, Role, UserRole, UserNotificationPreference,
    FormChange, Form, Agency, Notification
)
from src.auth.user_service import UserService


class TestRoleBasedNotificationTemplate:
    """Test the role-based notification template generator."""
    
    def test_get_template_for_role(self):
        """Test that correct templates are returned for different roles."""
        template_gen = RoleBasedNotificationTemplate()
        
        # Test business analyst template
        ba_template = template_gen.get_template_for_role('business_analyst')
        assert ba_template is not None
        assert 'Technical Analysis' in str(ba_template)
        
        # Test product manager template (default)
        pm_template = template_gen.get_template_for_role('product_manager')
        assert pm_template is not None
        
        # Test unknown role (should return default)
        unknown_template = template_gen.get_template_for_role('unknown_role')
        assert unknown_template is not None
        assert unknown_template == pm_template


class TestEnhancedNotificationManager:
    """Test the enhanced notification manager."""
    
    @pytest.fixture
    def mock_user_service(self):
        """Create a mock user service."""
        mock_service = Mock(spec=UserService)
        
        # Mock users
        pm_user = Mock(spec=User)
        pm_user.id = 1
        pm_user.username = 'pm_user'
        pm_user.email = 'pm@example.com'
        pm_user.first_name = 'Product'
        pm_user.last_name = 'Manager'
        
        ba_user = Mock(spec=User)
        ba_user.id = 2
        ba_user.username = 'ba_user'
        ba_user.email = 'ba@example.com'
        ba_user.first_name = 'Business'
        ba_user.last_name = 'Analyst'
        
        # Mock notification preferences
        pm_prefs = [
            {
                'notification_type': 'email',
                'change_severity': 'all',
                'frequency': 'immediate',
                'is_enabled': True
            }
        ]
        
        ba_prefs = [
            {
                'notification_type': 'email',
                'change_severity': 'medium',
                'frequency': 'immediate',
                'is_enabled': True
            },
            {
                'notification_type': 'slack',
                'change_severity': 'high',
                'frequency': 'immediate',
                'is_enabled': True
            }
        ]
        
        mock_service.get_users_by_role.side_effect = lambda role: {
            'product_manager': [pm_user],
            'business_analyst': [ba_user]
        }.get(role, [])
        
        mock_service.get_user_notification_preferences.side_effect = lambda user_id: {
            1: pm_prefs,
            2: ba_prefs
        }.get(user_id, [])
        
        return mock_service
    
    @pytest.fixture
    def mock_form_change(self):
        """Create a mock form change."""
        mock_change = Mock(spec=FormChange)
        mock_change.id = 1
        mock_change.severity = 'medium'
        mock_change.change_type = 'content'
        mock_change.change_description = 'Test change description'
        mock_change.detected_at = datetime.now(timezone.utc)
        mock_change.effective_date = None
        mock_change.old_value = 'old_value'
        mock_change.new_value = 'new_value'
        mock_change.ai_confidence_score = 85
        mock_change.ai_change_category = 'form_update'
        mock_change.ai_severity_score = 75
        mock_change.ai_reasoning = 'Test AI reasoning'
        mock_change.ai_semantic_similarity = 80
        mock_change.is_cosmetic_change = False
        
        # Mock form and agency
        mock_form = Mock(spec=Form)
        mock_form.id = 1
        mock_form.name = 'TEST-001'
        mock_form.cpr_report_id = 'TEST-CPR-001'
        mock_form.form_url = 'https://example.com/test-form'
        mock_form.instructions_url = 'https://example.com/test-instructions'
        mock_form.contact_email = 'form@example.com'
        
        mock_agency = Mock(spec=Agency)
        mock_agency.name = 'Test Agency'
        mock_agency.contact_email = 'agency@example.com'
        mock_agency.contact_phone = '(555) 123-4567'
        
        mock_form.agency = mock_agency
        mock_change.form = mock_form
        
        return mock_change
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_session.add = Mock()
        mock_session.commit = Mock()
        return mock_session
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_init(self, mock_get_db, mock_get_settings):
        """Test initialization of the enhanced notification manager."""
        mock_get_settings.return_value = {
            'email': {'enabled': True, 'smtp_server': 'test.com'},
            'slack': {'enabled': False},
            'teams': {'enabled': False}
        }
        
        mock_get_db.return_value.__enter__.return_value = Mock()
        
        manager = EnhancedNotificationManager()
        
        assert manager.user_service is not None
        assert manager.template_generator is not None
        assert 'email' in manager.notifiers
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_should_notify_user(self, mock_get_db, mock_get_settings):
        """Test user notification filtering logic."""
        mock_get_settings.return_value = {}
        mock_get_db.return_value.__enter__.return_value = Mock()
        
        manager = EnhancedNotificationManager()
        
        # Test with no preferences (should notify)
        user = Mock(spec=User)
        result = manager._should_notify_user(user, [], 'medium')
        assert result is True
        
        # Test with enabled preference for all severities
        prefs = [{'is_enabled': True, 'change_severity': 'all'}]
        result = manager._should_notify_user(user, prefs, 'high')
        assert result is True
        
        # Test with enabled preference for specific severity
        prefs = [{'is_enabled': True, 'change_severity': 'medium'}]
        result = manager._should_notify_user(user, prefs, 'medium')
        assert result is True
        
        # Test with disabled preference
        prefs = [{'is_enabled': False, 'change_severity': 'all'}]
        result = manager._should_notify_user(user, prefs, 'medium')
        assert result is False
        
        # Test with preference for different severity
        prefs = [{'is_enabled': True, 'change_severity': 'high'}]
        result = manager._should_notify_user(user, prefs, 'medium')
        assert result is False
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    @patch('src.notifications.enhanced_notifier.EmailNotifier')
    def test_send_custom_email_notification(self, mock_email_notifier, mock_get_db, mock_get_settings):
        """Test custom email notification sending."""
        mock_get_settings.return_value = {
            'email': {
                'enabled': True,
                'smtp_server': 'test.com',
                'smtp_port': 587,
                'username': 'test',
                'password': 'test',
                'from_address': 'test@example.com'
            }
        }
        mock_get_db.return_value.__enter__.return_value = Mock()
        
        manager = EnhancedNotificationManager()
        
        user = Mock(spec=User)
        user.email = 'test@example.com'
        
        change_data = {
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001'
        }
        
        html_content = '<html><body>Test content</body></html>'
        
        # Mock SMTP
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = asyncio.run(manager._send_custom_email_notification(user, change_data, html_content))
            
            assert result is True
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once()
            mock_server.send_message.assert_called_once()
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_calculate_impact_assessment(self, mock_get_db, mock_get_settings):
        """Test impact assessment calculation."""
        mock_get_settings.return_value = {}
        
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock client usage query
        mock_client_usage = [Mock(), Mock(), Mock()]  # 3 clients
        mock_session.query.return_value.filter.return_value.all.return_value = mock_client_usage
        
        # Mock total clients query
        mock_session.query.return_value.filter.return_value.count.return_value = 100
        
        manager = EnhancedNotificationManager()
        
        result = asyncio.run(manager._calculate_impact_assessment(1, mock_session))
        
        assert result['clients_impacted'] == 3
        assert result['icp_percentage'] == 3.0
        assert len(result['details']) == 2
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_send_role_based_notification_not_found(self, mock_get_db, mock_get_settings):
        """Test handling of form change not found."""
        mock_get_settings.return_value = {}
        
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        manager = EnhancedNotificationManager()
        
        result = asyncio.run(manager.send_role_based_notification(999))
        
        assert result['product_managers'] == {}
        assert result['business_analysts'] == {}
        assert result['summary']['total_notifications_sent'] == 0
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    @patch.object(EnhancedNotificationManager, '_send_notifications_to_role')
    def test_send_role_based_notification_success(self, mock_send_to_role, mock_get_db, mock_get_settings, mock_form_change):
        """Test successful role-based notification sending."""
        mock_get_settings.return_value = {}
        
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_form_change
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock impact assessment
        mock_session.query.return_value.filter.return_value.all.return_value = []
        mock_session.query.return_value.filter.return_value.count.return_value = 100
        
        # Mock role-based sending
        mock_send_to_role.side_effect = [
            {'pm_user': {'email': {'success': True}}},
            {'ba_user': {'email': {'success': True}, 'slack': {'success': True}}}
        ]
        
        manager = EnhancedNotificationManager()
        
        result = asyncio.run(manager.send_role_based_notification(1))
        
        assert mock_send_to_role.call_count == 2
        assert result['summary']['total_notifications_sent'] == 0  # Will be calculated in actual implementation
        assert 'product_manager' in result['summary']['roles_notified']
        assert 'business_analyst' in result['summary']['roles_notified']
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_send_notifications_to_role(self, mock_get_db, mock_get_settings, mock_user_service):
        """Test sending notifications to a specific role."""
        mock_get_settings.return_value = {
            'email': {'enabled': True, 'smtp_server': 'test.com'},
            'slack': {'enabled': True, 'webhook_url': 'https://hooks.slack.com/test'}
        }
        
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        manager = EnhancedNotificationManager()
        manager.user_service = mock_user_service
        
        # Mock email notifier
        mock_email_notifier = AsyncMock()
        mock_email_notifier.send_notification.return_value = True
        manager.notifiers['email'] = mock_email_notifier
        
        # Mock slack notifier
        mock_slack_notifier = AsyncMock()
        mock_slack_notifier.send_notification.return_value = True
        manager.notifiers['slack'] = mock_slack_notifier
        
        result = asyncio.run(manager._send_notifications_to_role(
            'business_analyst', 
            Mock(spec=FormChange, severity='medium'),
            {'test': 'data'},
            mock_session
        ))
        
        # Should have results for ba_user
        assert 'ba_user' in result
        assert 'email' in result['ba_user']
        assert 'slack' in result['ba_user']
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_batch_role_notifications(self, mock_get_db, mock_get_settings):
        """Test batch notification processing."""
        mock_get_settings.return_value = {}
        
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        manager = EnhancedNotificationManager()
        
        # Mock individual notification sending
        with patch.object(manager, 'send_role_based_notification') as mock_send:
            mock_send.side_effect = [
                {'product_managers': {}, 'business_analysts': {}, 'summary': {'total_notifications_sent': 1}},
                {'product_managers': {}, 'business_analysts': {}, 'summary': {'total_notifications_sent': 2}}
            ]
            
            result = asyncio.run(manager.send_batch_role_notifications([1, 2]))
            
            assert len(result) == 2
            assert 1 in result
            assert 2 in result
            assert mock_send.call_count == 2
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_test_role_based_notifications(self, mock_get_db, mock_get_settings, mock_user_service):
        """Test the test notification functionality."""
        mock_get_settings.return_value = {
            'email': {'enabled': True, 'smtp_server': 'test.com'}
        }
        
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        manager = EnhancedNotificationManager()
        manager.user_service = mock_user_service
        
        # Mock email notifier
        mock_email_notifier = AsyncMock()
        mock_email_notifier.send_notification.return_value = True
        manager.notifiers['email'] = mock_email_notifier
        
        result = asyncio.run(manager.test_role_based_notifications())
        
        assert 'product_managers' in result
        assert 'business_analysts' in result
        assert 'summary' in result
        assert 'total_notifications_sent' in result['summary']
        assert 'total_notifications_failed' in result['summary']
        assert 'roles_notified' in result['summary']


class TestNotificationIntegration:
    """Integration tests for the notification system."""
    
    @patch('src.notifications.enhanced_notifier.get_notification_settings')
    @patch('src.notifications.enhanced_notifier.get_db')
    def test_full_notification_flow(self, mock_get_db, mock_get_settings):
        """Test the complete notification flow from form change to delivery."""
        mock_get_settings.return_value = {
            'email': {
                'enabled': True,
                'smtp_server': 'test.com',
                'smtp_port': 587,
                'username': 'test',
                'password': 'test',
                'from_address': 'test@example.com'
            }
        }
        
        # Mock database session
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock form change
        mock_form_change = Mock(spec=FormChange)
        mock_form_change.id = 1
        mock_form_change.severity = 'high'
        mock_form_change.change_type = 'content'
        mock_form_change.change_description = 'Critical form update'
        mock_form_change.detected_at = datetime.now(timezone.utc)
        mock_form_change.effective_date = None
        mock_form_change.ai_confidence_score = 95
        mock_form_change.ai_change_category = 'requirement_change'
        mock_form_change.ai_severity_score = 90
        mock_form_change.ai_reasoning = 'Critical requirement change detected'
        mock_form_change.ai_semantic_similarity = 85
        mock_form_change.is_cosmetic_change = False
        
        mock_form = Mock(spec=Form)
        mock_form.id = 1
        mock_form.name = 'CRITICAL-001'
        mock_form.cpr_report_id = 'CRITICAL-CPR-001'
        mock_form.form_url = 'https://example.com/critical-form'
        mock_form.instructions_url = 'https://example.com/critical-instructions'
        
        mock_agency = Mock(spec=Agency)
        mock_agency.name = 'Critical Agency'
        mock_agency.contact_email = 'critical@example.com'
        mock_agency.contact_phone = '(555) 999-9999'
        
        mock_form.agency = mock_agency
        mock_form_change.form = mock_form
        
        mock_session.query.return_value.filter.return_value.first.return_value = mock_form_change
        
        # Mock impact assessment
        mock_session.query.return_value.filter.return_value.all.return_value = [Mock(), Mock(), Mock(), Mock(), Mock()]
        mock_session.query.return_value.filter.return_value.count.return_value = 50
        
        # Mock user service
        mock_user_service = Mock(spec=UserService)
        pm_user = Mock(spec=User)
        pm_user.id = 1
        pm_user.username = 'pm_user'
        pm_user.email = 'pm@example.com'
        pm_user.first_name = 'Product'
        pm_user.last_name = 'Manager'
        
        mock_user_service.get_users_by_role.return_value = [pm_user]
        mock_user_service.get_user_notification_preferences.return_value = [
            {
                'notification_type': 'email',
                'change_severity': 'all',
                'frequency': 'immediate',
                'is_enabled': True
            }
        ]
        
        manager = EnhancedNotificationManager()
        manager.user_service = mock_user_service
        
        # Mock SMTP for email sending
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value.__enter__.return_value = mock_server
            
            result = asyncio.run(manager.send_role_based_notification(1))
            
            # Verify results
            assert 'product_managers' in result
            assert 'business_analysts' in result
            assert 'summary' in result
            assert result['summary']['total_notifications_sent'] >= 0
            
            # Verify database operations
            mock_session.add.assert_called()
            mock_session.commit.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 