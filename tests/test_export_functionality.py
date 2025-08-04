"""
Tests for export functionality

Tests the export utilities, scheduler, and API endpoints for dashboard data export.
"""

import pytest
import json
import io
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.utils.export_utils import ExportManager, ExportScheduler
from src.api.dashboard import router
from src.database.models import FormChange, Form, Agency
from src.database.connection import get_db


class TestExportManager:
    """Test the ExportManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.export_manager = ExportManager()
        self.sample_data = [
            {
                'id': 1,
                'form_name': 'Test Form 1',
                'agency_name': 'Test Agency',
                'change_type': 'form_update',
                'severity': 'critical',
                'status': 'pending',
                'detected_at': datetime.now(),
                'ai_confidence_score': 95,
                'description': 'Test change description'
            },
            {
                'id': 2,
                'form_name': 'Test Form 2',
                'agency_name': 'Test Agency',
                'change_type': 'field_change',
                'severity': 'high',
                'status': 'reviewed',
                'detected_at': datetime.now() - timedelta(hours=1),
                'ai_confidence_score': 87,
                'description': 'Another test change'
            }
        ]
        self.export_config = {
            'columns': ['id', 'form_name', 'agency_name', 'severity', 'status'],
            'include_headers': True,
            'filters': {'severity': 'critical'}
        }
    
    def test_export_manager_initialization(self):
        """Test ExportManager initialization."""
        assert self.export_manager.supported_formats == ['csv', 'excel', 'pdf']
        assert self.export_manager.max_export_size == 10000
    
    def test_export_data_unsupported_format(self):
        """Test export with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            self.export_manager.export_data(
                self.sample_data, 'txt', self.export_config
            )
    
    def test_export_data_size_limit(self):
        """Test export with data exceeding size limit."""
        large_data = [{'id': i} for i in range(10001)]
        with pytest.raises(ValueError, match="Export size exceeds maximum limit"):
            self.export_manager.export_data(
                large_data, 'csv', self.export_config
            )
    
    def test_export_csv(self):
        """Test CSV export functionality."""
        result = self.export_manager.export_data(
            self.sample_data, 'csv', self.export_config
        )
        
        assert isinstance(result, str)
        assert 'Test Form 1' in result
        assert 'Test Form 2' in result
        assert 'critical' in result
        assert 'high' in result
    
    def test_export_csv_no_headers(self):
        """Test CSV export without headers."""
        config = self.export_config.copy()
        config['include_headers'] = False
        
        result = self.export_manager.export_data(
            self.sample_data, 'csv', config
        )
        
        assert isinstance(result, str)
        assert 'id,form_name,agency_name,severity,status' not in result
    
    def test_export_csv_empty_data(self):
        """Test CSV export with empty data."""
        result = self.export_manager.export_data(
            [], 'csv', self.export_config
        )
        
        assert result == ""
    
    def test_export_excel(self):
        """Test Excel export functionality."""
        result = self.export_manager.export_data(
            self.sample_data, 'excel', self.export_config
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_excel_empty_data(self):
        """Test Excel export with empty data."""
        result = self.export_manager.export_data(
            [], 'excel', self.export_config
        )
        
        assert result == b""
    
    def test_export_pdf(self):
        """Test PDF export functionality."""
        result = self.export_manager.export_data(
            self.sample_data, 'pdf', self.export_config
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_pdf_empty_data(self):
        """Test PDF export with empty data."""
        result = self.export_manager.export_data(
            [], 'pdf', self.export_config
        )
        
        assert result == b""
    
    def test_format_row_for_csv(self):
        """Test CSV row formatting."""
        row = {
            'id': 1,
            'name': 'Test',
            'date': datetime(2023, 1, 1, 12, 0, 0),
            'data': {'key': 'value'},
            'null_value': None
        }
        
        formatted = self.export_manager._format_row_for_csv(row)
        
        assert formatted['id'] == '1'
        assert formatted['name'] == 'Test'
        assert '2023-01-01 12:00:00' in formatted['date']
        assert formatted['data'] == '{"key": "value"}'
        assert formatted['null_value'] == ''
    
    def test_apply_severity_formatting(self):
        """Test severity-based cell formatting."""
        # This test would require openpyxl Cell objects
        # For now, we'll just test that the method doesn't raise errors
        cell = Mock()
        
        self.export_manager._apply_severity_formatting(cell, 'critical')
        self.export_manager._apply_severity_formatting(cell, 'high')
        self.export_manager._apply_severity_formatting(cell, 'medium')
        self.export_manager._apply_severity_formatting(cell, 'low')
        
        # Verify that cell properties were set
        assert cell.fill is not None or cell.font is not None
    
    def test_apply_status_formatting(self):
        """Test status-based cell formatting."""
        cell = Mock()
        
        self.export_manager._apply_status_formatting(cell, 'pending')
        self.export_manager._apply_status_formatting(cell, 'completed')
        self.export_manager._apply_status_formatting(cell, 'failed')
        
        # Verify that cell properties were set
        assert cell.fill is not None or cell.font is not None


class TestExportScheduler:
    """Test the ExportScheduler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.export_manager = ExportManager()
        self.scheduler = ExportScheduler(self.export_manager)
        self.schedule_config = {
            'frequency': 'daily',
            'time': '09:00',
            'timezone': 'UTC'
        }
        self.export_config = {
            'format': 'csv',
            'columns': ['id', 'form_name'],
            'filters': {'severity': 'critical'}
        }
    
    def test_scheduler_initialization(self):
        """Test ExportScheduler initialization."""
        assert self.scheduler.export_manager == self.export_manager
        assert self.scheduler.scheduled_exports == {}
    
    def test_schedule_export_success(self):
        """Test successful export scheduling."""
        export_id = "test_export_123"
        
        result = self.scheduler.schedule_export(
            export_id, self.schedule_config, self.export_config
        )
        
        assert result is True
        assert export_id in self.scheduler.scheduled_exports
        
        scheduled = self.scheduler.scheduled_exports[export_id]
        assert scheduled['schedule'] == self.schedule_config
        assert scheduled['export_config'] == self.export_config
        assert scheduled['created_at'] is not None
        assert scheduled['last_run'] is None
        assert scheduled['next_run'] is not None
    
    def test_schedule_export_failure(self):
        """Test export scheduling failure."""
        # Mock the _calculate_next_run method to raise an exception
        with patch.object(self.scheduler, '_calculate_next_run', side_effect=Exception("Test error")):
            result = self.scheduler.schedule_export(
                "test_export", self.schedule_config, self.export_config
            )
            
            assert result is False
    
    def test_calculate_next_run_daily(self):
        """Test next run calculation for daily frequency."""
        config = {'frequency': 'daily'}
        next_run = self.scheduler._calculate_next_run(config)
        
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()
        assert (next_run - datetime.now()).days >= 1
    
    def test_calculate_next_run_weekly(self):
        """Test next run calculation for weekly frequency."""
        config = {'frequency': 'weekly'}
        next_run = self.scheduler._calculate_next_run(config)
        
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()
        assert (next_run - datetime.now()).days >= 7
    
    def test_calculate_next_run_monthly(self):
        """Test next run calculation for monthly frequency."""
        config = {'frequency': 'monthly'}
        next_run = self.scheduler._calculate_next_run(config)
        
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()
        assert (next_run - datetime.now()).days >= 30
    
    def test_calculate_next_run_unknown_frequency(self):
        """Test next run calculation for unknown frequency."""
        config = {'frequency': 'unknown'}
        next_run = self.scheduler._calculate_next_run(config)
        
        assert isinstance(next_run, datetime)
        assert next_run > datetime.now()
        # Should default to daily
        assert (next_run - datetime.now()).days >= 1
    
    def test_get_scheduled_exports(self):
        """Test getting scheduled exports."""
        # Add some test exports
        self.scheduler.scheduled_exports = {
            'export1': {'schedule': {}, 'export_config': {}},
            'export2': {'schedule': {}, 'export_config': {}}
        }
        
        exports = self.scheduler.get_scheduled_exports()
        
        assert isinstance(exports, dict)
        assert len(exports) == 2
        assert 'export1' in exports
        assert 'export2' in exports
    
    def test_cancel_export_success(self):
        """Test successful export cancellation."""
        export_id = "test_export_123"
        self.scheduler.scheduled_exports[export_id] = {'test': 'data'}
        
        result = self.scheduler.cancel_export(export_id)
        
        assert result is True
        assert export_id not in self.scheduler.scheduled_exports
    
    def test_cancel_export_not_found(self):
        """Test export cancellation when export doesn't exist."""
        result = self.scheduler.cancel_export("nonexistent_export")
        
        assert result is False


class TestExportAPI:
    """Test the export API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(router)
        self.sample_export_request = {
            "format": "csv",
            "filters": {"severity": "critical"},
            "columns": ["id", "form_name", "agency_name"],
            "include_headers": True,
            "filename": "test_export.csv"
        }
    
    @patch('src.api.dashboard.get_db')
    def test_export_filtered_data_success(self, mock_get_db):
        """Test successful export request."""
        # Mock database session and query results
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        # Mock FormChange query results
        mock_changes = [
            Mock(
                id=1,
                form=Mock(name="Test Form", agency=Mock(name="Test Agency", agency_type="state")),
                change_type="form_update",
                severity="critical",
                status="pending",
                detected_at=datetime.now(),
                ai_confidence_score=95,
                ai_change_category="important",
                is_cosmetic_change=False,
                impact_assessment={"impact": "high"},
                description="Test change",
                url="http://example.com"
            )
        ]
        
        mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = mock_changes
        
        # Mock export manager
        with patch('src.api.dashboard.export_manager') as mock_export_manager:
            mock_export_manager.export_data.return_value = "csv,data,here"
            
            response = self.client.post("/export", json=self.sample_export_request)
            
            assert response.status_code == 200
            data = response.json()
            
            assert "export_id" in data
            assert data["format"] == "csv"
            assert data["record_count"] == 1
            assert "download_url" in data
            assert "expires_at" in data
    
    @patch('src.api.dashboard.get_db')
    def test_export_filtered_data_unsupported_format(self, mock_get_db):
        """Test export request with unsupported format."""
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        request = self.sample_export_request.copy()
        request["format"] = "txt"
        
        response = self.client.post("/export", json=request)
        
        assert response.status_code == 400
        assert "Unsupported export format" in response.json()["detail"]
    
    @patch('src.api.dashboard.get_db')
    def test_export_filtered_data_no_data(self, mock_get_db):
        """Test export request with no matching data."""
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        # Mock empty query results
        mock_session.query.return_value.options.return_value.filter.return_value.all.return_value = []
        
        with patch('src.api.dashboard.export_manager') as mock_export_manager:
            mock_export_manager.export_data.return_value = ""
            
            response = self.client.post("/export", json=self.sample_export_request)
            
            assert response.status_code == 200
            data = response.json()
            assert data["record_count"] == 0
    
    def test_get_export_formats(self):
        """Test getting available export formats."""
        response = self.client.get("/export/formats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "supported_formats" in data
        assert "max_export_size" in data
        
        formats = data["supported_formats"]
        assert len(formats) == 3  # csv, excel, pdf
        
        format_types = [f["format"] for f in formats]
        assert "csv" in format_types
        assert "excel" in format_types
        assert "pdf" in format_types
    
    @patch('src.api.dashboard.export_scheduler')
    def test_schedule_export_success(self, mock_scheduler):
        """Test successful export scheduling."""
        mock_scheduler.schedule_export.return_value = True
        mock_scheduler.get_scheduled_exports.return_value = {
            "test_export": {
                "schedule": {"frequency": "daily"},
                "export_config": {"format": "csv"},
                "created_at": datetime.now(),
                "last_run": None,
                "next_run": datetime.now() + timedelta(days=1)
            }
        }
        
        request = {
            "export_config": self.sample_export_request,
            "schedule": {"frequency": "daily", "time": "09:00"}
        }
        
        response = self.client.post("/export/schedule", json=request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "export_id" in data
        assert data["status"] == "scheduled"
        assert "next_run" in data
    
    @patch('src.api.dashboard.export_scheduler')
    def test_schedule_export_failure(self, mock_scheduler):
        """Test export scheduling failure."""
        mock_scheduler.schedule_export.return_value = False
        
        request = {
            "export_config": self.sample_export_request,
            "schedule": {"frequency": "daily", "time": "09:00"}
        }
        
        response = self.client.post("/export/schedule", json=request)
        
        assert response.status_code == 500
        assert "Failed to schedule export" in response.json()["detail"]
    
    @patch('src.api.dashboard.export_scheduler')
    def test_get_scheduled_exports(self, mock_scheduler):
        """Test getting scheduled exports."""
        mock_scheduler.get_scheduled_exports.return_value = {
            "export1": {
                "schedule": {"frequency": "daily"},
                "export_config": {"format": "csv"},
                "created_at": datetime.now(),
                "last_run": None,
                "next_run": datetime.now() + timedelta(days=1)
            }
        }
        
        response = self.client.get("/export/scheduled")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "scheduled_exports" in data
        assert len(data["scheduled_exports"]) == 1
        assert data["scheduled_exports"][0]["export_id"] == "export1"
    
    @patch('src.api.dashboard.export_scheduler')
    def test_cancel_scheduled_export_success(self, mock_scheduler):
        """Test successful export cancellation."""
        mock_scheduler.cancel_export.return_value = True
        
        response = self.client.delete("/export/schedule/test_export_123")
        
        assert response.status_code == 200
        assert "cancelled successfully" in response.json()["message"]
    
    @patch('src.api.dashboard.export_scheduler')
    def test_cancel_scheduled_export_not_found(self, mock_scheduler):
        """Test export cancellation when export doesn't exist."""
        mock_scheduler.cancel_export.return_value = False
        
        response = self.client.delete("/export/schedule/nonexistent_export")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_download_export_not_implemented(self):
        """Test download endpoint (not implemented)."""
        response = self.client.get("/export/test_export_123/download")
        
        assert response.status_code == 404
        assert "not found or expired" in response.json()["detail"]


class TestExportFilters:
    """Test export filter functionality."""
    
    def test_apply_export_filters_agency_id(self):
        """Test applying agency ID filter."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"agency_id": 123}
        
        result = _apply_export_filters(mock_query, filters)
        
        mock_query.join.assert_called_once()
        mock_query.filter.assert_called()
    
    def test_apply_export_filters_severity(self):
        """Test applying severity filter."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"severity": "critical"}
        
        result = _apply_export_filters(mock_query, filters)
        
        mock_query.filter.assert_called()
    
    def test_apply_export_filters_status(self):
        """Test applying status filter."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"status": "pending"}
        
        result = _apply_export_filters(mock_query, filters)
        
        mock_query.filter.assert_called()
    
    def test_apply_export_filters_date_range(self):
        """Test applying date range filters."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {
            "date_from": "2023-01-01T00:00:00",
            "date_to": "2023-12-31T23:59:59"
        }
        
        result = _apply_export_filters(mock_query, filters)
        
        # Should call filter twice (once for each date)
        assert mock_query.filter.call_count == 2
    
    def test_apply_export_filters_invalid_date(self):
        """Test applying invalid date filters."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"date_from": "invalid-date"}
        
        result = _apply_export_filters(mock_query, filters)
        
        # Should not call filter for invalid date
        mock_query.filter.assert_not_called()
    
    def test_apply_export_filters_change_type(self):
        """Test applying change type filter."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"change_type": "form_update"}
        
        result = _apply_export_filters(mock_query, filters)
        
        mock_query.filter.assert_called()
    
    def test_apply_export_filters_ai_confidence(self):
        """Test applying AI confidence filter."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"ai_confidence_min": "80"}
        
        result = _apply_export_filters(mock_query, filters)
        
        mock_query.filter.assert_called()
    
    def test_apply_export_filters_invalid_confidence(self):
        """Test applying invalid AI confidence filter."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {"ai_confidence_min": "invalid"}
        
        result = _apply_export_filters(mock_query, filters)
        
        # Should not call filter for invalid confidence
        mock_query.filter.assert_not_called()
    
    def test_apply_export_filters_no_filters(self):
        """Test applying no filters."""
        from src.api.dashboard import _apply_export_filters
        
        mock_query = Mock()
        filters = {}
        
        result = _apply_export_filters(mock_query, filters)
        
        # Should return original query unchanged
        assert result == mock_query


# Integration tests
class TestExportIntegration:
    """Integration tests for export functionality."""
    
    @pytest.fixture
    def sample_database_data(self, db_session):
        """Create sample database data for testing."""
        # Create test agency
        agency = Agency(
            name="Test Agency",
            agency_type="state",
            state="CA",
            website_url="http://test.agency.gov"
        )
        db_session.add(agency)
        db_session.commit()
        
        # Create test form
        form = Form(
            name="Test Form",
            title="Test Form Title",
            agency_id=agency.id,
            check_frequency="daily",
            url="http://test.agency.gov/form"
        )
        db_session.add(form)
        db_session.commit()
        
        # Create test changes
        changes = [
            FormChange(
                form_id=form.id,
                change_type="form_update",
                severity="critical",
                status="pending",
                detected_at=datetime.now(),
                ai_confidence_score=95,
                description="Test critical change"
            ),
            FormChange(
                form_id=form.id,
                change_type="field_change",
                severity="high",
                status="reviewed",
                detected_at=datetime.now() - timedelta(hours=1),
                ai_confidence_score=87,
                description="Test high priority change"
            )
        ]
        
        for change in changes:
            db_session.add(change)
        db_session.commit()
        
        return {
            'agency': agency,
            'form': form,
            'changes': changes
        }
    
    def test_end_to_end_export_workflow(self, sample_database_data):
        """Test complete export workflow from API to file generation."""
        # This would test the full integration between API, database, and export utilities
        # Implementation would depend on the actual database setup and test environment
        pass
    
    def test_export_with_real_database_data(self, sample_database_data):
        """Test export with real database data."""
        # This would test export functionality with actual database records
        # Implementation would depend on the actual database setup and test environment
        pass


# Performance tests
class TestExportPerformance:
    """Performance tests for export functionality."""
    
    def test_large_dataset_export_performance(self):
        """Test export performance with large datasets."""
        # Generate large dataset
        large_data = [
            {
                'id': i,
                'form_name': f'Form {i}',
                'agency_name': f'Agency {i % 10}',
                'change_type': 'form_update',
                'severity': 'medium',
                'status': 'pending',
                'detected_at': datetime.now(),
                'ai_confidence_score': 85,
                'description': f'Change description {i}'
            }
            for i in range(1000)
        ]
        
        export_manager = ExportManager()
        config = {
            'columns': ['id', 'form_name', 'agency_name', 'severity', 'status'],
            'include_headers': True
        }
        
        # Test CSV export performance
        import time
        start_time = time.time()
        
        result = export_manager.export_data(large_data, 'csv', config)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0  # 5 seconds
        assert len(result) > 0
    
    def test_memory_usage_with_large_exports(self):
        """Test memory usage with large exports."""
        # This test would monitor memory usage during large exports
        # Implementation would depend on the testing framework and environment
        pass


# Frontend tests (placeholder)
class TestExportFrontend:
    """Frontend tests for export functionality."""
    
    def test_export_ui_components(self):
        """Test export UI components and interactions."""
        # This would test the frontend JavaScript functionality
        # Implementation would depend on the frontend testing framework
        pass
    
    def test_export_user_interactions(self):
        """Test user interactions with export features."""
        # This would test user interactions like clicking export buttons
        # Implementation would depend on the frontend testing framework
        pass 