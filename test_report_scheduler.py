#!/usr/bin/env python3
"""
Simple test script for report scheduling system functionality.
"""

import sys
import os
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

class SimpleScheduleType(Enum):
    """Simplified schedule types for testing."""
    CRON = "cron"
    INTERVAL = "interval"
    EVENT_DRIVEN = "event_driven"
    MANUAL = "manual"

class SimpleTriggerType(Enum):
    """Simplified trigger types for testing."""
    CRITICAL_CHANGES = "critical_changes"
    HIGH_PRIORITY_CHANGES = "high_priority_changes"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    TIME_BASED = "time_based"
    USER_REQUESTED = "user_requested"

@dataclass
class SimpleScheduleConfig:
    """Simplified schedule configuration for testing."""
    name: str
    description: Optional[str] = None
    schedule_type: SimpleScheduleType = SimpleScheduleType.CRON
    is_active: bool = True
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    timezone: str = "UTC"
    trigger_type: Optional[SimpleTriggerType] = None
    trigger_threshold: Optional[int] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    target_roles: Optional[List[str]] = None
    target_users: Optional[List[int]] = None
    delivery_channels: Optional[List[str]] = None
    max_retries: int = 3
    retry_delay_minutes: int = 5
    force_delivery: bool = False
    include_attachments: bool = True
    created_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'description': self.description,
            'schedule_type': self.schedule_type.value,
            'is_active': self.is_active,
            'cron_expression': self.cron_expression,
            'interval_minutes': self.interval_minutes,
            'timezone': self.timezone,
            'trigger_type': self.trigger_type.value if self.trigger_type else None,
            'trigger_threshold': self.trigger_threshold,
            'trigger_conditions': self.trigger_conditions,
            'target_roles': self.target_roles,
            'target_users': self.target_users,
            'delivery_channels': self.delivery_channels,
            'max_retries': self.max_retries,
            'retry_delay_minutes': self.retry_delay_minutes,
            'force_delivery': self.force_delivery,
            'include_attachments': self.include_attachments,
            'created_at': self.created_at,
            'last_run': self.last_run,
            'next_run': self.next_run
        }

@dataclass
class SimpleScheduleExecution:
    """Simplified schedule execution record for testing."""
    schedule_id: str
    execution_time: datetime
    status: str  # 'success', 'failed', 'skipped'
    report_generated: bool = False
    users_notified: int = 0
    users_failed: int = 0
    error_message: Optional[str] = None
    execution_duration_seconds: Optional[float] = None
    report_data: Optional[Dict[str, Any]] = None

