"""
Notification Batching and Throttling Manager

This module provides functionality to batch notifications and implement throttling
to prevent spam and improve notification efficiency.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..database.models import Notification, User, UserNotificationPreference
from ..database.connection import get_db
from .enhanced_notifier import EnhancedNotificationManager

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Status of notification batches."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ThrottleType(Enum):
    """Types of throttling rules."""
    RATE_LIMIT = "rate_limit"  # Max notifications per time period
    COOLDOWN = "cooldown"      # Minimum time between notifications
    BURST_LIMIT = "burst_limit"  # Max notifications in burst
    DAILY_LIMIT = "daily_limit"  # Max notifications per day


@dataclass
class BatchConfig:
    """Configuration for notification batching."""
    enabled: bool = True
    max_batch_size: int = 10
    max_batch_delay_minutes: int = 30
    priority_override: bool = False  # Send high priority immediately
    group_by_user: bool = True
    group_by_severity: bool = True
    group_by_channel: bool = True


@dataclass
class ThrottleConfig:
    """Configuration for notification throttling."""
    enabled: bool = True
    rate_limit_per_hour: int = 50
    rate_limit_per_day: int = 200
    cooldown_minutes: int = 5
    burst_limit: int = 10
    burst_window_minutes: int = 15
    daily_limit: int = 100
    exempt_high_priority: bool = True
    exempt_critical_severity: bool = True


@dataclass
class NotificationBatch:
    """Represents a batch of notifications."""
    id: str
    user_id: int
    channel: str
    severity: str
    notifications: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_for: Optional[datetime] = None
    status: BatchStatus = BatchStatus.PENDING
    priority_score: float = 0.0
    
    def add_notification(self, notification: Dict[str, Any]) -> None:
        """Add a notification to the batch."""
        self.notifications.append(notification)
        # Update priority score based on highest priority notification
        if notification.get('severity') == 'critical':
            self.priority_score = max(self.priority_score, 10.0)
        elif notification.get('severity') == 'high':
            self.priority_score = max(self.priority_score, 7.0)
        elif notification.get('severity') == 'medium':
            self.priority_score = max(self.priority_score, 4.0)
        else:
            self.priority_score = max(self.priority_score, 1.0)


@dataclass
class ThrottleMetrics:
    """Metrics for throttling tracking."""
    user_id: int
    channel: str
    notifications_sent: int = 0
    last_notification_time: Optional[datetime] = None
    hourly_count: int = 0
    daily_count: int = 0
    burst_count: int = 0
    burst_start_time: Optional[datetime] = None


class NotificationBatchingManager:
    """Manages notification batching to group and optimize delivery."""
    
    def __init__(self, config: Optional[BatchConfig] = None):
        self.config = config or BatchConfig()
        self.notification_manager = EnhancedNotificationManager()
        self.active_batches: Dict[str, NotificationBatch] = {}
        self.batch_scheduler_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """Start the batching manager."""
        if self.config.enabled:
            self.batch_scheduler_task = asyncio.create_task(self._batch_scheduler())
            logger.info("Notification batching manager started")
    
    async def stop(self):
        """Stop the batching manager."""
        if self.batch_scheduler_task:
            self.batch_scheduler_task.cancel()
            try:
                await self.batch_scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Notification batching manager stopped")
    
    async def add_notification_to_batch(self, notification: Dict[str, Any], db: Session) -> str:
        """
        Add a notification to an appropriate batch.
        
        Args:
            notification: Notification data
            db: Database session
            
        Returns:
            Batch ID
        """
        if not self.config.enabled:
            return "no_batching"
        
        # Check if notification should be sent immediately
        if self._should_send_immediately(notification):
            return "immediate"
        
        # Generate batch key
        batch_key = self._generate_batch_key(notification)
        
        # Get or create batch
        if batch_key not in self.active_batches:
            self.active_batches[batch_key] = NotificationBatch(
                id=batch_key,
                user_id=notification['user_id'],
                channel=notification['channel'],
                severity=notification.get('severity', 'medium')
            )
        
        # Add notification to batch
        self.active_batches[batch_key].add_notification(notification)
        
        # Schedule batch if it's full or has been waiting too long
        await self._check_batch_ready(batch_key)
        
        return batch_key
    
    def _should_send_immediately(self, notification: Dict[str, Any]) -> bool:
        """Check if notification should be sent immediately."""
        if not self.config.priority_override:
            return False
        
        severity = notification.get('severity', 'medium')
        return severity in ['critical', 'high']
    
    def _generate_batch_key(self, notification: Dict[str, Any]) -> str:
        """Generate a unique key for batching notifications."""
        parts = []
        
        if self.config.group_by_user:
            parts.append(f"user_{notification['user_id']}")
        
        if self.config.group_by_channel:
            parts.append(f"channel_{notification['channel']}")
        
        if self.config.group_by_severity:
            parts.append(f"severity_{notification.get('severity', 'medium')}")
        
        return "_".join(parts)
    
    async def _check_batch_ready(self, batch_key: str) -> None:
        """Check if a batch is ready to be sent."""
        batch = self.active_batches[batch_key]
        
        # Check if batch is full
        if len(batch.notifications) >= self.config.max_batch_size:
            await self._send_batch(batch_key)
            return
        
        # Check if batch has been waiting too long
        if batch.created_at + timedelta(minutes=self.config.max_batch_delay_minutes) <= datetime.now():
            await self._send_batch(batch_key)
    
    async def _send_batch(self, batch_key: str) -> None:
        """Send a batch of notifications."""
        if batch_key not in self.active_batches:
            return
        
        batch = self.active_batches[batch_key]
        batch.status = BatchStatus.PROCESSING
        
        try:
            # Create consolidated notification
            consolidated_notification = self._create_consolidated_notification(batch)
            
            # Send the consolidated notification
            db = next(get_db())
            await self.notification_manager._send_notifications_with_tracking(
                consolidated_notification, [], None, None, db
            )
            
            batch.status = BatchStatus.SENT
            logger.info(f"Batch {batch_key} sent successfully with {len(batch.notifications)} notifications")
            
        except Exception as e:
            batch.status = BatchStatus.FAILED
            logger.error(f"Failed to send batch {batch_key}: {e}")
        
        finally:
            # Remove batch from active batches
            del self.active_batches[batch_key]
    
    def _create_consolidated_notification(self, batch: NotificationBatch) -> Dict[str, Any]:
        """Create a consolidated notification from batch contents."""
        # Count notifications by severity
        severity_counts = {}
        form_changes = []
        
        for notification in batch.notifications:
            severity = notification.get('severity', 'medium')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            form_changes.append(notification.get('form_change_id'))
        
        # Create summary
        total_notifications = len(batch.notifications)
        severity_summary = ", ".join([f"{count} {severity}" for severity, count in severity_counts.items()])
        
        return {
            'user_id': batch.user_id,
            'channel': batch.channel,
            'subject': f"Batch Notification: {total_notifications} form changes detected",
            'message': f"You have {total_notifications} form change notifications ({severity_summary}). Please review the dashboard for details.",
            'severity': batch.severity,
            'form_change_ids': form_changes,
            'is_batch': True,
            'batch_size': total_notifications
        }
    
    async def _batch_scheduler(self) -> None:
        """Background task to process batches."""
        while True:
            try:
                current_time = datetime.now()
                
                # Check all active batches
                for batch_key in list(self.active_batches.keys()):
                    batch = self.active_batches[batch_key]
                    
                    # Check if batch should be sent due to time delay
                    if (batch.created_at + timedelta(minutes=self.config.max_batch_delay_minutes) <= current_time):
                        await self._send_batch(batch_key)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch scheduler: {e}")
                await asyncio.sleep(60)


class NotificationThrottlingManager:
    """Manages notification throttling to prevent spam."""
    
    def __init__(self, config: Optional[ThrottleConfig] = None):
        self.config = config or ThrottleConfig()
        self.throttle_metrics: Dict[str, ThrottleMetrics] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the throttling manager."""
        if self.config.enabled:
            self.cleanup_task = asyncio.create_task(self._cleanup_scheduler())
            logger.info("Notification throttling manager started")
    
    async def stop(self):
        """Stop the throttling manager."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Notification throttling manager stopped")
    
    async def check_throttle(self, user_id: int, channel: str, severity: str = "medium") -> bool:
        """
        Check if a notification should be throttled.
        
        Args:
            user_id: User ID
            channel: Notification channel
            severity: Notification severity
            
        Returns:
            True if notification should be sent, False if throttled
        """
        if not self.config.enabled:
            return True
        
        # Check exemptions
        if self._is_exempt_from_throttling(severity):
            return True
        
        # Get or create metrics
        metrics_key = f"{user_id}_{channel}"
        if metrics_key not in self.throttle_metrics:
            self.throttle_metrics[metrics_key] = ThrottleMetrics(user_id, channel)
        
        metrics = self.throttle_metrics[metrics_key]
        current_time = datetime.now()
        
        # Update burst tracking
        await self._update_burst_tracking(metrics, current_time)
        
        # Check rate limits
        if not await self._check_rate_limits(metrics, current_time):
            return False
        
        # Check cooldown
        if not await self._check_cooldown(metrics, current_time):
            return False
        
        # Check daily limit
        if not await self._check_daily_limit(metrics, current_time):
            return False
        
        # Update metrics
        await self._update_metrics(metrics, current_time)
        
        return True
    
    def _is_exempt_from_throttling(self, severity: str) -> bool:
        """Check if notification is exempt from throttling."""
        if self.config.exempt_high_priority and severity == 'high':
            return True
        if self.config.exempt_critical_severity and severity == 'critical':
            return True
        return False
    
    async def _update_burst_tracking(self, metrics: ThrottleMetrics, current_time: datetime) -> None:
        """Update burst tracking metrics."""
        if metrics.burst_start_time is None:
            metrics.burst_start_time = current_time
            metrics.burst_count = 0
        
        # Reset burst if window has passed
        if (metrics.burst_start_time + timedelta(minutes=self.config.burst_window_minutes) <= current_time):
            metrics.burst_start_time = current_time
            metrics.burst_count = 0
    
    async def _check_rate_limits(self, metrics: ThrottleMetrics, current_time: datetime) -> bool:
        """Check hourly and daily rate limits."""
        # Check hourly limit
        if metrics.hourly_count >= self.config.rate_limit_per_hour:
            logger.warning(f"Hourly rate limit exceeded for user {metrics.user_id}")
            return False
        
        # Check daily limit
        if metrics.daily_count >= self.config.rate_limit_per_day:
            logger.warning(f"Daily rate limit exceeded for user {metrics.user_id}")
            return False
        
        return True
    
    async def _check_cooldown(self, metrics: ThrottleMetrics, current_time: datetime) -> bool:
        """Check cooldown period."""
        if metrics.last_notification_time is None:
            return True
        
        cooldown_end = metrics.last_notification_time + timedelta(minutes=self.config.cooldown_minutes)
        if current_time < cooldown_end:
            logger.info(f"Cooldown period active for user {metrics.user_id}")
            return False
        
        return True
    
    async def _check_daily_limit(self, metrics: ThrottleMetrics, current_time: datetime) -> bool:
        """Check daily notification limit."""
        if metrics.daily_count >= self.config.daily_limit:
            logger.warning(f"Daily limit exceeded for user {metrics.user_id}")
            return False
        
        return True
    
    async def _update_metrics(self, metrics: ThrottleMetrics, current_time: datetime) -> None:
        """Update throttling metrics after successful notification."""
        metrics.notifications_sent += 1
        metrics.last_notification_time = current_time
        metrics.hourly_count += 1
        metrics.daily_count += 1
        metrics.burst_count += 1
    
    async def _cleanup_scheduler(self) -> None:
        """Background task to clean up old metrics."""
        while True:
            try:
                current_time = datetime.now()
                
                # Clean up old metrics
                for key in list(self.throttle_metrics.keys()):
                    metrics = self.throttle_metrics[key]
                    
                    # Reset hourly count if hour has passed
                    if (metrics.last_notification_time and 
                        metrics.last_notification_time + timedelta(hours=1) <= current_time):
                        metrics.hourly_count = 0
                    
                    # Reset daily count if day has passed
                    if (metrics.last_notification_time and 
                        metrics.last_notification_time + timedelta(days=1) <= current_time):
                        metrics.daily_count = 0
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                await asyncio.sleep(3600)
    
    async def get_throttle_metrics(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get current throttling metrics."""
        if user_id:
            return {
                key: {
                    'user_id': metrics.user_id,
                    'channel': metrics.channel,
                    'notifications_sent': metrics.notifications_sent,
                    'hourly_count': metrics.hourly_count,
                    'daily_count': metrics.daily_count,
                    'burst_count': metrics.burst_count,
                    'last_notification_time': metrics.last_notification_time.isoformat() if metrics.last_notification_time else None
                }
                for key, metrics in self.throttle_metrics.items()
                if metrics.user_id == user_id
            }
        else:
            return {
                key: {
                    'user_id': metrics.user_id,
                    'channel': metrics.channel,
                    'notifications_sent': metrics.notifications_sent,
                    'hourly_count': metrics.hourly_count,
                    'daily_count': metrics.daily_count,
                    'burst_count': metrics.burst_count,
                    'last_notification_time': metrics.last_notification_time.isoformat() if metrics.last_notification_time else None
                }
                for key, metrics in self.throttle_metrics.items()
            }


