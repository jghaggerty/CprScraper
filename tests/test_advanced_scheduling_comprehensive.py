"""
Comprehensive tests for advanced export scheduling and automated delivery.

Tests scheduling functionality including:
- Advanced export scheduler with flexible timing
- Multiple delivery channels (email, FTP, S3)
- Schedule patterns and cron-like expressions
- API endpoints for scheduling management
- Export templates and automation
- Error handling and recovery
"""

import pytest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy.orm import Session

# Import modules under test
from src.scheduler.advanced_export_scheduler import (
    AdvancedExportScheduler, ScheduledExport, SchedulePattern,
    DeliveryChannel, EmailDelivery, FTPDelivery, S3Delivery,
    advanced_export_scheduler
)
from src.api.data_export import (
    AdvancedScheduleRequest, ScheduleUpdateRequest, DeliveryChannelConfig,
    create_advanced_schedule, list_advanced_schedules, get_advanced_schedule,
    update_advanced_schedule, delete_advanced_schedule
)


class TestSchedulePattern:
    """Test schedule pattern parsing and calculation."""
    
    def test_daily_pattern_parsing(self):
        """Test parsing of daily schedule patterns."""
        pattern = SchedulePattern("daily at 09:00")
        
        assert pattern.parsed_pattern['type'] == 'daily'
        assert pattern.parsed_pattern['time'] == '09:00'
    
    def test_weekly_pattern_parsing(self):
        """Test parsing of weekly schedule patterns."""
        pattern = SchedulePattern("weekly on monday at 10:30")
        
        assert pattern.parsed_pattern['type'] == 'weekly'
        assert pattern.parsed_pattern['day'] == 'monday'
        assert pattern.parsed_pattern['time'] == '10:30'
    
    def test_monthly_pattern_parsing(self):
        """Test parsing of monthly schedule patterns."""
        pattern = SchedulePattern("monthly on 15th at 14:00")
        
        assert pattern.parsed_pattern['type'] == 'monthly'
        assert pattern.parsed_pattern['date'] == 15
        assert pattern.parsed_pattern['time'] == '14:00'
    
    def test_hourly_pattern_parsing(self):
        """Test parsing of hourly schedule patterns."""
        pattern = SchedulePattern("every 6 hours")
        
        assert pattern.parsed_pattern['type'] == 'hourly'
        assert pattern.parsed_pattern['frequency'] == 6
    
    def test_weekdays_pattern_parsing(self):
        """Test parsing of weekdays schedule patterns."""
        pattern = SchedulePattern("weekdays at 08:30")
        
        assert pattern.parsed_pattern['type'] == 'weekdays'
        assert pattern.parsed_pattern['time'] == '08:30'
    
    def test_next_run_time_calculation(self):
        """Test next run time calculation for different patterns."""
        # Test daily pattern
        pattern = SchedulePattern("daily at 09:00")
        from_time = datetime(2024, 1, 15, 12, 0, 0)
        next_run = pattern.next_run_time(from_time)
        
        assert next_run.hour == 9
        assert next_run.minute == 0
        assert next_run.date() == from_time.date() + timedelta(days=1)
    
    def test_time_format_parsing(self):
        """Test different time format parsing."""
        pattern = SchedulePattern("daily at 14:30")
        assert pattern.parsed_pattern['time'] == '14:30'
        
        # Test 12-hour format (if implemented)
        pattern_12h = SchedulePattern("daily at 2:30 PM")
        # This would need implementation in the actual code
    
    def test_invalid_pattern_handling(self):
        """Test handling of invalid patterns."""
        pattern = SchedulePattern("invalid pattern")
        
        # Should not crash and provide sensible defaults
        assert pattern.parsed_pattern['type'] == 'unknown'


