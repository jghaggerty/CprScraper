"""
Report Scheduling API

This module provides API endpoints for scheduling automated report generation
and delivery, including cron-based schedules, event-driven triggers, and
intelligent delivery management.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..reporting.report_scheduler import (
    ReportScheduler, ScheduleConfig, ScheduleType, TriggerType, ScheduleExecution
)
from ..reporting.report_customization import ReportCustomizationOptions
from ..auth.auth import get_current_user
from ..database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/scheduling", tags=["Report Scheduling"])

# Pydantic models for API requests/responses
class ScheduleRequest(BaseModel):
    """Request for creating a report schedule."""
    name: str = Field(..., description="Name of the schedule")
    description: Optional[str] = Field(None, description="Description of the schedule")
    schedule_type: str = Field(..., description="Type of schedule (cron, interval, event_driven)")
    is_active: bool = Field(True, description="Whether the schedule is active")
    
    # Schedule parameters
    cron_expression: Optional[str] = Field(None, description="Cron expression for cron schedules")
    interval_minutes: Optional[int] = Field(None, description="Interval in minutes for interval schedules")
    timezone: str = Field("UTC", description="Timezone for the schedule")
    
    # Trigger configuration (for event-driven schedules)
    trigger_type: Optional[str] = Field(None, description="Type of trigger for event-driven schedules")
    trigger_threshold: Optional[int] = Field(None, description="Threshold for trigger conditions")
    trigger_conditions: Optional[Dict[str, Any]] = Field(None, description="Additional trigger conditions")
    
    # Report customization
    customization_options: Optional[Dict[str, Any]] = Field(None, description="Report customization options")
    
    # Delivery configuration
    target_roles: Optional[List[str]] = Field(None, description="Target user roles for delivery")
    target_users: Optional[List[int]] = Field(None, description="Target user IDs for delivery")
    delivery_channels: Optional[List[str]] = Field(None, description="Delivery channels (email, slack, etc.)")
    
    # Advanced options
    max_retries: int = Field(3, description="Maximum number of retry attempts")
    retry_delay_minutes: int = Field(5, description="Delay between retries in minutes")
    force_delivery: bool = Field(False, description="Force delivery even if conditions aren't met")
    include_attachments: bool = Field(True, description="Include report attachments")


class ScheduleResponse(BaseModel):
    """Response for schedule operations."""
    schedule_id: str
    name: str
    description: Optional[str]
    schedule_type: str
    is_active: bool
    timezone: str
    next_run: Optional[str]
    last_run: Optional[str]
    created_at: Optional[str]
    target_roles: Optional[List[str]]
    target_users: Optional[List[int]]
    delivery_channels: Optional[List[str]]
    status: str


class ScheduleUpdateRequest(BaseModel):
    """Request for updating a schedule."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    timezone: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_threshold: Optional[int] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    customization_options: Optional[Dict[str, Any]] = None
    target_roles: Optional[List[str]] = None
    target_users: Optional[List[int]] = None
    delivery_channels: Optional[List[str]] = None
    max_retries: Optional[int] = None
    retry_delay_minutes: Optional[int] = None
    force_delivery: Optional[bool] = None
    include_attachments: Optional[bool] = None


class ExecutionResponse(BaseModel):
    """Response for schedule execution."""
    schedule_id: str
    execution_time: str
    status: str
    report_generated: bool
    users_notified: int
    users_failed: int
    error_message: Optional[str]
    execution_duration_seconds: Optional[float]


class ScheduleStatisticsResponse(BaseModel):
    """Response for schedule statistics."""
    schedule_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_execution_time_seconds: float
    last_execution: Optional[str]
    next_execution: Optional[str]


# Helper function to get scheduler instance
def get_report_scheduler() -> ReportScheduler:
    """Get a report scheduler instance."""
    return ReportScheduler()


