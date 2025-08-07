"""
Report Scheduling and Automated Delivery System

This module provides comprehensive scheduling capabilities for automated report generation
and delivery, including cron-based schedules, event-driven triggers, and intelligent delivery.
"""

import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json
import asyncio
from croniter import croniter
import pytz

from ..database.connection import get_db
from ..database.models import User, UserRole, Role
from ..reporting.report_customization import ReportCustomizationOptions, ReportCustomizationManager
from ..reporting.report_distribution import ReportDistributionManager
from ..notifications.enhanced_notifier import EnhancedNotificationManager
from ..utils.config_loader import get_notification_settings

logger = logging.getLogger(__name__)


class ScheduleType(Enum):
    """Types of report schedules."""
    CRON = "cron"
    INTERVAL = "interval"
    EVENT_DRIVEN = "event_driven"
    MANUAL = "manual"


class TriggerType(Enum):
    """Types of triggers for event-driven schedules."""
    CRITICAL_CHANGES = "critical_changes"
    HIGH_PRIORITY_CHANGES = "high_priority_changes"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    TIME_BASED = "time_based"
    USER_REQUESTED = "user_requested"


@dataclass
class ScheduleConfig:
    """Configuration for report scheduling."""
    # Basic schedule info
    name: str
    description: Optional[str] = None
    schedule_type: ScheduleType = ScheduleType.CRON
    is_active: bool = True
    
    # Schedule parameters
    cron_expression: Optional[str] = None  # For cron schedules
    interval_minutes: Optional[int] = None  # For interval schedules
    timezone: str = "UTC"
    
    # Trigger configuration (for event-driven schedules)
    trigger_type: Optional[TriggerType] = None
    trigger_threshold: Optional[int] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    
    # Report customization
    customization_options: Optional[ReportCustomizationOptions] = None
    
    # Delivery configuration
    target_roles: Optional[List[str]] = None
    target_users: Optional[List[int]] = None
    delivery_channels: Optional[List[str]] = None
    
    # Advanced options
    max_retries: int = 3
    retry_delay_minutes: int = 5
    force_delivery: bool = False
    include_attachments: bool = True
    
    # Metadata
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        data = asdict(self)
        data['schedule_type'] = self.schedule_type.value
        if self.trigger_type:
            data['trigger_type'] = self.trigger_type.value
        if self.customization_options:
            data['customization_options'] = self.customization_options.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScheduleConfig':
        """Create from dictionary."""
        # Convert enum values back
        if 'schedule_type' in data:
            data['schedule_type'] = ScheduleType(data['schedule_type'])
        if 'trigger_type' in data and data['trigger_type']:
            data['trigger_type'] = TriggerType(data['trigger_type'])
        if 'customization_options' in data and data['customization_options']:
            data['customization_options'] = ReportCustomizationOptions.from_dict(data['customization_options'])
        
        return cls(**data)


@dataclass
class ScheduleExecution:
    """Record of schedule execution."""
    schedule_id: str
    execution_time: datetime
    status: str  # 'success', 'failed', 'skipped'
    report_generated: bool = False
    users_notified: int = 0
    users_failed: int = 0
    error_message: Optional[str] = None
    execution_duration_seconds: Optional[float] = None
    report_data: Optional[Dict[str, Any]] = None


