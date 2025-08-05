"""
Enhanced Notification Preference Manager

This module provides comprehensive notification preference management with
granular frequency settings and role-specific preferences for different user roles.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database.connection import get_db_session
from ..database.models import (
    User, Role, UserRole, UserNotificationPreference,
    FormChange, Agency, Form
)
from ..auth.user_service import UserService

logger = logging.getLogger(__name__)


class NotificationFrequency:
    """Constants for notification frequencies."""
    IMMEDIATE = "immediate"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    BUSINESS_HOURS = "business_hours"
    CUSTOM = "custom"
    
    @staticmethod
    def get_all_frequencies() -> List[str]:
        """Get all available notification frequencies."""
        return [
            NotificationFrequency.IMMEDIATE,
            NotificationFrequency.HOURLY,
            NotificationFrequency.DAILY,
            NotificationFrequency.WEEKLY,
            NotificationFrequency.BUSINESS_HOURS,
            NotificationFrequency.CUSTOM
        ]
    
    @staticmethod
    def get_frequency_display_name(frequency: str) -> str:
        """Get display name for frequency."""
        display_names = {
            NotificationFrequency.IMMEDIATE: "Immediate",
            NotificationFrequency.HOURLY: "Hourly",
            NotificationFrequency.DAILY: "Daily",
            NotificationFrequency.WEEKLY: "Weekly",
            NotificationFrequency.BUSINESS_HOURS: "Business Hours Only",
            NotificationFrequency.CUSTOM: "Custom Schedule"
        }
        return display_names.get(frequency, frequency.title())


class NotificationSeverity:
    """Constants for notification severities."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ALL = "all"
    
    @staticmethod
    def get_all_severities() -> List[str]:
        """Get all available notification severities."""
        return [
            NotificationSeverity.CRITICAL,
            NotificationSeverity.HIGH,
            NotificationSeverity.MEDIUM,
            NotificationSeverity.LOW,
            NotificationSeverity.ALL
        ]
    
    @staticmethod
    def get_severity_display_name(severity: str) -> str:
        """Get display name for severity."""
        display_names = {
            NotificationSeverity.CRITICAL: "Critical",
            NotificationSeverity.HIGH: "High",
            NotificationSeverity.MEDIUM: "Medium",
            NotificationSeverity.LOW: "Low",
            NotificationSeverity.ALL: "All Severities"
        }
        return display_names.get(severity, severity.title())


