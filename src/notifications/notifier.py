import asyncio
import json
import logging
import smtplib
from datetime import datetime
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional
from jinja2 import Template

import aiohttp
import requests

from ..database.connection import get_db
from ..database.models import FormChange, Notification, Agency, Form, Client, ClientFormUsage
from ..utils.config_loader import get_notification_settings

logger = logging.getLogger(__name__)


class NotificationTemplate:
    """Template generator for notifications."""
    
    def __init__(self):
        self.email_template = Template("""
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f4f4f4; padding: 20px; border-radius: 5px; }
        .content { margin: 20px 0; }
        .change-details { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .impact-section { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .action-items { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }
        .footer { margin-top: 30px; font-size: 12px; color: #666; }
        .urgent { border-left: 4px solid #dc3545; }
        .medium { border-left: 4px solid #ffc107; }
        .low { border-left: 4px solid #28a745; }
    </style>
</head>
<body>
    <div class="header">
        <h2>🚨 Certified Payroll Report Change Alert</h2>
        <p><strong>Detection Time:</strong> {{ detected_at }}</p>
        <p><strong>Severity:</strong> {{ severity.upper() }}</p>
    </div>
    
    <div class="content">
        <div class="change-details {{ severity }}">
            <h3>Change Details</h3>
            <p><strong>Agency:</strong> {{ agency_name }}</p>
            <p><strong>Report Name/ID:</strong> {{ form_name }}</p>
            <p><strong>CPR Report ID:</strong> {{ cpr_report_id or "N/A" }}</p>
            <p><strong>Change Type:</strong> {{ change_type }}</p>
            <p><strong>Description:</strong> {{ change_description }}</p>
            {% if effective_date %}
            <p><strong>Effective Date:</strong> {{ effective_date }}</p>
            {% endif %}
        </div>
        
        <div class="impact-section">
            <h3>📊 Impact Assessment</h3>
            <p><strong>Clients Impacted:</strong> {{ clients_impacted }}</p>
            <p><strong>ICP Segment Percentage:</strong> {{ icp_percentage }}%</p>
            {% if impact_details %}
            <ul>
                {% for detail in impact_details %}
                <li>{{ detail }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
        
        <div class="action-items">
            <h3>📋 Required Resources & Next Steps</h3>
            <h4>Resources:</h4>
            <ul>
                {% if form_url %}<li><a href="{{ form_url }}">Report Specifications</a></li>{% endif %}
                {% if instructions_url %}<li><a href="{{ instructions_url }}">Report Instructions</a></li>{% endif %}
                <li><strong>Agency Contact:</strong> {{ agency_contact_email }} | {{ agency_contact_phone }}</li>
                {% if field_mapping_current %}<li>Report field mapping (current): Available in CPR</li>{% endif %}
                {% if field_mapping_updated %}<li>Report field mapping (updated): Available in CPR</li>{% endif %}
            </ul>
            
            <h4>Development Process:</h4>
            <ol>
                <li><strong>Evaluation:</strong> Assess effort, risk, and impact</li>
                <li><strong>Development:</strong> Following strict guidelines for report updates</li>
                <li><strong>QA:</strong> Comprehensive testing of changes</li>
                <li><strong>EUT:</strong> End-user testing and final review</li>
                <li><strong>Production:</strong> Release and stakeholder notification</li>
                <li><strong>Monitoring:</strong> 3-month feedback collection period</li>
            </ol>
        </div>
    </div>
    
    <div class="footer">
        <p>This alert was generated automatically by the Payroll Monitoring System.</p>
        <p>For questions or support, please contact your development team.</p>
    </div>
</body>
</html>
        """)
        
        self.slack_template = Template("""
🚨 *Certified Payroll Report Change Alert*

*Agency:* {{ agency_name }}
*Report:* {{ form_name }} ({{ cpr_report_id or "No CPR ID" }})
*Severity:* {{ severity.upper() }}
*Change:* {{ change_description }}

📊 *Impact:*
• Clients affected: {{ clients_impacted }}
• ICP segment: {{ icp_percentage }}%

🔗 *Resources:*
{% if form_url %}• <{{ form_url }}|Report Specifications>{% endif %}
{% if instructions_url %}• <{{ instructions_url }}|Instructions>{% endif %}
• Contact: {{ agency_contact_email }}

⏰ *Detected:* {{ detected_at }}
{% if effective_date %}⚡ *Effective:* {{ effective_date }}{% endif %}
        """)


