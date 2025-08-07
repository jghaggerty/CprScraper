"""
Enhanced Dashboard API for Compliance Monitoring

Provides comprehensive API endpoints for the compliance monitoring dashboard,
including filtering, search, real-time status, and statistics.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
import logging

from ..database.connection import get_db
from ..database.models import (
    Agency, Form, FormChange, MonitoringRun, Notification,
    Client, ClientFormUsage, WorkItem
)
from ..monitors.monitoring_statistics import MonitoringStatistics, get_monitoring_statistics
from ..monitors.error_handler import GovernmentWebsiteErrorHandler
from ..utils.export_utils import export_manager, export_scheduler

# Initialize logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# Pydantic models for enhanced dashboard responses
class DashboardStats(BaseModel):
    """Comprehensive dashboard statistics."""
    total_agencies: int
    total_forms: int
    active_forms: int
    total_changes: int
    changes_last_24h: int
    changes_last_week: int
    changes_last_month: int
    critical_changes: int
    high_priority_changes: int
    pending_notifications: int
    active_work_items: int
    last_monitoring_run: Optional[datetime]
    system_health: str
    coverage_percentage: float

class ChangeSummary(BaseModel):
    """Summary of form changes for dashboard."""
    id: int
    form_name: str
    agency_name: str
    agency_type: str
    change_type: str
    severity: str
    status: str
    detected_at: datetime
    ai_confidence_score: Optional[int]
    ai_change_category: Optional[str]
    is_cosmetic_change: bool
    impact_assessment: Optional[Dict[str, Any]]

class AgencySummary(BaseModel):
    """Summary of agency monitoring status."""
    id: int
    name: str
    agency_type: str
    total_forms: int
    active_forms: int
    last_check: Optional[datetime]
    changes_last_week: int
    health_status: str

class FormSummary(BaseModel):
    """Summary of form monitoring status."""
    id: int
    name: str
    title: str
    agency_name: str
    check_frequency: str
    last_checked: Optional[datetime]
    last_modified: Optional[datetime]
    total_changes: int
    status: str

class MonitoringHealth(BaseModel):
    """System monitoring health status."""
    overall_status: str
    active_monitors: int
    error_rate: float
    avg_response_time: float
    last_successful_run: Optional[datetime]
    circuit_breakers_active: int
    coverage_stats: Dict[str, Any]

class FilterOptions(BaseModel):
    """Available filter options for dashboard."""
    states: List[str]
    agencies: List[str]
    form_types: List[str]
    severity_levels: List[str]
    status_options: List[str]
    date_ranges: List[str]

class SearchRequest(BaseModel):
    """Search request for dashboard data."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = "detected_at"
    sort_order: Optional[str] = "desc"
    page: Optional[int] = 1
    page_size: Optional[int] = 50

