"""
Unit tests for Enhanced Dashboard API

Tests the comprehensive dashboard API endpoints for compliance monitoring data,
including filtering, search, real-time status, and statistics.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.dashboard import (
    router, DashboardStats, ChangeSummary, AgencySummary, FormSummary,
    MonitoringHealth, FilterOptions, SearchRequest, SearchResponse
)
from src.database.models import Agency, Form, FormChange, MonitoringRun, Notification, WorkItem
from src.api.main import app


class TestDashboardAPI:
    """Test suite for Dashboard API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Test client for API testing."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session for testing."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_agency(self):
        """Sample agency for testing."""
        agency = Mock(spec=Agency)
        agency.id = 1
        agency.name = "Test Department of Labor"
        agency.agency_type = "federal"
        agency.is_active = True
        agency.forms = []
        return agency
    
    @pytest.fixture
    def sample_form(self, sample_agency):
        """Sample form for testing."""
        form = Mock(spec=Form)
        form.id = 1
        form.name = "WH-347"
        form.title = "Statement of Compliance"
        form.is_active = True
        form.last_checked = datetime.now(timezone.utc) - timedelta(hours=1)
        form.check_frequency = "weekly"
        form.agency = sample_agency
        return form
    
    @pytest.fixture
    def sample_form_change(self, sample_form):
        """Sample form change for testing."""
        change = Mock(spec=FormChange)
        change.id = 1
        change.form = sample_form
        change.change_type = "content"
        change.severity = "high"
        change.status = "detected"
        change.detected_at = datetime.now(timezone.utc) - timedelta(hours=2)
        change.ai_confidence_score = 85
        change.ai_change_category = "form_update"
        change.is_cosmetic_change = False
        change.impact_assessment = {"impact_level": "high"}
        return change
    
    @pytest.fixture
    def sample_monitoring_run(self):
        """Sample monitoring run for testing."""
        run = Mock(spec=MonitoringRun)
        run.id = 1
        run.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        run.completed_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        run.status = "completed"
        run.response_time_ms = 1500
        return run
    
    def test_get_dashboard_stats_success(self, mock_db_session, sample_agency, sample_form):
        """Test successful retrieval of dashboard statistics."""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [
            5,  # total_agencies
            25,  # total_forms
            20,  # active_forms
            3,   # changes_last_24h
            15,  # changes_last_week
            45,  # changes_last_month
            60,  # total_changes
            2,   # critical_changes
            8,   # high_priority_changes
            5,   # pending_notifications
            12   # active_work_items
        ]
        
        # Mock last monitoring run
        mock_last_run = Mock()
        mock_last_run.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_db_session.query.return_value.order_by.return_value.first.return_value = mock_last_run
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/stats")(mock_db_session)
            
            # Verify response
            assert response.total_agencies == 5
            assert response.total_forms == 25
            assert response.active_forms == 20
            assert response.changes_last_24h == 3
            assert response.changes_last_week == 15
            assert response.changes_last_month == 45
            assert response.total_changes == 60
            assert response.critical_changes == 2
            assert response.high_priority_changes == 8
            assert response.pending_notifications == 5
            assert response.active_work_items == 12
            assert response.system_health == "healthy"
            assert response.coverage_percentage == 80.0
    
    def test_get_dashboard_stats_error(self, mock_db_session):
        """Test dashboard stats endpoint with database error."""
        mock_db_session.query.side_effect = Exception("Database error")
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with pytest.raises(Exception):
                router.get("/stats")(mock_db_session)
    
    def test_get_recent_changes_success(self, mock_db_session, sample_form_change):
        """Test successful retrieval of recent changes."""
        # Setup mocks
        mock_db_session.query.return_value.options.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_form_change]
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/changes")(mock_db_session)
            
            # Verify response
            assert len(response) == 1
            change = response[0]
            assert change.id == 1
            assert change.form_name == "WH-347"
            assert change.agency_name == "Test Department of Labor"
            assert change.severity == "high"
            assert change.ai_confidence_score == 85
    
    def test_get_recent_changes_with_filters(self, mock_db_session, sample_form_change):
        """Test recent changes endpoint with filtering options."""
        # Setup mocks
        mock_query = Mock()
        mock_db_session.query.return_value.options.return_value = mock_query
        mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sample_form_change]
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test with filters
            response = router.get("/changes")(
                db=mock_db_session,
                agency_id=1,
                severity="high",
                status="detected",
                days=7
            )
            
            # Verify filters were applied
            assert len(response) == 1
    
    def test_get_agency_summaries_success(self, mock_db_session, sample_agency, sample_form):
        """Test successful retrieval of agency summaries."""
        # Setup mocks
        sample_agency.forms = [sample_form]
        mock_db_session.query.return_value.filter.return_value.all.return_value = [sample_agency]
        
        # Mock change count query
        mock_db_session.query.return_value.join.return_value.filter.return_value.count.return_value = 3
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/agencies")(mock_db_session)
            
            # Verify response
            assert len(response) == 1
            agency = response[0]
            assert agency.id == 1
            assert agency.name == "Test Department of Labor"
            assert agency.agency_type == "federal"
            assert agency.total_forms == 1
            assert agency.active_forms == 1
            assert agency.changes_last_week == 3
            assert agency.health_status == "healthy"
    
    def test_get_form_summaries_success(self, mock_db_session, sample_form):
        """Test successful retrieval of form summaries."""
        # Setup mocks
        mock_db_session.query.return_value.options.return_value.filter.return_value.all.return_value = [sample_form]
        
        # Mock change count query
        mock_db_session.query.return_value.filter.return_value.count.return_value = 5
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/forms")(mock_db_session)
            
            # Verify response
            assert len(response) == 1
            form = response[0]
            assert form.id == 1
            assert form.name == "WH-347"
            assert form.title == "Statement of Compliance"
            assert form.agency_name == "Test Department of Labor"
            assert form.total_changes == 5
            assert form.status == "active"
    
    def test_get_monitoring_health_success(self, mock_db_session, sample_monitoring_run):
        """Test successful retrieval of monitoring health status."""
        # Setup mocks
        mock_db_session.query.return_value.count.side_effect = [100, 90]  # total_runs, successful_runs
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [90, 25, 20]  # successful_runs, total_forms, checked_forms
        mock_db_session.query.return_value.order_by.return_value.first.return_value = sample_monitoring_run
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = sample_monitoring_run
        
        # Mock average response time
        mock_db_session.query.return_value.filter.return_value.scalar.return_value = 1500.0
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/health")(mock_db_session)
            
            # Verify response
            assert response.overall_status == "healthy"
            assert response.active_monitors == 25
            assert response.error_rate == 0.1
            assert response.avg_response_time == 1500.0
            assert response.circuit_breakers_active == 0
            assert "coverage_percentage" in response.coverage_stats
    
    def test_get_filter_options_success(self, mock_db_session):
        """Test successful retrieval of filter options."""
        # Setup mocks
        mock_db_session.query.return_value.distinct.return_value.all.side_effect = [
            [("federal",), ("state",)],  # states
            [("Test Agency 1",), ("Test Agency 2",)],  # agencies
            [("WH-347",), ("A1-131",)],  # form_types
            [("critical",), ("high",), ("medium",)],  # severity_levels
            [("detected",), ("notified",), ("evaluated",)]  # status_options
        ]
        mock_db_session.query.return_value.filter.return_value.all.return_value = [("Test Agency 1",), ("Test Agency 2",)]
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/filters")(mock_db_session)
            
            # Verify response
            assert "federal" in response.states
            assert "state" in response.states
            assert "Test Agency 1" in response.agencies
            assert "WH-347" in response.form_types
            assert "critical" in response.severity_levels
            assert "detected" in response.status_options
            assert "24h" in response.date_ranges
            assert "7d" in response.date_ranges
    
    def test_search_changes_success(self, mock_db_session, sample_form_change):
        """Test successful search of form changes."""
        # Setup mocks
        mock_query = Mock()
        mock_db_session.query.return_value.options.return_value = mock_query
        mock_query.filter.return_value.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [sample_form_change]
        
        search_request = SearchRequest(
            query="WH-347",
            filters={"severity": "high"},
            sort_by="detected_at",
            sort_order="desc",
            page=1,
            page_size=10
        )
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.post("/search")(search_request, mock_db_session)
            
            # Verify response
            assert response.total_count == 1
            assert response.page == 1
            assert response.page_size == 10
            assert response.total_pages == 1
            assert len(response.results) == 1
            assert response.results[0].form_name == "WH-347"
    
    def test_search_changes_with_pagination(self, mock_db_session, sample_form_change):
        """Test search changes with pagination."""
        # Setup mocks for pagination
        mock_query = Mock()
        mock_db_session.query.return_value.options.return_value = mock_query
        mock_query.filter.return_value.count.return_value = 25
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [sample_form_change]
        
        search_request = SearchRequest(
            query="",
            page=2,
            page_size=10
        )
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.post("/search")(search_request, mock_db_session)
            
            # Verify pagination
            assert response.total_count == 25
            assert response.page == 2
            assert response.page_size == 10
            assert response.total_pages == 3  # ceil(25/10)
    
    def test_get_active_alerts_success(self, mock_db_session):
        """Test successful retrieval of active alerts."""
        # Setup mocks
        mock_db_session.query.return_value.filter.return_value.count.side_effect = [
            2,  # critical_changes
            5,  # pending_notifications
            3,  # stale_forms
            1   # failed_runs
        ]
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/alerts")(mock_db_session)
            
            # Verify response
            assert response["total_alerts"] == 4
            assert len(response["alerts"]) == 4
            
            # Check alert types
            alert_types = [alert["type"] for alert in response["alerts"]]
            assert "critical" in alert_types
            assert "warning" in alert_types
            assert "error" in alert_types
    
    def test_get_active_alerts_no_alerts(self, mock_db_session):
        """Test alerts endpoint when no alerts are present."""
        # Setup mocks - no alerts
        mock_db_session.query.return_value.filter.return_value.count.return_value = 0
        
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test the endpoint
            response = router.get("/alerts")(mock_db_session)
            
            # Verify response
            assert response["total_alerts"] == 0
            assert len(response["alerts"]) == 0
    
    def test_calculate_error_rate_success(self, mock_db_session):
        """Test error rate calculation helper function."""
        from src.api.dashboard import _calculate_error_rate
        
        # Setup mocks
        mock_db_session.query.return_value.count.side_effect = [100, 10]  # total_runs, failed_runs
        
        # Test calculation
        error_rate = _calculate_error_rate(mock_db_session)
        assert error_rate == 0.1  # 10 failed out of 100 total
    
    def test_calculate_error_rate_zero_runs(self, mock_db_session):
        """Test error rate calculation with zero runs."""
        from src.api.dashboard import _calculate_error_rate
        
        # Setup mocks
        mock_db_session.query.return_value.count.return_value = 0
        
        # Test calculation
        error_rate = _calculate_error_rate(mock_db_session)
        assert error_rate == 0.0
    
    def test_parse_date_range_success(self):
        """Test date range parsing helper function."""
        from src.api.dashboard import _parse_date_range
        
        # Test valid date ranges
        assert _parse_date_range("24h") == 1
        assert _parse_date_range("7d") == 7
        assert _parse_date_range("30d") == 30
        assert _parse_date_range("90d") == 90
        assert _parse_date_range("1y") == 365
    
    def test_parse_date_range_invalid(self):
        """Test date range parsing with invalid input."""
        from src.api.dashboard import _parse_date_range
        
        # Test invalid date ranges
        assert _parse_date_range("invalid") is None
        assert _parse_date_range("") is None
        assert _parse_date_range("2d") is None


