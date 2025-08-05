"""
Unit tests for weekly report generation service.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Any

from src.reporting.weekly_reports import (
    WeeklyReportGenerator, generate_weekly_report, export_weekly_report
)
from src.database.models import (
    FormChange, Form, Agency, Client, ClientFormUsage, 
    MonitoringRun, Notification
)


class TestWeeklyReportGenerator:
    """Test the weekly report generator functionality."""
    
    @pytest.fixture
    def report_generator(self):
        """Create a report generator instance."""
        return WeeklyReportGenerator()
    
    @pytest.fixture
    def sample_form_changes(self):
        """Create sample form changes for testing."""
        return [
            {
                'id': 1,
                'form_name': 'WH-347',
                'form_title': 'Statement of Compliance',
                'agency_name': 'Department of Labor',
                'agency_type': 'federal',
                'change_type': 'content',
                'change_description': 'Updated wage determination requirements',
                'severity': 'high',
                'detected_at': datetime.now() - timedelta(days=2),
                'effective_date': datetime.now() + timedelta(days=30),
                'status': 'detected',
                'ai_confidence_score': 85,
                'ai_change_category': 'requirement_change',
                'ai_severity_score': 80,
                'is_cosmetic_change': False,
                'ai_reasoning': 'This change modifies core wage determination logic'
            },
            {
                'id': 2,
                'form_name': 'A1-131',
                'form_title': 'Application for Prevailing Wage',
                'agency_name': 'California Department of Industrial Relations',
                'agency_type': 'state',
                'change_type': 'metadata',
                'change_description': 'Updated contact information',
                'severity': 'low',
                'detected_at': datetime.now() - timedelta(days=5),
                'effective_date': None,
                'status': 'detected',
                'ai_confidence_score': 92,
                'ai_change_category': 'cosmetic_update',
                'ai_severity_score': 20,
                'is_cosmetic_change': True,
                'ai_reasoning': 'This appears to be a cosmetic update to contact information'
            }
        ]
    
    @pytest.fixture
    def sample_monitoring_stats(self):
        """Create sample monitoring statistics."""
        return {
            'total_runs': 100,
            'successful_runs': 95,
            'failed_runs': 5,
            'success_rate': 95.0,
            'avg_response_time_ms': 1250,
            'agency_breakdown': {
                'Department of Labor': {
                    'total_runs': 50,
                    'successful_runs': 48,
                    'failed_runs': 2,
                    'changes_detected': 3
                },
                'California Department of Industrial Relations': {
                    'total_runs': 50,
                    'successful_runs': 47,
                    'failed_runs': 3,
                    'changes_detected': 2
                }
            },
            'period': {
                'start_date': datetime.now() - timedelta(days=7),
                'end_date': datetime.now()
            }
        }
    
    @pytest.fixture
    def sample_notification_summary(self):
        """Create sample notification summary."""
        return {
            'total_notifications': 25,
            'delivered': 23,
            'failed': 2,
            'pending': 0,
            'delivery_rate': 92.0,
            'type_breakdown': {
                'email': {
                    'total': 20,
                    'delivered': 19,
                    'failed': 1,
                    'pending': 0
                },
                'slack': {
                    'total': 5,
                    'delivered': 4,
                    'failed': 1,
                    'pending': 0
                }
            },
            'period': {
                'start_date': datetime.now() - timedelta(days=7),
                'end_date': datetime.now()
            }
        }
    
    def test_report_generator_initialization(self, report_generator):
        """Test that report generator initializes correctly."""
        assert report_generator is not None
        assert hasattr(report_generator, 'export_utils')
        assert hasattr(report_generator, 'notifier')
    
    @patch('src.reporting.weekly_reports.get_db')
    def test_generate_weekly_report_default_period(self, mock_get_db, report_generator):
        """Test generating weekly report with default date range."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock form changes query
        mock_form_changes = []
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.order_by.return_value.all.return_value = mock_form_changes
        
        # Mock monitoring statistics
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Mock notification summary
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Generate report
        report = report_generator.generate_weekly_report()
        
        assert report is not None
        assert 'report_metadata' in report
        assert 'executive_summary' in report
        assert 'form_changes' in report
        assert 'impact_assessments' in report
        assert 'monitoring_statistics' in report
        assert 'notification_summary' in report
        assert 'trend_analysis' in report
        assert 'recommendations' in report
        
        # Check metadata
        metadata = report['report_metadata']
        assert 'generated_at' in metadata
        assert 'start_date' in metadata
        assert 'end_date' in metadata
        assert 'report_period' in metadata
    
    @patch('src.reporting.weekly_reports.get_db')
    def test_generate_weekly_report_with_filters(self, mock_get_db, report_generator):
        """Test generating weekly report with specific filters."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock form changes query
        mock_form_changes = []
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.options.return_value.order_by.return_value.all.return_value = mock_form_changes
        
        # Mock other queries
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Generate report with filters
        start_date = datetime.now() - timedelta(days=14)
        end_date = datetime.now()
        report = report_generator.generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            states=['federal'],
            form_types=['WH-347'],
            severity_levels=['high', 'critical']
        )
        
        assert report is not None
        metadata = report['report_metadata']
        assert metadata['start_date'] == start_date
        assert metadata['end_date'] == end_date
        assert metadata['filters_applied']['states'] == ['federal']
        assert metadata['filters_applied']['form_types'] == ['WH-347']
        assert metadata['filters_applied']['severity_levels'] == ['high', 'critical']
    
    def test_generate_executive_summary(self, report_generator, sample_form_changes, sample_monitoring_stats, sample_notification_summary):
        """Test executive summary generation."""
        summary = report_generator._generate_executive_summary(
            sample_form_changes, sample_monitoring_stats, sample_notification_summary
        )
        
        assert summary['total_changes_detected'] == 2
        assert summary['critical_changes'] == 0
        assert summary['high_priority_changes'] == 1
        
        # Check severity breakdown
        severity_breakdown = summary['severity_breakdown']
        assert severity_breakdown['high'] == 1
        assert severity_breakdown['low'] == 1
        
        # Check agency breakdown
        agency_breakdown = summary['agency_breakdown']
        assert agency_breakdown['Department of Labor'] == 1
        assert agency_breakdown['California Department of Industrial Relations'] == 1
        
        # Check change type breakdown
        change_type_breakdown = summary['change_type_breakdown']
        assert change_type_breakdown['content'] == 1
        assert change_type_breakdown['metadata'] == 1
        
        # Check monitoring performance
        monitoring_perf = summary['monitoring_performance']
        assert monitoring_perf['success_rate'] == 95.0
        assert monitoring_perf['total_runs'] == 100
        
        # Check notification performance
        notification_perf = summary['notification_performance']
        assert notification_perf['delivery_rate'] == 92.0
        assert notification_perf['total_notifications'] == 25
    
    def test_generate_executive_summary_no_data(self, report_generator):
        """Test executive summary generation with no data."""
        summary = report_generator._generate_executive_summary([], None, None)
        
        assert summary['total_changes_detected'] == 0
        assert summary['critical_changes'] == 0
        assert summary['high_priority_changes'] == 0
        assert summary['severity_breakdown'] == {}
        assert summary['agency_breakdown'] == {}
        assert summary['change_type_breakdown'] == {}
        assert summary['monitoring_performance']['success_rate'] == 0
        assert summary['notification_performance']['delivery_rate'] == 0
    
    def test_generate_trend_analysis(self, report_generator):
        """Test trend analysis generation."""
        # Mock database session
        mock_db = Mock()
        
        # Mock daily changes query
        mock_daily_changes = [
            (datetime.now() - timedelta(days=6), 2),
            (datetime.now() - timedelta(days=5), 1),
            (datetime.now() - timedelta(days=4), 3),
            (datetime.now() - timedelta(days=3), 0),
            (datetime.now() - timedelta(days=2), 2),
            (datetime.now() - timedelta(days=1), 1),
            (datetime.now(), 1)
        ]
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_daily_changes
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        trend_analysis = report_generator._generate_trend_analysis(mock_db, start_date, end_date)
        
        assert 'daily_trends' in trend_analysis
        assert 'avg_daily_changes' in trend_analysis
        assert 'trend_direction' in trend_analysis
        assert 'total_period_changes' in trend_analysis
        
        assert trend_analysis['total_period_changes'] == 10
        assert trend_analysis['avg_daily_changes'] == 10 / 7
        assert trend_analysis['trend_direction'] in ['increasing', 'decreasing', 'stable', 'insufficient_data']
    
    def test_generate_recommendations_with_critical_changes(self, report_generator):
        """Test recommendation generation with critical changes."""
        critical_changes = [
            {
                'id': 1,
                'form_name': 'WH-347',
                'agency_name': 'Department of Labor',
                'severity': 'critical',
                'change_description': 'Critical change'
            }
        ]
        
        recommendations = report_generator._generate_recommendations(critical_changes, None)
        
        assert len(recommendations) > 0
        assert any('critical changes detected' in rec for rec in recommendations)
        assert any('Immediate attention required' in rec for rec in recommendations)
    
    def test_generate_recommendations_with_monitoring_issues(self, report_generator):
        """Test recommendation generation with monitoring issues."""
        form_changes = []
        monitoring_stats = {
            'success_rate': 90.0,
            'failed_runs': 3
        }
        
        recommendations = report_generator._generate_recommendations(form_changes, monitoring_stats)
        
        assert len(recommendations) > 0
        assert any('success rate is 90.0%' in rec for rec in recommendations)
        assert any('3 monitoring runs failed' in rec for rec in recommendations)
    
    def test_generate_recommendations_with_high_volume(self, report_generator):
        """Test recommendation generation with high change volume."""
        high_volume_changes = [
            {'id': i, 'agency_name': f'Agency {i}', 'severity': 'medium'}
            for i in range(25)
        ]
        
        recommendations = report_generator._generate_recommendations(high_volume_changes, None)
        
        assert len(recommendations) > 0
        assert any('High volume of changes detected (25)' in rec for rec in recommendations)
    
    def test_generate_recommendations_no_changes(self, report_generator):
        """Test recommendation generation with no changes."""
        recommendations = report_generator._generate_recommendations([], None)
        
        assert len(recommendations) > 0
        assert any('No changes detected' in rec for rec in recommendations)
    
    @patch('src.reporting.weekly_reports.ExportUtils')
    def test_export_report_pdf(self, mock_export_utils, report_generator):
        """Test PDF report export."""
        mock_export_instance = Mock()
        mock_export_utils.return_value = mock_export_instance
        mock_export_instance.export_to_pdf.return_value = b'pdf_content'
        
        report_data = {'test': 'data'}
        result = report_generator.export_report(report_data, 'pdf')
        
        assert result == b'pdf_content'
        mock_export_instance.export_to_pdf.assert_called_once_with(report_data, True)
    
    @patch('src.reporting.weekly_reports.ExportUtils')
    def test_export_report_excel(self, mock_export_utils, report_generator):
        """Test Excel report export."""
        mock_export_instance = Mock()
        mock_export_utils.return_value = mock_export_instance
        mock_export_instance.export_to_excel.return_value = b'excel_content'
        
        report_data = {'test': 'data'}
        result = report_generator.export_report(report_data, 'excel')
        
        assert result == b'excel_content'
        mock_export_instance.export_to_excel.assert_called_once_with(report_data, True)
    
    @patch('src.reporting.weekly_reports.ExportUtils')
    def test_export_report_csv(self, mock_export_utils, report_generator):
        """Test CSV report export."""
        mock_export_instance = Mock()
        mock_export_utils.return_value = mock_export_instance
        mock_export_instance.export_to_csv.return_value = b'csv_content'
        
        report_data = {'test': 'data'}
        result = report_generator.export_report(report_data, 'csv')
        
        assert result == b'csv_content'
        mock_export_instance.export_to_csv.assert_called_once_with(report_data)
    
    def test_export_report_invalid_format(self, report_generator):
        """Test export with invalid format."""
        report_data = {'test': 'data'}
        
        with pytest.raises(ValueError, match="Unsupported export format"):
            report_generator.export_report(report_data, 'invalid_format')
    
    def test_schedule_weekly_report(self, report_generator):
        """Test weekly report scheduling."""
        recipients = ['user1@example.com', 'user2@example.com']
        filters = {'states': ['federal'], 'severity_levels': ['high', 'critical']}
        
        result = report_generator.schedule_weekly_report(
            recipients=recipients,
            day_of_week='monday',
            time='09:00',
            timezone='UTC',
            filters=filters
        )
        
        assert result['scheduled'] is True
        assert result['recipients'] == recipients
        assert result['schedule']['day_of_week'] == 'monday'
        assert result['schedule']['time'] == '09:00'
        assert result['schedule']['timezone'] == 'UTC'
        assert result['filters'] == filters
        assert 'next_run' in result
    
    def test_calculate_next_run(self, report_generator):
        """Test next run calculation."""
        # Test Monday scheduling
        next_run = report_generator._calculate_next_run('monday', '09:00', 'UTC')
        assert next_run.weekday() == 0  # Monday
        assert next_run.hour == 9
        assert next_run.minute == 0
        
        # Test Friday scheduling
        next_run = report_generator._calculate_next_run('friday', '14:30', 'UTC')
        assert next_run.weekday() == 4  # Friday
        assert next_run.hour == 14
        assert next_run.minute == 30
    
    @patch('src.reporting.weekly_reports.WeeklyReportGenerator')
    def test_generate_weekly_report_convenience_function(self, mock_generator_class):
        """Test convenience function for generating weekly reports."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_weekly_report.return_value = {'test': 'report'}
        
        result = generate_weekly_report(
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now()
        )
        
        assert result == {'test': 'report'}
        mock_generator.generate_weekly_report.assert_called_once()
    
    @patch('src.reporting.weekly_reports.WeeklyReportGenerator')
    def test_export_weekly_report_convenience_function(self, mock_generator_class):
        """Test convenience function for exporting weekly reports."""
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.export_report.return_value = b'exported_content'
        
        report_data = {'test': 'data'}
        result = export_weekly_report(report_data, 'pdf')
        
        assert result == b'exported_content'
        mock_generator.export_report.assert_called_once_with(report_data, 'pdf', True)