class SearchResponse(BaseModel):
    """Search response with pagination."""
    results: List[ChangeSummary]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    filters_applied: Dict[str, Any]


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get comprehensive dashboard statistics."""
    try:
        # Get basic counts
        total_agencies = db.query(Agency).filter(Agency.is_active == True).count()
        total_forms = db.query(Form).filter(Form.is_active == True).count()
        active_forms = db.query(Form).filter(
            and_(Form.is_active == True, Form.last_checked.isnot(None))
        ).count()
        
        # Get change statistics
        now = datetime.now(timezone.utc)
        changes_last_24h = db.query(FormChange).filter(
            FormChange.detected_at >= now - timedelta(days=1)
        ).count()
        changes_last_week = db.query(FormChange).filter(
            FormChange.detected_at >= now - timedelta(days=7)
        ).count()
        changes_last_month = db.query(FormChange).filter(
            FormChange.detected_at >= now - timedelta(days=30)
        ).count()
        total_changes = db.query(FormChange).count()
        
        # Get severity-based counts
        critical_changes = db.query(FormChange).filter(
            FormChange.severity == "critical"
        ).count()
        high_priority_changes = db.query(FormChange).filter(
            FormChange.severity.in_(["critical", "high"])
        ).count()
        
        # Get notification and work item counts
        pending_notifications = db.query(Notification).filter(
            Notification.status == "pending"
        ).count()
        active_work_items = db.query(WorkItem).filter(
            WorkItem.status.in_(["new", "in_progress"])
        ).count()
        
        # Get last monitoring run
        last_run = db.query(MonitoringRun).order_by(
            desc(MonitoringRun.started_at)
        ).first()
        last_monitoring_run = last_run.started_at if last_run else None
        
        # Calculate coverage percentage
        coverage_percentage = (active_forms / total_forms * 100) if total_forms > 0 else 0
        
        # Determine system health
        system_health = "healthy"
        if error_rate := _calculate_error_rate(db):
            if error_rate > 0.1:  # 10% error rate
                system_health = "degraded"
            elif error_rate > 0.25:  # 25% error rate
                system_health = "critical"
        
        return DashboardStats(
            total_agencies=total_agencies,
            total_forms=total_forms,
            active_forms=active_forms,
            total_changes=total_changes,
            changes_last_24h=changes_last_24h,
            changes_last_week=changes_last_week,
            changes_last_month=changes_last_month,
            critical_changes=critical_changes,
            high_priority_changes=high_priority_changes,
            pending_notifications=pending_notifications,
            active_work_items=active_work_items,
            last_monitoring_run=last_monitoring_run,
            system_health=system_health,
            coverage_percentage=round(coverage_percentage, 2)
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard statistics")


@router.get("/changes", response_model=List[ChangeSummary])
async def get_recent_changes(
    limit: int = Query(10, ge=1, le=100),
    agency_id: Optional[int] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    days: Optional[int] = 7,
    db: Session = Depends(get_db)
):
    """Get recent form changes with filtering options."""
    try:
        query = db.query(FormChange).options(
            joinedload(FormChange.form).joinedload(Form.agency)
        )
        
        # Apply filters
        if agency_id:
            query = query.join(Form).filter(Form.agency_id == agency_id)
        
        if severity:
            query = query.filter(FormChange.severity == severity)
        
        if status:
            query = query.filter(FormChange.status == status)
        
        if days:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = query.filter(FormChange.detected_at >= cutoff_date)
        
        # Get results
        changes = query.order_by(desc(FormChange.detected_at)).limit(limit).all()
        
        return [
            ChangeSummary(
                id=change.id,
                form_name=change.form.name,
                agency_name=change.form.agency.name,
                agency_type=change.form.agency.agency_type,
                change_type=change.change_type,
                severity=change.severity,
                status=change.status,
                detected_at=change.detected_at,
                ai_confidence_score=change.ai_confidence_score,
                ai_change_category=change.ai_change_category,
                is_cosmetic_change=change.is_cosmetic_change,
                impact_assessment=change.impact_assessment
            )
            for change in changes
        ]
    except Exception as e:
        logger.error(f"Error getting recent changes: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent changes")


@router.get("/agencies", response_model=List[AgencySummary])
async def get_agency_summaries(db: Session = Depends(get_db)):
    """Get summary of all agencies with monitoring status."""
    try:
        agencies = db.query(Agency).filter(Agency.is_active == True).all()
        
        summaries = []
        for agency in agencies:
            # Get form counts
            total_forms = len(agency.forms)
            active_forms = len([f for f in agency.forms if f.is_active])
            
            # Get last check time
            last_check = None
            if agency.forms:
                last_check = max(
                    (f.last_checked for f in agency.forms if f.last_checked),
                    default=None
                )
            
            # Get changes in last week
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            changes_last_week = db.query(FormChange).join(Form).filter(
                and_(
                    Form.agency_id == agency.id,
                    FormChange.detected_at >= week_ago
                )
            ).count()
            
            # Determine health status
            health_status = "healthy"
            if not last_check or last_check < datetime.now(timezone.utc) - timedelta(days=7):
                health_status = "warning"
            if changes_last_week > 10:  # High change volume
                health_status = "alert"
            
            summaries.append(AgencySummary(
                id=agency.id,
                name=agency.name,
                agency_type=agency.agency_type,
                total_forms=total_forms,
                active_forms=active_forms,
                last_check=last_check,
                changes_last_week=changes_last_week,
                health_status=health_status
            ))
        
        return summaries
    except Exception as e:
        logger.error(f"Error getting agency summaries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve agency summaries")


@router.get("/forms", response_model=List[FormSummary])
async def get_form_summaries(
    agency_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get summary of forms with monitoring status."""
    try:
        query = db.query(Form).options(joinedload(Form.agency))
        
        if agency_id:
            query = query.filter(Form.agency_id == agency_id)
        
        if status:
            if status == "active":
                query = query.filter(Form.is_active == True)
            elif status == "inactive":
                query = query.filter(Form.is_active == False)
        
        forms = query.all()
        
        summaries = []
        for form in forms:
            # Get total changes
            total_changes = db.query(FormChange).filter(
                FormChange.form_id == form.id
            ).count()
            
            # Determine status
            form_status = "active" if form.is_active else "inactive"
            if not form.last_checked:
                form_status = "never_checked"
            elif form.last_checked < datetime.now(timezone.utc) - timedelta(days=30):
                form_status = "stale"
            
            summaries.append(FormSummary(
                id=form.id,
                name=form.name,
                title=form.title,
                agency_name=form.agency.name,
                check_frequency=form.check_frequency,
                last_checked=form.last_checked,
                last_modified=form.last_modified,
                total_changes=total_changes,
                status=form_status
            ))
        
        return summaries
    except Exception as e:
        logger.error(f"Error getting form summaries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve form summaries")


@router.get("/health", response_model=MonitoringHealth)
async def get_monitoring_health(db: Session = Depends(get_db)):
    """Get comprehensive monitoring system health status."""
    try:
        # Get monitoring statistics
        total_runs = db.query(MonitoringRun).count()
        successful_runs = db.query(MonitoringRun).filter(
            MonitoringRun.status == "completed"
        ).count()
        
        error_rate = 0
        if total_runs > 0:
            error_rate = (total_runs - successful_runs) / total_runs
        
        # Get average response time
        avg_response = db.query(func.avg(MonitoringRun.response_time_ms)).scalar()
        avg_response_time = float(avg_response) if avg_response else 0
        
        # Get last successful run
        last_successful = db.query(MonitoringRun).filter(
            MonitoringRun.status == "completed"
        ).order_by(desc(MonitoringRun.completed_at)).first()
        
        last_successful_run = last_successful.completed_at if last_successful else None
        
        # Get coverage statistics
        total_forms = db.query(Form).filter(Form.is_active == True).count()
        checked_forms = db.query(Form).filter(
            and_(Form.is_active == True, Form.last_checked.isnot(None))
        ).count()
        
        coverage_stats = {
            "total_forms": total_forms,
            "checked_forms": checked_forms,
            "coverage_percentage": round((checked_forms / total_forms * 100), 2) if total_forms > 0 else 0,
            "last_24h_checks": db.query(Form).filter(
                and_(
                    Form.is_active == True,
                    Form.last_checked >= datetime.now(timezone.utc) - timedelta(days=1)
                )
            ).count()
        }
        
        # Determine overall status
        overall_status = "healthy"
        if error_rate > 0.1:
            overall_status = "degraded"
        if error_rate > 0.25 or coverage_stats["coverage_percentage"] < 50:
            overall_status = "critical"
        
        # Get circuit breaker status (placeholder - would integrate with error handler)
        circuit_breakers_active = 0
        
        return MonitoringHealth(
            overall_status=overall_status,
            active_monitors=total_forms,
            error_rate=round(error_rate, 3),
            avg_response_time=round(avg_response_time, 2),
            last_successful_run=last_successful_run,
            circuit_breakers_active=circuit_breakers_active,
            coverage_stats=coverage_stats
        )
    except Exception as e:
        logger.error(f"Error getting monitoring health: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve monitoring health")


