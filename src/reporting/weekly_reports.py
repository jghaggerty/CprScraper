"""
Weekly Summary Report Generation Service

This module provides automated weekly report generation for compliance monitoring,
including consolidated reports with all compliance changes, filtering options,
and distribution capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import joinedload

from ..database.connection import get_db
from ..database.models import (
    FormChange, Form, Agency, Client, ClientFormUsage, 
    MonitoringRun, Notification, WorkItem, User, UserRole, Role
)
from ..notifications.enhanced_notifier import EnhancedNotificationManager
from ..utils.export_utils import ExportUtils

logger = logging.getLogger(__name__)


class WeeklyReportGenerator:
    """Generate comprehensive weekly reports for compliance monitoring."""
    
    def __init__(self):
        self.export_utils = ExportUtils()
        self.notifier = EnhancedNotificationManager()
    
    def generate_weekly_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        states: Optional[List[str]] = None,
        form_types: Optional[List[str]] = None,
        severity_levels: Optional[List[str]] = None,
        include_ai_analysis: bool = True,
        include_impact_assessment: bool = True,
        include_notification_summary: bool = True,
        include_monitoring_statistics: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive weekly report with all compliance changes.
        
        Args:
            start_date: Start date for report period (defaults to 7 days ago)
            end_date: End date for report period (defaults to now)
            states: Filter by specific states (None for all)
            form_types: Filter by specific form types (None for all)
            severity_levels: Filter by severity levels (None for all)
            include_ai_analysis: Include AI analysis in report
            include_impact_assessment: Include impact assessment data
            include_notification_summary: Include notification delivery summary
            include_monitoring_statistics: Include monitoring performance stats
            
        Returns:
            Dictionary containing comprehensive report data
        """
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        logger.info(f"Generating weekly report from {start_date} to {end_date}")
        
        with get_db() as db:
            # Get form changes for the period
            form_changes = self._get_form_changes_for_period(
                db, start_date, end_date, states, form_types, severity_levels
            )
            
            # Get monitoring statistics
            monitoring_stats = None
            if include_monitoring_statistics:
                monitoring_stats = self._get_monitoring_statistics(db, start_date, end_date)
            
            # Get notification summary
            notification_summary = None
            if include_notification_summary:
                notification_summary = self._get_notification_summary(db, start_date, end_date)
            
            # Generate impact assessments
            impact_assessments = None
            if include_impact_assessment:
                impact_assessments = self._generate_impact_assessments(db, form_changes)
            
            # Compile executive summary
            executive_summary = self._generate_executive_summary(
                form_changes, monitoring_stats, notification_summary
            )
            
            # Generate trend analysis
            trend_analysis = self._generate_trend_analysis(db, start_date, end_date)
            
            return {
                'report_metadata': {
                    'generated_at': datetime.now(),
                    'start_date': start_date,
                    'end_date': end_date,
                    'report_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'filters_applied': {
                        'states': states,
                        'form_types': form_types,
                        'severity_levels': severity_levels
                    }
                },
                'executive_summary': executive_summary,
                'form_changes': form_changes,
                'impact_assessments': impact_assessments,
                'monitoring_statistics': monitoring_stats,
                'notification_summary': notification_summary,
                'trend_analysis': trend_analysis,
                'recommendations': self._generate_recommendations(form_changes, monitoring_stats)
            }
    
    def _get_form_changes_for_period(
        self,
        db,
        start_date: datetime,
        end_date: datetime,
        states: Optional[List[str]] = None,
        form_types: Optional[List[str]] = None,
        severity_levels: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get form changes for the specified period with filters."""
        query = db.query(FormChange).join(Form).join(Agency).filter(
            and_(
                FormChange.detected_at >= start_date,
                FormChange.detected_at <= end_date
            )
        ).options(
            joinedload(FormChange.form).joinedload(Form.agency)
        )
        
        # Apply filters
        if states:
            query = query.filter(Agency.agency_type.in_(states))
        
        if form_types:
            query = query.filter(Form.name.in_(form_types))
        
        if severity_levels:
            query = query.filter(FormChange.severity.in_(severity_levels))
        
        form_changes = query.order_by(FormChange.detected_at.desc()).all()
        
        # Convert to dictionaries with additional data
        result = []
        for change in form_changes:
            change_data = {
                'id': change.id,
                'form_name': change.form.name,
                'form_title': change.form.title,
                'agency_name': change.form.agency.name,
                'agency_type': change.form.agency.agency_type,
                'change_type': change.change_type,
                'change_description': change.change_description,
                'severity': change.severity,
                'detected_at': change.detected_at,
                'effective_date': change.effective_date,
                'status': change.status,
                'ai_confidence_score': change.ai_confidence_score,
                'ai_change_category': change.ai_change_category,
                'ai_severity_score': change.ai_severity_score,
                'is_cosmetic_change': change.is_cosmetic_change
            }
            
            # Add AI reasoning if available
            if change.ai_reasoning:
                change_data['ai_reasoning'] = change.ai_reasoning
            
            result.append(change_data)
        
        return result
    
    def _get_monitoring_statistics(self, db, start_date: datetime, end_date: datetime) -> Dict:
        """Get monitoring performance statistics for the period."""
        # Get monitoring runs
        monitoring_runs = db.query(MonitoringRun).filter(
            and_(
                MonitoringRun.started_at >= start_date,
                MonitoringRun.started_at <= end_date
            )
        ).all()
        
        total_runs = len(monitoring_runs)
        successful_runs = len([run for run in monitoring_runs if run.status == 'completed'])
        failed_runs = len([run for run in monitoring_runs if run.status == 'failed'])
        
        # Calculate average response times
        response_times = [run.response_time_ms for run in monitoring_runs if run.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Get agency breakdown
        agency_stats = {}
        for run in monitoring_runs:
            agency_name = run.agency.name
            if agency_name not in agency_stats:
                agency_stats[agency_name] = {
                    'total_runs': 0,
                    'successful_runs': 0,
                    'failed_runs': 0,
                    'changes_detected': 0
                }
            
            agency_stats[agency_name]['total_runs'] += 1
            if run.status == 'completed':
                agency_stats[agency_name]['successful_runs'] += 1
            elif run.status == 'failed':
                agency_stats[agency_name]['failed_runs'] += 1
            
            agency_stats[agency_name]['changes_detected'] += run.changes_detected or 0
        
        return {
            'total_runs': total_runs,
            'successful_runs': successful_runs,
            'failed_runs': failed_runs,
            'success_rate': (successful_runs / total_runs * 100) if total_runs > 0 else 0,
            'avg_response_time_ms': avg_response_time,
            'agency_breakdown': agency_stats,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    
    def _get_notification_summary(self, db, start_date: datetime, end_date: datetime) -> Dict:
        """Get notification delivery summary for the period."""
        notifications = db.query(Notification).filter(
            and_(
                Notification.sent_at >= start_date,
                Notification.sent_at <= end_date
            )
        ).all()
        
        total_notifications = len(notifications)
        delivered = len([n for n in notifications if n.status == 'delivered'])
        failed = len([n for n in notifications if n.status == 'failed'])
        pending = len([n for n in notifications if n.status == 'pending'])
        
        # Get notification type breakdown
        type_breakdown = {}
        for notification in notifications:
            notification_type = notification.notification_type
            if notification_type not in type_breakdown:
                type_breakdown[notification_type] = {
                    'total': 0,
                    'delivered': 0,
                    'failed': 0,
                    'pending': 0
                }
            
            type_breakdown[notification_type]['total'] += 1
            if notification.status == 'delivered':
                type_breakdown[notification_type]['delivered'] += 1
            elif notification.status == 'failed':
                type_breakdown[notification_type]['failed'] += 1
            elif notification.status == 'pending':
                type_breakdown[notification_type]['pending'] += 1
        
        return {
            'total_notifications': total_notifications,
            'delivered': delivered,
            'failed': failed,
            'pending': pending,
            'delivery_rate': (delivered / total_notifications * 100) if total_notifications > 0 else 0,
            'type_breakdown': type_breakdown,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    
    def _generate_impact_assessments(self, db, form_changes: List[Dict]) -> List[Dict]:
        """Generate impact assessments for form changes."""
        impact_assessments = []
        
        for change_data in form_changes:
            change_id = change_data['id']
            
            # Get client impact
            client_usage = db.query(ClientFormUsage).filter(
                ClientFormUsage.form_id == change_data.get('form_id'),
                ClientFormUsage.is_active == True
            ).join(Client).all()
            
            total_clients_impacted = len(client_usage)
            
            # Get total active clients for percentage calculation
            total_active_clients = db.query(Client).filter(Client.is_active == True).count()
            impact_percentage = (total_clients_impacted / total_active_clients * 100) if total_active_clients > 0 else 0
            
            # Get ICP segment breakdown
            icp_segments = {}
            for usage in client_usage:
                segment = usage.client.icp_segment or 'Unknown'
                if segment not in icp_segments:
                    icp_segments[segment] = 0
                icp_segments[segment] += 1
            
            impact_assessments.append({
                'form_change_id': change_id,
                'form_name': change_data['form_name'],
                'agency_name': change_data['agency_name'],
                'total_clients_impacted': total_clients_impacted,
                'impact_percentage': impact_percentage,
                'icp_segment_breakdown': icp_segments,
                'severity': change_data['severity'],
                'ai_confidence_score': change_data.get('ai_confidence_score'),
                'ai_severity_score': change_data.get('ai_severity_score')
            })
        
        return impact_assessments
    
    def _generate_executive_summary(
        self,
        form_changes: List[Dict],
        monitoring_stats: Optional[Dict],
        notification_summary: Optional[Dict]
    ) -> Dict:
        """Generate executive summary of the weekly report."""
        total_changes = len(form_changes)
        
        # Severity breakdown
        severity_breakdown = {}
        for change in form_changes:
            severity = change['severity']
            if severity not in severity_breakdown:
                severity_breakdown[severity] = 0
            severity_breakdown[severity] += 1
        
        # Agency breakdown
        agency_breakdown = {}
        for change in form_changes:
            agency = change['agency_name']
            if agency not in agency_breakdown:
                agency_breakdown[agency] = 0
            agency_breakdown[agency] += 1
        
        # Change type breakdown
        change_type_breakdown = {}
        for change in form_changes:
            change_type = change['change_type']
            if change_type not in change_type_breakdown:
                change_type_breakdown[change_type] = 0
            change_type_breakdown[change_type] += 1
        
        # Calculate critical changes
        critical_changes = [c for c in form_changes if c['severity'] == 'critical']
        high_priority_changes = [c for c in form_changes if c['severity'] in ['critical', 'high']]
        
        return {
            'total_changes_detected': total_changes,
            'critical_changes': len(critical_changes),
            'high_priority_changes': len(high_priority_changes),
            'severity_breakdown': severity_breakdown,
            'agency_breakdown': agency_breakdown,
            'change_type_breakdown': change_type_breakdown,
            'monitoring_performance': {
                'success_rate': monitoring_stats.get('success_rate', 0) if monitoring_stats else 0,
                'total_runs': monitoring_stats.get('total_runs', 0) if monitoring_stats else 0
            },
            'notification_performance': {
                'delivery_rate': notification_summary.get('delivery_rate', 0) if notification_summary else 0,
                'total_notifications': notification_summary.get('total_notifications', 0) if notification_summary else 0
            }
        }
    
    def _generate_trend_analysis(self, db, start_date: datetime, end_date: datetime) -> Dict:
        """Generate trend analysis for the reporting period."""
        # Get daily change counts for trend analysis
        daily_changes = db.query(
            func.date(FormChange.detected_at).label('date'),
            func.count(FormChange.id).label('change_count')
        ).filter(
            and_(
                FormChange.detected_at >= start_date,
                FormChange.detected_at <= end_date
            )
        ).group_by(func.date(FormChange.detected_at)).all()
        
        # Convert to dictionary format
        daily_trends = {}
        for date, count in daily_changes:
            daily_trends[date.strftime('%Y-%m-%d')] = count
        
        # Calculate trend metrics
        change_counts = [count for _, count in daily_changes]
        avg_daily_changes = sum(change_counts) / len(change_counts) if change_counts else 0
        
        # Determine trend direction
        if len(change_counts) >= 2:
            first_half = change_counts[:len(change_counts)//2]
            second_half = change_counts[len(change_counts)//2:]
            first_avg = sum(first_half) / len(first_half) if first_half else 0
            second_avg = sum(second_half) / len(second_half) if second_half else 0
            
            if second_avg > first_avg * 1.1:
                trend_direction = 'increasing'
            elif second_avg < first_avg * 0.9:
                trend_direction = 'decreasing'
            else:
                trend_direction = 'stable'
        else:
            trend_direction = 'insufficient_data'
        
        return {
            'daily_trends': daily_trends,
            'avg_daily_changes': avg_daily_changes,
            'trend_direction': trend_direction,
            'total_period_changes': sum(change_counts)
        }
    
    def _generate_recommendations(self, form_changes: List[Dict], monitoring_stats: Optional[Dict]) -> List[str]:
        """Generate actionable recommendations based on report data."""
        recommendations = []
        
        # Analyze critical changes
        critical_changes = [c for c in form_changes if c['severity'] == 'critical']
        if critical_changes:
            recommendations.append(
                f"Immediate attention required: {len(critical_changes)} critical changes detected. "
                "Review and prioritize development work for these changes."
            )
        
        # Analyze monitoring performance
        if monitoring_stats:
            success_rate = monitoring_stats.get('success_rate', 0)
            if success_rate < 95:
                recommendations.append(
                    f"Monitoring success rate is {success_rate:.1f}%, below target of 95%. "
                    "Investigate failed monitoring runs and improve error handling."
                )
            
            failed_runs = monitoring_stats.get('failed_runs', 0)
            if failed_runs > 0:
                recommendations.append(
                    f"{failed_runs} monitoring runs failed during the period. "
                    "Review error logs and implement retry mechanisms."
                )
        
        # Analyze change distribution
        agency_breakdown = {}
        for change in form_changes:
            agency = change['agency_name']
            if agency not in agency_breakdown:
                agency_breakdown[agency] = 0
            agency_breakdown[agency] += 1
        
        # Identify agencies with high change frequency
        high_change_agencies = [agency for agency, count in agency_breakdown.items() if count > 5]
        if high_change_agencies:
            recommendations.append(
                f"High change frequency detected for agencies: {', '.join(high_change_agencies)}. "
                "Consider increasing monitoring frequency for these agencies."
            )
        
        # General recommendations
        if len(form_changes) == 0:
            recommendations.append("No changes detected during the period. Verify monitoring is functioning correctly.")
        elif len(form_changes) > 20:
            recommendations.append(
                f"High volume of changes detected ({len(form_changes)}). "
                "Consider implementing automated change classification to prioritize critical changes."
            )
        
        return recommendations
    
    def export_report(
        self,
        report_data: Dict[str, Any],
        format: str = 'pdf',
        include_charts: bool = True
    ) -> bytes:
        """
        Export the weekly report in various formats.
        
        Args:
            report_data: Report data from generate_weekly_report
            format: Export format ('pdf', 'excel', 'csv')
            include_charts: Include charts and visualizations
            
        Returns:
            Report data as bytes
        """
        if format == 'pdf':
            return self.export_utils.export_to_pdf(report_data, include_charts)
        elif format == 'excel':
            return self.export_utils.export_to_excel(report_data, include_charts)
        elif format == 'csv':
            return self.export_utils.export_to_csv(report_data)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def schedule_weekly_report(
        self,
        recipients: List[str],
        day_of_week: str = 'monday',
        time: str = '09:00',
        timezone: str = 'UTC',
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Schedule automated weekly report generation and distribution.
        
        Args:
            recipients: List of email addresses to receive the report
            day_of_week: Day of week to generate report ('monday', 'tuesday', etc.)
            time: Time of day to generate report (HH:MM format)
            timezone: Timezone for scheduling
            filters: Optional filters to apply to the report
            
        Returns:
            Scheduling confirmation details
        """
        # This would integrate with the scheduler service
        # For now, return scheduling details
        return {
            'scheduled': True,
            'recipients': recipients,
            'schedule': {
                'day_of_week': day_of_week,
                'time': time,
                'timezone': timezone
            },
            'filters': filters or {},
            'next_run': self._calculate_next_run(day_of_week, time, timezone)
        }
    
    def _calculate_next_run(self, day_of_week: str, time: str, timezone: str) -> datetime:
        """Calculate the next scheduled run time."""
        # Simplified calculation - in production, use proper scheduling library
        now = datetime.now()
        days_ahead = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        target_day = days_ahead.get(day_of_week.lower(), 0)
        current_day = now.weekday()
        
        days_until_target = (target_day - current_day) % 7
        if days_until_target == 0 and now.time() > datetime.strptime(time, '%H:%M').time():
            days_until_target = 7
        
        next_run = now + timedelta(days=days_until_target)
        next_run = next_run.replace(
            hour=int(time.split(':')[0]),
            minute=int(time.split(':')[1]),
            second=0,
            microsecond=0
        )
        
        return next_run


def generate_weekly_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function to generate a weekly report.
    
    Args:
        start_date: Start date for report period
        end_date: End date for report period
        **kwargs: Additional arguments passed to WeeklyReportGenerator.generate_weekly_report
        
    Returns:
        Weekly report data
    """
    generator = WeeklyReportGenerator()
    return generator.generate_weekly_report(start_date, end_date, **kwargs)


def export_weekly_report(
    report_data: Dict[str, Any],
    format: str = 'pdf',
    **kwargs
) -> bytes:
    """
    Convenience function to export a weekly report.
    
    Args:
        report_data: Report data from generate_weekly_report
        format: Export format
        **kwargs: Additional arguments passed to WeeklyReportGenerator.export_report
        
    Returns:
        Report data as bytes
    """
    generator = WeeklyReportGenerator()
    return generator.export_report(report_data, format, **kwargs) 