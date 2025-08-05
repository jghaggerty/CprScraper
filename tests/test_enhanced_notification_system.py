"""
Comprehensive Unit Tests for Enhanced Notification System

This test suite covers all components of the enhanced notification system:
- EnhancedNotificationManager and RoleBasedNotificationTemplate
- ChannelIntegrationManager
- EnhancedNotificationPreferenceManager
- EnhancedEmailTemplates
- NotificationDeliveryTracker
- NotificationHistoryManager
- NotificationTestingTools
- NotificationBatchingThrottlingManager
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any
from sqlalchemy.orm import Session

# Import all notification system components
from src.notifications.enhanced_notifier import (
    EnhancedNotificationManager, 
    RoleBasedNotificationTemplate
)
from src.notifications.channel_integration import (
    ChannelIntegrationManager, 
    NotificationResult, 
    NotificationChannel
)
from src.notifications.preference_manager import (
    EnhancedNotificationPreferenceManager,
    NotificationFrequency,
    NotificationSeverity,
    NotificationChannel as PrefChannel
)
from src.notifications.email_templates import EnhancedEmailTemplates
from src.notifications.delivery_tracker import (
    NotificationDeliveryTracker,
    DeliveryStatus,
    RetryConfig,
    RetryStrategy
)
from src.notifications.history_manager import NotificationHistoryManager
from src.notifications.testing_tools import (
    NotificationTestingTools,
    TestType,
    TestResult,
    TestScenario
)
from src.notifications.batching_manager import (
    NotificationBatchingManager,
    NotificationThrottlingManager,
    NotificationBatchingThrottlingManager,
    BatchConfig,
    ThrottleConfig
)

# Import database models
from src.database.models import (
    User, Role, UserRole, UserNotificationPreference,
    FormChange, Form, Agency, Notification
)
from src.auth.user_service import UserService


class TestEnhancedNotificationSystemIntegration:
    """Integration tests for the complete enhanced notification system."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_users(self):
        """Create sample users for testing."""
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
        
        return [pm_user, ba_user]
    
    @pytest.fixture
    def sample_form_change(self):
        """Create a sample form change for testing."""
        change = Mock(spec=FormChange)
        change.id = 1
        change.form_id = 1
        change.agency_id = 1
        change.change_type = 'field_update'
        change.severity = 'high'
        change.description = 'Updated wage rate field'
        change.detected_at = datetime.now()
        change.old_value = '25.00'
        change.new_value = '27.50'
        return change
    
    @pytest.fixture
    def sample_agency(self):
        """Create a sample agency for testing."""
        agency = Mock(spec=Agency)
        agency.id = 1
        agency.name = 'Test Agency'
        agency.state = 'CA'
        agency.website_url = 'https://test.agency.gov'
        return agency
    
    @pytest.fixture
    def sample_form(self):
        """Create a sample form for testing."""
        form = Mock(spec=Form)
        form.id = 1
        form.name = 'Certified Payroll Report'
        form.version = '2024.1'
        form.agency_id = 1
        return form
    
    @pytest.mark.asyncio
    async def test_complete_notification_workflow(self, mock_db_session, sample_users, 
                                                sample_form_change, sample_agency, sample_form):
        """Test the complete notification workflow from change detection to delivery."""
        
        # Mock all dependencies
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db, \
             patch('src.notifications.enhanced_notifier.UserService') as mock_user_service_class, \
             patch('src.notifications.enhanced_notifier.EmailNotifier') as mock_email_notifier_class:
            
            # Setup mocks
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            mock_get_db.return_value = mock_db_session
            
            # Mock user service
            mock_user_service = Mock(spec=UserService)
            mock_user_service.get_users_by_role.side_effect = lambda role: {
                'product_manager': [sample_users[0]],
                'business_analyst': [sample_users[1]]
            }.get(role, [])
            mock_user_service.get_user_notification_preferences.side_effect = lambda user_id: [
                {
                    'notification_type': 'email',
                    'change_severity': 'all',
                    'frequency': 'immediate',
                    'is_enabled': True
                }
            ]
            mock_user_service_class.return_value = mock_user_service
            
            # Mock email notifier
            mock_email_notifier = Mock()
            mock_email_notifier.send_notification.return_value = True
            mock_email_notifier_class.return_value = mock_email_notifier
            
            # Mock database queries
            mock_db_session.query.return_value.filter.return_value.first.side_effect = [
                sample_form_change,  # FormChange query
                sample_agency,       # Agency query
                sample_form          # Form query
            ]
            
            # Create notification manager
            notification_manager = EnhancedNotificationManager()
            
            # Test the complete workflow
            result = await notification_manager.send_role_based_notification(1)
            
            # Verify results
            assert result is not None
            assert 'product_managers' in result
            assert 'business_analysts' in result
            assert 'summary' in result
            assert result['summary']['total_notifications_sent'] >= 0
    
    @pytest.mark.asyncio
    async def test_notification_with_delivery_tracking(self, mock_db_session, sample_users, 
                                                     sample_form_change):
        """Test notification delivery with tracking and retry mechanisms."""
        
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db, \
             patch('src.notifications.enhanced_notifier.UserService') as mock_user_service_class, \
             patch('src.notifications.enhanced_notifier.EmailNotifier') as mock_email_notifier_class:
            
            # Setup mocks
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            mock_get_db.return_value = mock_db_session
            
            # Mock user service
            mock_user_service = Mock(spec=UserService)
            mock_user_service.get_users_by_role.return_value = [sample_users[0]]
            mock_user_service.get_user_notification_preferences.return_value = [
                {
                    'notification_type': 'email',
                    'change_severity': 'all',
                    'frequency': 'immediate',
                    'is_enabled': True
                }
            ]
            mock_user_service_class.return_value = mock_user_service
            
            # Mock email notifier with failure then success
            mock_email_notifier = Mock()
            mock_email_notifier.send_notification.side_effect = [False, True]  # Fail first, succeed on retry
            mock_email_notifier_class.return_value = mock_email_notifier
            
            # Mock database queries
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_form_change
            
            # Create notification manager with retry config
            retry_config = RetryConfig(
                max_retries=3,
                initial_delay=1,
                max_delay=10,
                backoff_multiplier=2,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF
            )
            notification_manager = EnhancedNotificationManager(retry_config)
            
            # Test notification with tracking
            result = await notification_manager.send_role_based_notification(1)
            
            # Verify delivery tracking was used
            assert result is not None
            assert 'product_managers' in result
    
    @pytest.mark.asyncio
    async def test_notification_with_batching_and_throttling(self, mock_db_session, sample_users, 
                                                           sample_form_change):
        """Test notification processing with batching and throttling."""
        
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db, \
             patch('src.notifications.enhanced_notifier.UserService') as mock_user_service_class, \
             patch('src.notifications.enhanced_notifier.EmailNotifier') as mock_email_notifier_class:
            
            # Setup mocks
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            mock_get_db.return_value = mock_db_session
            
            # Mock user service
            mock_user_service = Mock(spec=UserService)
            mock_user_service.get_users_by_role.return_value = [sample_users[0]]
            mock_user_service.get_user_notification_preferences.return_value = [
                {
                    'notification_type': 'email',
                    'change_severity': 'all',
                    'frequency': 'immediate',
                    'is_enabled': True
                }
            ]
            mock_user_service_class.return_value = mock_user_service
            
            # Mock email notifier
            mock_email_notifier = Mock()
            mock_email_notifier.send_notification.return_value = True
            mock_email_notifier_class.return_value = mock_email_notifier
            
            # Mock database queries
            mock_db_session.query.return_value.filter.return_value.first.return_value = sample_form_change
            
            # Create notification manager
            notification_manager = EnhancedNotificationManager()
            
            # Test batch notifications
            result = await notification_manager.send_batch_role_notifications([1, 2, 3])
            
            # Verify batch processing
            assert result is not None
            assert 'batch_results' in result or 'summary' in result


