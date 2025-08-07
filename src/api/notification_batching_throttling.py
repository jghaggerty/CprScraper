"""
API endpoints for notification batching and throttling management.

This module provides REST API endpoints for configuring and monitoring
notification batching and throttling functionality.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from ..database.connection import get_db
from ..database.models import User, Notification, UserNotificationPreference
from ..auth.auth import get_current_user
from ..notifications.batching_manager import (
    NotificationBatchingThrottlingManager, BatchConfig, ThrottleConfig,
    batching_throttling_manager
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification-batching-throttling", tags=["notification-batching-throttling"])


@router.get("/status")
async def get_system_status(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current status of batching and throttling systems."""
    try:
        metrics = await batching_throttling_manager.get_metrics()
        return {
            "status": "success",
            "data": {
                "batching": {
                    "enabled": metrics["batching"]["batch_config"]["enabled"],
                    "active_batches": metrics["batching"]["active_batches"],
                    "config": metrics["batching"]["batch_config"]
                },
                "throttling": {
                    "enabled": metrics["throttling"]["throttle_config"]["enabled"],
                    "active_metrics": metrics["throttling"]["active_metrics"],
                    "config": metrics["throttling"]["throttle_config"]
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get system status")


@router.get("/batches")
async def get_active_batches(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get all active notification batches."""
    try:
        active_batches = batching_throttling_manager.batching_manager.active_batches
        
        batch_data = []
        for batch_id, batch in active_batches.items():
            batch_data.append({
                "id": batch.id,
                "user_id": batch.user_id,
                "channel": batch.channel,
                "severity": batch.severity,
                "status": batch.status.value,
                "notifications_count": len(batch.notifications),
                "priority_score": batch.priority_score,
                "created_at": batch.created_at.isoformat(),
                "scheduled_for": batch.scheduled_for.isoformat() if batch.scheduled_for else None,
                "estimated_send_time": (batch.created_at + timedelta(minutes=batching_throttling_manager.batching_manager.config.max_batch_delay_minutes)).isoformat()
            })
        
        return {
            "status": "success",
            "data": {
                "active_batches": batch_data,
                "total_active_batches": len(active_batches)
            }
        }
    except Exception as e:
        logger.error(f"Error getting active batches: {e}")
        raise HTTPException(status_code=500, detail="Failed to get active batches")


@router.get("/batches/{batch_id}")
async def get_batch_details(batch_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get detailed information about a specific batch."""
    try:
        if batch_id not in batching_throttling_manager.batching_manager.active_batches:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch = batching_throttling_manager.batching_manager.active_batches[batch_id]
        
        return {
            "status": "success",
            "data": {
                "id": batch.id,
                "user_id": batch.user_id,
                "channel": batch.channel,
                "severity": batch.severity,
                "status": batch.status.value,
                "notifications": batch.notifications,
                "notifications_count": len(batch.notifications),
                "priority_score": batch.priority_score,
                "created_at": batch.created_at.isoformat(),
                "scheduled_for": batch.scheduled_for.isoformat() if batch.scheduled_for else None,
                "estimated_send_time": (batch.created_at + timedelta(minutes=batching_throttling_manager.batching_manager.config.max_batch_delay_minutes)).isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch details: {e}")
        raise HTTPException(status_code=500, detail="Failed to get batch details")


@router.post("/batches/{batch_id}/send")
async def send_batch_immediately(batch_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Send a batch immediately instead of waiting for the scheduled time."""
    try:
        if batch_id not in batching_throttling_manager.batching_manager.active_batches:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch = batching_throttling_manager.batching_manager.active_batches[batch_id]
        
        # Send the batch immediately
        await batching_throttling_manager.batching_manager.send_batch_immediately(batch_id)
        
        return {
            "status": "success",
            "message": f"Batch {batch_id} sent successfully",
            "data": {
                "batch_id": batch_id,
                "notifications_count": len(batch.notifications),
                "sent_at": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending batch immediately: {e}")
        raise HTTPException(status_code=500, detail="Failed to send batch immediately")


@router.delete("/batches/{batch_id}")
async def cancel_batch(batch_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Cancel a pending batch."""
    try:
        if batch_id not in batching_throttling_manager.batching_manager.active_batches:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        batch = batching_throttling_manager.batching_manager.active_batches[batch_id]
        notifications_count = len(batch.notifications)
        
        # Cancel the batch
        await batching_throttling_manager.batching_manager.cancel_batch(batch_id)
        
        return {
            "status": "success",
            "message": f"Batch {batch_id} cancelled successfully",
            "data": {
                "batch_id": batch_id,
                "notifications_count": notifications_count,
                "cancelled_at": datetime.now().isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling batch: {e}")
        raise HTTPException(status_code=500, detail="Failed to cancel batch")


@router.get("/throttling/metrics")
async def get_throttling_metrics(user_id: Optional[int] = Query(None), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get throttling metrics for all users or a specific user."""
    try:
        metrics = await batching_throttling_manager.throttling_manager.get_throttle_metrics(user_id)
        
        return {
            "status": "success",
            "data": {
                "metrics": metrics,
                "total_users_tracked": len(metrics) if user_id is None else 1
            }
        }
    except Exception as e:
        logger.error(f"Error getting throttling metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get throttling metrics")


@router.get("/throttling/metrics/{user_id}")
async def get_user_throttling_metrics(user_id: int, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get throttling metrics for a specific user."""
    try:
        metrics = await batching_throttling_manager.throttling_manager.get_throttle_metrics(user_id)
        
        return {
            "status": "success",
            "data": {
                "user_id": user_id,
                "metrics": metrics
            }
        }
    except Exception as e:
        logger.error(f"Error getting user throttling metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user throttling metrics")


@router.post("/throttling/reset/{user_id}")
async def reset_user_throttling(user_id: int, channel: Optional[str] = Query(None), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Reset throttling metrics for a specific user and optionally a specific channel."""
    try:
        await batching_throttling_manager.throttling_manager.reset_user_throttling(user_id, channel)
        
        return {
            "status": "success",
            "message": f"Throttling metrics reset for user {user_id}" + (f" and channel {channel}" if channel else ""),
            "data": {
                "user_id": user_id,
                "channel": channel,
                "reset_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error resetting user throttling: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset user throttling")


@router.get("/config/batching")
async def get_batching_config(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current batching configuration."""
    try:
        config = batching_throttling_manager.batching_manager.config
        
        return {
            "status": "success",
            "data": {
                "enabled": config.enabled,
                "max_batch_size": config.max_batch_size,
                "max_batch_delay_minutes": config.max_batch_delay_minutes,
                "priority_override": config.priority_override,
                "group_by_user": config.group_by_user,
                "group_by_severity": config.group_by_severity,
                "group_by_channel": config.group_by_channel
            }
        }
    except Exception as e:
        logger.error(f"Error getting batching config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get batching config")


@router.put("/config/batching")
async def update_batching_config(config_data: Dict[str, Any] = Body(...), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Update the batching configuration."""
    try:
        # Validate and update configuration
        await batching_throttling_manager.batching_manager.update_config(config_data)
        
        return {
            "status": "success",
            "message": "Batching configuration updated successfully",
            "data": {
                "enabled": config_data.get("enabled", True),
                "max_batch_size": config_data.get("max_batch_size", 10),
                "max_batch_delay_minutes": config_data.get("max_batch_delay_minutes", 30),
                "priority_override": config_data.get("priority_override", False),
                "group_by_user": config_data.get("group_by_user", True),
                "group_by_severity": config_data.get("group_by_severity", True),
                "group_by_channel": config_data.get("group_by_channel", True),
                "updated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error updating batching config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update batching config")


@router.get("/config/throttling")
async def get_throttling_config(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Get the current throttling configuration."""
    try:
        config = batching_throttling_manager.throttling_manager.config
        
        return {
            "status": "success",
            "data": {
                "enabled": config.enabled,
                "rate_limit_per_hour": config.rate_limit_per_hour,
                "rate_limit_per_day": config.rate_limit_per_day,
                "cooldown_minutes": config.cooldown_minutes,
                "burst_limit": config.burst_limit,
                "burst_window_minutes": config.burst_window_minutes,
                "daily_limit": config.daily_limit,
                "exempt_high_priority": config.exempt_high_priority,
                "exempt_critical_severity": config.exempt_critical_severity
            }
        }
    except Exception as e:
        logger.error(f"Error getting throttling config: {e}")
        raise HTTPException(status_code=500, detail="Failed to get throttling config")


@router.put("/config/throttling")
async def update_throttling_config(config_data: Dict[str, Any] = Body(...), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Update the throttling configuration."""
    try:
        # Validate and update configuration
        await batching_throttling_manager.throttling_manager.update_config(config_data)
        
        return {
            "status": "success",
            "message": "Throttling configuration updated successfully",
            "data": {
                "enabled": config_data.get("enabled", True),
                "rate_limit_per_hour": config_data.get("rate_limit_per_hour", 50),
                "rate_limit_per_day": config_data.get("rate_limit_per_day", 200),
                "cooldown_minutes": config_data.get("cooldown_minutes", 5),
                "burst_limit": config_data.get("burst_limit", 10),
                "burst_window_minutes": config_data.get("burst_window_minutes", 15),
                "daily_limit": config_data.get("daily_limit", 100),
                "exempt_high_priority": config_data.get("exempt_high_priority", True),
                "exempt_critical_severity": config_data.get("exempt_critical_severity", True),
                "updated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error updating throttling config: {e}")
        raise HTTPException(status_code=500, detail="Failed to update throttling config")


@router.post("/test/notification")
async def test_notification_processing(notification_data: Dict[str, Any] = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Test notification processing through batching and throttling."""
    try:
        # Process the notification through batching and throttling
        result = await batching_throttling_manager.process_notification(notification_data, db)
        
        return {
            "status": "success",
            "message": "Notification processing test completed",
            "data": {
                "notification_data": notification_data,
                "processing_result": result,
                "tested_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error testing notification processing: {e}")
        raise HTTPException(status_code=500, detail="Failed to test notification processing")


@router.get("/analytics/summary")
async def get_analytics_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get analytics summary for batching and throttling."""
    try:
        # Get active batches count
        active_batches = len(batching_throttling_manager.batching_manager.active_batches)
        
        # Get active throttling metrics count
        active_throttle_metrics = len(batching_throttling_manager.throttling_manager.throttle_metrics)
        
        # Get recent notifications (last 24 hours)
        recent_notifications = db.query(Notification).filter(
            Notification.created_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        # Analyze recent notifications
        total_notifications = len(recent_notifications)
        batched_notifications = sum(1 for n in recent_notifications if getattr(n, 'is_batch', False))
        throttled_notifications = sum(1 for n in recent_notifications if getattr(n, 'throttled', False))
        immediate_notifications = total_notifications - batched_notifications - throttled_notifications
        
        return {
            "status": "success",
            "data": {
                "active_batches": active_batches,
                "active_throttle_metrics": active_throttle_metrics,
                "recent_notifications": {
                    "total": total_notifications,
                    "batched": batched_notifications,
                    "throttled": throttled_notifications,
                    "immediate": immediate_notifications
                },
                "summary_generated_at": datetime.now().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get analytics summary") 