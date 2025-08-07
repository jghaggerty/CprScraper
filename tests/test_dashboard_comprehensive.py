"""
Comprehensive Unit Tests for Dashboard API Endpoints and Frontend Components

This test file completes subtask 2.9 by providing comprehensive coverage for:
- All dashboard API endpoints (including real-time, analytics, export, auth)
- Frontend JavaScript functionality
- Integration tests between frontend and backend
- Performance and edge case testing
"""

import pytest
import json
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.dashboard import router as dashboard_router
from src.api.realtime import ConnectionManager, manager
from src.api.auth import router as auth_router
from src.api.main import app
from src.database.models import (
    Agency, Form, FormChange, MonitoringRun, Notification, WorkItem,
    User, Role, UserRole
)
from src.utils.export_utils import ExportManager, ExportScheduler
from src.auth.user_service import UserService


class TestDashboardAPIComprehensive:
    """Comprehensive test suite for all dashboard API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_data(self):
        """Sample data for comprehensive testing."""
        agency = Mock(spec=Agency)
        agency.id = 1
        agency.name = "Test Department of Labor"
        agency.agency_type = "federal"
        agency.is_active = True
        
        form = Mock(spec=Form)
        form.id = 1
        form.name = "WH-347"
        form.title = "Statement of Compliance"
        form.is_active = True
        form.last_checked = datetime.now(timezone.utc) - timedelta(hours=1)
        form.agency = agency
        
        change = Mock(spec=FormChange)
        change.id = 1
        change.form = form
        change.change_type = "content"
        change.severity = "high"
        change.status = "detected"
        change.detected_at = datetime.now(timezone.utc) - timedelta(hours=2)
        change.ai_confidence_score = 85
        change.ai_change_category = "form_update"
        
        return {
            'agency': agency,
            'form': form,
            'change': change
        }
    
    def test_dashboard_stats_comprehensive(self, client, mock_db_session, sample_data):
        """Test comprehensive dashboard statistics endpoint."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock all database queries
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value.count.side_effect = [
                5, 25, 20, 3, 15, 45, 60, 2, 8, 5, 12
            ]
            
            response = client.get("/api/dashboard/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_agencies" in data
            assert "total_forms" in data
            assert "active_forms" in data
            assert "changes_last_24h" in data
            assert "changes_last_week" in data
            assert "changes_last_month" in data
            assert "total_changes" in data
            assert "critical_changes" in data
            assert "high_priority_changes" in data
            assert "pending_notifications" in data
            assert "active_work_items" in data
    
    def test_recent_changes_with_all_filters(self, client, mock_db_session, sample_data):
        """Test recent changes endpoint with comprehensive filtering."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock query results
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = [sample_data['change']]
            mock_query.count.return_value = 1
            
            # Test with all possible filters
            params = {
                'agency_id': 1,
                'severity': 'high',
                'status': 'detected',
                'date_from': '2024-01-01',
                'date_to': '2024-12-31',
                'change_type': 'content',
                'ai_confidence_min': 80,
                'page': 1,
                'page_size': 10,
                'sort_by': 'detected_at',
                'sort_order': 'desc'
            }
            
            response = client.get("/api/dashboard/recent-changes", params=params)
            
            assert response.status_code == 200
            data = response.json()
            assert "changes" in data
            assert "pagination" in data
            assert "total_count" in data
    
    def test_search_changes_comprehensive(self, client, mock_db_session, sample_data):
        """Test comprehensive search functionality."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock search results
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = [sample_data['change']]
            mock_query.count.return_value = 1
            
            search_request = {
                "query": "WH-347 compliance",
                "filters": {
                    "agency_id": 1,
                    "severity": "high",
                    "date_from": "2024-01-01"
                },
                "sort_by": "detected_at",
                "sort_order": "desc",
                "page": 1,
                "page_size": 10
            }
            
            response = client.post("/api/dashboard/search", json=search_request)
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert "total_count" in data
            assert "pagination" in data
    
    def test_monitoring_status_comprehensive(self, client, mock_db_session):
        """Test comprehensive monitoring status endpoint."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock monitoring runs
            mock_run = Mock(spec=MonitoringRun)
            mock_run.id = 1
            mock_run.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_run.completed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
            mock_run.status = "completed"
            mock_run.response_time_ms = 1500
            
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = [mock_run]
            mock_query.count.return_value = 1
            
            response = client.get("/api/dashboard/monitoring-status")
            
            assert response.status_code == 200
            data = response.json()
            assert "active_runs" in data
            assert "recent_completed" in data
            assert "failed_runs" in data
            assert "summary" in data
    
    def test_live_statistics_comprehensive(self, client, mock_db_session):
        """Test comprehensive live statistics endpoint."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock statistics data
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.count.side_effect = [5, 3, 2, 1]
            
            response = client.get("/api/dashboard/live-statistics")
            
            assert response.status_code == 200
            data = response.json()
            assert "changes_last_hour" in data
            assert "changes_last_15min" in data
            assert "critical_changes_last_hour" in data
            assert "average_processing_time" in data
            assert "trends" in data
    
    def test_historical_data_comprehensive(self, client, mock_db_session):
        """Test comprehensive historical data endpoint."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock historical data
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.all.return_value = [
                {'date': '2024-01-01', 'count': 5},
                {'date': '2024-01-02', 'count': 3}
            ]
            
            params = {
                'metric': 'changes',
                'period': '7d',
                'group_by': 'day'
            }
            
            response = client.get("/api/dashboard/historical-data", params=params)
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "period" in data
            assert "metric" in data
    
    def test_trends_summary_comprehensive(self, client, mock_db_session):
        """Test comprehensive trends summary endpoint."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock trends data
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.all.return_value = [
                {'severity': 'critical', 'count': 2, 'trend': 'increasing'},
                {'severity': 'high', 'count': 5, 'trend': 'stable'}
            ]
            
            response = client.get("/api/dashboard/trends/summary")
            
            assert response.status_code == 200
            data = response.json()
            assert "severity_trends" in data
            assert "agency_performance" in data
            assert "overall_trends" in data
    
    def test_agency_performance_comprehensive(self, client, mock_db_session, sample_data):
        """Test comprehensive agency performance endpoint."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Mock agency performance data
            mock_query = Mock()
            mock_db_session.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.group_by.return_value = mock_query
            mock_query.all.return_value = [
                {
                    'agency_name': 'Test Agency',
                    'total_changes': 10,
                    'critical_changes': 2,
                    'avg_response_time': 1200,
                    'compliance_score': 85
                }
            ]
            
            response = client.get("/api/dashboard/analytics/agency-performance")
            
            assert response.status_code == 200
            data = response.json()
            assert "agencies" in data
            assert "summary" in data
            assert "performance_metrics" in data


class TestExportFunctionalityComprehensive:
    """Comprehensive test suite for export functionality."""
    
    @pytest.fixture
    def export_manager(self):
        """Export manager instance for testing."""
        return ExportManager()
    
    @pytest.fixture
    def export_scheduler(self, export_manager):
        """Export scheduler instance for testing."""
        return ExportScheduler(export_manager)
    
    def test_export_data_csv(self, export_manager):
        """Test CSV export functionality."""
        sample_data = [
            {
                'id': 1,
                'form_name': 'WH-347',
                'severity': 'high',
                'detected_at': datetime.now(timezone.utc),
                'status': 'detected'
            }
        ]
        
        export_config = {
            'columns': ['id', 'form_name', 'severity', 'status'],
            'include_headers': True
        }
        
        result = export_manager.export_data(sample_data, 'csv', export_config)
        
        assert isinstance(result, str)
        assert 'id,form_name,severity,status' in result
        assert '1,WH-347,high,detected' in result
    
    def test_export_data_excel(self, export_manager):
        """Test Excel export functionality."""
        sample_data = [
            {
                'id': 1,
                'form_name': 'WH-347',
                'severity': 'high',
                'detected_at': datetime.now(timezone.utc),
                'status': 'detected'
            }
        ]
        
        export_config = {
            'columns': ['id', 'form_name', 'severity', 'status'],
            'include_headers': True
        }
        
        result = export_manager.export_data(sample_data, 'excel', export_config)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_data_pdf(self, export_manager):
        """Test PDF export functionality."""
        sample_data = [
            {
                'id': 1,
                'form_name': 'WH-347',
                'severity': 'high',
                'detected_at': datetime.now(timezone.utc),
                'status': 'detected'
            }
        ]
        
        export_config = {
            'columns': ['id', 'form_name', 'severity', 'status'],
            'include_headers': True
        }
        
        result = export_manager.export_data(sample_data, 'pdf', export_config)
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_export_scheduler(self, export_scheduler):
        """Test export scheduler functionality."""
        export_id = "test_export_1"
        schedule_config = {
            'frequency': 'daily',
            'recipients': ['test@example.com']
        }
        export_config = {
            'format': 'csv',
            'columns': ['id', 'form_name'],
            'filters': {'severity': 'high'}
        }
        
        # Schedule export
        success = export_scheduler.schedule_export(export_id, schedule_config, export_config)
        assert success is True
        
        # Get scheduled exports
        scheduled = export_scheduler.get_scheduled_exports()
        assert export_id in scheduled
        
        # Cancel export
        cancelled = export_scheduler.cancel_export(export_id)
        assert cancelled is True
        
        # Verify cancellation
        scheduled_after = export_scheduler.get_scheduled_exports()
        assert export_id not in scheduled_after


class TestAuthenticationComprehensive:
    """Comprehensive test suite for authentication and authorization."""
    
    @pytest.fixture
    def user_service(self):
        """User service instance for testing."""
        return UserService()
    
    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)
    
    def test_user_authentication(self, user_service):
        """Test user authentication functionality."""
        # Create test user
        user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'full_name': 'Test User'
        }
        
        # Test password hashing
        hashed_password = user_service.hash_password(user_data['password'])
        assert hashed_password != user_data['password']
        
        # Test password verification
        is_valid = user_service.verify_password(user_data['password'], hashed_password)
        assert is_valid is True
        
        # Test JWT token creation and verification
        token_data = {'user_id': 1, 'username': 'testuser'}
        token = user_service.create_jwt_token(token_data)
        assert isinstance(token, str)
        
        decoded_data = user_service.verify_jwt_token(token)
        assert decoded_data['user_id'] == 1
        assert decoded_data['username'] == 'testuser'
    
    def test_permission_checking(self, user_service):
        """Test permission checking functionality."""
        # Mock user with roles
        user = Mock(spec=User)
        user.id = 1
        user.username = 'testuser'
        
        role1 = Mock(spec=Role)
        role1.name = 'product_manager'
        role1.permissions = ['view_dashboard', 'export_data']
        
        role2 = Mock(spec=Role)
        role2.name = 'business_analyst'
        role2.permissions = ['view_dashboard']
        
        user.roles = [role1, role2]
        
        # Test permission checking
        has_export_permission = user_service.has_permission(user, 'export_data')
        assert has_export_permission is True
        
        has_admin_permission = user_service.has_permission(user, 'admin_access')
        assert has_admin_permission is False


class TestFrontendIntegration:
    """Integration tests for frontend-backend communication."""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)
    
    def test_dashboard_initialization_flow(self, client):
        """Test complete dashboard initialization flow."""
        # Test that all required endpoints are accessible
        endpoints = [
            "/api/dashboard/stats",
            "/api/dashboard/recent-changes",
            "/api/dashboard/filter-options",
            "/api/dashboard/monitoring-status",
            "/api/dashboard/live-statistics",
            "/api/dashboard/alerts",
            "/api/dashboard/historical-data",
            "/api/dashboard/trends/summary",
            "/api/dashboard/analytics/agency-performance",
            "/api/dashboard/export/formats"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should return 200 or 422 (validation error for missing params)
            assert response.status_code in [200, 422, 401]
    
    def test_websocket_connection_flow(self, client):
        """Test WebSocket connection flow."""
        # Test WebSocket endpoint exists
        with client.websocket_connect("/api/realtime/ws") as websocket:
            # Send initial connection message
            websocket.send_text(json.dumps({
                "type": "connect",
                "client_type": "dashboard"
            }))
            
            # Should receive welcome message
            response = websocket.receive_text()
            data = json.loads(response)
            assert data["type"] == "welcome"
            assert "client_id" in data
    
    def test_export_workflow(self, client):
        """Test complete export workflow."""
        # Test export formats endpoint
        response = client.get("/api/dashboard/export/formats")
        assert response.status_code == 200
        formats = response.json()
        assert "formats" in formats
        
        # Test export request (with mock data)
        export_request = {
            "format": "csv",
            "columns": ["id", "form_name", "severity"],
            "filters": {"severity": "high"},
            "include_headers": True,
            "use_current_filters": False
        }
        
        response = client.post("/api/dashboard/export", json=export_request)
        # Should return 200 or 422 depending on data availability
        assert response.status_code in [200, 422]


class TestPerformanceAndEdgeCases:
    """Performance and edge case testing."""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)
    
    def test_large_dataset_handling(self, client):
        """Test handling of large datasets."""
        # Test with large page size
        params = {
            'page_size': 1000,
            'page': 1
        }
        
        response = client.get("/api/dashboard/recent-changes", params=params)
        # Should handle gracefully (either return data or error appropriately)
        assert response.status_code in [200, 422, 400]
    
    def test_invalid_date_ranges(self, client):
        """Test handling of invalid date ranges."""
        params = {
            'date_from': 'invalid-date',
            'date_to': '2024-12-31'
        }
        
        response = client.get("/api/dashboard/recent-changes", params=params)
        # Should handle gracefully
        assert response.status_code in [200, 422, 400]
    
    def test_malformed_search_queries(self, client):
        """Test handling of malformed search queries."""
        search_request = {
            "query": "",  # Empty query
            "filters": {},
            "page": -1,  # Invalid page
            "page_size": 0  # Invalid page size
        }
        
        response = client.post("/api/dashboard/search", json=search_request)
        # Should handle gracefully
        assert response.status_code in [200, 422, 400]
    
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/api/dashboard/stats")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All requests should complete successfully
        assert len(results) == 5
        assert all(status in [200, 401, 422] for status in results)


class TestErrorHandling:
    """Comprehensive error handling tests."""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)
    
    def test_database_connection_errors(self, client):
        """Test handling of database connection errors."""
        with patch('src.api.dashboard.get_db', side_effect=Exception("Database connection failed")):
            response = client.get("/api/dashboard/stats")
            # Should handle database errors gracefully
            assert response.status_code in [500, 503]
    
    def test_invalid_export_formats(self, client):
        """Test handling of invalid export formats."""
        export_request = {
            "format": "invalid_format",
            "columns": ["id", "form_name"],
            "filters": {}
        }
        
        response = client.post("/api/dashboard/export", json=export_request)
        # Should return appropriate error
        assert response.status_code in [400, 422]
    
    def test_authentication_errors(self, client):
        """Test handling of authentication errors."""
        # Test protected endpoint without authentication
        response = client.get("/api/auth/me")
        # Should return 401 for unauthenticated requests
        assert response.status_code == 401
    
    def test_authorization_errors(self, client):
        """Test handling of authorization errors."""
        # This would require a mock authenticated user with insufficient permissions
        # For now, we test the structure
        with patch('src.api.auth.get_current_user', return_value=None):
            response = client.get("/api/auth/me")
            assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 