"""
Change Classification System

This module provides comprehensive classification of form changes by severity and type
for certified payroll compliance monitoring. It uses both rule-based and AI-powered
classification to categorize changes accurately.
"""

import re
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeSeverity(Enum):
    """Enumeration for change severity levels."""
    CRITICAL = "critical"
    IMPORTANT = "important"
    INFORMATIONAL = "informational"
    COSMETIC = "cosmetic"


class ChangeType(Enum):
    """Enumeration for change types."""
    # Form Structure Changes
    FORM_STRUCTURE = "form_structure"
    FIELD_ADDITION = "field_addition"
    FIELD_REMOVAL = "field_removal"
    FIELD_MODIFICATION = "field_modification"
    VALIDATION_RULE_CHANGE = "validation_rule_change"
    
    # Content Changes
    CONTENT_UPDATE = "content_update"
    INSTRUCTION_CHANGE = "instruction_change"
    REQUIREMENT_CHANGE = "requirement_change"
    DEADLINE_CHANGE = "deadline_change"
    
    # Technical Changes
    URL_CHANGE = "url_change"
    VERSION_UPDATE = "version_update"
    METADATA_CHANGE = "metadata_change"
    FORMAT_CHANGE = "format_change"
    
    # Compliance Changes
    COMPLIANCE_REQUIREMENT = "compliance_requirement"
    LEGAL_REFERENCE_UPDATE = "legal_reference_update"
    PENALTY_CHANGE = "penalty_change"
    ENFORCEMENT_CHANGE = "enforcement_change"
    
    # System Changes
    SYSTEM_INTEGRATION = "system_integration"
    API_CHANGE = "api_change"
    AUTHENTICATION_CHANGE = "authentication_change"
    
    # Other
    COSMETIC_UPDATE = "cosmetic_update"
    MINOR_CORRECTION = "minor_correction"
    UNKNOWN = "unknown"


