"""
API endpoints for notification history and management interface.

This module provides comprehensive endpoints for managing notification history,
including filtering, searching, bulk operations, and administrative functions.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import io

from ..database.connection import get_db
from ..database.models import User
from ..notifications.history_manager import NotificationHistoryManager
from ..auth.auth import get_current_user

router = APIRouter(prefix="/api/notification-management", tags=["notification-management"])


@router.get("/history")
async def get_notification_history(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of records per page"),
    sort_by: str = Query("sent_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc or desc)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    recipient: Optional[str] = Query(None, description="Filter by recipient"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    form_change_id: Optional[int] = Query(None, description="Filter by form change ID"),
    agency_id: Optional[int] = Query(None, description="Filter by agency ID"),
    form_id: Optional[int] = Query(None, description="Filter by form ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    retry_count_min: Optional[int] = Query(None, description="Minimum retry count"),
    retry_count_max: Optional[int] = Query(None, description="Maximum retry count"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get paginated notification history with filtering and sorting."""
    try:
        history_manager = NotificationHistoryManager()
        
        # Build filters dictionary
        filters = {}
        if status:
            filters["status"] = status
        if notification_type:
            filters["notification_type"] = notification_type
        if recipient:
            filters["recipient"] = recipient
        if subject:
            filters["subject"] = subject
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        if form_change_id:
            filters["form_change_id"] = form_change_id
        if agency_id:
            filters["agency_id"] = agency_id
        if form_id:
            filters["form_id"] = form_id
        if severity:
            filters["severity"] = severity
        if retry_count_min is not None:
            filters["retry_count_min"] = retry_count_min
        if retry_count_max is not None:
            filters["retry_count_max"] = retry_count_max
        
        result = await history_manager.get_notification_history(
            db=db,
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving notification history: {str(e)}")


@router.get("/search")
async def search_notifications(
    search_term: str = Query(..., description="Search term"),
    search_fields: Optional[str] = Query(None, description="Comma-separated list of fields to search"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Number of records per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search notifications across multiple fields."""
    try:
        history_manager = NotificationHistoryManager()
        
        # Parse search fields
        fields_list = None
        if search_fields:
            fields_list = [field.strip() for field in search_fields.split(",")]
        
        result = await history_manager.search_notifications(
            db=db,
            search_term=search_term,
            search_fields=fields_list,
            page=page,
            page_size=page_size
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching notifications: {str(e)}")


@router.get("/analytics")
async def get_notification_analytics(
    start_date: Optional[datetime] = Query(None, description="Start date for analytics"),
    end_date: Optional[datetime] = Query(None, description="End date for analytics"),
    group_by: str = Query("day", description="Grouping interval (hour, day, week, month)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification analytics and trends."""
    try:
        history_manager = NotificationHistoryManager()
        
        result = await history_manager.get_notification_analytics(
            db=db,
            start_date=start_date,
            end_date=end_date,
            group_by=group_by
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving analytics: {str(e)}")


@router.post("/resend/{notification_id}")
async def resend_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resend a failed notification."""
    try:
        history_manager = NotificationHistoryManager()
        
        result = await history_manager.resend_notification(
            db=db,
            notification_id=notification_id,
            user=current_user
        )
        
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resending notification: {str(e)}")


@router.post("/cancel/{notification_id}")
async def cancel_notification(
    notification_id: int,
    reason: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel a pending or retrying notification."""
    try:
        history_manager = NotificationHistoryManager()
        
        result = await history_manager.cancel_notification(
            db=db,
            notification_id=notification_id,
            user=current_user,
            reason=reason
        )
        
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling notification: {str(e)}")


@router.post("/bulk-operations")
async def perform_bulk_operations(
    operation: str = Body(..., description="Operation to perform (resend, cancel, archive)"),
    notification_ids: List[int] = Body(..., description="List of notification IDs"),
    reason: Optional[str] = Body(None, description="Reason for cancellation (for cancel operation)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Perform bulk operations on notifications."""
    try:
        if not notification_ids:
            raise HTTPException(status_code=400, detail="No notification IDs provided")
        
        if operation not in ["resend", "cancel", "archive"]:
            raise HTTPException(status_code=400, detail="Invalid operation. Must be one of: resend, cancel, archive")
        
        history_manager = NotificationHistoryManager()
        
        kwargs = {}
        if operation == "cancel" and reason:
            kwargs["reason"] = reason
        
        result = await history_manager.bulk_operations(
            db=db,
            operation=operation,
            notification_ids=notification_ids,
            user=current_user,
            **kwargs
        )
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing bulk operation: {str(e)}")


@router.get("/user-preferences/{user_id}")
async def get_user_notification_preferences(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get notification preferences for a specific user."""
    try:
        # Check if current user has permission to view other user's preferences
        if current_user.id != user_id and not current_user.is_superuser:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        history_manager = NotificationHistoryManager()
        
        result = await history_manager.get_user_notification_preferences(
            db=db,
            user_id=user_id
        )
        
        return {
            "success": True,
            "data": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user preferences: {str(e)}")


@router.get("/export")
async def export_notification_history(
    format: str = Query("csv", description="Export format (csv, json, excel)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    notification_type: Optional[str] = Query(None, description="Filter by notification type"),
    recipient: Optional[str] = Query(None, description="Filter by recipient"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export notification history in various formats."""
    try:
        if format.lower() not in ["csv", "json", "excel"]:
            raise HTTPException(status_code=400, detail="Invalid format. Must be one of: csv, json, excel")
        
        history_manager = NotificationHistoryManager()
        
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if notification_type:
            filters["notification_type"] = notification_type
        if recipient:
            filters["recipient"] = recipient
        if start_date:
            filters["start_date"] = start_date
        if end_date:
            filters["end_date"] = end_date
        
        result = await history_manager.export_notification_history(
            db=db,
            filters=filters,
            format=format
        )
        
        # Create streaming response for file download
        if format.lower() == "csv":
            return StreamingResponse(
                io.StringIO(result["data"]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
            )
        elif format.lower() == "json":
            return StreamingResponse(
                io.StringIO(result["data"]),
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
            )
        elif format.lower() == "excel":
            return StreamingResponse(
                io.BytesIO(result["data"]),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={result['filename']}"}
            )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting notification history: {str(e)}")


@router.get("/filters/options")
async def get_filter_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get available filter options for the notification history interface."""
    try:
        from ..database.models import Agency, Form
        
        # Get available statuses
        statuses = ["pending", "sending", "delivered", "failed", "bounced", "retrying", "expired", "cancelled", "archived"]
        
        # Get available notification types
        notification_types = ["email", "slack", "teams", "webhook"]
        
        # Get available agencies
        agencies = db.query(Agency).filter(Agency.is_active == True).all()
        agency_options = [{"id": agency.id, "name": agency.name, "abbreviation": agency.abbreviation} for agency in agencies]
        
        # Get available forms
        forms = db.query(Form).filter(Form.is_active == True).all()
        form_options = [{"id": form.id, "name": form.name, "title": form.title} for form in forms]
        
        # Get available severities
        severities = ["low", "medium", "high", "critical"]
        
        return {
            "success": True,
            "data": {
                "statuses": statuses,
                "notification_types": notification_types,
                "agencies": agency_options,
                "forms": form_options,
                "severities": severities
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving filter options: {str(e)}")


@router.get("/stats/summary")
async def get_management_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get summary statistics for the notification management interface."""
    try:
        from sqlalchemy import func
        from ..database.models import Notification
        
        # Get overall counts
        total_notifications = db.query(func.count(Notification.id)).scalar()
        pending_count = db.query(func.count(Notification.id)).filter(Notification.status == "pending").scalar()
        failed_count = db.query(func.count(Notification.id)).filter(Notification.status == "failed").scalar()
        retrying_count = db.query(func.count(Notification.id)).filter(Notification.status == "retrying").scalar()
        
        # Get recent activity (last 24 hours)
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        recent_count = db.query(func.count(Notification.id)).filter(Notification.sent_at >= yesterday).scalar()
        
        # Get average delivery time
        avg_delivery_time = db.query(func.avg(Notification.delivery_time)).filter(
            Notification.delivery_time.isnot(None)
        ).scalar()
        
        return {
            "success": True,
            "data": {
                "total_notifications": total_notifications,
                "pending_count": pending_count,
                "failed_count": failed_count,
                "retrying_count": retrying_count,
                "recent_24h_count": recent_count,
                "average_delivery_time_seconds": float(avg_delivery_time) if avg_delivery_time else 0
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving summary stats: {str(e)}")


@router.get("/notifications/{notification_id}/details")
async def get_notification_details(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific notification."""
    try:
        from ..database.models import Notification, FormChange, Form, Agency
        
        notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Get related data
        form_change = db.query(FormChange).filter(FormChange.id == notification.form_change_id).first()
        form = None
        agency = None
        
        if form_change:
            form = db.query(Form).filter(Form.id == form_change.form_id).first()
            if form:
                agency = db.query(Agency).filter(Agency.id == form.agency_id).first()
        
        # Format detailed response
        details = {
            "notification": {
                "id": notification.id,
                "form_change_id": notification.form_change_id,
                "notification_type": notification.notification_type,
                "recipient": notification.recipient,
                "subject": notification.subject,
                "message": notification.message,
                "sent_at": notification.sent_at.isoformat() if notification.sent_at else None,
                "status": notification.status,
                "error_message": notification.error_message,
                "retry_count": notification.retry_count,
                "delivery_time": notification.delivery_time,
                "response_data": notification.response_data,
                "created_at": notification.created_at.isoformat() if notification.created_at else None,
                "updated_at": notification.updated_at.isoformat() if notification.updated_at else None
            },
            "form_change": {
                "id": form_change.id if form_change else None,
                "change_type": form_change.change_type if form_change else None,
                "change_description": form_change.change_description if form_change else None,
                "old_value": form_change.old_value if form_change else None,
                "new_value": form_change.new_value if form_change else None,
                "severity": form_change.severity if form_change else None,
                "detected_at": form_change.detected_at.isoformat() if form_change and form_change.detected_at else None,
                "ai_confidence_score": form_change.ai_confidence_score if form_change else None,
                "ai_change_category": form_change.ai_change_category if form_change else None
            } if form_change else None,
            "form": {
                "id": form.id if form else None,
                "name": form.name if form else None,
                "title": form.title if form else None,
                "form_url": form.form_url if form else None
            } if form else None,
            "agency": {
                "id": agency.id if agency else None,
                "name": agency.name if agency else None,
                "abbreviation": agency.abbreviation if agency else None,
                "agency_type": agency.agency_type if agency else None
            } if agency else None
        }
        
        return {
            "success": True,
            "data": details
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving notification details: {str(e)}") 