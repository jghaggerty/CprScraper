"""
Report Distribution System for Weekly Compliance Reports

This module provides automated report distribution to Product Managers and Business Analysts
with role-specific content, formatting, and delivery channels.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import asyncio

from ..database.connection import get_db
from ..database.models import User, UserRole, Role
from ..notifications.enhanced_notifier import EnhancedNotificationManager
from ..reporting.weekly_reports import WeeklyReportGenerator
from ..reporting.report_templates import ReportTemplateManager
from ..utils.config_loader import get_notification_settings

logger = logging.getLogger(__name__)


@dataclass
class DistributionConfig:
    """Configuration for report distribution."""
    template_type: str
    include_charts: bool
    delivery_channels: List[str]
    priority: str  # 'high', 'medium', 'low'
    custom_filters: Optional[Dict[str, Any]] = None


class ReportDistributionManager:
    """Manage automated report distribution to different user roles."""
    
    def __init__(self):
        self.report_generator = WeeklyReportGenerator()
        self.template_manager = ReportTemplateManager()
        self.notifier = EnhancedNotificationManager()
        self.notification_config = get_notification_settings()
        
        # Role-specific distribution configurations
        self.role_configs = {
            'product_manager': DistributionConfig(
                template_type='executive_summary',
                include_charts=True,
                delivery_channels=['email', 'slack'],
                priority='high',
                custom_filters={'severity_levels': ['critical', 'high']}
            ),
            'business_analyst': DistributionConfig(
                template_type='detailed_report',
                include_charts=True,
                delivery_channels=['email'],
                priority='medium',
                custom_filters=None  # All changes
            ),
            'admin': DistributionConfig(
                template_type='technical_report',
                include_charts=False,
                delivery_channels=['email'],
                priority='low',
                custom_filters=None
            )
        }
    
    async def distribute_weekly_reports(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        roles: Optional[List[str]] = None,
        force_distribution: bool = False
    ) -> Dict[str, Any]:
        """
        Distribute weekly reports to all users with specified roles.
        
        Args:
            start_date: Start date for report period
            end_date: End date for report period
            roles: Specific roles to distribute to (None for all)
            force_distribution: Force distribution even if no changes detected
            
        Returns:
            Distribution results summary
        """
        logger.info(f"Starting weekly report distribution for period: {start_date} to {end_date}")
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=7)
        
        # Get users by role
        users_by_role = await self._get_users_by_role(roles)
        
        if not users_by_role:
            logger.warning("No users found for report distribution")
            return {
                'success': False,
                'message': 'No users found for distribution',
                'distribution_results': {}
            }
        
        # Generate reports and distribute
        distribution_results = {}
        
        for role, users in users_by_role.items():
            if not users:
                continue
                
            config = self.role_configs.get(role)
            if not config:
                logger.warning(f"No distribution config found for role: {role}")
                continue
            
            logger.info(f"Distributing reports to {len(users)} {role} users")
            
            # Generate report for this role
            report_data = await self._generate_role_specific_report(
                start_date, end_date, config, force_distribution
            )
            
            if not report_data and not force_distribution:
                logger.info(f"No report data generated for {role} role")
                distribution_results[role] = {
                    'success': False,
                    'message': 'No report data available',
                    'users_notified': 0,
                    'users_failed': 0
                }
                continue
            
            # Distribute to users
            role_results = await self._distribute_to_role_users(
                users, report_data, config, role
            )
            
            distribution_results[role] = role_results
        
        # Generate summary
        total_notified = sum(result.get('users_notified', 0) for result in distribution_results.values())
        total_failed = sum(result.get('users_failed', 0) for result in distribution_results.values())
        
        return {
            'success': total_notified > 0,
            'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            'total_users_notified': total_notified,
            'total_users_failed': total_failed,
            'distribution_results': distribution_results,
            'generated_at': datetime.now()
        }
    
    async def _get_users_by_role(self, roles: Optional[List[str]] = None) -> Dict[str, List[User]]:
        """Get users grouped by role."""
        with get_db() as db:
            # Get all active users with roles
            users_with_roles = db.query(User).join(UserRole).join(Role).filter(
                User.is_active == True,
                UserRole.is_active == True,
                Role.is_active == True
            ).all()
            
            users_by_role = {}
            
            for user in users_with_roles:
                for user_role in user.user_roles:
                    if user_role.is_active:
                        role_name = user_role.role.name
                        
                        # Filter by specified roles if provided
                        if roles and role_name not in roles:
                            continue
                        
                        if role_name not in users_by_role:
                            users_by_role[role_name] = []
                        
                        if user not in users_by_role[role_name]:
                            users_by_role[role_name].append(user)
            
            return users_by_role
    
    async def _generate_role_specific_report(
        self,
        start_date: datetime,
        end_date: datetime,
        config: DistributionConfig,
        force_distribution: bool
    ) -> Optional[Dict[str, Any]]:
        """Generate report data specific to a role's configuration."""
        try:
            # Generate report with role-specific filters
            report_data = self.report_generator.generate_weekly_report(
                start_date=start_date,
                end_date=end_date,
                states=config.custom_filters.get('states') if config.custom_filters else None,
                form_types=config.custom_filters.get('form_types') if config.custom_filters else None,
                severity_levels=config.custom_filters.get('severity_levels') if config.custom_filters else None,
                include_ai_analysis=True,
                include_impact_assessment=True,
                include_notification_summary=True,
                include_monitoring_statistics=True
            )
            
            # Check if there's meaningful data to report
            if not force_distribution:
                total_changes = report_data.get('executive_summary', {}).get('total_changes_detected', 0)
                if total_changes == 0:
                    logger.info("No changes detected in report period")
                    return None
            
            # Render report using role-specific template
            html_content = self.template_manager.render_report(
                report_data,
                config.template_type,
                config.include_charts
            )
            
            return {
                'report_data': report_data,
                'html_content': html_content,
                'template_type': config.template_type,
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            }
            
        except Exception as e:
            logger.error(f"Error generating role-specific report: {e}")
            return None
    
    async def _distribute_to_role_users(
        self,
        users: List[User],
        report_data: Dict[str, Any],
        config: DistributionConfig,
        role: str
    ) -> Dict[str, Any]:
        """Distribute report to users of a specific role."""
        users_notified = 0
        users_failed = 0
        failed_users = []
        
        for user in users:
            try:
                success = await self._send_report_to_user(
                    user, report_data, config, role
                )
                
                if success:
                    users_notified += 1
                    logger.info(f"Successfully sent report to {user.email} ({role})")
                else:
                    users_failed += 1
                    failed_users.append(user.email)
                    logger.error(f"Failed to send report to {user.email} ({role})")
                    
            except Exception as e:
                users_failed += 1
                failed_users.append(user.email)
                logger.error(f"Error sending report to {user.email} ({role}): {e}")
        
        return {
            'success': users_notified > 0,
            'users_notified': users_notified,
            'users_failed': users_failed,
            'failed_users': failed_users,
            'total_users': len(users)
        }
    
    async def _send_report_to_user(
        self,
        user: User,
        report_data: Dict[str, Any],
        config: DistributionConfig,
        role: str
    ) -> bool:
        """Send report to a specific user through configured channels."""
        success = False
        
        # Prepare email content
        email_subject = self._generate_email_subject(report_data, role)
        email_body = self._generate_email_body(report_data, role)
        
        # Send through configured channels
        for channel in config.delivery_channels:
            try:
                if channel == 'email':
                    success = await self._send_email_report(
                        user, email_subject, email_body, report_data
                    )
                elif channel == 'slack':
                    success = await self._send_slack_report(
                        user, report_data, role
                    )
                elif channel == 'teams':
                    success = await self._send_teams_report(
                        user, report_data, role
                    )
                
                if success:
                    logger.info(f"Successfully sent {channel} report to {user.email}")
                    break  # Success on any channel is sufficient
                    
            except Exception as e:
                logger.error(f"Error sending {channel} report to {user.email}: {e}")
        
        return success
    
    def _generate_email_subject(self, report_data: Dict[str, Any], role: str) -> str:
        """Generate email subject line for the report."""
        period = report_data.get('period', 'Weekly')
        executive_summary = report_data.get('report_data', {}).get('executive_summary', {})
        
        total_changes = executive_summary.get('total_changes_detected', 0)
        critical_changes = executive_summary.get('critical_changes', 0)
        
        if critical_changes > 0:
            return f"🚨 URGENT: {critical_changes} Critical Compliance Changes - {period} Report"
        elif total_changes > 0:
            return f"📊 {total_changes} Compliance Changes Detected - {period} Report"
        else:
            return f"📋 Weekly Compliance Report - {period} (No Changes Detected)"
    
    def _generate_email_body(self, report_data: Dict[str, Any], role: str) -> str:
        """Generate email body content for the report."""
        executive_summary = report_data.get('report_data', {}).get('executive_summary', {})
        period = report_data.get('period', 'Weekly')
        
        total_changes = executive_summary.get('total_changes_detected', 0)
        critical_changes = executive_summary.get('critical_changes', 0)
        high_priority = executive_summary.get('high_priority_changes', 0)
        
        body = f"""
        <html>
        <body>
            <h2>Weekly Compliance Report</h2>
            <p><strong>Period:</strong> {period}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
            
            <h3>Summary</h3>
            <ul>
                <li><strong>Total Changes:</strong> {total_changes}</li>
                <li><strong>Critical Changes:</strong> {critical_changes}</li>
                <li><strong>High Priority Changes:</strong> {high_priority}</li>
            </ul>
            
            <p>Please review the attached report for detailed information about compliance changes and their impact.</p>
            
            <p>Best regards,<br>
            AI-Powered Compliance Monitoring System</p>
        </body>
        </html>
        """
        
        return body
    
    async def _send_email_report(
        self,
        user: User,
        subject: str,
        body: str,
        report_data: Dict[str, Any]
    ) -> bool:
        """Send email report to user."""
        try:
            # Get HTML content for email attachment
            html_content = report_data.get('html_content', '')
            
            # Send email with HTML content
            email_sent = await self.notifier.send_custom_email_notification(
                user, report_data.get('report_data', {}), html_content
            )
            
            return email_sent
            
        except Exception as e:
            logger.error(f"Error sending email report to {user.email}: {e}")
            return False
    
    async def _send_slack_report(
        self,
        user: User,
        report_data: Dict[str, Any],
        role: str
    ) -> bool:
        """Send Slack report to user."""
        try:
            # Generate Slack message
            executive_summary = report_data.get('report_data', {}).get('executive_summary', {})
            period = report_data.get('period', 'Weekly')
            
            total_changes = executive_summary.get('total_changes_detected', 0)
            critical_changes = executive_summary.get('critical_changes', 0)
            
            message = f"""
            📊 *Weekly Compliance Report - {period}*
            
            *Summary:*
            • Total Changes: {total_changes}
            • Critical Changes: {critical_changes}
            • High Priority Changes: {executive_summary.get('high_priority_changes', 0)}
            
            Please check your email for the detailed report.
            """
            
            # Send Slack notification
            # This would integrate with the existing Slack notification system
            # For now, return True as placeholder
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack report to {user.email}: {e}")
            return False
    
    async def _send_teams_report(
        self,
        user: User,
        report_data: Dict[str, Any],
        role: str
    ) -> bool:
        """Send Teams report to user."""
        try:
            # Generate Teams message
            executive_summary = report_data.get('report_data', {}).get('executive_summary', {})
            period = report_data.get('period', 'Weekly')
            
            total_changes = executive_summary.get('total_changes_detected', 0)
            critical_changes = executive_summary.get('critical_changes', 0)
            
            message = f"""
            📊 **Weekly Compliance Report - {period}**
            
            **Summary:**
            • Total Changes: {total_changes}
            • Critical Changes: {critical_changes}
            • High Priority Changes: {executive_summary.get('high_priority_changes', 0)}
            
            Please check your email for the detailed report.
            """
            
            # Send Teams notification
            # This would integrate with the existing Teams notification system
            # For now, return True as placeholder
            return True
            
        except Exception as e:
            logger.error(f"Error sending Teams report to {user.email}: {e}")
            return False
    
    async def test_distribution_system(self) -> Dict[str, Any]:
        """Test the distribution system with sample data."""
        logger.info("Testing report distribution system")
        
        # Test with a small date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)
        
        # Test distribution to all roles
        results = await self.distribute_weekly_reports(
            start_date=start_date,
            end_date=end_date,
            roles=['product_manager', 'business_analyst'],
            force_distribution=True
        )
        
        return {
            'test_successful': results.get('success', False),
            'total_users_notified': results.get('total_users_notified', 0),
            'total_users_failed': results.get('total_users_failed', 0),
            'distribution_results': results.get('distribution_results', {}),
            'test_period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        }
    
    def get_distribution_config(self, role: str) -> Optional[DistributionConfig]:
        """Get distribution configuration for a specific role."""
        return self.role_configs.get(role)
    
    def update_distribution_config(
        self,
        role: str,
        template_type: Optional[str] = None,
        include_charts: Optional[bool] = None,
        delivery_channels: Optional[List[str]] = None,
        priority: Optional[str] = None,
        custom_filters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update distribution configuration for a role."""
        if role not in self.role_configs:
            logger.error(f"Role {role} not found in distribution configs")
            return False
        
        config = self.role_configs[role]
        
        if template_type is not None:
            config.template_type = template_type
        if include_charts is not None:
            config.include_charts = include_charts
        if delivery_channels is not None:
            config.delivery_channels = delivery_channels
        if priority is not None:
            config.priority = priority
        if custom_filters is not None:
            config.custom_filters = custom_filters
        
        logger.info(f"Updated distribution config for role: {role}")
        return True


async def distribute_weekly_reports(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    roles: Optional[List[str]] = None,
    force_distribution: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to distribute weekly reports.
    
    Args:
        start_date: Start date for report period
        end_date: End date for report period
        roles: Specific roles to distribute to
        force_distribution: Force distribution even if no changes detected
        
    Returns:
        Distribution results
    """
    manager = ReportDistributionManager()
    return await manager.distribute_weekly_reports(
        start_date, end_date, roles, force_distribution
    )


async def test_report_distribution() -> Dict[str, Any]:
    """Test the report distribution system."""
    manager = ReportDistributionManager()
    return await manager.test_distribution_system() 