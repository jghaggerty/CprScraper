"""
Unit tests for Report Archiving API

This module contains comprehensive tests for the report archiving functionality,
including archive operations, search, retrieval, and management features.
"""

import pytest
import json
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.report_archiving import router
from src.reporting.report_archiving import (
    ReportArchiver, ArchiveMetadata, ReportType, ArchiveStatus,
    get_archiver
)
from src.database.models import User, Role, UserRole
from src.auth.auth import get_current_user


# Test data
SAMPLE_REPORT_DATA = {
    "report_metadata": {
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-07T23:59:59",
        "generated_at": "2024-01-08T10:00:00"
    },
    "executive_summary": {
        "total_changes": 15,
        "critical_changes": 2,
        "high_priority_changes": 5
    },
    "form_changes": [
        {
            "id": 1,
            "form_name": "Test Form 1",
            "agency_name": "Test Agency",
            "change_type": "field_addition",
            "severity": "high"
        }
    ]
}

SAMPLE_ARCHIVE_REQUEST = {
    "report_data": SAMPLE_REPORT_DATA,
    "report_type": "weekly_summary",
    "title": "Test Weekly Report",
    "description": "Test report for unit testing",
    "tags": ["test", "weekly", "compliance"],
    "retention_days": 2555,
    "access_level": "standard"
}

SAMPLE_SEARCH_REQUEST = {
    "report_type": "weekly_summary",
    "title_search": "Test",
    "date_from": "2024-01-01T00:00:00",
    "date_to": "2024-01-31T23:59:59",
    "tags": ["test"],
    "limit": 10,
    "offset": 0
}


