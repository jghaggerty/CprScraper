import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import func

from ..database.connection import get_db
from ..database.models import (
    FormChange, Form, Agency, Client, ClientFormUsage, 
    MonitoringRun, Notification, WorkItem
)

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """Analyze the impact of form changes on clients and development processes."""
    
    def __init__(self):
        pass
    
    def analyze_form_change_impact(self, form_change_id: int) -> Dict:
        """
        Comprehensive impact analysis for a specific form change.
        
        Returns detailed impact assessment including:
        1. Client impact
        2. Development effort estimation
        3. Risk assessment
        4. Timeline projections
        """
        with get_db() as db:
            form_change = db.query(FormChange).filter(
                FormChange.id == form_change_id
            ).first()
            
            if not form_change:
                raise ValueError(f"Form change {form_change_id} not found")
            
            form = form_change.form
            agency = form.agency
            
            # Client Impact Analysis
            client_impact = self._analyze_client_impact(form.id, db)
            
            # Development Impact Analysis
            dev_impact = self._analyze_development_impact(form_change, db)
            
            # Risk Assessment
            risk_assessment = self._assess_risk_factors(form_change, client_impact, db)
            
            # Timeline Estimation
            timeline = self._estimate_timeline(form_change, dev_impact, risk_assessment)
            
            return {
                'form_change_id': form_change_id,
                'agency_name': agency.name,
                'form_name': form.name,
                'change_type': form_change.change_type,
                'change_description': form_change.change_description,
                'severity': form_change.severity,
                'detected_at': form_change.detected_at,
                'effective_date': form_change.effective_date,
                'client_impact': client_impact,
                'development_impact': dev_impact,
                'risk_assessment': risk_assessment,
                'timeline_estimation': timeline,
                'recommendations': self._generate_recommendations(
                    form_change, client_impact, dev_impact, risk_assessment
                )
            }
    
    def _analyze_client_impact(self, form_id: int, db) -> Dict:
        """Analyze impact on clients using this form."""
        # Get clients using this form
        client_usage = db.query(ClientFormUsage).filter(
            ClientFormUsage.form_id == form_id,
            ClientFormUsage.is_active == True
        ).join(Client).all()
        
        total_clients_impacted = len(client_usage)
        
        # Get total active clients for percentage calculation
        total_active_clients = db.query(Client).filter(Client.is_active == True).count()
        
        # Calculate ICP segment breakdown
        icp_segments = {}
        for usage in client_usage:
            segment = usage.client.icp_segment or 'Unknown'
            if segment not in icp_segments:
                icp_segments[segment] = 0
            icp_segments[segment] += 1
        
        # Calculate usage frequency distribution
        frequency_distribution = {}
        for usage in client_usage:
            freq = usage.usage_frequency or 'Unknown'
            if freq not in frequency_distribution:
                frequency_distribution[freq] = 0
            frequency_distribution[freq] += 1
        
        # Calculate impact score (0-10 scale)
        impact_score = min(10, (total_clients_impacted / max(total_active_clients, 1)) * 100)
        
        return {
            'total_clients_impacted': total_clients_impacted,
            'total_active_clients': total_active_clients,
            'percentage_of_client_base': round((total_clients_impacted / max(total_active_clients, 1)) * 100, 2),
            'icp_segment_breakdown': icp_segments,
            'usage_frequency_distribution': frequency_distribution,
            'impact_score': round(impact_score, 1),
            'high_usage_clients': len([u for u in client_usage if u.usage_frequency in ['weekly', 'bi-weekly']]),
            'critical_clients': [
                {
                    'client_name': usage.client.name,
                    'client_id': usage.client.client_id,
                    'usage_frequency': usage.usage_frequency,
                    'last_used': usage.last_used
                }
                for usage in client_usage
                if usage.usage_frequency in ['weekly', 'bi-weekly']
            ][:10]  # Top 10 critical clients
        }
    
    def _analyze_development_impact(self, form_change: FormChange, db) -> Dict:
        """Analyze impact on development processes."""
        change_type = form_change.change_type
        severity = form_change.severity
        
        # Base effort estimation based on change type and severity
        effort_matrix = {
            ('content', 'low'): {'min_hours': 4, 'max_hours': 8, 'complexity': 'Low'},
            ('content', 'medium'): {'min_hours': 8, 'max_hours': 16, 'complexity': 'Medium'},
            ('content', 'high'): {'min_hours': 16, 'max_hours': 32, 'complexity': 'High'},
            ('content', 'critical'): {'min_hours': 32, 'max_hours': 64, 'complexity': 'Critical'},
            ('url', 'low'): {'min_hours': 2, 'max_hours': 4, 'complexity': 'Low'},
            ('url', 'medium'): {'min_hours': 4, 'max_hours': 8, 'complexity': 'Medium'},
            ('url', 'high'): {'min_hours': 8, 'max_hours': 16, 'complexity': 'High'},
            ('new_version', 'low'): {'min_hours': 8, 'max_hours': 16, 'complexity': 'Medium'},
            ('new_version', 'medium'): {'min_hours': 16, 'max_hours': 32, 'complexity': 'High'},
            ('new_version', 'high'): {'min_hours': 32, 'max_hours': 80, 'complexity': 'Critical'},
            ('new_version', 'critical'): {'min_hours': 80, 'max_hours': 160, 'complexity': 'Critical'},
        }
        
        key = (change_type, severity)
        base_effort = effort_matrix.get(key, {'min_hours': 8, 'max_hours': 16, 'complexity': 'Medium'})
        
        # Development phases with estimated effort distribution
        phases = {
            'evaluation': {
                'percentage': 10,
                'description': 'Assess effort, risk, and impact',
                'deliverables': ['Impact assessment', 'Effort estimation', 'Risk analysis']
            },
            'development': {
                'percentage': 50,
                'description': 'Following strict guidelines for report updates',
                'deliverables': [
                    'Weekly/Bi-weekly reporting updates',
                    'Time entries and data entry modifications',
                    'ST/OT/Other hours calculations',
                    'Fringes handling (old and new)',
                    'Report options implementation',
                    'No work reporting features',
                    'Calculation evaluation and testing'
                ]
            },
            'qa': {
                'percentage': 25,
                'description': 'Comprehensive testing of changes',
                'deliverables': [
                    'Specific report changes validation',
                    'Weekly/Bi-weekly functionality testing',
                    'Time entries and data entry testing',
                    'ST/OT/Other hours verification',
                    'Fringes validation (old and new)',
                    'Report options testing',
                    'No work reporting validation',
                    'Calculation verification',
                    'Font size/alignment checks'
                ]
            },
            'eut': {
                'percentage': 15,
                'description': 'End-user testing and final review',
                'deliverables': [
                    'Process alignment verification',
                    'Risk/Impact re-evaluation',
                    'End-to-end functionality testing',
                    'User acceptance testing',
                    'Final stakeholder review'
                ]
            }
        }
        
        # Calculate effort for each phase
        total_min_hours = base_effort['min_hours']
        total_max_hours = base_effort['max_hours']
        
        phase_efforts = {}
        for phase, config in phases.items():
            phase_efforts[phase] = {
                'min_hours': round(total_min_hours * config['percentage'] / 100, 1),
                'max_hours': round(total_max_hours * config['percentage'] / 100, 1),
                'description': config['description'],
                'deliverables': config['deliverables']
            }
        
        return {
            'complexity_level': base_effort['complexity'],
            'total_effort_estimate': {
                'min_hours': total_min_hours,
                'max_hours': total_max_hours,
                'estimated_hours': round((total_min_hours + total_max_hours) / 2, 1)
            },
            'phase_breakdown': phase_efforts,
            'required_skills': self._identify_required_skills(change_type, severity),
            'testing_requirements': self._define_testing_requirements(form_change),
            'compliance_requirements': [
                'Weekly/Bi-weekly reporting compliance',
                'Time entry accuracy validation',
                'ST/OT/Other hours calculation compliance',
                'Fringe benefits handling compliance',
                'Report formatting standards',
                'Data validation requirements'
            ]
        }
    
    def _assess_risk_factors(self, form_change: FormChange, client_impact: Dict, db) -> Dict:
        """Assess risk factors for the form change implementation."""
        risks = []
        risk_score = 0
        
        # Client impact risk
        client_percentage = client_impact['percentage_of_client_base']
        if client_percentage > 50:
            risks.append({
                'category': 'Client Impact',
                'level': 'High',
                'description': f'Affects {client_percentage}% of client base',
                'mitigation': 'Extensive communication and phased rollout'
            })
            risk_score += 3
        elif client_percentage > 20:
            risks.append({
                'category': 'Client Impact',
                'level': 'Medium',
                'description': f'Affects {client_percentage}% of client base',
                'mitigation': 'Standard communication and testing protocols'
            })
            risk_score += 2
        else:
            risks.append({
                'category': 'Client Impact',
                'level': 'Low',
                'description': f'Affects {client_percentage}% of client base',
                'mitigation': 'Standard communication'
            })
            risk_score += 1
        
        # Severity-based risk
        severity_risk_map = {
            'critical': {'level': 'Critical', 'score': 4},
            'high': {'level': 'High', 'score': 3},
            'medium': {'level': 'Medium', 'score': 2},
            'low': {'level': 'Low', 'score': 1}
        }
        
        severity_risk = severity_risk_map.get(form_change.severity, {'level': 'Medium', 'score': 2})
        risks.append({
            'category': 'Change Severity',
            'level': severity_risk['level'],
            'description': f'Change severity is {form_change.severity}',
            'mitigation': 'Appropriate testing and validation based on severity'
        })
        risk_score += severity_risk['score']
        
        # Timeline risk
        effective_date = form_change.effective_date
        if effective_date:
            days_until_effective = (effective_date - datetime.utcnow()).days
            if days_until_effective < 30:
                risks.append({
                    'category': 'Timeline',
                    'level': 'High',
                    'description': f'Only {days_until_effective} days until effective date',
                    'mitigation': 'Accelerated development and testing schedule'
                })
                risk_score += 3
            elif days_until_effective < 60:
                risks.append({
                    'category': 'Timeline',
                    'level': 'Medium',
                    'description': f'{days_until_effective} days until effective date',
                    'mitigation': 'Standard development schedule with close monitoring'
                })
                risk_score += 2
        
        # Historical risk (based on previous changes for this form/agency)
        recent_changes = db.query(FormChange).filter(
            FormChange.form_id == form_change.form_id,
            FormChange.detected_at >= datetime.utcnow() - timedelta(days=180),
            FormChange.id != form_change.id
        ).count()
        
        if recent_changes > 3:
            risks.append({
                'category': 'Change Frequency',
                'level': 'Medium',
                'description': f'Form has had {recent_changes} changes in last 6 months',
                'mitigation': 'Review form stability and communication with agency'
            })
            risk_score += 2
        
        # Overall risk assessment
        if risk_score >= 10:
            overall_risk = 'Critical'
        elif risk_score >= 7:
            overall_risk = 'High'
        elif risk_score >= 4:
            overall_risk = 'Medium'
        else:
            overall_risk = 'Low'
        
        return {
            'overall_risk_level': overall_risk,
            'risk_score': risk_score,
            'risk_factors': risks,
            'mitigation_strategy': self._create_mitigation_strategy(risks, overall_risk)
        }
    
    def _estimate_timeline(self, form_change: FormChange, dev_impact: Dict, risk_assessment: Dict) -> Dict:
        """Estimate implementation timeline."""
        base_hours = dev_impact['total_effort_estimate']['estimated_hours']
        
        # Adjust for risk factors
        risk_multiplier = {
            'Low': 1.0,
            'Medium': 1.2,
            'High': 1.5,
            'Critical': 2.0
        }
        
        risk_level = risk_assessment['overall_risk_level']
        adjusted_hours = base_hours * risk_multiplier.get(risk_level, 1.2)
        
        # Convert to calendar days (assuming 6 productive hours per day)
        calendar_days = max(1, round(adjusted_hours / 6))
        
        # Phase timeline breakdown
        phases = dev_impact['phase_breakdown']
        phase_timeline = {}
        
        current_date = datetime.utcnow().date()
        for phase, config in phases.items():
            phase_hours = config['max_hours'] * risk_multiplier.get(risk_level, 1.2)
            phase_days = max(1, round(phase_hours / 6))
            
            phase_timeline[phase] = {
                'estimated_days': phase_days,
                'start_date': current_date,
                'end_date': current_date + timedelta(days=phase_days - 1)
            }
            current_date = phase_timeline[phase]['end_date'] + timedelta(days=1)
        
        # Add buffer for production release and monitoring
        production_date = current_date
        monitoring_end_date = production_date + timedelta(days=90)  # 3-month monitoring period
        
        return {
            'total_estimated_hours': round(adjusted_hours, 1),
            'total_calendar_days': calendar_days,
            'estimated_completion_date': current_date - timedelta(days=1),
            'production_release_date': production_date,
            'monitoring_end_date': monitoring_end_date,
            'phase_timeline': phase_timeline,
            'critical_milestones': [
                {
                    'milestone': 'Evaluation Complete',
                    'date': phase_timeline['evaluation']['end_date']
                },
                {
                    'milestone': 'Development Complete',
                    'date': phase_timeline['development']['end_date']
                },
                {
                    'milestone': 'QA Complete',
                    'date': phase_timeline['qa']['end_date']
                },
                {
                    'milestone': 'EUT Complete',
                    'date': phase_timeline['eut']['end_date']
                },
                {
                    'milestone': 'Production Release',
                    'date': production_date
                },
                {
                    'milestone': 'Monitoring Period End',
                    'date': monitoring_end_date
                }
            ]
        }
    
    def _identify_required_skills(self, change_type: str, severity: str) -> List[str]:
        """Identify required skills based on change type and severity."""
        base_skills = [
            'Form design and layout',
            'Data validation and processing',
            'Report generation systems',
            'Quality assurance testing'
        ]
        
        if change_type == 'new_version':
            base_skills.extend([
                'Legacy system migration',
                'Data mapping and transformation',
                'Version control and deployment'
            ])
        
        if severity in ['high', 'critical']:
            base_skills.extend([
                'Advanced troubleshooting',
                'Stakeholder communication',
                'Risk management'
            ])
        
        if change_type == 'content':
            base_skills.extend([
                'Content analysis and comparison',
                'Field mapping updates',
                'Calculation verification'
            ])
        
        return base_skills
    
    def _define_testing_requirements(self, form_change: FormChange) -> List[Dict]:
        """Define comprehensive testing requirements."""
        requirements = [
            {
                'category': 'Functional Testing',
                'tests': [
                    'Form field validation',
                    'Data entry accuracy',
                    'Calculation verification',
                    'Report generation'
                ]
            },
            {
                'category': 'Integration Testing',
                'tests': [
                    'CPR system integration',
                    'Database connectivity',
                    'External API calls',
                    'File upload/download'
                ]
            },
            {
                'category': 'User Acceptance Testing',
                'tests': [
                    'End-user workflow validation',
                    'UI/UX verification',
                    'Performance testing',
                    'Accessibility compliance'
                ]
            },
            {
                'category': 'Regression Testing',
                'tests': [
                    'Existing functionality preservation',
                    'Cross-form compatibility',
                    'Historical data integrity',
                    'System performance'
                ]
            }
        ]
        
        if form_change.severity in ['high', 'critical']:
            requirements.append({
                'category': 'Security Testing',
                'tests': [
                    'Data encryption verification',
                    'Access control validation',
                    'Audit trail functionality',
                    'Compliance verification'
                ]
            })
        
        return requirements
    
    def _create_mitigation_strategy(self, risks: List[Dict], overall_risk: str) -> Dict:
        """Create risk mitigation strategy."""
        strategies = {
            'communication': [],
            'technical': [],
            'process': [],
            'monitoring': []
        }
        
        for risk in risks:
            if risk['category'] == 'Client Impact':
                strategies['communication'].append('Enhanced stakeholder communication')
                strategies['process'].append('Phased rollout approach')
            elif risk['category'] == 'Timeline':
                strategies['process'].append('Accelerated development schedule')
                strategies['monitoring'].append('Daily progress tracking')
            elif risk['category'] == 'Change Severity':
                strategies['technical'].append('Additional code review cycles')
                strategies['process'].append('Extended testing phases')
        
        if overall_risk in ['High', 'Critical']:
            strategies['communication'].extend([
                'Executive stakeholder briefings',
                'Client advisory notifications'
            ])
            strategies['technical'].extend([
                'Parallel development environments',
                'Rollback procedures preparation'
            ])
            strategies['monitoring'].extend([
                'Real-time system monitoring',
                'Dedicated support team assignment'
            ])
        
        return {
            'overall_strategy': f'Implement {overall_risk.lower()}-risk mitigation protocols',
            'action_categories': strategies,
            'key_controls': [
                'Regular progress reviews',
                'Quality gate checkpoints',
                'Stakeholder approval stages',
                'Contingency planning'
            ]
        }
    
    def _generate_recommendations(self, form_change: FormChange, client_impact: Dict, 
                                dev_impact: Dict, risk_assessment: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Client impact recommendations
        if client_impact['percentage_of_client_base'] > 30:
            recommendations.append(
                'Consider phased rollout due to high client impact'
            )
            recommendations.append(
                'Prepare comprehensive client communication materials'
            )
        
        # Development recommendations
        if dev_impact['complexity_level'] in ['High', 'Critical']:
            recommendations.append(
                'Assign senior development resources to this change'
            )
            recommendations.append(
                'Implement additional code review checkpoints'
            )
        
        # Risk-based recommendations
        overall_risk = risk_assessment['overall_risk_level']
        if overall_risk in ['High', 'Critical']:
            recommendations.append(
                'Establish dedicated project management oversight'
            )
            recommendations.append(
                'Prepare rollback procedures before deployment'
            )
        
        # Timeline recommendations
        effective_date = form_change.effective_date
        if effective_date:
            days_until_effective = (effective_date - datetime.utcnow()).days
            if days_until_effective < 45:
                recommendations.append(
                    'Expedite development schedule due to tight timeline'
                )
        
        # Standard recommendations
        recommendations.extend([
            'Follow strict development guidelines for report updates',
            'Implement comprehensive testing across all phases',
            'Maintain detailed documentation throughout process',
            'Plan for 3-month post-release monitoring period'
        ])
        
        return recommendations
    
    def generate_executive_summary(self, form_change_id: int) -> Dict:
        """Generate executive summary for form change impact."""
        analysis = self.analyze_form_change_impact(form_change_id)
        
        return {
            'executive_summary': {
                'form_change_id': form_change_id,
                'agency': analysis['agency_name'],
                'form': analysis['form_name'],
                'change_type': analysis['change_type'],
                'severity': analysis['severity'],
                'overall_risk': analysis['risk_assessment']['overall_risk_level'],
                'clients_impacted': analysis['client_impact']['total_clients_impacted'],
                'client_percentage': analysis['client_impact']['percentage_of_client_base'],
                'estimated_effort_hours': analysis['development_impact']['total_effort_estimate']['estimated_hours'],
                'estimated_completion_date': analysis['timeline_estimation']['estimated_completion_date'],
                'production_release_date': analysis['timeline_estimation']['production_release_date'],
                'key_risks': [risk['description'] for risk in analysis['risk_assessment']['risk_factors'][:3]],
                'top_recommendations': analysis['recommendations'][:5]
            },
            'detailed_analysis': analysis
        }


def generate_impact_report(form_change_id: int) -> Dict:
    """Generate a comprehensive impact report for a form change."""
    analyzer = ImpactAnalyzer()
    return analyzer.generate_executive_summary(form_change_id)


if __name__ == "__main__":
    # Test the impact analyzer
    analyzer = ImpactAnalyzer()
    
    # This would need an actual form change ID from the database
    # report = analyzer.generate_executive_summary(1)
    # print(json.dumps(report, indent=2, default=str))