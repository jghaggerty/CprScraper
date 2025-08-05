"""
Notification History and Management Service

This module provides comprehensive functionality for managing notification history,
including filtering, searching, bulk operations, and administrative functions.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc, func
from sqlalchemy.sql import text

from ..database.connection import get_db
from ..database.models import (
    Notification, FormChange, User, UserRole, Role, 
    Agency, Form, UserNotificationPreference
)
from .delivery_tracker import NotificationDeliveryTracker, DeliveryStatus
from .enhanced_notifier import EnhancedNotificationManager

logger = logging.getLogger(__name__)


class NotificationHistoryManager:
    """Manages notification history and provides administrative functions."""
    
    def __init__(self):
        self.delivery_tracker = NotificationDeliveryTracker()
        self.notification_manager = EnhancedNotificationManager()
    
    async def get_notification_history(
        self,
        db: Session,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "sent_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get paginated notification history with filtering and sorting.
        
        Args:
            db: Database session
            filters: Dictionary of filter criteria
            page: Page number (1-based)
            page_size: Number of records per page
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
        
        Returns:
            Dictionary with notifications and pagination info
        """
        try:
            # Build query
            query = db.query(Notification).join(FormChange)
            
            # Apply filters
            if filters:
                query = self._apply_filters(query, filters)
            
            # Get total count
            total_count = query.count()
            
            # Apply sorting
            if sort_order.lower() == "desc":
                query = query.order_by(desc(getattr(Notification, sort_by)))
            else:
                query = query.order_by(asc(getattr(Notification, sort_by)))
            
            # Apply pagination
            offset = (page - 1) * page_size
            notifications = query.offset(offset).limit(page_size).all()
            
            # Format results
            notification_list = []
            for notification in notifications:
                notification_data = await self._format_notification_data(notification, db)
                notification_list.append(notification_data)
            
            return {
                "notifications": notification_list,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "has_next": page * page_size < total_count,
                    "has_prev": page > 1
                }
            }
        except Exception as e:
            logger.error(f"Error retrieving notification history: {str(e)}")
            raise
    
    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to the query."""
        if filters.get("status"):
            status_list = filters["status"] if isinstance(filters["status"], list) else [filters["status"]]
            query = query.filter(Notification.status.in_(status_list))
        
        if filters.get("notification_type"):
            type_list = filters["notification_type"] if isinstance(filters["notification_type"], list) else [filters["notification_type"]]
            query = query.filter(Notification.notification_type.in_(type_list))
        
        if filters.get("recipient"):
            query = query.filter(Notification.recipient.ilike(f"%{filters['recipient']}%"))
        
        if filters.get("subject"):
            query = query.filter(Notification.subject.ilike(f"%{filters['subject']}%"))
        
        if filters.get("start_date"):
            query = query.filter(Notification.sent_at >= filters["start_date"])
        
        if filters.get("end_date"):
            query = query.filter(Notification.sent_at <= filters["end_date"])
        
        if filters.get("form_change_id"):
            query = query.filter(Notification.form_change_id == filters["form_change_id"])
        
        if filters.get("agency_id"):
            query = query.join(FormChange).join(Form).filter(Form.agency_id == filters["agency_id"])
        
        if filters.get("form_id"):
            query = query.join(FormChange).filter(FormChange.form_id == filters["form_id"])
        
        if filters.get("severity"):
            severity_list = filters["severity"] if isinstance(filters["severity"], list) else [filters["severity"]]
            query = query.join(FormChange).filter(FormChange.severity.in_(severity_list))
        
        if filters.get("retry_count_min"):
            query = query.filter(Notification.retry_count >= filters["retry_count_min"])
        
        if filters.get("retry_count_max"):
            query = query.filter(Notification.retry_count <= filters["retry_count_max"])
        
        return query
    
    async def _format_notification_data(self, notification: Notification, db: Session) -> Dict[str, Any]:
        """Format notification data for API response."""
        # Get related data
        form_change = db.query(FormChange).filter(FormChange.id == notification.form_change_id).first()
        form = None
        agency = None
        
        if form_change:
            form = db.query(Form).filter(Form.id == form_change.form_id).first()
            if form:
                agency = db.query(Agency).filter(Agency.id == form.agency_id).first()
        
        return {
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
            "updated_at": notification.updated_at.isoformat() if notification.updated_at else None,
            "form_change": {
                "change_type": form_change.change_type if form_change else None,
                "change_description": form_change.change_description if form_change else None,
                "severity": form_change.severity if form_change else None,
                "detected_at": form_change.detected_at.isoformat() if form_change and form_change.detected_at else None
            } if form_change else None,
            "form": {
                "name": form.name if form else None,
                "title": form.title if form else None
            } if form else None,
            "agency": {
                "name": agency.name if agency else None,
                "abbreviation": agency.abbreviation if agency else None
            } if agency else None
        }
    
    async def search_notifications(
        self,
        db: Session,
        search_term: str,
        search_fields: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """
        Search notifications across multiple fields.
        
        Args:
            db: Database session
            search_term: Search term to look for
            search_fields: List of fields to search in (default: all text fields)
            page: Page number
            page_size: Number of records per page
        
        Returns:
            Dictionary with search results and pagination info
        """
        try:
            if not search_fields:
                search_fields = ["recipient", "subject", "message", "error_message"]
            
            # Build search query
            search_conditions = []
            for field in search_fields:
                if hasattr(Notification, field):
                    search_conditions.append(getattr(Notification, field).ilike(f"%{search_term}%"))
            
            # Also search in related form change data
            search_conditions.append(FormChange.change_description.ilike(f"%{search_term}%"))
            
            query = db.query(Notification).join(FormChange).filter(or_(*search_conditions))
            
            # Get total count
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * page_size
            notifications = query.order_by(desc(Notification.sent_at)).offset(offset).limit(page_size).all()
            
            # Format results
            notification_list = []
            for notification in notifications:
                notification_data = await self._format_notification_data(notification, db)
                notification_list.append(notification_data)
            
            return {
                "notifications": notification_list,
                "search_term": search_term,
                "search_fields": search_fields,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": (total_count + page_size - 1) // page_size,
                    "has_next": page * page_size < total_count,
                    "has_prev": page > 1
                }
            }
        except Exception as e:
            logger.error(f"Error searching notifications: {str(e)}")
            raise
    
    async def get_notification_analytics(
        self,
        db: Session,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = "day"
    ) -> Dict[str, Any]:
        """
        Get notification analytics and trends.
        
        Args:
            db: Database session
            start_date: Start date for analytics
            end_date: End date for analytics
            group_by: Grouping interval ('hour', 'day', 'week', 'month')
        
        Returns:
            Dictionary with analytics data
        """
        try:
            # Build base query
            query = db.query(Notification)
            
            if start_date:
                query = query.filter(Notification.sent_at >= start_date)
            if end_date:
                query = query.filter(Notification.sent_at <= end_date)
            
            # Get overall statistics
            total_notifications = query.count()
            delivered_count = query.filter(Notification.status == "delivered").count()
            failed_count = query.filter(Notification.status == "failed").count()
            retrying_count = query.filter(Notification.status == "retrying").count()
            
            # Get status distribution
            status_distribution = db.query(
                Notification.status,
                func.count(Notification.id).label('count')
            ).filter(
                Notification.sent_at >= start_date if start_date else True,
                Notification.sent_at <= end_date if end_date else True
            ).group_by(Notification.status).all()
            
            # Get channel distribution
            channel_distribution = db.query(
                Notification.notification_type,
                func.count(Notification.id).label('count')
            ).filter(
                Notification.sent_at >= start_date if start_date else True,
                Notification.sent_at <= end_date if end_date else True
            ).group_by(Notification.notification_type).all()
            
            # Get time-based trends
            if group_by == "hour":
                time_format = "%Y-%m-%d %H:00:00"
            elif group_by == "day":
                time_format = "%Y-%m-%d"
            elif group_by == "week":
                time_format = "%Y-%u"
            elif group_by == "month":
                time_format = "%Y-%m"
            else:
                time_format = "%Y-%m-%d"
            
            time_trends = db.query(
                func.strftime(time_format, Notification.sent_at).label('time_period'),
                func.count(Notification.id).label('count')
            ).filter(
                Notification.sent_at >= start_date if start_date else True,
                Notification.sent_at <= end_date if end_date else True
            ).group_by(text('time_period')).order_by(text('time_period')).all()
            
            # Get top recipients
            top_recipients = db.query(
                Notification.recipient,
                func.count(Notification.id).label('count')
            ).filter(
                Notification.sent_at >= start_date if start_date else True,
                Notification.sent_at <= end_date if end_date else True
            ).group_by(Notification.recipient).order_by(desc(text('count'))).limit(10).all()
            
            # Get average delivery times
            avg_delivery_time = db.query(
                func.avg(Notification.delivery_time)
            ).filter(
                Notification.delivery_time.isnot(None),
                Notification.sent_at >= start_date if start_date else True,
                Notification.sent_at <= end_date if end_date else True
            ).scalar()
            
            return {
                "overview": {
                    "total_notifications": total_notifications,
                    "delivered_count": delivered_count,
                    "failed_count": failed_count,
                    "retrying_count": retrying_count,
                    "success_rate": (delivered_count / total_notifications * 100) if total_notifications > 0 else 0,
                    "average_delivery_time_seconds": float(avg_delivery_time) if avg_delivery_time else 0
                },
                "status_distribution": [
                    {"status": status, "count": count} for status, count in status_distribution
                ],
                "channel_distribution": [
                    {"channel": channel, "count": count} for channel, count in channel_distribution
                ],
                "time_trends": [
                    {"time_period": period, "count": count} for period, count in time_trends
                ],
                "top_recipients": [
                    {"recipient": recipient, "count": count} for recipient, count in top_recipients
                ]
            }
        except Exception as e:
            logger.error(f"Error getting notification analytics: {str(e)}")
            raise
    
    async def resend_notification(
        self,
        db: Session,
        notification_id: int,
        user: User
    ) -> Dict[str, Any]:
        """
        Resend a failed notification.
        
        Args:
            db: Database session
            notification_id: ID of the notification to resend
            user: Current user performing the action
        
        Returns:
            Dictionary with resend result
        """
        try:
            # Get the original notification
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if not notification:
                raise ValueError(f"Notification with ID {notification_id} not found")
            
            # Check if notification can be resent
            if notification.status not in ["failed", "expired"]:
                raise ValueError(f"Cannot resend notification with status '{notification.status}'")
            
            # Create a new notification record for the resend
            new_notification = Notification(
                form_change_id=notification.form_change_id,
                notification_type=notification.notification_type,
                recipient=notification.recipient,
                subject=notification.subject,
                message=notification.message,
                status="pending",
                retry_count=0
            )
            
            db.add(new_notification)
            db.commit()
            db.refresh(new_notification)
            
            # Attempt to send the notification
            success = await self.delivery_tracker.track_notification_delivery(
                new_notification.id,
                notification.notification_type,
                notification.recipient,
                notification.subject,
                notification.message,
                db
            )
            
            # Update the original notification to mark it as replaced
            notification.status = "replaced"
            notification.error_message = f"Replaced by resend (ID: {new_notification.id}) by user {user.username}"
            db.commit()
            
            return {
                "success": True,
                "original_notification_id": notification_id,
                "new_notification_id": new_notification.id,
                "resend_success": success
            }
        except Exception as e:
            logger.error(f"Error resending notification {notification_id}: {str(e)}")
            db.rollback()
            raise
    
    async def cancel_notification(
        self,
        db: Session,
        notification_id: int,
        user: User,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel a pending or retrying notification.
        
        Args:
            db: Database session
            notification_id: ID of the notification to cancel
            user: Current user performing the action
            reason: Optional reason for cancellation
        
        Returns:
            Dictionary with cancellation result
        """
        try:
            notification = db.query(Notification).filter(Notification.id == notification_id).first()
            if not notification:
                raise ValueError(f"Notification with ID {notification_id} not found")
            
            if notification.status not in ["pending", "retrying"]:
                raise ValueError(f"Cannot cancel notification with status '{notification.status}'")
            
            # Cancel the notification
            notification.status = "cancelled"
            notification.error_message = f"Cancelled by {user.username}"
            if reason:
                notification.error_message += f" - Reason: {reason}"
            
            db.commit()
            
            return {
                "success": True,
                "notification_id": notification_id,
                "status": "cancelled",
                "cancelled_by": user.username,
                "cancelled_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error cancelling notification {notification_id}: {str(e)}")
            db.rollback()
            raise
    
    async def bulk_operations(
        self,
        db: Session,
        operation: str,
        notification_ids: List[int],
        user: User,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform bulk operations on notifications.
        
        Args:
            db: Database session
            operation: Operation to perform ('resend', 'cancel', 'archive')
            notification_ids: List of notification IDs to operate on
            user: Current user performing the action
            **kwargs: Additional arguments for the operation
        
        Returns:
            Dictionary with bulk operation results
        """
        try:
            results = {
                "operation": operation,
                "total_requested": len(notification_ids),
                "successful": 0,
                "failed": 0,
                "errors": []
            }
            
            for notification_id in notification_ids:
                try:
                    if operation == "resend":
                        result = await self.resend_notification(db, notification_id, user)
                        if result["success"]:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Failed to resend notification {notification_id}")
                    
                    elif operation == "cancel":
                        result = await self.cancel_notification(
                            db, notification_id, user, kwargs.get("reason")
                        )
                        if result["success"]:
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Failed to cancel notification {notification_id}")
                    
                    elif operation == "archive":
                        # Archive operation (mark as archived)
                        notification = db.query(Notification).filter(Notification.id == notification_id).first()
                        if notification:
                            notification.status = "archived"
                            notification.error_message = f"Archived by {user.username}"
                            results["successful"] += 1
                        else:
                            results["failed"] += 1
                            results["errors"].append(f"Notification {notification_id} not found")
                    
                    else:
                        results["failed"] += 1
                        results["errors"].append(f"Unknown operation: {operation}")
                
                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append(f"Error processing notification {notification_id}: {str(e)}")
            
            db.commit()
            return results
        
        except Exception as e:
            logger.error(f"Error performing bulk operation {operation}: {str(e)}")
            db.rollback()
            raise
    
    async def get_user_notification_preferences(
        self,
        db: Session,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Get notification preferences for a specific user.
        
        Args:
            db: Database session
            user_id: ID of the user
        
        Returns:
            Dictionary with user notification preferences
        """
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError(f"User with ID {user_id} not found")
            
            # Get user roles
            user_roles = db.query(UserRole).join(Role).filter(
                UserRole.user_id == user_id,
                UserRole.is_active == True
            ).all()
            
            # Get notification preferences
            preferences = db.query(UserNotificationPreference).filter(
                UserNotificationPreference.user_id == user_id
            ).all()
            
            return {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                },
                "roles": [
                    {
                        "id": user_role.role.id,
                        "name": user_role.role.name,
                        "display_name": user_role.role.display_name
                    }
                    for user_role in user_roles
                ],
                "notification_preferences": [
                    {
                        "id": pref.id,
                        "notification_type": pref.notification_type,
                        "change_severity": pref.change_severity,
                        "frequency": pref.frequency,
                        "is_enabled": pref.is_enabled
                    }
                    for pref in preferences
                ]
            }
        except Exception as e:
            logger.error(f"Error getting user notification preferences: {str(e)}")
            raise
    
    async def export_notification_history(
        self,
        db: Session,
        filters: Optional[Dict[str, Any]] = None,
        format: str = "csv"
    ) -> Dict[str, Any]:
        """
        Export notification history in various formats.
        
        Args:
            db: Database session
            filters: Filter criteria
            format: Export format ('csv', 'json', 'excel')
        
        Returns:
            Dictionary with export data
        """
        try:
            # Get all notifications matching filters
            query = db.query(Notification).join(FormChange)
            if filters:
                query = self._apply_filters(query, filters)
            
            notifications = query.order_by(desc(Notification.sent_at)).all()
            
            # Format data for export
            export_data = []
            for notification in notifications:
                notification_data = await self._format_notification_data(notification, db)
                export_data.append(notification_data)
            
            # Generate export based on format
            if format.lower() == "csv":
                return await self._generate_csv_export(export_data)
            elif format.lower() == "json":
                return await self._generate_json_export(export_data)
            elif format.lower() == "excel":
                return await self._generate_excel_export(export_data)
            else:
                raise ValueError(f"Unsupported export format: {format}")
        
        except Exception as e:
            logger.error(f"Error exporting notification history: {str(e)}")
            raise
    
    async def _generate_csv_export(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate CSV export data."""
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "id", "form_change_id", "notification_type", "recipient", "subject",
            "status", "sent_at", "retry_count", "delivery_time", "error_message"
        ])
        
        writer.writeheader()
        for item in data:
            writer.writerow({
                "id": item["id"],
                "form_change_id": item["form_change_id"],
                "notification_type": item["notification_type"],
                "recipient": item["recipient"],
                "subject": item["subject"],
                "status": item["status"],
                "sent_at": item["sent_at"],
                "retry_count": item["retry_count"],
                "delivery_time": item["delivery_time"],
                "error_message": item["error_message"]
            })
        
        return {
            "format": "csv",
            "data": output.getvalue(),
            "filename": f"notification_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    
    async def _generate_json_export(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate JSON export data."""
        import json
        
        return {
            "format": "json",
            "data": json.dumps(data, indent=2, default=str),
            "filename": f"notification_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        }
    
    async def _generate_excel_export(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate Excel export data."""
        try:
            import pandas as pd
            from io import BytesIO
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Create Excel file in memory
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Notification History', index=False)
            
            output.seek(0)
            
            return {
                "format": "excel",
                "data": output.getvalue(),
                "filename": f"notification_history_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            }
        except ImportError:
            raise ValueError("pandas and openpyxl are required for Excel export") 