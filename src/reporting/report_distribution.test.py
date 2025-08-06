"""
Unit tests for report distribution system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, List, Any

from src.reporting.report_distribution import (
    ReportDistributionManager, DistributionConfig, distribute_weekly_reports, test_report_distribution
)


class TestDistributionConfig:
    """Test the DistributionConfig dataclass."""
    
    def test_distribution_config_creation(self):
        """Test creating a distribution config."""
        config = DistributionConfig(
            template_type='executive_summary',
            include_charts=True,
            delivery_channels=['email', 'slack'],
            priority='high',
            custom_filters={'severity_levels': ['critical', 'high']}
        )
        
        assert config.template_type == 'executive_summary'
        assert config.include_charts is True
        assert config.delivery_channels == ['email', 'slack']
        assert config.priority == 'high'
        assert config.custom_filters == {'severity_levels': ['critical', 'high']}
    
    def test_distribution_config_without_filters(self):
        """Test creating a distribution config without custom filters."""
        config = DistributionConfig(
            template_type='detailed_report',
            include_charts=False,
            delivery_channels=['email'],
            priority='medium'
        )
        
        assert config.template_type == 'detailed_report'
        assert config.include_charts is False
        assert config.delivery_channels == ['email']
        assert config.priority == 'medium'
        assert config.custom_filters is None


class TestReportDistributionManager:
    """Test the report distribution manager functionality."""
    
    @pytest.fixture
    def distribution_manager(self):
        """Create a distribution manager instance."""
        return ReportDistributionManager()
    
    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        user = Mock()
        user.id = 1
        user.email = 'test@example.com'
        user.first_name = 'John'
        user.last_name = 'Doe'
        user.is_active = True
        return user
    
    @pytest.fixture
    def sample_role(self):
        """Create a sample role for testing."""
        role = Mock()
        role.name = 'product_manager'
        role.is_active = True
        return role
    
    @pytest.fixture
    def sample_user_role(self, sample_user, sample_role):
        """Create a sample user role for testing."""
        user_role = Mock()
        user_role.user = sample_user
        user_role.role = sample_role
        user_role.is_active = True
        return user_role
    
    def test_distribution_manager_initialization(self, distribution_manager):
        """Test that distribution manager initializes correctly."""
        assert distribution_manager is not None
        assert hasattr(distribution_manager, 'report_generator')
        assert hasattr(distribution_manager, 'template_manager')
        assert hasattr(distribution_manager, 'notifier')
        assert hasattr(distribution_manager, 'role_configs')
        
        # Check role configurations
        assert 'product_manager' in distribution_manager.role_configs
        assert 'business_analyst' in distribution_manager.role_configs
        assert 'admin' in distribution_manager.role_configs
    
    def test_get_distribution_config(self, distribution_manager):
        """Test getting distribution configuration for roles."""
        # Test valid roles
        pm_config = distribution_manager.get_distribution_config('product_manager')
        assert pm_config is not None
        assert pm_config.template_type == 'executive_summary'
        assert pm_config.delivery_channels == ['email', 'slack']
        assert pm_config.priority == 'high'
        
        ba_config = distribution_manager.get_distribution_config('business_analyst')
        assert ba_config is not None
        assert ba_config.template_type == 'detailed_report'
        assert ba_config.delivery_channels == ['email']
        assert ba_config.priority == 'medium'
        
        # Test invalid role
        invalid_config = distribution_manager.get_distribution_config('invalid_role')
        assert invalid_config is None
    
    def test_update_distribution_config(self, distribution_manager):
        """Test updating distribution configuration."""
        # Update product manager config
        success = distribution_manager.update_distribution_config(
            'product_manager',
            template_type='detailed_report',
            delivery_channels=['email'],
            priority='medium'
        )
        
        assert success is True
        
        # Verify changes
        config = distribution_manager.get_distribution_config('product_manager')
        assert config.template_type == 'detailed_report'
        assert config.delivery_channels == ['email']
        assert config.priority == 'medium'
        
        # Test updating invalid role
        success = distribution_manager.update_distribution_config('invalid_role')
        assert success is False
    
    @patch('src.reporting.report_distribution.get_db')
    async def test_get_users_by_role(self, mock_get_db, distribution_manager, sample_user_role):
        """Test getting users grouped by role."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock user with roles
        user = sample_user_role.user
        user.user_roles = [sample_user_role]
        
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = [user]
        
        # Test getting users by role
        users_by_role = await distribution_manager._get_users_by_role(['product_manager'])
        
        assert 'product_manager' in users_by_role
        assert len(users_by_role['product_manager']) == 1
        assert users_by_role['product_manager'][0] == user
    
    @patch('src.reporting.report_distribution.get_db')
    async def test_get_users_by_role_no_users(self, mock_get_db, distribution_manager):
        """Test getting users by role when no users exist."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock empty result
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.all.return_value = []
        
        # Test getting users by role
        users_by_role = await distribution_manager._get_users_by_role(['product_manager'])
        
        assert users_by_role == {}
    
    @patch.object(ReportDistributionManager, '_generate_role_specific_report')
    async def test_distribute_weekly_reports_no_users(self, mock_generate_report, distribution_manager):
        """Test distributing reports when no users are found."""
        # Mock empty users
        with patch.object(distribution_manager, '_get_users_by_role', return_value={}):
            results = await distribution_manager.distribute_weekly_reports()
        
        assert results['success'] is False
        assert results['message'] == 'No users found for distribution'
        assert results['distribution_results'] == {}
    
    @patch.object(ReportDistributionManager, '_generate_role_specific_report')
    @patch.object(ReportDistributionManager, '_distribute_to_role_users')
    async def test_distribute_weekly_reports_success(self, mock_distribute, mock_generate_report, distribution_manager):
        """Test successful report distribution."""
        # Mock users by role
        mock_user = Mock()
        mock_user.email = 'test@example.com'
        
        users_by_role = {
            'product_manager': [mock_user],
            'business_analyst': [mock_user]
        }
        
        # Mock report generation
        mock_generate_report.return_value = {
            'report_data': {'executive_summary': {'total_changes_detected': 5}},
            'html_content': '<html>Test Report</html>',
            'template_type': 'executive_summary',
            'period': '2024-01-08 to 2024-01-15'
        }
        
        # Mock distribution results
        mock_distribute.return_value = {
            'success': True,
            'users_notified': 1,
            'users_failed': 0,
            'failed_users': [],
            'total_users': 1
        }
        
        with patch.object(distribution_manager, '_get_users_by_role', return_value=users_by_role):
            results = await distribution_manager.distribute_weekly_reports()
        
        assert results['success'] is True
        assert results['total_users_notified'] == 2  # One for each role
        assert results['total_users_failed'] == 0
        assert 'product_manager' in results['distribution_results']
        assert 'business_analyst' in results['distribution_results']
    
    @patch.object(ReportDistributionManager, '_generate_role_specific_report')
    async def test_distribute_weekly_reports_no_report_data(self, mock_generate_report, distribution_manager):
        """Test distributing reports when no report data is generated."""
        # Mock users by role
        mock_user = Mock()
        mock_user.email = 'test@example.com'
        
        users_by_role = {
            'product_manager': [mock_user]
        }
        
        # Mock no report data
        mock_generate_report.return_value = None
        
        with patch.object(distribution_manager, '_get_users_by_role', return_value=users_by_role):
            results = await distribution_manager.distribute_weekly_reports()
        
        assert results['success'] is False
        assert results['distribution_results']['product_manager']['success'] is False
        assert results['distribution_results']['product_manager']['message'] == 'No report data available'
    
    @patch.object(ReportDistributionManager, '_generate_role_specific_report')
    async def test_distribute_weekly_reports_force_distribution(self, mock_generate_report, distribution_manager):
        """Test distributing reports with force distribution enabled."""
        # Mock users by role
        mock_user = Mock()
        mock_user.email = 'test@example.com'
        
        users_by_role = {
            'product_manager': [mock_user]
        }
        
        # Mock report data
        mock_generate_report.return_value = {
            'report_data': {'executive_summary': {'total_changes_detected': 0}},
            'html_content': '<html>Test Report</html>',
            'template_type': 'executive_summary',
            'period': '2024-01-08 to 2024-01-15'
        }
        
        with patch.object(distribution_manager, '_get_users_by_role', return_value=users_by_role):
            with patch.object(distribution_manager, '_distribute_to_role_users') as mock_distribute:
                mock_distribute.return_value = {
                    'success': True,
                    'users_notified': 1,
                    'users_failed': 0,
                    'failed_users': [],
                    'total_users': 1
                }
                
                results = await distribution_manager.distribute_weekly_reports(force_distribution=True)
        
        assert results['success'] is True
        assert mock_generate_report.called
    
    def test_generate_email_subject(self, distribution_manager):
        """Test email subject generation."""
        # Test with critical changes
        report_data = {
            'period': '2024-01-08 to 2024-01-15',
            'report_data': {
                'executive_summary': {
                    'total_changes_detected': 5,
                    'critical_changes': 2
                }
            }
        }
        
        subject = distribution_manager._generate_email_subject(report_data, 'product_manager')
        assert '🚨 URGENT' in subject
        assert '2 Critical Compliance Changes' in subject
        
        # Test with no critical changes
        report_data['report_data']['executive_summary']['critical_changes'] = 0
        subject = distribution_manager._generate_email_subject(report_data, 'product_manager')
        assert '📊 5 Compliance Changes Detected' in subject
        
        # Test with no changes
        report_data['report_data']['executive_summary']['total_changes_detected'] = 0
        subject = distribution_manager._generate_email_subject(report_data, 'product_manager')
        assert '📋 Weekly Compliance Report' in subject
        assert 'No Changes Detected' in subject
    
    def test_generate_email_body(self, distribution_manager):
        """Test email body generation."""
        report_data = {
            'period': '2024-01-08 to 2024-01-15',
            'report_data': {
                'executive_summary': {
                    'total_changes_detected': 5,
                    'critical_changes': 2,
                    'high_priority_changes': 1
                }
            }
        }
        
        body = distribution_manager._generate_email_body(report_data, 'product_manager')
        
        assert 'Weekly Compliance Report' in body
        assert '2024-01-08 to 2024-01-15' in body
        assert 'Total Changes: 5' in body
        assert 'Critical Changes: 2' in body
        assert 'High Priority Changes: 1' in body
        assert 'AI-Powered Compliance Monitoring System' in body
    
    @patch.object(ReportDistributionManager, '_send_email_report')
    @patch.object(ReportDistributionManager, '_send_slack_report')
    async def test_send_report_to_user_success(self, mock_slack, mock_email, distribution_manager):
        """Test successful report sending to user."""
        # Mock user
        user = Mock()
        user.email = 'test@example.com'
        
        # Mock report data
        report_data = {
            'period': '2024-01-08 to 2024-01-15',
            'report_data': {
                'executive_summary': {
                    'total_changes_detected': 5,
                    'critical_changes': 1
                }
            }
        }
        
        # Mock config
        config = DistributionConfig(
            template_type='executive_summary',
            include_charts=True,
            delivery_channels=['email', 'slack'],
            priority='high'
        )
        
        # Mock successful email sending
        mock_email.return_value = True
        
        success = await distribution_manager._send_report_to_user(user, report_data, config, 'product_manager')
        
        assert success is True
        mock_email.assert_called_once()
        # Slack should not be called since email succeeded
        mock_slack.assert_not_called()
    
    @patch.object(ReportDistributionManager, '_send_email_report')
    @patch.object(ReportDistributionManager, '_send_slack_report')
    async def test_send_report_to_user_fallback(self, mock_slack, mock_email, distribution_manager):
        """Test report sending with fallback to second channel."""
        # Mock user
        user = Mock()
        user.email = 'test@example.com'
        
        # Mock report data
        report_data = {
            'period': '2024-01-08 to 2024-01-15',
            'report_data': {
                'executive_summary': {
                    'total_changes_detected': 5,
                    'critical_changes': 1
                }
            }
        }
        
        # Mock config
        config = DistributionConfig(
            template_type='executive_summary',
            include_charts=True,
            delivery_channels=['email', 'slack'],
            priority='high'
        )
        
        # Mock failed email, successful slack
        mock_email.return_value = False
        mock_slack.return_value = True
        
        success = await distribution_manager._send_report_to_user(user, report_data, config, 'product_manager')
        
        assert success is True
        mock_email.assert_called_once()
        mock_slack.assert_called_once()
    
    @patch.object(ReportDistributionManager, '_send_email_report')
    @patch.object(ReportDistributionManager, '_send_slack_report')
    async def test_send_report_to_user_all_failed(self, mock_slack, mock_email, distribution_manager):
        """Test report sending when all channels fail."""
        # Mock user
        user = Mock()
        user.email = 'test@example.com'
        
        # Mock report data
        report_data = {
            'period': '2024-01-08 to 2024-01-15',
            'report_data': {
                'executive_summary': {
                    'total_changes_detected': 5,
                    'critical_changes': 1
                }
            }
        }
        
        # Mock config
        config = DistributionConfig(
            template_type='executive_summary',
            include_charts=True,
            delivery_channels=['email', 'slack'],
            priority='high'
        )
        
        # Mock all channels failing
        mock_email.return_value = False
        mock_slack.return_value = False
        
        success = await distribution_manager._send_report_to_user(user, report_data, config, 'product_manager')
        
        assert success is False
        mock_email.assert_called_once()
        mock_slack.assert_called_once()
    
    @patch.object(ReportDistributionManager, 'distribute_weekly_reports')
    async def test_test_distribution_system(self, mock_distribute, distribution_manager):
        """Test the distribution system test function."""
        # Mock distribution results
        mock_distribute.return_value = {
            'success': True,
            'total_users_notified': 5,
            'total_users_failed': 1,
            'distribution_results': {
                'product_manager': {
                    'success': True,
                    'users_notified': 3,
                    'users_failed': 0
                },
                'business_analyst': {
                    'success': True,
                    'users_notified': 2,
                    'users_failed': 1
                }
            }
        }
        
        results = await distribution_manager.test_distribution_system()
        
        assert results['test_successful'] is True
        assert results['total_users_notified'] == 5
        assert results['total_users_failed'] == 1
        assert 'distribution_results' in results
        assert 'test_period' in results
        
        # Verify the test was called with correct parameters
        mock_distribute.assert_called_once()
        call_args = mock_distribute.call_args
        assert call_args[1]['roles'] == ['product_manager', 'business_analyst']
        assert call_args[1]['force_distribution'] is True


class TestReportDistributionConvenienceFunctions:
    """Test convenience functions for report distribution."""
    
    @patch('src.reporting.report_distribution.ReportDistributionManager')
    async def test_distribute_weekly_reports_convenience(self, mock_manager_class):
        """Test the convenience function for distributing weekly reports."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.distribute_weekly_reports.return_value = {
            'success': True,
            'total_users_notified': 3,
            'total_users_failed': 0
        }
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        results = await distribute_weekly_reports(
            start_date=start_date,
            end_date=end_date,
            roles=['product_manager'],
            force_distribution=False
        )
        
        assert results['success'] is True
        assert results['total_users_notified'] == 3
        assert results['total_users_failed'] == 0
        
        mock_manager.distribute_weekly_reports.assert_called_once_with(
            start_date, end_date, ['product_manager'], False
        )
    
    @patch('src.reporting.report_distribution.ReportDistributionManager')
    async def test_test_report_distribution(self, mock_manager_class):
        """Test the convenience function for testing report distribution."""
        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager
        mock_manager.test_distribution_system.return_value = {
            'test_successful': True,
            'total_users_notified': 2,
            'total_users_failed': 0
        }
        
        results = await test_report_distribution()
        
        assert results['test_successful'] is True
        assert results['total_users_notified'] == 2
        assert results['total_users_failed'] == 0
        
        mock_manager.test_distribution_system.assert_called_once()


