"""
Enhanced Email Notification Templates

This module provides comprehensive email templates for notifications with detailed
change information and impact assessment for certified payroll compliance monitoring.
"""

from jinja2 import Template
from typing import Dict, Any


class EnhancedEmailTemplates:
    """Enhanced email templates with detailed change information and impact assessment."""
    
    def __init__(self):
        self.templates = {
            'product_manager': self._create_product_manager_template(),
            'business_analyst': self._create_business_analyst_template(),
            'executive_summary': self._create_executive_summary_template(),
            'technical_detailed': self._create_technical_detailed_template()
        }
    
    def get_template(self, template_type: str = 'product_manager') -> Template:
        """Get a specific email template."""
        return self.templates.get(template_type, self.templates['product_manager'])
    
    def _create_product_manager_template(self) -> Template:
        """Create comprehensive template for Product Managers."""
        return Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certified Payroll Report Change Alert</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f8f9fa; 
            color: #333; 
        }
        .container { 
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 10px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            overflow: hidden; 
        }
        .header { 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            padding: 30px; 
            text-align: center; 
        }
        .header h1 { 
            margin: 0; 
            font-size: 28px; 
            font-weight: 600; 
        }
        .severity-badge { 
            display: inline-block; 
            padding: 8px 16px; 
            border-radius: 20px; 
            font-weight: bold; 
            margin-top: 10px; 
            font-size: 14px; 
        }
        .severity-critical { background-color: #dc3545; }
        .severity-high { background-color: #fd7e14; }
        .severity-medium { background-color: #ffc107; color: #333; }
        .severity-low { background-color: #28a745; }
        
        .content { padding: 30px; }
        .section { 
            margin-bottom: 30px; 
            border-radius: 8px; 
            overflow: hidden; 
        }
        .section-header { 
            padding: 15px 20px; 
            font-weight: 600; 
            font-size: 18px; 
            color: white; 
        }
        .section-content { padding: 20px; }
        
        .change-details { 
            background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); 
        }
        .change-details .section-header { background-color: #e67e22; }
        
        .impact-assessment { 
            background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); 
        }
        .impact-assessment .section-header { background-color: #3498db; }
        
        .ai-analysis { 
            background: linear-gradient(135deg, #d299c2 0%, #fef9d7 100%); 
        }
        .ai-analysis .section-header { background-color: #9b59b6; }
        
        .action-items { 
            background: linear-gradient(135deg, #e0c3fc 0%, #fc466b 100%); 
        }
        .action-items .section-header { background-color: #8e44ad; }
        
        .info-grid { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 15px; 
            margin: 15px 0; 
        }
        .info-item { 
            background: rgba(255,255,255,0.9); 
            padding: 15px; 
            border-radius: 6px; 
            border-left: 4px solid #3498db; 
        }
        .info-item strong { color: #2c3e50; }
        
        .impact-metrics { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
            margin: 15px 0; 
        }
        .metric-card { 
            background: rgba(255,255,255,0.9); 
            padding: 20px; 
            border-radius: 8px; 
            text-align: center; 
            border: 2px solid #ecf0f1; 
        }
        .metric-value { 
            font-size: 24px; 
            font-weight: bold; 
            color: #2c3e50; 
        }
        .metric-label { 
            font-size: 14px; 
            color: #7f8c8d; 
            margin-top: 5px; 
        }
        
        .ai-confidence { 
            background: rgba(255,255,255,0.9); 
            padding: 15px; 
            border-radius: 6px; 
            margin: 15px 0; 
        }
        .confidence-bar { 
            background: #ecf0f1; 
            border-radius: 10px; 
            height: 20px; 
            overflow: hidden; 
            margin: 10px 0; 
        }
        .confidence-fill { 
            height: 100%; 
            background: linear-gradient(90deg, #e74c3c, #f39c12, #f1c40f, #27ae60); 
            transition: width 0.3s ease; 
        }
        
        .action-list { 
            background: rgba(255,255,255,0.9); 
            padding: 20px; 
            border-radius: 6px; 
        }
        .action-list ol { 
            margin: 0; 
            padding-left: 20px; 
        }
        .action-list li { 
            margin-bottom: 10px; 
            line-height: 1.6; 
        }
        
        .resources { 
            background: rgba(255,255,255,0.9); 
            padding: 20px; 
            border-radius: 6px; 
        }
        .resources a { 
            color: #3498db; 
            text-decoration: none; 
            font-weight: 500; 
        }
        .resources a:hover { text-decoration: underline; }
        
        .footer { 
            background-color: #2c3e50; 
            color: white; 
            padding: 20px; 
            text-align: center; 
            font-size: 14px; 
        }
        
        @media (max-width: 600px) {
            .info-grid { grid-template-columns: 1fr; }
            .impact-metrics { grid-template-columns: 1fr; }
            .content { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 Certified Payroll Report Change Alert</h1>
            <div class="severity-badge severity-{{ severity.lower() }}">
                {{ severity.upper() }} PRIORITY
            </div>
            <p style="margin-top: 15px; opacity: 0.9;">
                Detected on {{ detected_at }} | AI Confidence: {{ ai_confidence_score }}%
            </p>
        </div>
        
        <div class="content">
            <!-- Change Details Section -->
            <div class="section change-details">
                <div class="section-header">📋 Change Details</div>
                <div class="section-content">
                    <div class="info-grid">
                        <div class="info-item">
                            <strong>Agency:</strong><br>
                            {{ agency_name }}
                        </div>
                        <div class="info-item">
                            <strong>Report Name/ID:</strong><br>
                            {{ form_name }}
                        </div>
                        <div class="info-item">
                            <strong>CPR Report ID:</strong><br>
                            {{ cpr_report_id or "N/A" }}
                        </div>
                        <div class="info-item">
                            <strong>Change Type:</strong><br>
                            {{ change_type|title }}
                        </div>
                    </div>
                    
                    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <strong>Change Description:</strong><br>
                        {{ change_description }}
                    </div>
                    
                    {% if effective_date %}
                    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <strong>Effective Date:</strong> {{ effective_date }}
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- Impact Assessment Section -->
            <div class="section impact-assessment">
                <div class="section-header">📊 Impact Assessment</div>
                <div class="section-content">
                    <div class="impact-metrics">
                        <div class="metric-card">
                            <div class="metric-value">{{ clients_impacted }}</div>
                            <div class="metric-label">Clients Impacted</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{{ icp_percentage }}%</div>
                            <div class="metric-label">ICP Segment</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{{ ai_severity_score }}/100</div>
                            <div class="metric-label">AI Severity Score</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{{ ai_semantic_similarity }}%</div>
                            <div class="metric-label">Semantic Similarity</div>
                        </div>
                    </div>
                    
                    {% if impact_details %}
                    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <strong>Impact Details:</strong>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {% for detail in impact_details %}
                            <li>{{ detail }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- AI Analysis Section -->
            <div class="section ai-analysis">
                <div class="section-header">🤖 AI Analysis</div>
                <div class="section-content">
                    <div class="ai-confidence">
                        <strong>AI Confidence Score:</strong>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {{ ai_confidence_score }}%;"></div>
                        </div>
                        <div style="text-align: center; margin-top: 5px;">{{ ai_confidence_score }}%</div>
                    </div>
                    
                    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <strong>Change Category:</strong> {{ ai_change_category|title if ai_change_category else "N/A" }}<br>
                        <strong>Cosmetic Change:</strong> {{ "Yes" if is_cosmetic_change else "No" }}
                    </div>
                    
                    {% if ai_reasoning %}
                    <div style="background: rgba(255,255,255,0.9); padding: 15px; border-radius: 6px; margin-top: 15px;">
                        <strong>AI Reasoning:</strong><br>
                        {{ ai_reasoning }}
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- Action Items Section -->
            <div class="section action-items">
                <div class="section-header">📋 Required Actions & Resources</div>
                <div class="section-content">
                    <div class="action-list">
                        <strong>Development Process:</strong>
                        <ol>
                            <li><strong>Evaluation:</strong> Assess effort, risk, and impact</li>
                            <li><strong>Development:</strong> Following strict guidelines for report updates</li>
                            <li><strong>QA:</strong> Comprehensive testing of changes</li>
                            <li><strong>EUT:</strong> End-user testing and final review</li>
                            <li><strong>Production:</strong> Release and stakeholder notification</li>
                            <li><strong>Monitoring:</strong> 3-month feedback collection period</li>
                        </ol>
                    </div>
                    
                    <div class="resources">
                        <strong>Resources:</strong>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {% if form_url %}<li><a href="{{ form_url }}" target="_blank">📄 Report Specifications</a></li>{% endif %}
                            {% if instructions_url %}<li><a href="{{ instructions_url }}" target="_blank">📖 Report Instructions</a></li>{% endif %}
                            <li><strong>📧 Agency Contact:</strong> {{ agency_contact_email }}</li>
                            <li><strong>📞 Agency Phone:</strong> {{ agency_contact_phone }}</li>
                            {% if field_mapping_current %}<li>🗺️ Report field mapping (current): Available in CPR</li>{% endif %}
                            {% if field_mapping_updated %}<li>🗺️ Report field mapping (updated): Available in CPR</li>{% endif %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>This alert was generated automatically by the Payroll Monitoring System.</p>
            <p>For questions or support, please contact your development team.</p>
            <p style="margin-top: 10px; font-size: 12px; opacity: 0.8;">
                Generated on {{ generated_at or "N/A" }} | Template: Product Manager Enhanced
            </p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _create_business_analyst_template(self) -> Template:
        """Create detailed technical template for Business Analysts."""
        return Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical Analysis - Payroll Report Change</title>
    <style>
        body { 
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace; 
            margin: 0; 
            padding: 20px; 
            background-color: #1e1e1e; 
            color: #d4d4d4; 
        }
        .container { 
            max-width: 900px; 
            margin: 0 auto; 
            background: #2d2d30; 
            border-radius: 8px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
            overflow: hidden; 
        }
        .header { 
            background: linear-gradient(135deg, #007acc 0%, #005a9e 100%); 
            color: white; 
            padding: 25px; 
            text-align: center; 
        }
        .header h1 { 
            margin: 0; 
            font-size: 24px; 
            font-weight: 600; 
        }
        .severity-badge { 
            display: inline-block; 
            padding: 6px 12px; 
            border-radius: 4px; 
            font-weight: bold; 
            margin-top: 10px; 
            font-size: 12px; 
            font-family: monospace; 
        }
        .severity-critical { background-color: #d73a49; }
        .severity-high { background-color: #f97583; }
        .severity-medium { background-color: #faa356; color: #24292e; }
        .severity-low { background-color: #28a745; }
        
        .content { padding: 25px; }
        .section { 
            margin-bottom: 25px; 
            border: 1px solid #3e3e42; 
            border-radius: 4px; 
            overflow: hidden; 
        }
        .section-header { 
            padding: 12px 15px; 
            font-weight: 600; 
            font-size: 16px; 
            color: white; 
            background-color: #007acc; 
            border-bottom: 1px solid #3e3e42; 
        }
        .section-content { padding: 15px; }
        
        .technical-table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 10px 0; 
            font-size: 13px; 
        }
        .technical-table th, .technical-table td { 
            border: 1px solid #3e3e42; 
            padding: 8px 12px; 
            text-align: left; 
        }
        .technical-table th { 
            background-color: #252526; 
            color: #cccccc; 
            font-weight: 600; 
        }
        .technical-table td { 
            background-color: #1e1e1e; 
        }
        .technical-table tr:nth-child(even) td { 
            background-color: #252526; 
        }
        
        .code-block { 
            background-color: #1e1e1e; 
            border: 1px solid #3e3e42; 
            border-radius: 4px; 
            padding: 15px; 
            margin: 10px 0; 
            font-family: 'Consolas', monospace; 
            font-size: 12px; 
            overflow-x: auto; 
        }
        .code-block pre { 
            margin: 0; 
            white-space: pre-wrap; 
        }
        
        .metric-grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
            margin: 15px 0; 
        }
        .metric-card { 
            background-color: #252526; 
            border: 1px solid #3e3e42; 
            padding: 15px; 
            border-radius: 4px; 
            text-align: center; 
        }
        .metric-value { 
            font-size: 20px; 
            font-weight: bold; 
            color: #007acc; 
        }
        .metric-label { 
            font-size: 12px; 
            color: #888888; 
            margin-top: 5px; 
        }
        
        .analysis-section { 
            background-color: #252526; 
            border: 1px solid #3e3e42; 
            padding: 15px; 
            border-radius: 4px; 
            margin: 15px 0; 
        }
        
        .footer { 
            background-color: #007acc; 
            color: white; 
            padding: 15px; 
            text-align: center; 
            font-size: 12px; 
            font-family: monospace; 
        }
        
        @media (max-width: 600px) {
            .metric-grid { grid-template-columns: 1fr; }
            .content { padding: 15px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Technical Analysis - Payroll Report Change</h1>
            <div class="severity-badge severity-{{ severity.lower() }}">
                SEVERITY: {{ severity.upper() }}
            </div>
            <p style="margin-top: 10px; opacity: 0.9; font-size: 14px;">
                Detected: {{ detected_at }} | AI Confidence: {{ ai_confidence_score }}%
            </p>
        </div>
        
        <div class="content">
            <!-- Change Details Section -->
            <div class="section">
                <div class="section-header">📋 Change Details</div>
                <div class="section-content">
                    <table class="technical-table">
                        <tr>
                            <th>Field</th>
                            <th>Value</th>
                        </tr>
                        <tr>
                            <td>Agency</td>
                            <td>{{ agency_name }}</td>
                        </tr>
                        <tr>
                            <td>Report Name/ID</td>
                            <td>{{ form_name }}</td>
                        </tr>
                        <tr>
                            <td>CPR Report ID</td>
                            <td>{{ cpr_report_id or "N/A" }}</td>
                        </tr>
                        <tr>
                            <td>Change Type</td>
                            <td>{{ change_type|title }}</td>
                        </tr>
                        <tr>
                            <td>Effective Date</td>
                            <td>{{ effective_date or "N/A" }}</td>
                        </tr>
                    </table>
                    
                    <div class="analysis-section">
                        <strong>Change Description:</strong><br>
                        {{ change_description }}
                    </div>
                </div>
            </div>
            
            <!-- Technical Analysis Section -->
            <div class="section">
                <div class="section-header">🔧 Technical Analysis</div>
                <div class="section-content">
                    <table class="technical-table">
                        <tr>
                            <th>Technical Field</th>
                            <th>Old Value</th>
                            <th>New Value</th>
                        </tr>
                        {% if old_value %}
                        <tr>
                            <td>Content Hash</td>
                            <td><code>{{ old_value[:20] }}...</code></td>
                            <td><code>{{ new_value[:20] }}...</code></td>
                        </tr>
                        {% endif %}
                        <tr>
                            <td>AI Severity Score</td>
                            <td colspan="2">{{ ai_severity_score }}/100</td>
                        </tr>
                        <tr>
                            <td>Semantic Similarity</td>
                            <td colspan="2">{{ ai_semantic_similarity }}%</td>
                        </tr>
                        <tr>
                            <td>AI Change Category</td>
                            <td colspan="2">{{ ai_change_category|title if ai_change_category else "N/A" }}</td>
                        </tr>
                        <tr>
                            <td>Cosmetic Change</td>
                            <td colspan="2">{{ "Yes" if is_cosmetic_change else "No" }}</td>
                        </tr>
                    </table>
                    
                    {% if ai_reasoning %}
                    <div class="analysis-section">
                        <strong>AI Reasoning:</strong>
                        <div class="code-block">
                            <pre>{{ ai_reasoning }}</pre>
                        </div>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- Impact Assessment Section -->
            <div class="section">
                <div class="section-header">📊 Impact Assessment</div>
                <div class="section-content">
                    <div class="metric-grid">
                        <div class="metric-card">
                            <div class="metric-value">{{ clients_impacted }}</div>
                            <div class="metric-label">Clients Impacted</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{{ icp_percentage }}%</div>
                            <div class="metric-label">ICP Segment</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{{ ai_confidence_score }}%</div>
                            <div class="metric-label">AI Confidence</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value">{{ ai_semantic_similarity }}%</div>
                            <div class="metric-label">Semantic Similarity</div>
                        </div>
                    </div>
                    
                    {% if impact_details %}
                    <div class="analysis-section">
                        <strong>Impact Details:</strong>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {% for detail in impact_details %}
                            <li>{{ detail }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <!-- Analysis Requirements Section -->
            <div class="section">
                <div class="section-header">📋 Analysis Requirements</div>
                <div class="section-content">
                    <div class="analysis-section">
                        <strong>Required Analysis:</strong>
                        <ol style="margin: 10px 0; padding-left: 20px;">
                            <li>Review AI analysis for accuracy and completeness</li>
                            <li>Assess technical impact on existing integrations</li>
                            <li>Evaluate data mapping requirements</li>
                            <li>Identify potential compliance risks</li>
                            <li>Prepare detailed impact report for Product Manager</li>
                            <li>Document technical implementation requirements</li>
                        </ol>
                    </div>
                    
                    <div class="analysis-section">
                        <strong>Resources:</strong>
                        <ul style="margin: 10px 0; padding-left: 20px;">
                            {% if form_url %}<li><a href="{{ form_url }}" target="_blank" style="color: #007acc;">📄 Report Specifications</a></li>{% endif %}
                            {% if instructions_url %}<li><a href="{{ instructions_url }}" target="_blank" style="color: #007acc;">📖 Report Instructions</a></li>{% endif %}
                            <li><strong>📧 Agency Contact:</strong> {{ agency_contact_email }}</li>
                            <li><strong>📞 Agency Phone:</strong> {{ agency_contact_phone }}</li>
                            {% if field_mapping_current %}<li>🗺️ Report field mapping (current): Available in CPR</li>{% endif %}
                            {% if field_mapping_updated %}<li>🗺️ Report field mapping (updated): Available in CPR</li>{% endif %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Generated by Payroll Monitoring System | Template: Business Analyst Technical</p>
            <p style="margin-top: 5px; font-size: 11px; opacity: 0.8;">
                {{ generated_at or "N/A" }} | Change ID: {{ change_id or "N/A" }}
            </p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _create_executive_summary_template(self) -> Template:
        """Create executive summary template for high-level overview."""
        return Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Executive Summary - Payroll Report Change</title>
    <style>
        body { 
            font-family: 'Georgia', 'Times New Roman', serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5; 
            color: #333; 
        }
        .container { 
            max-width: 700px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
            overflow: hidden; 
        }
        .header { 
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); 
            color: white; 
            padding: 30px; 
            text-align: center; 
        }
        .header h1 { 
            margin: 0; 
            font-size: 24px; 
            font-weight: 400; 
        }
        .severity-indicator { 
            display: inline-block; 
            padding: 8px 16px; 
            border-radius: 4px; 
            font-weight: bold; 
            margin-top: 15px; 
            font-size: 14px; 
        }
        .severity-critical { background-color: #e74c3c; }
        .severity-high { background-color: #e67e22; }
        .severity-medium { background-color: #f39c12; }
        .severity-low { background-color: #27ae60; }
        
        .content { padding: 30px; }
        .summary-box { 
            background-color: #ecf0f1; 
            padding: 20px; 
            border-radius: 6px; 
            margin-bottom: 25px; 
        }
        .summary-box h3 { 
            margin-top: 0; 
            color: #2c3e50; 
            border-bottom: 2px solid #3498db; 
            padding-bottom: 10px; 
        }
        .key-metrics { 
            display: grid; 
            grid-template-columns: repeat(2, 1fr); 
            gap: 20px; 
            margin: 20px 0; 
        }
        .metric { 
            text-align: center; 
            padding: 15px; 
            background: white; 
            border-radius: 6px; 
            border-left: 4px solid #3498db; 
        }
        .metric-value { 
            font-size: 28px; 
            font-weight: bold; 
            color: #2c3e50; 
        }
        .metric-label { 
            font-size: 14px; 
            color: #7f8c8d; 
            margin-top: 5px; 
        }
        .footer { 
            background-color: #2c3e50; 
            color: white; 
            padding: 20px; 
            text-align: center; 
            font-size: 14px; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Executive Summary</h1>
            <div class="severity-indicator severity-{{ severity.lower() }}">
                {{ severity.upper() }} Priority Change Detected
            </div>
            <p style="margin-top: 15px; opacity: 0.9;">
                {{ detected_at }}
            </p>
        </div>
        
        <div class="content">
            <div class="summary-box">
                <h3>Change Overview</h3>
                <p><strong>Agency:</strong> {{ agency_name }}</p>
                <p><strong>Report:</strong> {{ form_name }} ({{ cpr_report_id or "No CPR ID" }})</p>
                <p><strong>Type:</strong> {{ change_type|title }}</p>
                <p><strong>Description:</strong> {{ change_description }}</p>
            </div>
            
            <div class="summary-box">
                <h3>Business Impact</h3>
                <div class="key-metrics">
                    <div class="metric">
                        <div class="metric-value">{{ clients_impacted }}</div>
                        <div class="metric-label">Clients Affected</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{{ icp_percentage }}%</div>
                        <div class="metric-label">ICP Segment</div>
                    </div>
                </div>
                <p><strong>AI Confidence:</strong> {{ ai_confidence_score }}%</p>
                <p><strong>Risk Level:</strong> {{ "High" if severity in ["critical", "high"] else "Medium" if severity == "medium" else "Low" }}</p>
            </div>
            
            <div class="summary-box">
                <h3>Next Steps</h3>
                <ol>
                    <li>Review change details with technical team</li>
                    <li>Assess development effort and timeline</li>
                    <li>Coordinate with affected clients</li>
                    <li>Plan implementation and testing</li>
                </ol>
            </div>
        </div>
        
        <div class="footer">
            <p>Payroll Monitoring System | Executive Summary</p>
        </div>
    </div>
</body>
</html>
        """)
    
    def _create_technical_detailed_template(self) -> Template:
        """Create highly detailed technical template for developers."""
        return Template("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Technical Details - Payroll Report Change</title>
    <style>
        body { 
            font-family: 'Courier New', monospace; 
            margin: 0; 
            padding: 15px; 
            background-color: #0d1117; 
            color: #c9d1d9; 
        }
        .container { 
            max-width: 1000px; 
            margin: 0 auto; 
            background: #161b22; 
            border: 1px solid #30363d; 
            border-radius: 6px; 
        }
        .header { 
            background-color: #21262d; 
            color: #f0f6fc; 
            padding: 20px; 
            border-bottom: 1px solid #30363d; 
        }
        .header h1 { 
            margin: 0; 
            font-size: 20px; 
            font-weight: 600; 
        }
        .severity-tag { 
            display: inline-block; 
            padding: 4px 8px; 
            border-radius: 3px; 
            font-size: 12px; 
            font-weight: bold; 
            margin-top: 10px; 
        }
        .severity-critical { background-color: #da3633; color: #f0f6fc; }
        .severity-high { background-color: #f0883e; color: #0d1117; }
        .severity-medium { background-color: #d29922; color: #0d1117; }
        .severity-low { background-color: #238636; color: #f0f6fc; }
        
        .content { padding: 20px; }
        .section { 
            margin-bottom: 20px; 
            border: 1px solid #30363d; 
            border-radius: 4px; 
        }
        .section-header { 
            padding: 10px 15px; 
            background-color: #21262d; 
            border-bottom: 1px solid #30363d; 
            font-weight: 600; 
        }
        .section-content { padding: 15px; }
        
        .data-table { 
            width: 100%; 
            border-collapse: collapse; 
            font-size: 12px; 
        }
        .data-table th, .data-table td { 
            border: 1px solid #30363d; 
            padding: 8px; 
            text-align: left; 
        }
        .data-table th { 
            background-color: #161b22; 
            color: #58a6ff; 
        }
        .data-table td { 
            background-color: #0d1117; 
        }
        
        .code-snippet { 
            background-color: #0d1117; 
            border: 1px solid #30363d; 
            border-radius: 4px; 
            padding: 15px; 
            margin: 10px 0; 
            font-size: 12px; 
            overflow-x: auto; 
        }
        .code-snippet pre { 
            margin: 0; 
            white-space: pre-wrap; 
        }
        
        .footer { 
            background-color: #21262d; 
            color: #8b949e; 
            padding: 15px; 
            text-align: center; 
            font-size: 12px; 
            border-top: 1px solid #30363d; 
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Technical Details - Payroll Report Change</h1>
            <div class="severity-tag severity-{{ severity.lower() }}">
                {{ severity.upper() }}
            </div>
            <p style="margin-top: 10px; font-size: 14px; color: #8b949e;">
                {{ detected_at }} | AI Confidence: {{ ai_confidence_score }}%
            </p>
        </div>
        
        <div class="content">
            <div class="section">
                <div class="section-header">Change Information</div>
                <div class="section-content">
                    <table class="data-table">
                        <tr><td>Agency</td><td>{{ agency_name }}</td></tr>
                        <tr><td>Report</td><td>{{ form_name }}</td></tr>
                        <tr><td>CPR ID</td><td>{{ cpr_report_id or "N/A" }}</td></tr>
                        <tr><td>Type</td><td>{{ change_type }}</td></tr>
                        <tr><td>Effective Date</td><td>{{ effective_date or "N/A" }}</td></tr>
                    </table>
                    
                    <div class="code-snippet">
                        <strong>Description:</strong><br>
                        <pre>{{ change_description }}</pre>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">AI Analysis</div>
                <div class="section-content">
                    <table class="data-table">
                        <tr><td>Confidence Score</td><td>{{ ai_confidence_score }}%</td></tr>
                        <tr><td>Severity Score</td><td>{{ ai_severity_score }}/100</td></tr>
                        <tr><td>Semantic Similarity</td><td>{{ ai_semantic_similarity }}%</td></tr>
                        <tr><td>Change Category</td><td>{{ ai_change_category or "N/A" }}</td></tr>
                        <tr><td>Cosmetic Change</td><td>{{ "Yes" if is_cosmetic_change else "No" }}</td></tr>
                    </table>
                    
                    {% if ai_reasoning %}
                    <div class="code-snippet">
                        <strong>AI Reasoning:</strong><br>
                        <pre>{{ ai_reasoning }}</pre>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">Impact Assessment</div>
                <div class="section-content">
                    <table class="data-table">
                        <tr><td>Clients Impacted</td><td>{{ clients_impacted }}</td></tr>
                        <tr><td>ICP Percentage</td><td>{{ icp_percentage }}%</td></tr>
                    </table>
                    
                    {% if impact_details %}
                    <div class="code-snippet">
                        <strong>Impact Details:</strong><br>
                        <pre>{% for detail in impact_details %}{{ detail }}
{% endfor %}</pre>
                    </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="section">
                <div class="section-header">Technical Implementation</div>
                <div class="section-content">
                    <div class="code-snippet">
                        <strong>Required Actions:</strong><br>
                        <pre>1. Review AI analysis accuracy
2. Assess technical impact on integrations
3. Evaluate data mapping requirements
4. Identify compliance risks
5. Plan implementation timeline
6. Coordinate with affected clients</pre>
                    </div>
                    
                    <div class="code-snippet">
                        <strong>Resources:</strong><br>
                        <pre>{% if form_url %}Form URL: {{ form_url }}{% endif %}
{% if instructions_url %}Instructions: {{ instructions_url }}{% endif %}
Agency Contact: {{ agency_contact_email }}
Agency Phone: {{ agency_contact_phone }}</pre>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            Payroll Monitoring System | Technical Details | {{ generated_at or "N/A" }}
        </div>
    </div>
</body>
</html>
        """)
    
    def render_template(self, template_type: str, data: Dict[str, Any]) -> str:
        """Render a specific template with provided data."""
        template = self.get_template(template_type)
        return template.render(**data)
    
    def get_available_templates(self) -> list:
        """Get list of available template types."""
        return list(self.templates.keys()) 