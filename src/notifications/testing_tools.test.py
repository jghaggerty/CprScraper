"""
Unit tests for notification testing and validation tools.

This module contains comprehensive tests for the NotificationTestingTools class
and related functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

from src.notifications.testing_tools import (
    NotificationTestingTools,
    TestType,
    TestResult,
    TestScenario,
    notification_testing_tools
)
from src.database.models import (
    User, Role, UserRole, UserNotificationPreference,
    FormChange, Agency, Form, Notification
)
from src.notifications.delivery_tracker import DeliveryStatus


class TestNotificationTestingTools:
    """Test cases for NotificationTestingTools class."""
    
    @pytest.fixture
    def testing_tools(self):
        """Create a testing tools instance for testing."""
        return NotificationTestingTools()
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def sample_test_data(self):
        """Sample test data for notifications."""
        return {
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'severity': 'medium',
            'change_description': 'Test change description',
            'detected_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'form_url': 'https://example.com/test-form',
            'instructions_url': 'https://example.com/test-instructions',
            'agency_contact_email': 'test@example.com',
            'agency_contact_phone': '(555) 123-4567',
            'ai_confidence_score': 85,
            'ai_change_category': 'form_update',
            'ai_severity_score': 75,
            'ai_reasoning': 'Test AI reasoning',
            'is_cosmetic_change': False
        }
    
    @pytest.fixture
    def sample_users(self):
        """Sample users for testing."""
        return [
            User(id=1, username='test_user1', email='user1@example.com'),
            User(id=2, username='test_user2', email='user2@example.com'),
            User(id=3, username='test_user3', email='user3@example.com')
        ]
    
    @pytest.fixture
    def sample_form_changes(self):
        """Sample form changes for testing."""
        return [
            FormChange(id=1, agency_id=1, form_id=1, change_type='test'),
            FormChange(id=2, agency_id=1, form_id=1, change_type='test'),
            FormChange(id=3, agency_id=1, form_id=1, change_type='test')
        ]

    def test_test_type_enum(self):
        """Test TestType enum values."""
        assert TestType.CHANNEL_CONNECTIVITY.value == "channel_connectivity"
        assert TestType.TEMPLATE_VALIDATION.value == "template_validation"
        assert TestType.DELIVERY_VERIFICATION.value == "delivery_verification"
        assert TestType.PERFORMANCE_TESTING.value == "performance_testing"
        assert TestType.INTEGRATION_TESTING.value == "integration_testing"
        assert TestType.USER_PREFERENCE_TESTING.value == "user_preference_testing"
        assert TestType.RETRY_MECHANISM_TESTING.value == "retry_mechanism_testing"
        assert TestType.BATCH_NOTIFICATION_TESTING.value == "batch_notification_testing"

    def test_test_result_dataclass(self):
        """Test TestResult dataclass."""
        result = TestResult(
            test_type="test_type",
            test_name="Test Name",
            success=True,
            duration=1.5,
            details={"key": "value"},
            error_message=None
        )
        
        assert result.test_type == "test_type"
        assert result.test_name == "Test Name"
        assert result.success is True
        assert result.duration == 1.5
        assert result.details == {"key": "value"}
        assert result.error_message is None
        assert result.timestamp is not None

    def test_test_scenario_dataclass(self):
        """Test TestScenario dataclass."""
        scenario = TestScenario(
            name="Test Scenario",
            description="Test description",
            test_data={"key": "value"},
            expected_channels=["email", "slack"],
            expected_recipients=["user1@example.com"],
            validation_rules={"rule1": "value1"}
        )
        
        assert scenario.name == "Test Scenario"
        assert scenario.description == "Test description"
        assert scenario.test_data == {"key": "value"}
        assert scenario.expected_channels == ["email", "slack"]
        assert scenario.expected_recipients == ["user1@example.com"]
        assert scenario.validation_rules == {"rule1": "value1"}

    @pytest.mark.asyncio
    async def test_test_channel_connectivity_success(self, testing_tools):
        """Test successful channel connectivity test."""
        # Mock channel manager responses
        testing_tools.channel_manager.test_channel_connectivity = AsyncMock(return_value={
            'email': True,
            'slack': True,
            'teams': False
        })
        
        testing_tools.channel_manager.get_channel_status = Mock(return_value={
            'email': {'configured': True, 'enabled': True},
            'slack': {'configured': True, 'enabled': True},
            'teams': {'configured': False, 'enabled': False}
        })
        
        result = await testing_tools.test_channel_connectivity()
        
        assert result.test_type == TestType.CHANNEL_CONNECTIVITY.value
        assert result.test_name == "Channel Connectivity Test"
        assert result.success is False  # Should fail because teams is configured but not working
        assert result.duration > 0
        assert 'connectivity_results' in result.details
        assert 'channel_status' in result.details

    @pytest.mark.asyncio
    async def test_test_channel_connectivity_all_success(self, testing_tools):
        """Test channel connectivity test when all channels work."""
        # Mock all channels working
        testing_tools.channel_manager.test_channel_connectivity = AsyncMock(return_value={
            'email': True,
            'slack': True,
            'teams': True
        })
        
        testing_tools.channel_manager.get_channel_status = Mock(return_value={
            'email': {'configured': True, 'enabled': True},
            'slack': {'configured': True, 'enabled': True},
            'teams': {'configured': True, 'enabled': True}
        })
        
        result = await testing_tools.test_channel_connectivity()
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_test_channel_connectivity_exception(self, testing_tools):
        """Test channel connectivity test with exception."""
        testing_tools.channel_manager.test_channel_connectivity = AsyncMock(side_effect=Exception("Connection failed"))
        
        result = await testing_tools.test_channel_connectivity()
        
        assert result.success is False
        assert "Connection failed" in result.error_message

    @pytest.mark.asyncio
    async def test_test_template_validation_success(self, testing_tools, sample_test_data):
        """Test successful template validation."""
        # Mock email templates
        mock_template = Mock()
        mock_template.render.return_value = f"""
        <html>
            <body>
                <h1>Test Notification</h1>
                <p>Agency: {sample_test_data['agency_name']}</p>
                <p>Form: {sample_test_data['form_name']}</p>
                <p>Severity: {sample_test_data['severity']}</p>
                <p>Description: {sample_test_data['change_description']}</p>
            </body>
        </html>
        """
        
        testing_tools.email_templates.get_template = Mock(return_value=mock_template)
        
        result = await testing_tools.test_template_validation()
        
        assert result.test_type == TestType.TEMPLATE_VALIDATION.value
        assert result.test_name == "Template Validation Test"
        assert result.success is True
        assert result.duration > 0
        assert 'rendered_templates' in result.details
        assert 'template_errors' in result.details

    @pytest.mark.asyncio
    async def test_test_template_validation_failure(self, testing_tools):
        """Test template validation with template errors."""
        # Mock template with missing required elements
        mock_template = Mock()
        mock_template.render.return_value = "<html><body>Incomplete template</body></html>"
        
        testing_tools.email_templates.get_template = Mock(return_value=mock_template)
        
        result = await testing_tools.test_template_validation()
        
        assert result.success is False
        assert len(result.details['template_errors']) > 0

    def test_validate_template_content_success(self, testing_tools):
        """Test template content validation with valid content."""
        content = """
        <html>
            <body>
                <h1>Test Notification</h1>
                <p>Agency: Test Agency</p>
                <p>Form: TEST-001</p>
                <p>Severity: medium</p>
                <p>Description: Test change description</p>
            </body>
        </html>
        """
        
        result = testing_tools._validate_template_content(content, "general")
        
        assert len(result['errors']) == 0
        assert result['content_length'] > 100

    def test_validate_template_content_missing_elements(self, testing_tools):
        """Test template content validation with missing required elements."""
        content = "<html><body>Incomplete template</body></html>"
        
        result = testing_tools._validate_template_content(content, "general")
        
        assert len(result['errors']) > 0
        assert any("Missing required element" in error for error in result['errors'])

    @pytest.mark.asyncio
    async def test_test_delivery_verification_success(self, testing_tools, mock_db_session):
        """Test successful delivery verification."""
        # Mock database operations
        mock_notification = Mock()
        mock_notification.id = 1
        
        mock_db_session.add = Mock()
        mock_db_session.commit = Mock()
        mock_db_session.delete = Mock()
        
        # Mock delivery tracker
        testing_tools.delivery_tracker.get_delivery_metrics = AsyncMock(return_value={
            'total_notifications': 10,
            'successful_deliveries': 8,
            'failed_deliveries': 2
        })
        
        testing_tools.delivery_tracker.should_retry_notification = AsyncMock(return_value=True)
        
        result = await testing_tools.test_delivery_verification(mock_db_session)
        
        assert result.test_type == TestType.DELIVERY_VERIFICATION.value
        assert result.test_name == "Delivery Verification Test"
        assert result.success is True
        assert result.duration > 0
        assert 'delivery_metrics' in result.details
        assert 'retry_result' in result.details

    @pytest.mark.asyncio
    async def test_test_notification_performance_success(self, testing_tools):
        """Test successful performance testing."""
        # Mock channel manager
        testing_tools.channel_manager.test_channel_connectivity = AsyncMock(return_value={
            'email': True,
            'slack': True
        })
        
        # Mock email templates
        mock_template = Mock()
        mock_template.render.return_value = "Test template content"
        testing_tools.email_templates.get_template = Mock(return_value=mock_template)
        
        result = await testing_tools.test_notification_performance()
        
        assert result.test_type == TestType.PERFORMANCE_TESTING.value
        assert result.test_name == "Performance Test"
        assert result.success is True
        assert result.duration > 0
        assert 'channel_connectivity_duration' in result.details
        assert 'template_rendering_duration' in result.details

    @pytest.mark.asyncio
    async def test_test_integration_scenarios_success(self, testing_tools, mock_db_session, sample_users, sample_form_changes):
        """Test successful integration testing."""
        # Mock database queries
        mock_db_session.query.return_value.limit.return_value.all.side_effect = [
            sample_users,  # First call returns users
            sample_form_changes  # Second call returns form changes
        ]
        
        # Mock notification manager
        testing_tools.notification_manager.send_role_based_notification = AsyncMock(return_value={
            'product_managers': {},
            'business_analysts': {},
            'summary': {'total_notifications_sent': 0}
        })
        
        # Mock preference manager
        testing_tools.preference_manager.get_user_preferences = Mock(return_value={
            'email_enabled': True,
            'slack_enabled': False,
            'frequency': 'immediate'
        })
        
        result = await testing_tools.test_integration_scenarios(mock_db_session)
        
        assert result.test_type == TestType.INTEGRATION_TESTING.value
        assert result.test_name == "Integration Test"
        assert result.success is True
        assert result.duration > 0
        assert 'integration_results' in result.details
        assert 'preference_results' in result.details

    @pytest.mark.asyncio
    async def test_test_integration_scenarios_no_data(self, testing_tools, mock_db_session):
        """Test integration testing with no test data available."""
        # Mock empty database queries
        mock_db_session.query.return_value.limit.return_value.all.return_value = []
        
        result = await testing_tools.test_integration_scenarios(mock_db_session)
        
        assert result.success is False
        assert "No test users or form changes available" in result.error_message

    @pytest.mark.asyncio
    async def test_test_user_preferences_success(self, testing_tools, mock_db_session, sample_users):
        """Test successful user preference testing."""
        # Mock database queries
        mock_db_session.query.return_value.limit.return_value.all.return_value = sample_users
        
        # Mock preference manager
        testing_tools.preference_manager.get_user_preferences = Mock(return_value={
            'email_enabled': True,
            'slack_enabled': False,
            'teams_enabled': False,
            'frequency': 'immediate'
        })
        
        testing_tools.preference_manager.should_send_notification = Mock(return_value=True)
        
        result = await testing_tools.test_user_preferences(mock_db_session)
        
        assert result.test_type == TestType.USER_PREFERENCE_TESTING.value
        assert result.test_name == "User Preference Test"
        assert result.success is True
        assert result.duration > 0
        assert 'preference_results' in result.details

    def test_validate_user_preferences_valid(self, testing_tools):
        """Test user preference validation with valid preferences."""
        preferences = {
            'email_enabled': True,
            'slack_enabled': False,
            'teams_enabled': False,
            'frequency': 'immediate'
        }
        
        result = testing_tools._validate_user_preferences(preferences)
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0

    def test_validate_user_preferences_invalid(self, testing_tools):
        """Test user preference validation with invalid preferences."""
        preferences = {
            'email_enabled': True,
            'frequency': 'invalid_frequency'
        }
        
        result = testing_tools._validate_user_preferences(preferences)
        
        assert result['is_valid'] is False
        assert len(result['errors']) > 0

    @pytest.mark.asyncio
    async def test_test_retry_mechanisms_success(self, testing_tools):
        """Test successful retry mechanism testing."""
        # Mock delivery tracker
        testing_tools.delivery_tracker._calculate_retry_delay = Mock(side_effect=[5, 10, 20, 40])
        
        result = await testing_tools.test_retry_mechanisms()
        
        assert result.test_type == TestType.RETRY_MECHANISM_TESTING.value
        assert result.test_name == "Retry Mechanism Test"
        assert result.success is True
        assert result.duration > 0
        assert 'retry_results' in result.details

    @pytest.mark.asyncio
    async def test_test_batch_notifications_success(self, testing_tools, mock_db_session, sample_form_changes):
        """Test successful batch notification testing."""
        # Mock database queries
        mock_db_session.query.return_value.limit.return_value.all.return_value = sample_form_changes
        
        # Mock notification manager
        testing_tools.notification_manager.send_batch_role_notifications = AsyncMock(return_value={
            1: {'success': True},
            2: {'success': True},
            3: {'success': True}
        })
        
        result = await testing_tools.test_batch_notifications(mock_db_session)
        
        assert result.test_type == TestType.BATCH_NOTIFICATION_TESTING.value
        assert result.test_name == "Batch Notification Test"
        assert result.success is True
        assert result.duration > 0
        assert 'batch_result' in result.details
        assert 'batch_duration' in result.details

    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite(self, testing_tools, mock_db_session):
        """Test running comprehensive test suite."""
        # Mock all individual test methods
        testing_tools.test_channel_connectivity = AsyncMock(return_value=TestResult(
            test_type="channel_connectivity",
            test_name="Channel Connectivity Test",
            success=True,
            duration=1.0,
            details={}
        ))
        
        testing_tools.test_template_validation = AsyncMock(return_value=TestResult(
            test_type="template_validation",
            test_name="Template Validation Test",
            success=True,
            duration=0.5,
            details={}
        ))
        
        testing_tools.test_delivery_verification = AsyncMock(return_value=TestResult(
            test_type="delivery_verification",
            test_name="Delivery Verification Test",
            success=True,
            duration=2.0,
            details={}
        ))
        
        testing_tools.test_notification_performance = AsyncMock(return_value=TestResult(
            test_type="performance_testing",
            test_name="Performance Test",
            success=True,
            duration=1.5,
            details={}
        ))
        
        testing_tools.test_integration_scenarios = AsyncMock(return_value=TestResult(
            test_type="integration_testing",
            test_name="Integration Test",
            success=True,
            duration=3.0,
            details={}
        ))
        
        testing_tools.test_user_preferences = AsyncMock(return_value=TestResult(
            test_type="user_preference_testing",
            test_name="User Preference Test",
            success=True,
            duration=1.0,
            details={}
        ))
        
        testing_tools.test_retry_mechanisms = AsyncMock(return_value=TestResult(
            test_type="retry_mechanism_testing",
            test_name="Retry Mechanism Test",
            success=True,
            duration=0.8,
            details={}
        ))
        
        testing_tools.test_batch_notifications = AsyncMock(return_value=TestResult(
            test_type="batch_notification_testing",
            test_name="Batch Notification Test",
            success=True,
            duration=2.5,
            details={}
        ))
        
        result = await testing_tools.run_comprehensive_test_suite(mock_db_session)
        
        assert 'summary' in result
        assert 'test_results' in result
        assert 'recommendations' in result
        assert result['summary']['total_tests'] == 8
        assert result['summary']['passed_tests'] == 8
        assert result['summary']['failed_tests'] == 0
        assert result['summary']['total_duration'] > 0

    def test_generate_recommendations_no_failures(self, testing_tools):
        """Test recommendation generation with no test failures."""
        test_results = [
            TestResult(
                test_type="test1",
                test_name="Test 1",
                success=True,
                duration=1.0,
                details={}
            ),
            TestResult(
                test_type="test2",
                test_name="Test 2",
                success=True,
                duration=1.0,
                details={}
            )
        ]
        
        recommendations = testing_tools._generate_recommendations(test_results)
        
        assert len(recommendations) == 1
        assert "All tests passed" in recommendations[0]

    def test_generate_recommendations_with_failures(self, testing_tools):
        """Test recommendation generation with test failures."""
        test_results = [
            TestResult(
                test_type="channel_connectivity",
                test_name="Channel Connectivity Test",
                success=False,
                duration=1.0,
                details={}
            ),
            TestResult(
                test_type="template_validation",
                test_name="Template Validation Test",
                success=False,
                duration=1.0,
                details={}
            )
        ]
        
        recommendations = testing_tools._generate_recommendations(test_results)
        
        assert len(recommendations) == 2
        assert any("channel configurations" in rec for rec in recommendations)
        assert any("email template syntax" in rec for rec in recommendations)

    @pytest.mark.asyncio
    async def test_generate_test_report(self, testing_tools):
        """Test test report generation."""
        test_results = [
            TestResult(
                test_type="test1",
                test_name="Test 1",
                success=True,
                duration=1.0,
                details={}
            ),
            TestResult(
                test_type="test2",
                test_name="Test 2",
                success=False,
                duration=1.0,
                details={},
                error_message="Test failed"
            )
        ]
        
        report = await testing_tools.generate_test_report(test_results)
        
        assert "NOTIFICATION SYSTEM TEST REPORT" in report
        assert "Test 1" in report
        assert "Test 2" in report
        assert "PASS" in report
        assert "FAIL" in report
        assert "Test failed" in report


class TestNotificationTestingToolsIntegration:
    """Integration tests for notification testing tools."""
    
    @pytest.mark.asyncio
    async def test_full_test_workflow(self):
        """Test the complete testing workflow."""
        tools = NotificationTestingTools()
        
        # Mock all dependencies
        with patch.object(tools.channel_manager, 'test_channel_connectivity') as mock_connectivity, \
             patch.object(tools.channel_manager, 'get_channel_status') as mock_status, \
             patch.object(tools.email_templates, 'get_template') as mock_template, \
             patch.object(tools.delivery_tracker, 'get_delivery_metrics') as mock_metrics, \
             patch.object(tools.delivery_tracker, 'should_retry_notification') as mock_retry:
            
            # Set up mocks
            mock_connectivity.return_value = {'email': True, 'slack': True}
            mock_status.return_value = {
                'email': {'configured': True, 'enabled': True},
                'slack': {'configured': True, 'enabled': True}
            }
            
            mock_template_instance = Mock()
            mock_template_instance.render.return_value = "<html><body>Test template</body></html>"
            mock_template.return_value = mock_template_instance
            
            mock_metrics.return_value = {'total_notifications': 10, 'successful_deliveries': 8}
            mock_retry.return_value = True
            
            # Run a simple test
            result = await tools.test_channel_connectivity()
            
            assert result.success is True
            assert result.test_type == TestType.CHANNEL_CONNECTIVITY.value


class TestGlobalInstance:
    """Test the global notification testing tools instance."""
    
    def test_global_instance_exists(self):
        """Test that the global instance exists and is properly configured."""
        assert notification_testing_tools is not None
        assert isinstance(notification_testing_tools, NotificationTestingTools)
        assert notification_testing_tools.notification_manager is not None
        assert notification_testing_tools.delivery_tracker is not None
        assert notification_testing_tools.channel_manager is not None
        assert notification_testing_tools.preference_manager is not None
        assert notification_testing_tools.email_templates is not None


if __name__ == "__main__":
    pytest.main([__file__]) 