class TestReportDistributionIntegration:
    """Integration tests for report distribution."""
    
    @pytest.fixture
    def distribution_manager(self):
        return ReportDistributionManager()
    
    async def test_full_distribution_workflow(self, distribution_manager):
        """Test the complete distribution workflow."""
        # This would test with actual database data in integration tests
        # For now, test the workflow structure
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        # Test with mock data
        with patch.object(distribution_manager, '_get_users_by_role', return_value={}):
            results = await distribution_manager.distribute_weekly_reports(
                start_date=start_date,
                end_date=end_date,
                roles=['product_manager'],
                force_distribution=True
            )
        
        assert results is not None
        assert 'success' in results
        assert 'period' in results
        assert 'total_users_notified' in results
        assert 'total_users_failed' in results
        assert 'distribution_results' in results
    
    def test_role_configurations(self, distribution_manager):
        """Test role-specific configurations."""
        # Test product manager config
        pm_config = distribution_manager.get_distribution_config('product_manager')
        assert pm_config.template_type == 'executive_summary'
        assert 'email' in pm_config.delivery_channels
        assert 'slack' in pm_config.delivery_channels
        assert pm_config.priority == 'high'
        assert pm_config.custom_filters == {'severity_levels': ['critical', 'high']}
        
        # Test business analyst config
        ba_config = distribution_manager.get_distribution_config('business_analyst')
        assert ba_config.template_type == 'detailed_report'
        assert ba_config.delivery_channels == ['email']
        assert ba_config.priority == 'medium'
        assert ba_config.custom_filters is None
        
        # Test admin config
        admin_config = distribution_manager.get_distribution_config('admin')
        assert admin_config.template_type == 'technical_report'
        assert admin_config.delivery_channels == ['email']
        assert admin_config.priority == 'low'
        assert admin_config.custom_filters is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 