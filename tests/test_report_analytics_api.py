"""
Unit tests for Report Analytics API

This module contains comprehensive tests for the report analytics and trend identification
API endpoints, including tests for analytics generation, trend analysis, predictions,
anomaly detection, and system health scoring.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from src.api.report_analytics import router
from src.reporting.report_analytics import (
    ReportAnalytics, TrendDirection, AnalyticsPeriod,
    get_analytics
)
from src.database.models import User, Role, UserRole
from src.auth.auth import get_current_user

# Test data
SAMPLE_ANALYTICS_REQUEST = {
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-01-31T23:59:59",
    "agencies": [1, 2],
    "form_types": ["WH-347", "A1-131"],
    "include_predictions": True,
    "include_anomalies": True,
    "include_correlations": True
}

SAMPLE_QUICK_ANALYTICS_REQUEST = {
    "period_days": 30,
    "agencies": [1, 2],
    "form_types": ["WH-347"]
}

SAMPLE_TREND_COMPARISON_REQUEST = {
    "period1_start": "2024-01-01T00:00:00",
    "period1_end": "2024-01-15T23:59:59",
    "period2_start": "2024-01-16T00:00:00",
    "period2_end": "2024-01-31T23:59:59",
    "agencies": [1],
    "form_types": ["WH-347"]
}

SAMPLE_ANALYTICS_RESPONSE = {
    "period": {
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-31T23:59:59",
        "duration_days": 30
    },
    "summary": {
        "total_changes": 45,
        "monitoring_success_rate": 95.5,
        "average_impact_score": 6.2,
        "system_health_score": 78,
        "key_metrics": {
            "changes_per_day": 1.5,
            "critical_changes": 3,
            "uptime_percentage": 99.2
        }
    },
    "change_analytics": {
        "total_changes": 45,
        "avg_changes_per_day": 1.5,
        "change_frequency": "moderate",
        "severity_distribution": {"critical": 3, "high": 8, "medium": 20, "low": 14},
        "type_distribution": {"content": 25, "url": 10, "metadata": 10},
        "agency_breakdown": {"DOL": 20, "DOT": 15, "EPA": 10},
        "form_breakdown": {"WH-347": 30, "A1-131": 15},
        "temporal_patterns": {
            "day_of_week_distribution": {"Monday": 10, "Tuesday": 8, "Wednesday": 12},
            "hour_of_day_distribution": {"9": 15, "10": 12, "11": 8},
            "month_distribution": {"January": 45}
        }
    },
    "performance_analytics": {
        "total_runs": 120,
        "successful_runs": 115,
        "failed_runs": 5,
        "success_rate": 95.8,
        "avg_response_time": 1250.5,
        "performance_trend": "stable",
        "error_analysis": {"timeout": 3, "connection_error": 2},
        "uptime_metrics": {
            "uptime_percentage": 99.2,
            "total_duration_hours": 720.0,
            "successful_duration_hours": 714.2
        }
    },
    "impact_analytics": {
        "total_impacted_changes": 35,
        "avg_impact_score": 6.2,
        "impact_distribution": {"high": 8, "medium": 15, "low": 12},
        "client_impact_trends": {},
        "development_impact_trends": {}
    },
    "trend_analysis": {
        "trend_direction": "increasing",
        "trend_strength": 0.75,
        "trend_percentage": 15.5,
        "seasonality_detected": False,
        "volatility_score": 0.45,
        "trend_breakdown": {},
        "daily_data": {"2024-01-01": 2, "2024-01-02": 1, "2024-01-03": 3}
    },
    "pattern_analysis": {
        "temporal_patterns": {},
        "correlation_patterns": {},
        "sequential_patterns": {},
        "outlier_patterns": {}
    },
    "predictions": {
        "prediction_confidence": "medium",
        "predicted_changes_next_week": 10.5,
        "predicted_changes_next_month": 45.0,
        "prediction_factors": ["Recent trend increase", "Seasonal patterns"],
        "confidence_intervals": {
            "next_week": {"lower": 7.4, "upper": 13.7},
            "next_month": {"lower": 31.5, "upper": 58.5}
        }
    },
    "anomalies": {
        "anomalies_detected": 2,
        "anomaly_dates": ["2024-01-15", "2024-01-22"],
        "anomaly_details": [
            {
                "date": "2024-01-15",
                "value": 8,
                "z_score": 2.5,
                "expected_range": "1.0 - 4.0"
            }
        ],
        "anomaly_types": {"spike": 2},
        "anomaly_severity": {"high": 2}
    },
    "correlations": {
        "correlation_matrix": {},
        "strong_correlations": [],
        "correlation_insights": []
    },
    "insights": [
        "High change frequency detected - consider increasing monitoring resources",
        "Monitoring success rate (95.5%) below target - investigate failures"
    ],
    "recommendations": [
        "Implement automated change classification to prioritize critical changes",
        "Review monitoring error logs and implement retry mechanisms"
    ],
    "metadata": {
        "generated_at": "2024-01-31T12:00:00",
        "data_points_analyzed": 45,
        "agencies_analyzed": 3,
        "forms_analyzed": 2
    }
}


class TestReportAnalyticsAPI:
    """Test cases for Report Analytics API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create FastAPI test client."""
        from fastapi.testclient import TestClient
        return TestClient(router)
    
    @pytest.fixture
    def mock_user(self):
        """Mock standard user."""
        user = Mock(spec=User)
        user.id = 1
        user.username = "testuser"
        user.email = "test@example.com"
        user.is_active = True
        return user
    
    @pytest.fixture
    def mock_admin_user(self):
        """Mock admin user."""
        user = Mock(spec=User)
        user.id = 2
        user.username = "admin"
        user.email = "admin@example.com"
        user.is_active = True
        user.is_superuser = True
        return user
    
    @pytest.fixture
    def mock_analytics(self):
        """Mock analytics service."""
        analytics = Mock(spec=ReportAnalytics)
        analytics.generate_comprehensive_analytics.return_value = SAMPLE_ANALYTICS_RESPONSE
        return analytics
    
    def test_generate_comprehensive_analytics_success(self, client, mock_user, mock_analytics):
        """Test successful comprehensive analytics generation."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.post("/comprehensive", json=SAMPLE_ANALYTICS_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "period" in data
            assert "summary" in data
            assert "change_analytics" in data
            assert "performance_analytics" in data
            assert "trend_analysis" in data
            assert "insights" in data
            assert "recommendations" in data
            
            # Verify analytics service was called correctly
            mock_analytics.generate_comprehensive_analytics.assert_called_once()
            call_args = mock_analytics.generate_comprehensive_analytics.call_args[1]
            assert call_args["include_predictions"] is True
            assert call_args["include_anomalies"] is True
            assert call_args["include_correlations"] is True
    
    def test_generate_comprehensive_analytics_invalid_data(self, client, mock_user):
        """Test comprehensive analytics with invalid data."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user):
            invalid_request = {
                "start_date": "invalid-date",
                "end_date": "invalid-date"
            }
            
            response = client.post("/comprehensive", json=invalid_request)
            
            assert response.status_code == 422  # Validation error
    
    def test_generate_quick_analytics_success(self, client, mock_user, mock_analytics):
        """Test successful quick analytics generation."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.post("/quick", json=SAMPLE_QUICK_ANALYTICS_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "period" in data
            assert "summary" in data
            assert "trend_direction" in data
            assert "key_insights" in data
            assert "recommendations" in data
            
            # Verify analytics service was called correctly
            mock_analytics.generate_comprehensive_analytics.assert_called_once()
            call_args = mock_analytics.generate_comprehensive_analytics.call_args[1]
            assert call_args["include_predictions"] is False
            assert call_args["include_anomalies"] is False
            assert call_args["include_correlations"] is False
    
    def test_compare_trends_success(self, client, mock_user, mock_analytics):
        """Test successful trend comparison."""
        comparison_response = {
            "period1": {"start_date": "2024-01-01", "end_date": "2024-01-15"},
            "period2": {"start_date": "2024-01-16", "end_date": "2024-01-31"},
            "comparison": {
                "total_changes_change": 5,
                "success_rate_change": 2.5,
                "impact_score_change": -0.5,
                "health_score_change": 3
            },
            "changes": {
                "frequency_change": False,
                "severity_distribution_change": {},
                "agency_distribution_change": {}
            },
            "insights": [
                "Significant improvement in system health score",
                "Monitoring success rate improved significantly"
            ]
        }
        
        mock_analytics.generate_comprehensive_analytics.side_effect = [
            SAMPLE_ANALYTICS_RESPONSE,  # First period
            SAMPLE_ANALYTICS_RESPONSE   # Second period
        ]
        
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics), \
             patch('src.api.report_analytics._calculate_period_comparison', return_value=comparison_response["comparison"]), \
             patch('src.api.report_analytics._calculate_changes_between_periods', return_value=comparison_response["changes"]), \
             patch('src.api.report_analytics._generate_comparison_insights', return_value=comparison_response["insights"]):
            
            response = client.post("/trend-comparison", json=SAMPLE_TREND_COMPARISON_REQUEST)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "period1" in data
            assert "period2" in data
            assert "comparison" in data
            assert "changes" in data
            assert "insights" in data
            
            # Verify analytics service was called twice (once for each period)
            assert mock_analytics.generate_comprehensive_analytics.call_count == 2
    
    def test_get_trends_by_period_success(self, client, mock_user, mock_analytics):
        """Test successful trend analysis by period."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/trends/monthly?agencies=1,2&form_types=WH-347")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "period" in data
            assert "trend_analysis" in data
            assert "change_analytics" in data
            assert "summary" in data
    
    def test_get_predictions_success(self, client, mock_user, mock_analytics):
        """Test successful predictions generation."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/predictions?days_ahead=30&agencies=1,2")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "prediction_confidence" in data
            assert "predicted_changes_next_week" in data
            assert "predicted_changes_next_month" in data
            assert "prediction_factors" in data
            assert "confidence_intervals" in data
    
    def test_get_anomalies_success(self, client, mock_user, mock_analytics):
        """Test successful anomaly detection."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/anomalies?agencies=1,2&form_types=WH-347")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "anomalies_detected" in data
            assert "anomaly_dates" in data
            assert "anomaly_details" in data
            assert "anomaly_types" in data
            assert "anomaly_severity" in data
    
    def test_get_correlations_success(self, client, mock_user, mock_analytics):
        """Test successful correlation analysis."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/correlations?agencies=1,2")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "correlation_matrix" in data
            assert "strong_correlations" in data
            assert "correlation_insights" in data
    
    def test_get_analytics_summary_success(self, client, mock_user, mock_analytics):
        """Test successful analytics summary generation."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/summary?days=30&agencies=1,2")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "total_changes" in data
            assert "monitoring_success_rate" in data
            assert "average_impact_score" in data
            assert "system_health_score" in data
            assert "key_metrics" in data
    
    def test_get_analytics_insights_success(self, client, mock_user, mock_analytics):
        """Test successful insights generation."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/insights?days=30")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response is a list of insights
            assert isinstance(data, list)
            assert len(data) > 0
    
    def test_get_analytics_recommendations_success(self, client, mock_user, mock_analytics):
        """Test successful recommendations generation."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.get("/recommendations?days=30")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response is a list of recommendations
            assert isinstance(data, list)
            assert len(data) > 0
    
    def test_get_system_health_score_success(self, client, mock_user, mock_analytics):
        """Test successful system health score generation."""
        health_response = {
            "overall_score": 78,
            "performance_score": 30,
            "change_management_score": 25,
            "impact_management_score": 23,
            "recommendations": [
                "Review monitoring error logs and implement retry mechanisms",
                "Implement automated change classification to prioritize critical changes"
            ]
        }
        
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics), \
             patch('src.api.report_analytics._calculate_performance_score', return_value=30), \
             patch('src.api.report_analytics._calculate_change_management_score', return_value=25), \
             patch('src.api.report_analytics._calculate_impact_management_score', return_value=23):
            
            response = client.get("/health-score?days=30")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "overall_score" in data
            assert "performance_score" in data
            assert "change_management_score" in data
            assert "impact_management_score" in data
            assert "recommendations" in data
    
    def test_analytics_service_error_handling(self, client, mock_user, mock_analytics):
        """Test error handling when analytics service fails."""
        mock_analytics.generate_comprehensive_analytics.side_effect = Exception("Analytics service error")
        
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user), \
             patch('src.api.report_analytics.get_analytics', return_value=mock_analytics):
            
            response = client.post("/comprehensive", json=SAMPLE_ANALYTICS_REQUEST)
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to generate analytics" in data["detail"]
    
    def test_invalid_period_parameter(self, client, mock_user):
        """Test invalid period parameter handling."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user):
            response = client.get("/trends/invalid-period")
            
            assert response.status_code == 422  # Validation error
    
    def test_invalid_days_parameter(self, client, mock_user):
        """Test invalid days parameter handling."""
        with patch('src.api.report_analytics.get_current_user', return_value=mock_user):
            response = client.get("/summary?days=1000")  # Too many days
            
            assert response.status_code == 422  # Validation error
    
    def test_missing_authentication(self, client):
        """Test authentication requirement."""
        response = client.post("/comprehensive", json=SAMPLE_ANALYTICS_REQUEST)
        
        assert response.status_code == 401  # Unauthorized


