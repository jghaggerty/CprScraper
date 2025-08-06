"""
Unit tests for report scheduling system.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

from src.reporting.report_scheduler import (
    ReportScheduler, ScheduleConfig, ScheduleExecution, ScheduleType, TriggerType,
    get_scheduler, create_default_schedules
)
from src.reporting.report_customization import ReportCustomizationOptions, ReportFrequency


class TestScheduleType:
    """Test the ScheduleType enum."""
    
    def test_schedule_type_values(self):
        """Test that all schedule type values are correct."""
        assert ScheduleType.CRON.value == "cron"
        assert ScheduleType.INTERVAL.value == "interval"
        assert ScheduleType.EVENT_DRIVEN.value == "event_driven"
        assert ScheduleType.MANUAL.value == "manual"
    
    def test_schedule_type_creation(self):
        """Test creating schedule type from string."""
        assert ScheduleType("cron") == ScheduleType.CRON
        assert ScheduleType("interval") == ScheduleType.INTERVAL
        assert ScheduleType("event_driven") == ScheduleType.EVENT_DRIVEN


class TestTriggerType:
    """Test the TriggerType enum."""
    
    def test_trigger_type_values(self):
        """Test that all trigger type values are correct."""
        assert TriggerType.CRITICAL_CHANGES.value == "critical_changes"
        assert TriggerType.HIGH_PRIORITY_CHANGES.value == "high_priority_changes"
        assert TriggerType.THRESHOLD_EXCEEDED.value == "threshold_exceeded"
        assert TriggerType.TIME_BASED.value == "time_based"
        assert TriggerType.USER_REQUESTED.value == "user_requested"
    
    def test_trigger_type_creation(self):
        """Test creating trigger type from string."""
        assert TriggerType("critical_changes") == TriggerType.CRITICAL_CHANGES
        assert TriggerType("high_priority_changes") == TriggerType.HIGH_PRIORITY_CHANGES


class TestScheduleConfig:
    """Test the ScheduleConfig dataclass."""
    
    def test_schedule_config_creation(self):
        """Test creating schedule config."""
        config = ScheduleConfig(
            name="Test Schedule",
            description="Test description",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 9 * * *",
            timezone="America/New_York",
            target_roles=['product_manager'],
            is_active=True
        )
        
        assert config.name == "Test Schedule"
        assert config.description == "Test description"
        assert config.schedule_type == ScheduleType.CRON
        assert config.cron_expression == "0 9 * * *"
        assert config.timezone == "America/New_York"
        assert config.target_roles == ['product_manager']
        assert config.is_active is True
        assert config.max_retries == 3
        assert config.retry_delay_minutes == 5
    
    def test_schedule_config_defaults(self):
        """Test default values for schedule config."""
        config = ScheduleConfig(name="Test Schedule")
        
        assert config.name == "Test Schedule"
        assert config.description is None
        assert config.schedule_type == ScheduleType.CRON
        assert config.is_active is True
        assert config.timezone == "UTC"
        assert config.max_retries == 3
        assert config.retry_delay_minutes == 5
        assert config.force_delivery is False
        assert config.include_attachments is True
    
    def test_schedule_config_to_dict(self):
        """Test converting config to dictionary."""
        config = ScheduleConfig(
            name="Test Schedule",
            schedule_type=ScheduleType.EVENT_DRIVEN,
            trigger_type=TriggerType.CRITICAL_CHANGES,
            cron_expression="0 9 * * *",
            target_roles=['product_manager']
        )
        
        data = config.to_dict()
        
        assert data['name'] == "Test Schedule"
        assert data['schedule_type'] == "event_driven"
        assert data['trigger_type'] == "critical_changes"
        assert data['cron_expression'] == "0 9 * * *"
        assert data['target_roles'] == ['product_manager']
        assert data['is_active'] is True
    
    def test_schedule_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            'name': 'Test Schedule',
            'schedule_type': 'cron',
            'trigger_type': 'critical_changes',
            'cron_expression': '0 9 * * *',
            'target_roles': ['product_manager'],
            'is_active': True,
            'max_retries': 5
        }
        
        config = ScheduleConfig.from_dict(data)
        
        assert config.name == "Test Schedule"
        assert config.schedule_type == ScheduleType.CRON
        assert config.trigger_type == TriggerType.CRITICAL_CHANGES
        assert config.cron_expression == "0 9 * * *"
        assert config.target_roles == ['product_manager']
        assert config.is_active is True
        assert config.max_retries == 5


class TestScheduleExecution:
    """Test the ScheduleExecution dataclass."""
    
    def test_schedule_execution_creation(self):
        """Test creating schedule execution."""
        execution_time = datetime.now()
        execution = ScheduleExecution(
            schedule_id="test_schedule_1",
            execution_time=execution_time,
            status="success",
            report_generated=True,
            users_notified=5,
            users_failed=0,
            execution_duration_seconds=10.5
        )
        
        assert execution.schedule_id == "test_schedule_1"
        assert execution.execution_time == execution_time
        assert execution.status == "success"
        assert execution.report_generated is True
        assert execution.users_notified == 5
        assert execution.users_failed == 0
        assert execution.execution_duration_seconds == 10.5
        assert execution.error_message is None
    
    def test_schedule_execution_defaults(self):
        """Test default values for schedule execution."""
        execution_time = datetime.now()
        execution = ScheduleExecution(
            schedule_id="test_schedule_1",
            execution_time=execution_time,
            status="failed"
        )
        
        assert execution.schedule_id == "test_schedule_1"
        assert execution.execution_time == execution_time
        assert execution.status == "failed"
        assert execution.report_generated is False
        assert execution.users_notified == 0
        assert execution.users_failed == 0
        assert execution.execution_duration_seconds is None
        assert execution.error_message is None


class TestReportScheduler:
    """Test the report scheduler functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create a scheduler instance."""
        return ReportScheduler()
    
    @pytest.fixture
    def sample_customization_options(self):
        """Create sample customization options."""
        return ReportCustomizationOptions(
            frequency=ReportFrequency.WEEKLY,
            template_type='executive_summary',
            delivery_channels=['email']
        )
    
    def test_scheduler_initialization(self, scheduler):
        """Test that scheduler initializes correctly."""
        assert scheduler is not None
        assert hasattr(scheduler, 'customization_manager')
        assert hasattr(scheduler, 'distribution_manager')
        assert hasattr(scheduler, 'notifier')
        assert hasattr(scheduler, 'active_schedules')
        assert hasattr(scheduler, 'execution_history')
        assert hasattr(scheduler, 'event_listeners')
        
        # Check event listeners
        for trigger_type in TriggerType:
            assert trigger_type in scheduler.event_listeners
    
    def test_create_schedule(self, scheduler, sample_customization_options):
        """Test creating a schedule."""
        schedule = scheduler.create_schedule(
            name="Test Weekly Report",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 9 * * 1",
            timezone="America/New_York",
            target_roles=['product_manager'],
            customization_options=sample_customization_options
        )
        
        assert schedule.name == "Test Weekly Report"
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expression == "0 9 * * 1"
        assert schedule.timezone == "America/New_York"
        assert schedule.target_roles == ['product_manager']
        assert schedule.customization_options == sample_customization_options
        assert schedule.is_active is True
        assert schedule.created_at is not None
        assert schedule.next_run is not None
        
        # Check that schedule was stored
        assert len(scheduler.active_schedules) == 1
    
    def test_create_schedule_with_defaults(self, scheduler):
        """Test creating a schedule with default customization options."""
        schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=ScheduleType.INTERVAL,
            interval_minutes=60
        )
        
        assert schedule.name == "Test Schedule"
        assert schedule.schedule_type == ScheduleType.INTERVAL
        assert schedule.interval_minutes == 60
        assert schedule.customization_options is not None
        assert schedule.is_active is True
    
    def test_update_schedule(self, scheduler):
        """Test updating a schedule."""
        # Create a schedule first
        schedule = scheduler.create_schedule(
            name="Original Name",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 9 * * *"
        )
        
        # Get the schedule ID
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Update the schedule
        success = scheduler.update_schedule(
            schedule_id,
            name="Updated Name",
            description="Updated description",
            is_active=False
        )
        
        assert success is True
        
        # Verify changes
        updated_schedule = scheduler.get_schedule(schedule_id)
        assert updated_schedule.name == "Updated Name"
        assert updated_schedule.description == "Updated description"
        assert updated_schedule.is_active is False
    
    def test_update_schedule_not_found(self, scheduler):
        """Test updating a non-existent schedule."""
        success = scheduler.update_schedule("non_existent_id", name="New Name")
        assert success is False
    
    def test_delete_schedule(self, scheduler):
        """Test deleting a schedule."""
        # Create a schedule first
        schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON
        )
        
        # Get the schedule ID
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Delete the schedule
        success = scheduler.delete_schedule(schedule_id)
        assert success is True
        
        # Verify it's gone
        assert len(scheduler.active_schedules) == 0
        assert scheduler.get_schedule(schedule_id) is None
    
    def test_delete_schedule_not_found(self, scheduler):
        """Test deleting a non-existent schedule."""
        success = scheduler.delete_schedule("non_existent_id")
        assert success is False
    
    def test_get_schedule(self, scheduler):
        """Test getting a schedule by ID."""
        # Create a schedule first
        schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON
        )
        
        # Get the schedule ID
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Retrieve the schedule
        retrieved_schedule = scheduler.get_schedule(schedule_id)
        assert retrieved_schedule is not None
        assert retrieved_schedule.name == "Test Schedule"
    
    def test_get_all_schedules(self, scheduler):
        """Test getting all schedules."""
        # Create multiple schedules
        scheduler.create_schedule("Schedule 1", ScheduleType.CRON)
        scheduler.create_schedule("Schedule 2", ScheduleType.INTERVAL)
        scheduler.create_schedule("Schedule 3", ScheduleType.EVENT_DRIVEN)
        
        all_schedules = scheduler.get_all_schedules()
        assert len(all_schedules) == 3
        
        # Verify it's a copy
        all_schedules.clear()
        assert len(scheduler.active_schedules) == 3
    
    def test_get_schedules_by_type(self, scheduler):
        """Test getting schedules by type."""
        # Create schedules of different types
        scheduler.create_schedule("Cron Schedule", ScheduleType.CRON)
        scheduler.create_schedule("Interval Schedule", ScheduleType.INTERVAL)
        scheduler.create_schedule("Event Schedule", ScheduleType.EVENT_DRIVEN)
        scheduler.create_schedule("Another Cron", ScheduleType.CRON)
        
        cron_schedules = scheduler.get_schedules_by_type(ScheduleType.CRON)
        assert len(cron_schedules) == 2
        
        interval_schedules = scheduler.get_schedules_by_type(ScheduleType.INTERVAL)
        assert len(interval_schedules) == 1
        
        event_schedules = scheduler.get_schedules_by_type(ScheduleType.EVENT_DRIVEN)
        assert len(event_schedules) == 1
    
    @patch.object(ReportScheduler, '_user_has_role')
    def test_get_schedules_for_user(self, mock_user_has_role, scheduler):
        """Test getting schedules for a specific user."""
        # Mock user role check
        mock_user_has_role.return_value = True
        
        # Create schedules with different targeting
        scheduler.create_schedule(
            "User Schedule",
            ScheduleType.CRON,
            target_users=[1, 2, 3]
        )
        scheduler.create_schedule(
            "Role Schedule",
            ScheduleType.CRON,
            target_roles=['product_manager']
        )
        scheduler.create_schedule(
            "No Target Schedule",
            ScheduleType.CRON
        )
        
        user_schedules = scheduler.get_schedules_for_user(1)
        assert len(user_schedules) == 2  # User schedule and role schedule
    
    @patch('src.reporting.report_scheduler.get_db')
    def test_user_has_role(self, mock_get_db, scheduler):
        """Test checking if user has role."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock query result
        mock_user_role = Mock()
        mock_user_role.user_id = 1
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [mock_user_role]
        
        has_role = scheduler._user_has_role(1, ['product_manager'])
        assert has_role is True
    
    @patch('src.reporting.report_scheduler.get_db')
    def test_user_has_role_no_match(self, mock_get_db, scheduler):
        """Test checking if user has role when no match."""
        # Mock database session
        mock_db = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        
        # Mock empty query result
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        has_role = scheduler._user_has_role(1, ['product_manager'])
        assert has_role is False
    
    @patch.object(ReportScheduler, '_should_run_schedule')
    @patch.object(ReportScheduler, '_generate_scheduled_report')
    @patch.object(ReportScheduler, '_distribute_scheduled_report')
    async def test_execute_schedule_success(self, mock_distribute, mock_generate, mock_should_run, scheduler):
        """Test successful schedule execution."""
        # Mock schedule should run
        mock_should_run.return_value = True
        
        # Mock report generation
        mock_generate.return_value = {
            'success': True,
            'report_data': {'test': 'data'}
        }
        
        # Mock distribution
        mock_distribute.return_value = {
            'success': True,
            'total_users_notified': 5,
            'total_users_failed': 0
        }
        
        # Create a schedule
        schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON
        )
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Execute the schedule
        execution = await scheduler.execute_schedule(schedule_id)
        
        assert execution.status == "success"
        assert execution.report_generated is True
        assert execution.users_notified == 5
        assert execution.users_failed == 0
        assert execution.error_message is None
        assert execution.execution_duration_seconds is not None
    
    @patch.object(ReportScheduler, '_should_run_schedule')
    async def test_execute_schedule_skipped(self, mock_should_run, scheduler):
        """Test schedule execution when conditions not met."""
        # Mock schedule should not run
        mock_should_run.return_value = False
        
        # Create a schedule
        schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON
        )
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Execute the schedule
        execution = await scheduler.execute_schedule(schedule_id)
        
        assert execution.status == "skipped"
        assert execution.error_message == "Schedule conditions not met"
    
    @patch.object(ReportScheduler, '_should_run_schedule')
    @patch.object(ReportScheduler, '_generate_scheduled_report')
    async def test_execute_schedule_failed(self, mock_generate, mock_should_run, scheduler):
        """Test schedule execution when report generation fails."""
        # Mock schedule should run
        mock_should_run.return_value = True
        
        # Mock report generation failure
        mock_generate.return_value = {
            'success': False,
            'error': 'Report generation failed'
        }
        
        # Create a schedule
        schedule = scheduler.create_schedule(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON
        )
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Execute the schedule
        execution = await scheduler.execute_schedule(schedule_id)
        
        assert execution.status == "failed"
        assert execution.error_message == "Report generation failed"
    
    def test_should_run_schedule_active(self, scheduler):
        """Test schedule should run when active."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            next_run=datetime.now() - timedelta(minutes=1)  # Past due
        )
        
        should_run = scheduler._should_run_schedule(schedule)
        assert should_run is True
    
    def test_should_run_schedule_inactive(self, scheduler):
        """Test schedule should not run when inactive."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            is_active=False
        )
        
        should_run = scheduler._should_run_schedule(schedule)
        assert should_run is False
    
    def test_should_run_schedule_not_due(self, scheduler):
        """Test schedule should not run when not due."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            next_run=datetime.now() + timedelta(hours=1)  # Future
        )
        
        should_run = scheduler._should_run_schedule(schedule)
        assert should_run is False
    
    def test_should_run_schedule_event_driven(self, scheduler):
        """Test event-driven schedule should not run automatically."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            schedule_type=ScheduleType.EVENT_DRIVEN,
            is_active=True
        )
        
        should_run = scheduler._should_run_schedule(schedule)
        assert should_run is False
    
    @patch.object(ReportScheduler, 'execute_schedule')
    async def test_run_due_schedules(self, mock_execute, scheduler):
        """Test running all due schedules."""
        # Create schedules
        scheduler.create_schedule("Schedule 1", ScheduleType.CRON)
        scheduler.create_schedule("Schedule 2", ScheduleType.INTERVAL)
        
        # Mock execution
        mock_execution = Mock()
        mock_execution.status = "success"
        mock_execute.return_value = mock_execution
        
        # Mock _should_run_schedule to return True for all schedules
        with patch.object(scheduler, '_should_run_schedule', return_value=True):
            executions = await scheduler.run_due_schedules()
        
        assert len(executions) == 2
        mock_execute.assert_called()
    
    def test_trigger_event(self, scheduler):
        """Test triggering an event."""
        # Create an event-driven schedule
        schedule = scheduler.create_schedule(
            name="Critical Changes Alert",
            schedule_type=ScheduleType.EVENT_DRIVEN,
            trigger_type=TriggerType.CRITICAL_CHANGES,
            trigger_threshold=1
        )
        
        # Mock execute_schedule
        with patch.object(scheduler, 'execute_schedule') as mock_execute:
            scheduler.trigger_event(TriggerType.CRITICAL_CHANGES, {'critical_changes': 2})
            
            # Should trigger the schedule
            mock_execute.assert_called()
    
    def test_check_trigger_conditions_threshold_met(self, scheduler):
        """Test trigger conditions when threshold is met."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            trigger_type=TriggerType.CRITICAL_CHANGES,
            trigger_threshold=1
        )
        
        event_data = {'critical_changes': 2}
        conditions_met = scheduler._check_trigger_conditions(schedule, event_data)
        assert conditions_met is True
    
    def test_check_trigger_conditions_threshold_not_met(self, scheduler):
        """Test trigger conditions when threshold is not met."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            trigger_type=TriggerType.CRITICAL_CHANGES,
            trigger_threshold=5
        )
        
        event_data = {'critical_changes': 2}
        conditions_met = scheduler._check_trigger_conditions(schedule, event_data)
        assert conditions_met is False
    
    def test_check_trigger_conditions_custom_conditions(self, scheduler):
        """Test trigger conditions with custom conditions."""
        schedule = ScheduleConfig(
            name="Test Schedule",
            trigger_conditions={'state': 'CA', 'form_type': 'WH-347'}
        )
        
        event_data = {'state': 'CA', 'form_type': 'WH-347', 'critical_changes': 1}
        conditions_met = scheduler._check_trigger_conditions(schedule, event_data)
        assert conditions_met is True
    
    def test_get_execution_history(self, scheduler):
        """Test getting execution history."""
        # Create some mock executions
        execution1 = ScheduleExecution(
            schedule_id="schedule_1",
            execution_time=datetime.now(),
            status="success"
        )
        execution2 = ScheduleExecution(
            schedule_id="schedule_1",
            execution_time=datetime.now(),
            status="failed"
        )
        execution3 = ScheduleExecution(
            schedule_id="schedule_2",
            execution_time=datetime.now(),
            status="success"
        )
        
        scheduler.execution_history = [execution1, execution2, execution3]
        
        # Get all history
        all_history = scheduler.get_execution_history()
        assert len(all_history) == 3
        
        # Get history for specific schedule
        schedule_history = scheduler.get_execution_history("schedule_1")
        assert len(schedule_history) == 2
        
        # Get history with limit
        limited_history = scheduler.get_execution_history(limit=2)
        assert len(limited_history) == 2
    
    def test_get_schedule_statistics(self, scheduler):
        """Test getting schedule statistics."""
        # Create mock executions
        execution1 = ScheduleExecution(
            schedule_id="schedule_1",
            execution_time=datetime.now(),
            status="success",
            execution_duration_seconds=10.0
        )
        execution2 = ScheduleExecution(
            schedule_id="schedule_1",
            execution_time=datetime.now(),
            status="success",
            execution_duration_seconds=15.0
        )
        execution3 = ScheduleExecution(
            schedule_id="schedule_1",
            execution_time=datetime.now(),
            status="failed",
            execution_duration_seconds=5.0
        )
        
        scheduler.execution_history = [execution1, execution2, execution3]
        
        stats = scheduler.get_schedule_statistics("schedule_1")
        
        assert stats['total_executions'] == 3
        assert stats['successful_executions'] == 2
        assert stats['failed_executions'] == 1
        assert stats['skipped_executions'] == 0
        assert stats['success_rate'] == 2/3
        assert stats['average_duration'] == 10.0  # (10 + 15 + 5) / 3
        assert stats['last_execution'] is not None
    
    def test_create_weekly_schedule(self, scheduler):
        """Test creating a weekly schedule."""
        schedule = scheduler.create_weekly_schedule(
            name="Weekly Report",
            day_of_week=1,  # Tuesday
            hour=10,
            minute=30,
            timezone="America/New_York"
        )
        
        assert schedule.name == "Weekly Report"
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expression == "30 10 * * 1"
        assert schedule.timezone == "America/New_York"
    
    def test_create_daily_schedule(self, scheduler):
        """Test creating a daily schedule."""
        schedule = scheduler.create_daily_schedule(
            name="Daily Report",
            hour=9,
            minute=0,
            timezone="UTC"
        )
        
        assert schedule.name == "Daily Report"
        assert schedule.schedule_type == ScheduleType.CRON
        assert schedule.cron_expression == "0 9 * * *"
        assert schedule.timezone == "UTC"
    
    def test_create_event_driven_schedule(self, scheduler):
        """Test creating an event-driven schedule."""
        schedule = scheduler.create_event_driven_schedule(
            name="Critical Alert",
            trigger_type=TriggerType.CRITICAL_CHANGES,
            trigger_threshold=3,
            trigger_conditions={'state': 'CA'}
        )
        
        assert schedule.name == "Critical Alert"
        assert schedule.schedule_type == ScheduleType.EVENT_DRIVEN
        assert schedule.trigger_type == TriggerType.CRITICAL_CHANGES
        assert schedule.trigger_threshold == 3
        assert schedule.trigger_conditions == {'state': 'CA'}


