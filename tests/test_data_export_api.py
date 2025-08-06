"""
Unit tests for enhanced data export API endpoints

Tests the comprehensive data export functionality with advanced filtering,
customization options, and multiple data sources.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.data_export import (
    router, 
    AdvancedFilterRequest, 
    ExportCustomization, 
    DataExportRequest,
    BulkExportRequest,
    export_jobs,
    _estimate_export_size,
    _fetch_form_changes_data,
    _apply_form_changes_filters
)
from src.database.models import FormChange, Form, Agency, MonitoringRun, Notification
from src.database.connection import get_db


class TestDataExportAPI:
    """Test the enhanced data export API endpoints."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.client = TestClient(router)
        
        # Clear export jobs before each test
        export_jobs.clear()
        
        self.sample_export_request = {
            "filters": {
                "date_from": "2024-01-01T00:00:00",
                "date_to": "2024-01-31T23:59:59",
                "severities": ["high", "critical"],
                "agency_ids": [1, 2],
                "ai_confidence_min": 80
            },
            "customization": {
                "format": "csv",
                "columns": ["id", "form_name", "severity", "detected_at"],
                "include_headers": True,
                "include_ai_analysis": True
            },
            "data_source": "form_changes"
        }
        
        self.sample_bulk_request = {
            "exports": [
                self.sample_export_request,
                {
                    "customization": {
                        "format": "excel",
                        "include_headers": True
                    },
                    "data_source": "agencies"
                }
            ],
            "combined_output": False,
            "archive_format": "zip"
        }
    
    def test_get_export_formats(self):
        """Test getting available export formats."""
        response = self.client.get("/api/data-export/formats")
        assert response.status_code == 200
        
        data = response.json()
        assert "formats" in data
        assert "default_format" in data
        assert "max_file_size_mb" in data
        
        formats = data["formats"]
        assert len(formats) == 3
        
        format_names = [f["format"] for f in formats]
        assert "csv" in format_names
        assert "excel" in format_names
        assert "pdf" in format_names
        
        # Check format details
        csv_format = next(f for f in formats if f["format"] == "csv")
        assert "max_records" in csv_format
        assert "supports_multiple_sheets" in csv_format
        assert csv_format["supports_multiple_sheets"] is False
    
    def test_get_available_data_sources(self):
        """Test getting available data sources."""
        response = self.client.get("/api/data-export/data-sources")
        assert response.status_code == 200
        
        data = response.json()
        assert "data_sources" in data
        
        sources = data["data_sources"]
        assert len(sources) >= 5
        
        source_names = [s["name"] for s in sources]
        assert "form_changes" in source_names
        assert "agencies" in source_names
        assert "forms" in source_names
        assert "monitoring_runs" in source_names
        assert "notifications" in source_names
        
        # Check each source has required fields
        for source in sources:
            assert "name" in source
            assert "description" in source
            assert "available_columns" in source
            assert isinstance(source["available_columns"], list)
    
    @patch('src.api.data_export._get_form_changes_filter_options')
    def test_get_filter_options_form_changes(self, mock_get_options):
        """Test getting filter options for form changes."""
        # Mock the response from the filter options function
        mock_get_options.return_value = {
            "agencies": [{"id": 1, "name": "Agency 1"}],
            "severities": ["high", "critical"],
            "date_ranges": ["24h", "7d", "30d"],
            "ai_confidence_range": {"min": 0, "max": 100}
        }
        
        response = self.client.get("/api/data-export/filter-options?data_source=form_changes")
        assert response.status_code == 200
        
        data = response.json()
        assert "agencies" in data
        assert "severities" in data
        assert "date_ranges" in data
        assert "ai_confidence_range" in data
    
    def test_get_filter_options_invalid_source(self):
        """Test getting filter options for invalid data source."""
        response = self.client.get("/api/data-export/filter-options?data_source=invalid")
        assert response.status_code == 400
        assert "Unknown data source" in response.json()["detail"]
    
    @patch('src.api.data_export.get_db')
    @patch('src.api.data_export._estimate_export_size')
    @patch('src.api.data_export.BackgroundTasks.add_task')
    def test_create_export_job_success(self, mock_add_task, mock_estimate, mock_get_db):
        """Test successful export job creation."""
        # Mock dependencies
        mock_estimate.return_value = (1000, 2.5)  # 1000 records, 2.5MB
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        response = self.client.post("/api/data-export/export", json=self.sample_export_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["estimated_records"] == 1000
        assert data["estimated_size_mb"] == 2.5
        assert "expires_at" in data
        assert "created_at" in data
        
        # Check that background task was scheduled
        mock_add_task.assert_called_once()
    
    @patch('src.api.data_export.get_db')
    @patch('src.api.data_export._estimate_export_size')
    def test_create_export_job_too_large(self, mock_estimate, mock_get_db):
        """Test export job creation with data too large."""
        # Mock large export size
        mock_estimate.return_value = (200000, 150.0)  # Exceeds limits
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        response = self.client.post("/api/data-export/export", json=self.sample_export_request)
        assert response.status_code == 400
        assert "Export too large" in response.json()["detail"]
    
    def test_get_export_status_not_found(self):
        """Test getting status of non-existent export job."""
        response = self.client.get("/api/data-export/export/non_existent/status")
        assert response.status_code == 404
        assert "Export job not found" in response.json()["detail"]
    
    def test_get_export_status_success(self):
        """Test getting status of existing export job."""
        # Create a mock job
        job_id = "test_job_123"
        export_jobs[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "progress_percent": 50,
            "records_processed": 500,
            "total_records": 1000,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        
        response = self.client.get(f"/api/data-export/export/{job_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "processing"
        assert data["progress_percent"] == 50
        assert data["records_processed"] == 500
        assert data["total_records"] == 1000
    
    def test_get_export_status_expired(self):
        """Test getting status of expired export job."""
        # Create an expired job
        job_id = "expired_job_123"
        export_jobs[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "created_at": datetime.now() - timedelta(hours=25),
            "expires_at": datetime.now() - timedelta(hours=1)  # Expired
        }
        
        response = self.client.get(f"/api/data-export/export/{job_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "expired"
    
    def test_download_export_not_found(self):
        """Test downloading non-existent export."""
        response = self.client.get("/api/data-export/export/non_existent/download")
        assert response.status_code == 404
        assert "Export job not found" in response.json()["detail"]
    
    def test_download_export_not_ready(self):
        """Test downloading export that's not completed."""
        job_id = "processing_job_123"
        export_jobs[job_id] = {
            "status": "processing",
            "expires_at": datetime.now() + timedelta(hours=24)
        }
        
        response = self.client.get(f"/api/data-export/export/{job_id}/download")
        assert response.status_code == 400
        assert "Export not ready" in response.json()["detail"]
    
    def test_download_export_expired(self):
        """Test downloading expired export."""
        job_id = "expired_job_123"
        export_jobs[job_id] = {
            "status": "completed",
            "expires_at": datetime.now() - timedelta(hours=1)  # Expired
        }
        
        response = self.client.get(f"/api/data-export/export/{job_id}/download")
        assert response.status_code == 410
        assert "Export has expired" in response.json()["detail"]
    
    def test_cancel_export_job_not_found(self):
        """Test cancelling non-existent export job."""
        response = self.client.delete("/api/data-export/export/non_existent")
        assert response.status_code == 404
        assert "Export job not found" in response.json()["detail"]
    
    def test_cancel_export_job_success(self):
        """Test successful export job cancellation."""
        job_id = "test_job_123"
        export_jobs[job_id] = {
            "status": "processing",
            "file_path": None
        }
        
        response = self.client.delete(f"/api/data-export/export/{job_id}")
        assert response.status_code == 200
        assert "cancelled and cleaned up" in response.json()["message"]
        assert job_id not in export_jobs
    
    @patch('src.api.data_export.get_db')
    @patch('src.api.data_export._estimate_export_size')
    @patch('src.api.data_export.BackgroundTasks.add_task')
    def test_create_bulk_export_job_success(self, mock_add_task, mock_estimate, mock_get_db):
        """Test successful bulk export job creation."""
        # Mock dependencies
        mock_estimate.return_value = (500, 1.0)  # 500 records, 1MB per export
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        response = self.client.post("/api/data-export/bulk-export", json=self.sample_bulk_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["estimated_records"] == 1000  # 2 exports * 500 records
        assert data["estimated_size_mb"] == 2.0   # 2 exports * 1MB
        
        # Check that background task was scheduled
        mock_add_task.assert_called_once()
    
    @patch('src.api.data_export.get_db')
    @patch('src.api.data_export._estimate_export_size')
    def test_create_bulk_export_job_too_large(self, mock_estimate, mock_get_db):
        """Test bulk export job creation with data too large."""
        # Mock large export size
        mock_estimate.return_value = (300000, 300.0)  # Exceeds bulk limits
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        response = self.client.post("/api/data-export/bulk-export", json=self.sample_bulk_request)
        assert response.status_code == 400
        assert "Bulk export too large" in response.json()["detail"]


class TestAdvancedFilterRequest:
    """Test the AdvancedFilterRequest model."""
    
    def test_valid_filter_request(self):
        """Test creating a valid filter request."""
        filter_data = {
            "date_from": "2024-01-01T00:00:00",
            "date_to": "2024-01-31T23:59:59",
            "agency_ids": [1, 2, 3],
            "severities": ["high", "critical"],
            "ai_confidence_min": 80,
            "ai_confidence_max": 100,
            "include_cosmetic": False,
            "sort_by": "detected_at",
            "sort_order": "desc",
            "limit": 1000
        }
        
        filter_req = AdvancedFilterRequest(**filter_data)
        assert filter_req.date_from == "2024-01-01T00:00:00"
        assert filter_req.agency_ids == [1, 2, 3]
        assert filter_req.ai_confidence_min == 80
        assert filter_req.include_cosmetic is False
        assert filter_req.limit == 1000
    
    def test_invalid_confidence_values(self):
        """Test validation of AI confidence values."""
        with pytest.raises(ValueError):
            AdvancedFilterRequest(ai_confidence_min=-10)  # Below 0
        
        with pytest.raises(ValueError):
            AdvancedFilterRequest(ai_confidence_max=150)  # Above 100
    
    def test_invalid_limit(self):
        """Test validation of limit values."""
        with pytest.raises(ValueError):
            AdvancedFilterRequest(limit=0)  # Below minimum
        
        with pytest.raises(ValueError):
            AdvancedFilterRequest(limit=20000)  # Above maximum


class TestExportCustomization:
    """Test the ExportCustomization model."""
    
    def test_valid_customization(self):
        """Test creating a valid export customization."""
        custom_data = {
            "format": "excel",
            "filename": "my_export.xlsx",
            "columns": ["id", "name", "severity"],
            "include_headers": True,
            "include_ai_analysis": False,
            "date_format": "%Y-%m-%d",
            "timezone": "EST"
        }
        
        customization = ExportCustomization(**custom_data)
        assert customization.format == "excel"
        assert customization.filename == "my_export.xlsx"
        assert customization.columns == ["id", "name", "severity"]
        assert customization.include_ai_analysis is False
    
    def test_invalid_format(self):
        """Test validation of export format."""
        with pytest.raises(ValueError, match="Format must be csv, excel, or pdf"):
            ExportCustomization(format="invalid")
    
    def test_default_values(self):
        """Test default values for customization."""
        customization = ExportCustomization(format="csv")
        assert customization.include_headers is True
        assert customization.include_metadata is True
        assert customization.include_ai_analysis is True
        assert customization.date_format == "%Y-%m-%d %H:%M:%S"
        assert customization.timezone == "UTC"


class TestDataExportRequest:
    """Test the DataExportRequest model."""
    
    def test_valid_export_request(self):
        """Test creating a valid export request."""
        request_data = {
            "filters": {
                "severities": ["high"],
                "ai_confidence_min": 90
            },
            "customization": {
                "format": "pdf",
                "include_headers": True
            },
            "data_source": "form_changes"
        }
        
        export_req = DataExportRequest(**request_data)
        assert export_req.data_source == "form_changes"
        assert export_req.filters.severities == ["high"]
        assert export_req.customization.format == "pdf"
    
    def test_minimal_export_request(self):
        """Test creating a minimal export request."""
        request_data = {
            "customization": {
                "format": "csv"
            }
        }
        
        export_req = DataExportRequest(**request_data)
        assert export_req.filters is None
        assert export_req.data_source == "form_changes"  # Default value
        assert export_req.customization.format == "csv"


class TestHelperFunctions:
    """Test helper functions for data export."""
    
    @patch('src.api.data_export.get_db')
    @pytest.mark.asyncio
    async def test_estimate_export_size_form_changes(self, mock_get_db):
        """Test export size estimation for form changes."""
        # Mock database session and query
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.count.return_value = 500
        
        request = DataExportRequest(
            customization=ExportCustomization(format="csv"),
            data_source="form_changes"
        )
        
        records, size_mb = await _estimate_export_size(request, mock_session)
        
        assert records == 500
        assert size_mb > 0  # Should calculate some size
        assert isinstance(size_mb, float)
    
    @patch('src.api.data_export.get_db')
    @pytest.mark.asyncio
    async def test_estimate_export_size_excel_larger(self, mock_get_db):
        """Test that Excel estimates are larger than CSV."""
        mock_session = Mock()
        mock_get_db.return_value = mock_session
        
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.count.return_value = 1000
        
        # CSV request
        csv_request = DataExportRequest(
            customization=ExportCustomization(format="csv")
        )
        
        # Excel request
        excel_request = DataExportRequest(
            customization=ExportCustomization(format="excel")
        )
        
        csv_records, csv_size = await _estimate_export_size(csv_request, mock_session)
        excel_records, excel_size = await _estimate_export_size(excel_request, mock_session)
        
        assert csv_records == excel_records  # Same data
        assert excel_size > csv_size  # Excel should be larger
    
    @pytest.mark.asyncio
    async def test_estimate_export_size_unknown_source(self):
        """Test export size estimation with unknown data source."""
        mock_session = Mock()
        
        request = DataExportRequest(
            customization=ExportCustomization(format="csv"),
            data_source="unknown_source"
        )
        
        with pytest.raises(ValueError, match="Unknown data source"):
            await _estimate_export_size(request, mock_session)
    
    def test_apply_form_changes_filters(self):
        """Test applying filters to form changes query."""
        # Mock query object
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.join.return_value = mock_query
        
        filters = AdvancedFilterRequest(
            date_from="2024-01-01T00:00:00",
            date_to="2024-01-31T23:59:59",
            severities=["high", "critical"],
            ai_confidence_min=80,
            include_cosmetic=False,
            description_contains="important change"
        )
        
        result_query = _apply_form_changes_filters(mock_query, filters)
        
        # Should return the query object (chained filters)
        assert result_query == mock_query
        
        # Verify that filter was called multiple times
        assert mock_query.filter.call_count >= 5  # At least 5 filters applied
    
    def test_apply_form_changes_filters_invalid_dates(self):
        """Test applying filters with invalid date formats."""
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        
        filters = AdvancedFilterRequest(
            date_from="invalid-date",
            date_to="also-invalid"
        )
        
        # Should not raise an error, just skip invalid dates
        result_query = _apply_form_changes_filters(mock_query, filters)
        assert result_query == mock_query


class TestDataFetchingFunctions:
    """Test data fetching functions for different sources."""
    
    @patch('src.api.data_export._apply_form_changes_filters')
    @pytest.mark.asyncio
    async def test_fetch_form_changes_data(self, mock_apply_filters):
        """Test fetching form changes data."""
        # Mock database session and query results
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_apply_filters.return_value = mock_query
        
        # Mock form change objects
        mock_form = Mock()
        mock_form.name = "Test Form"
        mock_agency = Mock()
        mock_agency.name = "Test Agency"
        mock_agency.agency_type = "federal"
        mock_form.agency = mock_agency
        
        mock_change = Mock()
        mock_change.id = 1
        mock_change.form = mock_form
        mock_change.change_type = "form_update"
        mock_change.severity = "high"
        mock_change.status = "pending"
        mock_change.detected_at = datetime.now()
        mock_change.description = "Test change"
        mock_change.url = "http://example.com"
        mock_change.ai_confidence_score = 95
        mock_change.impact_assessment = {"impact": "high"}
        
        mock_query.all.return_value = [mock_change]
        
        # Create request
        request = DataExportRequest(
            filters=AdvancedFilterRequest(
                sort_by="detected_at",
                sort_order="desc",
                limit=100
            ),
            customization=ExportCustomization(
                format="csv",
                include_ai_analysis=True,
                include_impact_assessment=True
            ),
            data_source="form_changes"
        )
        
        # Fetch data
        data = await _fetch_form_changes_data(request, mock_session)
        
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["form_name"] == "Test Form"
        assert data[0]["agency_name"] == "Test Agency"
        assert data[0]["severity"] == "high"
        assert "ai_confidence_score" in data[0]  # AI analysis included
        assert "impact_assessment" in data[0]    # Impact assessment included


if __name__ == '__main__':
    pytest.main([__file__])