class TestDeliveryChannels:
    """Test delivery channel functionality."""
    
    def test_email_delivery_config_validation(self):
        """Test email delivery channel configuration validation."""
        # Valid configuration
        valid_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'password123',
            'recipients': ['admin@company.com']
        }
        
        email_channel = EmailDelivery(valid_config)
        assert email_channel.validate_config() == True
        
        # Invalid configuration (missing required fields)
        invalid_config = {
            'smtp_server': 'smtp.gmail.com'
        }
        
        email_channel_invalid = EmailDelivery(invalid_config)
        assert email_channel_invalid.validate_config() == False
    
    def test_ftp_delivery_config_validation(self):
        """Test FTP delivery channel configuration validation."""
        valid_config = {
            'server': 'ftp.example.com',
            'username': 'user',
            'password': 'pass',
            'remote_path': '/exports/'
        }
        
        ftp_channel = FTPDelivery(valid_config)
        assert ftp_channel.validate_config() == True
        
        # Invalid configuration
        invalid_config = {'server': 'ftp.example.com'}
        ftp_channel_invalid = FTPDelivery(invalid_config)
        assert ftp_channel_invalid.validate_config() == False
    
    def test_s3_delivery_config_validation(self):
        """Test S3 delivery channel configuration validation."""
        valid_config = {
            'aws_access_key': 'AKIAEXAMPLE',
            'aws_secret_key': 'secret123',
            'bucket_name': 'my-exports-bucket'
        }
        
        s3_channel = S3Delivery(valid_config)
        # Validation depends on boto3 availability
        result = s3_channel.validate_config()
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_email_delivery_mock(self):
        """Test email delivery with mocked SMTP."""
        config = {
            'smtp_server': 'smtp.example.com',
            'smtp_port': 587,
            'username': 'test@example.com',
            'password': 'password',
            'recipients': ['admin@company.com'],
            'use_tls': True
        }
        
        email_channel = EmailDelivery(config)
        
        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = Mock()
            mock_smtp.return_value = mock_server
            
            # Create a temporary test file
            test_file = tempfile.NamedTemporaryFile(delete=False)
            test_file.write(b"Test export content")
            test_file.close()
            
            try:
                result = await email_channel.deliver(test_file.name, {'export_name': 'Test Export'})
                assert result == True
                mock_server.sendmail.assert_called_once()
            finally:
                os.unlink(test_file.name)
    
    @pytest.mark.asyncio
    async def test_ftp_delivery_mock(self):
        """Test FTP delivery with mocked FTP client."""
        config = {
            'server': 'ftp.example.com',
            'username': 'user',
            'password': 'pass',
            'remote_path': '/exports/'
        }
        
        ftp_channel = FTPDelivery(config)
        
        with patch('ftplib.FTP') as mock_ftp_class:
            mock_ftp = Mock()
            mock_ftp_class.return_value = mock_ftp
            
            # Create a temporary test file
            test_file = tempfile.NamedTemporaryFile(delete=False)
            test_file.write(b"Test export content")
            test_file.close()
            
            try:
                result = await ftp_channel.deliver(test_file.name, {'export_name': 'Test Export'})
                assert result == True
                mock_ftp.login.assert_called_once_with('user', 'pass')
                mock_ftp.storbinary.assert_called_once()
            finally:
                os.unlink(test_file.name)


