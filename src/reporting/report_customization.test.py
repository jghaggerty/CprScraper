"""
Unit tests for report customization system.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.reporting.report_customization import (
    ReportCustomizationManager, ReportCustomizationOptions, ReportFrequency, ReportFormat,
    create_customization_options_from_request, get_customization_manager
)


class TestReportFrequency:
    """Test the ReportFrequency enum."""
    
    def test_report_frequency_values(self):
        """Test that all frequency values are correct."""
        assert ReportFrequency.DAILY.value == "daily"
        assert ReportFrequency.WEEKLY.value == "weekly"
        assert ReportFrequency.MONTHLY.value == "monthly"
        assert ReportFrequency.QUARTERLY.value == "quarterly"
        assert ReportFrequency.CUSTOM.value == "custom"
    
    def test_report_frequency_creation(self):
        """Test creating frequency from string."""
        assert ReportFrequency("daily") == ReportFrequency.DAILY
        assert ReportFrequency("weekly") == ReportFrequency.WEEKLY
        assert ReportFrequency("monthly") == ReportFrequency.MONTHLY


class TestReportFormat:
    """Test the ReportFormat enum."""
    
    def test_report_format_values(self):
        """Test that all format values are correct."""
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.PDF.value == "pdf"
        assert ReportFormat.CSV.value == "csv"
        assert ReportFormat.EXCEL.value == "excel"
        assert ReportFormat.JSON.value == "json"
    
    def test_report_format_creation(self):
        """Test creating format from string."""
        assert ReportFormat("html") == ReportFormat.HTML
        assert ReportFormat("pdf") == ReportFormat.PDF
        assert ReportFormat("csv") == ReportFormat.CSV


class TestReportCustomizationOptions:
    """Test the ReportCustomizationOptions dataclass."""
    
    def test_customization_options_creation(self):
        """Test creating customization options."""
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            frequency=ReportFrequency.WEEKLY,
            states=['CA', 'NY'],
            form_types=['WH-347'],
            severity_levels=['critical', 'high'],
            template_type='executive_summary'
        )
        
        assert options.start_date == datetime(2024, 1, 1)
        assert options.end_date == datetime(2024, 1, 7)
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.states == ['CA', 'NY']
        assert options.form_types == ['WH-347']
        assert options.severity_levels == ['critical', 'high']
        assert options.template_type == 'executive_summary'
        assert options.include_ai_analysis is True
        assert options.include_charts is True
    
    def test_customization_options_defaults(self):
        """Test default values for customization options."""
        options = ReportCustomizationOptions()
        
        assert options.start_date is None
        assert options.end_date is None
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.states is None
        assert options.include_ai_analysis is True
        assert options.include_charts is True
        assert options.report_format == ReportFormat.HTML
        assert options.template_type == 'detailed_report'
    
    def test_customization_options_to_dict(self):
        """Test converting options to dictionary."""
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            frequency=ReportFrequency.WEEKLY,
            states=['CA', 'NY'],
            report_format=ReportFormat.PDF
        )
        
        data = options.to_dict()
        
        assert data['frequency'] == 'weekly'
        assert data['report_format'] == 'pdf'
        assert data['states'] == ['CA', 'NY']
        assert data['include_ai_analysis'] is True
        assert data['include_charts'] is True
    
    def test_customization_options_from_dict(self):
        """Test creating options from dictionary."""
        data = {
            'start_date': datetime(2024, 1, 1),
            'end_date': datetime(2024, 1, 7),
            'frequency': 'weekly',
            'report_format': 'pdf',
            'states': ['CA', 'NY'],
            'include_ai_analysis': True,
            'include_charts': False
        }
        
        options = ReportCustomizationOptions.from_dict(data)
        
        assert options.start_date == datetime(2024, 1, 1)
        assert options.end_date == datetime(2024, 1, 7)
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.report_format == ReportFormat.PDF
        assert options.states == ['CA', 'NY']
        assert options.include_ai_analysis is True
        assert options.include_charts is False


class TestReportCustomizationManager:
    """Test the report customization manager functionality."""
    
    @pytest.fixture
    def customization_manager(self):
        """Create a customization manager instance."""
        return ReportCustomizationManager()
    
    def test_customization_manager_initialization(self, customization_manager):
        """Test that customization manager initializes correctly."""
        assert customization_manager is not None
        assert hasattr(customization_manager, 'report_generator')
        assert hasattr(customization_manager, 'template_manager')
        assert hasattr(customization_manager, 'available_states')
        assert hasattr(customization_manager, 'available_form_types')
        assert hasattr(customization_manager, 'available_severity_levels')
    
    @patch('src.reporting.report_customization.get_agencies_config')
    def test_get_available_states(self, mock_get_agencies_config, customization_manager):
        """Test getting available states from configuration."""
        # Mock agencies config
        mock_get_agencies_config.return_value = {
            'agencies': [
                {'state': 'CA', 'name': 'California'},
                {'state': 'NY', 'name': 'New York'},
                {'state': 'TX', 'name': 'Texas'},
                {'state': 'CA', 'name': 'California'}  # Duplicate
            ]
        }
        
        # Reinitialize to get fresh states
        manager = ReportCustomizationManager()
        states = manager._get_available_states()
        
        assert 'CA' in states
        assert 'NY' in states
        assert 'TX' in states
        assert len(states) == 3  # No duplicates
        assert states == ['CA', 'NY', 'TX']  # Sorted
    
    @patch('src.reporting.report_customization.get_db')
    def test_get_available_form_types(self, mock_get_db, customization_manager):
        """Test getting available form types from database."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock query result
        mock_db.query.return_value.distinct.return_value.all.return_value = [
            ('WH-347',), ('WH-348',), ('WH-349',), (None,)
        ]
        
        form_types = customization_manager._get_available_form_types()
        
        assert 'WH-347' in form_types
        assert 'WH-348' in form_types
        assert 'WH-349' in form_types
        assert None not in form_types  # None values should be filtered out
    
    @patch('src.reporting.report_customization.get_db')
    def test_get_available_form_types_error(self, mock_get_db, customization_manager):
        """Test getting form types when database error occurs."""
        # Mock database error
        mock_get_db.side_effect = Exception("Database error")
        
        form_types = customization_manager._get_available_form_types()
        
        # Should return default form types
        assert 'WH-347' in form_types
        assert 'WH-348' in form_types
        assert 'WH-349' in form_types
    
    def test_get_available_options(self, customization_manager):
        """Test getting all available options."""
        options = customization_manager.get_available_options()
        
        assert 'states' in options
        assert 'form_types' in options
        assert 'severity_levels' in options
        assert 'priority_levels' in options
        assert 'delivery_channels' in options
        assert 'template_types' in options
        assert 'frequencies' in options
        assert 'formats' in options
        
        # Check specific values
        assert 'critical' in options['severity_levels']
        assert 'email' in options['delivery_channels']
        assert 'executive_summary' in options['template_types']
        assert 'weekly' in options['frequencies']
        assert 'html' in options['formats']
    
    def test_create_default_options_product_manager(self, customization_manager):
        """Test creating default options for product manager."""
        options = customization_manager.create_default_options('product_manager')
        
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.severity_levels == ['critical', 'high']
        assert options.template_type == 'executive_summary'
        assert options.delivery_channels == ['email', 'slack']
        assert options.include_charts is True
    
    def test_create_default_options_business_analyst(self, customization_manager):
        """Test creating default options for business analyst."""
        options = customization_manager.create_default_options('business_analyst')
        
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.template_type == 'detailed_report'
        assert options.delivery_channels == ['email']
        assert options.include_charts is True
        assert options.include_ai_analysis is True
        assert options.include_impact_assessment is True
    
    def test_create_default_options_admin(self, customization_manager):
        """Test creating default options for admin."""
        options = customization_manager.create_default_options('admin')
        
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.template_type == 'technical_report'
        assert options.delivery_channels == ['email']
        assert options.include_charts is False
        assert options.include_monitoring_statistics is True
    
    def test_validate_customization_options_valid(self, customization_manager):
        """Test validation of valid customization options."""
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            states=['CA', 'NY'],
            form_types=['WH-347'],
            severity_levels=['critical', 'high'],
            template_type='executive_summary',
            delivery_channels=['email']
        )
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is True
        assert len(validation['errors']) == 0
    
    def test_validate_customization_options_invalid_dates(self, customization_manager):
        """Test validation with invalid date range."""
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 7),
            end_date=datetime(2024, 1, 1)  # End before start
        )
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is False
        assert "Start date must be before end date" in validation['errors']
    
    def test_validate_customization_options_invalid_states(self, customization_manager):
        """Test validation with invalid states."""
        options = ReportCustomizationOptions(
            states=['CA', 'INVALID_STATE', 'NY']
        )
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is False
        assert "Invalid states" in validation['errors'][0]
    
    def test_validate_customization_options_invalid_form_types(self, customization_manager):
        """Test validation with invalid form types."""
        options = ReportCustomizationOptions(
            form_types=['WH-347', 'INVALID_FORM', 'WH-348']
        )
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is False
        assert "Invalid form types" in validation['errors'][0]
    
    def test_validate_customization_options_invalid_template(self, customization_manager):
        """Test validation with invalid template type."""
        options = ReportCustomizationOptions(
            template_type='invalid_template'
        )
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is False
        assert "Invalid template type" in validation['errors'][0]
    
    def test_validate_customization_options_warnings(self, customization_manager):
        """Test validation warnings."""
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2025, 1, 1),  # Very large range
            frequency=ReportFrequency.DAILY
        )
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is True
        assert len(validation['warnings']) > 0
        assert "Date range is very large" in validation['warnings'][0]
        assert "Daily reports may generate a lot of data" in validation['suggestions'][0]
    
    def test_validate_customization_options_suggestions(self, customization_manager):
        """Test validation suggestions."""
        options = ReportCustomizationOptions()
        
        validation = customization_manager.validate_customization_options(options)
        
        assert validation['valid'] is True
        assert len(validation['suggestions']) > 0
        assert "Consider filtering by specific states" in validation['suggestions'][0]
        assert "Consider filtering by severity levels" in validation['suggestions'][1]
    
    @patch.object(ReportCustomizationManager, 'validate_customization_options')
    @patch.object(ReportCustomizationManager, 'report_generator')
    @patch.object(ReportCustomizationManager, 'template_manager')
    def test_generate_customized_report_success(self, mock_template_manager, mock_report_generator, mock_validate, customization_manager):
        """Test successful customized report generation."""
        # Mock validation
        mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': [], 'suggestions': []}
        
        # Mock report generation
        mock_report_generator.generate_weekly_report.return_value = {
            'executive_summary': {'total_changes_detected': 5}
        }
        
        # Mock template rendering
        mock_template_manager.render_report.return_value = '<html>Test Report</html>'
        
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            template_type='executive_summary'
        )
        
        result = customization_manager.generate_customized_report(options)
        
        assert result['success'] is True
        assert 'report_data' in result
        assert 'html_content' in result
        assert 'customization_options' in result
        assert 'generated_at' in result
        assert 'period' in result
    
    @patch.object(ReportCustomizationManager, 'validate_customization_options')
    def test_generate_customized_report_invalid(self, mock_validate, customization_manager):
        """Test customized report generation with invalid options."""
        # Mock validation failure
        mock_validate.return_value = {
            'valid': False,
            'errors': ['Invalid states'],
            'warnings': [],
            'suggestions': []
        }
        
        options = ReportCustomizationOptions(states=['INVALID_STATE'])
        
        result = customization_manager.generate_customized_report(options)
        
        assert result['success'] is False
        assert result['error'] == 'Invalid customization options'
        assert 'validation_results' in result
    
    @patch.object(ReportCustomizationManager, 'report_generator')
    def test_get_report_preview(self, mock_report_generator, customization_manager):
        """Test getting report preview."""
        # Mock report generation
        mock_report_generator.generate_weekly_report.return_value = {
            'executive_summary': {
                'total_changes_detected': 5,
                'critical_changes': 2,
                'high_priority_changes': 1
            }
        }
        
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            states=['CA', 'NY'],
            form_types=['WH-347']
        )
        
        result = customization_manager.get_report_preview(options)
        
        assert result['success'] is True
        assert 'preview_data' in result
        assert 'customization_options' in result
        assert 'validation_results' in result
        
        preview_data = result['preview_data']
        assert preview_data['total_changes'] == 5
        assert preview_data['critical_changes'] == 2
        assert preview_data['high_priority_changes'] == 1
        assert preview_data['states_covered'] == 2
        assert preview_data['form_types_covered'] == 1
    
    def test_save_user_preferences(self, customization_manager):
        """Test saving user preferences."""
        options = ReportCustomizationOptions(
            frequency=ReportFrequency.WEEKLY,
            template_type='executive_summary'
        )
        
        success = customization_manager.save_user_preferences(1, options, "test_preferences")
        
        assert success is True
    
    def test_load_user_preferences(self, customization_manager):
        """Test loading user preferences."""
        options = customization_manager.load_user_preferences(1, "test_preferences")
        
        assert options is not None
        assert isinstance(options, ReportCustomizationOptions)
    
    def test_get_recommended_options_high_activity(self, customization_manager):
        """Test getting recommended options for high activity."""
        recent_activity = {
            'high_critical_changes': 10,
            'total_changes': 50
        }
        
        options = customization_manager.get_recommended_options('product_manager', recent_activity)
        
        assert options.severity_levels == ['critical', 'high']
        assert options.frequency == ReportFrequency.DAILY
    
    def test_get_recommended_options_normal_activity(self, customization_manager):
        """Test getting recommended options for normal activity."""
        recent_activity = {
            'total_changes': 25
        }
        
        options = customization_manager.get_recommended_options('business_analyst', recent_activity)
        
        assert options.frequency == ReportFrequency.WEEKLY