class TestReportAnalyticsService:
    """Test cases for ReportAnalytics service class."""
    
    @pytest.fixture
    def analytics(self):
        """Create analytics service instance."""
        return ReportAnalytics()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()
    
    def test_init_analytics_service(self, analytics):
        """Test analytics service initialization."""
        assert analytics.min_data_points == 3
    
    def test_generate_comprehensive_analytics_default_period(self, analytics, mock_db):
        """Test comprehensive analytics with default period."""
        with patch('src.reporting.report_analytics.get_db', return_value=mock_db), \
             patch.object(analytics, '_analyze_change_patterns', return_value={}), \
             patch.object(analytics, '_analyze_performance_metrics', return_value={}), \
             patch.object(analytics, '_analyze_impact_trends', return_value={}), \
             patch.object(analytics, '_perform_trend_analysis', return_value={}), \
             patch.object(analytics, '_identify_patterns', return_value={}), \
             patch.object(analytics, '_generate_predictions', return_value={}), \
             patch.object(analytics, '_detect_anomalies', return_value={}), \
             patch.object(analytics, '_analyze_correlations', return_value={}), \
             patch.object(analytics, '_generate_insights', return_value=[]), \
             patch.object(analytics, '_generate_recommendations', return_value=[]), \
             patch.object(analytics, '_generate_executive_summary', return_value={}):
            
            result = analytics.generate_comprehensive_analytics()
            
            assert "period" in result
            assert "summary" in result
            assert "change_analytics" in result
            assert "performance_analytics" in result
            assert "trend_analysis" in result
            assert "pattern_analysis" in result
            assert "predictions" in result
            assert "anomalies" in result
            assert "correlations" in result
            assert "insights" in result
            assert "recommendations" in result
            assert "metadata" in result
    
    def test_analyze_change_patterns_empty_data(self, analytics, mock_db):
        """Test change pattern analysis with empty data."""
        with patch('src.reporting.report_analytics.get_db', return_value=mock_db):
            mock_db.query.return_value.filter.return_value.join.return_value.filter.return_value.all.return_value = []
            
            result = analytics._analyze_change_patterns(
                mock_db, 
                datetime(2024, 1, 1), 
                datetime(2024, 1, 31)
            )
            
            assert result["total_changes"] == 0
            assert result["avg_changes_per_day"] == 0
            assert result["change_frequency"] == "none"
    
    def test_analyze_performance_metrics_empty_data(self, analytics, mock_db):
        """Test performance metrics analysis with empty data."""
        with patch('src.reporting.report_analytics.get_db', return_value=mock_db):
            mock_db.query.return_value.filter.return_value.all.return_value = []
            
            result = analytics._analyze_performance_metrics(
                mock_db, 
                datetime(2024, 1, 1), 
                datetime(2024, 1, 31)
            )
            
            assert result["total_runs"] == 0
            assert result["success_rate"] == 0
            assert result["avg_response_time"] == 0
    
    def test_calculate_linear_trend_increasing(self, analytics):
        """Test linear trend calculation for increasing trend."""
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        values = [1, 2, 3]
        
        direction, strength, percentage = analytics._calculate_linear_trend(dates, values)
        
        assert direction == TrendDirection.INCREASING
        assert strength > 0
        assert percentage > 0
    
    def test_calculate_linear_trend_decreasing(self, analytics):
        """Test linear trend calculation for decreasing trend."""
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        values = [3, 2, 1]
        
        direction, strength, percentage = analytics._calculate_linear_trend(dates, values)
        
        assert direction == TrendDirection.DECREASING
        assert strength > 0
        assert percentage < 0
    
    def test_calculate_linear_trend_stable(self, analytics):
        """Test linear trend calculation for stable trend."""
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        values = [2, 2, 2]
        
        direction, strength, percentage = analytics._calculate_linear_trend(dates, values)
        
        assert direction == TrendDirection.STABLE
        assert strength == 0
        assert percentage == 0
    
    def test_detect_seasonality_with_pattern(self, analytics):
        """Test seasonality detection with weekly pattern."""
        values = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2]  # Weekly pattern
        
        result = analytics._detect_seasonality(values)
        
        assert result is True
    
    def test_detect_seasonality_no_pattern(self, analytics):
        """Test seasonality detection without pattern."""
        values = [1, 1, 1, 1, 1, 1, 1]  # No pattern
        
        result = analytics._detect_seasonality(values)
        
        assert result is False
    
    def test_calculate_volatility(self, analytics):
        """Test volatility calculation."""
        values = [1, 2, 3, 4, 5]
        
        volatility = analytics._calculate_volatility(values)
        
        assert volatility > 0
        assert isinstance(volatility, float)
    
    def test_calculate_prediction_confidence_high(self, analytics):
        """Test prediction confidence calculation for high confidence."""
        values = [10, 10, 10, 10, 10]  # Very consistent
        
        confidence = analytics._calculate_prediction_confidence(values)
        
        assert confidence == "high"
    
    def test_calculate_prediction_confidence_low(self, analytics):
        """Test prediction confidence calculation for low confidence."""
        values = [1, 10, 1, 10, 1]  # Very inconsistent
        
        confidence = analytics._calculate_prediction_confidence(values)
        
        assert confidence == "low"
    
    def test_generate_insights(self, analytics):
        """Test insights generation."""
        change_analytics = {"total_changes": 50, "change_frequency": "high"}
        performance_analytics = {"success_rate": 90}
        impact_analytics = {"avg_impact_score": 8}
        trend_analysis = {"trend_direction": TrendDirection.INCREASING}
        pattern_analysis = {}
        predictions = {}
        anomalies = {"anomalies_detected": 2}
        correlations = {}
        
        insights = analytics._generate_insights(
            change_analytics, performance_analytics, impact_analytics,
            trend_analysis, pattern_analysis, predictions, anomalies, correlations
        )
        
        assert isinstance(insights, list)
        assert len(insights) > 0
    
    def test_generate_recommendations(self, analytics):
        """Test recommendations generation."""
        insights = [
            "High change frequency detected - consider increasing monitoring resources",
            "Monitoring success rate (90%) below target - investigate failures"
        ]
        
        recommendations = analytics._generate_recommendations(insights)
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
    
    def test_generate_executive_summary(self, analytics):
        """Test executive summary generation."""
        change_analytics = {"total_changes": 45, "change_frequency": "moderate"}
        performance_analytics = {"success_rate": 95.5}
        impact_analytics = {"avg_impact_score": 6.2}
        
        summary = analytics._generate_executive_summary(
            change_analytics, performance_analytics, impact_analytics
        )
        
        assert "total_changes" in summary
        assert "monitoring_success_rate" in summary
        assert "average_impact_score" in summary
        assert "system_health_score" in summary
        assert "key_metrics" in summary


