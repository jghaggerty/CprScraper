"""
Unit tests for Change Classification System

Tests the comprehensive change classification functionality for certified payroll
compliance monitoring, including severity and type classification.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from .change_classifier import (
    ChangeClassifier, ChangeSeverity, ChangeType, get_change_classifier
)


class TestChangeSeverity:
    """Test suite for ChangeSeverity enum."""
    
    def test_severity_values(self):
        """Test that severity enum has correct values."""
        assert ChangeSeverity.CRITICAL.value == "critical"
        assert ChangeSeverity.IMPORTANT.value == "important"
        assert ChangeSeverity.INFORMATIONAL.value == "informational"
        assert ChangeSeverity.COSMETIC.value == "cosmetic"


class TestChangeType:
    """Test suite for ChangeType enum."""
    
    def test_type_values(self):
        """Test that change type enum has correct values."""
        assert ChangeType.FORM_STRUCTURE.value == "form_structure"
        assert ChangeType.FIELD_ADDITION.value == "field_addition"
        assert ChangeType.FIELD_REMOVAL.value == "field_removal"
        assert ChangeType.COMPLIANCE_REQUIREMENT.value == "compliance_requirement"
        assert ChangeType.COSMETIC_UPDATE.value == "cosmetic_update"
        assert ChangeType.UNKNOWN.value == "unknown"


class TestChangeClassifier:
    """Test suite for ChangeClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create a change classifier instance for testing."""
        return ChangeClassifier()
    
    def test_classifier_initialization(self, classifier):
        """Test classifier initialization with classification rules."""
        assert classifier is not None
        assert hasattr(classifier, 'severity_keywords')
        assert hasattr(classifier, 'type_patterns')
        assert hasattr(classifier, 'compliance_impact_scores')
        
        # Check that all severity levels are defined
        assert ChangeSeverity.CRITICAL in classifier.severity_keywords
        assert ChangeSeverity.IMPORTANT in classifier.severity_keywords
        assert ChangeSeverity.INFORMATIONAL in classifier.severity_keywords
        assert ChangeSeverity.COSMETIC in classifier.severity_keywords
        
        # Check that all change types are defined
        assert ChangeType.FORM_STRUCTURE in classifier.type_patterns
        assert ChangeType.FIELD_ADDITION in classifier.type_patterns
        assert ChangeType.COMPLIANCE_REQUIREMENT in classifier.type_patterns
    
    def test_classify_change_critical_severity(self, classifier):
        """Test classification of critical severity changes."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "Critical deadline change with penalty for non-compliance"
        form_name = "WH-347"
        agency_name = "Department of Labor"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["severity"] == "critical"
        assert result["severity_confidence"] >= 60
        assert result["compliance_impact_score"] >= 8
        assert result["classification_method"] == "rule_based"
        assert "critical" in result["reasoning"].lower()
    
    def test_classify_change_important_severity(self, classifier):
        """Test classification of important severity changes."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "Important requirement change for form validation"
        form_name = "A1-131"
        agency_name = "California DIR"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["severity"] == "important"
        assert result["severity_confidence"] >= 60
        assert result["classification_method"] == "rule_based"
        assert "important" in result["reasoning"].lower()
    
    def test_classify_change_informational_severity(self, classifier):
        """Test classification of informational severity changes."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "Informational update to form instructions"
        form_name = "Test Form"
        agency_name = "Test Agency"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["severity"] == "informational"
        assert result["severity_confidence"] >= 30
        assert result["classification_method"] == "rule_based"
    
    def test_classify_change_cosmetic_severity(self, classifier):
        """Test classification of cosmetic severity changes."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "Cosmetic formatting update to form layout"
        form_name = "Test Form"
        agency_name = "Test Agency"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["severity"] == "cosmetic"
        assert result["is_cosmetic"] == True
        assert result["severity_confidence"] >= 60
        assert result["classification_method"] == "rule_based"
    
    def test_classify_change_type_field_addition(self, classifier):
        """Test classification of field addition changes."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "New required field added to form structure"
        form_name = "WH-347"
        agency_name = "Department of Labor"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["change_type"] == "field_addition"
        assert result["type_confidence"] >= 70
        assert result["classification_method"] == "rule_based"
    
    def test_classify_change_type_compliance_requirement(self, classifier):
        """Test classification of compliance requirement changes."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "New compliance regulation requires additional validation"
        form_name = "A1-131"
        agency_name = "California DIR"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["change_type"] == "compliance_requirement"
        assert result["type_confidence"] >= 70
        assert result["compliance_impact_score"] >= 9
        assert result["classification_method"] == "rule_based"
    
    def test_classify_change_type_penalty_change(self, classifier):
        """Test classification of penalty change."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "Updated penalty structure for violations"
        form_name = "WH-347"
        agency_name = "Department of Labor"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["change_type"] == "penalty_change"
        assert result["type_confidence"] >= 70
        assert result["compliance_impact_score"] >= 9
        assert result["classification_method"] == "rule_based"
    
    def test_classify_change_type_unknown(self, classifier):
        """Test classification when no specific type is detected."""
        old_content = "Old form content"
        new_content = "New form content"
        change_description = "Some random change without specific keywords"
        form_name = "Test Form"
        agency_name = "Test Agency"
        
        result = classifier.classify_change(
            old_content, new_content, change_description, form_name, agency_name
        )
        
        assert result["change_type"] == "unknown"
        assert result["type_confidence"] == 30
        assert result["classification_method"] == "rule_based"
    
    def test_classify_change_with_exception(self, classifier):
        """Test classification when an exception occurs."""
        with patch.object(classifier, '_classify_severity', side_effect=Exception("Test error")):
            result = classifier.classify_change(
                "old", "new", "test", "form", "agency"
            )
            
            assert result["severity"] == "informational"
            assert result["change_type"] == "unknown"
            assert result["classification_method"] == "default"
            assert "error" in result["reasoning"].lower()
    
    def test_calculate_compliance_impact_critical(self, classifier):
        """Test compliance impact calculation for critical changes."""
        impact = classifier._calculate_compliance_impact(
            ChangeType.COMPLIANCE_REQUIREMENT, ChangeSeverity.CRITICAL
        )
        
        # Base score 10 * 1.2 multiplier = 12, capped at 100
        assert impact == 12
    
    def test_calculate_compliance_impact_cosmetic(self, classifier):
        """Test compliance impact calculation for cosmetic changes."""
        impact = classifier._calculate_compliance_impact(
            ChangeType.COSMETIC_UPDATE, ChangeSeverity.COSMETIC
        )
        
        # Base score 1 * 0.2 multiplier = 0.2, rounded to 0
        assert impact == 0
    
    def test_is_cosmetic_change_explicit(self, classifier):
        """Test cosmetic change detection with explicit keyword."""
        is_cosmetic = classifier._is_cosmetic_change(
            "old content", "new content", "This is a cosmetic update"
        )
        
        assert is_cosmetic == True
    
    def test_is_cosmetic_change_keywords(self, classifier):
        """Test cosmetic change detection with cosmetic keywords."""
        is_cosmetic = classifier._is_cosmetic_change(
            "old content", "new content", "Formatting changes to layout"
        )
        
        assert is_cosmetic == True
    
    def test_is_cosmetic_change_similar_content(self, classifier):
        """Test cosmetic change detection with very similar content."""
        old_content = "This is the form content with some data"
        new_content = "This is the form content with some data"  # Identical
        
        is_cosmetic = classifier._is_cosmetic_change(
            old_content, new_content, "Some change description"
        )
        
        assert is_cosmetic == True
    
    def test_is_cosmetic_change_different_content(self, classifier):
        """Test cosmetic change detection with different content."""
        old_content = "This is the old form content"
        new_content = "This is completely different new content"
        
        is_cosmetic = classifier._is_cosmetic_change(
            old_content, new_content, "Some change description"
        )
        
        assert is_cosmetic == False
    
    def test_calculate_similarity_identical(self, classifier):
        """Test similarity calculation for identical text."""
        similarity = classifier._calculate_similarity("test", "test")
        assert similarity == 1.0
    
    def test_calculate_similarity_different(self, classifier):
        """Test similarity calculation for different text."""
        similarity = classifier._calculate_similarity("test", "different")
        assert similarity < 1.0
    
    def test_calculate_similarity_empty(self, classifier):
        """Test similarity calculation with empty strings."""
        similarity = classifier._calculate_similarity("", "")
        assert similarity == 0.0
    
    def test_generate_classification_reasoning(self, classifier):
        """Test reasoning generation for classification."""
        reasoning = classifier._generate_classification_reasoning(
            ChangeSeverity.CRITICAL,
            ChangeType.COMPLIANCE_REQUIREMENT,
            "Critical compliance requirement change",
            95
        )
        
        assert "critical" in reasoning.lower()
        assert "compliance_requirement" in reasoning.lower()
        assert "95/100" in reasoning
        assert "immediate attention" in reasoning.lower()
    
    def test_get_default_classification(self, classifier):
        """Test default classification when analysis fails."""
        result = classifier._get_default_classification()
        
        assert result["severity"] == "informational"
        assert result["change_type"] == "unknown"
        assert result["severity_confidence"] == 30
        assert result["type_confidence"] == 30
        assert result["compliance_impact_score"] == 5
        assert result["is_cosmetic"] == False
        assert result["classification_method"] == "default"
        assert "error" in result["reasoning"].lower()
    
    def test_enhance_with_ai_classification_no_ai(self, classifier):
        """Test enhancement when no AI analysis is provided."""
        rule_based_result = {
            "severity": "important",
            "change_type": "field_addition",
            "severity_confidence": 70,
            "type_confidence": 80,
            "compliance_impact_score": 7,
            "is_cosmetic": False,
            "reasoning": "Rule-based classification",
            "classification_method": "rule_based"
        }
        
        enhanced = classifier.enhance_with_ai_classification(rule_based_result, None)
        
        assert enhanced == rule_based_result
    
    def test_enhance_with_ai_classification_higher_confidence(self, classifier):
        """Test enhancement when AI has higher confidence."""
        rule_based_result = {
            "severity": "important",
            "change_type": "field_addition",
            "severity_confidence": 70,
            "type_confidence": 80,
            "compliance_impact_score": 7,
            "is_cosmetic": False,
            "reasoning": "Rule-based classification",
            "classification_method": "rule_based"
        }
        
        ai_analysis = {
            "severity": "critical",
            "severity_confidence": 90,
            "change_type": "compliance_requirement",
            "type_confidence": 95,
            "compliance_impact_score": 9,
            "is_cosmetic": False,
            "reasoning": "AI analysis reasoning"
        }
        
        enhanced = classifier.enhance_with_ai_classification(rule_based_result, ai_analysis)
        
        assert enhanced["severity"] == "critical"
        assert enhanced["change_type"] == "compliance_requirement"
        assert enhanced["severity_confidence"] == 90
        assert enhanced["type_confidence"] == 95
        assert enhanced["compliance_impact_score"] == 9
        assert enhanced["ai_severity_override"] == True
        assert enhanced["ai_type_override"] == True
        assert enhanced["classification_method"] == "hybrid"
        assert enhanced["ai_reasoning"] == "AI analysis reasoning"
    
    def test_enhance_with_ai_classification_lower_confidence(self, classifier):
        """Test enhancement when AI has lower confidence."""
        rule_based_result = {
            "severity": "critical",
            "change_type": "compliance_requirement",
            "severity_confidence": 90,
            "type_confidence": 95,
            "compliance_impact_score": 9,
            "is_cosmetic": False,
            "reasoning": "Rule-based classification",
            "classification_method": "rule_based"
        }
        
        ai_analysis = {
            "severity": "important",
            "severity_confidence": 60,
            "change_type": "field_addition",
            "type_confidence": 70,
            "compliance_impact_score": 7,
            "is_cosmetic": False,
            "reasoning": "AI analysis reasoning"
        }
        
        enhanced = classifier.enhance_with_ai_classification(rule_based_result, ai_analysis)
        
        # Should keep rule-based results since AI confidence is lower
        assert enhanced["severity"] == "critical"
        assert enhanced["change_type"] == "compliance_requirement"
        assert enhanced["severity_confidence"] == 90
        assert enhanced["type_confidence"] == 95
        assert enhanced["classification_method"] == "hybrid"
        assert "ai_severity_override" not in enhanced
        assert "ai_type_override" not in enhanced
    
    def test_get_classification_summary_empty(self, classifier):
        """Test classification summary with empty list."""
        summary = classifier.get_classification_summary([])
        assert summary == {}
    
    def test_get_classification_summary_multiple(self, classifier):
        """Test classification summary with multiple classifications."""
        classifications = [
            {
                "severity": "critical",
                "change_type": "compliance_requirement",
                "severity_confidence": 90,
                "type_confidence": 95,
                "compliance_impact_score": 9,
                "is_cosmetic": False,
                "classification_method": "hybrid"
            },
            {
                "severity": "important",
                "change_type": "field_addition",
                "severity_confidence": 70,
                "type_confidence": 80,
                "compliance_impact_score": 7,
                "is_cosmetic": False,
                "classification_method": "rule_based"
            },
            {
                "severity": "cosmetic",
                "change_type": "cosmetic_update",
                "severity_confidence": 60,
                "type_confidence": 70,
                "compliance_impact_score": 1,
                "is_cosmetic": True,
                "classification_method": "rule_based"
            }
        ]
        
        summary = classifier.get_classification_summary(classifications)
        
        assert summary["total_changes"] == 3
        assert summary["severity_distribution"]["critical"] == 1
        assert summary["severity_distribution"]["important"] == 1
        assert summary["severity_distribution"]["cosmetic"] == 1
        assert summary["type_distribution"]["compliance_requirement"] == 1
        assert summary["type_distribution"]["field_addition"] == 1
        assert summary["type_distribution"]["cosmetic_update"] == 1
        assert summary["cosmetic_changes"] == 1
        assert summary["non_cosmetic_changes"] == 2
        assert summary["classification_methods"]["hybrid"] == 1
        assert summary["classification_methods"]["rule_based"] == 2
        assert summary["avg_confidence"] > 0
        assert summary["avg_compliance_impact"] > 0


class TestGlobalClassifier:
    """Test suite for global classifier functions."""
    
    def test_get_change_classifier_singleton(self):
        """Test that get_change_classifier returns singleton instance."""
        classifier1 = get_change_classifier()
        classifier2 = get_change_classifier()
        
        assert classifier1 is classifier2
    
    def test_get_change_classifier_type(self):
        """Test that get_change_classifier returns correct type."""
        classifier = get_change_classifier()
        assert isinstance(classifier, ChangeClassifier)


if __name__ == "__main__":
    pytest.main([__file__]) 