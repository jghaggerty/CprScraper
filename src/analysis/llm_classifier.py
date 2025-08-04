"""
LLMClassifier: Advanced change classification using Large Language Models.

This module provides sophisticated analysis of document changes using LLMs
for categorization, severity scoring, and impact assessment with fallback logic.
"""

import json
import time
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import os

try:
    import openai
except ImportError:
    openai = None

from .models import LLMAnalysis, ChangeClassification

logger = logging.getLogger(__name__)


class ChangeCategory(Enum):
    """Enumeration of change categories."""
    FORM_UPDATE = "form_update"
    REQUIREMENT_CHANGE = "requirement_change"
    LOGIC_MODIFICATION = "logic_modification"
    COSMETIC_CHANGE = "cosmetic_change"


class SeverityLevel(Enum):
    """Enumeration of severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LLMClassifier:
    """
    Classifies document changes using Large Language Models.
    
    Features:
    - OpenAI GPT-based change analysis
    - Structured classification prompts
    - Fallback to rule-based classification
    - Confidence scoring and reasoning
    """
    
    def __init__(self, 
                 model_name: str = "gpt-3.5-turbo",
                 api_key: Optional[str] = None,
                 temperature: float = 0.1,
                 max_tokens: int = 1000):
        """
        Initialize the LLMClassifier.
        
        Args:
            model_name: OpenAI model to use
            api_key: OpenAI API key (or from environment)
            temperature: Sampling temperature for responses
            max_tokens: Maximum tokens in response
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize OpenAI client
        self.client = None
        if openai:
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = openai.OpenAI(api_key=api_key)
            else:
                logger.warning("No OpenAI API key provided. LLM analysis will use fallback methods.")
        else:
            logger.warning("OpenAI library not installed. LLM analysis will use fallback methods.")
        
        # Rule-based patterns for fallback classification
        self.classification_patterns = {
            ChangeCategory.REQUIREMENT_CHANGE: [
                r'\b(must|shall|required|mandatory|obligation)\b',
                r'\b(deadline|due date|time limit)\b',
                r'\b(minimum|maximum|threshold|limit)\b',
                r'\b(penalty|fine|violation|non-compliance)\b'
            ],
            ChangeCategory.LOGIC_MODIFICATION: [
                r'\b(calculation|formula|algorithm|method)\b',
                r'\b(if|when|unless|provided that|in case)\b',
                r'\b(workflow|process|procedure|step)\b',
                r'\b(validation|verification|check)\b'
            ],
            ChangeCategory.FORM_UPDATE: [
                r'\b(field|box|line|section|page)\b',
                r'\b(form number|version|revision)\b',
                r'\b(layout|format|structure)\b',
                r'\b(instructions|guidance|help text)\b'
            ]
        }
        
        self.severity_keywords = {
            SeverityLevel.CRITICAL: [
                'critical', 'urgent', 'immediate', 'emergency', 'mandatory compliance',
                'legal requirement', 'regulatory violation', 'penalty'
            ],
            SeverityLevel.HIGH: [
                'important', 'significant', 'major', 'substantial', 'compliance',
                'deadline', 'enforcement', 'audit'
            ],
            SeverityLevel.MEDIUM: [
                'moderate', 'update', 'change', 'modification', 'revision',
                'clarification', 'improvement'
            ],
            SeverityLevel.LOW: [
                'minor', 'small', 'cosmetic', 'formatting', 'style',
                'typo', 'correction', 'editorial'
            ]
        }
    
    def _create_classification_prompt(self, 
                                     old_content: str, 
                                     new_content: str,
                                     form_name: Optional[str] = None,
                                     agency_name: Optional[str] = None) -> str:
        """Create a structured prompt for LLM classification."""
        
        context = f"Form: {form_name}, Agency: {agency_name}" if form_name and agency_name else "Government form"
        
        prompt = f"""You are an expert in regulatory compliance and government forms analysis. 
Analyze the changes between two versions of a {context} and provide a structured classification.

ORIGINAL VERSION:
{old_content[:2000]}

NEW VERSION:
{new_content[:2000]}

Please analyze these changes and respond with a JSON object containing:

1. "category": One of "form_update", "requirement_change", "logic_modification", or "cosmetic_change"
2. "subcategory": More specific classification (e.g., "field_addition", "deadline_change", "calculation_update")
3. "severity": One of "low", "medium", "high", or "critical"
4. "priority_score": Integer from 0-100 indicating urgency
5. "is_cosmetic": Boolean indicating if changes are purely formatting/cosmetic
6. "confidence": Integer from 0-100 indicating your confidence in this analysis
7. "reasoning": Detailed explanation of your analysis
8. "key_changes": Array of 3-5 most important changes identified
9. "impact_assessment": Description of potential impact on compliance/users
10. "recommendations": Array of recommended actions

Focus on:
- Regulatory compliance implications
- Impact on payroll reporting requirements
- Changes affecting data collection or submission
- Modifications to legal requirements or deadlines
- Structural vs cosmetic changes

Respond only with valid JSON, no additional text."""

        return prompt
    
    async def classify_with_llm(self, 
                               old_content: str, 
                               new_content: str,
                               form_name: Optional[str] = None,
                               agency_name: Optional[str] = None) -> Tuple[ChangeClassification, LLMAnalysis]:
        """
        Classify changes using LLM analysis.
        
        Args:
            old_content: Original document content
            new_content: Updated document content
            form_name: Name of the form being analyzed
            agency_name: Name of the agency
            
        Returns:
            Tuple of (ChangeClassification, LLMAnalysis)
        """
        if not self.client:
            raise ValueError("OpenAI client not initialized. Cannot perform LLM analysis.")
        
        start_time = time.time()
        
        try:
            prompt = self._create_classification_prompt(old_content, new_content, form_name, agency_name)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are an expert regulatory compliance analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Create classification object
            classification = ChangeClassification(
                category=result.get("category", "form_update"),
                subcategory=result.get("subcategory"),
                severity=result.get("severity", "medium"),
                priority_score=result.get("priority_score", 50),
                is_cosmetic=result.get("is_cosmetic", False),
                confidence=result.get("confidence", 70)
            )
            
            # Create LLM analysis object
            llm_analysis = LLMAnalysis(
                reasoning=result.get("reasoning", "LLM analysis completed"),
                key_changes=result.get("key_changes", []),
                impact_assessment=result.get("impact_assessment", "Impact assessment pending"),
                recommendations=result.get("recommendations", []),
                model_used=self.model_name,
                tokens_used=response.usage.total_tokens if response.usage else None
            )
            
            return classification, llm_analysis
            
        except Exception as e:
            logger.error(f"Error in LLM classification: {e}")
            # Return fallback classification
            fallback_classification, fallback_analysis = self._fallback_classification(
                old_content, new_content, form_name, agency_name
            )
            return fallback_classification, fallback_analysis
    
    def _fallback_classification(self, 
                                old_content: str, 
                                new_content: str,
                                form_name: Optional[str] = None,
                                agency_name: Optional[str] = None) -> Tuple[ChangeClassification, LLMAnalysis]:
        """
        Fallback rule-based classification when LLM is unavailable.
        
        Args:
            old_content: Original document content
            new_content: Updated document content
            form_name: Name of the form
            agency_name: Name of the agency
            
        Returns:
            Tuple of (ChangeClassification, LLMAnalysis)
        """
        logger.info("Using fallback rule-based classification")
        
        # Combine content for analysis
        combined_content = f"{old_content}\n{new_content}".lower()
        
        # Determine category based on patterns
        category_scores = {}
        for category, patterns in self.classification_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined_content, re.IGNORECASE))
                score += matches
            category_scores[category] = score
        
        # Select category with highest score
        if not category_scores or max(category_scores.values()) == 0:
            primary_category = ChangeCategory.FORM_UPDATE
        else:
            primary_category = max(category_scores, key=category_scores.get)
        
        # Determine severity based on keywords
        severity_scores = {}
        for severity, keywords in self.severity_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in combined_content:
                    score += 1
            severity_scores[severity] = score
        
        # Select severity with highest score
        if not severity_scores or max(severity_scores.values()) == 0:
            severity = SeverityLevel.MEDIUM
        else:
            severity = max(severity_scores, key=severity_scores.get)
        
        # Calculate priority score based on category and severity
        priority_mapping = {
            (ChangeCategory.REQUIREMENT_CHANGE, SeverityLevel.CRITICAL): 95,
            (ChangeCategory.REQUIREMENT_CHANGE, SeverityLevel.HIGH): 80,
            (ChangeCategory.LOGIC_MODIFICATION, SeverityLevel.CRITICAL): 90,
            (ChangeCategory.LOGIC_MODIFICATION, SeverityLevel.HIGH): 75,
            (ChangeCategory.FORM_UPDATE, SeverityLevel.HIGH): 60,
            (ChangeCategory.FORM_UPDATE, SeverityLevel.MEDIUM): 40,
            (ChangeCategory.COSMETIC_CHANGE, SeverityLevel.LOW): 10,
        }
        
        priority_score = priority_mapping.get((primary_category, severity), 50)
        
        # Determine if cosmetic
        is_cosmetic = primary_category == ChangeCategory.COSMETIC_CHANGE or severity == SeverityLevel.LOW
        
        # Generate reasoning
        reasoning = f"Rule-based analysis detected {primary_category.value} with {severity.value} severity. "
        reasoning += f"Classification based on pattern matching and keyword analysis."
        
        # Detect key changes (simplified)
        key_changes = self._detect_key_changes_fallback(old_content, new_content)
        
        classification = ChangeClassification(
            category=primary_category.value,
            subcategory="rule_based_detection",
            severity=severity.value,
            priority_score=priority_score,
            is_cosmetic=is_cosmetic,
            confidence=60  # Lower confidence for rule-based
        )
        
        llm_analysis = LLMAnalysis(
            reasoning=reasoning,
            key_changes=key_changes,
            impact_assessment="Impact assessment requires manual review (fallback mode)",
            recommendations=["Review changes manually", "Consider LLM analysis for detailed assessment"],
            model_used="rule_based_fallback",
            tokens_used=None
        )
        
        return classification, llm_analysis
    
    def _detect_key_changes_fallback(self, old_content: str, new_content: str) -> List[str]:
        """Detect key changes using simple diff analysis."""
        import difflib
        
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        differ = difflib.unified_diff(old_lines, new_lines, lineterm='')
        diff_lines = list(differ)
        
        key_changes = []
        
        # Extract additions and deletions
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                change = f"Added: {line[1:].strip()}"
                if len(change) > 20:  # Only significant additions
                    key_changes.append(change[:100])
            elif line.startswith('-') and not line.startswith('---'):
                change = f"Removed: {line[1:].strip()}"
                if len(change) > 20:  # Only significant deletions
                    key_changes.append(change[:100])
        
        return key_changes[:5]  # Return top 5 changes
    
    def validate_classification(self, classification: ChangeClassification) -> bool:
        """
        Validate classification results.
        
        Args:
            classification: Classification to validate
            
        Returns:
            True if classification is valid, False otherwise
        """
        # Check if category is valid
        valid_categories = [cat.value for cat in ChangeCategory]
        if classification.category not in valid_categories:
            return False
        
        # Check if severity is valid
        valid_severities = [sev.value for sev in SeverityLevel]
        if classification.severity not in valid_severities:
            return False
        
        # Check if scores are in valid range
        if not (0 <= classification.priority_score <= 100):
            return False
        
        if not (0 <= classification.confidence <= 100):
            return False
        
        return True
    
    async def classify(self, 
                      old_content: str, 
                      new_content: str,
                      form_name: Optional[str] = None,
                      agency_name: Optional[str] = None,
                      use_llm: bool = True) -> Tuple[ChangeClassification, Optional[LLMAnalysis]]:
        """
        Main classification method with fallback logic.
        
        Args:
            old_content: Original document content
            new_content: Updated document content
            form_name: Name of the form
            agency_name: Name of the agency
            use_llm: Whether to attempt LLM analysis
            
        Returns:
            Tuple of (ChangeClassification, Optional[LLMAnalysis])
        """
        llm_analysis = None
        
        # Try LLM analysis first if available and requested
        if use_llm and self.client:
            try:
                classification, llm_analysis = await self.classify_with_llm(
                    old_content, new_content, form_name, agency_name
                )
                
                # Validate LLM results
                if self.validate_classification(classification):
                    logger.info(f"LLM classification successful: {classification.category} ({classification.confidence}% confidence)")
                    return classification, llm_analysis
                else:
                    logger.warning("LLM classification validation failed, using fallback")
                    
            except Exception as e:
                logger.error(f"LLM classification failed: {e}")
        
        # Use fallback classification
        classification, fallback_analysis = self._fallback_classification(
            old_content, new_content, form_name, agency_name
        )
        
        # If we had an LLM analysis but it failed validation, keep it for reference
        if llm_analysis is None:
            llm_analysis = fallback_analysis
        
        return classification, llm_analysis