class TestSchedulerConvenienceFunctions:
    """Test convenience functions for report scheduling."""
    
    def test_get_scheduler(self):
        """Test getting scheduler instance."""
        scheduler = get_scheduler()
        
        assert isinstance(scheduler, ReportScheduler)
        assert hasattr(scheduler, 'create_schedule')
        assert hasattr(scheduler, 'execute_schedule')
    
    def test_create_default_schedules(self):
        """Test creating default schedules."""
        scheduler = get_scheduler()
        default_schedules = create_default_schedules(scheduler)
        
        assert len(default_schedules) == 3
        
        # Check weekly executive schedule
        weekly_executive = default_schedules['weekly_executive']
        assert weekly_executive.name == "Weekly Executive Summary"
        assert weekly_executive.target_roles == ['product_manager']
        assert weekly_executive.customization_options.template_type == 'executive_summary'
        
        # Check daily critical schedule
        daily_critical = default_schedules['daily_critical']
        assert daily_critical.name == "Daily Critical Changes Alert"
        assert daily_critical.trigger_type == TriggerType.CRITICAL_CHANGES
        assert daily_critical.trigger_threshold == 1
        
        # Check monthly detailed schedule
        monthly_detailed = default_schedules['monthly_detailed']
        assert monthly_detailed.name == "Monthly Detailed Report"
        assert monthly_detailed.target_roles == ['business_analyst']
        assert monthly_detailed.customization_options.template_type == 'detailed_report'


