"""
Unit tests for Report Export API

Tests the report export functionality including:
- Weekly report exports
- Analytics report exports
- Archive report exports
- Custom report exports
- Download functionality
- Export history
- Format validation
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from src.api.report_export import router
from src.reporting.report_export import (
    ReportExportService, export_weekly_report, export_analytics_report, export_archive_report
)
from src.database.models import User, Role, UserRole
from src.auth.auth import get_current_user

# Test data
SAMPLE_WEEKLY_EXPORT_REQUEST = {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-07T23:59:59",
    "format": "pdf",
    "include_charts": True,
    "include_analytics": True,
    "custom_title": "Test Weekly Report"
}

SAMPLE_ANALYTICS_EXPORT_REQUEST = {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-31T23:59:59",
    "format": "excel",
    "include_predictions": True,
    "include_anomalies": True,
    "include_correlations": True,
    "agencies": [1, 2, 3],
    "form_types": ["WH-347", "WH-348"]
}

SAMPLE_ARCHIVE_EXPORT_REQUEST = {
    "report_id": "test_report_123",
    "format": "csv",
    "include_metadata": True
}

SAMPLE_CUSTOM_EXPORT_REQUEST = {
    "report_data": {
        "title": "Custom Test Report",
        "content": "This is a test custom report",
        "data": [{"field1": "value1", "field2": "value2"}]
    },
    "format": "json",
    "report_type": "test",
    "include_charts": False
}

SAMPLE_EXPORT_RESPONSE = {
    "export_id": "weekly_export_20241201_120000",
    "format": "pdf",
    "filename": "weekly_report_20241201_120000.pdf",
    "size_bytes": 1024000,
    "generated_at": "2024-12-01T12:00:00",
    "download_url": "/api/reports/export/download/weekly_export_20241201_120000"
}


class TestReportExportAPI:
    """Test cases for Report Export API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        user = Mock(spec=User)
        user.id = 1
        user.email = "test@example.com"
        user.username = "testuser"
        return user
    
    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user."""
        user = Mock(spec=User)
        user.id = 2
        user.email = "admin@example.com"
        user.username = "admin"
        user.roles = [Mock(spec=Role, name="admin")]
        return user
    
    @pytest.fixture
    def mock_export_service(self):
        """Mock export service."""
        service = Mock(spec=ReportExportService)
        service.export_weekly_report.return_value = b"PDF content"
        service.export_analytics_report.return_value = b"Excel content"
        service.export_archive_report.return_value = b"CSV content"
        service.export_custom_report.return_value = '{"data": "JSON content"}'
        return service
    
    def test_export_weekly_report_success(self, client, mock_user, mock_export_service):
        """Test successful weekly report export."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/weekly", json=SAMPLE_WEEKLY_EXPORT_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert data["format"] == "pdf"
            assert "download_url" in data
            assert data["size_bytes"] > 0
    
    def test_export_weekly_report_invalid_format(self, client, mock_user):
        """Test weekly report export with invalid format."""
        invalid_request = SAMPLE_WEEKLY_EXPORT_REQUEST.copy()
        invalid_request["format"] = "invalid_format"
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.post("/api/reports/export/weekly", json=invalid_request)
            
            assert response.status_code == 422  # Validation error
    
    def test_export_weekly_report_service_error(self, client, mock_user, mock_export_service):
        """Test weekly report export when service fails."""
        mock_export_service.export_weekly_report.side_effect = Exception("Export failed")
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/weekly", json=SAMPLE_WEEKLY_EXPORT_REQUEST)
            
            assert response.status_code == 500
            assert "Export failed" in response.json()["detail"]
    
    def test_export_analytics_report_success(self, client, mock_user, mock_export_service):
        """Test successful analytics report export."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/analytics", json=SAMPLE_ANALYTICS_EXPORT_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert data["format"] == "excel"
            assert "download_url" in data
    
    def test_export_analytics_report_missing_dates(self, client, mock_user, mock_export_service):
        """Test analytics report export with missing dates."""
        request_without_dates = SAMPLE_ANALYTICS_EXPORT_REQUEST.copy()
        del request_without_dates["start_date"]
        del request_without_dates["end_date"]
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/analytics", json=request_without_dates)
            
            assert response.status_code == 200  # Should use defaults
    
    def test_export_archive_report_success(self, client, mock_user, mock_export_service):
        """Test successful archive report export."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/archive", json=SAMPLE_ARCHIVE_EXPORT_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert data["format"] == "csv"
            assert "download_url" in data
    
    def test_export_archive_report_missing_id(self, client, mock_user):
        """Test archive report export with missing report ID."""
        invalid_request = SAMPLE_ARCHIVE_EXPORT_REQUEST.copy()
        del invalid_request["report_id"]
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.post("/api/reports/export/archive", json=invalid_request)
            
            assert response.status_code == 422  # Validation error
    
    def test_export_archive_report_not_found(self, client, mock_user, mock_export_service):
        """Test archive report export when report not found."""
        mock_export_service.export_archive_report.side_effect = ValueError("Report not found")
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/archive", json=SAMPLE_ARCHIVE_EXPORT_REQUEST)
            
            assert response.status_code == 500
            assert "Report not found" in response.json()["detail"]
    
    def test_export_custom_report_success(self, client, mock_user, mock_export_service):
        """Test successful custom report export."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/custom", json=SAMPLE_CUSTOM_EXPORT_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert data["format"] == "json"
            assert "download_url" in data
    
    def test_export_custom_report_invalid_json(self, client, mock_user):
        """Test custom report export with invalid JSON data."""
        invalid_request = SAMPLE_CUSTOM_EXPORT_REQUEST.copy()
        invalid_request["report_data"] = "invalid json string"
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.post("/api/reports/export/custom", json=invalid_request)
            
            assert response.status_code == 422  # Validation error
    
    def test_download_export_success(self, client, mock_user):
        """Test successful export download."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.get("/api/reports/export/download/weekly_export_123")
            
            assert response.status_code == 200
            assert "Content-Disposition" in response.headers
            assert "attachment" in response.headers["Content-Disposition"]
    
    def test_download_export_not_found(self, client, mock_user):
        """Test download of non-existent export."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.get("/api/reports/export/download/nonexistent_export")
            
            assert response.status_code == 404
            assert "Export not found" in response.json()["detail"]
    
    def test_get_supported_formats(self, client):
        """Test getting supported export formats."""
        response = client.get("/api/reports/export/formats")
        
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert len(data["formats"]) == 5  # PDF, Excel, CSV, JSON, HTML
        
        formats = [f["format"] for f in data["formats"]]
        assert "pdf" in formats
        assert "excel" in formats
        assert "csv" in formats
        assert "json" in formats
        assert "html" in formats
    
    def test_get_export_status(self, client, mock_user):
        """Test getting export status."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.get("/api/reports/export/status/weekly_export_123")
            
            assert response.status_code == 200
            data = response.json()
            assert "export_id" in data
            assert "status" in data
            assert "progress" in data
    
    def test_delete_export_success(self, client, mock_user):
        """Test successful export deletion."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.delete("/api/reports/export/weekly_export_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["deleted"] is True
            assert "Export deleted successfully" in data["message"]
    
    def test_get_export_history(self, client, mock_user):
        """Test getting export history."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.get("/api/reports/export/history")
            
            assert response.status_code == 200
            data = response.json()
            assert "exports" in data
            assert "total" in data
            assert "limit" in data
            assert "offset" in data
    
    def test_get_export_history_with_pagination(self, client, mock_user):
        """Test getting export history with pagination parameters."""
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.get("/api/reports/export/history?limit=10&offset=5")
            
            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 5
    
    def test_export_without_authentication(self, client):
        """Test export endpoints without authentication."""
        endpoints = [
            ("/api/reports/export/weekly", "POST", SAMPLE_WEEKLY_EXPORT_REQUEST),
            ("/api/reports/export/analytics", "POST", SAMPLE_ANALYTICS_EXPORT_REQUEST),
            ("/api/reports/export/archive", "POST", SAMPLE_ARCHIVE_EXPORT_REQUEST),
            ("/api/reports/export/custom", "POST", SAMPLE_CUSTOM_EXPORT_REQUEST),
            ("/api/reports/export/download/test", "GET", None),
            ("/api/reports/export/status/test", "GET", None),
            ("/api/reports/export/history", "GET", None),
            ("/api/reports/export/test", "DELETE", None)
        ]
        
        for endpoint, method, data in endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "GET":
                response = client.get(endpoint)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401  # Unauthorized
    
    def test_export_with_invalid_date_format(self, client, mock_user):
        """Test export with invalid date format."""
        invalid_request = SAMPLE_WEEKLY_EXPORT_REQUEST.copy()
        invalid_request["start_date"] = "invalid-date"
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user):
            response = client.post("/api/reports/export/weekly", json=invalid_request)
            
            assert response.status_code == 422  # Validation error
    
    def test_export_with_future_dates(self, client, mock_user, mock_export_service):
        """Test export with future dates."""
        future_request = SAMPLE_WEEKLY_EXPORT_REQUEST.copy()
        future_date = datetime.now() + timedelta(days=30)
        future_request["start_date"] = future_date.isoformat()
        future_request["end_date"] = (future_date + timedelta(days=7)).isoformat()
        
        with patch('src.api.report_export.get_current_user', return_value=mock_user), \
             patch('src.api.report_export.export_service', mock_export_service):
            
            response = client.post("/api/reports/export/weekly", json=future_request)
            
            # Should still work (validation allows future dates)
            assert response.status_code == 200


