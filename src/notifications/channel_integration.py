"""
Notification Channel Integration Module

This module provides enhanced integration with existing notification channels
(email, Slack, Teams) for the AI-powered compliance monitoring system.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import aiohttp
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..database.models import Notification, User, UserNotificationPreference
from .notifier import EmailNotifier, SlackNotifier, TeamsNotifier
from .email_templates import EnhancedEmailTemplates
from ..utils.config_loader import get_notification_settings

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Supported notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    channel: str
    success: bool
    recipient: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    sent_at: Optional[datetime] = None


class ChannelIntegrationManager:
    """Manages integration with multiple notification channels."""
    
    def __init__(self):
        self.config = get_notification_settings()
        self.notifiers = self._initialize_notifiers()
        self.email_templates = EnhancedEmailTemplates()
        self.retry_config = {
            'max_retries': 3,
            'retry_delay': 5,  # seconds
            'backoff_multiplier': 2
        }
    
    def _initialize_notifiers(self) -> Dict[str, Any]:
        """Initialize notification services based on configuration."""
        notifiers = {}
        
        # Email notifier
        email_config = self.config.get('email', {})
        if email_config.get('enabled', False):
            notifiers['email'] = EmailNotifier(email_config)
            logger.info("Email notifier initialized")
        
        # Slack notifier
        slack_config = self.config.get('slack', {})
        if slack_config.get('enabled', False) and slack_config.get('webhook_url'):
            notifiers['slack'] = SlackNotifier(slack_config['webhook_url'])
            logger.info("Slack notifier initialized")
        
        # Teams notifier
        teams_config = self.config.get('teams', {})
        if teams_config.get('enabled', False) and teams_config.get('webhook_url'):
            notifiers['teams'] = TeamsNotifier(teams_config['webhook_url'])
            logger.info("Teams notifier initialized")
        
        return notifiers
    
    async def send_multi_channel_notification(
        self, 
        change_data: Dict[str, Any], 
        user_preferences: List[Dict[str, Any]],
        user: User
    ) -> List[NotificationResult]:
        """
        Send notifications through multiple channels based on user preferences.
        
        Args:
            change_data: Form change data to include in notification
            user_preferences: User's notification preferences
            user: User object
            
        Returns:
            List of notification results
        """
        results = []
        
        for pref in user_preferences:
            if not pref.get('is_enabled', False):
                continue
            
            channel = pref.get('notification_type')
            if channel not in self.notifiers:
                logger.warning(f"Channel {channel} not available for user {user.username}")
                continue
            
            # Check if notification should be sent based on severity and frequency
            if not self._should_send_notification(pref, change_data):
                continue
            
            # Send notification with retry logic
            result = await self._send_notification_with_retry(
                channel, change_data, user, pref
            )
            results.append(result)
            
            # Record notification in database
            await self._record_notification(result, user, change_data)
        
        return results
    
    def _should_send_notification(
        self, 
        preference: Dict[str, Any], 
        change_data: Dict[str, Any]
    ) -> bool:
        """Determine if notification should be sent based on preferences and change data."""
        # Check severity filter
        pref_severity = preference.get('change_severity', 'all')
        change_severity = change_data.get('severity', 'medium')
        
        if pref_severity != 'all':
            severity_levels = ['low', 'medium', 'high', 'critical']
            pref_level = severity_levels.index(pref_severity)
            change_level = severity_levels.index(change_severity)
            
            if change_level < pref_level:
                return False
        
        # Check business hours filter
        if preference.get('business_hours_only', False):
            now = datetime.now()
            if now.weekday() >= 5:  # Weekend
                return False
            if now.hour < 9 or now.hour > 17:  # Outside business hours
                return False
        
        return True
    
    async def _send_notification_with_retry(
        self, 
        channel: str, 
        change_data: Dict[str, Any], 
        user: User, 
        preference: Dict[str, Any]
    ) -> NotificationResult:
        """Send notification with retry logic."""
        max_retries = self.retry_config['max_retries']
        retry_delay = self.retry_config['retry_delay']
        
        for attempt in range(max_retries + 1):
            try:
                if channel == 'email':
                    success = await self._send_email_notification(change_data, user, preference)
                elif channel == 'slack':
                    success = await self._send_slack_notification(change_data, user, preference)
                elif channel == 'teams':
                    success = await self._send_teams_notification(change_data, user, preference)
                else:
                    success = False
                
                if success:
                    return NotificationResult(
                        channel=channel,
                        success=True,
                        recipient=user.email,
                        sent_at=datetime.now(),
                        retry_count=attempt
                    )
                
            except Exception as e:
                logger.error(f"Notification attempt {attempt + 1} failed for {channel}: {e}")
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (self.retry_config['backoff_multiplier'] ** attempt))
                else:
                    return NotificationResult(
                        channel=channel,
                        success=False,
                        recipient=user.email,
                        error_message=str(e),
                        retry_count=attempt,
                        sent_at=datetime.now()
                    )
        
        return NotificationResult(
            channel=channel,
            success=False,
            recipient=user.email,
            error_message="Max retries exceeded",
            retry_count=max_retries,
            sent_at=datetime.now()
        )
    
    async def _send_email_notification(
        self, 
        change_data: Dict[str, Any], 
        user: User, 
        preference: Dict[str, Any]
    ) -> bool:
        """Send email notification with enhanced template."""
        try:
            # Get appropriate template based on user role
            template_type = preference.get('template_type', 'product_manager')
            template = self.email_templates.get_template(template_type)
            
            # Prepare email data
            email_data = change_data.copy()
            email_data['user_name'] = f"{user.first_name} {user.last_name}"
            email_data['user_role'] = preference.get('role', 'user')
            
            # Generate HTML content
            html_content = template.render(**email_data)
            
            # Send email
            notifier = self.notifiers['email']
            notifier.to_addresses = [user.email]
            
            return await notifier.send_notification(email_data)
            
        except Exception as e:
            logger.error(f"Email notification failed for {user.email}: {e}")
            return False
    
    async def _send_slack_notification(
        self, 
        change_data: Dict[str, Any], 
        user: User, 
        preference: Dict[str, Any]
    ) -> bool:
        """Send Slack notification with user-specific formatting."""
        try:
            # Prepare Slack data
            slack_data = change_data.copy()
            slack_data['user_mention'] = f"<@{user.username}>" if hasattr(user, 'slack_id') else user.first_name
            
            # Send via Slack notifier
            notifier = self.notifiers['slack']
            return await notifier.send_notification(slack_data)
            
        except Exception as e:
            logger.error(f"Slack notification failed for {user.username}: {e}")
            return False
    
    async def _send_teams_notification(
        self, 
        change_data: Dict[str, Any], 
        user: User, 
        preference: Dict[str, Any]
    ) -> bool:
        """Send Teams notification with user-specific formatting."""
        try:
            # Prepare Teams data
            teams_data = change_data.copy()
            teams_data['user_name'] = f"{user.first_name} {user.last_name}"
            
            # Send via Teams notifier
            notifier = self.notifiers['teams']
            return await notifier.send_notification(teams_data)
            
        except Exception as e:
            logger.error(f"Teams notification failed for {user.username}: {e}")
            return False
    
    async def _record_notification(
        self, 
        result: NotificationResult, 
        user: User, 
        change_data: Dict[str, Any]
    ):
        """Record notification result in database."""
        try:
            with get_db() as db:
                notification = Notification(
                    form_change_id=change_data.get('form_change_id'),
                    notification_type=result.channel,
                    recipient=result.recipient,
                    subject=f"Payroll Form Change: {change_data.get('agency_name')} - {change_data.get('form_name')}",
                    message=json.dumps(change_data),
                    status="sent" if result.success else "failed",
                    sent_at=result.sent_at,
                    error_message=result.error_message,
                    retry_count=result.retry_count
                )
                db.add(notification)
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to record notification: {e}")
    
    async def test_channel_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all configured notification channels."""
        results = {}
        
        for channel, notifier in self.notifiers.items():
            try:
                if channel == 'email':
                    # Test email connectivity
                    test_data = {
                        'agency_name': 'Test Agency',
                        'form_name': 'TEST-001',
                        'severity': 'medium',
                        'change_description': 'Test notification'
                    }
                    success = await notifier.send_notification(test_data)
                    results[channel] = success
                    
                elif channel in ['slack', 'teams']:
                    # Test webhook connectivity
                    test_data = {
                        'agency_name': 'Test Agency',
                        'form_name': 'TEST-001',
                        'severity': 'medium',
                        'change_description': 'Test notification',
                        'detected_at': datetime.now().isoformat(),
                        'clients_impacted': 0,
                        'icp_percentage': 0
                    }
                    success = await notifier.send_notification(test_data)
                    results[channel] = success
                    
            except Exception as e:
                logger.error(f"Channel connectivity test failed for {channel}: {e}")
                results[channel] = False
        
        return results
    
    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all notification channels."""
        status = {}
        
        for channel in ['email', 'slack', 'teams']:
            config = self.config.get(channel, {})
            status[channel] = {
                'enabled': config.get('enabled', False),
                'configured': bool(config.get('webhook_url') if channel in ['slack', 'teams'] else config.get('smtp_server')),
                'available': channel in self.notifiers
            }
        
        return status


class NotificationBatching:
    """Handles batching of notifications to prevent spam."""
    
    def __init__(self, batch_size: int = 5, batch_window: int = 300):
        self.batch_size = batch_size
        self.batch_window = batch_window  # seconds
        self.pending_notifications = {}
    
    def should_batch_notification(self, user_id: int, channel: str) -> bool:
        """Determine if notification should be batched."""
        key = f"{user_id}_{channel}"
        now = datetime.now()
        
        if key not in self.pending_notifications:
            self.pending_notifications[key] = []
        
        # Remove old notifications
        self.pending_notifications[key] = [
            n for n in self.pending_notifications[key]
            if (now - n['timestamp']).seconds < self.batch_window
        ]
        
        # Add new notification
        self.pending_notifications[key].append({
            'timestamp': now,
            'data': {}
        })
        
        return len(self.pending_notifications[key]) < self.batch_size
    
    def get_batched_notifications(self, user_id: int, channel: str) -> List[Dict]:
        """Get batched notifications for a user and channel."""
        key = f"{user_id}_{channel}"
        return self.pending_notifications.get(key, [])
    
    def clear_batch(self, user_id: int, channel: str):
        """Clear batched notifications for a user and channel."""
        key = f"{user_id}_{channel}"
        if key in self.pending_notifications:
            del self.pending_notifications[key]


# Global instances
channel_manager = ChannelIntegrationManager()
notification_batching = NotificationBatching() 