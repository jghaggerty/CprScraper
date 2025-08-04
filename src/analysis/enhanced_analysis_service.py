"""
EnhancedAnalysisService: Advanced AI-powered change detection with false positive reduction.

This service extends the base AnalysisService with sophisticated semantic analysis,
false positive detection, and intelligent filtering for regulatory compliance monitoring.
"""

import uuid
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import asdict
import re
from collections import defaultdict

from .analysis_service import AnalysisService, AnalysisTimeoutError, AnalysisProcessingError
from .models import (
    AnalysisRequest, AnalysisResponse, AnalysisError,
    BatchAnalysisRequest, BatchAnalysisResponse,
    ChangeClassification, SemanticAnalysis, LLMAnalysis
)
from .change_analyzer import ChangeAnalyzer
from .llm_classifier import LLMClassifier

logger = logging.getLogger(__name__)


class EnhancedAnalysisService(AnalysisService):
    """
    Enhanced analysis service with advanced false positive reduction and semantic detection.
    
    Features:
    - Multi-stage false positive detection
    - Semantic change pattern recognition
    - Historical analysis correlation
    - Adaptive confidence thresholds
    - Content validation and filtering
    """
    
    def __init__(self,
                 semantic_model: str = "all-MiniLM-L6-v2",
                 llm_model: str = "gpt-3.5-turbo",
                 default_confidence_threshold: int = 70,
                 max_processing_time_seconds: int = 180,
                 enable_caching: bool = True,
                 false_positive_threshold: float = 0.15,
                 semantic_similarity_threshold: float = 0.85):
        """
        Initialize the EnhancedAnalysisService.
        
        Args:
            semantic_model: Sentence transformer model for semantic analysis
            llm_model: LLM model for classification
            default_confidence_threshold: Default threshold for analysis confidence
            max_processing_time_seconds: Maximum time allowed for analysis
            enable_caching: Whether to enable result caching
            false_positive_threshold: Threshold for false positive detection
            semantic_similarity_threshold: Threshold for semantic similarity
        """
        super().__init__(
            semantic_model=semantic_model,
            llm_model=llm_model,
            default_confidence_threshold=default_confidence_threshold,
            max_processing_time_seconds=max_processing_time_seconds,
            enable_caching=enable_caching
        )
        
        self.false_positive_threshold = false_positive_threshold
        self.semantic_similarity_threshold = semantic_similarity_threshold
        
        # False positive detection patterns
        self.false_positive_patterns = {
            "whitespace_only": [
                r'^\s*$',  # Empty lines
                r'\s+',    # Multiple whitespace
                r'[\t\r\n]+',  # Line breaks and tabs
            ],
            "formatting_only": [
                r'<[^>]+>',  # HTML tags
                r'<!--.*?-->',  # HTML comments
                r'/\*.*?\*/',   # CSS/JS comments
                r'//.*$',       # Line comments
                r'^\s*[#*\-+]\s*',  # Markdown formatting
            ],
            "dynamic_content": [
                r'\b\d{4}-\d{2}-\d{2}\b',  # Dates
                r'\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b',  # Times
                r'\b\d+\.\d+\.\d+\b',  # Version numbers
                r'page\s+\d+',  # Page numbers
                r'last\s+updated',  # Last updated timestamps
            ],
            "navigation_elements": [
                r'menu|navigation|sidebar|footer|header',
                r'breadcrumb|pagination|next|previous',
                r'home|about|contact|help',
            ]
        }
        
        # Semantic change patterns for compliance documents
        self.compliance_patterns = {
            "critical_changes": [
                r'\b(must|shall|required|mandatory|obligation)\b',
                r'\b(deadline|due date|time limit|expiration)\b',
                r'\b(penalty|fine|violation|non-compliance|enforcement)\b',
                r'\b(minimum|maximum|threshold|limit|cap)\b',
                r'\b(legal|regulatory|statutory|compliance)\b'
            ],
            "structural_changes": [
                r'\b(field|box|line|section|page|form)\b',
                r'\b(instruction|guidance|help|example)\b',
                r'\b(calculation|formula|algorithm|method)\b',
                r'\b(validation|verification|check|audit)\b'
            ],
            "cosmetic_changes": [
                r'\b(font|color|size|style|format)\b',
                r'\b(layout|spacing|margin|padding)\b',
                r'\b(logo|image|icon|graphic)\b',
                r'\b(typo|spelling|grammar|punctuation)\b'
            ]
        }
        
        # Historical analysis tracking
        self.analysis_history = defaultdict(list)
        self.false_positive_history = defaultdict(int)
        
    def _detect_false_positives(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """
        Detect potential false positive changes.
        
        Args:
            old_content: Original content
            new_content: Updated content
            
        Returns:
            Dictionary with false positive detection results
        """
        false_positive_score = 0.0
        detected_patterns = []
        reasons = []
        
        # Normalize content for comparison
        old_normalized = self._normalize_content(old_content)
        new_normalized = self._normalize_content(new_content)
        
        # Check if normalized content is identical
        if old_normalized == new_normalized:
            return {
                "is_false_positive": True,
                "confidence": 1.0,
                "patterns": ["content_normalization"],
                "reasons": ["Content identical after normalization"]
            }
        
        # Check for whitespace-only changes
        if self._is_whitespace_only_change(old_content, new_content):
            false_positive_score += 0.4
            detected_patterns.append("whitespace_only")
            reasons.append("Only whitespace changes detected")
        
        # Check for formatting-only changes
        if self._is_formatting_only_change(old_content, new_content):
            false_positive_score += 0.3
            detected_patterns.append("formatting_only")
            reasons.append("Only formatting changes detected")
        
        # Check for dynamic content changes
        if self._is_dynamic_content_change(old_content, new_content):
            false_positive_score += 0.2
            detected_patterns.append("dynamic_content")
            reasons.append("Dynamic content changes (dates, times, versions)")
        
        # Check for navigation element changes
        if self._is_navigation_change(old_content, new_content):
            false_positive_score += 0.3
            detected_patterns.append("navigation_elements")
            reasons.append("Navigation/menu changes detected")
        
        # Check for very small content changes
        content_change_ratio = self._calculate_content_change_ratio(old_content, new_content)
        if content_change_ratio < 0.05:  # Less than 5% change
            false_positive_score += 0.2
            detected_patterns.append("minimal_change")
            reasons.append(f"Minimal content change ({content_change_ratio:.2%})")
        
        return {
            "is_false_positive": false_positive_score >= self.false_positive_threshold,
            "confidence": min(false_positive_score, 1.0),
            "patterns": detected_patterns,
            "reasons": reasons,
            "change_ratio": content_change_ratio
        }
    
    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison by removing common false positive elements."""
        # Remove HTML tags and comments
        content = re.sub(r'<[^>]+>', '', content)
        content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
        
        # Remove CSS/JS comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common dynamic content
        content = re.sub(r'\b\d{4}-\d{2}-\d{2}\b', '[DATE]', content)
        content = re.sub(r'\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b', '[TIME]', content)
        content = re.sub(r'\b\d+\.\d+\.\d+\b', '[VERSION]', content)
        
        return content.strip().lower()
    
    def _is_whitespace_only_change(self, old_content: str, new_content: str) -> bool:
        """Check if changes are only whitespace-related."""
        old_clean = re.sub(r'\s+', '', old_content)
        new_clean = re.sub(r'\s+', '', new_content)
        return old_clean == new_clean
    
    def _is_formatting_only_change(self, old_content: str, new_content: str) -> bool:
        """Check if changes are only formatting-related."""
        # Remove formatting patterns from both contents
        old_no_format = old_content
        new_no_format = new_content
        
        for pattern in self.false_positive_patterns["formatting_only"]:
            old_no_format = re.sub(pattern, '', old_no_format, flags=re.IGNORECASE)
            new_no_format = re.sub(pattern, '', new_no_format, flags=re.IGNORECASE)
        
        # Normalize whitespace
        old_no_format = re.sub(r'\s+', ' ', old_no_format).strip()
        new_no_format = re.sub(r'\s+', ' ', new_no_format).strip()
        
        return old_no_format == new_no_format
    
    def _is_dynamic_content_change(self, old_content: str, new_content: str) -> bool:
        """Check if changes are only dynamic content (dates, times, versions)."""
        old_dynamic = set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b|\b\d+\.\d+\.\d+\b', old_content))
        new_dynamic = set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b|\b\d+\.\d+\.\d+\b', new_content))
        
        # If only dynamic content changed, it's likely a false positive
        if old_dynamic != new_dynamic:
            # Check if the rest of the content is similar
            old_clean = re.sub(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b|\b\d+\.\d+\.\d+\b', '[DYNAMIC]', old_content)
            new_clean = re.sub(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM)?\b|\b\d+\.\d+\.\d+\b', '[DYNAMIC]', new_content)
            
            old_clean = re.sub(r'\s+', ' ', old_clean).strip()
            new_clean = re.sub(r'\s+', ' ', new_clean).strip()
            
            return old_clean == new_clean
        
        return False
    
    def _is_navigation_change(self, old_content: str, new_content: str) -> bool:
        """Check if changes are only in navigation elements."""
        old_nav = set(re.findall(r'\b(menu|navigation|sidebar|footer|header|breadcrumb|pagination|next|previous|home|about|contact|help)\b', old_content, re.IGNORECASE))
        new_nav = set(re.findall(r'\b(menu|navigation|sidebar|footer|header|breadcrumb|pagination|next|previous|home|about|contact|help)\b', new_content, re.IGNORECASE))
        
        if old_nav != new_nav:
            # Check if the rest of the content is similar
            old_clean = re.sub(r'\b(menu|navigation|sidebar|footer|header|breadcrumb|pagination|next|previous|home|about|contact|help)\b', '[NAV]', old_content, flags=re.IGNORECASE)
            new_clean = re.sub(r'\b(menu|navigation|sidebar|footer|header|breadcrumb|pagination|next|previous|home|about|contact|help)\b', '[NAV]', new_content, flags=re.IGNORECASE)
            
            old_clean = re.sub(r'\s+', ' ', old_clean).strip()
            new_clean = re.sub(r'\s+', ' ', new_clean).strip()
            
            return old_clean == new_clean
        
        return False
    
    def _calculate_content_change_ratio(self, old_content: str, new_content: str) -> float:
        """Calculate the ratio of content changes."""
        import difflib
        
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        diff_lines = list(differ)
        
        # Count actual changes (excluding diff headers)
        changes = [line for line in diff_lines if line.startswith('+') or line.startswith('-')]
        total_lines = max(len(old_lines), len(new_lines))
        
        if total_lines == 0:
            return 0.0
        
        return len(changes) / total_lines
    
    def _detect_semantic_changes(self, old_content: str, new_content: str) -> Dict[str, Any]:
        """
        Detect semantic changes using pattern matching and analysis.
        
        Args:
            old_content: Original content
            new_content: Updated content
            
        Returns:
            Dictionary with semantic change detection results
        """
        semantic_changes = {
            "critical_changes": [],
            "structural_changes": [],
            "cosmetic_changes": [],
            "overall_impact": "low"
        }
        
        # Analyze changes by pattern type
        for change_type, patterns in self.compliance_patterns.items():
            changes = self._find_pattern_changes(old_content, new_content, patterns)
            semantic_changes[change_type] = changes
        
        # Determine overall impact
        if semantic_changes["critical_changes"]:
            semantic_changes["overall_impact"] = "critical"
        elif semantic_changes["structural_changes"]:
            semantic_changes["overall_impact"] = "high"
        elif semantic_changes["cosmetic_changes"]:
            semantic_changes["overall_impact"] = "low"
        else:
            semantic_changes["overall_impact"] = "medium"
        
        return semantic_changes
    
    def _find_pattern_changes(self, old_content: str, new_content: str, patterns: List[str]) -> List[str]:
        """Find changes related to specific patterns."""
        changes = []
        
        for pattern in patterns:
            old_matches = set(re.findall(pattern, old_content, re.IGNORECASE))
            new_matches = set(re.findall(pattern, new_content, re.IGNORECASE))
            
            added = new_matches - old_matches
            removed = old_matches - new_matches
            
            if added:
                changes.append(f"Added: {', '.join(list(added)[:3])}")
            if removed:
                changes.append(f"Removed: {', '.join(list(removed)[:3])}")
        
        return changes
    
    def _validate_content_relevance(self, content: str, form_name: str = "", agency_name: str = "") -> Dict[str, Any]:
        """
        Validate that content is relevant to certified payroll compliance.
        
        Args:
            content: Content to validate
            form_name: Name of the form
            agency_name: Name of the agency
            
        Returns:
            Dictionary with validation results
        """
        # Comprehensive certified payroll compliance keywords
        compliance_keywords = {
            "payroll_core": [
                "payroll", "wage", "salary", "hour", "overtime", "compensation", "earnings",
                "gross", "net", "deduction", "withholding", "fringe", "benefit"
            ],
            "certified_payroll": [
                "certified payroll", "certified payroll report", "wh-347", "a1-131", "a-1-131",
                "prevailing wage", "prevailing wage rate", "davis-bacon", "davis bacon",
                "public works", "government contract", "federal contract"
            ],
            "compliance_legal": [
                "compliance", "regulation", "requirement", "mandatory", "obligation", "statute",
                "law", "act", "rule", "standard", "policy", "directive", "order"
            ],
            "reporting_submission": [
                "report", "submit", "file", "certify", "statement", "affidavit", "declaration",
                "attest", "verify", "swear", "under penalty", "perjury"
            ],
            "forms_documents": [
                "form", "document", "template", "format", "structure", "field", "section",
                "attachment", "exhibit", "schedule", "worksheet", "summary"
            ],
            "government_entities": [
                "government", "agency", "department", "federal", "state", "local", "municipal",
                "county", "city", "township", "district", "authority", "commission"
            ],
            "construction_labor": [
                "construction", "contractor", "subcontractor", "laborer", "worker", "employee",
                "crew", "team", "project", "site", "job", "work", "trade", "craft"
            ],
            "time_tracking": [
                "time", "hours", "days", "week", "period", "shift", "schedule", "clock",
                "timecard", "timesheet", "attendance", "workday", "workweek"
            ],
            "wage_rates": [
                "rate", "hourly", "daily", "weekly", "monthly", "annual", "base", "premium",
                "bonus", "incentive", "differential", "scale", "schedule", "classification"
            ],
            "penalties_enforcement": [
                "penalty", "fine", "sanction", "violation", "enforcement", "investigation",
                "audit", "review", "inspection", "monitoring", "oversight"
            ],
            "deadlines_timing": [
                "deadline", "due date", "filing", "submission", "effective", "implementation",
                "compliance date", "grace period", "extension", "waiver"
            ],
            "contract_terms": [
                "contract", "agreement", "bid", "proposal", "award", "scope", "specification",
                "terms", "conditions", "clause", "provision", "amendment"
            ]
        }
        
        # Specific form patterns and identifiers
        form_patterns = {
            "wh_347": [
                r"wh-347", r"wh347", r"statement of compliance", r"federal construction",
                r"federally assisted", r"davis-bacon", r"davis bacon"
            ],
            "ca_a1_131": [
                r"a1-131", r"a-1-131", r"california certified", r"dir", r"department of industrial relations",
                r"public works", r"prevailing wage"
            ],
            "state_forms": [
                r"certified payroll", r"prevailing wage", r"public works", r"construction",
                r"wage report", r"labor compliance"
            ]
        }
        
        content_lower = content.lower()
        relevance_scores = {}
        total_score = 0
        
        # Calculate keyword-based relevance scores
        for category, keywords in compliance_keywords.items():
            score = sum(1 for keyword in keywords if keyword in content_lower)
            relevance_scores[category] = score
            total_score += score
        
        # Check for specific form patterns
        form_matches = {}
        for form_type, patterns in form_patterns.items():
            matches = []
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    matches.append(pattern)
            form_matches[form_type] = matches
        
        # Calculate overall relevance
        max_possible_score = sum(len(keywords) for keywords in compliance_keywords.values())
        relevance_percentage = (total_score / max_possible_score) * 100 if max_possible_score > 0 else 0
        
        # Enhanced relevance criteria
        is_relevant = (
            relevance_percentage >= 15 or  # At least 15% keyword relevance
            any(len(matches) > 0 for matches in form_matches.values()) or  # Specific form patterns found
            any(keyword in content_lower for keyword in ["certified payroll", "wh-347", "a1-131", "prevailing wage"])  # Core terms
        )
        
        # Calculate confidence based on multiple factors
        confidence_factors = {
            "keyword_density": min(relevance_percentage / 50, 1.0),  # Normalize to 0-1
            "form_patterns": min(sum(len(matches) for matches in form_matches.values()) / 5, 1.0),
            "core_terms": 1.0 if any(keyword in content_lower for keyword in ["certified payroll", "wh-347", "a1-131"]) else 0.0,
            "government_context": 1.0 if any(keyword in content_lower for keyword in ["government", "federal", "state", "agency"]) else 0.0
        }
        
        overall_confidence = sum(confidence_factors.values()) / len(confidence_factors) * 100
        
        return {
            "is_relevant": is_relevant,
            "relevance_percentage": relevance_percentage,
            "category_scores": relevance_scores,
            "form_matches": form_matches,
            "total_score": total_score,
            "confidence_factors": confidence_factors,
            "overall_confidence": overall_confidence,
            "validation_details": {
                "keyword_density": relevance_percentage,
                "pattern_matches": sum(len(matches) for matches in form_matches.values()),
                "core_compliance_terms": sum(1 for term in ["certified payroll", "wh-347", "a1-131", "prevailing wage"] if term in content_lower)
            }
        }
    
    def _validate_compliance_specific_content(self, content: str, form_name: str = "", agency_name: str = "") -> Dict[str, Any]:
        """
        Validate content for specific compliance requirements and patterns.
        
        Args:
            content: Content to validate
            form_name: Name of the form
            agency_name: Name of the agency
            
        Returns:
            Dictionary with compliance-specific validation results
        """
        content_lower = content.lower()
        
        # Compliance-specific validation patterns
        compliance_checks = {
            "wage_rate_requirements": {
                "patterns": [
                    r"prevailing wage rate", r"minimum wage", r"base rate", r"hourly rate",
                    r"wage determination", r"wage scale", r"rate schedule"
                ],
                "required_fields": ["rate", "wage", "hourly", "prevailing"],
                "severity": "high"
            },
            "certification_requirements": {
                "patterns": [
                    r"certify", r"certification", r"under penalty", r"perjury", r"swear",
                    r"affirm", r"attest", r"declare", r"verify"
                ],
                "required_fields": ["certify", "penalty", "perjury"],
                "severity": "critical"
            },
            "reporting_deadlines": {
                "patterns": [
                    r"due date", r"deadline", r"filing date", r"submission date",
                    r"within \d+ days", r"by \d{1,2}/\d{1,2}/\d{4}", r"monthly", r"weekly"
                ],
                "required_fields": ["due", "deadline", "filing", "submission"],
                "severity": "high"
            },
            "employee_identification": {
                "patterns": [
                    r"employee name", r"social security", r"ssn", r"employee id",
                    r"worker identification", r"laborer name", r"craft classification"
                ],
                "required_fields": ["employee", "name", "identification"],
                "severity": "medium"
            },
            "time_tracking_requirements": {
                "patterns": [
                    r"hours worked", r"time worked", r"daily hours", r"weekly hours",
                    r"overtime hours", r"straight time", r"time and a half"
                ],
                "required_fields": ["hours", "time", "worked"],
                "severity": "medium"
            },
            "fringe_benefits": {
                "patterns": [
                    r"fringe benefits", r"health insurance", r"pension", r"retirement",
                    r"vacation pay", r"holiday pay", r"bonus", r"incentive"
                ],
                "required_fields": ["fringe", "benefit", "insurance"],
                "severity": "medium"
            },
            "penalty_provisions": {
                "patterns": [
                    r"penalty", r"fine", r"sanction", r"violation", r"enforcement",
                    r"investigation", r"audit", r"review"
                ],
                "required_fields": ["penalty", "fine", "violation"],
                "severity": "high"
            }
        }
        
        validation_results = {}
        overall_compliance_score = 0
        total_checks = len(compliance_checks)
        
        for check_name, check_config in compliance_checks.items():
            # Check for pattern matches
            pattern_matches = []
            for pattern in check_config["patterns"]:
                if re.search(pattern, content_lower):
                    pattern_matches.append(pattern)
            
            # Check for required fields
            required_field_matches = []
            for field in check_config["required_fields"]:
                if field in content_lower:
                    required_field_matches.append(field)
            
            # Calculate check score
            pattern_score = len(pattern_matches) / len(check_config["patterns"]) * 100
            field_score = len(required_field_matches) / len(check_config["required_fields"]) * 100
            check_score = (pattern_score + field_score) / 2
            
            validation_results[check_name] = {
                "patterns_found": pattern_matches,
                "required_fields_found": required_field_matches,
                "pattern_score": pattern_score,
                "field_score": field_score,
                "overall_score": check_score,
                "severity": check_config["severity"],
                "is_compliant": check_score >= 50  # At least 50% compliance
            }
            
            if validation_results[check_name]["is_compliant"]:
                overall_compliance_score += 1
        
        overall_compliance_percentage = (overall_compliance_score / total_checks) * 100
        
        return {
            "overall_compliance_score": overall_compliance_percentage,
            "compliant_checks": overall_compliance_score,
            "total_checks": total_checks,
            "validation_results": validation_results,
            "compliance_summary": {
                "critical_checks": sum(1 for result in validation_results.values() if result["severity"] == "critical" and result["is_compliant"]),
                "high_checks": sum(1 for result in validation_results.values() if result["severity"] == "high" and result["is_compliant"]),
                "medium_checks": sum(1 for result in validation_results.values() if result["severity"] == "medium" and result["is_compliant"])
            }
        }
    
    def _validate_form_structure_integrity(self, content: str, form_name: str = "") -> Dict[str, Any]:
        """
        Validate the structural integrity of form content.
        
        Args:
            content: Content to validate
            form_name: Name of the form
            
        Returns:
            Dictionary with form structure validation results
        """
        content_lower = content.lower()
        
        # Form structure validation patterns
        structure_checks = {
            "form_header": {
                "patterns": [
                    r"form.*\d+", r"statement of", r"certified payroll", r"prevailing wage",
                    r"department of", r"agency", r"government"
                ],
                "required": True
            },
            "section_headers": {
                "patterns": [
                    r"section \d+", r"part \d+", r"employee information", r"wage information",
                    r"certification", r"signature", r"date"
                ],
                "required": True
            },
            "data_fields": {
                "patterns": [
                    r"name:", r"address:", r"ssn:", r"rate:", r"hours:", r"date:",
                    r"project:", r"contract:", r"classification:"
                ],
                "required": True
            },
            "certification_block": {
                "patterns": [
                    r"certify", r"under penalty", r"perjury", r"swear", r"affirm",
                    r"signature", r"date", r"authorized"
                ],
                "required": True
            },
            "instructions": {
                "patterns": [
                    r"instructions", r"directions", r"complete", r"fill", r"submit",
                    r"return", r"mail", r"file"
                ],
                "required": False
            }
        }
        
        structure_results = {}
        total_score = 0
        max_score = 0
        
        for check_name, check_config in structure_checks.items():
            # Count pattern matches
            matches = []
            for pattern in check_config["patterns"]:
                if re.search(pattern, content_lower):
                    matches.append(pattern)
            
            # Calculate score
            score = len(matches) / len(check_config["patterns"]) * 100
            max_score += 100
            
            structure_results[check_name] = {
                "patterns_found": matches,
                "score": score,
                "required": check_config["required"],
                "is_present": len(matches) > 0
            }
            
            if check_config["required"]:
                total_score += score
        
        structure_integrity_score = (total_score / max_score) * 100 if max_score > 0 else 0
        
        return {
            "structure_integrity_score": structure_integrity_score,
            "structure_results": structure_results,
            "has_required_elements": all(
                result["is_present"] for result in structure_results.values() 
                if result["required"]
            ),
            "missing_required_elements": [
                check_name for check_name, result in structure_results.items()
                if result["required"] and not result["is_present"]
            ]
        }
    
    async def analyze_document_changes_enhanced(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Perform enhanced document change analysis with false positive reduction.
        
        Args:
            request: Analysis request with document content and parameters
            
        Returns:
            Enhanced analysis response with false positive detection
        """
        analysis_id = self._generate_analysis_id()
        start_time = time.time()
        
        logger.info(f"Starting enhanced analysis {analysis_id} for {request.form_name or 'unknown form'}")
        
        try:
            # Step 1: False positive detection
            false_positive_result = self._detect_false_positives(request.old_content, request.new_content)
            
            # Step 2: Content relevance validation
            relevance_result = self._validate_content_relevance(
                request.new_content, request.form_name, request.agency_name
            )
            
            # Step 3: Compliance-specific content validation
            compliance_validation = self._validate_compliance_specific_content(
                request.new_content, request.form_name, request.agency_name
            )
            
            # Step 4: Form structure integrity validation
            structure_validation = self._validate_form_structure_integrity(
                request.new_content, request.form_name
            )
            
            # Step 5: Semantic change detection
            semantic_changes = self._detect_semantic_changes(request.old_content, request.new_content)
            
            # Step 4: If false positive detected, return early with minimal analysis
            if false_positive_result["is_false_positive"]:
                logger.info(f"False positive detected for {analysis_id}: {false_positive_result['reasons']}")
                
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                return AnalysisResponse(
                    analysis_id=analysis_id,
                    timestamp=datetime.utcnow(),
                    has_meaningful_changes=False,
                    classification=ChangeClassification(
                        category="cosmetic_change",
                        subcategory="false_positive",
                        severity="low",
                        priority_score=5,
                        is_cosmetic=True,
                        confidence=95
                    ),
                    semantic_analysis=SemanticAnalysis(
                        similarity_score=95,
                        significant_differences=[],
                        change_indicators=["False positive detected"],
                        model_name=self.change_analyzer.model_name,
                        processing_time_ms=processing_time_ms
                    ),
                    llm_analysis=None,
                    processing_summary={
                        "processing_time_ms": processing_time_ms,
                        "false_positive_detected": True,
                        "false_positive_confidence": false_positive_result["confidence"],
                        "false_positive_patterns": false_positive_result["patterns"],
                        "content_relevance": relevance_result,
                        "compliance_validation": compliance_validation,
                        "structure_validation": structure_validation,
                        "analysis_version": "2.0_enhanced"
                    },
                    confidence_breakdown={
                        "false_positive_score": false_positive_result["confidence"],
                        "relevance_score": relevance_result["relevance_percentage"],
                        "overall": 95
                    }
                )
            
            # Step 5: Perform standard analysis if not a false positive
            standard_result = await super().analyze_document_changes(request)
            
            # Step 6: Enhance the result with additional metadata
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Update processing summary
            enhanced_summary = {
                **standard_result.processing_summary,
                "false_positive_detected": False,
                "false_positive_confidence": false_positive_result["confidence"],
                "semantic_changes": semantic_changes,
                "content_relevance": relevance_result,
                "compliance_validation": compliance_validation,
                "structure_validation": structure_validation,
                "analysis_version": "2.0_enhanced"
            }
            
            # Update confidence breakdown
            enhanced_confidence = {
                **standard_result.confidence_breakdown,
                "false_positive_score": false_positive_result["confidence"],
                "relevance_score": relevance_result["relevance_percentage"],
                "compliance_score": compliance_validation["overall_compliance_score"],
                "structure_score": structure_validation["structure_integrity_score"],
                "semantic_impact": self._calculate_semantic_impact_score(semantic_changes)
            }
            
            # Create enhanced response
            enhanced_response = AnalysisResponse(
                analysis_id=analysis_id,
                timestamp=standard_result.timestamp,
                has_meaningful_changes=standard_result.has_meaningful_changes,
                classification=standard_result.classification,
                semantic_analysis=standard_result.semantic_analysis,
                llm_analysis=standard_result.llm_analysis,
                processing_summary=enhanced_summary,
                confidence_breakdown=enhanced_confidence
            )
            
            # Track analysis history
            self._track_analysis_history(request.form_name, enhanced_response)
            
            logger.info(f"Enhanced analysis {analysis_id} completed successfully in {processing_time_ms}ms")
            return enhanced_response
            
        except Exception as e:
            error_msg = f"Enhanced analysis {analysis_id} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.analysis_stats["failed_analyses"] += 1
            raise AnalysisProcessingError(error_msg) from e
    
    def _calculate_semantic_impact_score(self, semantic_changes: Dict[str, Any]) -> int:
        """Calculate semantic impact score based on detected changes."""
        impact_scores = {
            "critical": 90,
            "high": 70,
            "medium": 50,
            "low": 20
        }
        
        return impact_scores.get(semantic_changes["overall_impact"], 50)
    
    def _track_analysis_history(self, form_name: str, result: AnalysisResponse) -> None:
        """Track analysis history for pattern recognition."""
        if not form_name:
            return
        
        # Store recent analysis results
        self.analysis_history[form_name].append({
            "timestamp": result.timestamp,
            "has_meaningful_changes": result.has_meaningful_changes,
            "confidence": result.confidence_breakdown.get("overall", 0),
            "false_positive_score": result.confidence_breakdown.get("false_positive_score", 0)
        })
        
        # Keep only last 10 analyses per form
        if len(self.analysis_history[form_name]) > 10:
            self.analysis_history[form_name] = self.analysis_history[form_name][-10:]
        
        # Track false positive patterns
        if result.processing_summary.get("false_positive_detected", False):
            self.false_positive_history[form_name] += 1
    
    def get_enhanced_service_stats(self) -> Dict[str, Any]:
        """Get enhanced service statistics including false positive tracking."""
        base_stats = self.get_service_stats()
        
        # Calculate false positive rates
        total_forms = len(self.analysis_history)
        total_false_positives = sum(self.false_positive_history.values())
        total_analyses = sum(len(history) for history in self.analysis_history.values())
        
        false_positive_rate = (total_false_positives / total_analyses * 100) if total_analyses > 0 else 0
        
        return {
            **base_stats,
            "enhanced_features": {
                "false_positive_detection": True,
                "semantic_change_detection": True,
                "content_relevance_validation": True,
                "analysis_history_tracking": True
            },
            "false_positive_stats": {
                "total_false_positives_detected": total_false_positives,
                "false_positive_rate_percentage": round(false_positive_rate, 2),
                "forms_with_false_positives": len(self.false_positive_history),
                "total_forms_analyzed": total_forms
            },
            "analysis_history": {
                "total_historical_analyses": total_analyses,
                "average_confidence_score": self._calculate_average_confidence(),
                "most_analyzed_forms": self._get_most_analyzed_forms()
            }
        }
    
    def _calculate_average_confidence(self) -> float:
        """Calculate average confidence across all historical analyses."""
        all_confidences = []
        for history in self.analysis_history.values():
            all_confidences.extend([analysis["confidence"] for analysis in history])
        
        return sum(all_confidences) / len(all_confidences) if all_confidences else 0
    
    def _get_most_analyzed_forms(self) -> List[Dict[str, Any]]:
        """Get list of most analyzed forms."""
        form_stats = []
        for form_name, history in self.analysis_history.items():
            form_stats.append({
                "form_name": form_name,
                "analysis_count": len(history),
                "false_positive_count": self.false_positive_history.get(form_name, 0),
                "average_confidence": sum(analysis["confidence"] for analysis in history) / len(history)
            })
        
        # Sort by analysis count
        form_stats.sort(key=lambda x: x["analysis_count"], reverse=True)
        return form_stats[:5]  # Top 5
    
    async def health_check_enhanced(self) -> Dict[str, Any]:
        """Perform enhanced health check including false positive detection."""
        base_health = await self.health_check()
        
        # Test false positive detection
        test_old = "This is a test document with some content."
        test_new = "This is a test document with some content.  "  # Extra whitespace
        
        false_positive_result = self._detect_false_positives(test_old, test_new)
        
        # Test semantic change detection
        semantic_result = self._detect_semantic_changes(test_old, test_new)
        
        # Test content relevance validation
        relevance_result = self._validate_content_relevance(
            "This is a payroll compliance form with requirements and deadlines."
        )
        
        enhanced_health = {
            **base_health,
            "enhanced_features": {
                "false_positive_detection": "healthy" if false_positive_result["is_false_positive"] else "degraded",
                "semantic_change_detection": "healthy" if semantic_result else "degraded",
                "content_relevance_validation": "healthy" if relevance_result["is_relevant"] else "degraded"
            },
            "false_positive_threshold": self.false_positive_threshold,
            "semantic_similarity_threshold": self.semantic_similarity_threshold
        }
        
        return enhanced_health 