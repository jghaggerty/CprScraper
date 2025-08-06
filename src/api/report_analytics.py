"""
Report Analytics API Endpoints

This module provides REST API endpoints for comprehensive report analytics
and trend identification, including statistical analysis, pattern recognition,
predictive insights, and performance metrics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from enum import Enum

from ..reporting.report_analytics import (
    ReportAnalytics, TrendDirection, AnalyticsPeriod,
    get_analytics, generate_analytics_report
)
from ..auth.auth import get_current_user
from ..database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/analytics", tags=["Report Analytics"])

# Pydantic Models
class TrendDirectionEnum(str, Enum):
    """Enum for trend directions."""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    VOLATILE = "volatile"
    SEASONAL = "seasonal"

class AnalyticsPeriodEnum(str, Enum):
    """Enum for analytics periods."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class AnalyticsRequest(BaseModel):
    """Request model for analytics generation."""
    start_date: Optional[datetime] = Field(None, description="Start date for analysis period")
    end_date: Optional[datetime] = Field(None, description="End date for analysis period")
    agencies: Optional[List[int]] = Field(None, description="Filter by specific agency IDs")
    form_types: Optional[List[str]] = Field(None, description="Filter by specific form types")
    include_predictions: bool = Field(True, description="Include predictive analytics")
    include_anomalies: bool = Field(True, description="Include anomaly detection")
    include_correlations: bool = Field(True, description="Include correlation analysis")

class AnalyticsSummary(BaseModel):
    """Summary of analytics results."""
    total_changes: int
    monitoring_success_rate: float
    average_impact_score: float
    system_health_score: int
    key_metrics: Dict[str, Any]

class TrendAnalysis(BaseModel):
    """Trend analysis results."""
    trend_direction: TrendDirectionEnum
    trend_strength: float
    trend_percentage: float
    seasonality_detected: bool
    volatility_score: float
    daily_data: Dict[str, int]

class ChangeAnalytics(BaseModel):
    """Change pattern analytics."""
    total_changes: int
    avg_changes_per_day: float
    change_frequency: str
    severity_distribution: Dict[str, int]
    type_distribution: Dict[str, int]
    agency_breakdown: Dict[str, int]
    form_breakdown: Dict[str, int]
    temporal_patterns: Dict[str, Any]

class PerformanceAnalytics(BaseModel):
    """Performance metrics analytics."""
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float
    avg_response_time: float
    performance_trend: str
    error_analysis: Dict[str, int]
    uptime_metrics: Dict[str, Any]

class ImpactAnalytics(BaseModel):
    """Impact trends analytics."""
    total_impacted_changes: int
    avg_impact_score: float
    impact_distribution: Dict[str, int]
    client_impact_trends: Dict[str, Any]
    development_impact_trends: Dict[str, Any]

class PredictionResults(BaseModel):
    """Prediction results."""
    prediction_confidence: str
    predicted_changes_next_week: float
    predicted_changes_next_month: float
    prediction_factors: List[str]
    confidence_intervals: Dict[str, Dict[str, float]]

class AnomalyResults(BaseModel):
    """Anomaly detection results."""
    anomalies_detected: int
    anomaly_dates: List[str]
    anomaly_details: List[Dict[str, Any]]
    anomaly_types: Dict[str, int]
    anomaly_severity: Dict[str, int]

class CorrelationResults(BaseModel):
    """Correlation analysis results."""
    correlation_matrix: Dict[str, Any]
    strong_correlations: List[Dict[str, Any]]
    correlation_insights: List[str]

class AnalyticsResponse(BaseModel):
    """Complete analytics response."""
    period: Dict[str, Any]
    summary: AnalyticsSummary
    change_analytics: ChangeAnalytics
    performance_analytics: PerformanceAnalytics
    impact_analytics: ImpactAnalytics
    trend_analysis: TrendAnalysis
    pattern_analysis: Dict[str, Any]
    predictions: PredictionResults
    anomalies: AnomalyResults
    correlations: CorrelationResults
    insights: List[str]
    recommendations: List[str]
    metadata: Dict[str, Any]