class ReportScheduler:
    """Manage automated report scheduling and delivery."""
    
    def __init__(self):
        self.customization_manager = ReportCustomizationManager()
        self.distribution_manager = ReportDistributionManager()
        self.notifier = EnhancedNotificationManager()
        self.notification_config = get_notification_settings()
        
        # Active schedules
        self.active_schedules: Dict[str, ScheduleConfig] = {}
        self.execution_history: List[ScheduleExecution] = []
        
        # Event listeners
        self.event_listeners: Dict[TriggerType, List[Callable]] = {
            trigger_type: [] for trigger_type in TriggerType
        }
    
    def create_schedule(
        self,
        name: str,
        schedule_type: ScheduleType,
        customization_options: Optional[ReportCustomizationOptions] = None,
        **kwargs
    ) -> ScheduleConfig:
        """Create a new report schedule."""
        schedule_id = f"schedule_{len(self.active_schedules) + 1}_{int(datetime.now().timestamp())}"
        
        # Set default customization options if not provided
        if not customization_options:
            customization_options = self.customization_manager.create_default_options()
        
        schedule_config = ScheduleConfig(
            name=name,
            schedule_type=schedule_type,
            customization_options=customization_options,
            created_at=datetime.now(),
            **kwargs
        )
        
        # Calculate next run time
        schedule_config.next_run = self._calculate_next_run(schedule_config)
        
        # Store the schedule
        self.active_schedules[schedule_id] = schedule_config
        
        logger.info(f"Created schedule '{name}' with ID {schedule_id}")
        return schedule_config
    
    def _calculate_next_run(self, schedule: ScheduleConfig) -> Optional[datetime]:
        """Calculate the next run time for a schedule."""
        if not schedule.is_active:
            return None
        
        now = datetime.now(pytz.timezone(schedule.timezone))
        
        if schedule.schedule_type == ScheduleType.CRON:
            if schedule.cron_expression:
                cron = croniter(schedule.cron_expression, now)
                return cron.get_next(datetime)
        
        elif schedule.schedule_type == ScheduleType.INTERVAL:
            if schedule.interval_minutes:
                return now + timedelta(minutes=schedule.interval_minutes)
        
        elif schedule.schedule_type == ScheduleType.EVENT_DRIVEN:
            # Event-driven schedules don't have a fixed next run time
            return None
        
        return None
    
    def update_schedule(self, schedule_id: str, **updates) -> bool:
        """Update an existing schedule."""
        if schedule_id not in self.active_schedules:
            logger.error(f"Schedule {schedule_id} not found")
            return False
        
        schedule = self.active_schedules[schedule_id]
        
        # Update fields
        for key, value in updates.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        # Recalculate next run time
        schedule.next_run = self._calculate_next_run(schedule)
        
        logger.info(f"Updated schedule {schedule_id}")
        return True
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if schedule_id not in self.active_schedules:
            logger.error(f"Schedule {schedule_id} not found")
            return False
        
        del self.active_schedules[schedule_id]
        logger.info(f"Deleted schedule {schedule_id}")
        return True
    
    def get_schedule(self, schedule_id: str) -> Optional[ScheduleConfig]:
        """Get a schedule by ID."""
        return self.active_schedules.get(schedule_id)
    
    def get_all_schedules(self) -> Dict[str, ScheduleConfig]:
        """Get all active schedules."""
        return self.active_schedules.copy()
    
    def get_schedules_by_type(self, schedule_type: ScheduleType) -> List[ScheduleConfig]:
        """Get schedules by type."""
        return [
            schedule for schedule in self.active_schedules.values()
            if schedule.schedule_type == schedule_type
        ]
    
    def get_schedules_for_user(self, user_id: int) -> List[ScheduleConfig]:
        """Get schedules that target a specific user."""
        user_schedules = []
        
        for schedule in self.active_schedules.values():
            if (schedule.target_users and user_id in schedule.target_users) or \
               (schedule.target_roles and self._user_has_role(user_id, schedule.target_roles)):
                user_schedules.append(schedule)
        
        return user_schedules
    
    def _user_has_role(self, user_id: int, roles: List[str]) -> bool:
        """Check if a user has any of the specified roles."""
        try:
            with get_db() as db:
                user_roles = db.query(UserRole).join(Role).filter(
                    UserRole.user_id == user_id,
                    UserRole.is_active == True,
                    Role.name.in_(roles),
                    Role.is_active == True
                ).all()
                
                return len(user_roles) > 0
        except Exception as e:
            logger.error(f"Error checking user roles: {e}")
            return False
    
    async def execute_schedule(self, schedule_id: str, force: bool = False) -> ScheduleExecution:
        """Execute a specific schedule."""
        if schedule_id not in self.active_schedules:
            raise ValueError(f"Schedule {schedule_id} not found")
        
        schedule = self.active_schedules[schedule_id]
        execution_start = datetime.now()
        
        execution = ScheduleExecution(
            schedule_id=schedule_id,
            execution_time=execution_start,
            status='failed'
        )
        
        try:
            # Check if schedule should run
            if not force and not self._should_run_schedule(schedule):
                execution.status = 'skipped'
                execution.error_message = 'Schedule conditions not met'
                return execution
            
            # Generate report
            report_result = await self._generate_scheduled_report(schedule)
            
            if not report_result['success']:
                execution.error_message = report_result.get('error', 'Unknown error')
                return execution
            
            execution.report_generated = True
            execution.report_data = report_result
            
            # Distribute report
            distribution_result = await self._distribute_scheduled_report(schedule, report_result)
            
            execution.users_notified = distribution_result.get('total_users_notified', 0)
            execution.users_failed = distribution_result.get('total_users_failed', 0)
            
            if execution.users_notified > 0:
                execution.status = 'success'
            else:
                execution.error_message = 'No users were notified'
            
            # Update schedule metadata
            schedule.last_run = execution_start
            schedule.next_run = self._calculate_next_run(schedule)
            
        except Exception as e:
            execution.error_message = str(e)
            logger.error(f"Error executing schedule {schedule_id}: {e}")
        
        finally:
            execution.execution_duration_seconds = (datetime.now() - execution_start).total_seconds()
            self.execution_history.append(execution)
        
        return execution
    
    def _should_run_schedule(self, schedule: ScheduleConfig) -> bool:
        """Check if a schedule should run based on its conditions."""
        if not schedule.is_active:
            return False
        
        if schedule.schedule_type == ScheduleType.EVENT_DRIVEN:
            # Event-driven schedules are triggered externally
            return False
        
        if schedule.next_run and datetime.now() < schedule.next_run:
            return False
        
        return True
    
    async def _generate_scheduled_report(self, schedule: ScheduleConfig) -> Dict[str, Any]:
        """Generate a report for a scheduled execution."""
        if not schedule.customization_options:
            # Use default options if none provided
            schedule.customization_options = self.customization_manager.create_default_options()
        
        return self.customization_manager.generate_customized_report(
            schedule.customization_options
        )
    
    async def _distribute_scheduled_report(
        self,
        schedule: ScheduleConfig,
        report_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Distribute a scheduled report to target users."""
        # Determine target users
        target_users = []
        
        if schedule.target_users:
            # Direct user targeting
            target_users.extend(schedule.target_users)
        
        if schedule.target_roles:
            # Role-based targeting
            role_users = await self._get_users_by_roles(schedule.target_roles)
            target_users.extend(role_users)
        
        if not target_users:
            return {
                'success': False,
                'total_users_notified': 0,
                'total_users_failed': 0,
                'error': 'No target users found'
            }
        
        # Use distribution manager to send reports
        return await self.distribution_manager.distribute_weekly_reports(
            start_date=schedule.customization_options.start_date,
            end_date=schedule.customization_options.end_date,
            force_distribution=schedule.force_delivery
        )
    
    async def _get_users_by_roles(self, roles: List[str]) -> List[int]:
        """Get user IDs that have any of the specified roles."""
        try:
            with get_db() as db:
                user_roles = db.query(UserRole.user_id).join(Role).filter(
                    UserRole.is_active == True,
                    Role.name.in_(roles),
                    Role.is_active == True
                ).distinct().all()
                
                return [user_id[0] for user_id in user_roles]
        except Exception as e:
            logger.error(f"Error getting users by roles: {e}")
            return []
    
    async def run_due_schedules(self) -> List[ScheduleExecution]:
        """Run all schedules that are due for execution."""
        due_schedules = []
        
        for schedule_id, schedule in self.active_schedules.items():
            if self._should_run_schedule(schedule):
                due_schedules.append(schedule_id)
        
        executions = []
        for schedule_id in due_schedules:
            try:
                execution = await self.execute_schedule(schedule_id)
                executions.append(execution)
            except Exception as e:
                logger.error(f"Error running schedule {schedule_id}: {e}")
        
        return executions
    
    def trigger_event(self, trigger_type: TriggerType, event_data: Dict[str, Any]) -> None:
        """Trigger an event-driven schedule."""
        if trigger_type not in self.event_listeners:
            return
        
        # Find schedules that match this trigger
        matching_schedules = [
            schedule_id for schedule_id, schedule in self.active_schedules.items()
            if (schedule.schedule_type == ScheduleType.EVENT_DRIVEN and
                schedule.trigger_type == trigger_type and
                self._check_trigger_conditions(schedule, event_data))
        ]
        
        # Execute matching schedules
        for schedule_id in matching_schedules:
            asyncio.create_task(self.execute_schedule(schedule_id, force=True))
    
    def _check_trigger_conditions(self, schedule: ScheduleConfig, event_data: Dict[str, Any]) -> bool:
        """Check if trigger conditions are met."""
        if not schedule.trigger_conditions:
            return True
        
        # Check threshold conditions
        if schedule.trigger_threshold:
            if schedule.trigger_type == TriggerType.CRITICAL_CHANGES:
                critical_changes = event_data.get('critical_changes', 0)
                if critical_changes < schedule.trigger_threshold:
                    return False
            
            elif schedule.trigger_type == TriggerType.HIGH_PRIORITY_CHANGES:
                high_priority_changes = event_data.get('high_priority_changes', 0)
                if high_priority_changes < schedule.trigger_threshold:
                    return False
        
        # Check custom conditions
        custom_conditions = schedule.trigger_conditions
        for condition_key, expected_value in custom_conditions.items():
            actual_value = event_data.get(condition_key)
            if actual_value != expected_value:
                return False
        
        return True
    
    def get_execution_history(
        self,
        schedule_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ScheduleExecution]:
        """Get execution history for schedules."""
        history = self.execution_history
        
        if schedule_id:
            history = [execution for execution in history if execution.schedule_id == schedule_id]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_schedule_statistics(self, schedule_id: str) -> Dict[str, Any]:
        """Get statistics for a specific schedule."""
        executions = self.get_execution_history(schedule_id)
        
        if not executions:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'skipped_executions': 0,
                'average_duration': 0,
                'last_execution': None
            }
        
        successful = len([e for e in executions if e.status == 'success'])
        failed = len([e for e in executions if e.status == 'failed'])
        skipped = len([e for e in executions if e.status == 'skipped'])
        
        durations = [e.execution_duration_seconds for e in executions if e.execution_duration_seconds]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_executions': len(executions),
            'successful_executions': successful,
            'failed_executions': failed,
            'skipped_executions': skipped,
            'success_rate': successful / len(executions) if executions else 0,
            'average_duration': avg_duration,
            'last_execution': executions[-1].execution_time if executions else None
        }
    
    def create_weekly_schedule(
        self,
        name: str,
        day_of_week: int = 0,  # Monday = 0
        hour: int = 9,
        minute: int = 0,
        timezone: str = "UTC",
        **kwargs
    ) -> ScheduleConfig:
        """Create a weekly schedule."""
        cron_expression = f"{minute} {hour} * * {day_of_week}"
        
        return self.create_schedule(
            name=name,
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            timezone=timezone,
            **kwargs
        )
    
    def create_daily_schedule(
        self,
        name: str,
        hour: int = 9,
        minute: int = 0,
        timezone: str = "UTC",
        **kwargs
    ) -> ScheduleConfig:
        """Create a daily schedule."""
        cron_expression = f"{minute} {hour} * * *"
        
        return self.create_schedule(
            name=name,
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            timezone=timezone,
            **kwargs
        )
    
    def create_event_driven_schedule(
        self,
        name: str,
        trigger_type: TriggerType,
        trigger_threshold: Optional[int] = None,
        trigger_conditions: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ScheduleConfig:
        """Create an event-driven schedule."""
        return self.create_schedule(
            name=name,
            schedule_type=ScheduleType.EVENT_DRIVEN,
            trigger_type=trigger_type,
            trigger_threshold=trigger_threshold,
            trigger_conditions=trigger_conditions,
            **kwargs
        )


def get_scheduler() -> ReportScheduler:
    """Get a scheduler instance."""
    return ReportScheduler()


def create_default_schedules(scheduler: ReportScheduler) -> Dict[str, ScheduleConfig]:
    """Create default schedules for the system."""
    default_schedules = {}
    
    # Weekly executive summary for product managers
    weekly_executive = scheduler.create_weekly_schedule(
        name="Weekly Executive Summary",
        day_of_week=0,  # Monday
        hour=8,
        minute=0,
        timezone="America/New_York",
        target_roles=['product_manager'],
        customization_options=ReportCustomizationOptions(
            template_type='executive_summary',
            severity_levels=['critical', 'high'],
            delivery_channels=['email', 'slack']
        )
    )
    default_schedules['weekly_executive'] = weekly_executive
    
    # Daily critical changes alert
    daily_critical = scheduler.create_event_driven_schedule(
        name="Daily Critical Changes Alert",
        trigger_type=TriggerType.CRITICAL_CHANGES,
        trigger_threshold=1,
        target_roles=['product_manager', 'admin'],
        customization_options=ReportCustomizationOptions(
            template_type='email_summary',
            severity_levels=['critical'],
            delivery_channels=['email', 'slack']
        )
    )
    default_schedules['daily_critical'] = daily_critical
    
    # Monthly detailed report for business analysts
    monthly_detailed = scheduler.create_weekly_schedule(
        name="Monthly Detailed Report",
        day_of_week=0,  # First Monday of month
        hour=9,
        minute=0,
        timezone="America/New_York",
        target_roles=['business_analyst'],
        customization_options=ReportCustomizationOptions(
            template_type='detailed_report',
            delivery_channels=['email']
        )
    )
    default_schedules['monthly_detailed'] = monthly_detailed
    
    return default_schedules 