"""
Report Customization System for Weekly Compliance Reports

This module provides comprehensive customization options for reports including
date ranges, states, form types, severity levels, and other filtering options.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json

from ..database.connection import get_db
from ..database.models import User, Form, Agency, FormChange
from ..reporting.weekly_reports import WeeklyReportGenerator
from ..reporting.report_templates import ReportTemplateManager
from ..utils.config_loader import get_agencies_config

logger = logging.getLogger(__name__)


class ReportFrequency(Enum):
    """Report frequency options."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    CUSTOM = "custom"


class ReportFormat(Enum):
    """Report format options."""
    HTML = "html"
    PDF = "pdf"
    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"


@dataclass
class ReportCustomizationOptions:
    """Configuration for report customization."""
    # Date range options
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    frequency: ReportFrequency = ReportFrequency.WEEKLY
    
    # Geographic filters
    states: Optional[List[str]] = None
    agencies: Optional[List[str]] = None
    
    # Form type filters
    form_types: Optional[List[str]] = None
    form_categories: Optional[List[str]] = None
    
    # Severity and priority filters
    severity_levels: Optional[List[str]] = None
    priority_levels: Optional[List[str]] = None
    
    # Content options
    include_ai_analysis: bool = True
    include_impact_assessment: bool = True
    include_notification_summary: bool = True
    include_monitoring_statistics: bool = True
    include_charts: bool = True
    
    # Format and delivery options
    report_format: ReportFormat = ReportFormat.HTML
    template_type: str = 'detailed_report'
    delivery_channels: Optional[List[str]] = None
    
    # Custom filters
    custom_filters: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        data = asdict(self)
        data['frequency'] = self.frequency.value
        data['report_format'] = self.report_format.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReportCustomizationOptions':
        """Create from dictionary."""
        # Convert enum values back
        if 'frequency' in data:
            data['frequency'] = ReportFrequency(data['frequency'])
        if 'report_format' in data:
            data['report_format'] = ReportFormat(data['report_format'])
        
        return cls(**data)


