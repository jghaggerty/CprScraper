"""
Unit and integration tests for notification testing API endpoints.

This module contains tests for the notification testing API functionality,
including test execution, result retrieval, and system status monitoring.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.main import app
from src.api.notification_testing import NotificationTestingAPI
from src.notifications.testing_tools import TestResult, TestType
from src.database.models import User, Role, UserRole

client = TestClient(app)


class TestNotificationTestingAPI:
    """Test cases for notification testing API endpoints."""
    
    @pytest.fixture
    def api_instance(self):
        """Create an API instance for testing."""
        return NotificationTestingAPI()
    
    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        return User(
            id=1,
            username='test_user',
            email='test@example.com',
            is_active=True
        )
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return Mock()
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        return {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }

    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite_success(self, api_instance, mock_user, mock_db_session):
        """Test successful comprehensive test suite execution."""
        # Mock the testing tools
        mock_results = {
            'summary': {
                'total_tests': 8,
                'passed_tests': 7,
                'failed_tests': 1,
                'total_duration': 15.5
            },
            'test_results': [
                {
                    'test_type': 'channel_connectivity',
                    'test_name': 'Channel Connectivity Test',
                    'success': True,
                    'duration': 2.0,
                    'details': {},
                    'error_message': None,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ],
            'recommendations': ['Check notification channel configurations']
        }
        
        with patch('src.api.notification_testing.testing_tools.run_comprehensive_test_suite') as mock_run:
            mock_run.return_value = mock_results
            
            result = await api_instance.run_comprehensive_test_suite(
                background_tasks=Mock(),
                db=mock_db_session,
                current_user=mock_user
            )
            
            assert result['success'] is True
            assert result['message'] == 'Comprehensive test suite completed'
            assert 'results' in result
            assert result['results']['summary']['total_tests'] == 8
            assert result['results']['summary']['passed_tests'] == 7

    @pytest.mark.asyncio
    async def test_run_comprehensive_test_suite_failure(self, api_instance, mock_user, mock_db_session):
        """Test comprehensive test suite execution failure."""
        with patch('src.api.notification_testing.testing_tools.run_comprehensive_test_suite') as mock_run:
            mock_run.side_effect = Exception("Test suite failed")
            
            with pytest.raises(Exception) as exc_info:
                await api_instance.run_comprehensive_test_suite(
                    background_tasks=Mock(),
                    db=mock_db_session,
                    current_user=mock_user
                )
            
            assert "Test suite failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_individual_test_success(self, api_instance, mock_user, mock_db_session):
        """Test successful individual test execution."""
        mock_result = TestResult(
            test_type='channel_connectivity',
            test_name='Channel Connectivity Test',
            success=True,
            duration=1.5,
            details={'connectivity_results': {'email': True}},
            error_message=None
        )
        
        with patch('src.api.notification_testing.testing_tools.test_channel_connectivity') as mock_test:
            mock_test.return_value = mock_result
            
            result = await api_instance.run_individual_test(
                test_type='channel_connectivity',
                test_config={},
                db=mock_db_session,
                current_user=mock_user
            )
            
            assert result['success'] is True
            assert result['message'] == "Individual test 'channel_connectivity' completed"
            assert result['result']['test_type'] == 'channel_connectivity'
            assert result['result']['success'] is True

    @pytest.mark.asyncio
    async def test_run_individual_test_invalid_type(self, api_instance, mock_user, mock_db_session):
        """Test individual test execution with invalid test type."""
        with pytest.raises(Exception) as exc_info:
            await api_instance.run_individual_test(
                test_type='invalid_test_type',
                test_config={},
                db=mock_db_session,
                current_user=mock_user
            )
        
        assert "Invalid test type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_individual_test_failure(self, api_instance, mock_user, mock_db_session):
        """Test individual test execution failure."""
        with patch('src.api.notification_testing.testing_tools.test_channel_connectivity') as mock_test:
            mock_test.side_effect = Exception("Test failed")
            
            with pytest.raises(Exception) as exc_info:
                await api_instance.run_individual_test(
                    test_type='channel_connectivity',
                    test_config={},
                    db=mock_db_session,
                    current_user=mock_user
                )
            
            assert "Test failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_available_test_types(self, api_instance, mock_user):
        """Test getting available test types."""
        result = await api_instance.get_available_test_types(current_user=mock_user)
        
        assert result['success'] is True
        assert 'test_types' in result
        assert 'categories' in result
        
        # Check that all expected test types are present
        test_type_values = [tt['value'] for tt in result['test_types']]
        expected_types = [
            'channel_connectivity',
            'template_validation',
            'delivery_verification',
            'performance_testing',
            'integration_testing',
            'user_preference_testing',
            'retry_mechanism_testing',
            'batch_notification_testing'
        ]
        
        for expected_type in expected_types:
            assert expected_type in test_type_values

    @pytest.mark.asyncio
    async def test_run_test_scenario_success(self, api_instance, mock_user, mock_db_session):
        """Test successful test scenario execution."""
        scenario_data = {
            'name': 'Test Scenario',
            'description': 'Test description',
            'test_data': {'key': 'value'},
            'expected_channels': ['email'],
            'expected_recipients': ['test@example.com'],
            'validation_rules': {'rule1': 'value1'}
        }
        
        # Mock the testing tools methods
        with patch('src.api.notification_testing.testing_tools.test_channel_connectivity') as mock_connectivity, \
             patch('src.api.notification_testing.testing_tools.test_template_validation') as mock_template, \
             patch('src.api.notification_testing.testing_tools.test_integration_scenarios') as mock_integration, \
             patch('src.api.notification_testing.testing_tools.generate_test_report') as mock_report:
            
            mock_connectivity.return_value = TestResult(
                test_type='channel_connectivity',
                test_name='Channel Connectivity Test',
                success=True,
                duration=1.0,
                details={}
            )
            
            mock_template.return_value = TestResult(
                test_type='template_validation',
                test_name='Template Validation Test',
                success=True,
                duration=0.5,
                details={}
            )
            
            mock_integration.return_value = TestResult(
                test_type='integration_testing',
                test_name='Integration Test',
                success=True,
                duration=2.0,
                details={}
            )
            
            mock_report.return_value = "Test Report Content"
            
            result = await api_instance.run_test_scenario(
                scenario=Mock(**scenario_data),
                db=mock_db_session,
                current_user=mock_user
            )
            
            assert result['success'] is True
            assert result['message'] == "Test scenario 'Test Scenario' completed"
            assert 'scenario' in result
            assert 'results' in result
            assert 'report' in result

    @pytest.mark.asyncio
    async def test_run_test_scenario_invalid(self, api_instance, mock_user, mock_db_session):
        """Test test scenario execution with invalid scenario."""
        invalid_scenario = Mock(name='', test_data={})
        
        with pytest.raises(Exception) as exc_info:
            await api_instance.run_test_scenario(
                scenario=invalid_scenario,
                db=mock_db_session,
                current_user=mock_user
            )
        
        assert "Invalid test scenario" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_test_status(self, api_instance, mock_user):
        """Test getting test status."""
        # Mock channel manager
        with patch('src.api.notification_testing.testing_tools.get_channel_status') as mock_status:
            mock_status.return_value = {
                'email': {'configured': True, 'enabled': True},
                'slack': {'configured': False, 'enabled': False},
                'teams': {'configured': False, 'enabled': False}
            }
            
            result = await api_instance.get_test_status(current_user=mock_user)
            
            assert result['success'] is True
            assert result['status'] == 'ready'
            assert 'channel_status' in result
            assert 'health_indicators' in result
            assert 'available_channels' in result
            assert 'configured_channels' in result

    @pytest.mark.asyncio
    async def test_get_test_status_failure(self, api_instance, mock_user):
        """Test getting test status with failure."""
        with patch('src.api.notification_testing.testing_tools.get_channel_status') as mock_status:
            mock_status.side_effect = Exception("Status check failed")
            
            with pytest.raises(Exception) as exc_info:
                await api_instance.get_test_status(current_user=mock_user)
            
            assert "Status check failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_test_report_text_format(self, api_instance, mock_user):
        """Test generating test report in text format."""
        test_results = [
            {
                'test_type': 'channel_connectivity',
                'test_name': 'Channel Connectivity Test',
                'success': True,
                'duration': 1.5,
                'details': {},
                'error_message': None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        with patch('src.api.notification_testing.testing_tools.generate_test_report') as mock_report:
            mock_report.return_value = "Test Report Content"
            
            result = await api_instance.generate_test_report(
                test_results=test_results,
                format='text',
                current_user=mock_user
            )
            
            assert result['success'] is True
            assert result['format'] == 'text'
            assert result['report'] == "Test Report Content"

    @pytest.mark.asyncio
    async def test_generate_test_report_json_format(self, api_instance, mock_user):
        """Test generating test report in JSON format."""
        test_results = [
            {
                'test_type': 'channel_connectivity',
                'test_name': 'Channel Connectivity Test',
                'success': True,
                'duration': 1.5,
                'details': {},
                'error_message': None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        ]
        
        with patch('src.api.notification_testing.testing_tools._generate_recommendations') as mock_recommendations:
            mock_recommendations.return_value = ['All tests passed!']
            
            result = await api_instance.generate_test_report(
                test_results=test_results,
                format='json',
                current_user=mock_user
            )
            
            assert result['success'] is True
            assert result['format'] == 'json'
            assert 'report' in result
            assert result['report']['summary']['total_tests'] == 1
            assert result['report']['summary']['passed_tests'] == 1

    @pytest.mark.asyncio
    async def test_validate_notification_configuration_success(self, api_instance, mock_user):
        """Test successful configuration validation."""
        # Mock configuration
        with patch('src.api.notification_testing.testing_tools.config') as mock_config:
            mock_config.return_value = {
                'email': {
                    'enabled': True,
                    'smtp_server': 'smtp.example.com',
                    'smtp_port': 587,
                    'username': 'test@example.com',
                    'password': 'password',
                    'from_address': 'test@example.com'
                },
                'slack': {
                    'enabled': False,
                    'webhook_url': None
                },
                'teams': {
                    'enabled': False,
                    'webhook_url': None
                }
            }
            
            result = await api_instance.validate_notification_configuration(current_user=mock_user)
            
            assert result['success'] is True
            assert 'validation' in result
            assert result['validation']['configuration_valid'] is True
            assert len(result['validation']['errors']) == 0

    @pytest.mark.asyncio
    async def test_validate_notification_configuration_failure(self, api_instance, mock_user):
        """Test configuration validation with errors."""
        # Mock configuration with missing required fields
        with patch('src.api.notification_testing.testing_tools.config') as mock_config:
            mock_config.return_value = {
                'email': {
                    'enabled': True,
                    'smtp_server': 'smtp.example.com',
                    # Missing required fields
                },
                'slack': {
                    'enabled': False
                },
                'teams': {
                    'enabled': False
                }
            }
            
            result = await api_instance.validate_notification_configuration(current_user=mock_user)
            
            assert result['success'] is True
            assert 'validation' in result
            assert result['validation']['configuration_valid'] is False
            assert len(result['validation']['errors']) > 0

    @pytest.mark.asyncio
    async def test_get_test_history(self, api_instance, mock_user, mock_db_session):
        """Test getting test history."""
        result = await api_instance.get_test_history(
            limit=50,
            offset=0,
            test_type=None,
            status=None,
            db=mock_db_session,
            current_user=mock_user
        )
        
        assert result['success'] is True
        assert result['message'] == "Test history feature not yet implemented"
        assert 'test_history' in result
        assert result['total_count'] == 0

    @pytest.mark.asyncio
    async def test_clear_test_data(self, api_instance, mock_user, mock_db_session):
        """Test clearing test data."""
        result = await api_instance.clear_test_data(
            db=mock_db_session,
            current_user=mock_user
        )
        
        assert result['success'] is True
        assert result['message'] == "Test data cleared successfully"


class TestNotificationTestingAPIEndpoints:
    """Test cases for notification testing API endpoints using FastAPI TestClient."""
    
    @pytest.fixture
    def auth_headers(self):
        """Create authentication headers for testing."""
        return {
            'Authorization': 'Bearer test_token',
            'Content-Type': 'application/json'
        }

    def test_get_test_types_endpoint(self, auth_headers):
        """Test GET /api/notification-testing/test-types endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth:
            mock_auth.return_value = Mock(id=1, username='test_user')
            
            response = client.get('/api/notification-testing/test-types', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'test_types' in data
            assert 'categories' in data

    def test_get_test_status_endpoint(self, auth_headers):
        """Test GET /api/notification-testing/test-status endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.testing_tools.get_channel_status') as mock_status:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_status.return_value = {
                'email': {'configured': True, 'enabled': True},
                'slack': {'configured': False, 'enabled': False}
            }
            
            response = client.get('/api/notification-testing/test-status', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['status'] == 'ready'

    def test_run_comprehensive_test_endpoint(self, auth_headers):
        """Test POST /api/notification-testing/run-comprehensive-test endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.get_db') as mock_db, \
             patch('src.api.notification_testing.testing_tools.run_comprehensive_test_suite') as mock_run:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_db.return_value = Mock()
            mock_run.return_value = {
                'summary': {'total_tests': 8, 'passed_tests': 7, 'failed_tests': 1},
                'test_results': [],
                'recommendations': []
            }
            
            response = client.post('/api/notification-testing/run-comprehensive-test', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['message'] == 'Comprehensive test suite completed'

    def test_run_individual_test_endpoint(self, auth_headers):
        """Test POST /api/notification-testing/run-individual-test endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.get_db') as mock_db, \
             patch('src.api.notification_testing.testing_tools.test_channel_connectivity') as mock_test:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_db.return_value = Mock()
            mock_test.return_value = TestResult(
                test_type='channel_connectivity',
                test_name='Channel Connectivity Test',
                success=True,
                duration=1.5,
                details={}
            )
            
            response = client.post(
                '/api/notification-testing/run-individual-test',
                headers=auth_headers,
                json={
                    'test_type': 'channel_connectivity',
                    'test_config': {}
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['result']['test_type'] == 'channel_connectivity'

    def test_validate_configuration_endpoint(self, auth_headers):
        """Test POST /api/notification-testing/validate-configuration endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.testing_tools.config') as mock_config:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_config.return_value = {
                'email': {'enabled': True, 'smtp_server': 'smtp.example.com'},
                'slack': {'enabled': False},
                'teams': {'enabled': False}
            }
            
            response = client.post('/api/notification-testing/validate-configuration', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert 'validation' in data

    def test_get_test_report_endpoint(self, auth_headers):
        """Test GET /api/notification-testing/test-report endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.testing_tools.generate_test_report') as mock_report:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_report.return_value = "Test Report Content"
            
            response = client.get(
                '/api/notification-testing/test-report?format=text',
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['format'] == 'text'

    def test_get_test_history_endpoint(self, auth_headers):
        """Test GET /api/notification-testing/test-history endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.get_db') as mock_db:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_db.return_value = Mock()
            
            response = client.get('/api/notification-testing/test-history', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['message'] == "Test history feature not yet implemented"

    def test_clear_test_data_endpoint(self, auth_headers):
        """Test DELETE /api/notification-testing/clear-test-data endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.get_db') as mock_db:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_db.return_value = Mock()
            
            response = client.delete('/api/notification-testing/clear-test-data', headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            assert data['message'] == "Test data cleared successfully"

    def test_unauthorized_access(self):
        """Test unauthorized access to endpoints."""
        # Test without authentication headers
        response = client.get('/api/notification-testing/test-types')
        assert response.status_code == 401

        response = client.post('/api/notification-testing/run-comprehensive-test')
        assert response.status_code == 401

    def test_invalid_test_type(self, auth_headers):
        """Test invalid test type in individual test endpoint."""
        with patch('src.api.notification_testing.get_current_user') as mock_auth, \
             patch('src.api.notification_testing.get_db') as mock_db:
            
            mock_auth.return_value = Mock(id=1, username='test_user')
            mock_db.return_value = Mock()
            
            response = client.post(
                '/api/notification-testing/run-individual-test',
                headers=auth_headers,
                json={
                    'test_type': 'invalid_test_type',
                    'test_config': {}
                }
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "Invalid test type" in data['detail']


if __name__ == "__main__":
    pytest.main([__file__]) 