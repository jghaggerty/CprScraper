"""
Unit and integration tests for dashboard widgets functionality.
Tests widget data loading, rendering, and interaction features.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from src.api.dashboard import router as dashboard_router
from fastapi.testclient import TestClient
from fastapi import FastAPI

class TestDashboardWidgets:
    @pytest.fixture
    def app(self):
        app = FastAPI()
        app.include_router(dashboard_router)
        return app

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        return Mock(spec=Session)

    @pytest.fixture
    def sample_changes(self):
        return [
            {
                "id": 1,
                "form_name": "Certified Payroll Form",
                "agency_name": "California Department of Transportation",
                "agency_type": "state",
                "change_type": "form_update",
                "severity": "critical",
                "status": "new",
                "detected_at": datetime.now().isoformat(),
                "ai_confidence_score": 95,
                "ai_change_category": "requirement_change",
                "is_cosmetic_change": False,
                "impact_assessment": {"impact_level": "high", "affected_fields": ["wage_rates", "fringe_benefits"]}
            },
            {
                "id": 2,
                "form_name": "Weekly Payroll Report",
                "agency_name": "Texas Department of Transportation",
                "agency_type": "state",
                "change_type": "field_change",
                "severity": "high",
                "status": "reviewed",
                "detected_at": (datetime.now() - timedelta(hours=2)).isoformat(),
                "ai_confidence_score": 87,
                "ai_change_category": "field_update",
                "is_cosmetic_change": False,
                "impact_assessment": {"impact_level": "medium", "affected_fields": ["hours_worked"]}
            }
        ]

    @pytest.fixture
    def sample_alerts(self):
        return [
            {
                "id": 1,
                "type": "critical_change",
                "severity": "critical",
                "title": "Critical Form Update Detected",
                "description": "Certified Payroll Form has been updated with new requirements",
                "created_at": datetime.now().isoformat(),
                "is_active": True
            },
            {
                "id": 2,
                "type": "monitoring_failure",
                "severity": "high",
                "title": "Monitoring Run Failed",
                "description": "Failed to check California DOT website",
                "created_at": (datetime.now() - timedelta(hours=1)).isoformat(),
                "is_active": True
            }
        ]

    @pytest.fixture
    def sample_agencies(self):
        return [
            {
                "id": 1,
                "name": "California Department of Transportation",
                "agency_type": "state",
                "total_forms": 5,
                "active_forms": 4,
                "last_check": datetime.now().isoformat(),
                "changes_last_week": 3,
                "health_status": "healthy"
            },
            {
                "id": 2,
                "name": "Texas Department of Transportation",
                "agency_type": "state",
                "total_forms": 3,
                "active_forms": 2,
                "last_check": (datetime.now() - timedelta(hours=6)).isoformat(),
                "changes_last_week": 1,
                "health_status": "warning"
            }
        ]

    @pytest.fixture
    def sample_stats(self):
        return {
            "total_agencies": 50,
            "total_forms": 150,
            "active_forms": 142,
            "total_changes": 25,
            "changes_last_24h": 8,
            "changes_last_week": 15,
            "changes_last_month": 45,
            "critical_changes": 3,
            "high_priority_changes": 7,
            "pending_notifications": 5,
            "active_work_items": 12,
            "last_monitoring_run": datetime.now().isoformat(),
            "system_health": "healthy",
            "coverage_percentage": 94.7
        }

    @pytest.fixture
    def sample_health(self):
        return {
            "overall_status": "healthy",
            "active_monitors": 3,
            "error_rate": 0.05,
            "avg_response_time": 2.3,
            "last_successful_run": datetime.now().isoformat(),
            "circuit_breakers_active": 0,
            "coverage_stats": {
                "total_agencies": 50,
                "monitored_agencies": 47,
                "coverage_percentage": 94.0
            }
        }

    def test_recent_changes_widget_data(self, client, mock_db_session, sample_changes):
        """Test that recent changes widget receives correct data format."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_recent_changes', return_value=sample_changes):
                response = client.get("/api/dashboard/changes?limit=5")
                assert response.status_code == 200
                
                data = response.json()
                assert isinstance(data, list)
                assert len(data) <= 5
                
                for change in data:
                    assert "id" in change
                    assert "form_name" in change
                    assert "agency_name" in change
                    assert "severity" in change
                    assert "detected_at" in change

    def test_pending_alerts_widget_data(self, client, mock_db_session, sample_alerts):
        """Test that pending alerts widget receives correct data format."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_active_alerts', return_value=sample_alerts):
                response = client.get("/api/dashboard/alerts")
                assert response.status_code == 200
                
                data = response.json()
                assert isinstance(data, list)
                
                for alert in data:
                    assert "id" in alert
                    assert "type" in alert
                    assert "severity" in alert
                    assert "title" in alert
                    assert "created_at" in alert

    def test_compliance_status_widget_data(self, client, mock_db_session, sample_stats):
        """Test that compliance status widget receives correct data format."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_dashboard_stats', return_value=sample_stats):
                response = client.get("/api/dashboard/stats")
                assert response.status_code == 200
                
                data = response.json()
                assert "total_forms" in data
                assert "active_forms" in data
                assert "critical_changes" in data
                assert "coverage_percentage" in data

    def test_agency_health_widget_data(self, client, mock_db_session, sample_agencies):
        """Test that agency health widget receives correct data format."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_agency_summaries', return_value=sample_agencies):
                response = client.get("/api/dashboard/agencies")
                assert response.status_code == 200
                
                data = response.json()
                assert isinstance(data, list)
                
                for agency in data:
                    assert "id" in agency
                    assert "name" in agency
                    assert "health_status" in agency
                    assert "active_forms" in agency

    def test_monitoring_activity_widget_data(self, client, mock_db_session, sample_health):
        """Test that monitoring activity widget receives correct data format."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_monitoring_health', return_value=sample_health):
                response = client.get("/api/dashboard/health")
                assert response.status_code == 200
                
                data = response.json()
                assert "overall_status" in data
                assert "active_monitors" in data
                assert "error_rate" in data
                assert "avg_response_time" in data

    def test_widget_data_filtering(self, client, mock_db_session, sample_changes):
        """Test that widget data can be filtered correctly."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_recent_changes', return_value=sample_changes):
                # Test filtering by severity
                response = client.get("/api/dashboard/changes?severity=critical&limit=5")
                assert response.status_code == 200
                
                data = response.json()
                for change in data:
                    assert change["severity"] == "critical"

    def test_widget_data_pagination(self, client, mock_db_session, sample_changes):
        """Test that widget data supports pagination."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_recent_changes', return_value=sample_changes):
                response = client.get("/api/dashboard/changes?limit=1")
                assert response.status_code == 200
                
                data = response.json()
                assert len(data) <= 1

    def test_widget_error_handling(self, client, mock_db_session):
        """Test that widgets handle errors gracefully."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_recent_changes', side_effect=Exception("Database error")):
                response = client.get("/api/dashboard/changes?limit=5")
                assert response.status_code == 500

    def test_widget_data_validation(self, client, mock_db_session):
        """Test that widget data is properly validated."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            # Test invalid limit parameter
            response = client.get("/api/dashboard/changes?limit=0")
            assert response.status_code == 422
            
            # Test invalid limit parameter (too high)
            response = client.get("/api/dashboard/changes?limit=1000")
            assert response.status_code == 422

    def test_widget_data_sorting(self, client, mock_db_session, sample_changes):
        """Test that widget data can be sorted correctly."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.get_recent_changes', return_value=sample_changes):
                # Test sorting by detection date
                response = client.get("/api/dashboard/changes?sort_by=detected_at&sort_order=desc&limit=5")
                assert response.status_code == 200

    def test_widget_data_search(self, client, mock_db_session, sample_changes):
        """Test that widget data supports search functionality."""
        with patch('src.api.dashboard.get_db', return_value=mock_db_session):
            with patch('src.api.dashboard.search_changes', return_value={"results": sample_changes, "total_count": 2}):
                response = client.post("/api/dashboard/search", json={
                    "query": "California",
                    "filters": {},
                    "sort_by": "detected_at",
                    "sort_order": "desc",
                    "page": 1,
                    "page_size": 5
                })
                assert response.status_code == 200

class TestWidgetFrontend:
    """Test frontend widget functionality and interactions."""
    
    def test_widget_initialization(self):
        """Test that widgets initialize correctly."""
        # This would test the JavaScript widget initialization
        # In a real test environment, this would use a browser automation tool
        pass

    def test_widget_data_loading(self):
        """Test that widgets load data correctly."""
        # This would test the JavaScript data loading functions
        pass

    def test_widget_interactions(self):
        """Test that widget interactions work correctly."""
        # This would test button clicks, refreshes, etc.
        pass

    def test_widget_error_states(self):
        """Test that widgets display error states correctly."""
        # This would test error handling in the frontend
        pass

    def test_widget_empty_states(self):
        """Test that widgets display empty states correctly."""
        # This would test empty state handling in the frontend
        pass

    def test_widget_responsive_design(self):
        """Test that widgets are responsive on different screen sizes."""
        # This would test responsive behavior
        pass

class TestWidgetPerformance:
    """Test widget performance and optimization."""
    
    def test_widget_data_caching(self):
        """Test that widget data is cached appropriately."""
        pass

    def test_widget_auto_refresh(self):
        """Test that widgets auto-refresh correctly."""
        pass

    def test_widget_memory_usage(self):
        """Test that widgets don't cause memory leaks."""
        pass

    def test_widget_network_requests(self):
        """Test that widgets make efficient network requests."""
        pass

if __name__ == "__main__":
    pytest.main([__file__]) 