"""
Unit tests for Report Scheduling API

Tests the API endpoints for scheduling automated report generation and delivery.
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.api.report_scheduling import router
from src.reporting.report_scheduler import ScheduleType, TriggerType, ScheduleConfig
from src.reporting.report_customization import ReportCustomizationOptions

# Create test client
client = TestClient(router)


class TestReportSchedulingAPI:
    """Test cases for report scheduling API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sample_schedule_request = {
            "name": "Weekly Executive Summary",
            "description": "Weekly summary for product managers",
            "schedule_type": "cron",
            "is_active": True,
            "cron_expression": "0 9 * * 1",
            "timezone": "America/New_York",
            "target_roles": ["product_manager"],
            "delivery_channels": ["email", "slack"],
            "max_retries": 3,
            "retry_delay_minutes": 5,
            "force_delivery": False,
            "include_attachments": True
        }
        
        self.sample_schedule_response = {
            "schedule_id": "Weekly Executive Summary",
            "name": "Weekly Executive Summary",
            "description": "Weekly summary for product managers",
            "schedule_type": "cron",
            "is_active": True,
            "timezone": "America/New_York",
            "next_run": "2024-01-15T09:00:00",
            "last_run": None,
            "created_at": "2024-01-15T10:00:00",
            "target_roles": ["product_manager"],
            "target_users": None,
            "delivery_channels": ["email", "slack"],
            "status": "created"
        }
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_create_schedule_success(self, mock_get_scheduler, mock_get_user):
        """Test successful schedule creation."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_schedule = ScheduleConfig(
            name="Weekly Executive Summary",
            description="Weekly summary for product managers",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            cron_expression="0 9 * * 1",
            timezone="America/New_York",
            target_roles=["product_manager"],
            delivery_channels=["email", "slack"],
            max_retries=3,
            retry_delay_minutes=5,
            force_delivery=False,
            include_attachments=True,
            created_by=1,
            created_at=datetime.now(),
            next_run=datetime.now() + timedelta(days=1)
        )
        mock_scheduler.create_schedule.return_value = mock_schedule
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.post("/schedules", json=self.sample_schedule_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Weekly Executive Summary"
        assert data["schedule_type"] == "cron"
        assert data["is_active"] is True
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_create_schedule_invalid_type(self, mock_get_scheduler, mock_get_user):
        """Test schedule creation with invalid schedule type."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.create_schedule.side_effect = ValueError("Invalid schedule type")
        mock_get_scheduler.return_value = mock_scheduler
        
        invalid_request = self.sample_schedule_request.copy()
        invalid_request["schedule_type"] = "invalid_type"
        
        response = client.post("/schedules", json=invalid_request)
        
        assert response.status_code == 500
        assert "Failed to create schedule" in response.json()["detail"]
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_get_schedules_success(self, mock_get_scheduler, mock_get_user):
        """Test successful retrieval of schedules."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_schedule = ScheduleConfig(
            name="Weekly Executive Summary",
            description="Weekly summary for product managers",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            cron_expression="0 9 * * 1",
            timezone="America/New_York",
            target_roles=["product_manager"],
            delivery_channels=["email", "slack"],
            max_retries=3,
            retry_delay_minutes=5,
            force_delivery=False,
            include_attachments=True,
            created_by=1,
            created_at=datetime.now(),
            next_run=datetime.now() + timedelta(days=1)
        )
        mock_scheduler.get_all_schedules.return_value = {"Weekly Executive Summary": mock_schedule}
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.get("/schedules")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Weekly Executive Summary"
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_get_schedule_by_id_success(self, mock_get_scheduler, mock_get_user):
        """Test successful retrieval of a specific schedule."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_schedule = ScheduleConfig(
            name="Weekly Executive Summary",
            description="Weekly summary for product managers",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            cron_expression="0 9 * * 1",
            timezone="America/New_York",
            target_roles=["product_manager"],
            delivery_channels=["email", "slack"],
            max_retries=3,
            retry_delay_minutes=5,
            force_delivery=False,
            include_attachments=True,
            created_by=1,
            created_at=datetime.now(),
            next_run=datetime.now() + timedelta(days=1)
        )
        mock_scheduler.get_schedule.return_value = mock_schedule
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.get("/schedules/Weekly Executive Summary")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Weekly Executive Summary"
        assert data["schedule_type"] == "cron"
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_get_schedule_by_id_not_found(self, mock_get_scheduler, mock_get_user):
        """Test retrieval of non-existent schedule."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.get_schedule.return_value = None
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.get("/schedules/nonexistent")
        
        assert response.status_code == 404
        assert "Schedule not found" in response.json()["detail"]
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_update_schedule_success(self, mock_get_scheduler, mock_get_user):
        """Test successful schedule update."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.update_schedule.return_value = True
        
        updated_schedule = ScheduleConfig(
            name="Weekly Executive Summary",
            description="Updated description",
            schedule_type=ScheduleType.CRON,
            is_active=False,
            cron_expression="0 9 * * 1",
            timezone="America/New_York",
            target_roles=["product_manager"],
            delivery_channels=["email"],
            max_retries=3,
            retry_delay_minutes=5,
            force_delivery=False,
            include_attachments=True,
            created_by=1,
            created_at=datetime.now(),
            next_run=datetime.now() + timedelta(days=1)
        )
        mock_scheduler.get_schedule.return_value = updated_schedule
        mock_get_scheduler.return_value = mock_scheduler
        
        update_request = {
            "description": "Updated description",
            "is_active": False,
            "delivery_channels": ["email"]
        }
        
        response = client.put("/schedules/Weekly Executive Summary", json=update_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"
        assert data["is_active"] is False
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_delete_schedule_success(self, mock_get_scheduler, mock_get_user):
        """Test successful schedule deletion."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_scheduler.delete_schedule.return_value = True
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.delete("/schedules/Weekly Executive Summary")
        
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_execute_schedule_success(self, mock_get_scheduler, mock_get_user):
        """Test successful schedule execution."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_execution = MagicMock()
        mock_execution.schedule_id = "Weekly Executive Summary"
        mock_execution.execution_time = datetime.now()
        mock_execution.status = "success"
        mock_execution.report_generated = True
        mock_execution.users_notified = 5
        mock_execution.users_failed = 0
        mock_execution.error_message = None
        mock_execution.execution_duration_seconds = 2.5
        
        mock_scheduler.execute_schedule.return_value = mock_execution
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.post("/schedules/Weekly Executive Summary/execute")
        
        assert response.status_code == 200
        data = response.json()
        assert data["schedule_id"] == "Weekly Executive Summary"
        assert data["status"] == "success"
        assert data["report_generated"] is True
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_create_weekly_schedule_success(self, mock_get_scheduler, mock_get_user):
        """Test successful weekly schedule creation."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_schedule = ScheduleConfig(
            name="Weekly Report",
            description="Weekly report schedule",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            cron_expression="0 9 * * 1",
            timezone="America/New_York",
            target_roles=["product_manager"],
            delivery_channels=["email"],
            max_retries=3,
            retry_delay_minutes=5,
            force_delivery=False,
            include_attachments=True,
            created_by=1,
            created_at=datetime.now(),
            next_run=datetime.now() + timedelta(days=1)
        )
        mock_scheduler.create_weekly_schedule.return_value = mock_schedule
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.post("/schedules/weekly?name=Weekly Report&day_of_week=0&hour=9&minute=0&timezone=America/New_York&target_roles=product_manager&delivery_channels=email")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Weekly Report"
        assert data["schedule_type"] == "cron"
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_create_daily_schedule_success(self, mock_get_scheduler, mock_get_user):
        """Test successful daily schedule creation."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_schedule = ScheduleConfig(
            name="Daily Report",
            description="Daily report schedule",
            schedule_type=ScheduleType.CRON,
            is_active=True,
            cron_expression="0 9 * * *",
            timezone="America/New_York",
            target_roles=["product_manager"],
            delivery_channels=["email"],
            max_retries=3,
            retry_delay_minutes=5,
            force_delivery=False,
            include_attachments=True,
            created_by=1,
            created_at=datetime.now(),
            next_run=datetime.now() + timedelta(days=1)
        )
        mock_scheduler.create_daily_schedule.return_value = mock_schedule
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.post("/schedules/daily?name=Daily Report&hour=9&minute=0&timezone=America/New_York&target_roles=product_manager&delivery_channels=email")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Daily Report"
        assert data["schedule_type"] == "cron"
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_get_execution_history_success(self, mock_get_scheduler, mock_get_user):
        """Test successful execution history retrieval."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_execution = MagicMock()
        mock_execution.schedule_id = "Weekly Executive Summary"
        mock_execution.execution_time = datetime.now()
        mock_execution.status = "success"
        mock_execution.report_generated = True
        mock_execution.users_notified = 5
        mock_execution.users_failed = 0
        mock_execution.error_message = None
        mock_execution.execution_duration_seconds = 2.5
        
        mock_scheduler.get_execution_history.return_value = [mock_execution]
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.get("/schedules/Weekly Executive Summary/history?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["schedule_id"] == "Weekly Executive Summary"
        assert data[0]["status"] == "success"
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_get_schedule_statistics_success(self, mock_get_scheduler, mock_get_user):
        """Test successful schedule statistics retrieval."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_stats = {
            "schedule_id": "Weekly Executive Summary",
            "total_executions": 10,
            "successful_executions": 9,
            "failed_executions": 1,
            "success_rate": 0.9,
            "avg_execution_time_seconds": 2.5,
            "last_execution": datetime.now(),
            "next_execution": datetime.now() + timedelta(days=1)
        }
        mock_scheduler.get_schedule_statistics.return_value = mock_stats
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.get("/schedules/Weekly Executive Summary/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert data["schedule_id"] == "Weekly Executive Summary"
        assert data["total_executions"] == 10
        assert data["success_rate"] == 0.9
    
    @patch('src.api.report_scheduling.get_current_user')
    @patch('src.api.report_scheduling.get_report_scheduler')
    def test_run_due_schedules_success(self, mock_get_scheduler, mock_get_user):
        """Test successful execution of due schedules."""
        # Mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_get_user.return_value = mock_user
        
        # Mock scheduler
        mock_scheduler = MagicMock()
        mock_execution = MagicMock()
        mock_execution.schedule_id = "Weekly Executive Summary"
        mock_execution.status = "success"
        mock_execution.execution_time = datetime.now()
        
        mock_scheduler.run_due_schedules.return_value = [mock_execution]
        mock_get_scheduler.return_value = mock_scheduler
        
        response = client.post("/schedules/run-due")
        
        assert response.status_code == 200
        data = response.json()
        assert "Executed 1 due schedules" in data["message"]
        assert len(data["executions"]) == 1
        assert data["executions"][0]["schedule_id"] == "Weekly Executive Summary"


def test_schedule_request_validation():
    """Test Pydantic model validation for schedule requests."""
    from src.api.report_scheduling import ScheduleRequest
    
    # Valid request
    valid_request = ScheduleRequest(
        name="Test Schedule",
        schedule_type="cron",
        cron_expression="0 9 * * 1",
        timezone="UTC"
    )
    assert valid_request.name == "Test Schedule"
    assert valid_request.schedule_type == "cron"
    
    # Test with missing required fields
    with pytest.raises(ValueError):
        ScheduleRequest(schedule_type="cron")  # Missing name
    
    with pytest.raises(ValueError):
        ScheduleRequest(name="Test")  # Missing schedule_type


def test_schedule_response_validation():
    """Test Pydantic model validation for schedule responses."""
    from src.api.report_scheduling import ScheduleResponse
    
    # Valid response
    valid_response = ScheduleResponse(
        schedule_id="test-schedule",
        name="Test Schedule",
        schedule_type="cron",
        is_active=True,
        timezone="UTC",
        status="active"
    )
    assert valid_response.schedule_id == "test-schedule"
    assert valid_response.name == "Test Schedule"


if __name__ == "__main__":
    pytest.main([__file__]) 