class QuickAnalyticsRequest(BaseModel):
    """Request model for quick analytics."""
    period_days: int = Field(30, description="Number of days to analyze", ge=1, le=365)
    agencies: Optional[List[int]] = Field(None, description="Filter by specific agency IDs")
    form_types: Optional[List[str]] = Field(None, description="Filter by specific form types")

class QuickAnalyticsResponse(BaseModel):
    """Quick analytics response."""
    period: Dict[str, Any]
    summary: AnalyticsSummary
    trend_direction: TrendDirectionEnum
    key_insights: List[str]
    recommendations: List[str]

class TrendComparisonRequest(BaseModel):
    """Request model for trend comparison."""
    period1_start: datetime
    period1_end: datetime
    period2_start: datetime
    period2_end: datetime
    agencies: Optional[List[int]] = Field(None, description="Filter by specific agency IDs")
    form_types: Optional[List[str]] = Field(None, description="Filter by specific form types")

class TrendComparisonResponse(BaseModel):
    """Trend comparison response."""
    period1: Dict[str, Any]
    period2: Dict[str, Any]
    comparison: Dict[str, Any]
    changes: Dict[str, Any]
    insights: List[str]

# API Endpoints
@router.post("/comprehensive", response_model=AnalyticsResponse)
async def generate_comprehensive_analytics(
    request: AnalyticsRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive analytics report with trends, patterns, and insights."""
    try:
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=request.start_date,
            end_date=request.end_date,
            agencies=request.agencies,
            form_types=request.form_types,
            include_predictions=request.include_predictions,
            include_anomalies=request.include_anomalies,
            include_correlations=request.include_correlations
        )
        
        logger.info(f"Generated comprehensive analytics for user {current_user.id}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating comprehensive analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {str(e)}")

@router.post("/quick", response_model=QuickAnalyticsResponse)
async def generate_quick_analytics(
    request: QuickAnalyticsRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate quick analytics summary for recent period."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=request.period_days)
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=request.agencies,
            form_types=request.form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        # Extract key insights for quick view
        key_insights = result.get('insights', [])[:5]  # Top 5 insights
        recommendations = result.get('recommendations', [])[:3]  # Top 3 recommendations
        
        return QuickAnalyticsResponse(
            period=result['period'],
            summary=result['summary'],
            trend_direction=result['trend_analysis']['trend_direction'],
            key_insights=key_insights,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"Error generating quick analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quick analytics: {str(e)}")

@router.post("/trend-comparison", response_model=TrendComparisonResponse)
async def compare_trends(
    request: TrendComparisonRequest,
    current_user: User = Depends(get_current_user)
):
    """Compare trends between two different periods."""
    try:
        analytics = get_analytics()
        
        # Generate analytics for both periods
        period1_result = analytics.generate_comprehensive_analytics(
            start_date=request.period1_start,
            end_date=request.period1_end,
            agencies=request.agencies,
            form_types=request.form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        period2_result = analytics.generate_comprehensive_analytics(
            start_date=request.period2_start,
            end_date=request.period2_end,
            agencies=request.agencies,
            form_types=request.form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        # Calculate comparisons
        comparison = _calculate_period_comparison(period1_result, period2_result)
        changes = _calculate_changes_between_periods(period1_result, period2_result)
        insights = _generate_comparison_insights(comparison, changes)
        
        return TrendComparisonResponse(
            period1=period1_result['period'],
            period2=period2_result['period'],
            comparison=comparison,
            changes=changes,
            insights=insights
        )
        
    except Exception as e:
        logger.error(f"Error comparing trends: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compare trends: {str(e)}")

@router.get("/trends/{period}", response_model=Dict[str, Any])
async def get_trends_by_period(
    period: AnalyticsPeriodEnum,
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get trend analysis for a specific period."""
    try:
        # Calculate date range based on period
        end_date = datetime.now()
        if period == AnalyticsPeriodEnum.DAILY:
            start_date = end_date - timedelta(days=7)
        elif period == AnalyticsPeriodEnum.WEEKLY:
            start_date = end_date - timedelta(weeks=8)
        elif period == AnalyticsPeriodEnum.MONTHLY:
            start_date = end_date - timedelta(days=90)
        elif period == AnalyticsPeriodEnum.QUARTERLY:
            start_date = end_date - timedelta(days=270)
        else:  # YEARLY
            start_date = end_date - timedelta(days=365)
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        return {
            'period': result['period'],
            'trend_analysis': result['trend_analysis'],
            'change_analytics': result['change_analytics'],
            'summary': result['summary']
        }
        
    except Exception as e:
        logger.error(f"Error getting trends for period {period}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")

@router.get("/predictions", response_model=PredictionResults)
async def get_predictions(
    days_ahead: int = Query(30, description="Number of days to predict", ge=1, le=90),
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get predictions for future changes."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # Use 90 days of historical data
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=True,
            include_anomalies=False,
            include_correlations=False
        )
        
        return result['predictions']
        
    except Exception as e:
        logger.error(f"Error getting predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get predictions: {str(e)}")

@router.get("/anomalies", response_model=AnomalyResults)
async def get_anomalies(
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get anomaly detection results."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # Use 90 days of data
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=True,
            include_correlations=False
        )
        
        return result['anomalies']
        
    except Exception as e:
        logger.error(f"Error getting anomalies: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get anomalies: {str(e)}")

@router.get("/correlations", response_model=CorrelationResults)
async def get_correlations(
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get correlation analysis results."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)  # Use 90 days of data
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=True
        )
        
        return result['correlations']
        
    except Exception as e:
        logger.error(f"Error getting correlations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get correlations: {str(e)}")

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get analytics summary for recent period."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        return result['summary']
        
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics summary: {str(e)}")

@router.get("/insights", response_model=List[str])
async def get_analytics_insights(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get key insights from analytics."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        return result['insights']
        
    except Exception as e:
        logger.error(f"Error getting analytics insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics insights: {str(e)}")

@router.get("/recommendations", response_model=List[str])
async def get_analytics_recommendations(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get actionable recommendations from analytics."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        return result['recommendations']
        
    except Exception as e:
        logger.error(f"Error getting analytics recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get analytics recommendations: {str(e)}")

@router.get("/health-score", response_model=Dict[str, Any])
async def get_system_health_score(
    days: int = Query(30, description="Number of days to analyze", ge=1, le=365),
    agencies: Optional[List[int]] = Query(None, description="Filter by specific agency IDs"),
    form_types: Optional[List[str]] = Query(None, description="Filter by specific form types"),
    current_user: User = Depends(get_current_user)
):
    """Get system health score and breakdown."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        analytics = get_analytics()
        result = analytics.generate_comprehensive_analytics(
            start_date=start_date,
            end_date=end_date,
            agencies=agencies,
            form_types=form_types,
            include_predictions=False,
            include_anomalies=False,
            include_correlations=False
        )
        
        summary = result['summary']
        
        # Calculate health score breakdown
        health_breakdown = {
            'overall_score': summary['system_health_score'],
            'performance_score': _calculate_performance_score(summary),
            'change_management_score': _calculate_change_management_score(summary),
            'impact_management_score': _calculate_impact_management_score(summary),
            'recommendations': result['recommendations'][:3]  # Top 3 recommendations
        }
        
        return health_breakdown
        
    except Exception as e:
        logger.error(f"Error getting health score: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get health score: {str(e)}")

# Helper functions for comparison and scoring
def _calculate_period_comparison(period1_result: Dict, period2_result: Dict) -> Dict[str, Any]:
    """Calculate comparison between two periods."""
    p1_summary = period1_result['summary']
    p2_summary = period2_result['summary']
    
    return {
        'total_changes_change': p2_summary['total_changes'] - p1_summary['total_changes'],
        'success_rate_change': p2_summary['monitoring_success_rate'] - p1_summary['monitoring_success_rate'],
        'impact_score_change': p2_summary['average_impact_score'] - p1_summary['average_impact_score'],
        'health_score_change': p2_summary['system_health_score'] - p1_summary['system_health_score'],
        'period1_duration': period1_result['period']['duration_days'],
        'period2_duration': period2_result['period']['duration_days']
    }

def _calculate_changes_between_periods(period1_result: Dict, period2_result: Dict) -> Dict[str, Any]:
    """Calculate changes between two periods."""
    p1_changes = period1_result['change_analytics']
    p2_changes = period2_result['change_analytics']
    
    return {
        'frequency_change': p2_changes['change_frequency'] != p1_changes['change_frequency'],
        'severity_distribution_change': _compare_distributions(
            p1_changes['severity_distribution'], 
            p2_changes['severity_distribution']
        ),
        'agency_distribution_change': _compare_distributions(
            p1_changes['agency_breakdown'], 
            p2_changes['agency_breakdown']
        )
    }

def _compare_distributions(dist1: Dict[str, int], dist2: Dict[str, int]) -> Dict[str, Any]:
    """Compare two distributions."""
    all_keys = set(dist1.keys()) | set(dist2.keys())
    changes = {}
    
    for key in all_keys:
        val1 = dist1.get(key, 0)
        val2 = dist2.get(key, 0)
        if val1 != val2:
            changes[key] = {
                'from': val1,
                'to': val2,
                'change': val2 - val1,
                'percentage_change': ((val2 - val1) / val1 * 100) if val1 > 0 else 0
            }
    
    return changes

def _generate_comparison_insights(comparison: Dict, changes: Dict) -> List[str]:
    """Generate insights from period comparison."""
    insights = []
    
    # Health score insights
    health_change = comparison.get('health_score_change', 0)
    if health_change > 10:
        insights.append("Significant improvement in system health score")
    elif health_change < -10:
        insights.append("Significant decline in system health score")
    
    # Success rate insights
    success_change = comparison.get('success_rate_change', 0)
    if success_change > 5:
        insights.append("Monitoring success rate improved significantly")
    elif success_change < -5:
        insights.append("Monitoring success rate declined - investigate issues")
    
    # Change frequency insights
    if changes.get('frequency_change', False):
        insights.append("Change frequency pattern has shifted between periods")
    
    return insights

def _calculate_performance_score(summary: Dict) -> int:
    """Calculate performance component of health score."""
    success_rate = summary.get('monitoring_success_rate', 0)
    if success_rate >= 95:
        return 40
    elif success_rate >= 90:
        return 30
    elif success_rate >= 80:
        return 20
    else:
        return 10

def _calculate_change_management_score(summary: Dict) -> int:
    """Calculate change management component of health score."""
    total_changes = summary.get('total_changes', 0)
    changes_per_day = summary.get('key_metrics', {}).get('changes_per_day', 0)
    
    if total_changes == 0:
        return 30  # No changes might indicate stable system
    elif changes_per_day <= 1:
        return 30
    elif changes_per_day <= 3:
        return 20
    else:
        return 10

def _calculate_impact_management_score(summary: Dict) -> int:
    """Calculate impact management component of health score."""
    avg_impact = summary.get('average_impact_score', 0)
    critical_changes = summary.get('key_metrics', {}).get('critical_changes', 0)
    
    if avg_impact <= 5 and critical_changes <= 2:
        return 30
    elif avg_impact <= 7 and critical_changes <= 5:
        return 20
    else:
        return 10 