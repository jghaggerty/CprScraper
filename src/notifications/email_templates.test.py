"""
Unit tests for enhanced email notification templates.
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.notifications.email_templates import EnhancedEmailTemplates


class TestEnhancedEmailTemplates:
    """Test the enhanced email templates."""
    
    @pytest.fixture
    def template_manager(self):
        """Create a template manager instance."""
        return EnhancedEmailTemplates()
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for template testing."""
        return {
            'detected_at': '2024-01-15 10:30:00 UTC',
            'generated_at': '2024-01-15 10:31:00 UTC',
            'change_id': 123,
            'severity': 'high',
            'agency_name': 'Test Department of Labor',
            'form_name': 'WH-347',
            'cpr_report_id': 'WH347-2024',
            'change_type': 'content',
            'change_description': 'Updated wage determination requirements for construction projects',
            'effective_date': '2024-02-01',
            'form_url': 'https://example.com/wh347-specs',
            'instructions_url': 'https://example.com/wh347-instructions',
            'agency_contact_email': 'dol@example.com',
            'agency_contact_phone': '(555) 123-4567',
            'clients_impacted': 25,
            'icp_percentage': 15.5,
            'impact_details': [
                'Form used by 25 active construction clients',
                'Represents 15.5% of total client base',
                'High impact on prevailing wage calculations'
            ],
            'field_mapping_current': True,
            'field_mapping_updated': True,
            'ai_confidence_score': 92,
            'ai_change_category': 'requirement_change',
            'ai_severity_score': 85,
            'ai_reasoning': 'This change modifies core wage determination logic which affects all construction projects. The AI analysis indicates this is a significant requirement change that will impact client workflows.',
            'ai_semantic_similarity': 78,
            'is_cosmetic_change': False,
            'old_value': 'old_wage_determination_logic',
            'new_value': 'new_wage_determination_logic'
        }
    
    def test_template_manager_initialization(self, template_manager):
        """Test that template manager initializes correctly."""
        assert template_manager is not None
        assert hasattr(template_manager, 'templates')
        assert len(template_manager.templates) == 4
    
    def test_get_available_templates(self, template_manager):
        """Test getting list of available templates."""
        templates = template_manager.get_available_templates()
        expected_templates = ['product_manager', 'business_analyst', 'executive_summary', 'technical_detailed']
        
        assert len(templates) == 4
        for template in expected_templates:
            assert template in templates
    
    def test_get_template_default(self, template_manager):
        """Test getting default template."""
        template = template_manager.get_template()
        assert template is not None
    
    def test_get_template_specific(self, template_manager):
        """Test getting specific templates."""
        pm_template = template_manager.get_template('product_manager')
        ba_template = template_manager.get_template('business_analyst')
        exec_template = template_manager.get_template('executive_summary')
        tech_template = template_manager.get_template('technical_detailed')
        
        assert pm_template is not None
        assert ba_template is not None
        assert exec_template is not None
        assert tech_template is not None
    
    def test_get_template_invalid(self, template_manager):
        """Test getting invalid template returns default."""
        template = template_manager.get_template('invalid_template')
        default_template = template_manager.get_template('product_manager')
        assert template == default_template
    
    def test_product_manager_template_rendering(self, template_manager, sample_data):
        """Test product manager template renders correctly."""
        html_content = template_manager.render_template('product_manager', sample_data)
        
        # Check for key elements
        assert '🚨 Certified Payroll Report Change Alert' in html_content
        assert 'HIGH PRIORITY' in html_content
        assert 'Test Department of Labor' in html_content
        assert 'WH-347' in html_content
        assert 'Updated wage determination requirements' in html_content
        assert '25' in html_content  # clients impacted
        assert '15.5%' in html_content  # ICP percentage
        assert '92%' in html_content  # AI confidence
        assert 'requirement_change' in html_content
        assert 'AI Analysis' in html_content
        assert 'Impact Assessment' in html_content
        assert 'Required Actions' in html_content
    
    def test_business_analyst_template_rendering(self, template_manager, sample_data):
        """Test business analyst template renders correctly."""
        html_content = template_manager.render_template('business_analyst', sample_data)
        
        # Check for key elements
        assert '🔍 Technical Analysis - Payroll Report Change' in html_content
        assert 'SEVERITY: HIGH' in html_content
        assert 'Test Department of Labor' in html_content
        assert 'WH-347' in html_content
        assert 'Technical Analysis' in html_content
        assert 'Analysis Requirements' in html_content
        assert '85/100' in html_content  # AI severity score
        assert '78%' in html_content  # semantic similarity
        assert 'old_wage_determination_logic' in html_content
        assert 'new_wage_determination_logic' in html_content
    
    def test_executive_summary_template_rendering(self, template_manager, sample_data):
        """Test executive summary template renders correctly."""
        html_content = template_manager.render_template('executive_summary', sample_data)
        
        # Check for key elements
        assert 'Executive Summary' in html_content
        assert 'HIGH Priority Change Detected' in html_content
        assert 'Test Department of Labor' in html_content
        assert 'WH-347' in html_content
        assert 'Change Overview' in html_content
        assert 'Business Impact' in html_content
        assert 'Next Steps' in html_content
        assert '25' in html_content  # clients affected
        assert '15.5%' in html_content  # ICP segment
        assert '92%' in html_content  # AI confidence
    
    def test_technical_detailed_template_rendering(self, template_manager, sample_data):
        """Test technical detailed template renders correctly."""
        html_content = template_manager.render_template('technical_detailed', sample_data)
        
        # Check for key elements
        assert 'Technical Details - Payroll Report Change' in html_content
        assert 'HIGH' in html_content
        assert 'Test Department of Labor' in html_content
        assert 'WH-347' in html_content
        assert 'Change Information' in html_content
        assert 'AI Analysis' in html_content
        assert 'Impact Assessment' in html_content
        assert 'Technical Implementation' in html_content
        assert '92%' in html_content  # confidence score
        assert '85/100' in html_content  # severity score
    
    def test_template_with_missing_data(self, template_manager):
        """Test template rendering with minimal data."""
        minimal_data = {
            'detected_at': '2024-01-15 10:30:00 UTC',
            'severity': 'medium',
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'change_type': 'test',
            'change_description': 'Test change',
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'ai_confidence_score': 75,
            'ai_severity_score': 60,
            'ai_semantic_similarity': 70,
            'is_cosmetic_change': False
        }
        
        html_content = template_manager.render_template('product_manager', minimal_data)
        
        # Should render without errors
        assert 'Test Agency' in html_content
        assert 'TEST-001' in html_content
        assert 'Test change' in html_content
        assert '75%' in html_content
    
    def test_template_with_none_values(self, template_manager):
        """Test template rendering with None values."""
        data_with_nones = {
            'detected_at': '2024-01-15 10:30:00 UTC',
            'severity': 'low',
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'cpr_report_id': None,
            'change_type': 'test',
            'change_description': 'Test change',
            'effective_date': None,
            'form_url': None,
            'instructions_url': None,
            'agency_contact_email': 'test@example.com',
            'agency_contact_phone': None,
            'clients_impacted': 0,
            'icp_percentage': 0,
            'impact_details': [],
            'ai_confidence_score': 0,
            'ai_change_category': None,
            'ai_severity_score': 0,
            'ai_reasoning': None,
            'ai_semantic_similarity': 0,
            'is_cosmetic_change': False,
            'old_value': None,
            'new_value': None
        }
        
        html_content = template_manager.render_template('business_analyst', data_with_nones)
        
        # Should render without errors
        assert 'Test Agency' in html_content
        assert 'TEST-001' in html_content
        assert 'N/A' in html_content  # for None values
        assert '0' in html_content  # for zero values
    
    def test_severity_styling(self, template_manager, sample_data):
        """Test that different severities render with correct styling."""
        severities = ['critical', 'high', 'medium', 'low']
        
        for severity in severities:
            test_data = sample_data.copy()
            test_data['severity'] = severity
            
            html_content = template_manager.render_template('product_manager', test_data)
            
            # Check that severity is displayed
            assert severity.upper() in html_content
            assert f'severity-{severity}' in html_content
    
    def test_ai_analysis_section(self, template_manager, sample_data):
        """Test AI analysis section renders correctly."""
        html_content = template_manager.render_template('product_manager', sample_data)
        
        # Check AI analysis elements
        assert 'AI Confidence Score' in html_content
        assert '92%' in html_content
        assert 'requirement_change' in html_content
        assert 'AI Reasoning' in html_content
        assert 'wage determination logic' in html_content
    
    def test_impact_assessment_section(self, template_manager, sample_data):
        """Test impact assessment section renders correctly."""
        html_content = template_manager.render_template('product_manager', sample_data)
        
        # Check impact assessment elements
        assert 'Impact Assessment' in html_content
        assert '25' in html_content  # clients impacted
        assert '15.5%' in html_content  # ICP percentage
        assert '85/100' in html_content  # AI severity score
        assert '78%' in html_content  # semantic similarity
        assert 'construction clients' in html_content  # impact details
    
    def test_action_items_section(self, template_manager, sample_data):
        """Test action items section renders correctly."""
        html_content = template_manager.render_template('product_manager', sample_data)
        
        # Check action items elements
        assert 'Required Actions' in html_content
        assert 'Development Process' in html_content
        assert 'Evaluation' in html_content
        assert 'Development' in html_content
        assert 'QA' in html_content
        assert 'EUT' in html_content
        assert 'Production' in html_content
        assert 'Monitoring' in html_content
    
    def test_resources_section(self, template_manager, sample_data):
        """Test resources section renders correctly."""
        html_content = template_manager.render_template('product_manager', sample_data)
        
        # Check resources elements
        assert 'Resources' in html_content
        assert 'Report Specifications' in html_content
        assert 'Report Instructions' in html_content
        assert 'dol@example.com' in html_content
        assert '(555) 123-4567' in html_content
        assert 'field mapping' in html_content
    
    def test_mobile_responsive_elements(self, template_manager, sample_data):
        """Test that templates include mobile responsive CSS."""
        html_content = template_manager.render_template('product_manager', sample_data)
        
        # Check for responsive design elements
        assert '@media' in html_content
        assert 'max-width' in html_content
        assert 'grid-template-columns' in html_content
    
    def test_template_performance(self, template_manager, sample_data):
        """Test template rendering performance."""
        import time
        
        start_time = time.time()
        for _ in range(10):
            html_content = template_manager.render_template('product_manager', sample_data)
        end_time = time.time()
        
        # Should render 10 templates in under 1 second
        assert (end_time - start_time) < 1.0
        assert len(html_content) > 1000  # Should generate substantial HTML
    
    def test_all_templates_with_complete_data(self, template_manager, sample_data):
        """Test all templates render with complete data."""
        template_types = ['product_manager', 'business_analyst', 'executive_summary', 'technical_detailed']
        
        for template_type in template_types:
            html_content = template_manager.render_template(template_type, sample_data)
            
            # Each template should generate substantial HTML
            assert len(html_content) > 500
            assert 'Test Department of Labor' in html_content
            assert 'WH-347' in html_content
            assert 'Updated wage determination requirements' in html_content