class NotificationBatchingThrottlingManager:
    """Combined manager for batching and throttling notifications."""
    
    def __init__(self, batch_config: Optional[BatchConfig] = None, throttle_config: Optional[ThrottleConfig] = None):
        self.batching_manager = NotificationBatchingManager(batch_config)
        self.throttling_manager = NotificationThrottlingManager(throttle_config)
    
    async def start(self):
        """Start both managers."""
        await self.batching_manager.start()
        await self.throttling_manager.start()
    
    async def stop(self):
        """Stop both managers."""
        await self.batching_manager.stop()
        await self.throttling_manager.stop()
    
    async def process_notification(self, notification: Dict[str, Any], db: Session) -> Dict[str, Any]:
        """
        Process a notification through batching and throttling.
        
        Args:
            notification: Notification data
            db: Database session
            
        Returns:
            Processing result
        """
        user_id = notification.get('user_id')
        channel = notification.get('channel', 'email')
        severity = notification.get('severity', 'medium')
        
        # Check throttling first
        if not await self.throttling_manager.check_throttle(user_id, channel, severity):
            return {
                'status': 'throttled',
                'reason': 'Rate limit or cooldown active',
                'batch_id': None
            }
        
        # Add to batch
        batch_id = await self.batching_manager.add_notification_to_batch(notification, db)
        
        return {
            'status': 'processed',
            'batch_id': batch_id,
            'throttled': False
        }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get combined metrics from both managers."""
        return {
            'batching': {
                'active_batches': len(self.batching_manager.active_batches),
                'batch_config': {
                    'enabled': self.batching_manager.config.enabled,
                    'max_batch_size': self.batching_manager.config.max_batch_size,
                    'max_batch_delay_minutes': self.batching_manager.config.max_batch_delay_minutes
                }
            },
            'throttling': {
                'active_metrics': len(self.throttling_manager.throttle_metrics),
                'throttle_config': {
                    'enabled': self.throttling_manager.config.enabled,
                    'rate_limit_per_hour': self.throttling_manager.config.rate_limit_per_hour,
                    'rate_limit_per_day': self.throttling_manager.config.rate_limit_per_day,
                    'cooldown_minutes': self.throttling_manager.config.cooldown_minutes
                }
            }
        }


# Global instance
batching_throttling_manager = NotificationBatchingThrottlingManager() 