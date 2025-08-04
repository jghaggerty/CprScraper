"""
Unit tests for EnhancedAnalysisService.

Tests the enhanced AI analysis service with false positive reduction,
semantic change detection, and content relevance validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any

from src.analysis.enhanced_analysis_service import EnhancedAnalysisService
from src.analysis.models import AnalysisRequest, AnalysisResponse, ChangeClassification, SemanticAnalysis


class TestEnhancedAnalysisService:
    """Test cases for EnhancedAnalysisService."""
    
    @pytest.fixture
    def enhanced_service(self):
        """Create an EnhancedAnalysisService instance for testing."""
        with patch('src.analysis.enhanced_analysis_service.AnalysisService.__init__'):
            with patch('src.analysis.enhanced_analysis_service.ChangeAnalyzer'):
                with patch('src.analysis.enhanced_analysis_service.LLMClassifier'):
                    service = EnhancedAnalysisService(
                        false_positive_threshold=0.15,
                        semantic_similarity_threshold=0.85
                    )
                    # Mock the parent class methods
                    service.change_analyzer = Mock()
                    service.llm_classifier = Mock()
                    service.analysis_stats = {
                        "total_analyses": 0,
                        "successful_analyses": 0,
                        "failed_analyses": 0
                    }
                    return service
    
    @pytest.fixture
    def sample_request(self):
        """Create a sample AnalysisRequest for testing."""
        return AnalysisRequest(
            old_content="Original payroll form content",
            new_content="Updated payroll form content",
            form_name="WH-347",
            agency_name="U.S. Department of Labor",
            confidence_threshold=70,
            use_llm_fallback=True
        )
    
    def test_initialization(self, enhanced_service):
        """Test EnhancedAnalysisService initialization."""
        assert enhanced_service.false_positive_threshold == 0.15
        assert enhanced_service.semantic_similarity_threshold == 0.85
        assert "whitespace_only" in enhanced_service.false_positive_patterns
        assert "critical_changes" in enhanced_service.compliance_patterns
        assert enhanced_service.analysis_history == {}
        assert enhanced_service.false_positive_history == {}
    
    def test_detect_false_positives_identical_content(self, enhanced_service):
        """Test false positive detection with identical content."""
        old_content = "This is a test document."
        new_content = "This is a test document."
        
        result = enhanced_service._detect_false_positives(old_content, new_content)
        
        assert result["is_false_positive"] is True
        assert result["confidence"] == 1.0
        assert "content_normalization" in result["patterns"]
    
    def test_detect_false_positives_whitespace_only(self, enhanced_service):
        """Test false positive detection with whitespace-only changes."""
        old_content = "This is a test document."
        new_content = "This is a test document.  "  # Extra whitespace
        
        result = enhanced_service._detect_false_positives(old_content, new_content)
        
        assert result["is_false_positive"] is True
        assert "whitespace_only" in result["patterns"]
        assert result["confidence"] >= 0.4
    
    def test_detect_false_positives_formatting_only(self, enhanced_service):
        """Test false positive detection with formatting-only changes."""
        old_content = "This is a test document."
        new_content = "<p>This is a test document.</p>"
        
        result = enhanced_service._detect_false_positives(old_content, new_content)
        
        assert result["is_false_positive"] is True
        assert "formatting_only" in result["patterns"]
    
    def test_detect_false_positives_dynamic_content(self, enhanced_service):
        """Test false positive detection with dynamic content changes."""
        old_content = "Last updated: 2023-01-01"
        new_content = "Last updated: 2024-01-01"
        
        result = enhanced_service._detect_false_positives(old_content, new_content)
        
        assert result["is_false_positive"] is True
        assert "dynamic_content" in result["patterns"]
    
    def test_detect_false_positives_navigation_changes(self, enhanced_service):
        """Test false positive detection with navigation changes."""
        old_content = "Menu: Home | About | Contact"
        new_content = "Menu: Home | About | Contact | Help"
        
        result = enhanced_service._detect_false_positives(old_content, new_content)
        
        assert result["is_false_positive"] is True
        assert "navigation_elements" in result["patterns"]
    
    def test_detect_false_positives_meaningful_changes(self, enhanced_service):
        """Test false positive detection with meaningful changes."""
        old_content = "Payroll requirements: Submit monthly."
        new_content = "Payroll requirements: Submit weekly with new penalties."
        
        result = enhanced_service._detect_false_positives(old_content, new_content)
        
        assert result["is_false_positive"] is False
        assert result["confidence"] < enhanced_service.false_positive_threshold
    
    def test_normalize_content(self, enhanced_service):
        """Test content normalization."""
        content = "<p>Test <!--comment--> content with 2024-01-01 and v1.2.3</p>"
        normalized = enhanced_service._normalize_content(content)
        
        assert "[DATE]" in normalized
        assert "[VERSION]" in normalized
        assert "<!--comment-->" not in normalized
        assert "<p>" not in normalized
    
    def test_is_whitespace_only_change(self, enhanced_service):
        """Test whitespace-only change detection."""
        old_content = "Test content"
        new_content = "Test  content  "  # Extra spaces
        
        assert enhanced_service._is_whitespace_only_change(old_content, new_content) is True
        
        new_content = "Test content with new words"
        assert enhanced_service._is_whitespace_only_change(old_content, new_content) is False
    
    def test_is_formatting_only_change(self, enhanced_service):
        """Test formatting-only change detection."""
        old_content = "Test content"
        new_content = "<strong>Test content</strong>"
        
        assert enhanced_service._is_formatting_only_change(old_content, new_content) is True
        
        new_content = "Test content with new information"
        assert enhanced_service._is_formatting_only_change(old_content, new_content) is False
    
    def test_is_dynamic_content_change(self, enhanced_service):
        """Test dynamic content change detection."""
        old_content = "Updated: 2023-01-01"
        new_content = "Updated: 2024-01-01"
        
        assert enhanced_service._is_dynamic_content_change(old_content, new_content) is True
        
        old_content = "Requirements: Submit monthly"
        new_content = "Requirements: Submit weekly"
        assert enhanced_service._is_dynamic_content_change(old_content, new_content) is False
    
    def test_is_navigation_change(self, enhanced_service):
        """Test navigation change detection."""
        old_content = "Menu: Home | About"
        new_content = "Menu: Home | About | Contact"
        
        assert enhanced_service._is_navigation_change(old_content, new_content) is True
        
        old_content = "Payroll form requirements"
        new_content = "Updated payroll form requirements"
        assert enhanced_service._is_navigation_change(old_content, new_content) is False
    
    def test_calculate_content_change_ratio(self, enhanced_service):
        """Test content change ratio calculation."""
        old_content = "Line 1\nLine 2\nLine 3"
        new_content = "Line 1\nLine 2\nLine 3\nLine 4"
        
        ratio = enhanced_service._calculate_content_change_ratio(old_content, new_content)
        assert ratio > 0
        assert ratio < 1
    
    def test_detect_semantic_changes(self, enhanced_service):
        """Test semantic change detection."""
        old_content = "Submit payroll reports monthly."
        new_content = "Submit payroll reports weekly with penalties for late submission."
        
        result = enhanced_service._detect_semantic_changes(old_content, new_content)
        
        assert "critical_changes" in result
        assert "structural_changes" in result
        assert "cosmetic_changes" in result
        assert "overall_impact" in result
        assert result["overall_impact"] in ["low", "medium", "high", "critical"]
    
    def test_find_pattern_changes(self, enhanced_service):
        """Test pattern-based change detection."""
        old_content = "Submit monthly reports."
        new_content = "Submit weekly reports with penalties."
        
        patterns = [r'\b(monthly|weekly)\b', r'\b(penalty|penalties)\b']
        changes = enhanced_service._find_pattern_changes(old_content, new_content, patterns)
        
        assert len(changes) > 0
        assert any("Added:" in change for change in changes)
        assert any("Removed:" in change for change in changes)
    
    def test_validate_content_relevance(self, enhanced_service):
        """Test content relevance validation."""
        # Relevant content
        relevant_content = "This is a payroll compliance form with requirements and deadlines."
        result = enhanced_service._validate_content_relevance(relevant_content)
        
        assert result["is_relevant"] is True
        assert result["relevance_percentage"] > 20
        assert "payroll" in result["category_scores"]
        assert "compliance" in result["category_scores"]
        
        # Irrelevant content
        irrelevant_content = "This is a cooking recipe with ingredients and instructions."
        result = enhanced_service._validate_content_relevance(irrelevant_content)
        
        assert result["is_relevant"] is False
        assert result["relevance_percentage"] < 20
    
    @pytest.mark.asyncio
    async def test_analyze_document_changes_enhanced_false_positive(self, enhanced_service, sample_request):
        """Test enhanced analysis with false positive detection."""
        # Mock the parent class method
        with patch.object(enhanced_service, 'analyze_document_changes') as mock_parent:
            # Set up false positive detection
            enhanced_service._detect_false_positives = Mock(return_value={
                "is_false_positive": True,
                "confidence": 0.8,
                "patterns": ["whitespace_only"],
                "reasons": ["Only whitespace changes detected"]
            })
            
            result = await enhanced_service.analyze_document_changes_enhanced(sample_request)
            
            assert result.has_meaningful_changes is False
            assert result.classification.category == "cosmetic_change"
            assert result.classification.subcategory == "false_positive"
            assert result.processing_summary["false_positive_detected"] is True
            assert result.processing_summary["analysis_version"] == "2.0_enhanced"
            
            # Parent method should not be called for false positives
            mock_parent.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_analyze_document_changes_enhanced_meaningful_changes(self, enhanced_service, sample_request):
        """Test enhanced analysis with meaningful changes."""
        # Mock the parent class method
        mock_parent_response = AnalysisResponse(
            analysis_id="test_id",
            timestamp=datetime.utcnow(),
            has_meaningful_changes=True,
            classification=ChangeClassification(
                category="requirement_change",
                severity="high",
                priority_score=80,
                confidence=85,
                is_cosmetic=False
            ),
            semantic_analysis=SemanticAnalysis(
                similarity_score=70,
                significant_differences=["New requirement added"],
                change_indicators=["Compliance impact detected"],
                model_name="test_model",
                processing_time_ms=100
            ),
            llm_analysis=None,
            processing_summary={"processing_time_ms": 100},
            confidence_breakdown={"overall": 85}
        )
        
        with patch.object(enhanced_service, 'analyze_document_changes', return_value=mock_parent_response):
            # Set up false positive detection to return False
            enhanced_service._detect_false_positives = Mock(return_value={
                "is_false_positive": False,
                "confidence": 0.1,
                "patterns": [],
                "reasons": []
            })
            
            result = await enhanced_service.analyze_document_changes_enhanced(sample_request)
            
            assert result.has_meaningful_changes is True
            assert result.processing_summary["false_positive_detected"] is False
            assert result.processing_summary["analysis_version"] == "2.0_enhanced"
            assert "false_positive_score" in result.confidence_breakdown
            assert "relevance_score" in result.confidence_breakdown
            assert "semantic_impact" in result.confidence_breakdown
    
    def test_calculate_semantic_impact_score(self, enhanced_service):
        """Test semantic impact score calculation."""
        semantic_changes = {"overall_impact": "critical"}
        score = enhanced_service._calculate_semantic_impact_score(semantic_changes)
        assert score == 90
        
        semantic_changes = {"overall_impact": "low"}
        score = enhanced_service._calculate_semantic_impact_score(semantic_changes)
        assert score == 20
    
    def test_track_analysis_history(self, enhanced_service):
        """Test analysis history tracking."""
        mock_result = Mock()
        mock_result.timestamp = datetime.utcnow()
        mock_result.has_meaningful_changes = True
        mock_result.confidence_breakdown = {"overall": 85, "false_positive_score": 0.1}
        mock_result.processing_summary = {"false_positive_detected": False}
        
        enhanced_service._track_analysis_history("WH-347", mock_result)
        
        assert "WH-347" in enhanced_service.analysis_history
        assert len(enhanced_service.analysis_history["WH-347"]) == 1
        
        # Test history limit
        for _ in range(15):
            enhanced_service._track_analysis_history("WH-347", mock_result)
        
        assert len(enhanced_service.analysis_history["WH-347"]) == 10
    
    def test_get_enhanced_service_stats(self, enhanced_service):
        """Test enhanced service statistics."""
        # Add some test data
        enhanced_service.analysis_history["WH-347"] = [
            {"confidence": 85, "has_meaningful_changes": True},
            {"confidence": 90, "has_meaningful_changes": False}
        ]
        enhanced_service.false_positive_history["WH-347"] = 1
        
        stats = enhanced_service.get_enhanced_service_stats()
        
        assert "enhanced_features" in stats
        assert "false_positive_stats" in stats
        assert "analysis_history" in stats
        assert stats["enhanced_features"]["false_positive_detection"] is True
        assert stats["false_positive_stats"]["total_false_positives_detected"] == 1
        assert stats["analysis_history"]["total_historical_analyses"] == 2
    
    def test_calculate_average_confidence(self, enhanced_service):
        """Test average confidence calculation."""
        enhanced_service.analysis_history["Form1"] = [
            {"confidence": 80},
            {"confidence": 90}
        ]
        enhanced_service.analysis_history["Form2"] = [
            {"confidence": 70}
        ]
        
        avg_confidence = enhanced_service._calculate_average_confidence()
        assert avg_confidence == 80.0  # (80 + 90 + 70) / 3
    
    def test_get_most_analyzed_forms(self, enhanced_service):
        """Test most analyzed forms retrieval."""
        enhanced_service.analysis_history["Form1"] = [{"confidence": 80}] * 5
        enhanced_service.analysis_history["Form2"] = [{"confidence": 90}] * 3
        enhanced_service.analysis_history["Form3"] = [{"confidence": 70}] * 1
        
        enhanced_service.false_positive_history["Form1"] = 2
        enhanced_service.false_positive_history["Form2"] = 1
        
        most_analyzed = enhanced_service._get_most_analyzed_forms()
        
        assert len(most_analyzed) <= 5
        assert most_analyzed[0]["form_name"] == "Form1"  # Most analyzed
        assert most_analyzed[0]["analysis_count"] == 5
        assert most_analyzed[0]["false_positive_count"] == 2
    
    @pytest.mark.asyncio
    async def test_health_check_enhanced(self, enhanced_service):
        """Test enhanced health check."""
        with patch.object(enhanced_service, 'health_check', return_value={"service": "healthy"}):
            health = await enhanced_service.health_check_enhanced()
            
            assert "enhanced_features" in health
            assert "false_positive_threshold" in health
            assert "semantic_similarity_threshold" in health
            assert health["enhanced_features"]["false_positive_detection"] == "healthy"
            assert health["enhanced_features"]["semantic_change_detection"] == "healthy"
            assert health["enhanced_features"]["content_relevance_validation"] == "healthy"
    
    def test_error_handling_in_false_positive_detection(self, enhanced_service):
        """Test error handling in false positive detection."""
        # Test with None content
        result = enhanced_service._detect_false_positives(None, "test")
        assert result["is_false_positive"] is True
        
        result = enhanced_service._detect_false_positives("test", None)
        assert result["is_false_positive"] is True
    
    def test_error_handling_in_content_relevance_validation(self, enhanced_service):
        """Test error handling in content relevance validation."""
        # Test with None content
        result = enhanced_service._validate_content_relevance(None)
        assert result["is_relevant"] is False
        assert result["relevance_percentage"] == 0
        
        # Test with empty content
        result = enhanced_service._validate_content_relevance("")
        assert result["is_relevant"] is False
        assert result["relevance_percentage"] == 0
    
    @pytest.mark.asyncio
    async def test_analyze_document_changes_enhanced_error_handling(self, enhanced_service, sample_request):
        """Test error handling in enhanced analysis."""
        # Mock an exception in false positive detection
        enhanced_service._detect_false_positives = Mock(side_effect=Exception("Test error"))
        
        with pytest.raises(Exception):
            await enhanced_service.analyze_document_changes_enhanced(sample_request)
        
        assert enhanced_service.analysis_stats["failed_analyses"] == 1 


class TestEnhancedAnalysisServiceContentValidation:
    """Test content validation functionality in EnhancedAnalysisService."""
    
    @pytest.fixture
    def service(self):
        """Create EnhancedAnalysisService instance for testing."""
        return EnhancedAnalysisService(
            semantic_model="all-MiniLM-L6-v2",
            llm_model="gpt-3.5-turbo",
            false_positive_threshold=0.15,
            semantic_similarity_threshold=0.85
        )
    
    def test_validate_content_relevance_wh_347_form(self, service):
        """Test content relevance validation for WH-347 form."""
        content = """
        WH-347 Statement of Compliance for Federal and Federally Assisted Construction Projects
        This form is used to certify payroll compliance for federal construction contracts.
        The contractor must submit certified payroll reports showing prevailing wage rates.
        """
        
        result = service._validate_content_relevance(content, "WH-347", "Department of Labor")
        
        assert result["is_relevant"] is True
        assert result["relevance_percentage"] > 15
        assert "wh_347" in result["form_matches"]
        assert len(result["form_matches"]["wh_347"]) > 0
        assert result["overall_confidence"] > 50
        assert result["validation_details"]["core_compliance_terms"] >= 2
    
    def test_validate_content_relevance_ca_a1_131_form(self, service):
        """Test content relevance validation for CA A1-131 form."""
        content = """
        A1-131 California Certified Payroll Report
        Department of Industrial Relations - Public Works
        This form certifies compliance with prevailing wage requirements.
        """
        
        result = service._validate_content_relevance(content, "A1-131", "California DIR")
        
        assert result["is_relevant"] is True
        assert result["relevance_percentage"] > 15
        assert "ca_a1_131" in result["form_matches"]
        assert len(result["form_matches"]["ca_a1_131"]) > 0
        assert result["overall_confidence"] > 50
    
    def test_validate_content_relevance_irrelevant_content(self, service):
        """Test content relevance validation for irrelevant content."""
        content = """
        Welcome to our company website.
        We provide various services including marketing and consulting.
        Contact us for more information about our offerings.
        """
        
        result = service._validate_content_relevance(content, "Company Website", "Business")
        
        assert result["is_relevant"] is False
        assert result["relevance_percentage"] < 15
        assert result["overall_confidence"] < 50
        assert result["validation_details"]["core_compliance_terms"] == 0
    
    def test_validate_content_relevance_partial_compliance_content(self, service):
        """Test content relevance validation for content with some compliance terms."""
        content = """
        Employee handbook and company policies.
        This document covers payroll procedures and employee benefits.
        Please review the wage and hour requirements.
        """
        
        result = service._validate_content_relevance(content, "Employee Handbook", "Company")
        
        # Should be relevant due to payroll and wage terms
        assert result["is_relevant"] is True
        assert result["category_scores"]["payroll_core"] > 0
        assert result["category_scores"]["wage_rates"] > 0
        assert result["overall_confidence"] > 25
    
    def test_validate_compliance_specific_content_certification_requirements(self, service):
        """Test compliance-specific validation for certification requirements."""
        content = """
        I certify under penalty of perjury that the information provided is true and correct.
        This certification is made under the authority of the prevailing wage laws.
        """
        
        result = service._validate_compliance_specific_content(content, "Certification", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["certification_requirements"]["is_compliant"] is True
        assert result["validation_results"]["certification_requirements"]["severity"] == "critical"
        assert len(result["validation_results"]["certification_requirements"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_wage_rate_requirements(self, service):
        """Test compliance-specific validation for wage rate requirements."""
        content = """
        The prevailing wage rate for this classification is $25.00 per hour.
        All workers must be paid at least the minimum wage rate.
        Base rates and premium rates are specified in the wage determination.
        """
        
        result = service._validate_compliance_specific_content(content, "Wage Rates", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["wage_rate_requirements"]["is_compliant"] is True
        assert result["validation_results"]["wage_rate_requirements"]["severity"] == "high"
        assert len(result["validation_results"]["wage_rate_requirements"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_reporting_deadlines(self, service):
        """Test compliance-specific validation for reporting deadlines."""
        content = """
        Certified payroll reports must be submitted by the 15th of each month.
        The filing deadline is within 7 days of the end of the pay period.
        Due date for submission is 01/15/2024.
        """
        
        result = service._validate_compliance_specific_content(content, "Deadlines", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["reporting_deadlines"]["is_compliant"] is True
        assert result["validation_results"]["reporting_deadlines"]["severity"] == "high"
        assert len(result["validation_results"]["reporting_deadlines"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_employee_identification(self, service):
        """Test compliance-specific validation for employee identification."""
        content = """
        Employee name: John Doe
        Social Security Number: XXX-XX-1234
        Employee ID: 12345
        Craft classification: Electrician
        """
        
        result = service._validate_compliance_specific_content(content, "Employee Info", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["employee_identification"]["is_compliant"] is True
        assert result["validation_results"]["employee_identification"]["severity"] == "medium"
        assert len(result["validation_results"]["employee_identification"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_time_tracking(self, service):
        """Test compliance-specific validation for time tracking requirements."""
        content = """
        Hours worked: 40
        Daily hours: 8
        Weekly hours: 40
        Overtime hours: 5
        Straight time: 40
        """
        
        result = service._validate_compliance_specific_content(content, "Time Tracking", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["time_tracking_requirements"]["is_compliant"] is True
        assert result["validation_results"]["time_tracking_requirements"]["severity"] == "medium"
        assert len(result["validation_results"]["time_tracking_requirements"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_fringe_benefits(self, service):
        """Test compliance-specific validation for fringe benefits."""
        content = """
        Fringe benefits include health insurance and pension contributions.
        Vacation pay and holiday pay are provided.
        Bonus and incentive payments are included.
        """
        
        result = service._validate_compliance_specific_content(content, "Benefits", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["fringe_benefits"]["is_compliant"] is True
        assert result["validation_results"]["fringe_benefits"]["severity"] == "medium"
        assert len(result["validation_results"]["fringe_benefits"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_penalty_provisions(self, service):
        """Test compliance-specific validation for penalty provisions."""
        content = """
        Violations may result in penalties and fines.
        Enforcement actions include investigation and audit.
        Sanctions may be imposed for non-compliance.
        """
        
        result = service._validate_compliance_specific_content(content, "Penalties", "Agency")
        
        assert result["overall_compliance_score"] > 50
        assert result["validation_results"]["penalty_provisions"]["is_compliant"] is True
        assert result["validation_results"]["penalty_provisions"]["severity"] == "high"
        assert len(result["validation_results"]["penalty_provisions"]["patterns_found"]) > 0
    
    def test_validate_compliance_specific_content_low_compliance(self, service):
        """Test compliance-specific validation for content with low compliance."""
        content = """
        General information about construction projects.
        Contact information and project details.
        No specific compliance requirements mentioned.
        """
        
        result = service._validate_compliance_specific_content(content, "General Info", "Agency")
        
        assert result["overall_compliance_score"] < 50
        assert result["compliant_checks"] < result["total_checks"] / 2
        assert result["compliance_summary"]["critical_checks"] == 0
    
    def test_validate_form_structure_integrity_complete_form(self, service):
        """Test form structure integrity validation for a complete form."""
        content = """
        FORM WH-347
        Statement of Compliance for Federal Construction Projects
        
        Section 1: Employee Information
        Name: ________________
        Address: ______________
        SSN: _________________
        
        Section 2: Wage Information
        Rate: $25.00/hour
        Hours: 40
        Date: 01/15/2024
        
        CERTIFICATION
        I certify under penalty of perjury that the above information is true and correct.
        Signature: ________________
        Date: ________________
        
        INSTRUCTIONS
        Complete all sections and submit by the 15th of each month.
        """
        
        result = service._validate_form_structure_integrity(content, "WH-347")
        
        assert result["structure_integrity_score"] > 70
        assert result["has_required_elements"] is True
        assert len(result["missing_required_elements"]) == 0
        assert result["structure_results"]["form_header"]["is_present"] is True
        assert result["structure_results"]["section_headers"]["is_present"] is True
        assert result["structure_results"]["data_fields"]["is_present"] is True
        assert result["structure_results"]["certification_block"]["is_present"] is True
    
    def test_validate_form_structure_integrity_incomplete_form(self, service):
        """Test form structure integrity validation for an incomplete form."""
        content = """
        Some general information about a project.
        No clear form structure or required elements.
        Missing certification and data fields.
        """
        
        result = service._validate_form_structure_integrity(content, "Incomplete Form")
        
        assert result["structure_integrity_score"] < 50
        assert result["has_required_elements"] is False
        assert len(result["missing_required_elements"]) > 0
        assert result["structure_results"]["certification_block"]["is_present"] is False
        assert result["structure_results"]["data_fields"]["is_present"] is False
    
    def test_validate_form_structure_integrity_partial_form(self, service):
        """Test form structure integrity validation for a partial form."""
        content = """
        FORM A1-131
        California Certified Payroll Report
        
        Employee Name: John Doe
        Rate: $30.00/hour
        Hours: 40
        
        I certify this information is correct.
        """
        
        result = service._validate_form_structure_integrity(content, "A1-131")
        
        assert result["structure_integrity_score"] > 30
        assert result["structure_results"]["form_header"]["is_present"] is True
        assert result["structure_results"]["data_fields"]["is_present"] is True
        assert result["structure_results"]["certification_block"]["is_present"] is True
        # May be missing some required elements
        assert len(result["missing_required_elements"]) >= 0
    
    def test_validate_form_structure_integrity_no_form_elements(self, service):
        """Test form structure integrity validation for content with no form elements."""
        content = """
        This is just a regular document with no form structure.
        It contains general information but no form fields or sections.
        There are no certification blocks or data entry areas.
        """
        
        result = service._validate_form_structure_integrity(content, "Regular Document")
        
        assert result["structure_integrity_score"] < 30
        assert result["has_required_elements"] is False
        assert len(result["missing_required_elements"]) > 0
        assert result["structure_results"]["form_header"]["is_present"] is False
        assert result["structure_results"]["data_fields"]["is_present"] is False
    
    def test_validate_content_relevance_edge_cases(self, service):
        """Test content relevance validation with edge cases."""
        # Empty content
        result = service._validate_content_relevance("", "Empty", "Agency")
        assert result["is_relevant"] is False
        assert result["relevance_percentage"] == 0
        
        # Very short content
        result = service._validate_content_relevance("payroll", "Short", "Agency")
        assert result["is_relevant"] is True  # Contains core term
        
        # Very long content with mixed relevance
        long_content = "payroll " * 100 + "construction " * 50 + "unrelated " * 200
        result = service._validate_content_relevance(long_content, "Long", "Agency")
        assert result["is_relevant"] is True
        assert result["category_scores"]["payroll_core"] > 0
        assert result["category_scores"]["construction_labor"] > 0
    
    def test_validate_compliance_specific_content_edge_cases(self, service):
        """Test compliance-specific validation with edge cases."""
        # Empty content
        result = service._validate_compliance_specific_content("", "Empty", "Agency")
        assert result["overall_compliance_score"] == 0
        assert result["compliant_checks"] == 0
        
        # Content with only one compliance area
        content = "I certify this information is correct."
        result = service._validate_compliance_specific_content(content, "Certification Only", "Agency")
        assert result["overall_compliance_score"] > 0
        assert result["validation_results"]["certification_requirements"]["is_compliant"] is True
        
        # Content with all compliance areas
        comprehensive_content = """
        The prevailing wage rate is $25.00 per hour.
        I certify under penalty of perjury that this information is correct.
        Reports must be submitted by the 15th of each month.
        Employee name: John Doe, SSN: XXX-XX-1234
        Hours worked: 40, overtime: 5
        Fringe benefits include health insurance and pension.
        Violations may result in penalties and fines.
        """
        result = service._validate_compliance_specific_content(comprehensive_content, "Comprehensive", "Agency")
        assert result["overall_compliance_score"] > 80
        assert result["compliant_checks"] > result["total_checks"] * 0.8
    
    def test_validate_form_structure_integrity_edge_cases(self, service):
        """Test form structure integrity validation with edge cases."""
        # Empty content
        result = service._validate_form_structure_integrity("", "Empty")
        assert result["structure_integrity_score"] == 0
        assert result["has_required_elements"] is False
        
        # Content with only form header
        content = "FORM WH-347"
        result = service._validate_form_structure_integrity(content, "Header Only")
        assert result["structure_integrity_score"] > 0
        assert result["structure_results"]["form_header"]["is_present"] is True
        assert result["structure_results"]["data_fields"]["is_present"] is False
        
        # Content with all elements but minimal
        content = "FORM WH-347\nName:\nRate:\nI certify\nInstructions"
        result = service._validate_form_structure_integrity(content, "Minimal Complete")
        assert result["structure_integrity_score"] > 50
        assert result["has_required_elements"] is True 