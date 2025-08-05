"""
API endpoints for notification channel management and testing.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any
import logging

from ..notifications.channel_integration import ChannelIntegrationManager, notification_batching
from ..auth.user_service import UserService, get_current_user
from ..database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification-channels", tags=["notification-channels"])

# Global channel manager instance
channel_manager = ChannelIntegrationManager()


@router.get("/status")
async def get_channel_status() -> Dict[str, Any]:
    """
    Get the status of all notification channels.
    
    Returns:
        Dictionary with channel status information
    """
    try:
        status = channel_manager.get_channel_status()
        return {
            "success": True,
            "channels": status,
            "message": "Channel status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting channel status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get channel status: {str(e)}")


@router.post("/test-connectivity")
async def test_channel_connectivity() -> Dict[str, Any]:
    """
    Test connectivity to all configured notification channels.
    
    Returns:
        Dictionary with connectivity test results
    """
    try:
        results = await channel_manager.test_channel_connectivity()
        
        # Count successful and failed tests
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        return {
            "success": True,
            "connectivity_results": results,
            "summary": {
                "total_channels": total,
                "successful_connections": successful,
                "failed_connections": total - successful
            },
            "message": f"Connectivity test completed: {successful}/{total} channels working"
        }
    except Exception as e:
        logger.error(f"Error testing channel connectivity: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test connectivity: {str(e)}")


@router.post("/test-notification")
async def test_notification(
    channel: str,
    test_data: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Send a test notification through a specific channel.
    
    Args:
        channel: The notification channel to test (email, slack, teams)
        test_data: Optional test data to include in the notification
        current_user: Current authenticated user
        
    Returns:
        Dictionary with test results
    """
    try:
        if channel not in channel_manager.notifiers:
            raise HTTPException(
                status_code=400, 
                detail=f"Channel '{channel}' is not available or not configured"
            )
        
        # Use default test data if none provided
        if test_data is None:
            test_data = {
                "agency_name": "Test Agency",
                "form_name": "TEST-001",
                "severity": "medium",
                "change_description": "This is a test notification from the API",
                "detected_at": "2024-01-15 10:30:00 UTC",
                "clients_impacted": 0,
                "icp_percentage": 0
            }
        
        # Create mock user preferences
        preferences = [{
            "notification_type": channel,
            "is_enabled": True,
            "change_severity": "all",
            "template_type": "product_manager"
        }]
        
        # Send test notification
        results = await channel_manager.send_multi_channel_notification(
            test_data, preferences, current_user
        )
        
        # Find the result for the requested channel
        channel_result = next((r for r in results if r.channel == channel), None)
        
        if channel_result:
            return {
                "success": channel_result.success,
                "channel": channel,
                "recipient": channel_result.recipient,
                "sent_at": channel_result.sent_at.isoformat() if channel_result.sent_at else None,
                "error_message": channel_result.error_message,
                "retry_count": channel_result.retry_count,
                "message": f"Test notification {'sent successfully' if channel_result.success else 'failed'}"
            }
        else:
            return {
                "success": False,
                "channel": channel,
                "message": f"No result found for channel '{channel}'"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending test notification to {channel}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to send test notification: {str(e)}")


@router.get("/batching-status")
async def get_batching_status() -> Dict[str, Any]:
    """
    Get the current status of notification batching.
    
    Returns:
        Dictionary with batching status information
    """
    try:
        # Get batching configuration
        batching_config = {
            "batch_size": notification_batching.batch_size,
            "batch_window_seconds": notification_batching.batch_window,
            "pending_notifications_count": len(notification_batching.pending_notifications)
        }
        
        # Get pending notifications by user and channel
        pending_summary = {}
        for key, notifications in notification_batching.pending_notifications.items():
            user_id, channel = key.split('_', 1)
            if user_id not in pending_summary:
                pending_summary[user_id] = {}
            pending_summary[user_id][channel] = len(notifications)
        
        return {
            "success": True,
            "batching_config": batching_config,
            "pending_notifications": pending_summary,
            "message": "Batching status retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting batching status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get batching status: {str(e)}")


@router.post("/clear-batch")
async def clear_batch(
    user_id: int,
    channel: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Clear batched notifications for a specific user and channel.
    
    Args:
        user_id: ID of the user whose batch should be cleared
        channel: The notification channel
        current_user: Current authenticated user
        
    Returns:
        Dictionary with operation result
    """
    try:
        # Check if user has permission to clear batches
        if current_user.role != "admin" and current_user.id != user_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions to clear batch")
        
        notification_batching.clear_batch(user_id, channel)
        
        return {
            "success": True,
            "user_id": user_id,
            "channel": channel,
            "message": f"Batch cleared for user {user_id} on channel {channel}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing batch for user {user_id} on channel {channel}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear batch: {str(e)}")


@router.get("/configuration")
async def get_channel_configuration() -> Dict[str, Any]:
    """
    Get the current notification channel configuration.
    
    Returns:
        Dictionary with channel configuration (without sensitive data)
    """
    try:
        config = channel_manager.config
        
        # Remove sensitive information
        safe_config = {}
        for channel, settings in config.items():
            safe_config[channel] = {
                "enabled": settings.get("enabled", False),
                "configured": bool(
                    settings.get("webhook_url") if channel in ["slack", "teams"] 
                    else settings.get("smtp_server")
                )
            }
            
            # Add non-sensitive configuration details
            if channel == "email":
                safe_config[channel]["smtp_port"] = settings.get("smtp_port")
                safe_config[channel]["from_address"] = settings.get("from_address")
            elif channel in ["slack", "teams"]:
                safe_config[channel]["webhook_configured"] = bool(settings.get("webhook_url"))
        
        return {
            "success": True,
            "configuration": safe_config,
            "message": "Channel configuration retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error getting channel configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration: {str(e)}")


@router.post("/enable-channel")
async def enable_channel(
    channel: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Enable a notification channel.
    
    Args:
        channel: The channel to enable (email, slack, teams)
        current_user: Current authenticated user
        
    Returns:
        Dictionary with operation result
    """
    try:
        # Check if user has admin permissions
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin permissions required")
        
        if channel not in ["email", "slack", "teams"]:
            raise HTTPException(status_code=400, detail=f"Invalid channel: {channel}")
        
        # Update configuration
        if channel in channel_manager.config:
            channel_manager.config[channel]["enabled"] = True
            
            # Reinitialize notifiers if needed
            if channel not in channel_manager.notifiers:
                if channel == "email":
                    email_config = channel_manager.config.get("email", {})
                    if email_config.get("enabled", False):
                        from ..notifications.notifier import EmailNotifier
                        channel_manager.notifiers["email"] = EmailNotifier(email_config)
                elif channel == "slack":
                    slack_config = channel_manager.config.get("slack", {})
                    if slack_config.get("enabled", False) and slack_config.get("webhook_url"):
                        from ..notifications.notifier import SlackNotifier
                        channel_manager.notifiers["slack"] = SlackNotifier(slack_config["webhook_url"])
                elif channel == "teams":
                    teams_config = channel_manager.config.get("teams", {})
                    if teams_config.get("enabled", False) and teams_config.get("webhook_url"):
                        from ..notifications.notifier import TeamsNotifier
                        channel_manager.notifiers["teams"] = TeamsNotifier(teams_config["webhook_url"])
        
        return {
            "success": True,
            "channel": channel,
            "enabled": True,
            "message": f"Channel {channel} enabled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling channel {channel}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enable channel: {str(e)}")


@router.post("/disable-channel")
async def disable_channel(
    channel: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Disable a notification channel.
    
    Args:
        channel: The channel to disable (email, slack, teams)
        current_user: Current authenticated user
        
    Returns:
        Dictionary with operation result
    """
    try:
        # Check if user has admin permissions
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Admin permissions required")
        
        if channel not in ["email", "slack", "teams"]:
            raise HTTPException(status_code=400, detail=f"Invalid channel: {channel}")
        
        # Update configuration
        if channel in channel_manager.config:
            channel_manager.config[channel]["enabled"] = False
            
            # Remove notifier if present
            if channel in channel_manager.notifiers:
                del channel_manager.notifiers[channel]
        
        return {
            "success": True,
            "channel": channel,
            "enabled": False,
            "message": f"Channel {channel} disabled successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling channel {channel}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to disable channel: {str(e)}")


@router.get("/health")
async def channel_health_check() -> Dict[str, Any]:
    """
    Perform a health check on all notification channels.
    
    Returns:
        Dictionary with health check results
    """
    try:
        # Get channel status
        status = channel_manager.get_channel_status()
        
        # Test connectivity
        connectivity = await channel_manager.test_channel_connectivity()
        
        # Calculate overall health
        total_channels = len(status)
        available_channels = sum(1 for s in status.values() if s["available"])
        working_channels = sum(1 for success in connectivity.values() if success)
        
        overall_health = "healthy" if working_channels == total_channels else "degraded" if working_channels > 0 else "unhealthy"
        
        return {
            "success": True,
            "health": overall_health,
            "summary": {
                "total_channels": total_channels,
                "available_channels": available_channels,
                "working_channels": working_channels
            },
            "status": status,
            "connectivity": connectivity,
            "message": f"Health check completed: {working_channels}/{total_channels} channels working"
        }
    except Exception as e:
        logger.error(f"Error performing health check: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") 