@router.get("/monitoring-status")
async def get_real_time_monitoring_status(db: Session = Depends(get_db)):
    """Get real-time monitoring status and active runs."""
    try:
        with get_db() as db:
            # Get active monitoring runs
            active_runs = db.query(MonitoringRun).filter(
                MonitoringRun.status.in_(["running", "pending"])
            ).all()
            
            # Get recent completed runs
            recent_completed = db.query(MonitoringRun).filter(
                and_(
                    MonitoringRun.status == "completed",
                    MonitoringRun.completed_at >= datetime.now(timezone.utc) - timedelta(hours=6)
                )
            ).order_by(desc(MonitoringRun.completed_at)).limit(20).all()
            
            # Get failed runs in last 24 hours
            failed_runs = db.query(MonitoringRun).filter(
                and_(
                    MonitoringRun.status == "failed",
                    MonitoringRun.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                )
            ).order_by(desc(MonitoringRun.created_at)).limit(10).all()
            
            # Get current monitoring statistics
            stats = get_monitoring_statistics()
            current_stats = await stats.get_comprehensive_statistics()
            
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "active_runs": [
                    {
                        "id": run.id,
                        "agency_id": run.agency_id,
                        "form_id": run.form_id,
                        "status": run.status,
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                        "progress": getattr(run, 'progress', 0),
                        "estimated_completion": run.estimated_completion.isoformat() if hasattr(run, 'estimated_completion') and run.estimated_completion else None
                    }
                    for run in active_runs
                ],
                "recent_completed": [
                    {
                        "id": run.id,
                        "agency_id": run.agency_id,
                        "form_id": run.form_id,
                        "status": run.status,
                        "started_at": run.started_at.isoformat() if run.started_at else None,
                        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                        "changes_detected": run.changes_detected,
                        "processing_time_seconds": (run.completed_at - run.started_at).total_seconds() if run.completed_at and run.started_at else None
                    }
                    for run in recent_completed
                ],
                "failed_runs": [
                    {
                        "id": run.id,
                        "agency_id": run.agency_id,
                        "form_id": run.form_id,
                        "status": run.status,
                        "error_message": run.error_message,
                        "created_at": run.created_at.isoformat()
                    }
                    for run in failed_runs
                ],
                "statistics": current_stats,
                "summary": {
                    "total_active": len(active_runs),
                    "total_completed_6h": len(recent_completed),
                    "total_failed_24h": len(failed_runs),
                    "success_rate": len(recent_completed) / (len(recent_completed) + len(failed_runs)) * 100 if (len(recent_completed) + len(failed_runs)) > 0 else 100
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting real-time monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting monitoring status: {str(e)}")


@router.get("/live-statistics")
async def get_live_statistics(db: Session = Depends(get_db)):
    """Get live statistics with real-time updates."""
    try:
        # Get monitoring statistics
        stats = get_monitoring_statistics()
        comprehensive_stats = await stats.get_comprehensive_statistics()
        
        # Get additional real-time metrics
        with get_db() as db:
            # Get changes in last hour
            changes_last_hour = db.query(FormChange).filter(
                FormChange.detected_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).count()
            
            # Get changes in last 15 minutes
            changes_last_15min = db.query(FormChange).filter(
                FormChange.detected_at >= datetime.now(timezone.utc) - timedelta(minutes=15)
            ).count()
            
            # Get critical changes in last hour
            critical_changes_hour = db.query(FormChange).filter(
                and_(
                    FormChange.severity == "critical",
                    FormChange.detected_at >= datetime.now(timezone.utc) - timedelta(hours=1)
                )
            ).count()
            
            # Get active notifications
            active_notifications = db.query(Notification).filter(
                and_(
                    Notification.is_active == True,
                    Notification.created_at >= datetime.now(timezone.utc) - timedelta(days=1)
                )
            ).count()
            
            # Get system performance metrics
            recent_runs = db.query(MonitoringRun).filter(
                MonitoringRun.completed_at >= datetime.now(timezone.utc) - timedelta(hours=1)
            ).all()
            
            avg_processing_time = 0
            if recent_runs:
                total_time = sum([
                    (run.completed_at - run.started_at).total_seconds() 
                    for run in recent_runs 
                    if run.completed_at and run.started_at
                ])
                avg_processing_time = total_time / len(recent_runs)
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "comprehensive_statistics": comprehensive_stats,
            "real_time_metrics": {
                "changes_last_hour": changes_last_hour,
                "changes_last_15min": changes_last_15min,
                "critical_changes_hour": critical_changes_hour,
                "active_notifications": active_notifications,
                "avg_processing_time_seconds": avg_processing_time,
                "system_load": "normal",  # This would be actual system metrics
                "memory_usage": "65%",    # This would be actual system metrics
                "disk_usage": "45%"       # This would be actual system metrics
            },
            "trends": {
                "changes_trend": "increasing" if changes_last_15min > changes_last_hour / 4 else "stable",
                "performance_trend": "improving" if avg_processing_time < 30 else "stable",
                "error_trend": "decreasing" if comprehensive_stats.get("current_metrics", {}).get("error_rates", {}).get("total_errors", 0) < 5 else "stable"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting live statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting live statistics: {str(e)}")


@router.get("/filters", response_model=FilterOptions)
async def get_filter_options(db: Session = Depends(get_db)):
    """Get available filter options for dashboard."""
    try:
        # Get unique states from agencies
        states = db.query(Agency.agency_type).distinct().all()
        states = [state[0] for state in states if state[0]]
        
        # Get agency names
        agencies = db.query(Agency.name).filter(Agency.is_active == True).all()
        agencies = [agency[0] for agency in agencies]
        
        # Get form types
        form_types = db.query(Form.name).distinct().all()
        form_types = [form[0] for form in form_types]
        
        # Get severity levels
        severity_levels = db.query(FormChange.severity).distinct().all()
        severity_levels = [severity[0] for severity in severity_levels]
        
        # Get status options
        status_options = db.query(FormChange.status).distinct().all()
        status_options = [status[0] for status in status_options]
        
        # Predefined date ranges
        date_ranges = ["24h", "7d", "30d", "90d", "1y"]
        
        return FilterOptions(
            states=states,
            agencies=agencies,
            form_types=form_types,
            severity_levels=severity_levels,
            status_options=status_options,
            date_ranges=date_ranges
        )
    except Exception as e:
        logger.error(f"Error getting filter options: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve filter options")


@router.post("/search", response_model=SearchResponse)
async def search_changes(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Search form changes with advanced filtering and pagination."""
    try:
        query = db.query(FormChange).options(
            joinedload(FormChange.form).joinedload(Form.agency)
        )
        
        # Apply search query
        if request.query:
            search_term = f"%{request.query}%"
            query = query.filter(
                or_(
                    FormChange.change_description.ilike(search_term),
                    Form.name.ilike(search_term),
                    Agency.name.ilike(search_term)
                )
            )
        
        # Apply filters
        if request.filters:
            filters = request.filters
            
            if "agency_id" in filters:
                query = query.join(Form).filter(Form.agency_id == filters["agency_id"])
            
            if "severity" in filters:
                query = query.filter(FormChange.severity == filters["severity"])
            
            if "status" in filters:
                query = query.filter(FormChange.status == filters["status"])
            
            if "date_range" in filters:
                days = _parse_date_range(filters["date_range"])
                if days:
                    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                    query = query.filter(FormChange.detected_at >= cutoff_date)
            
            if "form_type" in filters:
                query = query.join(Form).filter(Form.name == filters["form_type"])
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply sorting
        if request.sort_by == "detected_at":
            if request.sort_order == "desc":
                query = query.order_by(desc(FormChange.detected_at))
            else:
                query = query.order_by(asc(FormChange.detected_at))
        elif request.sort_by == "severity":
            if request.sort_order == "desc":
                query = query.order_by(desc(FormChange.severity))
            else:
                query = query.order_by(asc(FormChange.severity))
        
        # Apply pagination
        offset = (request.page - 1) * request.page_size
        query = query.offset(offset).limit(request.page_size)
        
        # Get results
        changes = query.all()
        
        # Calculate total pages
        total_pages = (total_count + request.page_size - 1) // request.page_size
        
        return SearchResponse(
            results=[
                ChangeSummary(
                    id=change.id,
                    form_name=change.form.name,
                    agency_name=change.form.agency.name,
                    agency_type=change.form.agency.agency_type,
                    change_type=change.change_type,
                    severity=change.severity,
                    status=change.status,
                    detected_at=change.detected_at,
                    ai_confidence_score=change.ai_confidence_score,
                    ai_change_category=change.ai_change_category,
                    is_cosmetic_change=change.is_cosmetic_change,
                    impact_assessment=change.impact_assessment
                )
                for change in changes
            ],
            total_count=total_count,
            page=request.page,
            page_size=request.page_size,
            total_pages=total_pages,
            filters_applied=request.filters or {}
        )
    except Exception as e:
        logger.error(f"Error searching changes: {e}")
        raise HTTPException(status_code=500, detail="Failed to search changes")


@router.get("/alerts")
async def get_active_alerts(db: Session = Depends(get_db)):
    """Get active alerts and notifications."""
    try:
        with get_db() as db:
            # Get recent critical changes
            critical_changes = db.query(FormChange).filter(
                and_(
                    FormChange.severity == "critical",
                    FormChange.status.in_(["detected", "notified"])
                )
            ).order_by(desc(FormChange.detected_at)).limit(10).all()
            
            # Get failed monitoring runs
            failed_runs = db.query(MonitoringRun).filter(
                and_(
                    MonitoringRun.status == "failed",
                    MonitoringRun.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
                )
            ).order_by(desc(MonitoringRun.created_at)).limit(5).all()
            
            # Get pending notifications
            pending_notifications = db.query(Notification).filter(
                Notification.status == "pending"
            ).order_by(desc(Notification.sent_at)).limit(10).all()
            
            alerts = []
            
            # Add critical changes as alerts
            for change in critical_changes:
                alerts.append({
                    "id": f"change_{change.id}",
                    "type": "critical_change",
                    "title": f"Critical Change Detected: {change.form.name}",
                    "message": f"Critical change detected in {change.form.name} for {change.form.agency.name}",
                    "severity": "critical",
                    "timestamp": change.detected_at.isoformat(),
                    "details": {
                        "change_type": change.change_type,
                        "agency_name": change.form.agency.name,
                        "form_name": change.form.name,
                        "ai_confidence": change.ai_confidence_score
                    }
                })
            
            # Add failed runs as alerts
            for run in failed_runs:
                alerts.append({
                    "id": f"run_{run.id}",
                    "type": "monitoring_failure",
                    "title": f"Monitoring Run Failed: {run.agency.name}",
                    "message": f"Monitoring run failed for {run.agency.name}",
                    "severity": "high",
                    "timestamp": run.created_at.isoformat(),
                    "details": {
                        "error_message": run.error_message,
                        "agency_name": run.agency.name,
                        "form_name": run.form.name if run.form else "All Forms"
                    }
                })
            
            # Add pending notifications as alerts
            for notification in pending_notifications:
                alerts.append({
                    "id": f"notification_{notification.id}",
                    "type": "pending_notification",
                    "title": f"Pending Notification: {notification.subject}",
                    "message": f"Notification pending for {notification.recipient}",
                    "severity": "medium",
                    "timestamp": notification.sent_at.isoformat(),
                    "details": {
                        "recipient": notification.recipient,
                        "notification_type": notification.notification_type,
                        "retry_count": notification.retry_count
                    }
                })
            
            return {
                "alerts": alerts,
                "total_count": len(alerts),
                "critical_count": len([a for a in alerts if a["severity"] == "critical"]),
                "high_count": len([a for a in alerts if a["severity"] == "high"]),
                "medium_count": len([a for a in alerts if a["severity"] == "medium"])
            }
            
    except Exception as e:
        logger.error(f"Error getting active alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")


# Historical Data and Trend Analysis Endpoints

class TrendDataPoint(BaseModel):
    """Data point for trend analysis."""
    date: str
    value: int
    label: str

class TrendAnalysis(BaseModel):
    """Trend analysis results."""
    data_points: List[TrendDataPoint]
    trend_direction: str  # increasing, decreasing, stable
    trend_percentage: float
    period: str
    total_changes: int
    average_per_day: float

class HistoricalDataRequest(BaseModel):
    """Request for historical data."""
    metric: str  # changes, critical_changes, monitoring_runs, response_times
    period: str  # 7d, 30d, 90d, 1y
    group_by: str  # day, week, month
    filters: Optional[Dict[str, Any]] = None

@router.post("/historical-data")
async def get_historical_data(
    request: HistoricalDataRequest,
    db: Session = Depends(get_db)
):
    """Get historical data for visualization and trend analysis."""
    try:
        with get_db() as db:
            # Calculate date range based on period
            end_date = datetime.now(timezone.utc)
            if request.period == "7d":
                start_date = end_date - timedelta(days=7)
                group_format = "%Y-%m-%d"
            elif request.period == "30d":
                start_date = end_date - timedelta(days=30)
                group_format = "%Y-%m-%d"
            elif request.period == "90d":
                start_date = end_date - timedelta(days=90)
                group_format = "%Y-%m-%d"
            elif request.period == "1y":
                start_date = end_date - timedelta(days=365)
                group_format = "%Y-%m"
            else:
                start_date = end_date - timedelta(days=30)
                group_format = "%Y-%m-%d"
            
            # Build base query based on metric
            if request.metric == "changes":
                base_query = db.query(
                    func.date_format(FormChange.detected_at, group_format).label('date'),
                    func.count(FormChange.id).label('count')
                ).filter(
                    FormChange.detected_at >= start_date
                )
            elif request.metric == "critical_changes":
                base_query = db.query(
                    func.date_format(FormChange.detected_at, group_format).label('date'),
                    func.count(FormChange.id).label('count')
                ).filter(
                    and_(
                        FormChange.detected_at >= start_date,
                        FormChange.severity == "critical"
                    )
                )
            elif request.metric == "monitoring_runs":
                base_query = db.query(
                    func.date_format(MonitoringRun.started_at, group_format).label('date'),
                    func.count(MonitoringRun.id).label('count')
                ).filter(
                    MonitoringRun.started_at >= start_date
                )
            elif request.metric == "response_times":
                base_query = db.query(
                    func.date_format(MonitoringRun.started_at, group_format).label('date'),
                    func.avg(MonitoringRun.response_time_ms).label('count')
                ).filter(
                    and_(
                        MonitoringRun.started_at >= start_date,
                        MonitoringRun.response_time_ms.isnot(None)
                    )
                )
            else:
                raise HTTPException(status_code=400, detail="Invalid metric specified")
            
            # Apply filters if provided
            if request.filters:
                if "agency_id" in request.filters:
                    base_query = base_query.join(Form).filter(Form.agency_id == request.filters["agency_id"])
                if "severity" in request.filters:
                    base_query = base_query.filter(FormChange.severity == request.filters["severity"])
                if "status" in request.filters:
                    base_query = base_query.filter(FormChange.status == request.filters["status"])
            
            # Group and order results
            results = base_query.group_by('date').order_by('date').all()
            
            # Convert to data points
            data_points = []
            for result in results:
                data_points.append(TrendDataPoint(
                    date=result.date,
                    value=int(result.count) if result.count else 0,
                    label=result.date
                ))
            
            # Calculate trend analysis
            if len(data_points) >= 2:
                first_half = data_points[:len(data_points)//2]
                second_half = data_points[len(data_points)//2:]
                
                first_avg = sum(p.value for p in first_half) / len(first_half) if first_half else 0
                second_avg = sum(p.value for p in second_half) / len(second_half) if second_half else 0
                
                if first_avg > 0:
                    trend_percentage = ((second_avg - first_avg) / first_avg) * 100
                else:
                    trend_percentage = 0
                
                if trend_percentage > 5:
                    trend_direction = "increasing"
                elif trend_percentage < -5:
                    trend_direction = "decreasing"
                else:
                    trend_direction = "stable"
            else:
                trend_direction = "stable"
                trend_percentage = 0
            
            total_changes = sum(p.value for p in data_points)
            average_per_day = total_changes / len(data_points) if data_points else 0
            
            return TrendAnalysis(
                data_points=data_points,
                trend_direction=trend_direction,
                trend_percentage=trend_percentage,
                period=request.period,
                total_changes=total_changes,
                average_per_day=average_per_day
            )
            
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving historical data: {str(e)}")


@router.get("/trends/summary")
async def get_trends_summary(db: Session = Depends(get_db)):
    """Get summary of key trends across different metrics."""
    try:
        with get_db() as db:
            # Get trends for different metrics over the last 30 days
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            
            trends = {}
            
            # Changes trend
            changes_query = db.query(
                func.date_format(FormChange.detected_at, "%Y-%m-%d").label('date'),
                func.count(FormChange.id).label('count')
            ).filter(
                FormChange.detected_at >= start_date
            ).group_by('date').order_by('date').all()
            
            if len(changes_query) >= 2:
                first_half = changes_query[:len(changes_query)//2]
                second_half = changes_query[len(changes_query)//2:]
                
                first_avg = sum(r.count for r in first_half) / len(first_half) if first_half else 0
                second_avg = sum(r.count for r in second_half) / len(second_half) if second_half else 0
                
                if first_avg > 0:
                    changes_trend = ((second_avg - first_avg) / first_avg) * 100
                else:
                    changes_trend = 0
            else:
                changes_trend = 0
            
            # Critical changes trend
            critical_query = db.query(
                func.date_format(FormChange.detected_at, "%Y-%m-%d").label('date'),
                func.count(FormChange.id).label('count')
            ).filter(
                and_(
                    FormChange.detected_at >= start_date,
                    FormChange.severity == "critical"
                )
            ).group_by('date').order_by('date').all()
            
            if len(critical_query) >= 2:
                first_half = critical_query[:len(critical_query)//2]
                second_half = critical_query[len(critical_query)//2:]
                
                first_avg = sum(r.count for r in first_half) / len(first_half) if first_half else 0
                second_avg = sum(r.count for r in second_half) / len(second_half) if second_half else 0
                
                if first_avg > 0:
                    critical_trend = ((second_avg - first_avg) / first_avg) * 100
                else:
                    critical_trend = 0
            else:
                critical_trend = 0
            
            # Response time trend
            response_query = db.query(
                func.date_format(MonitoringRun.started_at, "%Y-%m-%d").label('date'),
                func.avg(MonitoringRun.response_time_ms).label('avg_time')
            ).filter(
                and_(
                    MonitoringRun.started_at >= start_date,
                    MonitoringRun.response_time_ms.isnot(None)
                )
            ).group_by('date').order_by('date').all()
            
            if len(response_query) >= 2:
                first_half = response_query[:len(response_query)//2]
                second_half = response_query[len(response_query)//2:]
                
                first_avg = sum(r.avg_time for r in first_half) / len(first_half) if first_half else 0
                second_avg = sum(r.avg_time for r in second_half) / len(second_half) if second_half else 0
                
                if first_avg > 0:
                    response_trend = ((second_avg - first_avg) / first_avg) * 100
                else:
                    response_trend = 0
            else:
                response_trend = 0
            
            return {
                "changes_trend": {
                    "percentage": changes_trend,
                    "direction": "increasing" if changes_trend > 5 else "decreasing" if changes_trend < -5 else "stable",
                    "description": f"Changes are {'increasing' if changes_trend > 5 else 'decreasing' if changes_trend < -5 else 'stable'} by {abs(changes_trend):.1f}%"
                },
                "critical_trend": {
                    "percentage": critical_trend,
                    "direction": "increasing" if critical_trend > 5 else "decreasing" if critical_trend < -5 else "stable",
                    "description": f"Critical changes are {'increasing' if critical_trend > 5 else 'decreasing' if critical_trend < -5 else 'stable'} by {abs(critical_trend):.1f}%"
                },
                "response_time_trend": {
                    "percentage": response_trend,
                    "direction": "increasing" if response_trend > 5 else "decreasing" if response_trend < -5 else "stable",
                    "description": f"Response times are {'increasing' if response_trend > 5 else 'decreasing' if response_trend < -5 else 'stable'} by {abs(response_trend):.1f}%"
                },
                "period": "30 days",
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error getting trends summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving trends summary: {str(e)}")


@router.get("/analytics/agency-performance")
async def get_agency_performance_analytics(db: Session = Depends(get_db)):
    """Get performance analytics by agency."""
    try:
        with get_db() as db:
            # Get performance data for each agency
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            
            agency_performance = []
            
            agencies = db.query(Agency).filter(Agency.is_active == True).all()
            
            for agency in agencies:
                # Get total changes for this agency
                total_changes = db.query(FormChange).join(Form).filter(
                    and_(
                        Form.agency_id == agency.id,
                        FormChange.detected_at >= start_date
                    )
                ).count()
                
                # Get critical changes
                critical_changes = db.query(FormChange).join(Form).filter(
                    and_(
                        Form.agency_id == agency.id,
                        FormChange.severity == "critical",
                        FormChange.detected_at >= start_date
                    )
                ).count()
                
                # Get monitoring runs
                monitoring_runs = db.query(MonitoringRun).filter(
                    and_(
                        MonitoringRun.agency_id == agency.id,
                        MonitoringRun.started_at >= start_date
                    )
                ).all()
                
                successful_runs = len([r for r in monitoring_runs if r.status == "completed"])
                failed_runs = len([r for r in monitoring_runs if r.status == "failed"])
                
                success_rate = (successful_runs / len(monitoring_runs) * 100) if monitoring_runs else 0
                
                # Calculate average response time
                response_times = [r.response_time_ms for r in monitoring_runs if r.response_time_ms]
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                
                agency_performance.append({
                    "agency_id": agency.id,
                    "agency_name": agency.name,
                    "agency_type": agency.agency_type,
                    "total_changes": total_changes,
                    "critical_changes": critical_changes,
                    "monitoring_runs": len(monitoring_runs),
                    "successful_runs": successful_runs,
                    "failed_runs": failed_runs,
                    "success_rate": success_rate,
                    "avg_response_time_ms": avg_response_time,
                    "performance_score": _calculate_performance_score(
                        total_changes, critical_changes, success_rate, avg_response_time
                    )
                })
            
            # Sort by performance score
            agency_performance.sort(key=lambda x: x["performance_score"], reverse=True)
            
            return {
                "agency_performance": agency_performance,
                "summary": {
                    "total_agencies": len(agency_performance),
                    "avg_success_rate": sum(p["success_rate"] for p in agency_performance) / len(agency_performance) if agency_performance else 0,
                    "avg_response_time": sum(p["avg_response_time_ms"] for p in agency_performance) / len(agency_performance) if agency_performance else 0,
                    "total_changes": sum(p["total_changes"] for p in agency_performance),
                    "total_critical": sum(p["critical_changes"] for p in agency_performance)
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting agency performance analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving agency performance: {str(e)}")


def _calculate_performance_score(changes, critical_changes, success_rate, response_time):
    """Calculate a performance score for an agency."""
    # Base score starts at 100
    score = 100
    
    # Deduct points for critical changes (higher weight)
    score -= critical_changes * 5
    
    # Deduct points for failed monitoring (lower weight)
    score -= (100 - success_rate) * 0.5
    
    # Deduct points for slow response times
    if response_time > 5000:  # 5 seconds
        score -= (response_time - 5000) / 100
    
    # Ensure score doesn't go below 0
    return max(0, score)


# Helper functions
def _calculate_error_rate(db: Session) -> float:
    """Calculate the current error rate for monitoring runs."""
    try:
        total_runs = db.query(MonitoringRun).filter(
            MonitoringRun.started_at >= datetime.now(timezone.utc) - timedelta(hours=24)
        ).count()
        
        if total_runs == 0:
            return 0.0
        
        failed_runs = db.query(MonitoringRun).filter(
            and_(
                MonitoringRun.status == "failed",
                MonitoringRun.started_at >= datetime.now(timezone.utc) - timedelta(hours=24)
            )
        ).count()
        
        return (failed_runs / total_runs) * 100
    except Exception as e:
        logger.error(f"Error calculating error rate: {e}")
        return 0.0


def _parse_date_range(date_range: str) -> Optional[int]:
    """Parse date range string to number of days."""
    range_map = {
        "24h": 1,
        "7d": 7,
        "30d": 30,
        "90d": 90,
        "1y": 365
    }
    return range_map.get(date_range)


# Export-related Pydantic models
class ExportRequest(BaseModel):
    """Request for data export."""
    format: str = Field(..., description="Export format: csv, excel, pdf")
    filters: Optional[Dict[str, Any]] = None
    columns: Optional[List[str]] = None
    include_headers: bool = True
    filename: Optional[str] = None


class ExportResponse(BaseModel):
    """Response for export request."""
    export_id: str
    filename: str
    format: str
    record_count: int
    download_url: str
    expires_at: datetime


class ScheduledExportRequest(BaseModel):
    """Request for scheduling an export."""
    export_config: ExportRequest
    schedule: Dict[str, Any] = Field(..., description="Schedule configuration")
    recipients: Optional[List[str]] = None


class ScheduledExportResponse(BaseModel):
    """Response for scheduled export."""
    export_id: str
    schedule: Dict[str, Any]
    next_run: datetime
    status: str


# Export endpoints
@router.post("/export", response_model=ExportResponse)
async def export_filtered_data(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    Export filtered dashboard data in various formats.
    
    Supports CSV, Excel, and PDF formats with filtering and column selection.
    """
    try:
        # Validate format
        if request.format not in ['csv', 'excel', 'pdf']:
            raise HTTPException(status_code=400, detail="Unsupported export format")
        
        # Build query based on filters
        query = db.query(FormChange).options(
            joinedload(FormChange.form).joinedload(Form.agency)
        )
        
        # Apply filters
        if request.filters:
            query = _apply_export_filters(query, request.filters)
        
        # Execute query
        changes = query.all()
        
        # Convert to dictionary format for export
        export_data = []
        for change in changes:
            change_dict = {
                'id': change.id,
                'form_name': change.form.name if change.form else 'Unknown',
                'agency_name': change.form.agency.name if change.form and change.form.agency else 'Unknown',
                'agency_type': change.form.agency.agency_type if change.form and change.form.agency else 'Unknown',
                'change_type': change.change_type,
                'severity': change.severity,
                'status': change.status,
                'detected_at': change.detected_at,
                'ai_confidence_score': change.ai_confidence_score,
                'ai_change_category': change.ai_change_category,
                'is_cosmetic_change': change.is_cosmetic_change,
                'impact_assessment': change.impact_assessment,
                'description': change.description,
                'url': change.url
            }
            export_data.append(change_dict)
        
        # Prepare export configuration
        export_config = {
            'filters': request.filters,
            'columns': request.columns,
            'include_headers': request.include_headers
        }
        
        # Generate export
        export_content = export_manager.export_data(
            data=export_data,
            format_type=request.format,
            export_config=export_config,
            filename=request.filename
        )
        
        # Generate unique export ID
        export_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(export_data)}"
        
        # Create filename
        if not request.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            request.filename = f"compliance_export_{timestamp}.{request.format}"
        
        # Store export temporarily (in production, this would be stored in a file system or cloud storage)
        # For now, we'll return the content directly
        
        return ExportResponse(
            export_id=export_id,
            filename=request.filename,
            format=request.format,
            record_count=len(export_data),
            download_url=f"/api/dashboard/export/{export_id}/download",
            expires_at=datetime.now() + timedelta(hours=24)
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/export/{export_id}/download")
async def download_export(
    export_id: str,
    db: Session = Depends(get_db)
):
    """
    Download an exported file.
    
    This is a simplified implementation. In production, this would retrieve
    the file from storage and return it as a proper file download.
    """
    try:
        # In a real implementation, this would retrieve the file from storage
        # For now, we'll return a placeholder response
        raise HTTPException(status_code=404, detail="Export file not found or expired")
        
    except Exception as e:
        logger.error(f"Download failed for export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/export/schedule", response_model=ScheduledExportResponse)
async def schedule_export(
    request: ScheduledExportRequest,
    db: Session = Depends(get_db)
):
    """
    Schedule a recurring export.
    
    Allows users to set up automated exports with custom schedules.
    """
    try:
        # Generate unique export ID
        export_id = f"scheduled_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Schedule the export
        success = export_scheduler.schedule_export(
            export_id=export_id,
            schedule_config=request.schedule,
            export_config=request.export_config.dict()
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to schedule export")
        
        # Get scheduled export details
        scheduled_exports = export_scheduler.get_scheduled_exports()
        export_details = scheduled_exports.get(export_id)
        
        if not export_details:
            raise HTTPException(status_code=500, detail="Export scheduling failed")
        
        return ScheduledExportResponse(
            export_id=export_id,
            schedule=request.schedule,
            next_run=export_details['next_run'],
            status="scheduled"
        )
        
    except Exception as e:
        logger.error(f"Export scheduling failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export scheduling failed: {str(e)}")


@router.get("/export/scheduled")
async def get_scheduled_exports():
    """
    Get all scheduled exports.
    
    Returns a list of all currently scheduled exports.
    """
    try:
        scheduled_exports = export_scheduler.get_scheduled_exports()
        
        # Convert to response format
        exports = []
        for export_id, details in scheduled_exports.items():
            exports.append({
                'export_id': export_id,
                'schedule': details['schedule'],
                'export_config': details['export_config'],
                'created_at': details['created_at'],
                'last_run': details['last_run'],
                'next_run': details['next_run']
            })
        
        return {"scheduled_exports": exports}
        
    except Exception as e:
        logger.error(f"Failed to get scheduled exports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduled exports: {str(e)}")


@router.delete("/export/schedule/{export_id}")
async def cancel_scheduled_export(export_id: str):
    """
    Cancel a scheduled export.
    
    Removes the scheduled export from the system.
    """
    try:
        success = export_scheduler.cancel_export(export_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled export not found")
        
        return {"message": f"Scheduled export {export_id} cancelled successfully"}
        
    except Exception as e:
        logger.error(f"Failed to cancel scheduled export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cancel scheduled export: {str(e)}")


@router.get("/export/formats")
async def get_export_formats():
    """
    Get available export formats and their capabilities.
    
    Returns information about supported export formats and their features.
    """
    return {
        "supported_formats": [
            {
                "format": "csv",
                "description": "Comma-separated values format",
                "features": ["Simple tabular data", "Universal compatibility", "Small file size"],
                "max_records": 10000
            },
            {
                "format": "excel",
                "description": "Microsoft Excel format with formatting and charts",
                "features": ["Multiple sheets", "Conditional formatting", "Charts and graphs", "Professional styling"],
                "max_records": 10000
            },
            {
                "format": "pdf",
                "description": "Portable Document Format with professional styling",
                "features": ["Professional appearance", "Fixed layout", "Summary statistics", "Charts"],
                "max_records": 1000
            }
        ],
        "max_export_size": 10000
    }


def _apply_export_filters(query, filters: Dict[str, Any]):
    """Apply filters to the export query."""
    if filters.get('agency_id'):
        query = query.join(Form).filter(Form.agency_id == filters['agency_id'])
    
    if filters.get('severity'):
        query = query.filter(FormChange.severity == filters['severity'])
    
    if filters.get('status'):
        query = query.filter(FormChange.status == filters['status'])
    
    if filters.get('date_from'):
        try:
            date_from = datetime.fromisoformat(filters['date_from'])
            query = query.filter(FormChange.detected_at >= date_from)
        except ValueError:
            pass
    
    if filters.get('date_to'):
        try:
            date_to = datetime.fromisoformat(filters['date_to'])
            query = query.filter(FormChange.detected_at <= date_to)
        except ValueError:
            pass
    
    if filters.get('change_type'):
        query = query.filter(FormChange.change_type == filters['change_type'])
    
    if filters.get('ai_confidence_min'):
        try:
            confidence_min = int(filters['ai_confidence_min'])
            query = query.filter(FormChange.ai_confidence_score >= confidence_min)
        except ValueError:
            pass
    
    return query 