class ReportCustomizationManager:
    """Manage report customization options and preferences."""
    
    def __init__(self):
        self.report_generator = WeeklyReportGenerator()
        self.template_manager = ReportTemplateManager()
        self.agencies_config = get_agencies_config()
        
        # Available options
        self.available_states = self._get_available_states()
        self.available_form_types = self._get_available_form_types()
        self.available_severity_levels = ['critical', 'high', 'medium', 'low', 'informational']
        self.available_priority_levels = ['urgent', 'high', 'medium', 'low']
        self.available_delivery_channels = ['email', 'slack', 'teams', 'webhook']
        self.available_template_types = [
            'executive_summary',
            'detailed_report',
            'technical_report',
            'dashboard_report',
            'email_summary'
        ]
    
    def _get_available_states(self) -> List[str]:
        """Get list of available states from configuration."""
        states = []
        for agency in self.agencies_config.get('agencies', []):
            state = agency.get('state')
            if state and state not in states:
                states.append(state)
        return sorted(states)
    
    def _get_available_form_types(self) -> List[str]:
        """Get list of available form types from database."""
        try:
            with get_db() as db:
                form_types = db.query(Form.form_type).distinct().all()
                return [form_type[0] for form_type in form_types if form_type[0]]
        except Exception as e:
            logger.error(f"Error getting form types: {e}")
            return ['WH-347', 'WH-348', 'WH-349', 'WH-350', 'WH-351']
    
    def get_available_options(self) -> Dict[str, Any]:
        """Get all available customization options."""
        return {
            'states': self.available_states,
            'form_types': self.available_form_types,
            'severity_levels': self.available_severity_levels,
            'priority_levels': self.available_priority_levels,
            'delivery_channels': self.available_delivery_channels,
            'template_types': self.available_template_types,
            'frequencies': [freq.value for freq in ReportFrequency],
            'formats': [fmt.value for fmt in ReportFormat]
        }
    
    def create_default_options(self, user_role: str = 'business_analyst') -> ReportCustomizationOptions:
        """Create default customization options for a user role."""
        if user_role == 'product_manager':
            return ReportCustomizationOptions(
                frequency=ReportFrequency.WEEKLY,
                severity_levels=['critical', 'high'],
                template_type='executive_summary',
                delivery_channels=['email', 'slack'],
                include_charts=True
            )
        elif user_role == 'business_analyst':
            return ReportCustomizationOptions(
                frequency=ReportFrequency.WEEKLY,
                template_type='detailed_report',
                delivery_channels=['email'],
                include_charts=True,
                include_ai_analysis=True,
                include_impact_assessment=True
            )
        elif user_role == 'admin':
            return ReportCustomizationOptions(
                frequency=ReportFrequency.WEEKLY,
                template_type='technical_report',
                delivery_channels=['email'],
                include_charts=False,
                include_monitoring_statistics=True
            )
        else:
            return ReportCustomizationOptions()
    
    def validate_customization_options(self, options: ReportCustomizationOptions) -> Dict[str, Any]:
        """Validate customization options and return validation results."""
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        # Validate date range
        if options.start_date and options.end_date:
            if options.start_date >= options.end_date:
                validation_results['valid'] = False
                validation_results['errors'].append("Start date must be before end date")
            
            # Check if date range is reasonable
            date_diff = options.end_date - options.start_date
            if date_diff.days > 365:
                validation_results['warnings'].append("Date range is very large (>1 year)")
            elif date_diff.days < 1:
                validation_results['warnings'].append("Date range is very small (<1 day)")
        
        # Validate states
        if options.states:
            invalid_states = [state for state in options.states if state not in self.available_states]
            if invalid_states:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Invalid states: {invalid_states}")
        
        # Validate form types
        if options.form_types:
            invalid_form_types = [ft for ft in options.form_types if ft not in self.available_form_types]
            if invalid_form_types:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Invalid form types: {invalid_form_types}")
        
        # Validate severity levels
        if options.severity_levels:
            invalid_severities = [sev for sev in options.severity_levels if sev not in self.available_severity_levels]
            if invalid_severities:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Invalid severity levels: {invalid_severities}")
        
        # Validate template type
        if options.template_type not in self.available_template_types:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Invalid template type: {options.template_type}")
        
        # Validate delivery channels
        if options.delivery_channels:
            invalid_channels = [ch for ch in options.delivery_channels if ch not in self.available_delivery_channels]
            if invalid_channels:
                validation_results['valid'] = False
                validation_results['errors'].append(f"Invalid delivery channels: {invalid_channels}")
        
        # Suggestions
        if not options.states and not options.agencies:
            validation_results['suggestions'].append("Consider filtering by specific states or agencies for more focused reports")
        
        if not options.severity_levels:
            validation_results['suggestions'].append("Consider filtering by severity levels to focus on important changes")
        
        if options.frequency == ReportFrequency.DAILY:
            validation_results['suggestions'].append("Daily reports may generate a lot of data. Consider weekly frequency for better overview")
        
        return validation_results
    
    def generate_customized_report(self, options: ReportCustomizationOptions) -> Dict[str, Any]:
        """Generate a report with custom options."""
        # Validate options first
        validation = self.validate_customization_options(options)
        if not validation['valid']:
            return {
                'success': False,
                'error': 'Invalid customization options',
                'validation_results': validation
            }
        
        try:
            # Set default date range if not provided
            if not options.end_date:
                options.end_date = datetime.now()
            if not options.start_date:
                if options.frequency == ReportFrequency.DAILY:
                    options.start_date = options.end_date - timedelta(days=1)
                elif options.frequency == ReportFrequency.WEEKLY:
                    options.start_date = options.end_date - timedelta(days=7)
                elif options.frequency == ReportFrequency.MONTHLY:
                    options.start_date = options.end_date - timedelta(days=30)
                elif options.frequency == ReportFrequency.QUARTERLY:
                    options.start_date = options.end_date - timedelta(days=90)
                else:
                    options.start_date = options.end_date - timedelta(days=7)
            
            # Generate report with custom options
            report_data = self.report_generator.generate_weekly_report(
                start_date=options.start_date,
                end_date=options.end_date,
                states=options.states,
                form_types=options.form_types,
                severity_levels=options.severity_levels,
                include_ai_analysis=options.include_ai_analysis,
                include_impact_assessment=options.include_impact_assessment,
                include_notification_summary=options.include_notification_summary,
                include_monitoring_statistics=options.include_monitoring_statistics
            )
            
            # Render report with custom template
            html_content = self.template_manager.render_report(
                report_data,
                options.template_type,
                options.include_charts
            )
            
            return {
                'success': True,
                'report_data': report_data,
                'html_content': html_content,
                'customization_options': options.to_dict(),
                'generated_at': datetime.now(),
                'period': f"{options.start_date.strftime('%Y-%m-%d')} to {options.end_date.strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            logger.error(f"Error generating customized report: {e}")
            return {
                'success': False,
                'error': str(e),
                'customization_options': options.to_dict()
            }
    
    def get_report_preview(self, options: ReportCustomizationOptions) -> Dict[str, Any]:
        """Get a preview of what the report would contain."""
        # Create a sample report with limited data for preview
        preview_options = ReportCustomizationOptions(
            start_date=options.start_date or (datetime.now() - timedelta(days=1)),
            end_date=options.end_date or datetime.now(),
            states=options.states,
            form_types=options.form_types,
            severity_levels=options.severity_levels,
            include_ai_analysis=False,  # Skip AI analysis for preview
            include_impact_assessment=False,
            include_notification_summary=False,
            include_monitoring_statistics=False,
            include_charts=False,
            template_type=options.template_type
        )
        
        try:
            # Generate minimal report for preview
            report_data = self.report_generator.generate_weekly_report(
                start_date=preview_options.start_date,
                end_date=preview_options.end_date,
                states=preview_options.states,
                form_types=preview_options.form_types,
                severity_levels=preview_options.severity_levels,
                include_ai_analysis=False,
                include_impact_assessment=False,
                include_notification_summary=False,
                include_monitoring_statistics=False
            )
            
            # Get summary statistics
            executive_summary = report_data.get('executive_summary', {})
            
            return {
                'success': True,
                'preview_data': {
                    'total_changes': executive_summary.get('total_changes_detected', 0),
                    'critical_changes': executive_summary.get('critical_changes', 0),
                    'high_priority_changes': executive_summary.get('high_priority_changes', 0),
                    'states_covered': len(options.states) if options.states else len(self.available_states),
                    'form_types_covered': len(options.form_types) if options.form_types else len(self.available_form_types),
                    'period': f"{preview_options.start_date.strftime('%Y-%m-%d')} to {preview_options.end_date.strftime('%Y-%m-%d')}"
                },
                'customization_options': options.to_dict(),
                'validation_results': self.validate_customization_options(options)
            }
            
        except Exception as e:
            logger.error(f"Error generating report preview: {e}")
            return {
                'success': False,
                'error': str(e),
                'customization_options': options.to_dict()
            }
    
    def save_user_preferences(self, user_id: int, options: ReportCustomizationOptions, name: str = "default") -> bool:
        """Save user's report customization preferences."""
        try:
            # This would typically save to a database table
            # For now, we'll just log the preferences
            logger.info(f"Saving preferences for user {user_id}: {name}")
            logger.info(f"Preferences: {options.to_dict()}")
            return True
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
            return False
    
    def load_user_preferences(self, user_id: int, name: str = "default") -> Optional[ReportCustomizationOptions]:
        """Load user's saved report customization preferences."""
        try:
            # This would typically load from a database table
            # For now, return default options
            logger.info(f"Loading preferences for user {user_id}: {name}")
            return self.create_default_options()
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
            return None
    
    def get_recommended_options(self, user_role: str, recent_activity: Dict[str, Any] = None) -> ReportCustomizationOptions:
        """Get recommended customization options based on user role and recent activity."""
        base_options = self.create_default_options(user_role)
        
        if recent_activity:
            # Adjust based on recent activity
            if recent_activity.get('high_critical_changes', 0) > 5:
                base_options.severity_levels = ['critical', 'high']
                base_options.frequency = ReportFrequency.DAILY
            elif recent_activity.get('total_changes', 0) > 20:
                base_options.frequency = ReportFrequency.WEEKLY
            else:
                base_options.frequency = ReportFrequency.MONTHLY
        
        return base_options


def create_customization_options_from_request(request_data: Dict[str, Any]) -> ReportCustomizationOptions:
    """Create customization options from API request data."""
    # Parse date strings
    start_date = None
    end_date = None
    
    if request_data.get('start_date'):
        start_date = datetime.fromisoformat(request_data['start_date'].replace('Z', '+00:00'))
    if request_data.get('end_date'):
        end_date = datetime.fromisoformat(request_data['end_date'].replace('Z', '+00:00'))
    
    # Parse enums
    frequency = ReportFrequency(request_data.get('frequency', 'weekly'))
    report_format = ReportFormat(request_data.get('report_format', 'html'))
    
    return ReportCustomizationOptions(
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        states=request_data.get('states'),
        agencies=request_data.get('agencies'),
        form_types=request_data.get('form_types'),
        form_categories=request_data.get('form_categories'),
        severity_levels=request_data.get('severity_levels'),
        priority_levels=request_data.get('priority_levels'),
        include_ai_analysis=request_data.get('include_ai_analysis', True),
        include_impact_assessment=request_data.get('include_impact_assessment', True),
        include_notification_summary=request_data.get('include_notification_summary', True),
        include_monitoring_statistics=request_data.get('include_monitoring_statistics', True),
        include_charts=request_data.get('include_charts', True),
        report_format=report_format,
        template_type=request_data.get('template_type', 'detailed_report'),
        delivery_channels=request_data.get('delivery_channels'),
        custom_filters=request_data.get('custom_filters')
    )


def get_customization_manager() -> ReportCustomizationManager:
    """Get a customization manager instance."""
    return ReportCustomizationManager() 