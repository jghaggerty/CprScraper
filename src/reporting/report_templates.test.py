"""
Unit tests for report templates.
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

from src.reporting.report_templates import (
    ReportTemplateManager, render_consolidated_report, get_available_templates
)


class TestReportTemplateManager:
    """Test the report template manager functionality."""
    
    @pytest.fixture
    def template_manager(self):
        """Create a template manager instance."""
        return ReportTemplateManager()
    
    @pytest.fixture
    def sample_report_data(self):
        """Create sample report data for testing."""
        return {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': datetime.now() - timedelta(days=7),
                'end_date': datetime.now(),
                'report_period': '2024-01-08 to 2024-01-15',
                'filters_applied': {
                    'states': ['federal', 'state'],
                    'form_types': ['WH-347', 'A1-131'],
                    'severity_levels': ['high', 'critical']
                }
            },
            'executive_summary': {
                'total_changes_detected': 5,
                'critical_changes': 1,
                'high_priority_changes': 2,
                'severity_breakdown': {'critical': 1, 'high': 2, 'medium': 1, 'low': 1},
                'agency_breakdown': {'Department of Labor': 2, 'California DIR': 3},
                'change_type_breakdown': {'content': 3, 'metadata': 2},
                'monitoring_performance': {'success_rate': 95.0, 'total_runs': 100},
                'notification_performance': {'delivery_rate': 92.0, 'total_notifications': 25}
            },
            'form_changes': [
                {
                    'id': 1,
                    'form_name': 'WH-347',
                    'form_title': 'Statement of Compliance',
                    'agency_name': 'Department of Labor',
                    'agency_type': 'federal',
                    'change_type': 'content',
                    'change_description': 'Updated wage determination requirements',
                    'severity': 'critical',
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
                    'severity': 'high',
                    'detected_at': datetime.now() - timedelta(days=5),
                    'effective_date': None,
                    'status': 'detected',
                    'ai_confidence_score': 92,
                    'ai_change_category': 'cosmetic_update',
                    'ai_severity_score': 20,
                    'is_cosmetic_change': True,
                    'ai_reasoning': 'This appears to be a cosmetic update to contact information'
                }
            ],
            'impact_assessments': [
                {
                    'form_change_id': 1,
                    'form_name': 'WH-347',
                    'agency_name': 'Department of Labor',
                    'total_clients_impacted': 25,
                    'impact_percentage': 15.5,
                    'icp_segment_breakdown': {
                        'Enterprise': 15,
                        'Mid-Market': 8,
                        'SMB': 2
                    },
                    'severity': 'critical',
                    'ai_confidence_score': 85,
                    'ai_severity_score': 80
                }
            ],
            'monitoring_statistics': {
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
                    }
                }
            },
            'notification_summary': {
                'total_notifications': 25,
                'delivered': 23,
                'failed': 2,
                'pending': 0,
                'delivery_rate': 92.0,
                'type_breakdown': {
                    'email': {'total': 20, 'delivered': 19, 'failed': 1, 'pending': 0},
                    'slack': {'total': 5, 'delivered': 4, 'failed': 1, 'pending': 0}
                }
            },
            'trend_analysis': {
                'daily_trends': {
                    '2024-01-08': 1,
                    '2024-01-09': 2,
                    '2024-01-10': 0,
                    '2024-01-11': 1,
                    '2024-01-12': 1
                },
                'avg_daily_changes': 1.0,
                'trend_direction': 'stable',
                'total_period_changes': 5
            },
            'recommendations': [
                'Immediate attention required: 1 critical changes detected. Review and prioritize development work for these changes.',
                'Monitoring success rate is 95.0%, meeting target of 95%.',
                'Consider implementing automated change classification to prioritize critical changes.'
            ]
        }
    
    def test_template_manager_initialization(self, template_manager):
        """Test that template manager initializes correctly."""
        assert template_manager is not None
        assert hasattr(template_manager, 'templates')
        assert len(template_manager.templates) == 5
    
    def test_get_template(self, template_manager):
        """Test getting specific templates."""
        # Test getting each template type
        executive_template = template_manager.get_template('executive_summary')
        detailed_template = template_manager.get_template('detailed_report')
        technical_template = template_manager.get_template('technical_report')
        dashboard_template = template_manager.get_template('dashboard_report')
        email_template = template_manager.get_template('email_summary')
        
        assert executive_template is not None
        assert detailed_template is not None
        assert technical_template is not None
        assert dashboard_template is not None
        assert email_template is not None
    
    def test_get_template_invalid(self, template_manager):
        """Test getting invalid template returns default."""
        template = template_manager.get_template('invalid_template')
        default_template = template_manager.get_template('detailed_report')
        assert template == default_template
    
    def test_render_executive_summary_template(self, template_manager, sample_report_data):
        """Test rendering executive summary template."""
        html_content = template_manager.render_report(
            sample_report_data, 'executive_summary'
        )
        
        # Check for key elements
        assert 'Executive Summary' in html_content
        assert 'Compliance Monitoring Report' in html_content
        assert '2024-01-08 to 2024-01-15' in html_content
        assert '5' in html_content  # total changes
        assert '1' in html_content  # critical changes
        assert '2' in html_content  # high priority changes
        assert '95.0%' in html_content  # monitoring success rate
        assert 'Key Findings' in html_content
        assert 'Key Recommendations' in html_content
    
    def test_render_detailed_report_template(self, template_manager, sample_report_data):
        """Test rendering detailed report template."""
        html_content = template_manager.render_report(
            sample_report_data, 'detailed_report'
        )
        
        # Check for key elements
        assert 'Detailed Compliance Report' in html_content
        assert 'Comprehensive Analysis of All Compliance Changes' in html_content
        assert 'WH-347' in html_content
        assert 'Department of Labor' in html_content
        assert 'Updated wage determination requirements' in html_content
        assert 'CRITICAL' in html_content
        assert 'Changes by Agency' in html_content
        assert 'Impact Assessment' in html_content
        assert 'Monitoring Performance' in html_content
        assert 'Recommendations' in html_content
    
    def test_render_technical_report_template(self, template_manager, sample_report_data):
        """Test rendering technical report template."""
        html_content = template_manager.render_report(
            sample_report_data, 'technical_report'
        )
        
        # Check for key elements
        assert 'Technical Compliance Report' in html_content
        assert 'Detailed Technical Analysis for Development Team' in html_content
        assert 'Technical Summary' in html_content
        assert 'Detailed Change Analysis' in html_content
        assert 'AI Analysis Details' in html_content
        assert 'Monitoring System Performance' in html_content
        assert 'Trend Analysis' in html_content
        assert 'This change modifies core wage determination logic' in html_content
    
    def test_render_dashboard_report_template(self, template_manager, sample_report_data):
        """Test rendering dashboard report template."""
        html_content = template_manager.render_report(
            sample_report_data, 'dashboard_report'
        )
        
        # Check for key elements
        assert 'Compliance Dashboard' in html_content
        assert 'Real-time Overview of Compliance Changes' in html_content
        assert 'Recent Changes' in html_content
        assert 'Key Metrics' in html_content
        assert 'Top Recommendations' in html_content
        assert 'WH-347' in html_content
        assert 'Department of Labor' in html_content
    
    def test_render_email_summary_template(self, template_manager, sample_report_data):
        """Test rendering email summary template."""
        html_content = template_manager.render_report(
            sample_report_data, 'email_summary'
        )
        
        # Check for key elements
        assert 'Weekly Compliance Summary' in html_content
        assert 'Quick Overview' in html_content
        assert 'Priority Changes' in html_content
        assert 'Key Recommendations' in html_content
        assert '5' in html_content  # total changes
        assert '1' in html_content  # critical changes
        assert '2' in html_content  # high priority changes
        assert '95.0%' in html_content  # monitoring success rate
    
    def test_template_with_empty_data(self, template_manager):
        """Test template rendering with minimal data."""
        minimal_data = {
            'report_metadata': {
                'generated_at': datetime.now(),
                'start_date': datetime.now() - timedelta(days=7),
                'end_date': datetime.now(),
                'report_period': '2024-01-08 to 2024-01-15',
                'filters_applied': {}
            },
            'executive_summary': {
                'total_changes_detected': 0,
                'critical_changes': 0,
                'high_priority_changes': 0,
                'severity_breakdown': {},
                'agency_breakdown': {},
                'change_type_breakdown': {},
                'monitoring_performance': {'success_rate': 0, 'total_runs': 0},
                'notification_performance': {'delivery_rate': 0, 'total_notifications': 0}
            },
            'form_changes': [],
            'impact_assessments': [],
            'monitoring_statistics': None,
            'notification_summary': None,
            'trend_analysis': {},
            'recommendations': []
        }
        
        html_content = template_manager.render_report(minimal_data, 'executive_summary')
        
        # Should render without errors
        assert 'Executive Summary' in html_content
        assert '0' in html_content  # total changes
        assert '2024-01-08 to 2024-01-15' in html_content
    
    def test_group_changes_by_severity(self, template_manager):
        """Test grouping changes by severity."""
        form_changes = [
            {'severity': 'critical', 'form_name': 'Form1'},
            {'severity': 'high', 'form_name': 'Form2'},
            {'severity': 'medium', 'form_name': 'Form3'},
            {'severity': 'low', 'form_name': 'Form4'},
            {'severity': 'critical', 'form_name': 'Form5'}
        ]
        
        grouped = template_manager._group_changes_by_severity(form_changes)
        
        assert len(grouped['critical']) == 2
        assert len(grouped['high']) == 1
        assert len(grouped['medium']) == 1
        assert len(grouped['low']) == 1
        assert grouped['critical'][0]['form_name'] == 'Form1'
        assert grouped['critical'][1]['form_name'] == 'Form5'
    
    def test_group_changes_by_agency(self, template_manager):
        """Test grouping changes by agency."""
        form_changes = [
            {'agency_name': 'Agency A', 'form_name': 'Form1'},
            {'agency_name': 'Agency B', 'form_name': 'Form2'},
            {'agency_name': 'Agency A', 'form_name': 'Form3'},
            {'agency_name': 'Agency C', 'form_name': 'Form4'}
        ]
        
        grouped = template_manager._group_changes_by_agency(form_changes)
        
        assert len(grouped['Agency A']) == 2
        assert len(grouped['Agency B']) == 1
        assert len(grouped['Agency C']) == 1
        assert grouped['Agency A'][0]['form_name'] == 'Form1'
        assert grouped['Agency A'][1]['form_name'] == 'Form3'
    
    def test_calculate_summary_statistics(self, template_manager):
        """Test summary statistics calculation."""
        form_changes = [
            {'severity': 'critical', 'agency_name': 'Agency A', 'change_type': 'content', 'ai_confidence_score': 85},
            {'severity': 'high', 'agency_name': 'Agency B', 'change_type': 'metadata', 'ai_confidence_score': 92},
            {'severity': 'medium', 'agency_name': 'Agency A', 'change_type': 'content', 'ai_confidence_score': 75}
        ]
        
        monitoring_stats = {'success_rate': 95.0}
        notification_summary = {'delivery_rate': 92.0}
        
        stats = template_manager._calculate_summary_statistics(
            form_changes, monitoring_stats, notification_summary
        )
        
        assert stats['total_changes'] == 3
        assert stats['severity_counts']['critical'] == 1
        assert stats['severity_counts']['high'] == 1
        assert stats['severity_counts']['medium'] == 1
        assert stats['agency_counts']['Agency A'] == 2
        assert stats['agency_counts']['Agency B'] == 1
        assert stats['change_type_counts']['content'] == 2
        assert stats['change_type_counts']['metadata'] == 1
        assert stats['avg_ai_confidence'] == 84.0
        assert stats['monitoring_success_rate'] == 95.0
        assert stats['notification_delivery_rate'] == 92.0
    
    def test_calculate_summary_statistics_no_data(self, template_manager):
        """Test summary statistics calculation with no data."""
        stats = template_manager._calculate_summary_statistics([], None, None)
        
        assert stats['total_changes'] == 0
        assert stats['severity_counts'] == {}
        assert stats['agency_counts'] == {}
        assert stats['change_type_counts'] == {}
        assert stats['avg_ai_confidence'] == 0
        assert stats['monitoring_success_rate'] == 0
        assert stats['notification_delivery_rate'] == 0
    
    def test_template_performance(self, template_manager, sample_report_data):
        """Test template rendering performance."""
        import time
        
        start_time = time.time()
        for _ in range(5):
            html_content = template_manager.render_report(sample_report_data, 'detailed_report')
        end_time = time.time()
        
        # Should render 5 templates in under 2 seconds
        assert (end_time - start_time) < 2.0
        assert len(html_content) > 1000  # Should generate substantial HTML
    
    def test_all_template_types(self, template_manager, sample_report_data):
        """Test all template types render correctly."""
        template_types = ['executive_summary', 'detailed_report', 'technical_report', 'dashboard_report', 'email_summary']
        
        for template_type in template_types:
            html_content = template_manager.render_report(sample_report_data, template_type)
            
            # Each template should generate substantial HTML
            assert len(html_content) > 500
            assert 'html' in html_content.lower()
            assert 'body' in html_content.lower()
            
            # Check for template-specific content
            if template_type == 'executive_summary':
                assert 'Executive Summary' in html_content
            elif template_type == 'detailed_report':
                assert 'Detailed Compliance Report' in html_content
            elif template_type == 'technical_report':
                assert 'Technical Compliance Report' in html_content
            elif template_type == 'dashboard_report':
                assert 'Compliance Dashboard' in html_content
            elif template_type == 'email_summary':
                assert 'Weekly Compliance Summary' in html_content


class TestReportTemplateConvenienceFunctions:
    """Test convenience functions for report templates."""
    
    def test_render_consolidated_report(self, sample_report_data):
        """Test render_consolidated_report convenience function."""
        html_content = render_consolidated_report(sample_report_data, 'executive_summary')
        
        assert html_content is not None
        assert len(html_content) > 500
        assert 'Executive Summary' in html_content
        assert 'Compliance Monitoring Report' in html_content
    
    def test_render_consolidated_report_with_charts(self, sample_report_data):
        """Test render_consolidated_report with charts enabled."""
        html_content = render_consolidated_report(
            sample_report_data, 'detailed_report', include_charts=True
        )
        
        assert html_content is not None
        assert len(html_content) > 1000
        assert 'Detailed Compliance Report' in html_content
    
    def test_get_available_templates(self):
        """Test get_available_templates function."""
        templates = get_available_templates()
        
        expected_templates = [
            'executive_summary',
            'detailed_report',
            'technical_report',
            'dashboard_report',
            'email_summary'
        ]
        
        assert len(templates) == len(expected_templates)
        for template in expected_templates:
            assert template in templates


class TestReportTemplateEdgeCases:
    """Test edge cases and error handling in report templates."""
    
    @pytest.fixture
    def template_manager(self):
        return ReportTemplateManager()
    
    def test_template_with_missing_fields(self, template_manager):
        """Test template rendering with missing data fields."""
        incomplete_data = {
            'report_metadata': {
                'report_period': '2024-01-08 to 2024-01-15'
            },
            'form_changes': [
                {
                    'form_name': 'WH-347',
                    'agency_name': 'Department of Labor',
                    'change_description': 'Test change',
                    'severity': 'high'
                }
            ]
        }
        
        # Should handle missing fields gracefully
        html_content = template_manager.render_report(incomplete_data, 'executive_summary')
        
        assert html_content is not None
        assert 'WH-347' in html_content
        assert 'Department of Labor' in html_content
        assert 'Test change' in html_content
    
    def test_template_with_none_values(self, template_manager):
        """Test template rendering with None values."""
        data_with_nones = {
            'report_metadata': {
                'report_period': '2024-01-08 to 2024-01-15'
            },
            'form_changes': [
                {
                    'form_name': 'WH-347',
                    'agency_name': 'Department of Labor',
                    'change_description': 'Test change',
                    'severity': 'high',
                    'ai_confidence_score': None,
                    'ai_reasoning': None
                }
            ],
            'monitoring_statistics': None,
            'notification_summary': None,
            'impact_assessments': None,
            'trend_analysis': None,
            'recommendations': None
        }
        
        html_content = template_manager.render_report(data_with_nones, 'detailed_report')
        
        assert html_content is not None
        assert 'WH-347' in html_content
        assert 'Department of Labor' in html_content
    
    def test_template_with_special_characters(self, template_manager):
        """Test template rendering with special characters in data."""
        data_with_special_chars = {
            'report_metadata': {
                'report_period': '2024-01-08 to 2024-01-15'
            },
            'form_changes': [
                {
                    'form_name': 'WH-347 & Partners',
                    'agency_name': 'Department of Labor & Industry',
                    'change_description': 'Updated requirements for "special" projects & compliance',
                    'severity': 'high',
                    'ai_reasoning': 'This change affects <script>alert("test")</script> functionality'
                }
            ]
        }
        
        html_content = template_manager.render_report(data_with_special_chars, 'executive_summary')
        
        assert html_content is not None
        assert 'WH-347 & Partners' in html_content
        assert 'Department of Labor & Industry' in html_content
        assert 'Updated requirements for "special" projects & compliance' in html_content
        # Should escape HTML in AI reasoning
        assert '&lt;script&gt;alert("test")&lt;/script&gt;' in html_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 