class TestAnalyticsHelperFunctions:
    """Test cases for analytics helper functions."""
    
    def test_calculate_period_comparison(self):
        """Test period comparison calculation."""
        from src.api.report_analytics import _calculate_period_comparison
        
        period1_result = {
            "summary": {
                "total_changes": 20,
                "monitoring_success_rate": 90,
                "average_impact_score": 5.0,
                "system_health_score": 70
            },
            "period": {"duration_days": 15}
        }
        
        period2_result = {
            "summary": {
                "total_changes": 25,
                "monitoring_success_rate": 95,
                "average_impact_score": 6.0,
                "system_health_score": 80
            },
            "period": {"duration_days": 15}
        }
        
        comparison = _calculate_period_comparison(period1_result, period2_result)
        
        assert comparison["total_changes_change"] == 5
        assert comparison["success_rate_change"] == 5
        assert comparison["impact_score_change"] == 1.0
        assert comparison["health_score_change"] == 10
    
    def test_compare_distributions(self):
        """Test distribution comparison."""
        from src.api.report_analytics import _compare_distributions
        
        dist1 = {"A": 10, "B": 5}
        dist2 = {"A": 15, "B": 5, "C": 3}
        
        changes = _compare_distributions(dist1, dist2)
        
        assert "A" in changes
        assert changes["A"]["change"] == 5
        assert "C" in changes
        assert changes["C"]["change"] == 3
    
    def test_generate_comparison_insights(self):
        """Test comparison insights generation."""
        from src.api.report_analytics import _generate_comparison_insights
        
        comparison = {
            "health_score_change": 15,
            "success_rate_change": 8
        }
        changes = {"frequency_change": True}
        
        insights = _generate_comparison_insights(comparison, changes)
        
        assert isinstance(insights, list)
        assert len(insights) > 0
    
    def test_calculate_performance_score(self):
        """Test performance score calculation."""
        from src.api.report_analytics import _calculate_performance_score
        
        summary = {"monitoring_success_rate": 95}
        score = _calculate_performance_score(summary)
        
        assert score == 40  # Should be 40 for 95% success rate
    
    def test_calculate_change_management_score(self):
        """Test change management score calculation."""
        from src.api.report_analytics import _calculate_change_management_score
        
        summary = {
            "total_changes": 10,
            "key_metrics": {"changes_per_day": 0.5}
        }
        score = _calculate_change_management_score(summary)
        
        assert score == 30  # Should be 30 for low change frequency
    
    def test_calculate_impact_management_score(self):
        """Test impact management score calculation."""
        from src.api.report_analytics import _calculate_impact_management_score
        
        summary = {
            "average_impact_score": 4.0,
            "key_metrics": {"critical_changes": 1}
        }
        score = _calculate_impact_management_score(summary)
        
        assert score == 30  # Should be 30 for low impact and few critical changes


if __name__ == "__main__":
    pytest.main([__file__]) 