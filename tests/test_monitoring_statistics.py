"""
Unit tests for monitoring statistics and performance tracking.

Tests the comprehensive monitoring statistics system including performance metrics,
AI analysis tracking, error monitoring, and historical trend analysis.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from collections import defaultdict

from src.monitors.monitoring_statistics import (
    MonitoringStatistics,
    PerformanceMetrics,
    AIAnalysisMetrics,
    ErrorMetrics,
    CoverageMetrics,
    ChangeMetrics,
    SystemHealthMetrics,
    MetricType,
    get_monitoring_statistics,
    record_monitoring_event
)


class TestMonitoringStatistics:
    """Test the MonitoringStatistics class."""
    
    @pytest.fixture
    def stats(self):
        """Create a fresh MonitoringStatistics instance for each test."""
        return MonitoringStatistics(history_window_days=7)
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        with patch('src.monitors.monitoring_statistics.get_db') as mock_get_db:
            mock_session = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            yield mock_session
    
    def test_initialization(self, stats):
        """Test MonitoringStatistics initialization."""
        assert stats.history_window_days == 7
        assert stats.history_window == timedelta(days=7)
        assert len(stats.performance_history) == 0
        assert len(stats.ai_analysis_history) == 0
        assert len(stats.error_history) == 0
        assert stats.monitoring_start_time is None
        assert stats.last_metrics_update is None
        
        # Check that all metric types are initialized
        for metric_type in MetricType:
            assert metric_type in stats.current_metrics
            assert stats.current_metrics[metric_type] is not None
    
    def test_initialization_nested_dicts(self, stats):
        """Test that nested dictionaries are properly initialized."""
        ai_metrics = stats.current_metrics[MetricType.AI_ANALYSIS]
        assert ai_metrics.enhanced_features_usage == {}
        
        error_metrics = stats.current_metrics[MetricType.ERROR_RATES]
        assert error_metrics.errors_by_type == {}
        assert error_metrics.errors_by_severity == {}
        assert error_metrics.http_errors == {}
        
        coverage_metrics = stats.current_metrics[MetricType.COVERAGE]
        assert coverage_metrics.monitoring_frequency_distribution == {}
        
        change_metrics = stats.current_metrics[MetricType.CHANGES]
        assert change_metrics.changes_by_severity == {}
        assert change_metrics.changes_by_type == {}
        assert change_metrics.changes_by_agency == {}
    
    @pytest.mark.asyncio
    async def test_start_monitoring_session(self, stats):
        """Test starting a monitoring session."""
        session_id = await stats.start_monitoring_session()
        
        assert session_id.startswith("session_")
        assert stats.monitoring_start_time is not None
        assert isinstance(stats.monitoring_start_time, datetime)
    
    @pytest.mark.asyncio
    async def test_record_performance_metric(self, stats):
        """Test recording performance metrics."""
        await stats.record_performance_metric(
            operation_type="agency_monitoring",
            processing_time_ms=1500,
            additional_data={"agencies": 5, "forms": 25}
        )
        
        metrics = stats.current_metrics[MetricType.PERFORMANCE]
        assert metrics.total_processing_time_ms == 1500
        assert metrics.total_requests_made == 1
        assert metrics.avg_processing_time_ms == 1500.0
        assert metrics.min_processing_time_ms == 1500.0
        assert metrics.max_processing_time_ms == 1500.0
        
        # Check history
        assert len(stats.performance_history) == 1
        history_entry = stats.performance_history[0]
        assert history_entry["operation_type"] == "agency_monitoring"
        assert history_entry["processing_time_ms"] == 1500
        assert history_entry["additional_data"]["agencies"] == 5
    
    @pytest.mark.asyncio
    async def test_record_performance_metric_multiple(self, stats):
        """Test recording multiple performance metrics."""
        await stats.record_performance_metric("operation1", 1000)
        await stats.record_performance_metric("operation2", 2000)
        await stats.record_performance_metric("operation3", 500)
        
        metrics = stats.current_metrics[MetricType.PERFORMANCE]
        assert metrics.total_processing_time_ms == 3500
        assert metrics.total_requests_made == 3
        assert metrics.avg_processing_time_ms == 1166.67  # 3500/3
        assert metrics.min_processing_time_ms == 500.0
        assert metrics.max_processing_time_ms == 2000.0
        assert len(stats.performance_history) == 3
    
    @pytest.mark.asyncio
    async def test_record_ai_analysis_metric(self, stats):
        """Test recording AI analysis metrics."""
        await stats.record_ai_analysis_metric(
            analysis_type="semantic_analysis",
            processing_time_ms=2500,
            confidence_score=85.5,
            success=True,
            enhanced_features=["false_positive_reduction", "semantic_detection"],
            model_version="v2.1.0"
        )
        
        metrics = stats.current_metrics[MetricType.AI_ANALYSIS]
        assert metrics.total_analyses_performed == 1
        assert metrics.successful_analyses == 1
        assert metrics.failed_analyses == 0
        assert metrics.avg_analysis_time_ms == 2500.0
        assert metrics.avg_confidence_score == 85.5
        assert metrics.model_version == "v2.1.0"
        assert metrics.enhanced_features_usage["false_positive_reduction"] == 1
        assert metrics.enhanced_features_usage["semantic_detection"] == 1
        
        # Check history
        assert len(stats.ai_analysis_history) == 1
        history_entry = stats.ai_analysis_history[0]
        assert history_entry["analysis_type"] == "semantic_analysis"
        assert history_entry["confidence_score"] == 85.5
        assert history_entry["success"] is True
    
    @pytest.mark.asyncio
    async def test_record_ai_analysis_metric_failed(self, stats):
        """Test recording failed AI analysis metrics."""
        await stats.record_ai_analysis_metric(
            analysis_type="llm_classification",
            processing_time_ms=5000,
            confidence_score=0.0,
            success=False,
            model_version="v2.1.0"
        )
        
        metrics = stats.current_metrics[MetricType.AI_ANALYSIS]
        assert metrics.total_analyses_performed == 1
        assert metrics.successful_analyses == 0
        assert metrics.failed_analyses == 1
        assert metrics.avg_analysis_time_ms == 5000.0
        assert metrics.avg_confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_record_error_metric(self, stats):
        """Test recording error metrics."""
        await stats.record_error_metric(
            error_type="connection_timeout",
            error_severity="medium",
            http_status_code=408,
            retry_attempts=3,
            circuit_breaker_tripped=False
        )
        
        metrics = stats.current_metrics[MetricType.ERROR_RATES]
        assert metrics.total_errors == 1
        assert metrics.errors_by_type["connection_timeout"] == 1
        assert metrics.errors_by_severity["medium"] == 1
        assert metrics.http_errors[408] == 1
        assert metrics.avg_retry_attempts == 3.0
        assert metrics.circuit_breaker_trips == 0
        
        # Check history
        assert len(stats.error_history) == 1
        history_entry = stats.error_history[0]
        assert history_entry["error_type"] == "connection_timeout"
        assert history_entry["error_severity"] == "medium"
        assert history_entry["http_status_code"] == 408
    
    @pytest.mark.asyncio
    async def test_record_error_metric_circuit_breaker(self, stats):
        """Test recording error metrics with circuit breaker trip."""
        await stats.record_error_metric(
            error_type="http_500",
            error_severity="high",
            http_status_code=500,
            retry_attempts=5,
            circuit_breaker_tripped=True
        )
        
        metrics = stats.current_metrics[MetricType.ERROR_RATES]
        assert metrics.circuit_breaker_trips == 1
        assert metrics.errors_by_type["http_500"] == 1
        assert metrics.errors_by_severity["high"] == 1
    
    @pytest.mark.asyncio
    async def test_record_change_metric(self, stats):
        """Test recording change detection metrics."""
        await stats.record_change_metric(
            change_severity="critical",
            change_type="form_structure",
            agency_name="Department of Labor",
            confidence_score=92.5,
            has_ai_analysis=True
        )
        
        metrics = stats.current_metrics[MetricType.CHANGES]
        assert metrics.total_changes_detected == 1
        assert metrics.changes_by_severity["critical"] == 1
        assert metrics.changes_by_type["form_structure"] == 1
        assert metrics.changes_by_agency["Department of Labor"] == 1
        assert metrics.critical_changes == 1
        assert metrics.changes_with_ai_analysis == 1
        assert metrics.avg_change_confidence == 92.5
    
    @pytest.mark.asyncio
    async def test_record_change_metric_cosmetic(self, stats):
        """Test recording cosmetic change metrics."""
        await stats.record_change_metric(
            change_severity="low",
            change_type="formatting",
            agency_name="State of California",
            confidence_score=45.0,
            has_ai_analysis=False
        )
        
        metrics = stats.current_metrics[MetricType.CHANGES]
        assert metrics.changes_by_severity["low"] == 1
        assert metrics.changes_by_type["formatting"] == 1
        assert metrics.changes_by_agency["State of California"] == 1
        assert metrics.critical_changes == 0
        assert metrics.changes_with_ai_analysis == 0
    
    @pytest.mark.asyncio
    async def test_update_coverage_metrics(self, stats):
        """Test updating coverage metrics."""
        frequency_distribution = {"daily": 10, "weekly": 35, "monthly": 5}
        
        await stats.update_coverage_metrics(
            total_agencies=51,
            active_agencies=50,
            total_forms=150,
            active_forms=148,
            states_covered=50,
            federal_agencies_covered=1,
            frequency_distribution=frequency_distribution
        )
        
        metrics = stats.current_metrics[MetricType.COVERAGE]
        assert metrics.total_agencies_configured == 51
        assert metrics.active_agencies == 50
        assert metrics.total_forms_configured == 150
        assert metrics.active_forms == 148
        assert metrics.states_covered == 50
        assert metrics.federal_agencies_covered == 1
        assert metrics.coverage_percentage == pytest.approx(98.04, rel=0.01)
        assert metrics.monitoring_frequency_distribution == frequency_distribution
        assert metrics.last_comprehensive_run is not None
    
    @pytest.mark.asyncio
    async def test_update_system_health_metrics(self, stats):
        """Test updating system health metrics."""
        service_health = {
            "database": {"status": "healthy"},
            "ai_service": {"status": "degraded"},
            "error_handler": {"status": "healthy"},
            "config_manager": {"status": "healthy"}
        }
        
        await stats.update_system_health_metrics(
            service_health=service_health,
            system_load=0.75,
            memory_usage=65.5,
            disk_usage=45.2
        )
        
        metrics = stats.current_metrics[MetricType.SYSTEM_HEALTH]
        assert metrics.database_connection_health == "healthy"
        assert metrics.ai_service_health == "degraded"
        assert metrics.error_handler_health == "healthy"
        assert metrics.config_manager_health == "healthy"
        assert metrics.system_load_avg == 0.75
        assert metrics.memory_usage_percentage == 65.5
        assert metrics.disk_usage_percentage == 45.2
        assert metrics.last_health_check is not None
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_statistics(self, stats, mock_db_session):
        """Test getting comprehensive statistics."""
        # Setup mock database responses
        mock_db_session.query.return_value.count.return_value = 10
        mock_db_session.query.return_value.filter.return_value.count.return_value = 8
        
        # Record some metrics first
        await stats.start_monitoring_session()
        await stats.record_performance_metric("test_operation", 1000)
        await stats.record_ai_analysis_metric("test_analysis", 2000, 85.0, True)
        await stats.record_error_metric("test_error", "medium")
        await stats.record_change_metric("high", "test_change", "Test Agency", 90.0)
        
        # Get comprehensive statistics
        stats_report = await stats.get_comprehensive_statistics()
        
        # Verify structure
        assert "timestamp" in stats_report
        assert "monitoring_session" in stats_report
        assert "current_metrics" in stats_report
        assert "historical_trends" in stats_report
        assert "database_statistics" in stats_report
        assert "performance_insights" in stats_report
        assert "recommendations" in stats_report
        
        # Verify monitoring session
        session = stats_report["monitoring_session"]
        assert session["start_time"] is not None
        assert session["duration_minutes"] is not None
        
        # Verify current metrics
        current_metrics = stats_report["current_metrics"]
        assert "performance" in current_metrics
        assert "ai_analysis" in current_metrics
        assert "error_rates" in current_metrics
        assert "coverage" in current_metrics
        assert "changes" in current_metrics
        assert "system_health" in current_metrics
        
        # Verify historical trends
        trends = stats_report["historical_trends"]
        assert "performance_trends" in trends
        assert "ai_analysis_trends" in trends
        assert "error_trends" in trends
        assert "change_trends" in trends
    
    @pytest.mark.asyncio
    async def test_calculate_historical_trends(self, stats):
        """Test historical trends calculation."""
        # Add some historical data
        await stats.record_performance_metric("op1", 1000)
        await stats.record_performance_metric("op2", 2000)
        await stats.record_performance_metric("op3", 1500)
        
        await stats.record_ai_analysis_metric("analysis1", 1000, 80.0, True)
        await stats.record_ai_analysis_metric("analysis2", 2000, 90.0, True)
        await stats.record_ai_analysis_metric("analysis3", 1500, 0.0, False)
        
        await stats.record_error_metric("error1", "low")
        await stats.record_error_metric("error2", "medium")
        await stats.record_error_metric("error1", "low")  # Duplicate
        
        trends = await stats._calculate_historical_trends()
        
        # Performance trends
        perf_trends = trends["performance_trends"]
        assert perf_trends["avg_processing_time"] == 1500.0
        assert perf_trends["total_operations"] == 3
        
        # AI analysis trends
        ai_trends = trends["ai_analysis_trends"]
        assert ai_trends["avg_confidence"] == 85.0  # Only successful analyses
        assert ai_trends["success_rate"] == pytest.approx(0.667, rel=0.01)  # 2/3
        assert ai_trends["total_analyses"] == 3
        
        # Error trends
        error_trends = trends["error_trends"]
        assert error_trends["most_common_errors"]["error1"] == 2
        assert error_trends["most_common_errors"]["error2"] == 1
        assert error_trends["total_errors"] == 3
    
    @pytest.mark.asyncio
    async def test_get_database_statistics(self, stats, mock_db_session):
        """Test database statistics retrieval."""
        # Setup mock responses
        mock_db_session.query.return_value.count.side_effect = [20, 18, 100, 95, 500, 50, 200, 180]
        
        db_stats = await stats._get_database_statistics()
        
        # Verify structure
        assert "agencies" in db_stats
        assert "forms" in db_stats
        assert "changes" in db_stats
        assert "monitoring_runs" in db_stats
        
        # Verify calculations
        agencies = db_stats["agencies"]
        assert agencies["total"] == 20
        assert agencies["active"] == 18
        assert agencies["coverage_percentage"] == 90.0
        
        forms = db_stats["forms"]
        assert forms["total"] == 100
        assert forms["active"] == 95
        assert forms["coverage_percentage"] == 95.0
        
        changes = db_stats["changes"]
        assert changes["total"] == 500
        assert changes["recent_7_days"] == 50
        
        runs = db_stats["monitoring_runs"]
        assert runs["total"] == 200
        assert runs["successful"] == 180
        assert runs["success_rate"] == 90.0
    
    @pytest.mark.asyncio
    async def test_generate_performance_insights(self, stats):
        """Test performance insights generation."""
        # Set up metrics that should trigger insights
        perf_metrics = stats.current_metrics[MetricType.PERFORMANCE]
        perf_metrics.avg_processing_time_ms = 6000  # High processing time
        perf_metrics.cache_hit_rate = 0.3  # Low cache hit rate
        
        ai_metrics = stats.current_metrics[MetricType.AI_ANALYSIS]
        ai_metrics.total_analyses_performed = 100
        ai_metrics.failed_analyses = 15  # 15% failure rate
        
        error_metrics = stats.current_metrics[MetricType.ERROR_RATES]
        error_metrics.circuit_breaker_trips = 3
        error_metrics.retry_success_rate = 0.7  # Low retry success rate
        
        insights = await stats._generate_performance_insights()
        
        assert len(insights) >= 4
        assert any("processing time is high" in insight for insight in insights)
        assert any("cache hit rate is low" in insight for insight in insights)
        assert any("AI analysis failure rate" in insight for insight in insights)
        assert any("Circuit breakers have been triggered" in insight for insight in insights)
        assert any("Retry success rate is low" in insight for insight in insights)
    
    @pytest.mark.asyncio
    async def test_generate_recommendations(self, stats):
        """Test recommendations generation."""
        # Set up metrics that should trigger recommendations
        coverage_metrics = stats.current_metrics[MetricType.COVERAGE]
        coverage_metrics.coverage_percentage = 90.0  # Below 95%
        
        perf_metrics = stats.current_metrics[MetricType.PERFORMANCE]
        perf_metrics.avg_processing_time_ms = 12000  # Above 10 seconds
        
        ai_metrics = stats.current_metrics[MetricType.AI_ANALYSIS]
        ai_metrics.avg_confidence_score = 65.0  # Below 70%
        
        recommendations = await stats._generate_recommendations()
        
        assert len(recommendations) >= 3
        assert any("Coverage is below 95%" in rec for rec in recommendations)
        assert any("parallel processing" in rec for rec in recommendations)
        assert any("confidence scores are low" in rec for rec in recommendations)
    
    def test_calculate_session_duration(self, stats):
        """Test session duration calculation."""
        # No session started
        assert stats._calculate_session_duration() is None
        
        # Start session
        stats.monitoring_start_time = datetime.utcnow() - timedelta(minutes=30)
        duration = stats._calculate_session_duration()
        assert duration is not None
        assert duration > 29  # Should be around 30 minutes
    
    @pytest.mark.asyncio
    async def test_reset_metrics(self, stats):
        """Test resetting all metrics."""
        # Add some data first
        await stats.start_monitoring_session()
        await stats.record_performance_metric("test", 1000)
        await stats.record_ai_analysis_metric("test", 1000, 80.0, True)
        await stats.record_error_metric("test", "low")
        await stats.record_change_metric("medium", "test", "Test", 80.0)
        
        # Verify data exists
        assert len(stats.performance_history) > 0
        assert len(stats.ai_analysis_history) > 0
        assert len(stats.error_history) > 0
        assert stats.current_metrics[MetricType.PERFORMANCE].total_requests_made > 0
        
        # Reset metrics
        await stats.reset_metrics()
        
        # Verify reset
        assert len(stats.performance_history) == 0
        assert len(stats.ai_analysis_history) == 0
        assert len(stats.error_history) == 0
        assert stats.current_metrics[MetricType.PERFORMANCE].total_requests_made == 0
        assert stats.current_metrics[MetricType.AI_ANALYSIS].total_analyses_performed == 0
        assert stats.current_metrics[MetricType.ERROR_RATES].total_errors == 0
        assert stats.current_metrics[MetricType.CHANGES].total_changes_detected == 0


class TestMonitoringStatisticsGlobal:
    """Test global monitoring statistics functionality."""
    
    def test_get_monitoring_statistics_singleton(self):
        """Test that get_monitoring_statistics returns a singleton."""
        stats1 = get_monitoring_statistics()
        stats2 = get_monitoring_statistics()
        assert stats1 is stats2
    
    @pytest.mark.asyncio
    async def test_record_monitoring_event(self):
        """Test the convenience function for recording events."""
        with patch('src.monitors.monitoring_statistics.get_monitoring_statistics') as mock_get_stats:
            mock_stats = AsyncMock()
            mock_get_stats.return_value = mock_stats
            
            # Test performance event
            await record_monitoring_event("performance", operation_type="test", processing_time_ms=1000)
            mock_stats.record_performance_metric.assert_called_once_with(
                operation_type="test", processing_time_ms=1000
            )
            
            # Test AI analysis event
            await record_monitoring_event("ai_analysis", analysis_type="test", processing_time_ms=1000, confidence_score=80.0, success=True)
            mock_stats.record_ai_analysis_metric.assert_called_once_with(
                analysis_type="test", processing_time_ms=1000, confidence_score=80.0, success=True
            )
            
            # Test error event
            await record_monitoring_event("error", error_type="test", error_severity="low")
            mock_stats.record_error_metric.assert_called_once_with(
                error_type="test", error_severity="low"
            )
            
            # Test change event
            await record_monitoring_event("change", change_severity="medium", change_type="test", agency_name="Test", confidence_score=80.0)
            mock_stats.record_change_metric.assert_called_once_with(
                change_severity="medium", change_type="test", agency_name="Test", confidence_score=80.0
            )
    
    @pytest.mark.asyncio
    async def test_record_monitoring_event_unknown_type(self):
        """Test recording unknown event type."""
        with patch('src.monitors.monitoring_statistics.get_monitoring_statistics') as mock_get_stats:
            mock_stats = AsyncMock()
            mock_get_stats.return_value = mock_stats
            
            await record_monitoring_event("unknown_type", some_data="test")
            # Should not call any recording methods
            mock_stats.record_performance_metric.assert_not_called()
            mock_stats.record_ai_analysis_metric.assert_not_called()
            mock_stats.record_error_metric.assert_not_called()
            mock_stats.record_change_metric.assert_not_called()


class TestMetricDataclasses:
    """Test the metric dataclass definitions."""
    
    def test_performance_metrics_defaults(self):
        """Test PerformanceMetrics default values."""
        metrics = PerformanceMetrics()
        assert metrics.total_agencies_monitored == 0
        assert metrics.total_forms_processed == 0
        assert metrics.total_processing_time_ms == 0
        assert metrics.avg_processing_time_ms == 0.0
        assert metrics.min_processing_time_ms == 0.0
        assert metrics.max_processing_time_ms == 0.0
        assert metrics.total_requests_made == 0
        assert metrics.avg_response_time_ms == 0.0
        assert metrics.cache_hit_rate == 0.0
        assert metrics.concurrent_operations == 0
        assert metrics.batch_processing_efficiency == 0.0
    
    def test_ai_analysis_metrics_defaults(self):
        """Test AIAnalysisMetrics default values."""
        metrics = AIAnalysisMetrics()
        assert metrics.total_analyses_performed == 0
        assert metrics.successful_analyses == 0
        assert metrics.failed_analyses == 0
        assert metrics.avg_analysis_time_ms == 0.0
        assert metrics.avg_confidence_score == 0.0
        assert metrics.false_positive_rate == 0.0
        assert metrics.semantic_similarity_avg == 0.0
        assert metrics.change_classification_accuracy == 0.0
        assert metrics.llm_response_time_avg == 0.0
        assert metrics.model_version == ""
        assert metrics.enhanced_features_usage is None
    
    def test_error_metrics_defaults(self):
        """Test ErrorMetrics default values."""
        metrics = ErrorMetrics()
        assert metrics.total_errors == 0
        assert metrics.errors_by_type is None
        assert metrics.errors_by_severity is None
        assert metrics.circuit_breaker_trips == 0
        assert metrics.retry_success_rate == 0.0
        assert metrics.avg_retry_attempts == 0.0
        assert metrics.timeout_errors == 0
        assert metrics.connection_errors == 0
        assert metrics.http_errors is None
        assert metrics.selenium_errors == 0
    
    def test_coverage_metrics_defaults(self):
        """Test CoverageMetrics default values."""
        metrics = CoverageMetrics()
        assert metrics.total_agencies_configured == 0
        assert metrics.active_agencies == 0
        assert metrics.total_forms_configured == 0
        assert metrics.active_forms == 0
        assert metrics.coverage_percentage == 0.0
        assert metrics.states_covered == 0
        assert metrics.federal_agencies_covered == 0
        assert metrics.last_comprehensive_run is None
        assert metrics.monitoring_frequency_distribution is None
    
    def test_change_metrics_defaults(self):
        """Test ChangeMetrics default values."""
        metrics = ChangeMetrics()
        assert metrics.total_changes_detected == 0
        assert metrics.changes_by_severity is None
        assert metrics.changes_by_type is None
        assert metrics.changes_by_agency is None
        assert metrics.avg_change_confidence == 0.0
        assert metrics.critical_changes == 0
        assert metrics.cosmetic_changes == 0
        assert metrics.changes_with_ai_analysis == 0
        assert metrics.notification_success_rate == 0.0
    
    def test_system_health_metrics_defaults(self):
        """Test SystemHealthMetrics default values."""
        metrics = SystemHealthMetrics()
        assert metrics.service_uptime_percentage == 0.0
        assert metrics.database_connection_health == "unknown"
        assert metrics.ai_service_health == "unknown"
        assert metrics.error_handler_health == "unknown"
        assert metrics.config_manager_health == "unknown"
        assert metrics.last_health_check is None
        assert metrics.system_load_avg == 0.0
        assert metrics.memory_usage_percentage == 0.0
        assert metrics.disk_usage_percentage == 0.0


class TestMetricTypeEnum:
    """Test the MetricType enum."""
    
    def test_metric_type_values(self):
        """Test MetricType enum values."""
        assert MetricType.PERFORMANCE.value == "performance"
        assert MetricType.AI_ANALYSIS.value == "ai_analysis"
        assert MetricType.ERROR_RATES.value == "error_rates"
        assert MetricType.COVERAGE.value == "coverage"
        assert MetricType.CHANGES.value == "changes"
        assert MetricType.SYSTEM_HEALTH.value == "system_health"
    
    def test_metric_type_members(self):
        """Test MetricType enum members."""
        assert len(MetricType) == 6
        assert MetricType.PERFORMANCE in MetricType
        assert MetricType.AI_ANALYSIS in MetricType
        assert MetricType.ERROR_RATES in MetricType
        assert MetricType.COVERAGE in MetricType
        assert MetricType.CHANGES in MetricType
        assert MetricType.SYSTEM_HEALTH in MetricType 