class ChangeClassifier:
    """
    Comprehensive change classifier for certified payroll compliance monitoring.
    
    Features:
    - Rule-based classification using keywords and patterns
    - AI-enhanced classification for complex changes
    - Severity assessment based on compliance impact
    - Change type categorization for workflow management
    - Confidence scoring for classification accuracy
    """
    
    def __init__(self):
        """Initialize the change classifier with classification rules."""
        self.severity_keywords = {
            ChangeSeverity.CRITICAL: [
                "critical", "urgent", "immediate", "required", "mandatory",
                "deadline", "penalty", "violation", "non-compliance", "legal",
                "regulatory", "enforcement", "audit", "investigation", "fine",
                "sanction", "suspension", "termination", "criminal", "felony"
            ],
            ChangeSeverity.IMPORTANT: [
                "important", "significant", "major", "substantial", "key",
                "essential", "required", "necessary", "update", "modification",
                "change", "revision", "amendment", "correction", "improvement",
                "enhancement", "new requirement", "additional", "supplemental"
            ],
            ChangeSeverity.INFORMATIONAL: [
                "informational", "notice", "announcement", "update", "news",
                "clarification", "guidance", "example", "sample", "template",
                "reference", "documentation", "help", "support", "faq"
            ],
            ChangeSeverity.COSMETIC: [
                "cosmetic", "formatting", "styling", "layout", "design",
                "appearance", "visual", "presentation", "typography", "spacing",
                "alignment", "color", "font", "size", "minor", "trivial"
            ]
        }
        
        self.type_patterns = {
            ChangeType.FORM_STRUCTURE: [
                r"form\s+structure", r"layout\s+change", r"reorganization",
                r"restructure", r"reformat", r"new\s+section", r"section\s+change"
            ],
            ChangeType.FIELD_ADDITION: [
                r"new\s+field", r"add\s+field", r"additional\s+field",
                r"required\s+field", r"mandatory\s+field", r"new\s+input"
            ],
            ChangeType.FIELD_REMOVAL: [
                r"remove\s+field", r"delete\s+field", r"eliminate\s+field",
                r"no\s+longer\s+required", r"discontinued", r"obsolete"
            ],
            ChangeType.FIELD_MODIFICATION: [
                r"modify\s+field", r"change\s+field", r"update\s+field",
                r"field\s+change", r"field\s+update", r"field\s+modification"
            ],
            ChangeType.VALIDATION_RULE_CHANGE: [
                r"validation", r"rule\s+change", r"requirement\s+change",
                r"criteria\s+change", r"standard\s+change", r"threshold"
            ],
            ChangeType.CONTENT_UPDATE: [
                r"content\s+update", r"text\s+change", r"information\s+update",
                r"description\s+change", r"wording\s+change", r"language\s+update"
            ],
            ChangeType.INSTRUCTION_CHANGE: [
                r"instruction", r"guidance", r"procedure", r"process",
                r"step\s+by\s+step", r"how\s+to", r"manual", r"guide"
            ],
            ChangeType.REQUIREMENT_CHANGE: [
                r"requirement", r"mandatory", r"obligation", r"duty",
                r"responsibility", r"compliance", r"standard", r"criteria"
            ],
            ChangeType.DEADLINE_CHANGE: [
                r"deadline", r"due\s+date", r"timeline", r"schedule",
                r"timeframe", r"period", r"extension", r"postponement"
            ],
            ChangeType.URL_CHANGE: [
                r"url\s+change", r"link\s+change", r"website\s+change",
                r"address\s+change", r"location\s+change", r"redirect"
            ],
            ChangeType.VERSION_UPDATE: [
                r"version", r"update", r"new\s+version", r"revision",
                r"edition", r"release", r"upgrade", r"latest"
            ],
            ChangeType.COMPLIANCE_REQUIREMENT: [
                r"compliance", r"regulation", r"legal", r"statutory",
                r"regulatory", r"law", r"act", r"statute", r"ordinance"
            ],
            ChangeType.LEGAL_REFERENCE_UPDATE: [
                r"legal\s+reference", r"statute", r"regulation", r"law",
                r"code", r"section", r"clause", r"provision", r"article"
            ],
            ChangeType.PENALTY_CHANGE: [
                r"penalty", r"fine", r"sanction", r"violation", r"punishment",
                r"consequence", r"enforcement", r"disciplinary", r"corrective"
            ],
            ChangeType.ENFORCEMENT_CHANGE: [
                r"enforcement", r"audit", r"inspection", r"review",
                r"monitoring", r"oversight", r"supervision", r"compliance\s+check"
            ]
        }
        
        # Compliance impact scoring
        self.compliance_impact_scores = {
            ChangeType.FORM_STRUCTURE: 8,
            ChangeType.FIELD_ADDITION: 7,
            ChangeType.FIELD_REMOVAL: 9,
            ChangeType.FIELD_MODIFICATION: 6,
            ChangeType.VALIDATION_RULE_CHANGE: 8,
            ChangeType.CONTENT_UPDATE: 4,
            ChangeType.INSTRUCTION_CHANGE: 5,
            ChangeType.REQUIREMENT_CHANGE: 9,
            ChangeType.DEADLINE_CHANGE: 7,
            ChangeType.URL_CHANGE: 3,
            ChangeType.VERSION_UPDATE: 5,
            ChangeType.COMPLIANCE_REQUIREMENT: 10,
            ChangeType.LEGAL_REFERENCE_UPDATE: 8,
            ChangeType.PENALTY_CHANGE: 9,
            ChangeType.ENFORCEMENT_CHANGE: 8,
            ChangeType.COSMETIC_UPDATE: 1,
            ChangeType.MINOR_CORRECTION: 2,
            ChangeType.UNKNOWN: 5
        }
    
    def classify_change(self, 
                       old_content: str, 
                       new_content: str, 
                       change_description: str,
                       form_name: str = "",
                       agency_name: str = "") -> Dict[str, Any]:
        """
        Classify a change by severity and type.
        
        Args:
            old_content: Previous content
            new_content: New content
            change_description: Human-readable description of the change
            form_name: Name of the form being changed
            agency_name: Name of the agency
            
        Returns:
            Dictionary containing classification results
        """
        try:
            # Combine all text for analysis
            analysis_text = f"{change_description} {form_name} {agency_name}".lower()
            
            # Perform rule-based classification
            severity = self._classify_severity(analysis_text)
            change_type = self._classify_type(analysis_text)
            
            # Calculate confidence scores
            severity_confidence = self._calculate_severity_confidence(analysis_text, severity)
            type_confidence = self._calculate_type_confidence(analysis_text, change_type)
            
            # Calculate compliance impact score
            compliance_impact = self._calculate_compliance_impact(change_type, severity)
            
            # Determine if change is cosmetic
            is_cosmetic = self._is_cosmetic_change(old_content, new_content, analysis_text)
            
            # Generate reasoning
            reasoning = self._generate_classification_reasoning(
                severity, change_type, analysis_text, compliance_impact
            )
            
            return {
                "severity": severity.value,
                "change_type": change_type.value,
                "severity_confidence": severity_confidence,
                "type_confidence": type_confidence,
                "compliance_impact_score": compliance_impact,
                "is_cosmetic": is_cosmetic,
                "reasoning": reasoning,
                "classification_timestamp": datetime.now(timezone.utc).isoformat(),
                "classification_method": "rule_based"
            }
            
        except Exception as e:
            logger.error(f"Error classifying change: {e}")
            return self._get_default_classification()
    
    def _classify_severity(self, text: str) -> ChangeSeverity:
        """Classify change severity based on keywords and patterns."""
        text_lower = text.lower()
        
        # Count keyword matches for each severity level
        severity_scores = {}
        for severity, keywords in self.severity_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            severity_scores[severity] = score
        
        # Determine severity based on highest score
        if severity_scores[ChangeSeverity.CRITICAL] > 0:
            return ChangeSeverity.CRITICAL
        elif severity_scores[ChangeSeverity.IMPORTANT] > 0:
            return ChangeSeverity.IMPORTANT
        elif severity_scores[ChangeSeverity.COSMETIC] > 0:
            return ChangeSeverity.COSMETIC
        else:
            return ChangeSeverity.INFORMATIONAL
    
    def _classify_type(self, text: str) -> ChangeType:
        """Classify change type based on patterns and keywords."""
        text_lower = text.lower()
        
        # Check each type pattern
        type_scores = {}
        for change_type, patterns in self.type_patterns.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    score += 1
            type_scores[change_type] = score
        
        # Return type with highest score, or UNKNOWN if no matches
        if type_scores:
            best_type = max(type_scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:
                return best_type[0]
        
        return ChangeType.UNKNOWN
    
    def _calculate_severity_confidence(self, text: str, severity: ChangeSeverity) -> int:
        """Calculate confidence score for severity classification."""
        text_lower = text.lower()
        keywords = self.severity_keywords[severity]
        
        # Count keyword matches
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        
        # Calculate confidence based on matches and text length
        if matches == 0:
            return 30  # Low confidence for default classification
        elif matches == 1:
            return 60
        elif matches == 2:
            return 80
        else:
            return 95
    
    def _calculate_type_confidence(self, text: str, change_type: ChangeType) -> int:
        """Calculate confidence score for type classification."""
        text_lower = text.lower()
        patterns = self.type_patterns.get(change_type, [])
        
        if not patterns:
            return 30  # Low confidence for unknown type
        
        # Count pattern matches
        matches = sum(1 for pattern in patterns if re.search(pattern, text_lower))
        
        # Calculate confidence based on matches
        if matches == 0:
            return 30
        elif matches == 1:
            return 70
        elif matches == 2:
            return 85
        else:
            return 95
    
    def _calculate_compliance_impact(self, change_type: ChangeType, severity: ChangeSeverity) -> int:
        """Calculate compliance impact score (0-100)."""
        base_score = self.compliance_impact_scores.get(change_type, 5)
        
        # Adjust based on severity
        severity_multiplier = {
            ChangeSeverity.CRITICAL: 1.2,
            ChangeSeverity.IMPORTANT: 1.0,
            ChangeSeverity.INFORMATIONAL: 0.6,
            ChangeSeverity.COSMETIC: 0.2
        }
        
        adjusted_score = int(base_score * severity_multiplier[severity])
        return min(100, max(0, adjusted_score))
    
    def _is_cosmetic_change(self, old_content: str, new_content: str, analysis_text: str) -> bool:
        """Determine if change is cosmetic."""
        # Check if explicitly marked as cosmetic
        if "cosmetic" in analysis_text.lower():
            return True
        
        # Check for cosmetic keywords
        cosmetic_keywords = ["formatting", "styling", "layout", "design", "visual", "appearance"]
        if any(keyword in analysis_text.lower() for keyword in cosmetic_keywords):
            return True
        
        # Simple content similarity check (basic implementation)
        if old_content and new_content:
            # Remove whitespace and compare
            old_clean = re.sub(r'\s+', '', old_content.lower())
            new_clean = re.sub(r'\s+', '', new_content.lower())
            
            # If content is very similar, likely cosmetic
            if len(old_clean) > 0 and len(new_clean) > 0:
                similarity = self._calculate_similarity(old_clean, new_clean)
                if similarity > 0.95:  # 95% similar
                    return True
        
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity (0-1)."""
        if not text1 or not text2:
            return 0.0
        
        # Simple character-based similarity
        common_chars = sum(1 for c in text1 if c in text2)
        total_chars = max(len(text1), len(text2))
        
        return common_chars / total_chars if total_chars > 0 else 0.0
    
    def _generate_classification_reasoning(self, 
                                         severity: ChangeSeverity, 
                                         change_type: ChangeType, 
                                         analysis_text: str,
                                         compliance_impact: int) -> str:
        """Generate human-readable reasoning for classification."""
        reasoning_parts = []
        
        # Severity reasoning
        severity_keywords = self.severity_keywords[severity]
        found_keywords = [kw for kw in severity_keywords if kw in analysis_text.lower()]
        
        if found_keywords:
            reasoning_parts.append(f"Severity classified as '{severity.value}' based on keywords: {', '.join(found_keywords[:3])}")
        else:
            reasoning_parts.append(f"Severity classified as '{severity.value}' (default classification)")
        
        # Type reasoning
        if change_type != ChangeType.UNKNOWN:
            reasoning_parts.append(f"Change type identified as '{change_type.value}' based on pattern matching")
        else:
            reasoning_parts.append("Change type classified as 'unknown' (no specific patterns detected)")
        
        # Compliance impact reasoning
        if compliance_impact >= 8:
            reasoning_parts.append(f"High compliance impact score ({compliance_impact}/100) - requires immediate attention")
        elif compliance_impact >= 5:
            reasoning_parts.append(f"Moderate compliance impact score ({compliance_impact}/100) - should be reviewed")
        else:
            reasoning_parts.append(f"Low compliance impact score ({compliance_impact}/100) - minimal compliance risk")
        
        return ". ".join(reasoning_parts)
    
    def _get_default_classification(self) -> Dict[str, Any]:
        """Return default classification when analysis fails."""
        return {
            "severity": ChangeSeverity.INFORMATIONAL.value,
            "change_type": ChangeType.UNKNOWN.value,
            "severity_confidence": 30,
            "type_confidence": 30,
            "compliance_impact_score": 5,
            "is_cosmetic": False,
            "reasoning": "Default classification due to analysis error",
            "classification_timestamp": datetime.now(timezone.utc).isoformat(),
            "classification_method": "default"
        }
    
    def enhance_with_ai_classification(self, 
                                     rule_based_result: Dict[str, Any],
                                     ai_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enhance rule-based classification with AI analysis results.
        
        Args:
            rule_based_result: Results from rule-based classification
            ai_analysis: Optional AI analysis results
            
        Returns:
            Enhanced classification results
        """
        if not ai_analysis:
            return rule_based_result
        
        enhanced_result = rule_based_result.copy()
        
        # Use AI severity if available and confidence is higher
        ai_severity = ai_analysis.get("severity")
        ai_severity_confidence = ai_analysis.get("severity_confidence", 0)
        
        if (ai_severity and 
            ai_severity_confidence > rule_based_result.get("severity_confidence", 0)):
            enhanced_result["severity"] = ai_severity
            enhanced_result["severity_confidence"] = ai_severity_confidence
            enhanced_result["ai_severity_override"] = True
        
        # Use AI change type if available and confidence is higher
        ai_change_type = ai_analysis.get("change_type")
        ai_type_confidence = ai_analysis.get("type_confidence", 0)
        
        if (ai_change_type and 
            ai_type_confidence > rule_based_result.get("type_confidence", 0)):
            enhanced_result["change_type"] = ai_change_type
            enhanced_result["type_confidence"] = ai_type_confidence
            enhanced_result["ai_type_override"] = True
        
        # Update compliance impact if AI provides it
        ai_compliance_impact = ai_analysis.get("compliance_impact_score")
        if ai_compliance_impact is not None:
            enhanced_result["compliance_impact_score"] = ai_compliance_impact
        
        # Update cosmetic determination
        ai_is_cosmetic = ai_analysis.get("is_cosmetic")
        if ai_is_cosmetic is not None:
            enhanced_result["is_cosmetic"] = ai_is_cosmetic
        
        # Add AI reasoning if available
        ai_reasoning = ai_analysis.get("reasoning")
        if ai_reasoning:
            enhanced_result["ai_reasoning"] = ai_reasoning
        
        enhanced_result["classification_method"] = "hybrid"
        enhanced_result["ai_enhancement_timestamp"] = datetime.now(timezone.utc).isoformat()
        
        return enhanced_result
    
    def get_classification_summary(self, classifications: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate summary statistics for multiple classifications.
        
        Args:
            classifications: List of classification results
            
        Returns:
            Summary statistics
        """
        if not classifications:
            return {}
        
        # Count severities
        severity_counts = {}
        type_counts = {}
        confidence_scores = []
        impact_scores = []
        cosmetic_count = 0
        
        for classification in classifications:
            # Severity counts
            severity = classification.get("severity", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # Type counts
            change_type = classification.get("change_type", "unknown")
            type_counts[change_type] = type_counts.get(change_type, 0) + 1
            
            # Confidence scores
            severity_conf = classification.get("severity_confidence", 0)
            type_conf = classification.get("type_confidence", 0)
            confidence_scores.extend([severity_conf, type_conf])
            
            # Impact scores
            impact_score = classification.get("compliance_impact_score", 0)
            impact_scores.append(impact_score)
            
            # Cosmetic count
            if classification.get("is_cosmetic", False):
                cosmetic_count += 1
        
        return {
            "total_changes": len(classifications),
            "severity_distribution": severity_counts,
            "type_distribution": type_counts,
            "avg_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "avg_compliance_impact": sum(impact_scores) / len(impact_scores) if impact_scores else 0,
            "cosmetic_changes": cosmetic_count,
            "non_cosmetic_changes": len(classifications) - cosmetic_count,
            "classification_methods": {
                "rule_based": sum(1 for c in classifications if c.get("classification_method") == "rule_based"),
                "hybrid": sum(1 for c in classifications if c.get("classification_method") == "hybrid"),
                "default": sum(1 for c in classifications if c.get("classification_method") == "default")
            }
        }


# Global classifier instance
_change_classifier = None

def get_change_classifier() -> ChangeClassifier:
    """Get the global change classifier instance."""
    global _change_classifier
    if _change_classifier is None:
        _change_classifier = ChangeClassifier()
    return _change_classifier 