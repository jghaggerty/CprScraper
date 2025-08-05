"""
Enhanced Notification System with Role-Based Notifications

This module extends the existing notification system to provide role-based
notifications for Product Managers and Business Analysts, with customizable
preferences and delivery mechanisms.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..database.models import (
    FormChange, Notification, User, Role, UserRole, UserNotificationPreference,
    Agency, Form, Client, ClientFormUsage
)
from ..auth.user_service import UserService
from .notifier import NotificationTemplate, EmailNotifier, SlackNotifier, TeamsNotifier
from .email_templates import EnhancedEmailTemplates
from .preference_manager import EnhancedNotificationPreferenceManager, should_send_notification
from .channel_integration import ChannelIntegrationManager, NotificationResult
from .delivery_tracker import NotificationDeliveryTracker, RetryConfig, DeliveryStatus
from ..utils.config_loader import get_notification_settings

logger = logging.getLogger(__name__)


class RoleBasedNotificationTemplate:
    """Enhanced template generator with role-specific content."""
    
    def __init__(self):
        self.user_service = UserService()
        self.enhanced_templates = EnhancedEmailTemplates()
        
        # Role-specific templates
        self.product_manager_template = self.enhanced_templates.get_template('product_manager')
        self.business_analyst_template = self.enhanced_templates.get_template('business_analyst')
        

    
    def get_template_for_role(self, role_name: str):
        """Get the appropriate template for a user role."""
        if role_name == 'business_analyst':
            return self.business_analyst_template
        else:
            return self.product_manager_template


class EnhancedNotificationManager:
    """Enhanced notification management with role-based delivery."""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.notification_config = get_notification_settings()
        self.notifiers = self._setup_notifiers()
        self.user_service = UserService()
        self.template_generator = RoleBasedNotificationTemplate()
        self.preference_manager = EnhancedNotificationPreferenceManager()
        self.channel_manager = ChannelIntegrationManager()
        self.delivery_tracker = NotificationDeliveryTracker(retry_config)
    
    def _setup_notifiers(self) -> Dict:
        """Set up notification services based on configuration."""
        notifiers = {}
        
        # Email notifier
        email_config = self.notification_config.get('email', {})
        if email_config.get('enabled', False):
            notifiers['email'] = EmailNotifier(email_config)
        
        # Slack notifier
        slack_config = self.notification_config.get('slack', {})
        if slack_config.get('enabled', False):
            notifiers['slack'] = SlackNotifier(slack_config.get('webhook_url'))
        
        # Teams notifier
        teams_config = self.notification_config.get('teams', {})
        if teams_config.get('enabled', False):
            notifiers['teams'] = TeamsNotifier(teams_config.get('webhook_url'))
        
        return notifiers
    
    async def send_role_based_notification(self, form_change_id: int) -> Dict[str, Any]:
        """
        Send role-based notifications for a form change.
        
        Returns:
            Dictionary with notification results by role and channel
        """
        results = {
            'product_managers': {},
            'business_analysts': {},
            'summary': {
                'total_notifications_sent': 0,
                'total_notifications_failed': 0,
                'roles_notified': []
            }
        }
        
        with get_db() as db:
            # Get the form change with related data
            form_change = db.query(FormChange).filter(
                FormChange.id == form_change_id
            ).first()
            
            if not form_change:
                logger.error(f"Form change {form_change_id} not found")
                return results
            
            form = form_change.form
            agency = form.agency
            
            # Calculate impact assessment
            impact_data = await self._calculate_impact_assessment(form.id, db)
            
            # Prepare base notification data
            base_change_data = {
                'detected_at': form_change.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
                'generated_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'change_id': form_change.id,
                'severity': form_change.severity,
                'agency_name': agency.name,
                'form_name': form.name,
                'cpr_report_id': form.cpr_report_id,
                'change_type': form_change.change_type,
                'change_description': form_change.change_description,
                'effective_date': form_change.effective_date.strftime('%Y-%m-%d') if form_change.effective_date else None,
                'form_url': form.form_url,
                'instructions_url': form.instructions_url,
                'agency_contact_email': agency.contact_email or form.contact_email,
                'agency_contact_phone': agency.contact_phone,
                'clients_impacted': impact_data['clients_impacted'],
                'icp_percentage': impact_data['icp_percentage'],
                'impact_details': impact_data.get('details', []),
                'field_mapping_current': True,
                'field_mapping_updated': True,
                # AI Analysis fields
                'ai_confidence_score': form_change.ai_confidence_score or 0,
                'ai_change_category': form_change.ai_change_category,
                'ai_severity_score': form_change.ai_severity_score or 0,
                'ai_reasoning': form_change.ai_reasoning,
                'ai_semantic_similarity': form_change.ai_semantic_similarity or 0,
                'is_cosmetic_change': form_change.is_cosmetic_change or False,
                'old_value': form_change.old_value,
                'new_value': form_change.new_value
            }
            
            # Send notifications to Product Managers
            pm_results = await self._send_notifications_to_role(
                'product_manager', form_change, base_change_data, db
            )
            results['product_managers'] = pm_results
            
            # Send notifications to Business Analysts
            ba_results = await self._send_notifications_to_role(
                'business_analyst', form_change, base_change_data, db
            )
            results['business_analysts'] = ba_results
            
            # Update summary
            for role_results in [pm_results, ba_results]:
                for user_results in role_results.values():
                    for channel_result in user_results.values():
                        if channel_result['success']:
                            results['summary']['total_notifications_sent'] += 1
                        else:
                            results['summary']['total_notifications_failed'] += 1
            
            if pm_results:
                results['summary']['roles_notified'].append('product_manager')
            if ba_results:
                results['summary']['roles_notified'].append('business_analyst')
        
        return results
    
    async def _send_notifications_to_role(self, role_name: str, form_change: FormChange, 
                                         base_change_data: Dict, db: Session) -> Dict[str, Dict]:
        """Send notifications to users with a specific role using enhanced channel integration."""
        results = {}
        
        # Get users with this role
        users = self.user_service.get_users_by_role(role_name)
        
        for user in users:
            user_results = {}
            
            # Prepare role-specific notification data
            change_data = base_change_data.copy()
            change_data['user_name'] = f"{user.first_name} {user.last_name}"
            change_data['user_role'] = role_name
            change_data['form_change_id'] = form_change.id
            
            # Get user's notification preferences
            preferences = self.preference_manager.get_user_notification_preferences(user.id)
            
            # Add role-specific template preference
            for pref in preferences:
                pref['template_type'] = role_name
                pref['role'] = role_name
            
            # Send notifications through all configured channels with delivery tracking
            notification_results = await self._send_notifications_with_tracking(
                change_data, preferences, user, form_change.id, db
            )
            
            # Convert results to expected format
            for result in notification_results:
                user_results[result.channel] = {
                    'success': result.success,
                    'error': result.error_message,
                    'retry_count': result.retry_count,
                    'sent_at': result.sent_at.isoformat() if result.sent_at else None
                }
            
            if user_results:
                results[user.username] = user_results
        
        return results
    
    async def _send_notifications_with_tracking(self, change_data: Dict, preferences: List[Dict], 
                                              user: User, form_change_id: int, db: Session) -> List[NotificationResult]:
        """Send notifications with delivery tracking and retry mechanisms."""
        results = []
        
        for pref in preferences:
            if not pref.get('is_enabled', True):
                continue
                
            channel_type = pref['notification_type']
            
            # Create notification record in database
            notification = Notification(
                form_change_id=form_change_id,
                notification_type=channel_type,
                recipient=user.email if channel_type == 'email' else user.username,
                subject=f"🚨 Payroll Form Change: {change_data['agency_name']} - {change_data['form_name']}",
                message=self._generate_notification_message(change_data, pref),
                status=DeliveryStatus.PENDING.value
            )
            db.add(notification)
            db.commit()
            db.refresh(notification)
            
            # Prepare content for delivery
            content = {
                'subject': notification.subject,
                'message': notification.message,
                'recipient': notification.recipient,
                'template_type': pref.get('template_type', 'product_manager'),
                'change_data': change_data
            }
            
            # Track delivery with retry mechanisms
            delivery_result = await self.delivery_tracker.track_notification_delivery(
                notification.id, channel_type, notification.recipient, content
            )
            
            # Create result object
            result = NotificationResult(
                success=delivery_result.success,
                error_message=delivery_result.error_message,
                delivery_time=delivery_result.delivery_time,
                response_data=delivery_result.response_data,
                channel=channel_type,
                retry_count=notification.retry_count,
                sent_at=notification.sent_at
            )
            
            results.append(result)
        
        return results
    
    def _generate_notification_message(self, change_data: Dict, preference: Dict) -> str:
        """Generate notification message based on template and preference."""
        template_type = preference.get('template_type', 'product_manager')
        
        # Get appropriate template
        if template_type == 'business_analyst':
            template = self.template_generator.get_template_for_role('business_analyst')
        else:
            template = self.template_generator.get_template_for_role('product_manager')
        
        # Render template with change data
        try:
            return self.template_generator.enhanced_templates.render_template(template_type, change_data)
        except Exception as e:
            logger.error(f"Error rendering notification template: {e}")
            # Fallback to simple message
            return f"Form change detected: {change_data.get('change_description', 'Unknown change')}"
    

    
    async def _send_custom_email_notification(self, user: User, change_data: Dict, 
                                            html_content: str) -> bool:
        """Send custom email notification to a specific user."""
        try:
            email_config = self.notification_config.get('email', {})
            notifier = EmailNotifier(email_config)
            
            # Override recipient for this specific user
            notifier.to_addresses = [user.email]
            
            # Create message with custom content
            from email.mime.text import MimeText
            from email.mime.multipart import MimeMultipart
            
            msg = MimeMultipart('alternative')
            msg['Subject'] = f"🚨 Payroll Form Change: {change_data['agency_name']} - {change_data['form_name']}"
            msg['From'] = email_config.get('from_address')
            msg['To'] = user.email
            
            html_part = MimeText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            import smtplib
            with smtplib.SMTP(notifier.smtp_server, notifier.smtp_port) as server:
                server.starttls()
                server.login(notifier.username, notifier.password)
                server.send_message(msg)
            
            logger.info(f"Custom email notification sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send custom email notification to {user.email}: {e}")
            return False
    
    async def _calculate_impact_assessment(self, form_id: int, db: Session) -> Dict:
        """Calculate the impact assessment for a form change."""
        # Get clients using this form
        client_usage = db.query(ClientFormUsage).filter(
            ClientFormUsage.form_id == form_id,
            ClientFormUsage.is_active == True
        ).all()
        
        total_clients = len(client_usage)
        
        # Calculate ICP segment percentage
        total_active_clients = db.query(Client).filter(Client.is_active == True).count()
        icp_percentage = round((total_clients / max(total_active_clients, 1)) * 100, 2)
        
        return {
            'clients_impacted': total_clients,
            'icp_percentage': icp_percentage,
            'details': [
                f"Form used by {total_clients} active clients",
                f"Represents {icp_percentage}% of total client base"
            ]
        }
    
    async def send_batch_role_notifications(self, form_change_ids: List[int]) -> Dict:
        """Send role-based notifications for multiple form changes."""
        results = {}
        
        for change_id in form_change_ids:
            try:
                change_results = await self.send_role_based_notification(change_id)
                results[change_id] = change_results
            except Exception as e:
                logger.error(f"Error processing role-based notification for change {change_id}: {e}")
                results[change_id] = {}
        
        return results
    
    async def test_role_based_notifications(self) -> Dict[str, Any]:
        """Test role-based notification system."""
        test_data = {
            'detected_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'severity': 'medium',
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'cpr_report_id': 'TEST-CPR-001',
            'change_type': 'test',
            'change_description': 'This is a test role-based notification',
            'effective_date': None,
            'form_url': 'https://example.com/test-form',
            'instructions_url': 'https://example.com/test-instructions',
            'agency_contact_email': 'test@example.com',
            'agency_contact_phone': '(555) 123-4567',
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'impact_details': ['Test impact detail'],
            'field_mapping_current': True,
            'field_mapping_updated': True,
            'ai_confidence_score': 85,
            'ai_change_category': 'form_update',
            'ai_severity_score': 75,
            'ai_reasoning': 'Test AI reasoning for change classification',
            'ai_semantic_similarity': 80,
            'is_cosmetic_change': False,
            'old_value': 'old_test_value',
            'new_value': 'new_test_value'
        }
        
        results = {
            'product_managers': {},
            'business_analysts': {},
            'summary': {
                'total_notifications_sent': 0,
                'total_notifications_failed': 0,
                'roles_notified': []
            }
        }
        
        # Test with each role
        for role_name in ['product_manager', 'business_analyst']:
            users = self.user_service.get_users_by_role(role_name)
            
            for user in users:
                logger.info(f"Testing notification for {user.username} ({role_name})")
                
                # Test email notification
                if 'email' in self.notifiers:
                    try:
                        success = await self._send_custom_email_notification(
                            user, test_data, 
                            self.template_generator.get_template_for_role(role_name).render(**test_data)
                        )
                        
                        if role_name == 'product_manager':
                            results['product_managers'][user.username] = {'email': {'success': success}}
                        else:
                            results['business_analysts'][user.username] = {'email': {'success': success}}
                        
                        if success:
                            results['summary']['total_notifications_sent'] += 1
                        else:
                            results['summary']['total_notifications_failed'] += 1
                            
                    except Exception as e:
                        logger.error(f"Test notification failed for {user.username}: {e}")
                        if role_name == 'product_manager':
                            results['product_managers'][user.username] = {'email': {'success': False, 'error': str(e)}}
                        else:
                            results['business_analysts'][user.username] = {'email': {'success': False, 'error': str(e)}}
                        results['summary']['total_notifications_failed'] += 1
        
        if results['product_managers']:
            results['summary']['roles_notified'].append('product_manager')
        if results['business_analysts']:
            results['summary']['roles_notified'].append('business_analyst')
        
        return results
    
    async def test_channel_integration(self) -> Dict[str, Any]:
        """Test notification channel integration."""
        logger.info("Testing notification channel integration...")
        
        # Test channel connectivity
        connectivity_results = await self.channel_manager.test_channel_connectivity()
        
        # Get channel status
        channel_status = self.channel_manager.get_channel_status()
        
        return {
            'connectivity': connectivity_results,
            'status': channel_status,
            'available_channels': list(self.channel_manager.notifiers.keys())
        }


async def main():
    """Test the enhanced notification system."""
    manager = EnhancedNotificationManager()
    
    print("Testing enhanced role-based notification system...")
    results = await manager.test_role_based_notifications()
    
    print("\n=== Test Results ===")
    print(f"Product Managers: {len(results['product_managers'])} users")
    print(f"Business Analysts: {len(results['business_analysts'])} users")
    print(f"Total notifications sent: {results['summary']['total_notifications_sent']}")
    print(f"Total notifications failed: {results['summary']['total_notifications_failed']}")
    print(f"Roles notified: {', '.join(results['summary']['roles_notified'])}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 