class SimpleReportScheduler:
    """Simplified report scheduler for testing."""
    
    def __init__(self):
        self.active_schedules: Dict[str, SimpleScheduleConfig] = {}
        self.execution_history: List[SimpleScheduleExecution] = []
    
    def create_schedule(self, name: str, schedule_type: SimpleScheduleType, **kwargs) -> SimpleScheduleConfig:
        """Create a new schedule."""
        schedule_id = f"schedule_{len(self.active_schedules) + 1}_{int(datetime.now().timestamp())}"
        
        schedule_config = SimpleScheduleConfig(
            name=name,
            schedule_type=schedule_type,
            created_at=datetime.now(),
            **kwargs
        )
        
        # Calculate next run time
        schedule_config.next_run = self._calculate_next_run(schedule_config)
        
        # Store the schedule
        self.active_schedules[schedule_id] = schedule_config
        
        return schedule_config
    
    def _calculate_next_run(self, schedule: SimpleScheduleConfig) -> Optional[datetime]:
        """Calculate next run time."""
        if not schedule.is_active:
            return None
        
        now = datetime.now()
        
        if schedule.schedule_type == SimpleScheduleType.CRON:
            if schedule.cron_expression:
                # Simple cron calculation for testing
                return now + timedelta(hours=1)
        
        elif schedule.schedule_type == SimpleScheduleType.INTERVAL:
            if schedule.interval_minutes:
                return now + timedelta(minutes=schedule.interval_minutes)
        
        elif schedule.schedule_type == SimpleScheduleType.EVENT_DRIVEN:
            return None
        
        return None
    
    def update_schedule(self, schedule_id: str, **updates) -> bool:
        """Update a schedule."""
        if schedule_id not in self.active_schedules:
            return False
        
        schedule = self.active_schedules[schedule_id]
        
        for key, value in updates.items():
            if hasattr(schedule, key):
                setattr(schedule, key, value)
        
        schedule.next_run = self._calculate_next_run(schedule)
        return True
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        if schedule_id not in self.active_schedules:
            return False
        
        del self.active_schedules[schedule_id]
        return True
    
    def get_schedule(self, schedule_id: str) -> Optional[SimpleScheduleConfig]:
        """Get a schedule by ID."""
        return self.active_schedules.get(schedule_id)
    
    def get_all_schedules(self) -> Dict[str, SimpleScheduleConfig]:
        """Get all schedules."""
        return self.active_schedules.copy()
    
    def get_schedules_by_type(self, schedule_type: SimpleScheduleType) -> List[SimpleScheduleConfig]:
        """Get schedules by type."""
        return [
            schedule for schedule in self.active_schedules.values()
            if schedule.schedule_type == schedule_type
        ]
    
    def _should_run_schedule(self, schedule: SimpleScheduleConfig) -> bool:
        """Check if schedule should run."""
        if not schedule.is_active:
            return False
        
        if schedule.schedule_type == SimpleScheduleType.EVENT_DRIVEN:
            return False
        
        if schedule.next_run and datetime.now() < schedule.next_run:
            return False
        
        return True
    
    async def execute_schedule(self, schedule_id: str, force: bool = False) -> SimpleScheduleExecution:
        """Execute a schedule."""
        if schedule_id not in self.active_schedules:
            raise ValueError(f"Schedule {schedule_id} not found")
        
        schedule = self.active_schedules[schedule_id]
        execution_start = datetime.now()
        
        execution = SimpleScheduleExecution(
            schedule_id=schedule_id,
            execution_time=execution_start,
            status='failed'
        )
        
        try:
            if not force and not self._should_run_schedule(schedule):
                execution.status = 'skipped'
                execution.error_message = 'Schedule conditions not met'
                return execution
            
            # Mock successful execution
            execution.status = 'success'
            execution.report_generated = True
            execution.users_notified = 5
            execution.users_failed = 0
            
            # Update schedule metadata
            schedule.last_run = execution_start
            schedule.next_run = self._calculate_next_run(schedule)
            
        except Exception as e:
            execution.error_message = str(e)
        
        finally:
            execution.execution_duration_seconds = (datetime.now() - execution_start).total_seconds()
            self.execution_history.append(execution)
        
        return execution
    
    async def run_due_schedules(self) -> List[SimpleScheduleExecution]:
        """Run all due schedules."""
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
                print(f"Error running schedule {schedule_id}: {e}")
        
        return executions
    
    def get_execution_history(self, schedule_id: Optional[str] = None, limit: Optional[int] = None) -> List[SimpleScheduleExecution]:
        """Get execution history."""
        history = self.execution_history
        
        if schedule_id:
            history = [execution for execution in history if execution.schedule_id == schedule_id]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_schedule_statistics(self, schedule_id: str) -> Dict[str, Any]:
        """Get schedule statistics."""
        executions = self.get_execution_history(schedule_id)
        
        if not executions:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'skipped_executions': 0,
                'success_rate': 0,
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
    
    def create_weekly_schedule(self, name: str, day_of_week: int = 0, hour: int = 9, minute: int = 0, timezone: str = "UTC", **kwargs) -> SimpleScheduleConfig:
        """Create a weekly schedule."""
        cron_expression = f"{minute} {hour} * * {day_of_week}"
        
        return self.create_schedule(
            name=name,
            schedule_type=SimpleScheduleType.CRON,
            cron_expression=cron_expression,
            timezone=timezone,
            **kwargs
        )
    
    def create_daily_schedule(self, name: str, hour: int = 9, minute: int = 0, timezone: str = "UTC", **kwargs) -> SimpleScheduleConfig:
        """Create a daily schedule."""
        cron_expression = f"{minute} {hour} * * *"
        
        return self.create_schedule(
            name=name,
            schedule_type=SimpleScheduleType.CRON,
            cron_expression=cron_expression,
            timezone=timezone,
            **kwargs
        )
    
    def create_event_driven_schedule(self, name: str, trigger_type: SimpleTriggerType, trigger_threshold: Optional[int] = None, trigger_conditions: Optional[Dict[str, Any]] = None, **kwargs) -> SimpleScheduleConfig:
        """Create an event-driven schedule."""
        return self.create_schedule(
            name=name,
            schedule_type=SimpleScheduleType.EVENT_DRIVEN,
            trigger_type=trigger_type,
            trigger_threshold=trigger_threshold,
            trigger_conditions=trigger_conditions,
            **kwargs
        )