class TestScheduledExport:
    """Test scheduled export functionality."""
    
    def test_scheduled_export_creation(self):
        """Test creation and initialization of scheduled exports."""
        config = {
            'name': 'Daily Report',
            'description': 'Daily compliance report',
            'schedule': 'daily at 09:00',
            'export_config': {
                'data_source': 'form_changes',
                'format': 'csv'
            },
            'delivery_channels': [{
                'type': 'email',
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'password',
                'recipients': ['admin@company.com']
            }]
        }
        
        scheduled_export = ScheduledExport('test_export_123', config)
        
        assert scheduled_export.export_id == 'test_export_123'
        assert scheduled_export.config['name'] == 'Daily Report'
        assert scheduled_export.status == 'active'
        assert scheduled_export.run_count == 0
        assert scheduled_export.failure_count == 0
        assert len(scheduled_export.delivery_channels) == 1
        assert scheduled_export.next_run is not None
    
    def test_schedule_due_detection(self):
        """Test detection of due schedules."""
        config = {
            'name': 'Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': []
        }
        
        scheduled_export = ScheduledExport('test_export', config)
        
        # Set next run to past time
        scheduled_export.next_run = datetime.now() - timedelta(minutes=5)
        assert scheduled_export.is_due() == True
        
        # Set next run to future time
        scheduled_export.next_run = datetime.now() + timedelta(hours=1)
        assert scheduled_export.is_due() == False
        
        # Disabled schedule should not be due
        scheduled_export.status = 'disabled'
        scheduled_export.next_run = datetime.now() - timedelta(minutes=5)
        assert scheduled_export.is_due() == False
    
    def test_success_and_failure_recording(self):
        """Test recording of successful and failed executions."""
        config = {
            'name': 'Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': []
        }
        
        scheduled_export = ScheduledExport('test_export', config)
        
        # Record success
        initial_next_run = scheduled_export.next_run
        scheduled_export.record_success()
        
        assert scheduled_export.run_count == 1
        assert scheduled_export.failure_count == 0
        assert scheduled_export.last_run is not None
        assert scheduled_export.next_run != initial_next_run
        assert scheduled_export.last_error is None
        
        # Record failure
        scheduled_export.record_failure("Test error")
        
        assert scheduled_export.run_count == 1
        assert scheduled_export.failure_count == 1
        assert scheduled_export.last_error == "Test error"
        assert scheduled_export.status == 'active'  # Should still be active
        
        # Record multiple failures to trigger disable
        for i in range(4):
            scheduled_export.record_failure(f"Error {i+2}")
        
        assert scheduled_export.failure_count == 5
        assert scheduled_export.status == 'disabled'
    
    def test_schedule_serialization(self):
        """Test conversion to dictionary format."""
        config = {
            'name': 'Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': [{
                'type': 'email',
                'recipients': ['test@example.com']
            }]
        }
        
        scheduled_export = ScheduledExport('test_export', config)
        scheduled_export.record_success()
        
        export_dict = scheduled_export.to_dict()
        
        assert export_dict['export_id'] == 'test_export'
        assert export_dict['config']['name'] == 'Test Export'
        assert export_dict['run_count'] == 1
        assert export_dict['status'] == 'active'
        assert export_dict['delivery_channels'] == 1