class TestTemplateDataHandling:
    """Test template data handling and edge cases."""
    
    @pytest.fixture
    def template_manager(self):
        return EnhancedEmailTemplates()
    
    def test_empty_impact_details(self, template_manager):
        """Test template with empty impact details."""
        data = {
            'detected_at': '2024-01-15 10:30:00 UTC',
            'severity': 'medium',
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'change_type': 'test',
            'change_description': 'Test change',
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'ai_confidence_score': 75,
            'ai_severity_score': 60,
            'ai_semantic_similarity': 70,
            'is_cosmetic_change': False,
            'impact_details': []
        }
        
        html_content = template_manager.render_template('product_manager', data)
        assert 'Test Agency' in html_content
        assert '5' in html_content
        assert '2.5%' in html_content
    
    def test_long_text_handling(self, template_manager):
        """Test template with very long text fields."""
        long_description = "This is a very long change description that contains many words and should be handled properly by the template. " * 10
        
        data = {
            'detected_at': '2024-01-15 10:30:00 UTC',
            'severity': 'high',
            'agency_name': 'Test Agency',
            'form_name': 'TEST-001',
            'change_type': 'test',
            'change_description': long_description,
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'ai_confidence_score': 75,
            'ai_severity_score': 60,
            'ai_semantic_similarity': 70,
            'is_cosmetic_change': False,
            'ai_reasoning': long_description
        }
        
        html_content = template_manager.render_template('business_analyst', data)
        assert 'Test Agency' in html_content
        assert 'very long change description' in html_content
    
    def test_special_characters(self, template_manager):
        """Test template with special characters in data."""
        data = {
            'detected_at': '2024-01-15 10:30:00 UTC',
            'severity': 'medium',
            'agency_name': 'Test Agency & Partners, LLC',
            'form_name': 'TEST-001 (v2.0)',
            'change_type': 'test',
            'change_description': 'Updated requirements for "special" projects & compliance',
            'clients_impacted': 5,
            'icp_percentage': 2.5,
            'ai_confidence_score': 75,
            'ai_severity_score': 60,
            'ai_semantic_similarity': 70,
            'is_cosmetic_change': False
        }
        
        html_content = template_manager.render_template('product_manager', data)
        assert 'Test Agency & Partners, LLC' in html_content
        assert 'TEST-001 (v2.0)' in html_content
        assert 'Updated requirements for "special" projects & compliance' in html_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 