class TestReportArchivingAPI:
    """Test cases for Report Archiving API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        user.roles = []
        return user
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create mock admin user for testing."""
        user = Mock(spec=User)
        user.id = 2
        user.username = "adminuser"
        user.email = "admin@example.com"
        user.is_active = True
        
        # Mock admin role
        admin_role = Mock(spec=Role)
        admin_role.name = "admin"
        user_role = Mock(spec=UserRole)
        user_role.role = admin_role
        user.roles = [user_role]
        return user
    
    @pytest.fixture
    def temp_archive_dir(self):
        """Create temporary archive directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_archiver(self, temp_archive_dir):
        """Create mock archiver instance."""
        with patch('src.api.report_archiving.get_archiver') as mock_get_archiver:
            archiver = ReportArchiver(archive_path=temp_archive_dir)
            mock_get_archiver.return_value = archiver
            yield archiver
    
    @pytest.fixture
    def sample_metadata(self):
        """Create sample archive metadata."""
        return ArchiveMetadata(
            report_id="test_report_20240108_100000_test_weekly",
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Weekly Report",
            description="Test report for unit testing",
            generated_at=datetime.now(),
            report_period_start=datetime(2024, 1, 1),
            report_period_end=datetime(2024, 1, 7),
            generated_by=1,
            file_size_bytes=1024,
            file_hash="test_hash_123",
            format="json",
            version="1.0",
            tags=["test", "weekly"],
            filters_applied={},
            status=ArchiveStatus.ACTIVE,
            retention_days=2555,
            access_level="standard",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    def test_archive_report_success(self, client, mock_user, mock_archiver, sample_metadata):
        """Test successful report archiving."""
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'archive_report', return_value=sample_metadata):
                response = client.post(
                    "/api/reports/archiving/archive",
                    json=SAMPLE_ARCHIVE_REQUEST,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["report_id"] == sample_metadata.report_id
                assert data["title"] == sample_metadata.title
                assert data["report_type"] == "weekly_summary"
                assert data["status"] == "active"
    
    def test_archive_report_invalid_data(self, client, mock_user):
        """Test archiving with invalid report data."""
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            invalid_request = SAMPLE_ARCHIVE_REQUEST.copy()
            invalid_request["report_data"] = "invalid_json"
            
            response = client.post(
                "/api/reports/archiving/archive",
                json=invalid_request,
                headers={"Authorization": "Bearer test_token"}
            )
                
            assert response.status_code == 422  # Validation error
    
    def test_retrieve_report_success(self, client, mock_user, mock_archiver):
        """Test successful report retrieval."""
        report_id = "test_report_123"
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'retrieve_report', return_value=SAMPLE_REPORT_DATA):
                response = client.get(
                    f"/api/reports/archiving/reports/{report_id}",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["report_metadata"]["start_date"] == "2024-01-01T00:00:00"
                assert data["executive_summary"]["total_changes"] == 15
    
    def test_retrieve_report_not_found(self, client, mock_user, mock_archiver):
        """Test report retrieval when report doesn't exist."""
        report_id = "nonexistent_report"
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'retrieve_report', return_value=None):
                response = client.get(
                    f"/api/reports/archiving/reports/{report_id}",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 404
                assert "not found" in response.json()["detail"].lower()
    
    def test_search_reports_success(self, client, mock_user, mock_archiver, sample_metadata):
        """Test successful report search."""
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'search_reports', return_value=[sample_metadata]):
                response = client.post(
                    "/api/reports/archiving/search",
                    json=SAMPLE_SEARCH_REQUEST,
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["reports"]) == 1
                assert data["reports"][0]["report_id"] == sample_metadata.report_id
                assert data["total_count"] == 1
                assert not data["has_more"]
    
    def test_search_reports_get_params(self, client, mock_user, mock_archiver, sample_metadata):
        """Test report search using GET parameters."""
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'search_reports', return_value=[sample_metadata]):
                response = client.get(
                    "/api/reports/archiving/search",
                    params={
                        "report_type": "weekly_summary",
                        "title_search": "Test",
                        "limit": 10
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data["reports"]) == 1
    
    def test_get_archive_statistics(self, client, mock_user, mock_archiver):
        """Test getting archive statistics."""
        stats = {
            "total_reports": 50,
            "reports_by_type": {"weekly_summary": 30, "daily_summary": 20},
            "total_storage_bytes": 1048576,
            "total_storage_mb": 1.0,
            "reports_by_status": {"active": 45, "archived": 5},
            "oldest_report": "2023-01-01T00:00:00",
            "newest_report": "2024-01-08T10:00:00"
        }
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'get_archive_statistics', return_value=stats):
                response = client.get(
                    "/api/reports/archiving/statistics",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total_reports"] == 50
                assert data["total_storage_mb"] == 1.0
                assert len(data["reports_by_type"]) == 2
    
    def test_cleanup_expired_reports(self, client, mock_user, mock_archiver):
        """Test cleanup of expired reports."""
        cleanup_result = {
            "expired_reports_found": 5,
            "successfully_deleted": 4,
            "failed_deletions": 1
        }
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'cleanup_expired_reports', return_value=cleanup_result):
                response = client.post(
                    "/api/reports/archiving/cleanup",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["expired_reports_found"] == 5
                assert data["successfully_deleted"] == 4
                assert data["failed_deletions"] == 1
    
    def test_export_metadata_admin_only(self, client, mock_user, mock_archiver):
        """Test metadata export (admin only)."""
        export_data = b'{"metadata": "test"}'
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'export_archive_metadata', return_value=export_data):
                response = client.get(
                    "/api/reports/archiving/export/metadata?format=json",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                # Should fail for non-admin user
                assert response.status_code == 403
    
    def test_export_metadata_admin_success(self, client, mock_admin_user, mock_archiver):
        """Test metadata export with admin user."""
        export_data = b'{"metadata": "test"}'
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_admin_user):
            with patch.object(mock_archiver, 'export_archive_metadata', return_value=export_data):
                response = client.get(
                    "/api/reports/archiving/export/metadata?format=json",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["content"] == export_data
                assert data["content_type"] == "application/json"
                assert "archive_metadata" in data["filename"]
    
    def test_delete_report_success(self, client, mock_user, mock_archiver, sample_metadata):
        """Test successful report deletion."""
        report_id = "test_report_123"
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, '_get_metadata', return_value=sample_metadata):
                with patch('sqlite3.connect') as mock_sqlite:
                    mock_conn = Mock()
                    mock_sqlite.return_value.__enter__.return_value = mock_conn
                    
                    response = client.delete(
                        f"/api/reports/archiving/reports/{report_id}",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    
                    assert response.status_code == 200
                    assert "deleted successfully" in response.json()["message"]
    
    def test_delete_report_not_found(self, client, mock_user, mock_archiver):
        """Test report deletion when report doesn't exist."""
        report_id = "nonexistent_report"
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, '_get_metadata', return_value=None):
                response = client.delete(
                    f"/api/reports/archiving/reports/{report_id}",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 404
    
    def test_delete_report_insufficient_permissions(self, client, mock_user, mock_archiver):
        """Test report deletion with insufficient permissions."""
        report_id = "test_report_123"
        
        # Create metadata for different user
        other_user_metadata = ArchiveMetadata(
            report_id=report_id,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test",
            generated_at=datetime.now(),
            report_period_start=datetime.now(),
            report_period_end=datetime.now(),
            generated_by=999,  # Different user
            file_size_bytes=1024,
            file_hash="test",
            format="json",
            version="1.0",
            tags=[],
            filters_applied={},
            status=ArchiveStatus.ACTIVE,
            retention_days=2555,
            access_level="standard",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, '_get_metadata', return_value=other_user_metadata):
                response = client.delete(
                    f"/api/reports/archiving/reports/{report_id}",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 403
    
    def test_get_report_metadata(self, client, mock_user, mock_archiver, sample_metadata):
        """Test getting report metadata."""
        report_id = "test_report_123"
        
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, '_get_metadata', return_value=sample_metadata):
                with patch.object(mock_archiver, '_check_access_permissions', return_value=True):
                    response = client.get(
                        f"/api/reports/archiving/reports/{report_id}/metadata",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["report_id"] == sample_metadata.report_id
                    assert data["title"] == sample_metadata.title
    
    def test_archive_weekly_report_convenience(self, client, mock_user, mock_archiver, sample_metadata):
        """Test convenience endpoint for archiving weekly reports."""
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch('src.api.report_archiving.archive_weekly_report', return_value=sample_metadata):
                response = client.post(
                    "/api/reports/archiving/archive/weekly",
                    json={
                        "report_data": SAMPLE_REPORT_DATA,
                        "title": "Test Weekly Report",
                        "description": "Test description",
                        "tags": ["test", "weekly"]
                    },
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["report_id"] == sample_metadata.report_id
    
    def test_get_recent_reports(self, client, mock_user, mock_archiver, sample_metadata):
        """Test getting recent reports."""
        with patch('src.api.report_archiving.get_current_user', return_value=mock_user):
            with patch.object(mock_archiver, 'search_reports', return_value=[sample_metadata]):
                response = client.get(
                    "/api/reports/archiving/recent?limit=5",
                    headers={"Authorization": "Bearer test_token"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["report_id"] == sample_metadata.report_id


class TestReportArchiver:
    """Test cases for ReportArchiver class."""
    
    @pytest.fixture
    def temp_archive_dir(self):
        """Create temporary archive directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def archiver(self, temp_archive_dir):
        """Create archiver instance for testing."""
        return ReportArchiver(archive_path=temp_archive_dir)
    
    def test_init_creates_directory(self, temp_archive_dir):
        """Test that archiver creates archive directory."""
        archiver = ReportArchiver(archive_path=temp_archive_dir)
        assert Path(temp_archive_dir).exists()
        assert (Path(temp_archive_dir) / "archive_metadata.db").exists()
    
    def test_archive_report_success(self, archiver):
        """Test successful report archiving."""
        metadata = archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test description",
            generated_by=1,
            tags=["test"],
            retention_days=2555,
            access_level="standard"
        )
        
        assert metadata.report_id is not None
        assert metadata.title == "Test Report"
        assert metadata.report_type == ReportType.WEEKLY_SUMMARY
        assert metadata.status == ArchiveStatus.ACTIVE
        
        # Check that file was created
        file_path = archiver._get_file_path(metadata.report_id, metadata.format)
        assert file_path.exists()
    
    def test_retrieve_report_success(self, archiver):
        """Test successful report retrieval."""
        # First archive a report
        metadata = archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test description",
            generated_by=1
        )
        
        # Then retrieve it
        retrieved_data = archiver.retrieve_report(metadata.report_id, user_id=1)
        
        assert retrieved_data is not None
        assert retrieved_data["report_metadata"]["start_date"] == "2024-01-01T00:00:00"
        assert retrieved_data["executive_summary"]["total_changes"] == 15
    
    def test_retrieve_report_not_found(self, archiver):
        """Test report retrieval when report doesn't exist."""
        retrieved_data = archiver.retrieve_report("nonexistent_report", user_id=1)
        assert retrieved_data is None
    
    def test_search_reports(self, archiver):
        """Test report search functionality."""
        # Archive multiple reports
        archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Weekly Report 1",
            description="First weekly report",
            generated_by=1
        )
        
        archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.DAILY_SUMMARY,
            title="Daily Report 1",
            description="First daily report",
            generated_by=1
        )
        
        # Search for weekly reports
        results = archiver.search_reports(
            report_type=ReportType.WEEKLY_SUMMARY,
            limit=10
        )
        
        assert len(results) == 1
        assert results[0].report_type == ReportType.WEEKLY_SUMMARY
        assert "Weekly Report" in results[0].title
    
    def test_get_archive_statistics(self, archiver):
        """Test archive statistics."""
        # Archive a report
        archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test description",
            generated_by=1
        )
        
        stats = archiver.get_archive_statistics()
        
        assert stats["total_reports"] == 1
        assert stats["reports_by_type"]["weekly_summary"] == 1
        assert stats["total_storage_bytes"] > 0
        assert stats["reports_by_status"]["active"] == 1
    
    def test_cleanup_expired_reports(self, archiver):
        """Test cleanup of expired reports."""
        # Archive a report with short retention
        metadata = archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test description",
            generated_by=1,
            retention_days=1  # Very short retention
        )
        
        # Manually update the generated_at to be old
        db_path = archiver.archive_path / "archive_metadata.db"
        import sqlite3
        
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE archive_metadata SET generated_at = datetime('now', '-2 days') WHERE report_id = ?",
                (metadata.report_id,)
            )
        
        # Run cleanup
        cleanup_result = archiver.cleanup_expired_reports()
        
        assert cleanup_result["expired_reports_found"] == 1
        assert cleanup_result["successfully_deleted"] == 1
        assert cleanup_result["failed_deletions"] == 0
    
    def test_export_archive_metadata(self, archiver):
        """Test metadata export."""
        # Archive a report
        archiver.archive_report(
            report_data=SAMPLE_REPORT_DATA,
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test description",
            generated_by=1
        )
        
        # Export metadata
        export_data = archiver.export_archive_metadata(format='json')
        
        assert export_data is not None
        metadata_list = json.loads(export_data.decode('utf-8'))
        assert len(metadata_list) == 1
        assert metadata_list[0]["title"] == "Test Report"
    
    def test_access_control_public(self, archiver):
        """Test access control for public reports."""
        metadata = ArchiveMetadata(
            report_id="test",
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test",
            description="Test",
            generated_at=datetime.now(),
            report_period_start=datetime.now(),
            report_period_end=datetime.now(),
            generated_by=1,
            file_size_bytes=1024,
            file_hash="test",
            format="json",
            version="1.0",
            tags=[],
            filters_applied={},
            status=ArchiveStatus.ACTIVE,
            retention_days=2555,
            access_level="public",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Should allow access for any user
        assert archiver._check_access_permissions(metadata, None) == True
        assert archiver._check_access_permissions(metadata, 1) == True
    
    def test_access_control_restricted(self, archiver):
        """Test access control for restricted reports."""
        metadata = ArchiveMetadata(
            report_id="test",
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test",
            description="Test",
            generated_at=datetime.now(),
            report_period_start=datetime.now(),
            report_period_end=datetime.now(),
            generated_by=1,
            file_size_bytes=1024,
            file_hash="test",
            format="json",
            version="1.0",
            tags=[],
            filters_applied={},
            status=ArchiveStatus.ACTIVE,
            retention_days=2555,
            access_level="restricted",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Should require authenticated user
        assert archiver._check_access_permissions(metadata, None) == False
        assert archiver._check_access_permissions(metadata, 1) == True


class TestArchiveMetadata:
    """Test cases for ArchiveMetadata class."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        metadata = ArchiveMetadata(
            report_id="test",
            report_type=ReportType.WEEKLY_SUMMARY,
            title="Test Report",
            description="Test description",
            generated_at=datetime(2024, 1, 1),
            report_period_start=datetime(2024, 1, 1),
            report_period_end=datetime(2024, 1, 7),
            generated_by=1,
            file_size_bytes=1024,
            file_hash="test_hash",
            format="json",
            version="1.0",
            tags=["test"],
            filters_applied={"state": "CA"},
            status=ArchiveStatus.ACTIVE,
            retention_days=2555,
            access_level="standard",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1)
        )
        
        data = metadata.to_dict()
        
        assert data["report_id"] == "test"
        assert data["report_type"] == "weekly_summary"
        assert data["status"] == "active"
        assert data["title"] == "Test Report"
        assert data["tags"] == ["test"]
        assert data["filters_applied"] == {"state": "CA"}
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "report_id": "test",
            "report_type": "weekly_summary",
            "title": "Test Report",
            "description": "Test description",
            "generated_at": "2024-01-01T00:00:00",
            "report_period_start": "2024-01-01T00:00:00",
            "report_period_end": "2024-01-07T00:00:00",
            "generated_by": 1,
            "file_size_bytes": 1024,
            "file_hash": "test_hash",
            "format": "json",
            "version": "1.0",
            "tags": ["test"],
            "filters_applied": {"state": "CA"},
            "status": "active",
            "retention_days": 2555,
            "access_level": "standard",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        
        metadata = ArchiveMetadata.from_dict(data)
        
        assert metadata.report_id == "test"
        assert metadata.report_type == ReportType.WEEKLY_SUMMARY
        assert metadata.status == ArchiveStatus.ACTIVE
        assert metadata.title == "Test Report"
        assert metadata.tags == ["test"]
        assert metadata.filters_applied == {"state": "CA"}


if __name__ == "__main__":
    pytest.main([__file__]) 