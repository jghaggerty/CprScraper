"""
AI-powered change detection and analysis package for regulatory document monitoring.

This package provides semantic similarity analysis, change classification,
and severity scoring for government payroll forms and documents.
"""

from .models import (
    AnalysisRequest, 
    AnalysisResponse, 
    ChangeClassification,
    SemanticAnalysis,
    AnalysisError,
    BatchAnalysisRequest,
    BatchAnalysisResponse
)

# Optional imports to avoid dependency issues during testing
try:
    from .change_analyzer import ChangeAnalyzer
    from .llm_classifier import LLMClassifier
    from .analysis_service import AnalysisService, AnalysisTimeoutError, AnalysisProcessingError
    __all__ = [
        "AnalysisRequest",
        "AnalysisResponse", 
        "ChangeClassification",
        "SemanticAnalysis",
        "AnalysisError",
        "BatchAnalysisRequest",
        "BatchAnalysisResponse",
        "ChangeAnalyzer",
        "LLMClassifier",
        "AnalysisService",
        "AnalysisTimeoutError",
        "AnalysisProcessingError"
    ]
except ImportError:
    __all__ = [
        "AnalysisRequest",
        "AnalysisResponse", 
        "ChangeClassification",
        "SemanticAnalysis",
        "AnalysisError",
        "BatchAnalysisRequest",
        "BatchAnalysisResponse"
    ]