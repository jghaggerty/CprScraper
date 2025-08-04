"""
Monitoring Statistics and Performance Tracking

This module provides comprehensive tracking and analysis of monitoring operations,
AI analysis performance, error rates, and system health metrics for the
AI-powered compliance monitoring system.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import statistics
from collections import defaultdict, deque

from ..database.connection import get_db
from ..database.models import Agency, Form, FormChange, MonitoringRun

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics that can be tracked."""
    PERFORMANCE = "performance"
    AI_ANALYSIS = "ai_analysis"
    ERROR_RATES = "error_rates"
    COVERAGE = "coverage"
    CHANGES = "changes"
    SYSTEM_HEALTH = "system_health"


@dataclass
class PerformanceMetrics:
    """Performance metrics for monitoring operations."""
    total_agencies_monitored: int = 0
    total_forms_processed: int = 0
    total_processing_time_ms: int = 0
    avg_processing_time_ms: float = 0.0
    min_processing_time_ms: float = 0.0
    max_processing_time_ms: float = 0.0
    total_requests_made: int = 0
    avg_response_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    concurrent_operations: int = 0
    batch_processing_efficiency: float = 0.0


@dataclass
class AIAnalysisMetrics:
    """AI analysis performance metrics."""
    total_analyses_performed: int = 0
    successful_analyses: int = 0
    failed_analyses: int = 0
    avg_analysis_time_ms: float = 0.0
    avg_confidence_score: float = 0.0
    false_positive_rate: float = 0.0
    semantic_similarity_avg: float = 0.0
    change_classification_accuracy: float = 0.0
    llm_response_time_avg: float = 0.0
    model_version: str = ""
    enhanced_features_usage: Dict[str, int] = None


@dataclass
class ErrorMetrics:
    """Error tracking metrics."""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = None
    errors_by_severity: Dict[str, int] = None
    circuit_breaker_trips: int = 0
    retry_success_rate: float = 0.0
    avg_retry_attempts: float = 0.0
    timeout_errors: int = 0
    connection_errors: int = 0
    http_errors: Dict[int, int] = None
    selenium_errors: int = 0


@dataclass
class CoverageMetrics:
    """Coverage and monitoring metrics."""
    total_agencies_configured: int = 0
    active_agencies: int = 0
    total_forms_configured: int = 0
    active_forms: int = 0
    coverage_percentage: float = 0.0
    states_covered: int = 0
    federal_agencies_covered: int = 0
    last_comprehensive_run: Optional[datetime] = None
    monitoring_frequency_distribution: Dict[str, int] = None


@dataclass
class ChangeMetrics:
    """Change detection metrics."""
    total_changes_detected: int = 0
    changes_by_severity: Dict[str, int] = None
    changes_by_type: Dict[str, int] = None
    changes_by_agency: Dict[str, int] = None
    avg_change_confidence: float = 0.0
    critical_changes: int = 0
    cosmetic_changes: int = 0
    changes_with_ai_analysis: int = 0
    notification_success_rate: float = 0.0


@dataclass
class SystemHealthMetrics:
    """System health and availability metrics."""
    service_uptime_percentage: float = 0.0
    database_connection_health: str = "unknown"
    ai_service_health: str = "unknown"
    error_handler_health: str = "unknown"
    config_manager_health: str = "unknown"
    last_health_check: Optional[datetime] = None
    system_load_avg: float = 0.0
    memory_usage_percentage: float = 0.0
    disk_usage_percentage: float = 0.0


