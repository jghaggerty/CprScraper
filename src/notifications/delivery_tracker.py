"""
Notification Delivery Tracking and Retry Mechanisms

This module provides comprehensive tracking and retry functionality for notification delivery,
including delivery status tracking, automatic retries, and delivery analytics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..database.connection import get_db
from ..database.models import Notification, User, FormChange
from .channel_integration import ChannelIntegrationManager, NotificationResult

logger = logging.getLogger(__name__)


class DeliveryStatus(Enum):
    """Enumeration for notification delivery statuses."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    RETRYING = "retrying"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RetryStrategy(Enum):
    """Enumeration for retry strategies."""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay_seconds: int = 60
    max_delay_seconds: int = 3600  # 1 hour
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    backoff_multiplier: float = 2.0


@dataclass
class DeliveryMetrics:
    """Metrics for notification delivery tracking."""
    total_sent: int = 0
    total_delivered: int = 0
    total_failed: int = 0
    total_retried: int = 0
    average_delivery_time_seconds: float = 0.0
    success_rate: float = 0.0
    retry_rate: float = 0.0


class NotificationDeliveryTracker:
    """Enhanced notification delivery tracking with retry mechanisms."""
    
    def __init__(self, retry_config: Optional[RetryConfig] = None):
        self.retry_config = retry_config or RetryConfig()
        self.channel_manager = ChannelIntegrationManager()
        self._active_retries: Dict[int, asyncio.Task] = {}
        
    async def track_notification_delivery(self, notification_id: int, 
                                        channel_type: str, 
                                        recipient: str,
                                        content: Dict[str, Any]) -> NotificationResult:
        """
        Track and manage notification delivery with automatic retries.
        
        Args:
            notification_id: ID of the notification record
            channel_type: Type of notification channel (email, slack, teams)
            recipient: Recipient identifier (email, user ID, etc.)
            content: Notification content to send
            
        Returns:
            NotificationResult with delivery status and details
        """
        db = next(get_db())
        
        try:
            # Update notification status to sending
            await self._update_notification_status(db, notification_id, DeliveryStatus.SENDING)
            
            # Attempt delivery
            result = await self._attempt_delivery(channel_type, recipient, content)
            
            if result.success:
                # Mark as delivered
                await self._update_notification_status(
                    db, notification_id, DeliveryStatus.DELIVERED, 
                    delivery_time=result.delivery_time,
                    response_data=result.response_data
                )
                logger.info(f"Notification {notification_id} delivered successfully to {recipient}")
            else:
                # Handle delivery failure
                await self._handle_delivery_failure(db, notification_id, result, recipient)
                
            return result
            
        except Exception as e:
            logger.error(f"Error tracking notification delivery {notification_id}: {e}")
            await self._update_notification_status(
                db, notification_id, DeliveryStatus.FAILED, 
                error_message=str(e)
            )
            return NotificationResult(
                success=False,
                error_message=str(e),
                delivery_time=None,
                response_data=None
            )
        finally:
            db.close()
    
    async def _attempt_delivery(self, channel_type: str, recipient: str, 
                              content: Dict[str, Any]) -> NotificationResult:
        """Attempt to deliver notification through specified channel."""
        try:
            if channel_type == 'email':
                return await self.channel_manager.send_email_notification(recipient, content)
            elif channel_type == 'slack':
                return await self.channel_manager.send_slack_notification(recipient, content)
            elif channel_type == 'teams':
                return await self.channel_manager.send_teams_notification(recipient, content)
            else:
                raise ValueError(f"Unsupported channel type: {channel_type}")
        except Exception as e:
            logger.error(f"Delivery attempt failed for {channel_type} to {recipient}: {e}")
            return NotificationResult(
                success=False,
                error_message=str(e),
                delivery_time=None,
                response_data=None
            )
    
    async def _handle_delivery_failure(self, db: Session, notification_id: int, 
                                     result: NotificationResult, recipient: str):
        """Handle delivery failure and initiate retry if appropriate."""
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        
        if not notification:
            logger.error(f"Notification {notification_id} not found")
            return
        
        # Increment retry count
        notification.retry_count += 1
        notification.error_message = result.error_message
        
        if notification.retry_count <= self.retry_config.max_retries:
            # Schedule retry
            await self._schedule_retry(db, notification, recipient)
        else:
            # Max retries exceeded
            await self._update_notification_status(
                db, notification_id, DeliveryStatus.FAILED,
                error_message=f"Max retries ({self.retry_config.max_retries}) exceeded"
            )
            logger.warning(f"Notification {notification_id} failed after {notification.retry_count} retries")
        
        db.commit()
    
    async def _schedule_retry(self, db: Session, notification: Notification, recipient: str):
        """Schedule a retry for failed notification delivery."""
        delay_seconds = self._calculate_retry_delay(notification.retry_count)
        
        # Update status to retrying
        await self._update_notification_status(db, notification.id, DeliveryStatus.RETRYING)
        
        # Schedule retry task
        retry_task = asyncio.create_task(
            self._execute_retry(notification.id, recipient, delay_seconds)
        )
        self._active_retries[notification.id] = retry_task
        
        logger.info(f"Scheduled retry {notification.retry_count} for notification {notification.id} in {delay_seconds}s")
    
    async def _execute_retry(self, notification_id: int, recipient: str, delay_seconds: int):
        """Execute a scheduled retry after the specified delay."""
        try:
            # Wait for the delay
            await asyncio.sleep(delay_seconds)
            
            # Get notification data for retry
            db = next(get_db())
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            
            if not notification:
                logger.error(f"Notification {notification_id} not found for retry")
                return
            
            # Check if notification is still in retrying status
            if notification.status != DeliveryStatus.RETRYING.value:
                logger.info(f"Notification {notification_id} no longer in retrying status, skipping retry")
                return
            
            # Attempt retry delivery
            content = {
                'subject': notification.subject,
                'message': notification.message
            }
            
            result = await self._attempt_delivery(notification.notification_type, recipient, content)
            
            if result.success:
                await self._update_notification_status(
                    db, notification_id, DeliveryStatus.DELIVERED,
                    delivery_time=result.delivery_time,
                    response_data=result.response_data
                )
                logger.info(f"Retry successful for notification {notification_id}")
            else:
                # Handle retry failure
                await self._handle_delivery_failure(db, notification_id, result, recipient)
                
        except Exception as e:
            logger.error(f"Error during retry execution for notification {notification_id}: {e}")
            await self._update_notification_status(
                db, notification_id, DeliveryStatus.FAILED,
                error_message=f"Retry execution error: {str(e)}"
            )
        finally:
            db.close()
            # Remove from active retries
            self._active_retries.pop(notification_id, None)
    
    def _calculate_retry_delay(self, retry_count: int) -> int:
        """Calculate delay for retry based on strategy."""
        if self.retry_config.strategy == RetryStrategy.IMMEDIATE:
            return 0
        elif self.retry_config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.retry_config.initial_delay_seconds * (self.retry_config.backoff_multiplier ** (retry_count - 1))
        elif self.retry_config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = self.retry_config.initial_delay_seconds * retry_count
        elif self.retry_config.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = self.retry_config.initial_delay_seconds
        else:
            delay = self.retry_config.initial_delay_seconds
        
        return min(delay, self.retry_config.max_delay_seconds)
    
    async def _update_notification_status(self, db: Session, notification_id: int, 
                                        status: DeliveryStatus, **kwargs):
        """Update notification status and additional fields."""
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if notification:
            notification.status = status.value
            notification.sent_at = datetime.utcnow()
            
            if 'delivery_time' in kwargs:
                notification.delivery_time = kwargs['delivery_time']
            if 'error_message' in kwargs:
                notification.error_message = kwargs['error_message']
            if 'response_data' in kwargs:
                notification.response_data = kwargs['response_data']
            
            db.commit()
    
    async def get_delivery_metrics(self, time_range: Optional[Tuple[datetime, datetime]] = None) -> DeliveryMetrics:
        """Get delivery metrics for the specified time range."""
        db = next(get_db())
        
        try:
            query = db.query(Notification)
            
            if time_range:
                start_time, end_time = time_range
                query = query.filter(
                    and_(
                        Notification.sent_at >= start_time,
                        Notification.sent_at <= end_time
                    )
                )
            
            notifications = query.all()
            
            metrics = DeliveryMetrics()
            total_delivery_time = 0.0
            delivered_count = 0
            
            for notification in notifications:
                metrics.total_sent += 1
                
                if notification.status == DeliveryStatus.DELIVERED.value:
                    metrics.total_delivered += 1
                    if notification.delivery_time:
                        total_delivery_time += notification.delivery_time
                        delivered_count += 1
                elif notification.status == DeliveryStatus.FAILED.value:
                    metrics.total_failed += 1
                
                if notification.retry_count > 0:
                    metrics.total_retried += 1
            
            # Calculate derived metrics
            if metrics.total_sent > 0:
                metrics.success_rate = (metrics.total_delivered / metrics.total_sent) * 100
                metrics.retry_rate = (metrics.total_retried / metrics.total_sent) * 100
            
            if delivered_count > 0:
                metrics.average_delivery_time_seconds = total_delivery_time / delivered_count
            
            return metrics
            
        finally:
            db.close()
    
    async def get_pending_retries(self) -> List[Notification]:
        """Get list of notifications pending retry."""
        db = next(get_db())
        
        try:
            return db.query(Notification).filter(
                Notification.status == DeliveryStatus.RETRYING.value
            ).all()
        finally:
            db.close()
    
    async def cancel_retry(self, notification_id: int) -> bool:
        """Cancel a pending retry for a notification."""
        # Cancel the retry task if it exists
        if notification_id in self._active_retries:
            self._active_retries[notification_id].cancel()
            del self._active_retries[notification_id]
        
        # Update notification status
        db = next(get_db())
        try:
            await self._update_notification_status(db, notification_id, DeliveryStatus.CANCELLED)
            return True
        except Exception as e:
            logger.error(f"Error cancelling retry for notification {notification_id}: {e}")
            return False
        finally:
            db.close()
    
    async def cleanup_expired_notifications(self, max_age_hours: int = 24):
        """Clean up notifications that have been pending too long."""
        db = next(get_db())
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
            
            expired_notifications = db.query(Notification).filter(
                and_(
                    Notification.status.in_([DeliveryStatus.PENDING.value, DeliveryStatus.RETRYING.value]),
                    Notification.sent_at < cutoff_time
                )
            ).all()
            
            for notification in expired_notifications:
                await self._update_notification_status(
                    db, notification.id, DeliveryStatus.EXPIRED,
                    error_message="Notification expired due to age"
                )
                
                # Cancel any active retry task
                if notification.id in self._active_retries:
                    self._active_retries[notification.id].cancel()
                    del self._active_retries[notification.id]
            
            logger.info(f"Cleaned up {len(expired_notifications)} expired notifications")
            
        finally:
            db.close()
    
    async def get_notification_history(self, user_id: Optional[int] = None, 
                                     limit: int = 100) -> List[Dict[str, Any]]:
        """Get notification delivery history with optional user filtering."""
        db = next(get_db())
        
        try:
            query = db.query(Notification).join(FormChange)
            
            if user_id:
                # Filter by user if specified
                query = query.filter(FormChange.user_id == user_id)
            
            notifications = query.order_by(desc(Notification.sent_at)).limit(limit).all()
            
            history = []
            for notification in notifications:
                history.append({
                    'id': notification.id,
                    'form_change_id': notification.form_change_id,
                    'notification_type': notification.notification_type,
                    'recipient': notification.recipient,
                    'status': notification.status,
                    'sent_at': notification.sent_at,
                    'retry_count': notification.retry_count,
                    'error_message': notification.error_message,
                    'delivery_time': notification.delivery_time
                })
            
            return history
            
        finally:
            db.close()