class TestReportExportService:
    """Test cases for ReportExportService class."""
    
    @pytest.fixture
    def export_service(self):
        """Create ReportExportService instance."""
        return ReportExportService()
    
    @pytest.fixture
    def mock_weekly_generator(self):
        """Mock weekly report generator."""
        generator = Mock()
        generator.generate_weekly_report.return_value = {
            "executive_summary": {"total_changes": 10},
            "form_changes": [{"agency_name": "Test Agency", "form_name": "Test Form"}],
            "monitoring_statistics": {"total_runs": 100}
        }
        return generator
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Mock analytics service."""
        service = Mock()
        service.generate_comprehensive_analytics.return_value = {
            "summary": {"data_points_analyzed": 1000},
            "trend_analysis": {"trend_direction": "increasing"},
            "insights": ["Test insight"]
        }
        return service
    
    @pytest.fixture
    def mock_archiver(self):
        """Mock archiver service."""
        archiver = Mock()
        archiver.retrieve_report.return_value = {
            "form_changes": [{"agency_name": "Test Agency", "form_name": "Test Form"}]
        }
        archiver._get_metadata.return_value = {
            "title": "Test Archived Report",
            "generated_at": "2024-01-01T00:00:00"
        }
        return archiver
    
    def test_init_export_service(self, export_service):
        """Test export service initialization."""
        assert export_service.supported_formats == ['pdf', 'excel', 'csv', 'json', 'html']
        assert export_service.max_export_size == 50000
    
    def test_export_weekly_report_pdf(self, export_service, mock_weekly_generator, mock_analytics_service):
        """Test weekly report export to PDF format."""
        with patch.object(export_service, 'weekly_generator', mock_weekly_generator), \
             patch.object(export_service, 'analytics_service', mock_analytics_service):
            
            result = export_service.export_weekly_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                format='pdf'
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    def test_export_weekly_report_excel(self, export_service, mock_weekly_generator, mock_analytics_service):
        """Test weekly report export to Excel format."""
        with patch.object(export_service, 'weekly_generator', mock_weekly_generator), \
             patch.object(export_service, 'analytics_service', mock_analytics_service):
            
            result = export_service.export_weekly_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                format='excel'
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    def test_export_weekly_report_csv(self, export_service, mock_weekly_generator):
        """Test weekly report export to CSV format."""
        with patch.object(export_service, 'weekly_generator', mock_weekly_generator):
            
            result = export_service.export_weekly_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                format='csv'
            )
            
            assert isinstance(result, str)
            assert len(result) > 0
    
    def test_export_weekly_report_json(self, export_service, mock_weekly_generator):
        """Test weekly report export to JSON format."""
        with patch.object(export_service, 'weekly_generator', mock_weekly_generator):
            
            result = export_service.export_weekly_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                format='json'
            )
            
            assert isinstance(result, str)
            data = json.loads(result)
            assert "executive_summary" in data
    
    def test_export_weekly_report_html(self, export_service, mock_weekly_generator):
        """Test weekly report export to HTML format."""
        with patch.object(export_service, 'weekly_generator', mock_weekly_generator):
            
            result = export_service.export_weekly_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                format='html'
            )
            
            assert isinstance(result, str)
            assert "<html>" in result
            assert "</html>" in result
    
    def test_export_weekly_report_invalid_format(self, export_service):
        """Test weekly report export with invalid format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            export_service.export_weekly_report(format='invalid')
    
    def test_export_analytics_report_pdf(self, export_service, mock_analytics_service):
        """Test analytics report export to PDF format."""
        with patch.object(export_service, 'analytics_service', mock_analytics_service):
            
            result = export_service.export_analytics_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                format='pdf'
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    def test_export_analytics_report_excel(self, export_service, mock_analytics_service):
        """Test analytics report export to Excel format."""
        with patch.object(export_service, 'analytics_service', mock_analytics_service):
            
            result = export_service.export_analytics_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                format='excel'
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    def test_export_archive_report_success(self, export_service, mock_archiver):
        """Test successful archive report export."""
        with patch.object(export_service, 'archiver', mock_archiver):
            
            result = export_service.export_archive_report(
                report_id="test_report_123",
                format='pdf'
            )
            
            assert isinstance(result, bytes)
            assert len(result) > 0
    
    def test_export_archive_report_not_found(self, export_service, mock_archiver):
        """Test archive report export when report not found."""
        mock_archiver.retrieve_report.return_value = None
        
        with patch.object(export_service, 'archiver', mock_archiver):
            with pytest.raises(ValueError, match="Archived report test_report_123 not found"):
                export_service.export_archive_report(
                    report_id="test_report_123",
                    format='pdf'
                )
    
    def test_export_custom_report_success(self, export_service):
        """Test successful custom report export."""
        custom_data = {
            "title": "Custom Report",
            "content": "This is a custom report",
            "data": [{"field1": "value1"}]
        }
        
        result = export_service.export_custom_report(
            report_data=custom_data,
            format='json'
        )
        
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["title"] == "Custom Report"
    
    def test_format_row_for_csv(self, export_service):
        """Test CSV row formatting."""
        row = {
            "string_field": "test",
            "number_field": 123,
            "date_field": datetime(2024, 1, 1, 12, 0, 0),
            "dict_field": {"key": "value"},
            "none_field": None
        }
        
        formatted = export_service._format_row_for_csv(row)
        
        assert formatted["string_field"] == "test"
        assert formatted["number_field"] == "123"
        assert "2024-01-01 12:00:00" in formatted["date_field"]
        assert "key" in formatted["dict_field"]
        assert formatted["none_field"] == ""


class TestExportConvenienceFunctions:
    """Test cases for export convenience functions."""
    
    def test_export_weekly_report_function(self):
        """Test export_weekly_report convenience function."""
        with patch('src.reporting.report_export.export_service') as mock_service:
            mock_service.export_weekly_report.return_value = b"test content"
            
            result = export_weekly_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 7),
                format='pdf'
            )
            
            assert result == b"test content"
            mock_service.export_weekly_report.assert_called_once()
    
    def test_export_analytics_report_function(self):
        """Test export_analytics_report convenience function."""
        with patch('src.reporting.report_export.export_service') as mock_service:
            mock_service.export_analytics_report.return_value = b"test content"
            
            result = export_analytics_report(
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                format='excel'
            )
            
            assert result == b"test content"
            mock_service.export_analytics_report.assert_called_once()
    
    def test_export_archive_report_function(self):
        """Test export_archive_report convenience function."""
        with patch('src.reporting.report_export.export_service') as mock_service:
            mock_service.export_archive_report.return_value = b"test content"
            
            result = export_archive_report(
                report_id="test_report_123",
                format='csv'
            )
            
            assert result == b"test content"
            mock_service.export_archive_report.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 