"""
API endpoints for notification batching and throttling management.

This module provides REST API endpoints for configuring and monitoring
notification batching and throttling functionality.
"""

import logging
from datetime import datetime, timedelta
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


class NotificationBatchingThrottlingAPI:
    """API endpoints for notification batching and throttling management."""
    
    @router.get("/status")
    async def get_system_status(self, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
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
    async def get_active_batches(self, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
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
    async def get_batch_details(self, batch_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
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
    async def send_batch_immediately(self, batch_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Send a batch immediately instead of waiting for the scheduled time."""
        try:
            if batch_id not in batching_throttling_manager.batching_manager.active_batches:
                raise HTTPException(status_code=404, detail="Batch not found")
            
            await batching_throttling_manager.batching_manager._send_batch(batch_id)
            
            return {
                "status": "success",
                "message": f"Batch {batch_id} sent successfully",
                "data": {
                    "batch_id": batch_id,
                    "sent_at": datetime.now().isoformat()
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
            raise HTTPException(status_code=500, detail="Failed to send batch")
    
    @router.delete("/batches/{batch_id}")
    async def cancel_batch(self, batch_id: str, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Cancel a pending batch."""
        try:
            if batch_id not in batching_throttling_manager.batching_manager.active_batches:
                raise HTTPException(status_code=404, detail="Batch not found")
            
            batch = batching_throttling_manager.batching_manager.active_batches[batch_id]
            batch.status = batching_throttling_manager.batching_manager.BatchStatus.CANCELLED
            
            # Remove from active batches
            del batching_throttling_manager.batching_manager.active_batches[batch_id]
            
            return {
                "status": "success",
                "message": f"Batch {batch_id} cancelled successfully",
                "data": {
                    "batch_id": batch_id,
                    "cancelled_at": datetime.now().isoformat(),
                    "notifications_count": len(batch.notifications)
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling batch: {e}")
            raise HTTPException(status_code=500, detail="Failed to cancel batch")
    
    @router.get("/throttling/metrics")
    async def get_throttling_metrics(self, user_id: Optional[int] = Query(None), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Get throttling metrics for users."""
        try:
            metrics = await batching_throttling_manager.throttling_manager.get_throttle_metrics(user_id)
            
            return {
                "status": "success",
                "data": {
                    "throttle_metrics": metrics,
                    "total_users_tracked": len(metrics)
                }
            }
        except Exception as e:
            logger.error(f"Error getting throttling metrics: {e}")
            raise HTTPException(status_code=500, detail="Failed to get throttling metrics")
    
    @router.get("/throttling/metrics/{user_id}")
    async def get_user_throttling_metrics(self, user_id: int, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Get throttling metrics for a specific user."""
        try:
            metrics = await batching_throttling_manager.throttling_manager.get_throttle_metrics(user_id)
            
            return {
                "status": "success",
                "data": {
                    "user_id": user_id,
                    "throttle_metrics": metrics
                }
            }
        except Exception as e:
            logger.error(f"Error getting user throttling metrics: {e}")
            raise HTTPException(status_code=500, detail="Failed to get user throttling metrics")
    
    @router.post("/throttling/reset/{user_id}")
    async def reset_user_throttling(self, user_id: int, channel: Optional[str] = Query(None), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Reset throttling metrics for a user."""
        try:
            if channel:
                metrics_key = f"{user_id}_{channel}"
                if metrics_key in batching_throttling_manager.throttling_manager.throttle_metrics:
                    del batching_throttling_manager.throttling_manager.throttle_metrics[metrics_key]
            else:
                # Reset all channels for user
                keys_to_remove = [
                    key for key in batching_throttling_manager.throttling_manager.throttle_metrics.keys()
                    if key.startswith(f"{user_id}_")
                ]
                for key in keys_to_remove:
                    del batching_throttling_manager.throttling_manager.throttle_metrics[key]
            
            return {
                "status": "success",
                "message": f"Throttling metrics reset for user {user_id}",
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
    async def get_batching_config(self, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Get current batching configuration."""
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
            raise HTTPException(status_code=500, detail="Failed to get batching configuration")
    
    @router.put("/config/batching")
    async def update_batching_config(self, config_data: Dict[str, Any] = Body(...), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Update batching configuration."""
        try:
            config = batching_throttling_manager.batching_manager.config
            
            # Update config fields
            if "enabled" in config_data:
                config.enabled = config_data["enabled"]
            if "max_batch_size" in config_data:
                config.max_batch_size = config_data["max_batch_size"]
            if "max_batch_delay_minutes" in config_data:
                config.max_batch_delay_minutes = config_data["max_batch_delay_minutes"]
            if "priority_override" in config_data:
                config.priority_override = config_data["priority_override"]
            if "group_by_user" in config_data:
                config.group_by_user = config_data["group_by_user"]
            if "group_by_severity" in config_data:
                config.group_by_severity = config_data["group_by_severity"]
            if "group_by_channel" in config_data:
                config.group_by_channel = config_data["group_by_channel"]
            
            return {
                "status": "success",
                "message": "Batching configuration updated successfully",
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
            logger.error(f"Error updating batching config: {e}")
            raise HTTPException(status_code=500, detail="Failed to update batching configuration")
    
    @router.get("/config/throttling")
    async def get_throttling_config(self, current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Get current throttling configuration."""
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
            raise HTTPException(status_code=500, detail="Failed to get throttling configuration")
    
    @router.put("/config/throttling")
    async def update_throttling_config(self, config_data: Dict[str, Any] = Body(...), current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
        """Update throttling configuration."""
        try:
            config = batching_throttling_manager.throttling_manager.config
            
            # Update config fields
            if "enabled" in config_data:
                config.enabled = config_data["enabled"]
            if "rate_limit_per_hour" in config_data:
                config.rate_limit_per_hour = config_data["rate_limit_per_hour"]
            if "rate_limit_per_day" in config_data:
                config.rate_limit_per_day = config_data["rate_limit_per_day"]
            if "cooldown_minutes" in config_data:
                config.cooldown_minutes = config_data["cooldown_minutes"]
            if "burst_limit" in config_data:
                config.burst_limit = config_data["burst_limit"]
            if "burst_window_minutes" in config_data:
                config.burst_window_minutes = config_data["burst_window_minutes"]
            if "daily_limit" in config_data:
                config.daily_limit = config_data["daily_limit"]
            if "exempt_high_priority" in config_data:
                config.exempt_high_priority = config_data["exempt_high_priority"]
            if "exempt_critical_severity" in config_data:
                config.exempt_critical_severity = config_data["exempt_critical_severity"]
            
            return {
                "status": "success",
                "message": "Throttling configuration updated successfully",
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
            logger.error(f"Error updating throttling config: {e}")
            raise HTTPException(status_code=500, detail="Failed to update throttling configuration")
    
    @router.post("/test/notification")
    async def test_notification_processing(self, notification_data: Dict[str, Any] = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
        """Test notification processing through batching and throttling."""
        try:
            # Add required fields if not present
            if "user_id" not in notification_data:
                notification_data["user_id"] = current_user.id
            if "channel" not in notification_data:
                notification_data["channel"] = "email"
            if "severity" not in notification_data:
                notification_data["severity"] = "medium"
            
            # Process the notification
            result = await batching_throttling_manager.process_notification(notification_data, db)
            
            return {
                "status": "success",
                "data": {
                    "notification_data": notification_data,
                    "processing_result": result,
                    "processed_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error testing notification processing: {e}")
            raise HTTPException(status_code=500, detail="Failed to test notification processing")
    
    @router.get("/analytics/summary")
    async def get_analytics_summary(self, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Dict[str, Any]:
        """Get analytics summary for batching and throttling."""
        try:
            # Get active batches count
            active_batches = len(batching_throttling_manager.batching_manager.active_batches)
            
            # Get throttling metrics count
            active_metrics = len(batching_throttling_manager.throttling_manager.throttle_metrics)
            
            # Get recent notifications with batching/throttling info
            recent_notifications = db.query(Notification).filter(
                Notification.created_at >= datetime.now() - timedelta(hours=24)
            ).all()
            
            batched_count = sum(1 for n in recent_notifications if n.is_batch)
            throttled_count = sum(1 for n in recent_notifications if n.throttled)
            
            return {
                "status": "success",
                "data": {
                    "active_batches": active_batches,
                    "active_throttle_metrics": active_metrics,
                    "recent_notifications": {
                        "total": len(recent_notifications),
                        "batched": batched_count,
                        "throttled": throttled_count,
                        "immediate": len(recent_notifications) - batched_count - throttled_count
                    },
                    "generated_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error getting analytics summary: {e}")
            raise HTTPException(status_code=500, detail="Failed to get analytics summary")


# Create API instance
api_instance = NotificationBatchingThrottlingAPI() 