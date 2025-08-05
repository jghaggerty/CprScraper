"""
Consolidated Report Templates for Weekly Compliance Reports

This module provides comprehensive report templates for displaying all compliance changes
in a well-structured, professional format suitable for different audiences.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from jinja2 import Template

logger = logging.getLogger(__name__)


class ReportTemplateManager:
    """Manage and render different types of report templates."""
    
    def __init__(self):
        self.templates = {
            'executive_summary': self._get_executive_summary_template(),
            'detailed_report': self._get_detailed_report_template(),
            'technical_report': self._get_technical_report_template(),
            'dashboard_report': self._get_dashboard_report_template(),
            'email_summary': self._get_email_summary_template()
        }
    
    def get_template(self, template_type: str = 'detailed_report') -> Template:
        """Get a specific report template."""
        return self.templates.get(template_type, self.templates['detailed_report'])
    
    def render_report(
        self,
        report_data: Dict[str, Any],
        template_type: str = 'detailed_report',
        include_charts: bool = True
    ) -> str:
        """
        Render a complete report using the specified template.
        
        Args:
            report_data: Report data from WeeklyReportGenerator
            template_type: Type of template to use
            include_charts: Whether to include chart placeholders
            
        Returns:
            Rendered HTML report
        """
        template = self.get_template(template_type)
        
        # Prepare template context
        context = self._prepare_template_context(report_data, include_charts)
        
        return template.render(**context)
    
    def _prepare_template_context(self, report_data: Dict[str, Any], include_charts: bool) -> Dict[str, Any]:
        """Prepare context data for template rendering."""
        metadata = report_data.get('report_metadata', {})
        executive_summary = report_data.get('executive_summary', {})
        form_changes = report_data.get('form_changes', [])
        impact_assessments = report_data.get('impact_assessments', [])
        monitoring_stats = report_data.get('monitoring_statistics', {})
        notification_summary = report_data.get('notification_summary', {})
        trend_analysis = report_data.get('trend_analysis', {})
        recommendations = report_data.get('recommendations', [])
        
        # Group form changes by severity
        changes_by_severity = self._group_changes_by_severity(form_changes)
        
        # Group form changes by agency
        changes_by_agency = self._group_changes_by_agency(form_changes)
        
        # Calculate summary statistics
        summary_stats = self._calculate_summary_statistics(
            form_changes, monitoring_stats, notification_summary
        )
        
        return {
            'metadata': metadata,
            'executive_summary': executive_summary,
            'form_changes': form_changes,
            'impact_assessments': impact_assessments,
            'monitoring_stats': monitoring_stats,
            'notification_summary': notification_summary,
            'trend_analysis': trend_analysis,
            'recommendations': recommendations,
            'changes_by_severity': changes_by_severity,
            'changes_by_agency': changes_by_agency,
            'summary_stats': summary_stats,
            'include_charts': include_charts,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
    
    def _group_changes_by_severity(self, form_changes: List[Dict]) -> Dict[str, List[Dict]]:
        """Group form changes by severity level."""
        grouped = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }
        
        for change in form_changes:
            severity = change.get('severity', 'medium')
            if severity in grouped:
                grouped[severity].append(change)
        
        return grouped
    
    def _group_changes_by_agency(self, form_changes: List[Dict]) -> Dict[str, List[Dict]]:
        """Group form changes by agency."""
        grouped = {}
        
        for change in form_changes:
            agency = change.get('agency_name', 'Unknown Agency')
            if agency not in grouped:
                grouped[agency] = []
            grouped[agency].append(change)
        
        return grouped
    
    def _calculate_summary_statistics(
        self,
        form_changes: List[Dict],
        monitoring_stats: Optional[Dict],
        notification_summary: Optional[Dict]
    ) -> Dict[str, Any]:
        """Calculate comprehensive summary statistics."""
        total_changes = len(form_changes)
        
        # Severity breakdown
        severity_counts = {}
        for change in form_changes:
            severity = change.get('severity', 'medium')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Agency breakdown
        agency_counts = {}
        for change in form_changes:
            agency = change.get('agency_name', 'Unknown')
            agency_counts[agency] = agency_counts.get(agency, 0) + 1
        
        # Change type breakdown
        change_type_counts = {}
        for change in form_changes:
            change_type = change.get('change_type', 'unknown')
            change_type_counts[change_type] = change_type_counts.get(change_type, 0) + 1
        
        # AI analysis statistics
        ai_confidence_scores = [
            change.get('ai_confidence_score', 0) 
            for change in form_changes 
            if change.get('ai_confidence_score') is not None
        ]
        
        avg_ai_confidence = sum(ai_confidence_scores) / len(ai_confidence_scores) if ai_confidence_scores else 0
        
        return {
            'total_changes': total_changes,
            'severity_counts': severity_counts,
            'agency_counts': agency_counts,
            'change_type_counts': change_type_counts,
            'avg_ai_confidence': round(avg_ai_confidence, 1),
            'monitoring_success_rate': monitoring_stats.get('success_rate', 0) if monitoring_stats else 0,
            'notification_delivery_rate': notification_summary.get('delivery_rate', 0) if notification_summary else 0
        }
    
    def _get_executive_summary_template(self) -> Template:
        """Get executive summary template."""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executive Summary - Compliance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #2c3e50; margin: 0; font-size: 2.5em; }
        .header .subtitle { color: #7f8c8d; font-size: 1.2em; margin-top: 10px; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .summary-card { background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; }
        .summary-card h3 { margin: 0 0 10px 0; color: #2c3e50; }
        .summary-card .number { font-size: 2.5em; font-weight: bold; color: #e74c3c; }
        .summary-card .label { color: #7f8c8d; font-size: 0.9em; }
        .critical { color: #e74c3c !important; }
        .high { color: #f39c12 !important; }
        .medium { color: #f1c40f !important; }
        .low { color: #27ae60 !important; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .recommendations { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; }
        .recommendations h3 { color: #856404; margin-top: 0; }
        .recommendations ul { margin: 0; padding-left: 20px; }
        .recommendations li { margin-bottom: 10px; color: #856404; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Executive Summary</h1>
            <div class="subtitle">Compliance Monitoring Report</div>
            <div class="subtitle">{{ metadata.report_period }}</div>
            <div class="subtitle">Generated: {{ generated_at }}</div>
        </div>
        
        <div class="summary-grid">
            <div class="summary-card">
                <h3>Total Changes</h3>
                <div class="number">{{ summary_stats.total_changes }}</div>
                <div class="label">Detected Changes</div>
            </div>
            <div class="summary-card">
                <h3>Critical Changes</h3>
                <div class="number critical">{{ summary_stats.severity_counts.critical|default(0) }}</div>
                <div class="label">Require Immediate Attention</div>
            </div>
            <div class="summary-card">
                <h3>High Priority</h3>
                <div class="number high">{{ summary_stats.severity_counts.high|default(0) }}</div>
                <div class="label">High Priority Changes</div>
            </div>
            <div class="summary-card">
                <h3>Monitoring Success</h3>
                <div class="number">{{ "%.1f"|format(summary_stats.monitoring_success_rate) }}%</div>
                <div class="label">Success Rate</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Key Findings</h2>
            <ul>
                <li><strong>{{ summary_stats.total_changes }}</strong> compliance changes detected during the reporting period</li>
                <li><strong>{{ summary_stats.severity_counts.critical|default(0) }}</strong> critical changes requiring immediate attention</li>
                <li><strong>{{ summary_stats.severity_counts.high|default(0) }}</strong> high-priority changes that need prompt review</li>
                <li>Monitoring system operating at <strong>{{ "%.1f"|format(summary_stats.monitoring_success_rate) }}%</strong> success rate</li>
                <li>Notification delivery rate: <strong>{{ "%.1f"|format(summary_stats.notification_delivery_rate) }}%</strong></li>
            </ul>
        </div>
        
        {% if recommendations %}
        <div class="section">
            <div class="recommendations">
                <h3>Key Recommendations</h3>
                <ul>
                    {% for recommendation in recommendations %}
                    <li>{{ recommendation }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>This report was automatically generated by the AI-Powered Compliance Monitoring System</p>
            <p>For detailed information, please refer to the complete report</p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _get_detailed_report_template(self) -> Template:
        """Get detailed report template."""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Detailed Compliance Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #2c3e50; margin: 0; font-size: 2.5em; }
        .header .subtitle { color: #7f8c8d; font-size: 1.2em; margin-top: 10px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: #ecf0f1; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-card .number { font-size: 2em; font-weight: bold; color: #2c3e50; }
        .stat-card .label { color: #7f8c8d; font-size: 0.9em; }
        .changes-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .changes-table th, .changes-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        .changes-table th { background: #34495e; color: white; font-weight: bold; }
        .changes-table tr:nth-child(even) { background: #f8f9fa; }
        .changes-table tr:hover { background: #e8f4f8; }
        .severity-critical { color: #e74c3c; font-weight: bold; }
        .severity-high { color: #f39c12; font-weight: bold; }
        .severity-medium { color: #f1c40f; font-weight: bold; }
        .severity-low { color: #27ae60; font-weight: bold; }
        .agency-section { margin-bottom: 30px; }
        .agency-section h3 { color: #2c3e50; background: #ecf0f1; padding: 10px; border-radius: 5px; }
        .impact-section { background: #e8f5e8; border: 1px solid #c3e6c3; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .impact-section h3 { color: #27ae60; margin-top: 0; }
        .recommendations { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 20px; }
        .recommendations h3 { color: #856404; margin-top: 0; }
        .recommendations ul { margin: 0; padding-left: 20px; }
        .recommendations li { margin-bottom: 10px; color: #856404; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Detailed Compliance Report</h1>
            <div class="subtitle">Comprehensive Analysis of All Compliance Changes</div>
            <div class="subtitle">{{ metadata.report_period }}</div>
            <div class="subtitle">Generated: {{ generated_at }}</div>
        </div>
        
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{{ summary_stats.total_changes }}</div>
                    <div class="label">Total Changes</div>
                </div>
                <div class="stat-card">
                    <div class="number severity-critical">{{ summary_stats.severity_counts.critical|default(0) }}</div>
                    <div class="label">Critical</div>
                </div>
                <div class="stat-card">
                    <div class="number severity-high">{{ summary_stats.severity_counts.high|default(0) }}</div>
                    <div class="label">High Priority</div>
                </div>
                <div class="stat-card">
                    <div class="number severity-medium">{{ summary_stats.severity_counts.medium|default(0) }}</div>
                    <div class="label">Medium</div>
                </div>
                <div class="stat-card">
                    <div class="number severity-low">{{ summary_stats.severity_counts.low|default(0) }}</div>
                    <div class="label">Low</div>
                </div>
                <div class="stat-card">
                    <div class="number">{{ "%.1f"|format(summary_stats.monitoring_success_rate) }}%</div>
                    <div class="label">Monitoring Success</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>Changes by Agency</h2>
            {% for agency, changes in changes_by_agency.items() %}
            <div class="agency-section">
                <h3>{{ agency }} ({{ changes|length }} changes)</h3>
                <table class="changes-table">
                    <thead>
                        <tr>
                            <th>Form</th>
                            <th>Change Type</th>
                            <th>Severity</th>
                            <th>Description</th>
                            <th>Detected</th>
                            <th>AI Confidence</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for change in changes %}
                        <tr>
                            <td><strong>{{ change.form_name }}</strong><br><small>{{ change.form_title }}</small></td>
                            <td>{{ change.change_type|title }}</td>
                            <td class="severity-{{ change.severity }}">{{ change.severity|upper }}</td>
                            <td>{{ change.change_description }}</td>
                            <td>{{ change.detected_at.strftime('%Y-%m-%d') if change.detected_at else 'N/A' }}</td>
                            <td>{{ change.ai_confidence_score }}%</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endfor %}
        </div>
        
        {% if impact_assessments %}
        <div class="section">
            <h2>Impact Assessment</h2>
            {% for assessment in impact_assessments %}
            <div class="impact-section">
                <h3>{{ assessment.form_name }} - {{ assessment.agency_name }}</h3>
                <p><strong>Total Clients Impacted:</strong> {{ assessment.total_clients_impacted }} ({{ "%.1f"|format(assessment.impact_percentage) }}% of total client base)</p>
                <p><strong>Severity:</strong> <span class="severity-{{ assessment.severity }}">{{ assessment.severity|upper }}</span></p>
                <p><strong>AI Confidence:</strong> {{ assessment.ai_confidence_score }}%</p>
                {% if assessment.icp_segment_breakdown %}
                <p><strong>ICP Segment Breakdown:</strong></p>
                <ul>
                    {% for segment, count in assessment.icp_segment_breakdown.items() %}
                    <li>{{ segment }}: {{ count }} clients</li>
                    {% endfor %}
                </ul>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if monitoring_stats %}
        <div class="section">
            <h2>Monitoring Performance</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="number">{{ monitoring_stats.total_runs }}</div>
                    <div class="label">Total Runs</div>
                </div>
                <div class="stat-card">
                    <div class="number">{{ monitoring_stats.successful_runs }}</div>
                    <div class="label">Successful</div>
                </div>
                <div class="stat-card">
                    <div class="number">{{ monitoring_stats.failed_runs }}</div>
                    <div class="label">Failed</div>
                </div>
                <div class="stat-card">
                    <div class="number">{{ "%.1f"|format(monitoring_stats.success_rate) }}%</div>
                    <div class="label">Success Rate</div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if recommendations %}
        <div class="section">
            <div class="recommendations">
                <h3>Recommendations</h3>
                <ul>
                    {% for recommendation in recommendations %}
                    <li>{{ recommendation }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>This report was automatically generated by the AI-Powered Compliance Monitoring System</p>
            <p>For questions or additional information, please contact the compliance team</p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _get_technical_report_template(self) -> Template:
        """Get technical report template for developers and technical staff."""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical Compliance Report</title>
    <style>
        body { font-family: 'Courier New', monospace; margin: 0; padding: 20px; background-color: #1e1e1e; color: #d4d4d4; }
        .container { max-width: 1400px; margin: 0 auto; background: #2d2d30; padding: 30px; border-radius: 8px; border: 1px solid #3e3e42; }
        .header { text-align: center; border-bottom: 3px solid #007acc; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #007acc; margin: 0; font-size: 2.5em; }
        .header .subtitle { color: #858585; font-size: 1.2em; margin-top: 10px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #007acc; border-bottom: 2px solid #007acc; padding-bottom: 10px; }
        .code-block { background: #1e1e1e; border: 1px solid #3e3e42; border-radius: 5px; padding: 15px; margin: 10px 0; overflow-x: auto; }
        .changes-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .changes-table th, .changes-table td { padding: 12px; text-align: left; border-bottom: 1px solid #3e3e42; }
        .changes-table th { background: #007acc; color: white; font-weight: bold; }
        .changes-table tr:nth-child(even) { background: #252526; }
        .changes-table tr:hover { background: #2a2d2e; }
        .severity-critical { color: #f44747; font-weight: bold; }
        .severity-high { color: #ff8c00; font-weight: bold; }
        .severity-medium { color: #ffcc02; font-weight: bold; }
        .severity-low { color: #4ec9b0; font-weight: bold; }
        .ai-analysis { background: #1e1e1e; border-left: 4px solid #007acc; padding: 15px; margin: 10px 0; }
        .ai-analysis h4 { color: #007acc; margin-top: 0; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #3e3e42; color: #858585; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Technical Compliance Report</h1>
            <div class="subtitle">Detailed Technical Analysis for Development Team</div>
            <div class="subtitle">{{ metadata.report_period }}</div>
            <div class="subtitle">Generated: {{ generated_at }}</div>
        </div>
        
        <div class="section">
            <h2>Technical Summary</h2>
            <div class="code-block">
                <strong>Total Changes Detected:</strong> {{ summary_stats.total_changes }}<br>
                <strong>Critical Changes:</strong> {{ summary_stats.severity_counts.critical|default(0) }}<br>
                <strong>High Priority Changes:</strong> {{ summary_stats.severity_counts.high|default(0) }}<br>
                <strong>Average AI Confidence:</strong> {{ summary_stats.avg_ai_confidence }}%<br>
                <strong>Monitoring Success Rate:</strong> {{ "%.1f"|format(summary_stats.monitoring_success_rate) }}%
            </div>
        </div>
        
        <div class="section">
            <h2>Detailed Change Analysis</h2>
            <table class="changes-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Form</th>
                        <th>Agency</th>
                        <th>Change Type</th>
                        <th>Severity</th>
                        <th>AI Confidence</th>
                        <th>AI Category</th>
                        <th>Detected</th>
                    </tr>
                </thead>
                <tbody>
                    {% for change in form_changes %}
                    <tr>
                        <td>{{ change.id }}</td>
                        <td><strong>{{ change.form_name }}</strong><br><small>{{ change.form_title }}</small></td>
                        <td>{{ change.agency_name }}</td>
                        <td>{{ change.change_type|upper }}</td>
                        <td class="severity-{{ change.severity }}">{{ change.severity|upper }}</td>
                        <td>{{ change.ai_confidence_score }}%</td>
                        <td>{{ change.ai_change_category|default('N/A') }}</td>
                        <td>{{ change.detected_at.strftime('%Y-%m-%d %H:%M') if change.detected_at else 'N/A' }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>AI Analysis Details</h2>
            {% for change in form_changes %}
            {% if change.ai_reasoning %}
            <div class="ai-analysis">
                <h4>{{ change.form_name }} - {{ change.agency_name }}</h4>
                <p><strong>AI Confidence:</strong> {{ change.ai_confidence_score }}%</p>
                <p><strong>AI Category:</strong> {{ change.ai_change_category|default('N/A') }}</p>
                <p><strong>AI Severity Score:</strong> {{ change.ai_severity_score|default('N/A') }}/100</p>
                <p><strong>Cosmetic Change:</strong> {{ 'Yes' if change.is_cosmetic_change else 'No' }}</p>
                <p><strong>AI Reasoning:</strong></p>
                <div class="code-block">{{ change.ai_reasoning }}</div>
            </div>
            {% endif %}
            {% endfor %}
        </div>
        
        {% if monitoring_stats %}
        <div class="section">
            <h2>Monitoring System Performance</h2>
            <div class="code-block">
                <strong>Total Monitoring Runs:</strong> {{ monitoring_stats.total_runs }}<br>
                <strong>Successful Runs:</strong> {{ monitoring_stats.successful_runs }}<br>
                <strong>Failed Runs:</strong> {{ monitoring_stats.failed_runs }}<br>
                <strong>Success Rate:</strong> {{ "%.1f"|format(monitoring_stats.success_rate) }}%<br>
                <strong>Average Response Time:</strong> {{ "%.0f"|format(monitoring_stats.avg_response_time_ms) }}ms
            </div>
            
            <h3>Agency Performance Breakdown</h3>
            {% for agency, stats in monitoring_stats.agency_breakdown.items() %}
            <div class="code-block">
                <strong>{{ agency }}</strong><br>
                Total Runs: {{ stats.total_runs }} | 
                Successful: {{ stats.successful_runs }} | 
                Failed: {{ stats.failed_runs }} | 
                Changes Detected: {{ stats.changes_detected }}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        {% if trend_analysis %}
        <div class="section">
            <h2>Trend Analysis</h2>
            <div class="code-block">
                <strong>Trend Direction:</strong> {{ trend_analysis.trend_direction|upper }}<br>
                <strong>Average Daily Changes:</strong> {{ "%.1f"|format(trend_analysis.avg_daily_changes) }}<br>
                <strong>Total Period Changes:</strong> {{ trend_analysis.total_period_changes }}
            </div>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Technical Report - AI-Powered Compliance Monitoring System</p>
            <p>Generated for development and technical analysis purposes</p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _get_dashboard_report_template(self) -> Template:
        """Get dashboard-style report template."""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
        .header h1 { color: #2c3e50; margin: 0; font-size: 2.5em; }
        .header .subtitle { color: #7f8c8d; font-size: 1.2em; margin-top: 10px; }
        .dashboard-grid { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 20px; }
        .main-content { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .sidebar { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .section { margin-bottom: 30px; }
        .section h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }
        .metric-card { background: #ecf0f1; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 15px; }
        .metric-card .number { font-size: 2.5em; font-weight: bold; color: #2c3e50; }
        .metric-card .label { color: #7f8c8d; font-size: 0.9em; }
        .changes-list { list-style: none; padding: 0; }
        .changes-list li { padding: 15px; border-bottom: 1px solid #ecf0f1; }
        .changes-list li:last-child { border-bottom: none; }
        .change-item { display: flex; justify-content: space-between; align-items: center; }
        .change-info h4 { margin: 0 0 5px 0; color: #2c3e50; }
        .change-info p { margin: 0; color: #7f8c8d; font-size: 0.9em; }
        .severity-badge { padding: 5px 10px; border-radius: 15px; font-size: 0.8em; font-weight: bold; }
        .severity-critical { background: #e74c3c; color: white; }
        .severity-high { background: #f39c12; color: white; }
        .severity-medium { background: #f1c40f; color: #2c3e50; }
        .severity-low { background: #27ae60; color: white; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Compliance Dashboard</h1>
            <div class="subtitle">Real-time Overview of Compliance Changes</div>
            <div class="subtitle">{{ metadata.report_period }}</div>
            <div class="subtitle">Generated: {{ generated_at }}</div>
        </div>
        
        <div class="dashboard-grid">
            <div class="main-content">
                <div class="section">
                    <h2>Recent Changes</h2>
                    <ul class="changes-list">
                        {% for change in form_changes[:10] %}
                        <li>
                            <div class="change-item">
                                <div class="change-info">
                                    <h4>{{ change.form_name }} - {{ change.agency_name }}</h4>
                                    <p>{{ change.change_description }}</p>
                                    <p><small>Detected: {{ change.detected_at.strftime('%Y-%m-%d %H:%M') if change.detected_at else 'N/A' }}</small></p>
                                </div>
                                <span class="severity-badge severity-{{ change.severity }}">{{ change.severity|upper }}</span>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
            
            <div class="sidebar">
                <div class="section">
                    <h2>Key Metrics</h2>
                    <div class="metric-card">
                        <div class="number">{{ summary_stats.total_changes }}</div>
                        <div class="label">Total Changes</div>
                    </div>
                    <div class="metric-card">
                        <div class="number severity-critical">{{ summary_stats.severity_counts.critical|default(0) }}</div>
                        <div class="label">Critical</div>
                    </div>
                    <div class="metric-card">
                        <div class="number severity-high">{{ summary_stats.severity_counts.high|default(0) }}</div>
                        <div class="label">High Priority</div>
                    </div>
                    <div class="metric-card">
                        <div class="number">{{ "%.1f"|format(summary_stats.monitoring_success_rate) }}%</div>
                        <div class="label">Monitoring Success</div>
                    </div>
                </div>
                
                {% if recommendations %}
                <div class="section">
                    <h2>Top Recommendations</h2>
                    <ul>
                        {% for recommendation in recommendations[:3] %}
                        <li>{{ recommendation }}</li>
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
            </div>
        </div>
        
        <div class="footer">
            <p>Dashboard Report - AI-Powered Compliance Monitoring System</p>
            <p>For detailed information, please refer to the complete report</p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _get_email_summary_template(self) -> Template:
        """Get email summary template for quick overview."""
        return Template("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weekly Compliance Summary</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #2c3e50; margin: 0; font-size: 2em; }
        .header .subtitle { color: #7f8c8d; font-size: 1.1em; margin-top: 10px; }
        .summary-box { background: #ecf0f1; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .summary-box h3 { color: #2c3e50; margin-top: 0; }
        .changes-list { list-style: none; padding: 0; }
        .changes-list li { padding: 10px 0; border-bottom: 1px solid #ecf0f1; }
        .changes-list li:last-child { border-bottom: none; }
        .severity-critical { color: #e74c3c; font-weight: bold; }
        .severity-high { color: #f39c12; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ecf0f1; color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Weekly Compliance Summary</h1>
            <div class="subtitle">{{ metadata.report_period }}</div>
        </div>
        
        <div class="summary-box">
            <h3>Quick Overview</h3>
            <p><strong>{{ summary_stats.total_changes }}</strong> compliance changes detected this week</p>
            <p><strong>{{ summary_stats.severity_counts.critical|default(0) }}</strong> critical changes requiring immediate attention</p>
            <p><strong>{{ summary_stats.severity_counts.high|default(0) }}</strong> high-priority changes</p>
            <p>Monitoring system operating at <strong>{{ "%.1f"|format(summary_stats.monitoring_success_rate) }}%</strong> success rate</p>
        </div>
        
        {% if summary_stats.severity_counts.critical|default(0) > 0 or summary_stats.severity_counts.high|default(0) > 0 %}
        <div class="summary-box">
            <h3>Priority Changes</h3>
            <ul class="changes-list">
                {% for change in form_changes %}
                {% if change.severity in ['critical', 'high'] %}
                <li>
                    <strong>{{ change.form_name }}</strong> - {{ change.agency_name }}<br>
                    <span class="severity-{{ change.severity }}">{{ change.severity|upper }}</span>: {{ change.change_description }}
                </li>
                {% endif %}
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        {% if recommendations %}
        <div class="summary-box">
            <h3>Key Recommendations</h3>
            <ul>
                {% for recommendation in recommendations[:3] %}
                <li>{{ recommendation }}</li>
                {% endfor %}
            </ul>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>This summary was automatically generated by the AI-Powered Compliance Monitoring System</p>
            <p>For detailed information, please access the full report in the dashboard</p>
        </div>
    </div>
</body>
</html>
        """)


def render_consolidated_report(
    report_data: Dict[str, Any],
    template_type: str = 'detailed_report',
    include_charts: bool = True
) -> str:
    """
    Convenience function to render a consolidated report.
    
    Args:
        report_data: Report data from WeeklyReportGenerator
        template_type: Type of template to use
        include_charts: Whether to include chart placeholders
        
    Returns:
        Rendered HTML report
    """
    template_manager = ReportTemplateManager()
    return template_manager.render_report(report_data, template_type, include_charts)


def get_available_templates() -> List[str]:
    """Get list of available report templates."""
    return [
        'executive_summary',
        'detailed_report', 
        'technical_report',
        'dashboard_report',
        'email_summary'
    ] 