class MonitoringStatistics:
    """
    Comprehensive monitoring statistics and performance tracking.
    
    Tracks detailed metrics about monitoring operations, AI analysis performance,
    error rates, and system health for the AI-powered compliance monitoring system.
    """
    
    def __init__(self, history_window_days: int = 30):
        """
        Initialize the monitoring statistics tracker.
        
        Args:
            history_window_days: Number of days to keep historical data
        """
        self.history_window_days = history_window_days
        self.history_window = timedelta(days=history_window_days)
        
        # Performance tracking
        self.performance_history = deque(maxlen=1000)
        self.ai_analysis_history = deque(maxlen=1000)
        self.error_history = deque(maxlen=1000)
        
        # Real-time metrics
        self.current_metrics = {
            MetricType.PERFORMANCE: PerformanceMetrics(),
            MetricType.AI_ANALYSIS: AIAnalysisMetrics(),
            MetricType.ERROR_RATES: ErrorMetrics(),
            MetricType.COVERAGE: CoverageMetrics(),
            MetricType.CHANGES: ChangeMetrics(),
            MetricType.SYSTEM_HEALTH: SystemHealthMetrics()
        }
        
        # Initialize nested dictionaries
        self.current_metrics[MetricType.AI_ANALYSIS].enhanced_features_usage = {}
        self.current_metrics[MetricType.ERROR_RATES].errors_by_type = {}
        self.current_metrics[MetricType.ERROR_RATES].errors_by_severity = {}
        self.current_metrics[MetricType.ERROR_RATES].http_errors = {}
        self.current_metrics[MetricType.COVERAGE].monitoring_frequency_distribution = {}
        self.current_metrics[MetricType.CHANGES].changes_by_severity = {}
        self.current_metrics[MetricType.CHANGES].changes_by_type = {}
        self.current_metrics[MetricType.CHANGES].changes_by_agency = {}
        
        # Tracking state
        self.monitoring_start_time = None
        self.last_metrics_update = None
        
        logger.info(f"Monitoring statistics initialized with {history_window_days} day history window")
    
    async def start_monitoring_session(self) -> str:
        """
        Start a new monitoring session and return session ID.
        
        Returns:
            Session ID for tracking this monitoring run
        """
        self.monitoring_start_time = datetime.utcnow()
        session_id = f"session_{self.monitoring_start_time.strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Started monitoring session: {session_id}")
        return session_id
    
    async def record_performance_metric(self, 
                                      operation_type: str,
                                      processing_time_ms: int,
                                      additional_data: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a performance metric for monitoring operations.
        
        Args:
            operation_type: Type of operation (e.g., 'agency_monitoring', 'form_analysis')
            processing_time_ms: Processing time in milliseconds
            additional_data: Additional performance data
        """
        timestamp = datetime.utcnow()
        
        # Update current metrics
        metrics = self.current_metrics[MetricType.PERFORMANCE]
        metrics.total_processing_time_ms += processing_time_ms
        metrics.total_requests_made += 1
        
        # Calculate averages
        if metrics.total_requests_made > 0:
            metrics.avg_processing_time_ms = metrics.total_processing_time_ms / metrics.total_requests_made
        
        # Update min/max
        if metrics.min_processing_time_ms == 0 or processing_time_ms < metrics.min_processing_time_ms:
            metrics.min_processing_time_ms = processing_time_ms
        if processing_time_ms > metrics.max_processing_time_ms:
            metrics.max_processing_time_ms = processing_time_ms
        
        # Store in history
        history_entry = {
            "timestamp": timestamp,
            "operation_type": operation_type,
            "processing_time_ms": processing_time_ms,
            "additional_data": additional_data or {}
        }
        self.performance_history.append(history_entry)
        
        logger.debug(f"Recorded performance metric: {operation_type} took {processing_time_ms}ms")
    
    async def record_ai_analysis_metric(self,
                                      analysis_type: str,
                                      processing_time_ms: int,
                                      confidence_score: float,
                                      success: bool,
                                      enhanced_features: Optional[List[str]] = None,
                                      model_version: str = "") -> None:
        """
        Record AI analysis performance metrics.
        
        Args:
            analysis_type: Type of AI analysis performed
            processing_time_ms: Processing time in milliseconds
            confidence_score: AI confidence score (0-100)
            success: Whether the analysis was successful
            enhanced_features: List of enhanced features used
            model_version: Version of the AI model used
        """
        timestamp = datetime.utcnow()
        
        # Update current metrics
        metrics = self.current_metrics[MetricType.AI_ANALYSIS]
        metrics.total_analyses_performed += 1
        
        if success:
            metrics.successful_analyses += 1
        else:
            metrics.failed_analyses += 1
        
        # Update averages
        if metrics.total_analyses_performed > 0:
            metrics.avg_analysis_time_ms = (
                (metrics.avg_analysis_time_ms * (metrics.total_analyses_performed - 1) + processing_time_ms) 
                / metrics.total_analyses_performed
            )
            metrics.avg_confidence_score = (
                (metrics.avg_confidence_score * (metrics.total_analyses_performed - 1) + confidence_score)
                / metrics.total_analyses_performed
            )
        
        # Track enhanced features usage
        if enhanced_features:
            for feature in enhanced_features:
                metrics.enhanced_features_usage[feature] = metrics.enhanced_features_usage.get(feature, 0) + 1
        
        if model_version:
            metrics.model_version = model_version
        
        # Store in history
        history_entry = {
            "timestamp": timestamp,
            "analysis_type": analysis_type,
            "processing_time_ms": processing_time_ms,
            "confidence_score": confidence_score,
            "success": success,
            "enhanced_features": enhanced_features or [],
            "model_version": model_version
        }
        self.ai_analysis_history.append(history_entry)
        
        logger.debug(f"Recorded AI analysis metric: {analysis_type} - {confidence_score}% confidence, {processing_time_ms}ms")
    
    async def record_error_metric(self,
                                error_type: str,
                                error_severity: str,
                                http_status_code: Optional[int] = None,
                                retry_attempts: int = 0,
                                circuit_breaker_tripped: bool = False) -> None:
        """
        Record error metrics for monitoring operations.
        
        Args:
            error_type: Type of error (e.g., 'connection_timeout', 'http_404')
            error_severity: Severity level (low, medium, high, critical)
            http_status_code: HTTP status code if applicable
            retry_attempts: Number of retry attempts made
            circuit_breaker_tripped: Whether circuit breaker was triggered
        """
        timestamp = datetime.utcnow()
        
        # Update current metrics
        metrics = self.current_metrics[MetricType.ERROR_RATES]
        metrics.total_errors += 1
        
        # Track by type
        metrics.errors_by_type[error_type] = metrics.errors_by_type.get(error_type, 0) + 1
        
        # Track by severity
        metrics.errors_by_severity[error_severity] = metrics.errors_by_severity.get(error_severity, 0) + 1
        
        # Track HTTP errors
        if http_status_code:
            metrics.http_errors[http_status_code] = metrics.http_errors.get(http_status_code, 0) + 1
        
        # Track retry metrics
        if retry_attempts > 0:
            total_retries = metrics.avg_retry_attempts * (metrics.total_errors - 1) + retry_attempts
            metrics.avg_retry_attempts = total_retries / metrics.total_errors
        
        # Track circuit breaker trips
        if circuit_breaker_tripped:
            metrics.circuit_breaker_trips += 1
        
        # Store in history
        history_entry = {
            "timestamp": timestamp,
            "error_type": error_type,
            "error_severity": error_severity,
            "http_status_code": http_status_code,
            "retry_attempts": retry_attempts,
            "circuit_breaker_tripped": circuit_breaker_tripped
        }
        self.error_history.append(history_entry)
        
        logger.debug(f"Recorded error metric: {error_type} ({error_severity})")
    
    async def record_change_metric(self,
                                 change_severity: str,
                                 change_type: str,
                                 agency_name: str,
                                 confidence_score: float,
                                 has_ai_analysis: bool = False) -> None:
        """
        Record change detection metrics.
        
        Args:
            change_severity: Severity of the change (low, medium, high, critical)
            change_type: Type of change detected
            agency_name: Name of the agency where change was detected
            confidence_score: Confidence score for the change detection
            has_ai_analysis: Whether AI analysis was performed
        """
        # Update current metrics
        metrics = self.current_metrics[MetricType.CHANGES]
        metrics.total_changes_detected += 1
        
        # Track by severity
        metrics.changes_by_severity[change_severity] = metrics.changes_by_severity.get(change_severity, 0) + 1
        
        # Track by type
        metrics.changes_by_type[change_type] = metrics.changes_by_type.get(change_type, 0) + 1
        
        # Track by agency
        metrics.changes_by_agency[agency_name] = metrics.changes_by_agency.get(agency_name, 0) + 1
        
        # Track critical changes
        if change_severity == "critical":
            metrics.critical_changes += 1
        
        # Track AI analysis usage
        if has_ai_analysis:
            metrics.changes_with_ai_analysis += 1
        
        # Update average confidence
        if metrics.total_changes_detected > 0:
            metrics.avg_change_confidence = (
                (metrics.avg_change_confidence * (metrics.total_changes_detected - 1) + confidence_score)
                / metrics.total_changes_detected
            )
        
        logger.debug(f"Recorded change metric: {change_type} ({change_severity}) for {agency_name}")
    
    async def update_coverage_metrics(self, 
                                   total_agencies: int,
                                   active_agencies: int,
                                   total_forms: int,
                                   active_forms: int,
                                   states_covered: int,
                                   federal_agencies_covered: int,
                                   frequency_distribution: Dict[str, int]) -> None:
        """
        Update coverage metrics for the monitoring system.
        
        Args:
            total_agencies: Total number of configured agencies
            active_agencies: Number of active agencies
            total_forms: Total number of configured forms
            active_forms: Number of active forms
            states_covered: Number of states covered
            federal_agencies_covered: Number of federal agencies covered
            frequency_distribution: Distribution of monitoring frequencies
        """
        metrics = self.current_metrics[MetricType.COVERAGE]
        metrics.total_agencies_configured = total_agencies
        metrics.active_agencies = active_agencies
        metrics.total_forms_configured = total_forms
        metrics.active_forms = active_forms
        metrics.states_covered = states_covered
        metrics.federal_agencies_covered = federal_agencies_covered
        metrics.monitoring_frequency_distribution = frequency_distribution.copy()
        
        # Calculate coverage percentage
        if total_agencies > 0:
            metrics.coverage_percentage = (active_agencies / total_agencies) * 100
        
        metrics.last_comprehensive_run = datetime.utcnow()
        
        logger.debug(f"Updated coverage metrics: {active_agencies}/{total_agencies} agencies active")
    
    async def update_system_health_metrics(self,
                                         service_health: Dict[str, Any],
                                         system_load: float = 0.0,
                                         memory_usage: float = 0.0,
                                         disk_usage: float = 0.0) -> None:
        """
        Update system health metrics.
        
        Args:
            service_health: Health status from various services
            system_load: System load average
            memory_usage: Memory usage percentage
            disk_usage: Disk usage percentage
        """
        metrics = self.current_metrics[MetricType.SYSTEM_HEALTH]
        
        # Update service health status
        if "database" in service_health:
            metrics.database_connection_health = service_health["database"].get("status", "unknown")
        
        if "ai_service" in service_health:
            metrics.ai_service_health = service_health["ai_service"].get("status", "unknown")
        
        if "error_handler" in service_health:
            metrics.error_handler_health = service_health["error_handler"].get("status", "unknown")
        
        if "config_manager" in service_health:
            metrics.config_manager_health = service_health["config_manager"].get("status", "unknown")
        
        # Update system metrics
        metrics.system_load_avg = system_load
        metrics.memory_usage_percentage = memory_usage
        metrics.disk_usage_percentage = disk_usage
        metrics.last_health_check = datetime.utcnow()
        
        # Calculate uptime percentage (simplified)
        if self.monitoring_start_time:
            total_time = datetime.utcnow() - self.monitoring_start_time
            # This is a simplified calculation - in practice you'd track actual downtime
            metrics.service_uptime_percentage = 99.5  # Placeholder
        
        logger.debug("Updated system health metrics")
    
    async def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics for all tracked metrics.
        
        Returns:
            Dictionary containing all current metrics and historical analysis
        """
        self.last_metrics_update = datetime.utcnow()
        
        # Calculate historical trends
        historical_trends = await self._calculate_historical_trends()
        
        # Get database statistics
        db_stats = await self._get_database_statistics()
        
        # Compile comprehensive report
        stats = {
            "timestamp": self.last_metrics_update.isoformat(),
            "monitoring_session": {
                "start_time": self.monitoring_start_time.isoformat() if self.monitoring_start_time else None,
                "duration_minutes": self._calculate_session_duration()
            },
            "current_metrics": {
                metric_type.value: asdict(metrics)
                for metric_type, metrics in self.current_metrics.items()
            },
            "historical_trends": historical_trends,
            "database_statistics": db_stats,
            "performance_insights": await self._generate_performance_insights(),
            "recommendations": await self._generate_recommendations()
        }
        
        return stats
    
    async def _calculate_historical_trends(self) -> Dict[str, Any]:
        """Calculate historical trends from stored data."""
        trends = {
            "performance_trends": {},
            "ai_analysis_trends": {},
            "error_trends": {},
            "change_trends": {}
        }
        
        # Performance trends
        if self.performance_history:
            processing_times = [entry["processing_time_ms"] for entry in self.performance_history]
            trends["performance_trends"] = {
                "avg_processing_time": statistics.mean(processing_times),
                "processing_time_trend": "stable",  # Simplified
                "total_operations": len(processing_times)
            }
        
        # AI analysis trends
        if self.ai_analysis_history:
            confidence_scores = [entry["confidence_score"] for entry in self.ai_analysis_history if entry["success"]]
            if confidence_scores:
                trends["ai_analysis_trends"] = {
                    "avg_confidence": statistics.mean(confidence_scores),
                    "success_rate": len([e for e in self.ai_analysis_history if e["success"]]) / len(self.ai_analysis_history),
                    "total_analyses": len(self.ai_analysis_history)
                }
        
        # Error trends
        if self.error_history:
            error_types = [entry["error_type"] for entry in self.error_history]
            error_counts = defaultdict(int)
            for error_type in error_types:
                error_counts[error_type] += 1
            
            trends["error_trends"] = {
                "most_common_errors": dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]),
                "total_errors": len(self.error_history)
            }
        
        return trends
    
    async def _get_database_statistics(self) -> Dict[str, Any]:
        """Get statistics from the database."""
        try:
            with get_db() as db:
                # Agency statistics
                total_agencies = db.query(Agency).count()
                active_agencies = db.query(Agency).filter(Agency.is_active == True).count()
                
                # Form statistics
                total_forms = db.query(Form).count()
                active_forms = db.query(Form).filter(Form.is_active == True).count()
                
                # Change statistics
                total_changes = db.query(FormChange).count()
                recent_changes = db.query(FormChange).filter(
                    FormChange.detected_at >= datetime.utcnow() - timedelta(days=7)
                ).count()
                
                # Monitoring run statistics
                total_runs = db.query(MonitoringRun).count()
                successful_runs = db.query(MonitoringRun).filter(MonitoringRun.status == "completed").count()
                
                return {
                    "agencies": {
                        "total": total_agencies,
                        "active": active_agencies,
                        "coverage_percentage": (active_agencies / total_agencies * 100) if total_agencies > 0 else 0
                    },
                    "forms": {
                        "total": total_forms,
                        "active": active_forms,
                        "coverage_percentage": (active_forms / total_forms * 100) if total_forms > 0 else 0
                    },
                    "changes": {
                        "total": total_changes,
                        "recent_7_days": recent_changes
                    },
                    "monitoring_runs": {
                        "total": total_runs,
                        "successful": successful_runs,
                        "success_rate": (successful_runs / total_runs * 100) if total_runs > 0 else 0
                    }
                }
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {"error": str(e)}
    
    async def _generate_performance_insights(self) -> List[str]:
        """Generate performance insights and recommendations."""
        insights = []
        
        # Performance insights
        perf_metrics = self.current_metrics[MetricType.PERFORMANCE]
        if perf_metrics.avg_processing_time_ms > 5000:  # 5 seconds
            insights.append("Average processing time is high - consider optimizing batch sizes or increasing concurrency")
        
        if perf_metrics.cache_hit_rate < 0.5:
            insights.append("Cache hit rate is low - consider expanding cache size or improving cache strategy")
        
        # AI analysis insights
        ai_metrics = self.current_metrics[MetricType.AI_ANALYSIS]
        if ai_metrics.failed_analyses > 0:
            failure_rate = ai_metrics.failed_analyses / ai_metrics.total_analyses_performed
            if failure_rate > 0.1:  # 10% failure rate
                insights.append(f"AI analysis failure rate is {failure_rate:.1%} - investigate AI service health")
        
        # Error insights
        error_metrics = self.current_metrics[MetricType.ERROR_RATES]
        if error_metrics.circuit_breaker_trips > 0:
            insights.append("Circuit breakers have been triggered - some endpoints may be experiencing issues")
        
        if error_metrics.retry_success_rate < 0.8:
            insights.append("Retry success rate is low - consider adjusting retry strategies")
        
        return insights
    
    async def _generate_recommendations(self) -> List[str]:
        """Generate system recommendations based on current metrics."""
        recommendations = []
        
        # Coverage recommendations
        coverage_metrics = self.current_metrics[MetricType.COVERAGE]
        if coverage_metrics.coverage_percentage < 95:
            recommendations.append("Coverage is below 95% - review inactive agencies and forms")
        
        # Performance recommendations
        perf_metrics = self.current_metrics[MetricType.PERFORMANCE]
        if perf_metrics.avg_processing_time_ms > 10000:  # 10 seconds
            recommendations.append("Consider implementing parallel processing for large-scale monitoring")
        
        # AI analysis recommendations
        ai_metrics = self.current_metrics[MetricType.AI_ANALYSIS]
        if ai_metrics.avg_confidence_score < 70:
            recommendations.append("AI confidence scores are low - consider model retraining or threshold adjustment")
        
        return recommendations
    
    def _calculate_session_duration(self) -> Optional[float]:
        """Calculate monitoring session duration in minutes."""
        if self.monitoring_start_time:
            duration = datetime.utcnow() - self.monitoring_start_time
            return duration.total_seconds() / 60
        return None
    
    async def reset_metrics(self) -> None:
        """Reset all current metrics."""
        for metric_type in MetricType:
            if metric_type == MetricType.PERFORMANCE:
                self.current_metrics[metric_type] = PerformanceMetrics()
            elif metric_type == MetricType.AI_ANALYSIS:
                self.current_metrics[metric_type] = AIAnalysisMetrics()
                self.current_metrics[metric_type].enhanced_features_usage = {}
            elif metric_type == MetricType.ERROR_RATES:
                self.current_metrics[metric_type] = ErrorMetrics()
                self.current_metrics[metric_type].errors_by_type = {}
                self.current_metrics[metric_type].errors_by_severity = {}
                self.current_metrics[metric_type].http_errors = {}
            elif metric_type == MetricType.COVERAGE:
                self.current_metrics[metric_type] = CoverageMetrics()
                self.current_metrics[metric_type].monitoring_frequency_distribution = {}
            elif metric_type == MetricType.CHANGES:
                self.current_metrics[metric_type] = ChangeMetrics()
                self.current_metrics[metric_type].changes_by_severity = {}
                self.current_metrics[metric_type].changes_by_type = {}
                self.current_metrics[metric_type].changes_by_agency = {}
            elif metric_type == MetricType.SYSTEM_HEALTH:
                self.current_metrics[metric_type] = SystemHealthMetrics()
        
        # Clear history
        self.performance_history.clear()
        self.ai_analysis_history.clear()
        self.error_history.clear()
        
        logger.info("All monitoring metrics have been reset")


# Global statistics instance
_monitoring_stats = None


def get_monitoring_statistics() -> MonitoringStatistics:
    """Get the global monitoring statistics instance."""
    global _monitoring_stats
    if _monitoring_stats is None:
        _monitoring_stats = MonitoringStatistics()
    return _monitoring_stats


async def record_monitoring_event(event_type: str, **kwargs) -> None:
    """
    Convenience function to record monitoring events.
    
    Args:
        event_type: Type of event to record
        **kwargs: Event-specific data
    """
    stats = get_monitoring_statistics()
    
    if event_type == "performance":
        await stats.record_performance_metric(**kwargs)
    elif event_type == "ai_analysis":
        await stats.record_ai_analysis_metric(**kwargs)
    elif event_type == "error":
        await stats.record_error_metric(**kwargs)
    elif event_type == "change":
        await stats.record_change_metric(**kwargs)
    else:
        logger.warning(f"Unknown event type: {event_type}") 