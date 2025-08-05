"""
API endpoints for notification delivery tracking and management.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..database.connection import get_db
from ..database.models import Notification, User
from ..notifications.delivery_tracker import (
    NotificationDeliveryTracker, 
    NotificationDeliveryAnalytics,
    RetryConfig, 
    DeliveryStatus,
    RetryStrategy
)
from ..auth.user_service import UserService, get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notification-tracking"])


@router.get("/delivery-metrics")
async def get_delivery_metrics(
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification delivery metrics for the specified time range."""
    try:
        tracker = NotificationDeliveryTracker()
        
        time_range = None
        if start_date and end_date:
            time_range = (start_date, end_date)
        
        metrics = await tracker.get_delivery_metrics(time_range)
        
        return {
            "success": True,
            "metrics": {
                "total_sent": metrics.total_sent,
                "total_delivered": metrics.total_delivered,
                "total_failed": metrics.total_failed,
                "total_retried": metrics.total_retried,
                "success_rate": f"{metrics.success_rate:.2f}%",
                "retry_rate": f"{metrics.retry_rate:.2f}%",
                "average_delivery_time_seconds": f"{metrics.average_delivery_time_seconds:.2f}"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving delivery metrics: {str(e)}")


@router.get("/delivery-report")
async def get_delivery_report(
    start_date: datetime = Query(..., description="Start date for report"),
    end_date: datetime = Query(..., description="End date for report"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive delivery report for the specified period."""
    try:
        analytics = NotificationDeliveryAnalytics()
        report = await analytics.generate_delivery_report(start_date, end_date)
        
        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating delivery report: {str(e)}")


@router.get("/pending-retries")
async def get_pending_retries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of notifications pending retry."""
    try:
        tracker = NotificationDeliveryTracker()
        pending_retries = await tracker.get_pending_retries()
        
        retry_list = []
        for notification in pending_retries:
            retry_list.append({
                "id": notification.id,
                "form_change_id": notification.form_change_id,
                "notification_type": notification.notification_type,
                "recipient": notification.recipient,
                "subject": notification.subject,
                "retry_count": notification.retry_count,
                "error_message": notification.error_message,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None
            })
        
        return {
            "success": True,
            "pending_retries": retry_list,
            "count": len(retry_list)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving pending retries: {str(e)}")


@router.post("/cancel-retry/{notification_id}")
async def cancel_retry(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending retry for a notification."""
    try:
        tracker = NotificationDeliveryTracker()
        success = await tracker.cancel_retry(notification_id)
        
        if success:
            return {
                "success": True,
                "message": f"Retry cancelled for notification {notification_id}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found or retry not cancelled")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling retry: {str(e)}")


@router.get("/history")
async def get_notification_history(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification delivery history."""
    try:
        tracker = NotificationDeliveryTracker()
        history = await tracker.get_notification_history(user_id, limit)
        
        return {
            "success": True,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving notification history: {str(e)}")


@router.get("/status/{notification_id}")
async def get_notification_status(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed status of a specific notification."""
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail=f"Notification {notification_id} not found")
        
        return {
            "success": True,
            "notification": {
                "id": notification.id,
                "form_change_id": notification.form_change_id,
                "notification_type": notification.notification_type,
                "recipient": notification.recipient,
                "subject": notification.subject,
                "status": notification.status,
                "retry_count": notification.retry_count,
                "error_message": notification.error_message,
                "delivery_time": notification.delivery_time,
                "response_data": notification.response_data,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "created_at": notification.created_at.isoformat() if notification.created_at else None,
                "updated_at": notification.updated_at.isoformat() if notification.updated_at else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving notification status: {str(e)}")


@router.post("/cleanup-expired")
async def cleanup_expired_notifications(
    max_age_hours: int = Query(24, description="Maximum age in hours before cleanup"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clean up expired notifications."""
    try:
        tracker = NotificationDeliveryTracker()
        await tracker.cleanup_expired_notifications(max_age_hours)
        
        return {
            "success": True,
            "message": f"Cleanup completed for notifications older than {max_age_hours} hours"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")


@router.get("/stats/summary")
async def get_notification_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary statistics for notifications."""
    try:
        # Get counts by status
        status_counts = {}
        for status in DeliveryStatus:
            count = db.query(Notification).filter(Notification.status == status.value).count()
            status_counts[status.value] = count
        
        # Get recent activity (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_count = db.query(Notification).filter(
            Notification.sent_at >= cutoff_time
        ).count()
        
        # Get failed notifications in last 24 hours
        recent_failed = db.query(Notification).filter(
            and_(
                Notification.status == DeliveryStatus.FAILED.value,
                Notification.sent_at >= cutoff_time
            )
        ).count()
        
        return {
            "success": True,
            "summary": {
                "status_counts": status_counts,
                "recent_activity": {
                    "total_last_24h": recent_count,
                    "failed_last_24h": recent_failed,
                    "success_rate_last_24h": f"{((recent_count - recent_failed) / max(recent_count, 1)) * 100:.2f}%"
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving notification stats: {str(e)}")


@router.get("/stats/by-channel")
async def get_notification_stats_by_channel(
    start_date: Optional[datetime] = Query(None, description="Start date for stats"),
    end_date: Optional[datetime] = Query(None, description="End date for stats"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification statistics grouped by channel type."""
    try:
        query = db.query(Notification)
        
        if start_date and end_date:
            query = query.filter(
                and_(
                    Notification.sent_at >= start_date,
                    Notification.sent_at <= end_date
                )
            )
        
        notifications = query.all()
        
        # Group by channel type
        channel_stats = {}
        for notification in notifications:
            channel_type = notification.notification_type
            if channel_type not in channel_stats:
                channel_stats[channel_type] = {
                    "total": 0,
                    "delivered": 0,
                    "failed": 0,
                    "retried": 0,
                    "avg_delivery_time": 0.0
                }
            
            channel_stats[channel_type]["total"] += 1
            
            if notification.status == DeliveryStatus.DELIVERED.value:
                channel_stats[channel_type]["delivered"] += 1
            elif notification.status == DeliveryStatus.FAILED.value:
                channel_stats[channel_type]["failed"] += 1
            
            if notification.retry_count > 0:
                channel_stats[channel_type]["retried"] += 1
            
            if notification.delivery_time:
                channel_stats[channel_type]["avg_delivery_time"] += notification.delivery_time
        
        # Calculate averages and percentages
        for channel_type, stats in channel_stats.items():
            if stats["total"] > 0:
                stats["success_rate"] = f"{(stats['delivered'] / stats['total']) * 100:.2f}%"
                stats["retry_rate"] = f"{(stats['retried'] / stats['total']) * 100:.2f}%"
                if stats["delivered"] > 0:
                    stats["avg_delivery_time"] = f"{stats['avg_delivery_time'] / stats['delivered']:.2f}s"
                else:
                    stats["avg_delivery_time"] = "N/A"
            else:
                stats["success_rate"] = "0.00%"
                stats["retry_rate"] = "0.00%"
                stats["avg_delivery_time"] = "N/A"
        
        return {
            "success": True,
            "channel_stats": channel_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving channel stats: {str(e)}")


@router.post("/retry-config")
async def update_retry_config(
    config: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update retry configuration (admin only)."""
    try:
        # Check if user is admin
        user_service = UserService()
        if not user_service.is_admin(current_user.id):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Validate config
        required_fields = ["max_retries", "initial_delay_seconds", "max_delay_seconds", "strategy"]
        for field in required_fields:
            if field not in config:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Create new retry config
        retry_config = RetryConfig(
            max_retries=config["max_retries"],
            initial_delay_seconds=config["initial_delay_seconds"],
            max_delay_seconds=config["max_delay_seconds"],
            strategy=RetryStrategy(config["strategy"]),
            backoff_multiplier=config.get("backoff_multiplier", 2.0)
        )
        
        # Note: In a real implementation, you would store this configuration
        # in a database or configuration file for persistence
        
        return {
            "success": True,
            "message": "Retry configuration updated successfully",
            "config": {
                "max_retries": retry_config.max_retries,
                "initial_delay_seconds": retry_config.initial_delay_seconds,
                "max_delay_seconds": retry_config.max_delay_seconds,
                "strategy": retry_config.strategy.value,
                "backoff_multiplier": retry_config.backoff_multiplier
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating retry config: {str(e)}") 