@router.post("/schedules", response_model=ScheduleResponse)
async def create_schedule(
    request: ScheduleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new report schedule.
    
    Creates a schedule for automated report generation and delivery.
    """
    try:
        scheduler = get_report_scheduler()
        
        # Convert string to enum
        schedule_type = ScheduleType(request.schedule_type)
        trigger_type = None
        if request.trigger_type:
            trigger_type = TriggerType(request.trigger_type)
        
        # Convert customization options
        customization_options = None
        if request.customization_options:
            customization_options = ReportCustomizationOptions.from_dict(request.customization_options)
        
        # Create schedule
        schedule = scheduler.create_schedule(
            name=request.name,
            schedule_type=schedule_type,
            description=request.description,
            is_active=request.is_active,
            cron_expression=request.cron_expression,
            interval_minutes=request.interval_minutes,
            timezone=request.timezone,
            trigger_type=trigger_type,
            trigger_threshold=request.trigger_threshold,
            trigger_conditions=request.trigger_conditions,
            customization_options=customization_options,
            target_roles=request.target_roles,
            target_users=request.target_users,
            delivery_channels=request.delivery_channels,
            max_retries=request.max_retries,
            retry_delay_minutes=request.retry_delay_minutes,
            force_delivery=request.force_delivery,
            include_attachments=request.include_attachments,
            created_by=current_user.id,
            created_at=datetime.now()
        )
        
        return ScheduleResponse(
            schedule_id=schedule.name,  # Using name as ID for now
            name=schedule.name,
            description=schedule.description,
            schedule_type=schedule.schedule_type.value,
            is_active=schedule.is_active,
            timezone=schedule.timezone,
            next_run=schedule.next_run.isoformat() if schedule.next_run else None,
            last_run=schedule.last_run.isoformat() if schedule.last_run else None,
            created_at=schedule.created_at.isoformat() if schedule.created_at else None,
            target_roles=schedule.target_roles,
            target_users=schedule.target_users,
            delivery_channels=schedule.delivery_channels,
            status="created"
        )
        
    except Exception as e:
        logger.error(f"Failed to create schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create schedule: {str(e)}")


@router.get("/schedules", response_model=List[ScheduleResponse])
async def get_schedules(
    schedule_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all report schedules.
    
    Returns a list of all schedules, optionally filtered by type and status.
    """
    try:
        scheduler = get_report_scheduler()
        
        if schedule_type:
            schedules = scheduler.get_schedules_by_type(ScheduleType(schedule_type))
        else:
            schedules = list(scheduler.get_all_schedules().values())
        
        # Filter by active status if specified
        if is_active is not None:
            schedules = [s for s in schedules if s.is_active == is_active]
        
        # Convert to response format
        response_schedules = []
        for schedule in schedules:
            response_schedules.append(ScheduleResponse(
                schedule_id=schedule.name,
                name=schedule.name,
                description=schedule.description,
                schedule_type=schedule.schedule_type.value,
                is_active=schedule.is_active,
                timezone=schedule.timezone,
                next_run=schedule.next_run.isoformat() if schedule.next_run else None,
                last_run=schedule.last_run.isoformat() if schedule.last_run else None,
                created_at=schedule.created_at.isoformat() if schedule.created_at else None,
                target_roles=schedule.target_roles,
                target_users=schedule.target_users,
                delivery_channels=schedule.delivery_channels,
                status="active" if schedule.is_active else "inactive"
            ))
        
        return response_schedules
        
    except Exception as e:
        logger.error(f"Failed to get schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedules: {str(e)}")


@router.get("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific report schedule.
    
    Returns details for a specific schedule by ID.
    """
    try:
        scheduler = get_report_scheduler()
        schedule = scheduler.get_schedule(schedule_id)
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return ScheduleResponse(
            schedule_id=schedule.name,
            name=schedule.name,
            description=schedule.description,
            schedule_type=schedule.schedule_type.value,
            is_active=schedule.is_active,
            timezone=schedule.timezone,
            next_run=schedule.next_run.isoformat() if schedule.next_run else None,
            last_run=schedule.last_run.isoformat() if schedule.last_run else None,
            created_at=schedule.created_at.isoformat() if schedule.created_at else None,
            target_roles=schedule.target_roles,
            target_users=schedule.target_users,
            delivery_channels=schedule.delivery_channels,
            status="active" if schedule.is_active else "inactive"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


@router.put("/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: str,
    request: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a report schedule.
    
    Updates an existing schedule with new configuration.
    """
    try:
        scheduler = get_report_scheduler()
        
        # Convert string to enum if provided
        updates = request.dict(exclude_unset=True)
        if 'schedule_type' in updates:
            updates['schedule_type'] = ScheduleType(updates['schedule_type'])
        if 'trigger_type' in updates and updates['trigger_type']:
            updates['trigger_type'] = TriggerType(updates['trigger_type'])
        if 'customization_options' in updates and updates['customization_options']:
            updates['customization_options'] = ReportCustomizationOptions.from_dict(updates['customization_options'])
        
        success = scheduler.update_schedule(schedule_id, **updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        # Get updated schedule
        schedule = scheduler.get_schedule(schedule_id)
        
        return ScheduleResponse(
            schedule_id=schedule.name,
            name=schedule.name,
            description=schedule.description,
            schedule_type=schedule.schedule_type.value,
            is_active=schedule.is_active,
            timezone=schedule.timezone,
            next_run=schedule.next_run.isoformat() if schedule.next_run else None,
            last_run=schedule.last_run.isoformat() if schedule.last_run else None,
            created_at=schedule.created_at.isoformat() if schedule.created_at else None,
            target_roles=schedule.target_roles,
            target_users=schedule.target_users,
            delivery_channels=schedule.delivery_channels,
            status="active" if schedule.is_active else "inactive"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update schedule: {str(e)}")


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a report schedule.
    
    Removes a schedule from the system.
    """
    try:
        scheduler = get_report_scheduler()
        success = scheduler.delete_schedule(schedule_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {"message": f"Schedule {schedule_id} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete schedule: {str(e)}")


@router.post("/schedules/{schedule_id}/execute", response_model=ExecutionResponse)
async def execute_schedule(
    schedule_id: str,
    force: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a report schedule immediately.
    
    Runs a schedule immediately, regardless of its normal schedule.
    """
    try:
        scheduler = get_report_scheduler()
        
        # Execute the schedule
        execution = await scheduler.execute_schedule(schedule_id, force=force)
        
        return ExecutionResponse(
            schedule_id=execution.schedule_id,
            execution_time=execution.execution_time.isoformat(),
            status=execution.status,
            report_generated=execution.report_generated,
            users_notified=execution.users_notified,
            users_failed=execution.users_failed,
            error_message=execution.error_message,
            execution_duration_seconds=execution.execution_duration_seconds
        )
        
    except Exception as e:
        logger.error(f"Failed to execute schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to execute schedule: {str(e)}")


@router.post("/schedules/{schedule_id}/trigger")
async def trigger_schedule(
    schedule_id: str,
    trigger_type: str,
    event_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger an event-driven schedule.
    
    Manually triggers an event-driven schedule with specific event data.
    """
    try:
        scheduler = get_report_scheduler()
        
        # Trigger the event
        scheduler.trigger_event(TriggerType(trigger_type), event_data)
        
        return {"message": f"Event {trigger_type} triggered for schedule {schedule_id}"}
        
    except Exception as e:
        logger.error(f"Failed to trigger schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger schedule: {str(e)}")


@router.get("/schedules/{schedule_id}/history", response_model=List[ExecutionResponse])
async def get_execution_history(
    schedule_id: str,
    limit: Optional[int] = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get execution history for a schedule.
    
    Returns the execution history for a specific schedule.
    """
    try:
        scheduler = get_report_scheduler()
        history = scheduler.get_execution_history(schedule_id=schedule_id, limit=limit)
        
        return [
            ExecutionResponse(
                schedule_id=execution.schedule_id,
                execution_time=execution.execution_time.isoformat(),
                status=execution.status,
                report_generated=execution.report_generated,
                users_notified=execution.users_notified,
                users_failed=execution.users_failed,
                error_message=execution.error_message,
                execution_duration_seconds=execution.execution_duration_seconds
            )
            for execution in history
        ]
        
    except Exception as e:
        logger.error(f"Failed to get execution history for schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get execution history: {str(e)}")


@router.get("/schedules/{schedule_id}/statistics", response_model=ScheduleStatisticsResponse)
async def get_schedule_statistics(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for a schedule.
    
    Returns performance and execution statistics for a specific schedule.
    """
    try:
        scheduler = get_report_scheduler()
        stats = scheduler.get_schedule_statistics(schedule_id)
        
        return ScheduleStatisticsResponse(
            schedule_id=stats['schedule_id'],
            total_executions=stats['total_executions'],
            successful_executions=stats['successful_executions'],
            failed_executions=stats['failed_executions'],
            success_rate=stats['success_rate'],
            avg_execution_time_seconds=stats['avg_execution_time_seconds'],
            last_execution=stats['last_execution'].isoformat() if stats.get('last_execution') else None,
            next_execution=stats['next_execution'].isoformat() if stats.get('next_execution') else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get statistics for schedule {schedule_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule statistics: {str(e)}")


@router.post("/schedules/run-due")
async def run_due_schedules(
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Run all due schedules.
    
    Executes all schedules that are due to run.
    """
    try:
        scheduler = get_report_scheduler()
        executions = await scheduler.run_due_schedules()
        
        return {
            "message": f"Executed {len(executions)} due schedules",
            "executions": [
                {
                    "schedule_id": execution.schedule_id,
                    "status": execution.status,
                    "execution_time": execution.execution_time.isoformat()
                }
                for execution in executions
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to run due schedules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run due schedules: {str(e)}")


# Convenience endpoints for common schedule types
@router.post("/schedules/weekly", response_model=ScheduleResponse)
async def create_weekly_schedule(
    name: str,
    day_of_week: int = 0,  # Monday = 0
    hour: int = 9,
    minute: int = 0,
    timezone: str = "UTC",
    target_roles: Optional[List[str]] = None,
    delivery_channels: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a weekly report schedule.
    
    Convenience endpoint for creating weekly schedules.
    """
    try:
        scheduler = get_report_scheduler()
        
        schedule = scheduler.create_weekly_schedule(
            name=name,
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone=timezone,
            target_roles=target_roles,
            delivery_channels=delivery_channels,
            created_by=current_user.id,
            created_at=datetime.now()
        )
        
        return ScheduleResponse(
            schedule_id=schedule.name,
            name=schedule.name,
            description=schedule.description,
            schedule_type=schedule.schedule_type.value,
            is_active=schedule.is_active,
            timezone=schedule.timezone,
            next_run=schedule.next_run.isoformat() if schedule.next_run else None,
            last_run=schedule.last_run.isoformat() if schedule.last_run else None,
            created_at=schedule.created_at.isoformat() if schedule.created_at else None,
            target_roles=schedule.target_roles,
            target_users=schedule.target_users,
            delivery_channels=schedule.delivery_channels,
            status="created"
        )
        
    except Exception as e:
        logger.error(f"Failed to create weekly schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create weekly schedule: {str(e)}")


@router.post("/schedules/daily", response_model=ScheduleResponse)
async def create_daily_schedule(
    name: str,
    hour: int = 9,
    minute: int = 0,
    timezone: str = "UTC",
    target_roles: Optional[List[str]] = None,
    delivery_channels: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a daily report schedule.
    
    Convenience endpoint for creating daily schedules.
    """
    try:
        scheduler = get_report_scheduler()
        
        schedule = scheduler.create_daily_schedule(
            name=name,
            hour=hour,
            minute=minute,
            timezone=timezone,
            target_roles=target_roles,
            delivery_channels=delivery_channels,
            created_by=current_user.id,
            created_at=datetime.now()
        )
        
        return ScheduleResponse(
            schedule_id=schedule.name,
            name=schedule.name,
            description=schedule.description,
            schedule_type=schedule.schedule_type.value,
            is_active=schedule.is_active,
            timezone=schedule.timezone,
            next_run=schedule.next_run.isoformat() if schedule.next_run else None,
            last_run=schedule.last_run.isoformat() if schedule.last_run else None,
            created_at=schedule.created_at.isoformat() if schedule.created_at else None,
            target_roles=schedule.target_roles,
            target_users=schedule.target_users,
            delivery_channels=schedule.delivery_channels,
            status="created"
        )
        
    except Exception as e:
        logger.error(f"Failed to create daily schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create daily schedule: {str(e)}") 