class TestSchedulerIntegration:
    """Integration tests for report scheduling."""
    
    @pytest.fixture
    def scheduler(self):
        return ReportScheduler()
    
    async def test_full_scheduling_workflow(self, scheduler):
        """Test the complete scheduling workflow."""
        # Create a schedule
        schedule = scheduler.create_schedule(
            name="Test Weekly Report",
            schedule_type=ScheduleType.CRON,
            cron_expression="0 9 * * 1",
            target_roles=['product_manager'],
            customization_options=ReportCustomizationOptions(
                template_type='executive_summary',
                delivery_channels=['email']
            )
        )
        
        # Get schedule ID
        schedule_id = list(scheduler.active_schedules.keys())[0]
        
        # Verify schedule was created
        retrieved_schedule = scheduler.get_schedule(schedule_id)
        assert retrieved_schedule.name == "Test Weekly Report"
        assert retrieved_schedule.is_active is True
        
        # Get schedules by type
        cron_schedules = scheduler.get_schedules_by_type(ScheduleType.CRON)
        assert len(cron_schedules) == 1
        
        # Test schedule execution (with mocked dependencies)
        with patch.object(scheduler, '_should_run_schedule', return_value=True):
            with patch.object(scheduler, '_generate_scheduled_report') as mock_generate:
                with patch.object(scheduler, '_distribute_scheduled_report') as mock_distribute:
                    mock_generate.return_value = {'success': True, 'report_data': {}}
                    mock_distribute.return_value = {
                        'success': True,
                        'total_users_notified': 3,
                        'total_users_failed': 0
                    }
                    
                    execution = await scheduler.execute_schedule(schedule_id)
                    
                    assert execution.status == "success"
                    assert execution.users_notified == 3
        
        # Check execution history
        history = scheduler.get_execution_history(schedule_id)
        assert len(history) == 1
        
        # Get statistics
        stats = scheduler.get_schedule_statistics(schedule_id)
        assert stats['total_executions'] == 1
        assert stats['successful_executions'] == 1
        assert stats['success_rate'] == 1.0
    
    def test_schedule_serialization(self, scheduler):
        """Test serialization and deserialization of schedules."""
        # Create a complex schedule
        original_schedule = scheduler.create_schedule(
            name="Complex Schedule",
            schedule_type=ScheduleType.EVENT_DRIVEN,
            trigger_type=TriggerType.CRITICAL_CHANGES,
            trigger_threshold=5,
            trigger_conditions={'state': 'CA', 'form_type': 'WH-347'},
            target_roles=['product_manager', 'admin'],
            customization_options=ReportCustomizationOptions(
                template_type='executive_summary',
                severity_levels=['critical', 'high'],
                delivery_channels=['email', 'slack']
            ),
            max_retries=5,
            retry_delay_minutes=10,
            force_delivery=True
        )
        
        # Convert to dict
        data = original_schedule.to_dict()
        
        # Convert back to schedule
        restored_schedule = ScheduleConfig.from_dict(data)
        
        # Verify they match
        assert restored_schedule.name == original_schedule.name
        assert restored_schedule.schedule_type == original_schedule.schedule_type
        assert restored_schedule.trigger_type == original_schedule.trigger_type
        assert restored_schedule.trigger_threshold == original_schedule.trigger_threshold
        assert restored_schedule.trigger_conditions == original_schedule.trigger_conditions
        assert restored_schedule.target_roles == original_schedule.target_roles
        assert restored_schedule.max_retries == original_schedule.max_retries
        assert restored_schedule.retry_delay_minutes == original_schedule.retry_delay_minutes
        assert restored_schedule.force_delivery == original_schedule.force_delivery
        
        # Check customization options
        assert restored_schedule.customization_options.template_type == original_schedule.customization_options.template_type
        assert restored_schedule.customization_options.severity_levels == original_schedule.customization_options.severity_levels
        assert restored_schedule.customization_options.delivery_channels == original_schedule.customization_options.delivery_channels


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 