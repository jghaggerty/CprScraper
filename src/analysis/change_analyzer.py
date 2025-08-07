"""
ChangeAnalyzer: Core semantic similarity analysis for document changes.

This module provides fast, accurate detection of meaningful changes between
document versions using sentence transformers and semantic similarity analysis.
"""

import re
import time
import logging
import difflib
from typing import List, Tuple, Dict, Set, Any
from dataclasses import dataclass
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import Levenshtein
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    # Note: logger is not available yet, will be set up later

from .models import SemanticAnalysis

logger = logging.getLogger(__name__)


@dataclass
class DocumentSection:
    """Represents a section of a document for analysis."""
    content: str
    section_type: str  # 'header', 'instruction', 'field', 'requirement', 'other'
    line_start: int
    line_end: int
    

class ChangeAnalyzer:
    """
    Analyzes document changes using semantic similarity and NLP techniques.
    
    Features:
    - Sentence transformer-based semantic similarity
    - Document structure-aware comparison
    - Cosmetic change filtering
    - Performance optimization for real-time analysis
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", similarity_threshold: float = 0.85):
        """
        Initialize the ChangeAnalyzer.
        
        Args:
            model_name: Sentence transformer model to use
            similarity_threshold: Threshold below which changes are considered significant
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.model = None
        
        if DEPENDENCIES_AVAILABLE:
            self._load_model()
        else:
            logger.warning("Dependencies not available. Using mock implementation.")
        
        # Patterns for detecting cosmetic changes
        self.cosmetic_patterns = [
            r'\s+',  # Whitespace changes
            r'^\s*$',  # Empty lines
            r'<!--.*?-->',  # HTML comments
            r'<!\[CDATA\[.*?\]\]>',  # CDATA sections
            r'<!--\s*.*?\s*-->',  # More HTML comments
            r'/\*.*?\*/',  # CSS/JS comments
            r'//.*$',  # Line comments
        ]
        
        # Keywords that indicate important content
        self.important_keywords = {
            'requirement', 'mandatory', 'required', 'must', 'shall', 'should',
            'deadline', 'date', 'amount', 'rate', 'wage', 'hour', 'overtime',
            'employee', 'employer', 'contractor', 'subcontractor',
            'form', 'report', 'statement', 'certification', 'compliance',
            'penalty', 'fine', 'violation', 'enforcement'
        }
        
    def _load_model(self) -> None:
        """Load the sentence transformer model."""
        if not DEPENDENCIES_AVAILABLE:
            logger.warning("Cannot load model - dependencies not available")
            return
            
        try:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model {self.model_name}: {e}")
            raise
    
    def preprocess_document(self, content: str) -> Tuple[str, List[DocumentSection]]:
        """
        Preprocess document content and extract structured sections.
        
        Args:
            content: Raw document content
            
        Returns:
            Tuple of (cleaned_content, document_sections)
        """
        # Remove excessive whitespace but preserve structure
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        
        # Split into lines for section analysis
        lines = content.split('\n')
        sections = []
        current_section = []
        current_type = 'other'
        line_start = 0
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Detect section types based on patterns
            section_type = self._classify_line_type(line)
            
            if section_type != current_type and current_section:
                # Save previous section
                sections.append(DocumentSection(
                    content='\n'.join(current_section),
                    section_type=current_type,
                    line_start=line_start,
                    line_end=i-1
                ))
                current_section = []
                line_start = i
                current_type = section_type
            
            current_section.append(line)
        
        # Add final section
        if current_section:
            sections.append(DocumentSection(
                content='\n'.join(current_section),
                section_type=current_type,
                line_start=line_start,
                line_end=len(lines)-1
            ))
        
        # Rejoin cleaned content
        cleaned_content = '\n'.join([s.content for s in sections])
        
        return cleaned_content, sections
    
    def _classify_line_type(self, line: str) -> str:
        """Classify a line by its content type."""
        line_lower = line.lower()
        
        # Headers (numbered sections, bold text indicators, etc.)
        if re.match(r'^\d+\.', line) or re.match(r'^[A-Z\s]+:?$', line):
            return 'header'
        
        # Instructions/procedures
        if any(word in line_lower for word in ['instruction', 'procedure', 'step', 'how to']):
            return 'instruction'
        
        # Form fields
        if re.search(r'_+|\.{3,}|\[\s*\]', line) or 'field' in line_lower:
            return 'field'
        
        # Requirements
        if any(word in line_lower for word in ['must', 'required', 'shall', 'mandatory']):
            return 'requirement'
        
        return 'other'
    
    def calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        if not DEPENDENCIES_AVAILABLE or self.model is None:
            # Fallback to simple text comparison
            if text1 == text2:
                return 1.0
            elif text1.lower() == text2.lower():
                return 0.9
            else:
                # Simple similarity based on common words
                words1 = set(text1.lower().split())
                words2 = set(text2.lower().split())
                if not words1 and not words2:
                    return 1.0
                intersection = words1.intersection(words2)
                union = words1.union(words2)
                return len(intersection) / len(union) if union else 0.0
        
        try:
            # Encode texts
            embeddings = self.model.encode([text1, text2])
            
            # Calculate cosine similarity
            similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
            
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating semantic similarity: {e}")
            return 0.0
    
    def detect_significant_changes(self, old_content: str, new_content: str) -> List[str]:
        """
        Detect significant changes between document versions.
        
        Args:
            old_content: Original document content
            new_content: Updated document content
            
        Returns:
            List of significant changes detected
        """
        changes = []
        
        # Preprocess both documents
        old_clean, old_sections = self.preprocess_document(old_content)
        new_clean, new_sections = self.preprocess_document(new_content)
        
        # Compare section by section
        old_by_type = self._group_sections_by_type(old_sections)
        new_by_type = self._group_sections_by_type(new_sections)
        
        for section_type in set(old_by_type.keys()) | set(new_by_type.keys()):
            old_type_content = old_by_type.get(section_type, [])
            new_type_content = new_by_type.get(section_type, [])
            
            section_changes = self._compare_section_type(
                old_type_content, new_type_content, section_type
            )
            changes.extend(section_changes)
        
        return changes
    
    def _group_sections_by_type(self, sections: List[DocumentSection]) -> Dict[str, List[str]]:
        """Group document sections by their type."""
        grouped = {}
        for section in sections:
            if section.section_type not in grouped:
                grouped[section.section_type] = []
            grouped[section.section_type].append(section.content)
        return grouped
    
    def _compare_section_type(self, old_sections: List[str], new_sections: List[str], section_type: str) -> List[str]:
        """Compare sections of the same type."""
        changes = []
        
        old_combined = '\n'.join(old_sections)
        new_combined = '\n'.join(new_sections)
        
        if not old_combined and new_combined:
            changes.append(f"New {section_type} section added: {new_combined[:100]}...")
        elif old_combined and not new_combined:
            changes.append(f"{section_type.title()} section removed: {old_combined[:100]}...")
        elif old_combined and new_combined:
            similarity = self.calculate_semantic_similarity(old_combined, new_combined)
            
            if similarity < self.similarity_threshold:
                # Significant change detected
                change_details = self._analyze_specific_changes(old_combined, new_combined)
                changes.append(f"{section_type.title()} section modified (similarity: {similarity:.2f}): {change_details}")
        
        return changes
    
    def _analyze_specific_changes(self, old_text: str, new_text: str) -> str:
        """Analyze specific changes between two texts."""
        # Use difflib to find specific differences
        differ = difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            lineterm=''
        )
        
        diff_lines = list(differ)
        if len(diff_lines) <= 4:  # Only headers, no actual changes
            return "Minor modifications detected"
        
        # Extract meaningful changes
        additions = [line[1:] for line in diff_lines if line.startswith('+') and not line.startswith('+++')]
        deletions = [line[1:] for line in diff_lines if line.startswith('-') and not line.startswith('---')]
        
        change_summary = []
        if additions:
            change_summary.append(f"Added: {'; '.join(additions[:3])}")
        if deletions:
            change_summary.append(f"Removed: {'; '.join(deletions[:3])}")
        
        return '; '.join(change_summary)[:200]
    
    def is_cosmetic_change(self, old_content: str, new_content: str) -> bool:
        """
        Determine if changes are purely cosmetic (formatting, whitespace, etc.).
        
        Args:
            old_content: Original content
            new_content: Updated content
            
        Returns:
            True if changes are cosmetic, False otherwise
        """
        # Normalize both texts by removing common cosmetic elements
        old_normalized = self._normalize_for_cosmetic_check(old_content)
        new_normalized = self._normalize_for_cosmetic_check(new_content)
        
        # If normalized versions are identical, changes are cosmetic
        if old_normalized == new_normalized:
            return True
        
        # Calculate Levenshtein distance on normalized text
        distance = Levenshtein.distance(old_normalized, new_normalized)
        max_length = max(len(old_normalized), len(new_normalized))
        
        if max_length == 0:
            return True
        
        # If changes are very small relative to document size, likely cosmetic
        change_ratio = distance / max_length
        return change_ratio < 0.05  # Less than 5% change
    
    def _normalize_for_cosmetic_check(self, content: str) -> str:
        """Normalize content for cosmetic change detection."""
        # Remove all whitespace variations
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common formatting elements
        for pattern in self.cosmetic_patterns:
            content = re.sub(pattern, '', content, flags=re.MULTILINE | re.DOTALL)
        
        # Convert to lowercase for comparison
        content = content.lower().strip()
        
        return content
    
    def generate_change_indicators(self, old_content: str, new_content: str) -> List[str]:
        """
        Generate indicators of what types of changes occurred.
        
        Args:
            old_content: Original content
            new_content: Updated content
            
        Returns:
            List of change indicators
        """
        indicators = []
        
        # Check for important keyword changes
        old_keywords = self._extract_important_keywords(old_content)
        new_keywords = self._extract_important_keywords(new_content)
        
        added_keywords = new_keywords - old_keywords
        removed_keywords = old_keywords - new_keywords
        
        if added_keywords:
            indicators.append(f"New important terms: {', '.join(list(added_keywords)[:5])}")
        if removed_keywords:
            indicators.append(f"Removed important terms: {', '.join(list(removed_keywords)[:5])}")
        
        # Check for structural changes
        old_lines = len(old_content.splitlines())
        new_lines = len(new_content.splitlines())
        
        if abs(new_lines - old_lines) > old_lines * 0.1:  # More than 10% line change
            indicators.append(f"Significant structural change: {old_lines} -> {new_lines} lines")
        
        # Check for URL/link changes
        old_urls = set(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', old_content))
        new_urls = set(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', new_content))
        
        if old_urls != new_urls:
            indicators.append("URL/link changes detected")
        
        return indicators
    
    def _extract_important_keywords(self, content: str) -> Set[str]:
        """Extract important keywords from content."""
        content_lower = content.lower()
        found_keywords = set()
        
        for keyword in self.important_keywords:
            if keyword in content_lower:
                found_keywords.add(keyword)
        
        return found_keywords
    
    def analyze(self, old_content: str, new_content: str) -> SemanticAnalysis:
        """
        Perform complete semantic analysis of document changes.
        
        Args:
            old_content: Original document content
            new_content: Updated document content
            
        Returns:
            SemanticAnalysis object with complete results
        """
        start_time = time.time()
        
        try:
            # Calculate overall semantic similarity
            similarity = self.calculate_semantic_similarity(old_content, new_content)
            similarity_percentage = int(similarity * 100)
            
            # Detect significant changes
            significant_differences = self.detect_significant_changes(old_content, new_content)
            
            # Generate change indicators
            change_indicators = self.generate_change_indicators(old_content, new_content)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return SemanticAnalysis(
                similarity_score=similarity_percentage,
                significant_differences=significant_differences,
                change_indicators=change_indicators,
                model_name=self.model_name,
                processing_time_ms=processing_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error during semantic analysis: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return SemanticAnalysis(
                similarity_score=0,
                significant_differences=[f"Analysis error: {str(e)}"],
                change_indicators=["Error during analysis"],
                model_name=self.model_name,
                processing_time_ms=processing_time_ms
            )