class TestAdvancedExportScheduler:
    """Test the main scheduler functionality."""
    
    @pytest.fixture
    def scheduler(self):
        """Create scheduler instance for testing."""
        return AdvancedExportScheduler()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    def test_scheduler_initialization(self, scheduler):
        """Test scheduler initialization."""
        assert scheduler.export_manager is not None
        assert scheduler.bulk_export_manager is not None
        assert isinstance(scheduler.scheduled_exports, dict)
        assert len(scheduler.scheduled_exports) == 0
        assert scheduler.running == False
        assert scheduler.export_templates is not None
    
    def test_export_templates_loading(self, scheduler):
        """Test loading of export templates."""
        templates = scheduler.export_templates
        
        # Should have predefined templates
        assert 'daily_summary' in templates
        assert 'weekly_detailed' in templates
        assert 'monthly_archive' in templates
        
        # Templates should have required structure
        daily_template = templates['daily_summary']
        assert 'name' in daily_template
        assert 'description' in daily_template
        assert 'export_config' in daily_template
    
    def test_schedule_export_creation(self, scheduler):
        """Test creation of new scheduled exports."""
        export_config = {
            'name': 'Test Schedule',
            'schedule': 'daily at 10:00',
            'export_config': {
                'data_source': 'form_changes',
                'format': 'csv'
            },
            'delivery_channels': [{
                'type': 'email',
                'smtp_server': 'smtp.example.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'password',
                'recipients': ['admin@company.com']
            }]
        }
        
        export_id = scheduler.schedule_export(export_config)
        
        assert export_id is not None
        assert export_id in scheduler.scheduled_exports
        
        scheduled_export = scheduler.scheduled_exports[export_id]
        assert scheduled_export.config['name'] == 'Test Schedule'
        assert scheduled_export.status == 'active'
    
    def test_get_scheduled_exports(self, scheduler):
        """Test retrieval of scheduled exports."""
        # Add some test exports
        config = {
            'name': 'Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': []
        }
        
        export_id1 = scheduler.schedule_export(config)
        export_id2 = scheduler.schedule_export({**config, 'name': 'Test Export 2'})
        
        exports = scheduler.get_scheduled_exports()
        
        assert len(exports) == 2
        assert export_id1 in exports
        assert export_id2 in exports
        
        # Check structure
        export_data = exports[export_id1]
        assert 'export_id' in export_data
        assert 'config' in export_data
        assert 'status' in export_data
    
    def test_cancel_scheduled_export(self, scheduler):
        """Test cancellation of scheduled exports."""
        config = {
            'name': 'Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': []
        }
        
        export_id = scheduler.schedule_export(config)
        assert export_id in scheduler.scheduled_exports
        
        # Cancel the export
        success = scheduler.cancel_scheduled_export(export_id)
        assert success == True
        assert export_id not in scheduler.scheduled_exports
        
        # Try to cancel non-existent export
        success = scheduler.cancel_scheduled_export('non_existent')
        assert success == False
    
    def test_update_scheduled_export(self, scheduler):
        """Test updating scheduled export configuration."""
        config = {
            'name': 'Original Name',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': []
        }
        
        export_id = scheduler.schedule_export(config)
        
        # Update the configuration
        updated_config = {
            'name': 'Updated Name',
            'schedule': 'weekly on monday at 10:00',
            'export_config': {'format': 'excel'},
            'delivery_channels': []
        }
        
        success = scheduler.update_scheduled_export(export_id, updated_config)
        assert success == True
        
        # Verify update
        exports = scheduler.get_scheduled_exports()
        updated_export = exports[export_id]
        assert updated_export['config']['name'] == 'Updated Name'
        assert updated_export['config']['schedule'] == 'weekly on monday at 10:00'
    
    @patch('src.scheduler.advanced_export_scheduler.get_db')
    def test_fetch_export_data(self, mock_get_db, scheduler):
        """Test data fetching for different export configurations."""
        # Mock database session and query results
        mock_session = Mock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock form changes query
        mock_change = Mock()
        mock_change.id = 1
        mock_change.form = Mock()
        mock_change.form.name = 'Test Form'
        mock_change.form.agency = Mock()
        mock_change.form.agency.name = 'Test Agency'
        mock_change.change_type = 'update'
        mock_change.severity = 'medium'
        mock_change.status = 'detected'
        mock_change.detected_at = datetime.now()
        mock_change.description = 'Test change'
        mock_change.url = 'http://example.com'
        
        mock_session.query.return_value.filter.return_value.limit.return_value.all.return_value = [mock_change]
        
        # Test form changes data fetch
        export_config = {
            'data_source': 'form_changes',
            'filters': {'date_range': '24h'}
        }
        
        data = scheduler._fetch_export_data(export_config, mock_session)
        
        assert len(data) == 1
        assert data[0]['id'] == 1
        assert data[0]['form_name'] == 'Test Form'
        assert data[0]['agency_name'] == 'Test Agency'
    
    def test_scheduler_lifecycle(self, scheduler):
        """Test starting and stopping the scheduler."""
        # Initially not running
        assert scheduler.running == False
        
        # Start scheduler
        scheduler.start()
        assert scheduler.running == True
        
        # Starting again should not cause issues
        scheduler.start()
        assert scheduler.running == True
        
        # Stop scheduler
        scheduler.stop()
        assert scheduler.running == False