class EmailNotifier:
    """Email notification service."""
    
    def __init__(self, smtp_config: Dict):
        self.smtp_server = smtp_config.get('smtp_server')
        self.smtp_port = smtp_config.get('smtp_port', 587)
        self.username = smtp_config.get('username')
        self.password = smtp_config.get('password')
        self.from_address = smtp_config.get('from_address')
        self.to_addresses = smtp_config.get('to_addresses', [])
        
    async def send_notification(self, change_data: Dict) -> bool:
        """Send email notification."""
        try:
            template = NotificationTemplate()
            
            # Generate email content
            html_content = template.email_template.render(**change_data)
            
            # Create message
            msg = MimeMultipart('alternative')
            msg['Subject'] = f"🚨 Payroll Form Change: {change_data['agency_name']} - {change_data['form_name']}"
            msg['From'] = self.from_address
            msg['To'] = ', '.join(self.to_addresses)
            
            # Add HTML content
            html_part = MimeText(html_content, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent for {change_data['form_name']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class SlackNotifier:
    """Slack notification service."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    async def send_notification(self, change_data: Dict) -> bool:
        """Send Slack notification."""
        try:
            template = NotificationTemplate()
            
            # Generate Slack message
            text_content = template.slack_template.render(**change_data)
            
            payload = {
                "text": text_content,
                "username": "Payroll Monitor",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": self._get_color_for_severity(change_data['severity']),
                        "fields": [
                            {
                                "title": "Agency",
                                "value": change_data['agency_name'],
                                "short": True
                            },
                            {
                                "title": "Form",
                                "value": change_data['form_name'],
                                "short": True
                            },
                            {
                                "title": "Clients Impacted",
                                "value": str(change_data['clients_impacted']),
                                "short": True
                            },
                            {
                                "title": "ICP Percentage",
                                "value": f"{change_data['icp_percentage']}%",
                                "short": True
                            }
                        ],
                        "footer": "Payroll Monitoring System",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Slack notification sent for {change_data['form_name']}")
                        return True
                    else:
                        logger.error(f"Slack notification failed: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False
    
    def _get_color_for_severity(self, severity: str) -> str:
        """Get color code for severity level."""
        colors = {
            'low': 'good',
            'medium': 'warning', 
            'high': 'danger',
            'critical': 'danger'
        }
        return colors.get(severity.lower(), 'warning')


class TeamsNotifier:
    """Microsoft Teams notification service."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    async def send_notification(self, change_data: Dict) -> bool:
        """Send Teams notification."""
        try:
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": self._get_color_for_severity(change_data['severity']),
                "summary": f"Payroll Form Change: {change_data['form_name']}",
                "sections": [
                    {
                        "activityTitle": "🚨 Certified Payroll Report Change Alert",
                        "activitySubtitle": f"Detected at {change_data['detected_at']}",
                        "facts": [
                            {"name": "Agency", "value": change_data['agency_name']},
                            {"name": "Report", "value": change_data['form_name']},
                            {"name": "CPR Report ID", "value": change_data.get('cpr_report_id', 'N/A')},
                            {"name": "Severity", "value": change_data['severity'].upper()},
                            {"name": "Change", "value": change_data['change_description']},
                            {"name": "Clients Impacted", "value": str(change_data['clients_impacted'])},
                            {"name": "ICP Percentage", "value": f"{change_data['icp_percentage']}%"}
                        ],
                        "markdown": True
                    }
                ],
                "potentialActions": [
                    {
                        "@type": "OpenUri",
                        "name": "View Report",
                        "targets": [
                            {"os": "default", "uri": change_data.get('form_url', '#')}
                        ]
                    }
                ]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Teams notification sent for {change_data['form_name']}")
                        return True
                    else:
                        logger.error(f"Teams notification failed: HTTP {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Failed to send Teams notification: {e}")
            return False
    
    def _get_color_for_severity(self, severity: str) -> str:
        """Get color code for severity level."""
        colors = {
            'low': '00FF00',
            'medium': 'FFA500',
            'high': 'FF0000',
            'critical': '8B0000'
        }
        return colors.get(severity.lower(), 'FFA500')


class NotificationManager:
    """Main notification management class."""
    
    def __init__(self):
        self.notification_config = get_notification_settings()
        self.notifiers = self._setup_notifiers()
    
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
    
    async def send_change_notification(self, form_change_id: int) -> Dict[str, bool]:
        """
        Send notifications for a form change to all configured channels.
        
        Returns:
            Dictionary with notification results by channel
        """
        results = {}
        
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
            
            # Prepare notification data
            change_data = {
                'detected_at': form_change.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC'),
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
                'field_mapping_current': True,  # Assume available in CPR
                'field_mapping_updated': True   # Assume available in CPR
            }
            
            # Send notifications through all configured channels
            for channel, notifier in self.notifiers.items():
                try:
                    success = await notifier.send_notification(change_data)
                    results[channel] = success
                    
                    # Record notification in database
                    notification = Notification(
                        form_change_id=form_change_id,
                        notification_type=channel,
                        recipient=self._get_recipient_info(channel),
                        subject=f"Payroll Form Change: {agency.name} - {form.name}",
                        message=json.dumps(change_data),
                        status="sent" if success else "failed"
                    )
                    db.add(notification)
                    
                except Exception as e:
                    logger.error(f"Error sending {channel} notification: {e}")
                    results[channel] = False
            
            db.commit()
        
        return results
    
    async def _calculate_impact_assessment(self, form_id: int, db) -> Dict:
        """Calculate the impact assessment for a form change."""
        # Get clients using this form
        client_usage = db.query(ClientFormUsage).filter(
            ClientFormUsage.form_id == form_id,
            ClientFormUsage.is_active == True
        ).all()
        
        total_clients = len(client_usage)
        
        # Calculate ICP segment percentage
        # This is a simplified calculation - in practice, you'd have more complex logic
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
    
    def _get_recipient_info(self, channel: str) -> str:
        """Get recipient information for a notification channel."""
        if channel == 'email':
            return ', '.join(self.notification_config.get('email', {}).get('to_addresses', []))
        elif channel == 'slack':
            return self.notification_config.get('slack', {}).get('channel', '#payroll-alerts')
        elif channel == 'teams':
            return 'Teams Webhook'
        else:
            return 'Unknown'
    
    async def send_batch_notifications(self, form_change_ids: List[int]) -> Dict:
        """Send notifications for multiple form changes."""
        results = {}
        
        for change_id in form_change_ids:
            try:
                change_results = await self.send_change_notification(change_id)
                results[change_id] = change_results
            except Exception as e:
                logger.error(f"Error processing notification for change {change_id}: {e}")
                results[change_id] = {}
        
        return results
    
    async def test_notifications(self) -> Dict[str, bool]:
        """Test all configured notification channels."""
        test_data = {
            'detected_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'severity': 'low',
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'cpr_report_id': 'TEST-CPR-001',
            'change_type': 'test',
            'change_description': 'This is a test notification',
            'effective_date': None,
            'form_url': 'https://example.com/test-form',
            'instructions_url': 'https://example.com/test-instructions',
            'agency_contact_email': 'test@example.com',
            'agency_contact_phone': '(555) 123-4567',
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'impact_details': ['Test impact detail'],
            'field_mapping_current': True,
            'field_mapping_updated': True
        }
        
        results = {}
        for channel, notifier in self.notifiers.items():
            try:
                success = await notifier.send_notification(test_data)
                results[channel] = success
                logger.info(f"Test notification sent via {channel}: {'Success' if success else 'Failed'}")
            except Exception as e:
                logger.error(f"Test notification failed for {channel}: {e}")
                results[channel] = False
        
        return results


async def main():
    """Test the notification system."""
    manager = NotificationManager()
    
    print("Testing notification system...")
    results = await manager.test_notifications()
    
    for channel, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"{channel}: {status}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())