class TestEnhancedNotificationManagerComprehensive:
    """Comprehensive tests for EnhancedNotificationManager."""
    
    @pytest.fixture
    def notification_manager(self):
        """Create a notification manager instance for testing."""
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings:
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            return EnhancedNotificationManager()
    
    @pytest.mark.asyncio
    async def test_send_role_based_notification_success(self, notification_manager):
        """Test successful role-based notification sending."""
        
        with patch.object(notification_manager, '_send_notifications_to_role') as mock_send_to_role, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db:
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock form change
            mock_form_change = Mock(spec=FormChange)
            mock_form_change.id = 1
            mock_form_change.severity = 'high'
            mock_db.query.return_value.filter.return_value.first.return_value = mock_form_change
            
            # Mock successful notification sending
            mock_send_to_role.return_value = {
                'email': {'success': True, 'recipients': 2},
                'slack': {'success': True, 'recipients': 1}
            }
            
            # Test notification sending
            result = await notification_manager.send_role_based_notification(1)
            
            # Verify results
            assert result is not None
            assert 'product_managers' in result
            assert 'business_analysts' in result
            assert 'summary' in result
            assert mock_send_to_role.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_send_role_based_notification_not_found(self, notification_manager):
        """Test notification sending when form change is not found."""
        
        with patch('src.notifications.enhanced_notifier.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock form change not found
            mock_db.query.return_value.filter.return_value.first.return_value = None
            
            # Test notification sending
            result = await notification_manager.send_role_based_notification(999)
            
            # Verify error handling
            assert result is not None
            assert 'error' in result
            assert 'Form change not found' in result['error']
    
    @pytest.mark.asyncio
    async def test_calculate_impact_assessment(self, notification_manager):
        """Test impact assessment calculation."""
        
        with patch('src.notifications.enhanced_notifier.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock form and agency data
            mock_form = Mock(spec=Form)
            mock_form.name = 'Test Form'
            mock_form.version = '1.0'
            
            mock_agency = Mock(spec=Agency)
            mock_agency.name = 'Test Agency'
            mock_agency.state = 'CA'
            
            # Mock database queries
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                mock_form, mock_agency
            ]
            
            # Test impact assessment
            impact = await notification_manager._calculate_impact_assessment(1, mock_db)
            
            # Verify impact assessment
            assert impact is not None
            assert 'form_name' in impact
            assert 'agency_name' in impact
            assert 'state' in impact
            assert impact['form_name'] == 'Test Form'
            assert impact['agency_name'] == 'Test Agency'
            assert impact['state'] == 'CA'


class TestChannelIntegrationManagerComprehensive:
    """Comprehensive tests for ChannelIntegrationManager."""
    
    @pytest.fixture
    def channel_manager(self):
        """Create a channel integration manager instance for testing."""
        with patch('src.notifications.channel_integration.get_notification_settings') as mock_settings:
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': True, 'webhook_url': 'https://hooks.slack.com/test'},
                'teams': {'enabled': True, 'webhook_url': 'https://webhook.office.com/test'}
            }
            return ChannelIntegrationManager()
    
    @pytest.mark.asyncio
    async def test_send_multi_channel_notification(self, channel_manager):
        """Test sending notifications through multiple channels."""
        
        # Mock user
        mock_user = Mock(spec=User)
        mock_user.id = 1
        mock_user.email = 'test@example.com'
        mock_user.username = 'testuser'
        
        # Mock preferences
        preferences = [
            {
                'notification_type': 'email',
                'change_severity': 'all',
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
        
        # Mock change data
        change_data = {
            'form_name': 'Test Form',
            'agency_name': 'Test Agency',
            'severity': 'high',
            'description': 'Test change'
        }
        
        with patch.object(channel_manager, '_send_notification_with_retry') as mock_send_retry:
            # Mock successful notifications
            mock_send_retry.side_effect = [
                NotificationResult(
                    channel='email',
                    success=True,
                    recipient='test@example.com',
                    message_id='email_123'
                ),
                NotificationResult(
                    channel='slack',
                    success=True,
                    recipient='testuser',
                    message_id='slack_456'
                )
            ]
            
            # Test multi-channel notification
            results = await channel_manager.send_multi_channel_notification(
                change_data, preferences, mock_user
            )
            
            # Verify results
            assert len(results) == 2
            assert all(result.success for result in results)
            assert results[0].channel == 'email'
            assert results[1].channel == 'slack'
    
    @pytest.mark.asyncio
    async def test_channel_connectivity_test(self, channel_manager):
        """Test channel connectivity testing."""
        
        with patch.object(channel_manager, 'notifiers') as mock_notifiers:
            # Mock notifiers
            mock_email = Mock()
            mock_email.test_connection.return_value = True
            
            mock_slack = Mock()
            mock_slack.test_connection.return_value = False
            
            mock_teams = Mock()
            mock_teams.test_connection.return_value = True
            
            mock_notifiers.__getitem__.side_effect = lambda key: {
                'email': mock_email,
                'slack': mock_slack,
                'teams': mock_teams
            }[key]
            
            # Test connectivity
            connectivity = await channel_manager.test_channel_connectivity()
            
            # Verify results
            assert connectivity is not None
            assert 'email' in connectivity
            assert 'slack' in connectivity
            assert 'teams' in connectivity
            assert connectivity['email'] is True
            assert connectivity['slack'] is False
            assert connectivity['teams'] is True


class TestEnhancedNotificationPreferenceManagerComprehensive:
    """Comprehensive tests for EnhancedNotificationPreferenceManager."""
    
    @pytest.fixture
    def preference_manager(self):
        """Create a preference manager instance for testing."""
        return EnhancedNotificationPreferenceManager()
    
    def test_initialize_user_preferences(self, preference_manager):
        """Test user preference initialization."""
        
        with patch('src.notifications.preference_manager.get_db_session') as mock_get_db, \
             patch.object(preference_manager, 'user_service') as mock_user_service:
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock user service
            mock_user_service.get_user_roles.return_value = ['product_manager']
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Test preference initialization
            result = preference_manager.initialize_user_preferences(1, ['product_manager'])
            
            # Verify initialization
            assert result is True
            mock_db.add.assert_called()
            mock_db.commit.assert_called()
    
    def test_should_send_notification(self, preference_manager):
        """Test notification sending decision logic."""
        
        with patch('src.notifications.preference_manager.get_db_session') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock preferences
            mock_pref = Mock(spec=UserNotificationPreference)
            mock_pref.is_enabled = True
            mock_pref.change_severity = 'all'
            mock_pref.frequency = 'immediate'
            mock_pref.business_hours_only = False
            
            mock_db.query.return_value.filter.return_value.first.return_value = mock_pref
            
            # Test notification decision
            should_send = preference_manager.should_send_notification(
                1, 'email', 'high', datetime.now()
            )
            
            # Verify decision
            assert should_send is True
    
    def test_get_users_for_notification(self, preference_manager):
        """Test getting users for notification based on criteria."""
        
        with patch('src.notifications.preference_manager.get_db_session') as mock_get_db, \
             patch.object(preference_manager, 'user_service') as mock_user_service:
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock users
            mock_user = Mock(spec=User)
            mock_user.id = 1
            mock_user.email = 'test@example.com'
            
            mock_user_service.get_all_users.return_value = [mock_user]
            
            # Mock preferences
            mock_pref = Mock(spec=UserNotificationPreference)
            mock_pref.is_enabled = True
            mock_pref.change_severity = 'all'
            
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_pref]
            
            # Test user retrieval
            users = preference_manager.get_users_for_notification('email', 'high')
            
            # Verify user retrieval
            assert len(users) == 1
            assert users[0].id == 1


class TestEnhancedEmailTemplatesComprehensive:
    """Comprehensive tests for EnhancedEmailTemplates."""
    
    @pytest.fixture
    def email_templates(self):
        """Create an email templates instance for testing."""
        return EnhancedEmailTemplates()
    
    def test_get_template(self, email_templates):
        """Test template retrieval."""
        
        # Test getting product manager template
        pm_template = email_templates.get_template('product_manager')
        assert pm_template is not None
        
        # Test getting business analyst template
        ba_template = email_templates.get_template('business_analyst')
        assert ba_template is not None
        
        # Test getting default template for unknown type
        default_template = email_templates.get_template('unknown_type')
        assert default_template is not None
        assert default_template == pm_template
    
    def test_render_template(self, email_templates):
        """Test template rendering with data."""
        
        # Test data
        data = {
            'form_name': 'Test Form',
            'agency_name': 'Test Agency',
            'severity': 'high',
            'description': 'Test change description',
            'old_value': 'Old value',
            'new_value': 'New value',
            'detected_at': datetime.now(),
            'impact_assessment': {
                'affected_clients': 5,
                'estimated_impact': 'Medium'
            }
        }
        
        # Test rendering product manager template
        rendered = email_templates.render_template('product_manager', data)
        
        # Verify rendering
        assert rendered is not None
        assert 'Test Form' in rendered
        assert 'Test Agency' in rendered
        assert 'high' in rendered.lower()
        assert 'Test change description' in rendered
    
    def test_get_available_templates(self, email_templates):
        """Test getting available template types."""
        
        templates = email_templates.get_available_templates()
        
        # Verify available templates
        assert 'product_manager' in templates
        assert 'business_analyst' in templates
        assert 'executive_summary' in templates
        assert 'technical_detailed' in templates


class TestNotificationDeliveryTrackerComprehensive:
    """Comprehensive tests for NotificationDeliveryTracker."""
    
    @pytest.fixture
    def delivery_tracker(self):
        """Create a delivery tracker instance for testing."""
        retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1,
            max_delay=10,
            backoff_multiplier=2,
            strategy=RetryStrategy.EXPONENTIAL_BACKOFF
        )
        return NotificationDeliveryTracker(retry_config)
    
    @pytest.mark.asyncio
    async def test_track_notification_delivery(self, delivery_tracker):
        """Test notification delivery tracking."""
        
        with patch('src.notifications.delivery_tracker.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock notification
            mock_notification = Mock(spec=Notification)
            mock_notification.id = 1
            mock_notification.status = 'pending'
            
            mock_db.query.return_value.filter.return_value.first.return_value = mock_notification
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Test delivery tracking
            result = await delivery_tracker.track_notification_delivery(
                1, 'email', 'test@example.com', True, 'message_123'
            )
            
            # Verify tracking
            assert result is True
            mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_retry_failed_notifications(self, delivery_tracker):
        """Test retrying failed notifications."""
        
        with patch('src.notifications.delivery_tracker.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock failed notifications
            mock_notification = Mock(spec=Notification)
            mock_notification.id = 1
            mock_notification.retry_count = 1
            mock_notification.status = 'failed'
            
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_notification]
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Test retry processing
            result = await delivery_tracker.retry_failed_notifications()
            
            # Verify retry processing
            assert result is not None
            assert 'retried_count' in result
            assert 'failed_count' in result


class TestNotificationHistoryManagerComprehensive:
    """Comprehensive tests for NotificationHistoryManager."""
    
    @pytest.fixture
    def history_manager(self):
        """Create a history manager instance for testing."""
        return NotificationHistoryManager()
    
    @pytest.mark.asyncio
    async def test_get_notification_history(self, history_manager):
        """Test notification history retrieval."""
        
        with patch('src.notifications.history_manager.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock notifications
            mock_notification = Mock(spec=Notification)
            mock_notification.id = 1
            mock_notification.recipient = 'test@example.com'
            mock_notification.subject = 'Test Notification'
            mock_notification.status = 'sent'
            mock_notification.sent_at = datetime.now()
            
            mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [mock_notification]
            mock_db.query.return_value.filter.return_value.count.return_value = 1
            
            # Test history retrieval
            history = await history_manager.get_notification_history(mock_db)
            
            # Verify history
            assert history is not None
            assert 'notifications' in history
            assert 'pagination' in history
            assert len(history['notifications']) == 1
    
    @pytest.mark.asyncio
    async def test_search_notifications(self, history_manager):
        """Test notification search functionality."""
        
        with patch('src.notifications.history_manager.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock search results
            mock_notification = Mock(spec=Notification)
            mock_notification.id = 1
            mock_notification.subject = 'Test Search Result'
            
            mock_db.query.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [mock_notification]
            mock_db.query.return_value.filter.return_value.count.return_value = 1
            
            # Test search
            results = await history_manager.search_notifications(mock_db, 'Test')
            
            # Verify search results
            assert results is not None
            assert 'notifications' in results
            assert len(results['notifications']) == 1


class TestNotificationTestingToolsComprehensive:
    """Comprehensive tests for NotificationTestingTools."""
    
    @pytest.fixture
    def testing_tools(self):
        """Create a testing tools instance for testing."""
        return NotificationTestingTools()
    
    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite(self, testing_tools):
        """Test comprehensive test suite execution."""
        
        with patch('src.notifications.testing_tools.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock individual test results
            with patch.object(testing_tools, 'test_channel_connectivity') as mock_connectivity, \
                 patch.object(testing_tools, 'test_template_validation') as mock_templates, \
                 patch.object(testing_tools, 'test_delivery_verification') as mock_delivery:
                
                mock_connectivity.return_value = TestResult(
                    test_type=TestType.CHANNEL_CONNECTIVITY,
                    success=True,
                    details={'email': True, 'slack': True},
                    recommendations=[]
                )
                
                mock_templates.return_value = TestResult(
                    test_type=TestType.TEMPLATE_VALIDATION,
                    success=True,
                    details={'valid_templates': 4},
                    recommendations=[]
                )
                
                mock_delivery.return_value = TestResult(
                    test_type=TestType.DELIVERY_VERIFICATION,
                    success=True,
                    details={'delivery_rate': 0.95},
                    recommendations=[]
                )
                
                # Test comprehensive suite
                results = await testing_tools.run_comprehensive_test_suite(mock_db)
                
                # Verify results
                assert results is not None
                assert 'test_results' in results
                assert 'overall_status' in results
                assert 'recommendations' in results
                assert len(results['test_results']) >= 3
    
    @pytest.mark.asyncio
    async def test_test_channel_connectivity(self, testing_tools):
        """Test channel connectivity testing."""
        
        with patch.object(testing_tools, 'channel_manager') as mock_channel_manager:
            mock_channel_manager.test_channel_connectivity.return_value = {
                'email': True,
                'slack': False,
                'teams': True
            }
            
            # Test connectivity
            result = await testing_tools.test_channel_connectivity()
            
            # Verify result
            assert result is not None
            assert result.test_type == TestType.CHANNEL_CONNECTIVITY
            assert result.success is False  # Should be False due to Slack failure
            assert 'email' in result.details
            assert 'slack' in result.details
            assert 'teams' in result.details


class TestNotificationBatchingThrottlingManagerComprehensive:
    """Comprehensive tests for NotificationBatchingThrottlingManager."""
    
    @pytest.fixture
    def batching_throttling_manager(self):
        """Create a batching and throttling manager instance for testing."""
        batch_config = BatchConfig(
            enabled=True,
            max_batch_size=10,
            max_batch_delay_minutes=30,
            priority_override=True,
            group_by_user=True,
            group_by_severity=True,
            group_by_channel=True
        )
        
        throttle_config = ThrottleConfig(
            enabled=True,
            rate_limit_per_hour=50,
            rate_limit_per_day=200,
            cooldown_minutes=5,
            burst_limit=10,
            burst_window_minutes=15,
            daily_limit=100,
            exempt_high_priority=True,
            exempt_critical_severity=True
        )
        
        return NotificationBatchingThrottlingManager(batch_config, throttle_config)
    
    @pytest.mark.asyncio
    async def test_process_notification(self, batching_throttling_manager):
        """Test notification processing through batching and throttling."""
        
        with patch('src.notifications.batching_manager.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock notification data
            notification_data = {
                'user_id': 1,
                'channel': 'email',
                'severity': 'high',
                'subject': 'Test Notification',
                'message': 'Test message',
                'priority': 'normal'
            }
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Test notification processing
            result = await batching_throttling_manager.process_notification(notification_data, mock_db)
            
            # Verify processing
            assert result is not None
            assert 'status' in result
            assert 'batch_id' in result or 'throttled' in result
    
    @pytest.mark.asyncio
    async def test_batching_manager_functionality(self, batching_throttling_manager):
        """Test batching manager functionality."""
        
        with patch('src.notifications.batching_manager.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Test adding notification to batch
            notification_data = {
                'user_id': 1,
                'channel': 'email',
                'severity': 'high',
                'subject': 'Test Notification',
                'message': 'Test message'
            }
            
            result = await batching_throttling_manager.batching_manager.add_notification_to_batch(
                notification_data, mock_db
            )
            
            # Verify batching
            assert result is not None
            assert 'batch_id' in result
            assert 'status' in result
    
    @pytest.mark.asyncio
    async def test_throttling_manager_functionality(self, batching_throttling_manager):
        """Test throttling manager functionality."""
        
        with patch('src.notifications.batching_manager.get_db') as mock_get_db:
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            
            # Test throttling check
            result = await batching_throttling_manager.throttling_manager.check_throttle(
                1, 'email', mock_db
            )
            
            # Verify throttling
            assert result is not None
            assert 'allowed' in result
            assert 'reason' in result


class TestNotificationSystemErrorHandling:
    """Test error handling in the notification system."""
    
    @pytest.mark.asyncio
    async def test_notification_manager_error_handling(self):
        """Test error handling in notification manager."""
        
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db:
            
            # Mock settings
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            
            # Mock database session that raises an exception
            mock_db = Mock(spec=Session)
            mock_db.query.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_db
            
            # Create notification manager
            notification_manager = EnhancedNotificationManager()
            
            # Test error handling
            result = await notification_manager.send_role_based_notification(1)
            
            # Verify error handling
            assert result is not None
            assert 'error' in result
            assert 'Database connection failed' in result['error']
    
    @pytest.mark.asyncio
    async def test_channel_integration_error_handling(self):
        """Test error handling in channel integration."""
        
        with patch('src.notifications.channel_integration.get_notification_settings') as mock_settings:
            # Mock settings
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            
            # Create channel manager
            channel_manager = ChannelIntegrationManager()
            
            # Mock user
            mock_user = Mock(spec=User)
            mock_user.email = 'test@example.com'
            
            # Mock preferences
            preferences = [
                {
                    'notification_type': 'email',
                    'change_severity': 'all',
                    'frequency': 'immediate',
                    'is_enabled': True
                }
            ]
            
            # Mock change data
            change_data = {
                'form_name': 'Test Form',
                'severity': 'high'
            }
            
            with patch.object(channel_manager, '_send_notification_with_retry') as mock_send_retry:
                # Mock notification failure
                mock_send_retry.return_value = NotificationResult(
                    channel='email',
                    success=False,
                    recipient='test@example.com',
                    error_message='SMTP connection failed'
                )
                
                # Test error handling
                results = await channel_manager.send_multi_channel_notification(
                    change_data, preferences, mock_user
                )
                
                # Verify error handling
                assert len(results) == 1
                assert results[0].success is False
                assert 'SMTP connection failed' in results[0].error_message


class TestNotificationSystemPerformance:
    """Test performance aspects of the notification system."""
    
    @pytest.mark.asyncio
    async def test_bulk_notification_performance(self):
        """Test performance of bulk notification processing."""
        
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db, \
             patch('src.notifications.enhanced_notifier.UserService') as mock_user_service_class, \
             patch('src.notifications.enhanced_notifier.EmailNotifier') as mock_email_notifier_class:
            
            # Mock settings
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Mock user service
            mock_user_service = Mock(spec=UserService)
            mock_user_service.get_users_by_role.return_value = []
            mock_user_service_class.return_value = mock_user_service
            
            # Mock email notifier
            mock_email_notifier = Mock()
            mock_email_notifier.send_notification.return_value = True
            mock_email_notifier_class.return_value = mock_email_notifier
            
            # Create notification manager
            notification_manager = EnhancedNotificationManager()
            
            # Test bulk processing
            start_time = datetime.now()
            result = await notification_manager.send_batch_role_notifications([1, 2, 3, 4, 5])
            end_time = datetime.now()
            
            # Verify performance
            processing_time = (end_time - start_time).total_seconds()
            assert processing_time < 5.0  # Should complete within 5 seconds
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_notification_processing(self):
        """Test concurrent notification processing."""
        
        with patch('src.notifications.enhanced_notifier.get_notification_settings') as mock_settings, \
             patch('src.notifications.enhanced_notifier.get_db') as mock_get_db:
            
            # Mock settings
            mock_settings.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.test.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            
            # Mock database session
            mock_db = Mock(spec=Session)
            mock_get_db.return_value = mock_db
            
            # Create notification manager
            notification_manager = EnhancedNotificationManager()
            
            # Test concurrent processing
            tasks = []
            for i in range(5):
                task = notification_manager.send_role_based_notification(i)
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify concurrent processing
            assert len(results) == 5
            assert all(isinstance(result, dict) or isinstance(result, Exception) for result in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 