class TestCustomizationConvenienceFunctions:
    """Test convenience functions for report customization."""
    
    def test_create_customization_options_from_request(self):
        """Test creating options from request data."""
        request_data = {
            'start_date': '2024-01-01T00:00:00Z',
            'end_date': '2024-01-07T00:00:00Z',
            'frequency': 'weekly',
            'report_format': 'pdf',
            'states': ['CA', 'NY'],
            'form_types': ['WH-347'],
            'severity_levels': ['critical', 'high'],
            'include_ai_analysis': True,
            'include_charts': False,
            'template_type': 'executive_summary',
            'delivery_channels': ['email', 'slack']
        }
        
        options = create_customization_options_from_request(request_data)
        
        assert options.start_date == datetime(2024, 1, 1)
        assert options.end_date == datetime(2024, 1, 7)
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.report_format == ReportFormat.PDF
        assert options.states == ['CA', 'NY']
        assert options.form_types == ['WH-347']
        assert options.severity_levels == ['critical', 'high']
        assert options.include_ai_analysis is True
        assert options.include_charts is False
        assert options.template_type == 'executive_summary'
        assert options.delivery_channels == ['email', 'slack']
    
    def test_create_customization_options_from_request_defaults(self):
        """Test creating options from request data with defaults."""
        request_data = {}
        
        options = create_customization_options_from_request(request_data)
        
        assert options.start_date is None
        assert options.end_date is None
        assert options.frequency == ReportFrequency.WEEKLY
        assert options.report_format == ReportFormat.HTML
        assert options.include_ai_analysis is True
        assert options.include_charts is True
        assert options.template_type == 'detailed_report'
    
    def test_get_customization_manager(self):
        """Test getting customization manager instance."""
        manager = get_customization_manager()
        
        assert isinstance(manager, ReportCustomizationManager)
        assert hasattr(manager, 'get_available_options')
        assert hasattr(manager, 'create_default_options')