class TestDashboardAPIIntegration:
    """Integration tests for Dashboard API with real client."""
    
    @pytest.fixture
    def client(self):
        """Test client for integration testing."""
        return TestClient(app)
    
    def test_dashboard_stats_endpoint_integration(self, client):
        """Test dashboard stats endpoint integration."""
        with patch('src.api.dashboard.get_db') as mock_get_db:
            # Setup mock database session
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.count.side_effect = [
                5, 25, 20, 3, 15, 45, 60, 2, 8, 5, 12
            ]
            mock_last_run = Mock()
            mock_last_run.started_at = datetime.now(timezone.utc) - timedelta(hours=1)
            mock_db.query.return_value.order_by.return_value.first.return_value = mock_last_run
            mock_get_db.return_value = mock_db
            
            # Make request
            response = client.get("/api/dashboard/stats")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["total_agencies"] == 5
            assert data["total_forms"] == 25
            assert data["system_health"] == "healthy"
    
    def test_recent_changes_endpoint_integration(self, client):
        """Test recent changes endpoint integration."""
        with patch('src.api.dashboard.get_db') as mock_get_db:
            # Setup mock database session
            mock_db = Mock()
            mock_query = Mock()
            mock_db.query.return_value.options.return_value = mock_query
            mock_query.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Make request
            response = client.get("/api/dashboard/changes?limit=10")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
    
    def test_search_changes_endpoint_integration(self, client):
        """Test search changes endpoint integration."""
        with patch('src.api.dashboard.get_db') as mock_get_db:
            # Setup mock database session
            mock_db = Mock()
            mock_query = Mock()
            mock_db.query.return_value.options.return_value = mock_query
            mock_query.filter.return_value.count.return_value = 0
            mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            # Make request
            search_data = {
                "query": "test",
                "filters": {"severity": "high"},
                "page": 1,
                "page_size": 10
            }
            response = client.post("/api/dashboard/search", json=search_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["total_count"] == 0
            assert data["page"] == 1
            assert data["page_size"] == 10
    
    def test_filter_options_endpoint_integration(self, client):
        """Test filter options endpoint integration."""
        with patch('src.api.dashboard.get_db') as mock_get_db:
            # Setup mock database session
            mock_db = Mock()
            mock_db.query.return_value.distinct.return_value.all.side_effect = [
                [("federal",)], [("Test Agency",)], [("WH-347",)], [("high",)], [("detected",)]
            ]
            mock_db.query.return_value.filter.return_value.all.return_value = [("Test Agency",)]
            mock_get_db.return_value = mock_db
            
            # Make request
            response = client.get("/api/dashboard/filters")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "states" in data
            assert "agencies" in data
            assert "form_types" in data
            assert "severity_levels" in data
            assert "status_options" in data
            assert "date_ranges" in data


if __name__ == "__main__":
    pytest.main([__file__]) 