class TestWeeklyReportGeneratorIntegration:
    """Integration tests for weekly report generator."""
    
    @pytest.fixture
    def report_generator(self):
        return WeeklyReportGenerator()
    
    def test_full_report_generation_workflow(self, report_generator):
        """Test the complete report generation workflow."""
        # This would test with actual database data in integration tests
        # For now, test the workflow structure
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        # Test with minimal data
        report = report_generator.generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            include_monitoring_statistics=False,
            include_notification_summary=False,
            include_impact_assessment=False
        )
        
        assert report is not None
        assert 'report_metadata' in report
        assert 'executive_summary' in report
        assert 'form_changes' in report
        assert 'recommendations' in report
    
    def test_report_customization_options(self, report_generator):
        """Test various report customization options."""
        start_date = datetime.now() - timedelta(days=14)
        end_date = datetime.now()
        
        # Test with different filter combinations
        report = report_generator.generate_weekly_report(
            start_date=start_date,
            end_date=end_date,
            states=['federal', 'state'],
            form_types=['WH-347', 'A1-131'],
            severity_levels=['high'],
            include_ai_analysis=False,
            include_impact_assessment=False,
            include_notification_summary=False,
            include_monitoring_statistics=False
        )
        
        assert report is not None
        metadata = report['report_metadata']
        assert metadata['filters_applied']['states'] == ['federal', 'state']
        assert metadata['filters_applied']['form_types'] == ['WH-347', 'A1-131']
        assert metadata['filters_applied']['severity_levels'] == ['high']


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 