class TestCustomizationIntegration:
    """Integration tests for report customization."""
    
    @pytest.fixture
    def customization_manager(self):
        return ReportCustomizationManager()
    
    def test_full_customization_workflow(self, customization_manager):
        """Test the complete customization workflow."""
        # Create options
        options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            frequency=ReportFrequency.WEEKLY,
            states=['CA', 'NY'],
            form_types=['WH-347'],
            severity_levels=['critical', 'high'],
            template_type='executive_summary',
            include_charts=True,
            include_ai_analysis=True
        )
        
        # Validate options
        validation = customization_manager.validate_customization_options(options)
        assert validation['valid'] is True
        
        # Get preview
        preview = customization_manager.get_report_preview(options)
        assert preview['success'] is True
        
        # Get available options
        available_options = customization_manager.get_available_options()
        assert 'states' in available_options
        assert 'form_types' in available_options
        
        # Test role-based defaults
        pm_options = customization_manager.create_default_options('product_manager')
        ba_options = customization_manager.create_default_options('business_analyst')
        admin_options = customization_manager.create_default_options('admin')
        
        assert pm_options.template_type == 'executive_summary'
        assert ba_options.template_type == 'detailed_report'
        assert admin_options.template_type == 'technical_report'
    
    def test_customization_options_serialization(self, customization_manager):
        """Test serialization and deserialization of options."""
        original_options = ReportCustomizationOptions(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7),
            frequency=ReportFrequency.WEEKLY,
            report_format=ReportFormat.PDF,
            states=['CA', 'NY'],
            form_types=['WH-347'],
            severity_levels=['critical', 'high'],
            template_type='executive_summary',
            include_charts=True,
            include_ai_analysis=True
        )
        
        # Convert to dict
        data = original_options.to_dict()
        
        # Convert back to options
        restored_options = ReportCustomizationOptions.from_dict(data)
        
        # Verify they match
        assert restored_options.start_date == original_options.start_date
        assert restored_options.end_date == original_options.end_date
        assert restored_options.frequency == original_options.frequency
        assert restored_options.report_format == original_options.report_format
        assert restored_options.states == original_options.states
        assert restored_options.form_types == original_options.form_types
        assert restored_options.severity_levels == original_options.severity_levels
        assert restored_options.template_type == original_options.template_type
        assert restored_options.include_charts == original_options.include_charts
        assert restored_options.include_ai_analysis == original_options.include_ai_analysis


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 