class TestSchedulingAPI:
    """Test scheduling API endpoints."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def schedule_request(self):
        """Sample schedule request."""
        from src.api.data_export import DataExportRequest, ExportCustomization
        
        export_request = DataExportRequest(
            data_source="form_changes",
            customization=ExportCustomization(
                format="csv",
                include_headers=True
            )
        )
        
        delivery_channel = DeliveryChannelConfig(
            type="email",
            name="email_channel",
            smtp_server="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="password",
            recipients=["admin@company.com"]
        )
        
        return AdvancedScheduleRequest(
            name="Test Schedule",
            description="Test scheduled export",
            schedule="daily at 09:00",
            export_config=export_request,
            delivery_channels=[delivery_channel],
            enabled=True
        )
    
    @pytest.mark.asyncio
    async def test_create_advanced_schedule_endpoint(self, schedule_request, mock_db):
        """Test creation of advanced schedule via API."""
        with patch('src.api.data_export.advanced_export_scheduler') as mock_scheduler:
            # Mock scheduler response
            mock_scheduler.schedule_export.return_value = "test_export_123"
            mock_scheduler.get_scheduled_exports.return_value = {
                "test_export_123": {
                    'export_id': 'test_export_123',
                    'config': {
                        'name': 'Test Schedule',
                        'schedule': 'daily at 09:00'
                    },
                    'next_run': datetime.now() + timedelta(days=1),
                    'last_run': None,
                    'run_count': 0,
                    'failure_count': 0,
                    'status': 'active',
                    'created_at': datetime.now(),
                    'delivery_channels': 1
                }
            }
            
            response = await create_advanced_schedule(schedule_request, mock_db)
            
            assert response.export_id == "test_export_123"
            assert response.name == "Test Schedule"
            assert response.status == "active"
            assert response.delivery_channels == 1
    
    @pytest.mark.asyncio
    async def test_list_advanced_schedules_endpoint(self):
        """Test listing of advanced schedules via API."""
        with patch('src.api.data_export.advanced_export_scheduler') as mock_scheduler:
            mock_scheduler.get_scheduled_exports.return_value = {
                "export_1": {
                    'export_id': 'export_1',
                    'config': {'name': 'Export 1', 'schedule': 'daily at 09:00'},
                    'next_run': datetime.now(),
                    'last_run': None,
                    'run_count': 0,
                    'failure_count': 0,
                    'status': 'active',
                    'created_at': datetime.now(),
                    'delivery_channels': 1
                }
            }
            
            response = await list_advanced_schedules()
            
            assert "scheduled_exports" in response
            assert len(response["scheduled_exports"]) == 1
            assert response["scheduled_exports"][0].export_id == "export_1"
    
    @pytest.mark.asyncio
    async def test_get_advanced_schedule_endpoint(self):
        """Test retrieval of specific schedule via API."""
        with patch('src.api.data_export.advanced_export_scheduler') as mock_scheduler:
            mock_scheduler.get_scheduled_exports.return_value = {
                "test_export": {
                    'export_id': 'test_export',
                    'config': {'name': 'Test Export', 'schedule': 'daily at 09:00'},
                    'next_run': datetime.now(),
                    'last_run': None,
                    'run_count': 5,
                    'failure_count': 1,
                    'status': 'active',
                    'created_at': datetime.now(),
                    'delivery_channels': 2
                }
            }
            
            response = await get_advanced_schedule("test_export")
            
            assert response.export_id == "test_export"
            assert response.name == "Test Export"
            assert response.run_count == 5
            assert response.failure_count == 1
    
    @pytest.mark.asyncio
    async def test_update_advanced_schedule_endpoint(self, mock_db):
        """Test updating of schedule via API."""
        update_request = ScheduleUpdateRequest(
            name="Updated Name",
            schedule="weekly on monday at 10:00"
        )
        
        with patch('src.api.data_export.advanced_export_scheduler') as mock_scheduler:
            # Mock current schedule
            mock_scheduler.get_scheduled_exports.return_value = {
                "test_export": {
                    'export_id': 'test_export',
                    'config': {
                        'name': 'Original Name',
                        'schedule': 'daily at 09:00',
                        'export_config': {},
                        'delivery_channels': []
                    },
                    'next_run': datetime.now(),
                    'last_run': None,
                    'run_count': 0,
                    'failure_count': 0,
                    'status': 'active',
                    'created_at': datetime.now(),
                    'delivery_channels': 0
                }
            }
            
            mock_scheduler.update_scheduled_export.return_value = True
            
            response = await update_advanced_schedule("test_export", update_request, mock_db)
            
            assert response.export_id == "test_export"
            mock_scheduler.update_scheduled_export.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_advanced_schedule_endpoint(self):
        """Test deletion of schedule via API."""
        with patch('src.api.data_export.advanced_export_scheduler') as mock_scheduler:
            mock_scheduler.cancel_scheduled_export.return_value = True
            
            response = await delete_advanced_schedule("test_export")
            
            assert "deleted successfully" in response["message"]
            mock_scheduler.cancel_scheduled_export.assert_called_once_with("test_export")


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_schedule_patterns(self):
        """Test handling of invalid schedule patterns."""
        invalid_patterns = [
            "",
            "invalid pattern",
            "daily at 25:00",  # Invalid time
            "weekly on invalid_day at 10:00"
        ]
        
        for pattern_str in invalid_patterns:
            pattern = SchedulePattern(pattern_str)
            # Should not crash and provide reasonable defaults
            assert pattern.parsed_pattern is not None
            
            # Next run time should be calculable
            next_run = pattern.next_run_time()
            assert isinstance(next_run, datetime)
    
    def test_delivery_channel_errors(self):
        """Test handling of delivery channel errors."""
        # Invalid email configuration
        invalid_email_config = {
            'type': 'email',
            'smtp_server': 'invalid_server',
            'recipients': []
        }
        
        email_channel = EmailDelivery(invalid_email_config)
        assert email_channel.validate_config() == False
    
    def test_scheduler_resource_cleanup(self):
        """Test proper resource cleanup in scheduler."""
        scheduler = AdvancedExportScheduler()
        
        # Add some scheduled exports
        config = {
            'name': 'Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {'format': 'csv'},
            'delivery_channels': []
        }
        
        export_id = scheduler.schedule_export(config)
        assert len(scheduler.scheduled_exports) == 1
        
        # Start and stop scheduler
        scheduler.start()
        scheduler.stop()
        
        # Verify cleanup
        assert scheduler.running == False
    
    def test_concurrent_scheduler_operations(self):
        """Test concurrent operations on scheduler."""
        scheduler = AdvancedExportScheduler()
        
        # Multiple simultaneous schedule creations
        configs = []
        for i in range(5):
            configs.append({
                'name': f'Export {i}',
                'schedule': 'daily at 09:00',
                'export_config': {'format': 'csv'},
                'delivery_channels': []
            })
        
        export_ids = []
        for config in configs:
            export_id = scheduler.schedule_export(config)
            export_ids.append(export_id)
        
        assert len(scheduler.scheduled_exports) == 5
        assert all(eid in scheduler.scheduled_exports for eid in export_ids)


class TestIntegration:
    """Integration tests for the complete scheduling system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_scheduling_workflow(self):
        """Test complete workflow from schedule creation to execution."""
        scheduler = AdvancedExportScheduler()
        
        # Create schedule
        config = {
            'name': 'Integration Test Export',
            'schedule': 'daily at 09:00',
            'export_config': {
                'data_source': 'form_changes',
                'format': 'csv',
                'filters': {'date_range': '24h'}
            },
            'delivery_channels': []  # No delivery for test
        }
        
        export_id = scheduler.schedule_export(config)
        scheduled_export = scheduler.scheduled_exports[export_id]
        
        # Verify schedule is created correctly
        assert scheduled_export.status == 'active'
        assert scheduled_export.run_count == 0
        
        # Mock due time
        scheduled_export.next_run = datetime.now() - timedelta(minutes=1)
        
        # Test due detection
        assert scheduled_export.is_due() == True
        
        # Simulate successful execution
        scheduled_export.record_success()
        
        assert scheduled_export.run_count == 1
        assert scheduled_export.failure_count == 0
        assert scheduled_export.next_run > datetime.now()


if __name__ == '__main__':
    """Run advanced scheduling tests."""
    pytest.main([__file__, '-v', '--tb=short'])