class NotificationChannel:
    """Constants for notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    TEAMS = "teams"
    WEBHOOK = "webhook"
    SMS = "sms"
    PUSH = "push"
    
    @staticmethod
    def get_all_channels() -> List[str]:
        """Get all available notification channels."""
        return [
            NotificationChannel.EMAIL,
            NotificationChannel.SLACK,
            NotificationChannel.TEAMS,
            NotificationChannel.WEBHOOK,
            NotificationChannel.SMS,
            NotificationChannel.PUSH
        ]
    
    @staticmethod
    def get_channel_display_name(channel: str) -> str:
        """Get display name for channel."""
        display_names = {
            NotificationChannel.EMAIL: "Email",
            NotificationChannel.SLACK: "Slack",
            NotificationChannel.TEAMS: "Microsoft Teams",
            NotificationChannel.WEBHOOK: "Webhook",
            NotificationChannel.SMS: "SMS",
            NotificationChannel.PUSH: "Push Notification"
        }
        return display_names.get(channel, channel.title())


class RoleBasedDefaults:
    """Default notification preferences for different roles."""
    
    @staticmethod
    def get_product_manager_defaults() -> List[Dict[str, Any]]:
        """Get default notification preferences for Product Managers."""
        return [
            {
                "notification_type": NotificationChannel.EMAIL,
                "change_severity": NotificationSeverity.ALL,
                "frequency": NotificationFrequency.IMMEDIATE,
                "is_enabled": True,
                "business_hours_only": False,
                "custom_schedule": None,
                "batch_notifications": False,
                "batch_size": 1,
                "batch_window_minutes": 0
            },
            {
                "notification_type": NotificationChannel.SLACK,
                "change_severity": NotificationSeverity.HIGH,
                "frequency": NotificationFrequency.IMMEDIATE,
                "is_enabled": True,
                "business_hours_only": True,
                "custom_schedule": None,
                "batch_notifications": False,
                "batch_size": 1,
                "batch_window_minutes": 0
            }
        ]
    
    @staticmethod
    def get_business_analyst_defaults() -> List[Dict[str, Any]]:
        """Get default notification preferences for Business Analysts."""
        return [
            {
                "notification_type": NotificationChannel.EMAIL,
                "change_severity": NotificationSeverity.ALL,
                "frequency": NotificationFrequency.DAILY,
                "is_enabled": True,
                "business_hours_only": True,
                "custom_schedule": None,
                "batch_notifications": True,
                "batch_size": 10,
                "batch_window_minutes": 60
            },
            {
                "notification_type": NotificationChannel.SLACK,
                "change_severity": NotificationSeverity.MEDIUM,
                "frequency": NotificationFrequency.HOURLY,
                "is_enabled": True,
                "business_hours_only": True,
                "custom_schedule": None,
                "batch_notifications": True,
                "batch_size": 5,
                "batch_window_minutes": 30
            },
            {
                "notification_type": NotificationChannel.TEAMS,
                "change_severity": NotificationSeverity.CRITICAL,
                "frequency": NotificationFrequency.IMMEDIATE,
                "is_enabled": True,
                "business_hours_only": False,
                "custom_schedule": None,
                "batch_notifications": False,
                "batch_size": 1,
                "batch_window_minutes": 0
            }
        ]
    
    @staticmethod
    def get_admin_defaults() -> List[Dict[str, Any]]:
        """Get default notification preferences for Administrators."""
        return [
            {
                "notification_type": NotificationChannel.EMAIL,
                "change_severity": NotificationSeverity.ALL,
                "frequency": NotificationFrequency.IMMEDIATE,
                "is_enabled": True,
                "business_hours_only": False,
                "custom_schedule": None,
                "batch_notifications": False,
                "batch_size": 1,
                "batch_window_minutes": 0
            }
        ]


class EnhancedNotificationPreferenceManager:
    """Enhanced notification preference management with role-based defaults and granular settings."""
    
    def __init__(self):
        self.user_service = UserService()
    
    def initialize_user_preferences(self, user_id: int, role_names: List[str] = None) -> bool:
        """Initialize notification preferences for a user based on their roles."""
        try:
            with get_db_session() as session:
                # Get user's roles if not provided
                if not role_names:
                    user_roles = session.query(UserRole).join(Role).filter(
                        and_(
                            UserRole.user_id == user_id,
                            UserRole.is_active == True,
                            Role.is_active == True
                        )
                    ).all()
                    role_names = [user_role.role.name for user_role in user_roles]
                
                # Get default preferences for each role
                all_defaults = []
                for role_name in role_names:
                    if role_name == 'product_manager':
                        all_defaults.extend(RoleBasedDefaults.get_product_manager_defaults())
                    elif role_name == 'business_analyst':
                        all_defaults.extend(RoleBasedDefaults.get_business_analyst_defaults())
                    elif role_name == 'admin':
                        all_defaults.extend(RoleBasedDefaults.get_admin_defaults())
                
                # Remove duplicates based on notification_type
                seen_types = set()
                unique_defaults = []
                for default in all_defaults:
                    if default['notification_type'] not in seen_types:
                        seen_types.add(default['notification_type'])
                        unique_defaults.append(default)
                
                # Create preferences
                for default in unique_defaults:
                    existing_pref = session.query(UserNotificationPreference).filter(
                        and_(
                            UserNotificationPreference.user_id == user_id,
                            UserNotificationPreference.notification_type == default['notification_type']
                        )
                    ).first()
                    
                    if not existing_pref:
                        new_pref = UserNotificationPreference(
                            user_id=user_id,
                            notification_type=default['notification_type'],
                            change_severity=default['change_severity'],
                            frequency=default['frequency'],
                            is_enabled=default['is_enabled']
                        )
                        session.add(new_pref)
                
                session.commit()
                logger.info(f"Initialized notification preferences for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error initializing notification preferences for user {user_id}: {e}")
            return False
    
    def update_user_notification_preference(self, user_id: int, notification_type: str,
                                          change_severity: str = None, frequency: str = "daily",
                                          is_enabled: bool = True, business_hours_only: bool = False,
                                          custom_schedule: Dict[str, Any] = None,
                                          batch_notifications: bool = False,
                                          batch_size: int = 1,
                                          batch_window_minutes: int = 0) -> bool:
        """Update a user's notification preference with enhanced settings."""
        try:
            with get_db_session() as session:
                existing_pref = session.query(UserNotificationPreference).filter(
                    and_(
                        UserNotificationPreference.user_id == user_id,
                        UserNotificationPreference.notification_type == notification_type
                    )
                ).first()
                
                if existing_pref:
                    existing_pref.change_severity = change_severity
                    existing_pref.frequency = frequency
                    existing_pref.is_enabled = is_enabled
                    existing_pref.updated_at = datetime.utcnow()
                else:
                    new_pref = UserNotificationPreference(
                        user_id=user_id,
                        notification_type=notification_type,
                        change_severity=change_severity,
                        frequency=frequency,
                        is_enabled=is_enabled
                    )
                    session.add(new_pref)
                
                session.commit()
                logger.info(f"Updated notification preference for user {user_id}, type {notification_type}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating notification preference for user {user_id}: {e}")
            return False
    
    def get_user_notification_preferences(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all notification preferences for a user with enhanced information."""
        try:
            with get_db_session() as session:
                prefs = session.query(UserNotificationPreference).filter(
                    UserNotificationPreference.user_id == user_id
                ).all()
                
                return [
                    {
                        "id": pref.id,
                        "notification_type": pref.notification_type,
                        "notification_type_display": NotificationChannel.get_channel_display_name(pref.notification_type),
                        "change_severity": pref.change_severity,
                        "change_severity_display": NotificationSeverity.get_severity_display_name(pref.change_severity),
                        "frequency": pref.frequency,
                        "frequency_display": NotificationFrequency.get_frequency_display_name(pref.frequency),
                        "is_enabled": pref.is_enabled,
                        "created_at": pref.created_at,
                        "updated_at": pref.updated_at
                    }
                    for pref in prefs
                ]
                
        except Exception as e:
            logger.error(f"Error getting notification preferences for user {user_id}: {e}")
            return []
    
    def get_user_preferences_summary(self, user_id: int) -> Dict[str, Any]:
        """Get a summary of user's notification preferences."""
        try:
            preferences = self.get_user_notification_preferences(user_id)
            
            summary = {
                "total_preferences": len(preferences),
                "enabled_preferences": len([p for p in preferences if p['is_enabled']]),
                "channels": {},
                "severities": {},
                "frequencies": {}
            }
            
            for pref in preferences:
                # Channel summary
                channel = pref['notification_type']
                if channel not in summary['channels']:
                    summary['channels'][channel] = {
                        'count': 0,
                        'enabled': 0,
                        'display_name': pref['notification_type_display']
                    }
                summary['channels'][channel]['count'] += 1
                if pref['is_enabled']:
                    summary['channels'][channel]['enabled'] += 1
                
                # Severity summary
                severity = pref['change_severity']
                if severity not in summary['severities']:
                    summary['severities'][severity] = {
                        'count': 0,
                        'display_name': pref['change_severity_display']
                    }
                summary['severities'][severity]['count'] += 1
                
                # Frequency summary
                frequency = pref['frequency']
                if frequency not in summary['frequencies']:
                    summary['frequencies'][frequency] = {
                        'count': 0,
                        'display_name': pref['frequency_display']
                    }
                summary['frequencies'][frequency]['count'] += 1
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting preferences summary for user {user_id}: {e}")
            return {}
    
    def should_send_notification(self, user_id: int, notification_type: str, 
                               change_severity: str, change_time: datetime = None) -> bool:
        """Determine if a notification should be sent based on user preferences."""
        try:
            with get_db_session() as session:
                pref = session.query(UserNotificationPreference).filter(
                    and_(
                        UserNotificationPreference.user_id == user_id,
                        UserNotificationPreference.notification_type == notification_type,
                        UserNotificationPreference.is_enabled == True
                    )
                ).first()
                
                if not pref:
                    return False
                
                # Check severity
                if pref.change_severity != NotificationSeverity.ALL and pref.change_severity != change_severity:
                    return False
                
                # Check frequency and timing
                if change_time:
                    return self._check_frequency_timing(pref.frequency, change_time)
                
                return True
                
        except Exception as e:
            logger.error(f"Error checking notification preference for user {user_id}: {e}")
            return False
    
    def _check_frequency_timing(self, frequency: str, change_time: datetime) -> bool:
        """Check if notification timing matches frequency requirements."""
        now = datetime.utcnow()
        
        if frequency == NotificationFrequency.IMMEDIATE:
            return True
        
        elif frequency == NotificationFrequency.HOURLY:
            # Check if we're in a new hour since the change
            return (now - change_time).total_seconds() >= 3600
        
        elif frequency == NotificationFrequency.DAILY:
            # Check if we're in a new day since the change
            return (now.date() - change_time.date()).days >= 1
        
        elif frequency == NotificationFrequency.WEEKLY:
            # Check if we're in a new week since the change
            return (now.date() - change_time.date()).days >= 7
        
        elif frequency == NotificationFrequency.BUSINESS_HOURS:
            # Check if we're in business hours (9 AM - 5 PM, Monday-Friday)
            if now.weekday() >= 5:  # Weekend
                return False
            if now.hour < 9 or now.hour >= 17:  # Outside business hours
                return False
            return True
        
        return True
    
    def get_users_for_notification(self, notification_type: str, change_severity: str = None,
                                 change_time: datetime = None) -> List[User]:
        """Get users who should receive a specific type of notification."""
        try:
            with get_db_session() as session:
                # Get all users with this notification type enabled
                query = session.query(User).join(UserNotificationPreference).filter(
                    and_(
                        UserNotificationPreference.notification_type == notification_type,
                        UserNotificationPreference.is_enabled == True,
                        User.is_active == True
                    )
                )
                
                if change_severity:
                    query = query.filter(
                        or_(
                            UserNotificationPreference.change_severity == change_severity,
                            UserNotificationPreference.change_severity == NotificationSeverity.ALL
                        )
                    )
                
                users = query.all()
                
                # Filter by frequency timing if change_time is provided
                if change_time:
                    filtered_users = []
                    for user in users:
                        if self.should_send_notification(user.id, notification_type, change_severity, change_time):
                            filtered_users.append(user)
                    return filtered_users
                
                return users
                
        except Exception as e:
            logger.error(f"Error getting users for notification: {e}")
            return []
    
    def get_role_based_preferences(self, role_name: str) -> List[Dict[str, Any]]:
        """Get default notification preferences for a specific role."""
        if role_name == 'product_manager':
            return RoleBasedDefaults.get_product_manager_defaults()
        elif role_name == 'business_analyst':
            return RoleBasedDefaults.get_business_analyst_defaults()
        elif role_name == 'admin':
            return RoleBasedDefaults.get_admin_defaults()
        else:
            return []
    
    def get_available_options(self) -> Dict[str, List[Dict[str, str]]]:
        """Get all available options for notification preferences."""
        return {
            "frequencies": [
                {"value": freq, "display": NotificationFrequency.get_frequency_display_name(freq)}
                for freq in NotificationFrequency.get_all_frequencies()
            ],
            "severities": [
                {"value": sev, "display": NotificationSeverity.get_severity_display_name(sev)}
                for sev in NotificationSeverity.get_all_severities()
            ],
            "channels": [
                {"value": chan, "display": NotificationChannel.get_channel_display_name(chan)}
                for chan in NotificationChannel.get_all_channels()
            ]
        }
    
    def bulk_update_user_preferences(self, user_id: int, preferences: List[Dict[str, Any]]) -> bool:
        """Bulk update multiple notification preferences for a user."""
        try:
            with get_db_session() as session:
                for pref_data in preferences:
                    existing_pref = session.query(UserNotificationPreference).filter(
                        and_(
                            UserNotificationPreference.user_id == user_id,
                            UserNotificationPreference.notification_type == pref_data['notification_type']
                        )
                    ).first()
                    
                    if existing_pref:
                        existing_pref.change_severity = pref_data.get('change_severity')
                        existing_pref.frequency = pref_data.get('frequency', 'daily')
                        existing_pref.is_enabled = pref_data.get('is_enabled', True)
                        existing_pref.updated_at = datetime.utcnow()
                    else:
                        new_pref = UserNotificationPreference(
                            user_id=user_id,
                            notification_type=pref_data['notification_type'],
                            change_severity=pref_data.get('change_severity'),
                            frequency=pref_data.get('frequency', 'daily'),
                            is_enabled=pref_data.get('is_enabled', True)
                        )
                        session.add(new_pref)
                
                session.commit()
                logger.info(f"Bulk updated notification preferences for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error bulk updating notification preferences for user {user_id}: {e}")
            return False
    
    def reset_user_preferences_to_defaults(self, user_id: int) -> bool:
        """Reset user's notification preferences to role-based defaults."""
        try:
            # Get user's roles
            with get_db_session() as session:
                user_roles = session.query(UserRole).join(Role).filter(
                    and_(
                        UserRole.user_id == user_id,
                        UserRole.is_active == True,
                        Role.is_active == True
                    )
                ).all()
                
                role_names = [user_role.role.name for user_role in user_roles]
            
            # Delete existing preferences
            with get_db_session() as session:
                session.query(UserNotificationPreference).filter(
                    UserNotificationPreference.user_id == user_id
                ).delete()
                session.commit()
            
            # Initialize with defaults
            return self.initialize_user_preferences(user_id, role_names)
            
        except Exception as e:
            logger.error(f"Error resetting notification preferences for user {user_id}: {e}")
            return False
    
    def get_notification_statistics(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """Get notification statistics for a user."""
        try:
            with get_db_session() as session:
                from ..database.models import Notification
                
                # Get notifications sent to this user in the last N days
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                notifications = session.query(Notification).filter(
                    and_(
                        Notification.recipient.like(f"%{user_id}%"),  # Assuming recipient contains user info
                        Notification.sent_at >= cutoff_date
                    )
                ).all()
                
                stats = {
                    "total_notifications": len(notifications),
                    "successful_notifications": len([n for n in notifications if n.status == "sent"]),
                    "failed_notifications": len([n for n in notifications if n.status == "failed"]),
                    "by_channel": {},
                    "by_severity": {},
                    "by_day": {}
                }
                
                for notification in notifications:
                    # By channel
                    channel = notification.notification_type
                    if channel not in stats["by_channel"]:
                        stats["by_channel"][channel] = {"total": 0, "success": 0, "failed": 0}
                    stats["by_channel"][channel]["total"] += 1
                    if notification.status == "sent":
                        stats["by_channel"][channel]["success"] += 1
                    else:
                        stats["by_channel"][channel]["failed"] += 1
                    
                    # By day
                    day = notification.sent_at.date().isoformat()
                    if day not in stats["by_day"]:
                        stats["by_day"][day] = 0
                    stats["by_day"][day] += 1
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting notification statistics for user {user_id}: {e}")
            return {}


# Convenience functions for easy access
def get_preference_manager() -> EnhancedNotificationPreferenceManager:
    """Get a preference manager instance."""
    return EnhancedNotificationPreferenceManager()


def initialize_user_preferences(user_id: int, role_names: List[str] = None) -> bool:
    """Initialize notification preferences for a user."""
    manager = get_preference_manager()
    return manager.initialize_user_preferences(user_id, role_names)


def update_user_preference(user_id: int, notification_type: str, **kwargs) -> bool:
    """Update a user's notification preference."""
    manager = get_preference_manager()
    return manager.update_user_notification_preference(user_id, notification_type, **kwargs)


def get_user_preferences(user_id: int) -> List[Dict[str, Any]]:
    """Get all notification preferences for a user."""
    manager = get_preference_manager()
    return manager.get_user_notification_preferences(user_id)


def should_send_notification(user_id: int, notification_type: str, 
                           change_severity: str, change_time: datetime = None) -> bool:
    """Determine if a notification should be sent."""
    manager = get_preference_manager()
    return manager.should_send_notification(user_id, notification_type, change_severity, change_time) 