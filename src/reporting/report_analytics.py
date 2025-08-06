"""
Report Analytics and Trend Identification Service

This module provides comprehensive analytics and trend identification capabilities
for compliance monitoring reports, including statistical analysis, pattern recognition,
predictive insights, and performance metrics.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from collections import defaultdict, Counter
import pandas as pd
import numpy as np
from sqlalchemy import func, and_, or_, desc, case, extract
from sqlalchemy.orm import joinedload

from ..database.connection import get_db
from ..database.models import (
    FormChange, Form, Agency, Client, ClientFormUsage, 
    MonitoringRun, Notification, WorkItem, User, UserRole, Role
)

logger = logging.getLogger(__name__)


class TrendDirection:
    """Enum for trend directions."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    SEASONAL = "seasonal"


class AnalyticsPeriod:
    """Enum for analytics periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportAnalytics:
    """Comprehensive analytics and trend identification for compliance reports."""
    
    def __init__(self):
        self.min_data_points = 3  # Minimum data points for trend analysis
        
    def generate_comprehensive_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None,
        include_predictions: bool = True,
        include_anomalies: bool = True,
        include_correlations: bool = True
    ) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report with trends, patterns, and insights.
        
        Args:
            start_date: Start date for analysis period
            end_date: End date for analysis period
            agencies: Filter by specific agency IDs
            form_types: Filter by specific form types
            include_predictions: Include predictive analytics
            include_anomalies: Include anomaly detection
            include_correlations: Include correlation analysis
            
        Returns:
            Comprehensive analytics report
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=90)  # Default to 90 days
            
        logger.info(f"Generating comprehensive analytics from {start_date} to {end_date}")
        
        with get_db() as db:
            # Core analytics
            change_analytics = self._analyze_change_patterns(db, start_date, end_date, agencies, form_types)
            performance_analytics = self._analyze_performance_metrics(db, start_date, end_date, agencies)
            impact_analytics = self._analyze_impact_trends(db, start_date, end_date, agencies, form_types)
            
            # Advanced analytics
            trend_analysis = self._perform_trend_analysis(db, start_date, end_date, agencies, form_types)
            pattern_analysis = self._identify_patterns(db, start_date, end_date, agencies, form_types)
            
            # Optional advanced features
            predictions = {}
            if include_predictions:
                predictions = self._generate_predictions(db, start_date, end_date, agencies, form_types)
            
            anomalies = {}
            if include_anomalies:
                anomalies = self._detect_anomalies(db, start_date, end_date, agencies, form_types)
            
            correlations = {}
            if include_correlations:
                correlations = self._analyze_correlations(db, start_date, end_date, agencies, form_types)
            
            # Compile insights and recommendations
            insights = self._generate_insights(
                change_analytics, performance_analytics, impact_analytics,
                trend_analysis, pattern_analysis, predictions, anomalies, correlations
            )
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'duration_days': (end_date - start_date).days
                },
                'summary': self._generate_executive_summary(
                    change_analytics, performance_analytics, impact_analytics
                ),
                'change_analytics': change_analytics,
                'performance_analytics': performance_analytics,
                'impact_analytics': impact_analytics,
                'trend_analysis': trend_analysis,
                'pattern_analysis': pattern_analysis,
                'predictions': predictions,
                'anomalies': anomalies,
                'correlations': correlations,
                'insights': insights,
                'recommendations': self._generate_recommendations(insights),
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'data_points_analyzed': change_analytics.get('total_changes', 0),
                    'agencies_analyzed': len(change_analytics.get('agency_breakdown', {})),
                    'forms_analyzed': len(change_analytics.get('form_breakdown', {}))
                }
            }
    
    def _analyze_change_patterns(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze patterns in form changes."""
        # Build base query
        query = db.query(FormChange).filter(
            and_(
                FormChange.detected_at >= start_date,
                FormChange.detected_at <= end_date
            )
        )
        
        if agencies:
            query = query.join(Form).filter(Form.agency_id.in_(agencies))
        if form_types:
            query = query.join(Form).filter(Form.name.in_(form_types))
        
        changes = query.all()
        
        # Basic statistics
        total_changes = len(changes)
        if total_changes == 0:
            return {
                'total_changes': 0,
                'avg_changes_per_day': 0,
                'change_frequency': 'none',
                'severity_distribution': {},
                'type_distribution': {},
                'agency_breakdown': {},
                'form_breakdown': {},
                'temporal_patterns': {}
            }
        
        # Severity distribution
        severity_counts = Counter(change.severity for change in changes)
        severity_distribution = dict(severity_counts)
        
        # Change type distribution
        type_counts = Counter(change.change_type for change in changes)
        type_distribution = dict(type_counts)
        
        # Agency breakdown
        agency_breakdown = defaultdict(int)
        for change in changes:
            agency_name = change.form.agency.name
            agency_breakdown[agency_name] += 1
        
        # Form breakdown
        form_breakdown = defaultdict(int)
        for change in changes:
            form_name = change.form.name
            form_breakdown[form_name] += 1
        
        # Temporal patterns
        temporal_patterns = self._analyze_temporal_patterns(changes)
        
        # Calculate averages
        duration_days = (end_date - start_date).days
        avg_changes_per_day = total_changes / max(duration_days, 1)
        
        # Determine change frequency
        if avg_changes_per_day > 2:
            change_frequency = 'high'
        elif avg_changes_per_day > 0.5:
            change_frequency = 'moderate'
        else:
            change_frequency = 'low'
        
        return {
            'total_changes': total_changes,
            'avg_changes_per_day': round(avg_changes_per_day, 2),
            'change_frequency': change_frequency,
            'severity_distribution': severity_distribution,
            'type_distribution': type_distribution,
            'agency_breakdown': dict(agency_breakdown),
            'form_breakdown': dict(form_breakdown),
            'temporal_patterns': temporal_patterns
        }
    
    def _analyze_performance_metrics(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Analyze monitoring performance metrics."""
        # Build base query
        query = db.query(MonitoringRun).filter(
            and_(
                MonitoringRun.started_at >= start_date,
                MonitoringRun.started_at <= end_date
            )
        )
        
        if agencies:
            query = query.filter(MonitoringRun.agency_id.in_(agencies))
        
        runs = query.all()
        
        if not runs:
            return {
                'total_runs': 0,
                'success_rate': 0,
                'avg_response_time': 0,
                'performance_trend': 'stable',
                'error_analysis': {},
                'uptime_metrics': {}
            }
        
        # Success rate
        successful_runs = [run for run in runs if run.status == 'completed']
        success_rate = len(successful_runs) / len(runs) * 100
        
        # Response time analysis
        response_times = [run.response_time_ms for run in successful_runs if run.response_time_ms]
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        # Error analysis
        error_counts = Counter(run.status for run in runs if run.status != 'completed')
        error_analysis = dict(error_counts)
        
        # Performance trend
        performance_trend = self._calculate_performance_trend(runs)
        
        # Uptime metrics
        uptime_metrics = self._calculate_uptime_metrics(runs, start_date, end_date)
        
        return {
            'total_runs': len(runs),
            'successful_runs': len(successful_runs),
            'failed_runs': len(runs) - len(successful_runs),
            'success_rate': round(success_rate, 2),
            'avg_response_time': round(avg_response_time, 2),
            'performance_trend': performance_trend,
            'error_analysis': error_analysis,
            'uptime_metrics': uptime_metrics
        }
    
    def _analyze_impact_trends(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze impact trends of changes."""
        # Get changes with impact assessments
        query = db.query(FormChange).filter(
            and_(
                FormChange.detected_at >= start_date,
                FormChange.detected_at <= end_date,
                FormChange.impact_assessment.isnot(None)
            )
        )
        
        if agencies:
            query = query.join(Form).filter(Form.agency_id.in_(agencies))
        if form_types:
            query = query.join(Form).filter(Form.name.in_(form_types))
        
        changes_with_impact = query.all()
        
        if not changes_with_impact:
            return {
                'total_impacted_changes': 0,
                'avg_impact_score': 0,
                'impact_distribution': {},
                'client_impact_trends': {},
                'development_impact_trends': {}
            }
        
        # Analyze impact scores
        impact_scores = []
        impact_distribution = defaultdict(int)
        
        for change in changes_with_impact:
            impact_data = change.impact_assessment
            if isinstance(impact_data, dict):
                # Extract impact score from various possible locations
                score = (
                    impact_data.get('impact_score') or
                    impact_data.get('client_impact', {}).get('impact_score') or
                    impact_data.get('development_impact', {}).get('effort_score') or
                    5  # Default score
                )
                impact_scores.append(score)
                
                # Categorize impact
                if score >= 8:
                    impact_distribution['high'] += 1
                elif score >= 5:
                    impact_distribution['medium'] += 1
                else:
                    impact_distribution['low'] += 1
        
        avg_impact_score = statistics.mean(impact_scores) if impact_scores else 0
        
        # Client impact trends
        client_impact_trends = self._analyze_client_impact_trends(changes_with_impact)
        
        # Development impact trends
        development_impact_trends = self._analyze_development_impact_trends(changes_with_impact)
        
        return {
            'total_impacted_changes': len(changes_with_impact),
            'avg_impact_score': round(avg_impact_score, 2),
            'impact_distribution': dict(impact_distribution),
            'client_impact_trends': client_impact_trends,
            'development_impact_trends': development_impact_trends
        }
    
    def _perform_trend_analysis(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Perform comprehensive trend analysis."""
        # Get daily change counts
        daily_changes = self._get_daily_change_counts(db, start_date, end_date, agencies, form_types)
        
        if len(daily_changes) < self.min_data_points:
            return {
                'trend_direction': TrendDirection.STABLE,
                'trend_strength': 0,
                'trend_percentage': 0,
                'seasonality_detected': False,
                'volatility_score': 0,
                'trend_breakdown': {}
            }
        
        # Calculate trend metrics
        dates = list(daily_changes.keys())
        values = list(daily_changes.values())
        
        # Linear regression for trend
        trend_direction, trend_strength, trend_percentage = self._calculate_linear_trend(dates, values)
        
        # Detect seasonality
        seasonality_detected = self._detect_seasonality(values)
        
        # Calculate volatility
        volatility_score = self._calculate_volatility(values)
        
        # Trend breakdown by different metrics
        trend_breakdown = {
            'severity_trends': self._analyze_severity_trends(db, start_date, end_date, agencies, form_types),
            'agency_trends': self._analyze_agency_trends(db, start_date, end_date, agencies, form_types),
            'type_trends': self._analyze_type_trends(db, start_date, end_date, agencies, form_types)
        }
        
        return {
            'trend_direction': trend_direction,
            'trend_strength': round(trend_strength, 3),
            'trend_percentage': round(trend_percentage, 2),
            'seasonality_detected': seasonality_detected,
            'volatility_score': round(volatility_score, 3),
            'trend_breakdown': trend_breakdown,
            'daily_data': daily_changes
        }
    
    def _identify_patterns(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Identify patterns in the data."""
        changes = self._get_changes_for_period(db, start_date, end_date, agencies, form_types)
        
        if not changes:
            return {
                'temporal_patterns': {},
                'correlation_patterns': {},
                'sequential_patterns': {},
                'outlier_patterns': {}
            }
        
        return {
            'temporal_patterns': self._identify_temporal_patterns(changes),
            'correlation_patterns': self._identify_correlation_patterns(changes),
            'sequential_patterns': self._identify_sequential_patterns(changes),
            'outlier_patterns': self._identify_outlier_patterns(changes)
        }
    
    def _generate_predictions(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate predictions based on historical data."""
        # Get historical data
        daily_changes = self._get_daily_change_counts(db, start_date, end_date, agencies, form_types)
        
        if len(daily_changes) < self.min_data_points:
            return {
                'prediction_confidence': 'low',
                'predicted_changes_next_week': 0,
                'predicted_changes_next_month': 0,
                'prediction_factors': [],
                'confidence_intervals': {}
            }
        
        # Simple moving average prediction
        values = list(daily_changes.values())
        recent_avg = statistics.mean(values[-7:]) if len(values) >= 7 else statistics.mean(values)
        
        # Predict next week and month
        predicted_next_week = recent_avg * 7
        predicted_next_month = recent_avg * 30
        
        # Calculate confidence based on data consistency
        confidence = self._calculate_prediction_confidence(values)
        
        # Identify prediction factors
        prediction_factors = self._identify_prediction_factors(db, start_date, end_date, agencies, form_types)
        
        return {
            'prediction_confidence': confidence,
            'predicted_changes_next_week': round(predicted_next_week, 1),
            'predicted_changes_next_month': round(predicted_next_month, 1),
            'prediction_factors': prediction_factors,
            'confidence_intervals': {
                'next_week': {
                    'lower': round(predicted_next_week * 0.7, 1),
                    'upper': round(predicted_next_week * 1.3, 1)
                },
                'next_month': {
                    'lower': round(predicted_next_month * 0.7, 1),
                    'upper': round(predicted_next_month * 1.3, 1)
                }
            }
        }
    
    def _detect_anomalies(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Detect anomalies in the data."""
        daily_changes = self._get_daily_change_counts(db, start_date, end_date, agencies, form_types)
        
        if len(daily_changes) < self.min_data_points:
            return {
                'anomalies_detected': 0,
                'anomaly_dates': [],
                'anomaly_types': {},
                'anomaly_severity': {}
            }
        
        values = list(daily_changes.values())
        dates = list(daily_changes.keys())
        
        # Calculate statistical thresholds
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values) if len(values) > 1 else 0
        
        # Detect anomalies (values beyond 2 standard deviations)
        anomalies = []
        anomaly_types = defaultdict(int)
        anomaly_severity = defaultdict(int)
        
        for i, value in enumerate(values):
            if std_val > 0:
                z_score = abs(value - mean_val) / std_val
                if z_score > 2:
                    anomaly_date = dates[i]
                    anomalies.append({
                        'date': anomaly_date,
                        'value': value,
                        'z_score': round(z_score, 2),
                        'expected_range': f"{round(mean_val - 2*std_val, 1)} - {round(mean_val + 2*std_val, 1)}"
                    })
                    
                    # Categorize anomaly
                    if value > mean_val + 2*std_val:
                        anomaly_types['spike'] += 1
                        anomaly_severity['high'] += 1
                    else:
                        anomaly_types['drop'] += 1
                        anomaly_severity['medium'] += 1
        
        return {
            'anomalies_detected': len(anomalies),
            'anomaly_dates': [a['date'] for a in anomalies],
            'anomaly_details': anomalies,
            'anomaly_types': dict(anomaly_types),
            'anomaly_severity': dict(anomaly_severity)
        }
    
    def _analyze_correlations(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Analyze correlations between different metrics."""
        # Get data for correlation analysis
        changes = self._get_changes_for_period(db, start_date, end_date, agencies, form_types)
        
        if len(changes) < 10:  # Need sufficient data for correlation
            return {
                'correlation_matrix': {},
                'strong_correlations': [],
                'correlation_insights': []
            }
        
        # Prepare data for correlation analysis
        correlation_data = self._prepare_correlation_data(changes)
        
        # Calculate correlations
        correlation_matrix = self._calculate_correlation_matrix(correlation_data)
        
        # Identify strong correlations
        strong_correlations = self._identify_strong_correlations(correlation_matrix)
        
        # Generate correlation insights
        correlation_insights = self._generate_correlation_insights(strong_correlations)
        
        return {
            'correlation_matrix': correlation_matrix,
            'strong_correlations': strong_correlations,
            'correlation_insights': correlation_insights
        }
    
    # Helper methods for analytics calculations
    def _analyze_temporal_patterns(self, changes: List[FormChange]) -> Dict[str, Any]:
        """Analyze temporal patterns in changes."""
        # Day of week analysis
        day_counts = defaultdict(int)
        hour_counts = defaultdict(int)
        month_counts = defaultdict(int)
        
        for change in changes:
            day_counts[change.detected_at.strftime('%A')] += 1
            hour_counts[change.detected_at.hour] += 1
            month_counts[change.detected_at.strftime('%B')] += 1
        
        return {
            'day_of_week_distribution': dict(day_counts),
            'hour_of_day_distribution': dict(hour_counts),
            'month_distribution': dict(month_counts),
            'peak_hours': sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:3],
            'peak_days': sorted(day_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        }
    
    def _calculate_performance_trend(self, runs: List[MonitoringRun]) -> str:
        """Calculate performance trend from monitoring runs."""
        if len(runs) < 7:
            return 'stable'
        
        # Group by week and calculate success rates
        weekly_success_rates = defaultdict(list)
        for run in runs:
            week_start = run.started_at - timedelta(days=run.started_at.weekday())
            week_key = week_start.strftime('%Y-%W')
            if run.status == 'completed':
                weekly_success_rates[week_key].append(1)
            else:
                weekly_success_rates[week_key].append(0)
        
        # Calculate average success rate per week
        weekly_avgs = []
        for week_rates in weekly_success_rates.values():
            if week_rates:
                weekly_avgs.append(statistics.mean(week_rates))
        
        if len(weekly_avgs) < 2:
            return 'stable'
        
        # Determine trend
        first_half = weekly_avgs[:len(weekly_avgs)//2]
        second_half = weekly_avgs[len(weekly_avgs)//2:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        if second_avg > first_avg * 1.05:
            return 'improving'
        elif second_avg < first_avg * 0.95:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_uptime_metrics(self, runs: List[MonitoringRun], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Calculate uptime metrics."""
        total_duration = (end_date - start_date).total_seconds()
        successful_duration = 0
        
        for run in runs:
            if run.status == 'completed' and run.completed_at:
                run_duration = (run.completed_at - run.started_at).total_seconds()
                successful_duration += run_duration
        
        uptime_percentage = (successful_duration / total_duration * 100) if total_duration > 0 else 0
        
        return {
            'uptime_percentage': round(uptime_percentage, 2),
            'total_duration_hours': round(total_duration / 3600, 2),
            'successful_duration_hours': round(successful_duration / 3600, 2)
        }
    
    def _get_daily_change_counts(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Get daily change counts for trend analysis."""
        query = db.query(
            func.date(FormChange.detected_at).label('date'),
            func.count(FormChange.id).label('count')
        ).filter(
            and_(
                FormChange.detected_at >= start_date,
                FormChange.detected_at <= end_date
            )
        )
        
        if agencies:
            query = query.join(Form).filter(Form.agency_id.in_(agencies))
        if form_types:
            query = query.join(Form).filter(Form.name.in_(form_types))
        
        results = query.group_by(func.date(FormChange.detected_at)).order_by(func.date(FormChange.detected_at)).all()
        
        return {str(result.date): result.count for result in results}
    
    def _calculate_linear_trend(self, dates: List[str], values: List[int]) -> Tuple[str, float, float]:
        """Calculate linear trend using simple linear regression."""
        if len(values) < 2:
            return TrendDirection.STABLE, 0, 0
        
        # Convert dates to numeric values for regression
        x_values = list(range(len(values)))
        
        # Simple linear regression
        n = len(values)
        sum_x = sum(x_values)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(x_values, values))
        sum_x2 = sum(x * x for x in x_values)
        
        # Calculate slope and intercept
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x) if (n * sum_x2 - sum_x * sum_x) != 0 else 0
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate trend percentage
        if sum_y > 0:
            trend_percentage = (slope * n / sum_y) * 100
        else:
            trend_percentage = 0
        
        # Determine trend direction
        if abs(slope) < 0.1:
            trend_direction = TrendDirection.STABLE
        elif slope > 0:
            trend_direction = TrendDirection.INCREASING
        else:
            trend_direction = TrendDirection.DECREASING
        
        return trend_direction, abs(slope), trend_percentage
    
    def _detect_seasonality(self, values: List[int]) -> bool:
        """Detect seasonality in the data."""
        if len(values) < 14:  # Need at least 2 weeks of data
            return False
        
        # Simple seasonality detection using autocorrelation
        # Check if there's a weekly pattern
        weekly_patterns = []
        for i in range(7, len(values)):
            if i >= 7:
                weekly_patterns.append(values[i] - values[i-7])
        
        if weekly_patterns:
            # Calculate variance of weekly differences
            variance = statistics.variance(weekly_patterns) if len(weekly_patterns) > 1 else 0
            total_variance = statistics.variance(values) if len(values) > 1 else 0
            
            # If weekly variance is low compared to total variance, there's seasonality
            return variance < total_variance * 0.5
        
        return False
    
    def _calculate_volatility(self, values: List[int]) -> float:
        """Calculate volatility score."""
        if len(values) < 2:
            return 0
        
        # Calculate coefficient of variation
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        
        return (std_val / mean_val) if mean_val > 0 else 0
    
    def _calculate_prediction_confidence(self, values: List[int]) -> str:
        """Calculate prediction confidence based on data consistency."""
        if len(values) < 3:
            return 'low'
        
        # Calculate coefficient of variation
        mean_val = statistics.mean(values)
        std_val = statistics.stdev(values)
        cv = (std_val / mean_val) if mean_val > 0 else 1
        
        if cv < 0.3:
            return 'high'
        elif cv < 0.6:
            return 'medium'
        else:
            return 'low'
    
    def _get_changes_for_period(
        self, 
        db, 
        start_date: datetime, 
        end_date: datetime, 
        agencies: Optional[List[int]] = None,
        form_types: Optional[List[str]] = None
    ) -> List[FormChange]:
        """Get form changes for the specified period."""
        query = db.query(FormChange).filter(
            and_(
                FormChange.detected_at >= start_date,
                FormChange.detected_at <= end_date
            )
        )
        
        if agencies:
            query = query.join(Form).filter(Form.agency_id.in_(agencies))
        if form_types:
            query = query.join(Form).filter(Form.name.in_(form_types))
        
        return query.all()
    
    def _generate_insights(
        self, 
        change_analytics: Dict, 
        performance_analytics: Dict, 
        impact_analytics: Dict,
        trend_analysis: Dict, 
        pattern_analysis: Dict, 
        predictions: Dict, 
        anomalies: Dict, 
        correlations: Dict
    ) -> List[str]:
        """Generate insights from analytics data."""
        insights = []
        
        # Change pattern insights
        if change_analytics.get('total_changes', 0) > 0:
            change_frequency = change_analytics.get('change_frequency', 'low')
            if change_frequency == 'high':
                insights.append("High change frequency detected - consider increasing monitoring resources")
            elif change_frequency == 'low':
                insights.append("Low change frequency - verify monitoring is functioning correctly")
        
        # Performance insights
        success_rate = performance_analytics.get('success_rate', 0)
        if success_rate < 95:
            insights.append(f"Monitoring success rate ({success_rate}%) below target - investigate failures")
        
        # Trend insights
        trend_direction = trend_analysis.get('trend_direction', TrendDirection.STABLE)
        if trend_direction == TrendDirection.INCREASING:
            insights.append("Increasing trend in changes detected - prepare for higher workload")
        elif trend_direction == TrendDirection.DECREASING:
            insights.append("Decreasing trend in changes - may indicate improved stability")
        
        # Anomaly insights
        anomalies_detected = anomalies.get('anomalies_detected', 0)
        if anomalies_detected > 0:
            insights.append(f"{anomalies_detected} anomalies detected - review for potential issues")
        
        # Impact insights
        avg_impact = impact_analytics.get('avg_impact_score', 0)
        if avg_impact > 7:
            insights.append("High average impact score - prioritize critical changes")
        
        return insights
    
    def _generate_recommendations(self, insights: List[str]) -> List[str]:
        """Generate actionable recommendations based on insights."""
        recommendations = []
        
        for insight in insights:
            if "high change frequency" in insight.lower():
                recommendations.append("Implement automated change classification to prioritize critical changes")
                recommendations.append("Consider increasing monitoring frequency for high-change agencies")
            elif "success rate" in insight.lower():
                recommendations.append("Review monitoring error logs and implement retry mechanisms")
                recommendations.append("Optimize monitoring schedules to reduce load during peak times")
            elif "increasing trend" in insight.lower():
                recommendations.append("Scale up development resources to handle increased change volume")
                recommendations.append("Implement automated impact assessment to speed up evaluation")
            elif "anomalies detected" in insight.lower():
                recommendations.append("Investigate anomaly causes and implement early warning systems")
            elif "high average impact" in insight.lower():
                recommendations.append("Establish rapid response procedures for high-impact changes")
                recommendations.append("Implement automated client impact notifications")
        
        return list(set(recommendations))  # Remove duplicates
    
    def _generate_executive_summary(
        self, 
        change_analytics: Dict, 
        performance_analytics: Dict, 
        impact_analytics: Dict
    ) -> Dict[str, Any]:
        """Generate executive summary of analytics."""
        total_changes = change_analytics.get('total_changes', 0)
        success_rate = performance_analytics.get('success_rate', 0)
        avg_impact = impact_analytics.get('avg_impact_score', 0)
        
        # Determine overall health score
        health_score = 0
        if success_rate >= 95:
            health_score += 40
        elif success_rate >= 90:
            health_score += 30
        elif success_rate >= 80:
            health_score += 20
        
        if total_changes > 0:
            if avg_impact <= 5:
                health_score += 30
            elif avg_impact <= 7:
                health_score += 20
            else:
                health_score += 10
        
        if change_analytics.get('change_frequency') == 'moderate':
            health_score += 30
        elif change_analytics.get('change_frequency') == 'low':
            health_score += 20
        
        return {
            'total_changes': total_changes,
            'monitoring_success_rate': success_rate,
            'average_impact_score': avg_impact,
            'system_health_score': min(100, health_score),
            'key_metrics': {
                'changes_per_day': change_analytics.get('avg_changes_per_day', 0),
                'critical_changes': change_analytics.get('severity_distribution', {}).get('critical', 0),
                'uptime_percentage': performance_analytics.get('uptime_metrics', {}).get('uptime_percentage', 0)
            }
        }
    
    # Additional helper methods for specific analytics
    def _analyze_severity_trends(self, db, start_date, end_date, agencies, form_types):
        """Analyze trends by severity level."""
        # Implementation for severity trend analysis
        return {}
    
    def _analyze_agency_trends(self, db, start_date, end_date, agencies, form_types):
        """Analyze trends by agency."""
        # Implementation for agency trend analysis
        return {}
    
    def _analyze_type_trends(self, db, start_date, end_date, agencies, form_types):
        """Analyze trends by change type."""
        # Implementation for change type trend analysis
        return {}
    
    def _identify_temporal_patterns(self, changes):
        """Identify temporal patterns in changes."""
        # Implementation for temporal pattern identification
        return {}
    
    def _identify_correlation_patterns(self, changes):
        """Identify correlation patterns in changes."""
        # Implementation for correlation pattern identification
        return {}
    
    def _identify_sequential_patterns(self, changes):
        """Identify sequential patterns in changes."""
        # Implementation for sequential pattern identification
        return {}
    
    def _identify_outlier_patterns(self, changes):
        """Identify outlier patterns in changes."""
        # Implementation for outlier pattern identification
        return {}
    
    def _analyze_client_impact_trends(self, changes):
        """Analyze client impact trends."""
        # Implementation for client impact trend analysis
        return {}
    
    def _analyze_development_impact_trends(self, changes):
        """Analyze development impact trends."""
        # Implementation for development impact trend analysis
        return {}
    
    def _identify_prediction_factors(self, db, start_date, end_date, agencies, form_types):
        """Identify factors that influence predictions."""
        # Implementation for prediction factor identification
        return []
    
    def _prepare_correlation_data(self, changes):
        """Prepare data for correlation analysis."""
        # Implementation for correlation data preparation
        return {}
    
    def _calculate_correlation_matrix(self, data):
        """Calculate correlation matrix."""
        # Implementation for correlation matrix calculation
        return {}
    
    def _identify_strong_correlations(self, matrix):
        """Identify strong correlations in the matrix."""
        # Implementation for strong correlation identification
        return []
    
    def _generate_correlation_insights(self, correlations):
        """Generate insights from correlations."""
        # Implementation for correlation insight generation
        return []


# Global analytics instance and convenience functions
_analytics = None

def get_analytics() -> ReportAnalytics:
    """Get the global analytics instance."""
    global _analytics
    if _analytics is None:
        _analytics = ReportAnalytics()
    return _analytics

def generate_analytics_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    agencies: Optional[List[int]] = None,
    form_types: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to generate analytics report."""
    analytics = get_analytics()
    return analytics.generate_comprehensive_analytics(
        start_date, end_date, agencies, form_types, **kwargs
    ) 