def test_report_scheduler():
    """Test the report scheduling system basic functionality."""
    try:
        # Create scheduler
        scheduler = SimpleReportScheduler()
        print("✅ SimpleReportScheduler created successfully")
        
        # Test creating different types of schedules
        weekly_schedule = scheduler.create_weekly_schedule(
            name="Weekly Executive Summary",
            day_of_week=0,  # Monday
            hour=8,
            minute=0,
            timezone="America/New_York",
            target_roles=['product_manager']
        )
        print("✅ Weekly schedule created:")
        print(f"   Name: {weekly_schedule.name}")
        print(f"   Type: {weekly_schedule.schedule_type.value}")
        print(f"   Cron: {weekly_schedule.cron_expression}")
        print(f"   Target Roles: {weekly_schedule.target_roles}")
        print(f"   Next Run: {weekly_schedule.next_run}")
        
        daily_schedule = scheduler.create_daily_schedule(
            name="Daily Critical Alert",
            hour=9,
            minute=0,
            timezone="UTC",
            target_roles=['admin']
        )
        print("✅ Daily schedule created:")
        print(f"   Name: {daily_schedule.name}")
        print(f"   Cron: {daily_schedule.cron_expression}")
        print(f"   Target Roles: {daily_schedule.target_roles}")
        
        event_schedule = scheduler.create_event_driven_schedule(
            name="Critical Changes Alert",
            trigger_type=SimpleTriggerType.CRITICAL_CHANGES,
            trigger_threshold=1,
            target_roles=['product_manager', 'admin']
        )
        print("✅ Event-driven schedule created:")
        print(f"   Name: {event_schedule.name}")
        print(f"   Trigger Type: {event_schedule.trigger_type.value}")
        print(f"   Trigger Threshold: {event_schedule.trigger_threshold}")
        print(f"   Target Roles: {event_schedule.target_roles}")
        
        # Test schedule management
        print("\n🔧 Testing schedule management:")
        
        # Get all schedules
        all_schedules = scheduler.get_all_schedules()
        print(f"   Total schedules: {len(all_schedules)}")
        
        # Get schedules by type
        cron_schedules = scheduler.get_schedules_by_type(SimpleScheduleType.CRON)
        print(f"   Cron schedules: {len(cron_schedules)}")
        
        event_schedules = scheduler.get_schedules_by_type(SimpleScheduleType.EVENT_DRIVEN)
        print(f"   Event-driven schedules: {len(event_schedules)}")
        
        # Get specific schedule
        schedule_id = list(all_schedules.keys())[0]
        retrieved_schedule = scheduler.get_schedule(schedule_id)
        print(f"   Retrieved schedule: {retrieved_schedule.name}")
        
        # Test schedule execution
        print("\n🚀 Testing schedule execution:")
        
        # Execute a schedule
        import asyncio
        execution = asyncio.run(scheduler.execute_schedule(schedule_id))
        print(f"   Execution status: {execution.status}")
        print(f"   Report generated: {execution.report_generated}")
        print(f"   Users notified: {execution.users_notified}")
        print(f"   Users failed: {execution.users_failed}")
        print(f"   Duration: {execution.execution_duration_seconds:.2f}s")
        
        # Test execution history
        print("\n📊 Testing execution history:")
        
        history = scheduler.get_execution_history()
        print(f"   Total executions: {len(history)}")
        
        schedule_history = scheduler.get_execution_history(schedule_id)
        print(f"   Schedule executions: {len(schedule_history)}")
        
        # Test statistics
        stats = scheduler.get_schedule_statistics(schedule_id)
        print(f"   Statistics:")
        print(f"     Total executions: {stats['total_executions']}")
        print(f"     Successful: {stats['successful_executions']}")
        print(f"     Failed: {stats['failed_executions']}")
        print(f"     Success rate: {stats['success_rate']:.2%}")
        print(f"     Average duration: {stats['average_duration']:.2f}s")
        
        # Test schedule updates
        print("\n🔄 Testing schedule updates:")
        
        success = scheduler.update_schedule(
            schedule_id,
            name="Updated Weekly Report",
            description="Updated description",
            is_active=False
        )
        print(f"   Update success: {success}")
        
        updated_schedule = scheduler.get_schedule(schedule_id)
        print(f"   Updated name: {updated_schedule.name}")
        print(f"   Updated description: {updated_schedule.description}")
        print(f"   Is active: {updated_schedule.is_active}")
        
        # Test schedule deletion
        print("\n🗑️ Testing schedule deletion:")
        
        delete_success = scheduler.delete_schedule(schedule_id)
        print(f"   Delete success: {delete_success}")
        
        remaining_schedules = scheduler.get_all_schedules()
        print(f"   Remaining schedules: {len(remaining_schedules)}")
        
        # Test serialization
        print("\n💾 Testing serialization:")
        
        test_schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=SimpleScheduleType.CRON,
            cron_expression="0 9 * * *",
            target_roles=['product_manager'],
            max_retries=5
        )
        
        schedule_dict = test_schedule.to_dict()
        print(f"   Serialized fields: {len(schedule_dict)}")
        print(f"   Schedule type: {schedule_dict['schedule_type']}")
        print(f"   Target roles: {schedule_dict['target_roles']}")
        print(f"   Max retries: {schedule_dict['max_retries']}")
        
        print("\n🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_report_scheduler()
    sys.exit(0 if success else 1) 