class NotificationDeliveryAnalytics:
    """Analytics and reporting for notification delivery performance."""
    
    def __init__(self):
        self.tracker = NotificationDeliveryTracker()
    
    async def generate_delivery_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate comprehensive delivery report for the specified period."""
        metrics = await self.tracker.get_delivery_metrics((start_date, end_date))
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'metrics': {
                'total_sent': metrics.total_sent,
                'total_delivered': metrics.total_delivered,
                'total_failed': metrics.total_failed,
                'total_retried': metrics.total_retried,
                'success_rate': f"{metrics.success_rate:.2f}%",
                'retry_rate': f"{metrics.retry_rate:.2f}%",
                'average_delivery_time_seconds': f"{metrics.average_delivery_time_seconds:.2f}"
            },
            'performance_grade': self._calculate_performance_grade(metrics),
            'recommendations': self._generate_recommendations(metrics)
        }
    
    def _calculate_performance_grade(self, metrics: DeliveryMetrics) -> str:
        """Calculate performance grade based on metrics."""
        if metrics.success_rate >= 95:
            return "A"
        elif metrics.success_rate >= 85:
            return "B"
        elif metrics.success_rate >= 75:
            return "C"
        elif metrics.success_rate >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_recommendations(self, metrics: DeliveryMetrics) -> List[str]:
        """Generate recommendations based on delivery metrics."""
        recommendations = []
        
        if metrics.success_rate < 90:
            recommendations.append("Consider reviewing retry configuration and error handling")
        
        if metrics.retry_rate > 20:
            recommendations.append("High retry rate detected - investigate delivery channel issues")
        
        if metrics.average_delivery_time_seconds > 30:
            recommendations.append("Slow delivery times - consider optimizing notification processing")
        
        if metrics.total_failed > 0:
            recommendations.append("Failed notifications detected - review error logs and channel configuration")
        
        return recommendations 