"""
Pydantic models for AI analysis requests and responses.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field, validator


class AnalysisRequest(BaseModel):
    """Request model for document change analysis."""
    
    old_content: str = Field(..., description="Original document content")
    new_content: str = Field(..., description="Updated document content")
    document_type: str = Field(default="form", description="Type of document being analyzed")
    form_name: Optional[str] = Field(None, description="Name of the form (e.g., WH-347)")
    agency_name: Optional[str] = Field(None, description="Name of the agency")
    confidence_threshold: int = Field(default=70, ge=0, le=100, description="Minimum confidence threshold for AI analysis")
    use_llm_fallback: bool = Field(default=True, description="Whether to use LLM analysis for low-confidence cases")
    
    @validator('confidence_threshold')
    def validate_confidence_threshold(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Confidence threshold must be between 0 and 100')
        return v


class ChangeClassification(BaseModel):
    """Classification of detected changes."""
    
    category: Literal["form_update", "requirement_change", "logic_modification", "cosmetic_change"] = Field(
        ..., description="Primary category of the change"
    )
    subcategory: Optional[str] = Field(None, description="More specific classification")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Severity level")
    priority_score: int = Field(..., ge=0, le=100, description="Priority score (0-100)")
    is_cosmetic: bool = Field(..., description="Whether the change is purely cosmetic")
    confidence: int = Field(..., ge=0, le=100, description="AI confidence in classification")


class SemanticAnalysis(BaseModel):
    """Semantic similarity analysis results."""
    
    similarity_score: int = Field(..., ge=0, le=100, description="Semantic similarity percentage")
    significant_differences: List[str] = Field(default_factory=list, description="List of significant differences found")
    change_indicators: List[str] = Field(default_factory=list, description="Indicators that suggest meaningful changes")
    model_name: str = Field(..., description="Name of the model used for analysis")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class LLMAnalysis(BaseModel):
    """LLM-based analysis results."""
    
    reasoning: str = Field(..., description="Detailed explanation of the analysis")
    key_changes: List[str] = Field(default_factory=list, description="List of key changes identified")
    impact_assessment: str = Field(..., description="Assessment of potential impact")
    recommendations: List[str] = Field(default_factory=list, description="Recommended actions")
    model_used: str = Field(..., description="LLM model used for analysis")
    tokens_used: Optional[int] = Field(None, description="Number of tokens consumed")


class AnalysisResponse(BaseModel):
    """Response model for document change analysis."""
    
    analysis_id: str = Field(..., description="Unique identifier for this analysis")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    
    # Core results
    has_meaningful_changes: bool = Field(..., description="Whether meaningful changes were detected")
    classification: ChangeClassification = Field(..., description="Change classification results")
    
    # Analysis details
    semantic_analysis: SemanticAnalysis = Field(..., description="Semantic similarity analysis")
    llm_analysis: Optional[LLMAnalysis] = Field(None, description="LLM analysis (if performed)")
    
    # Metadata
    processing_summary: Dict[str, Any] = Field(default_factory=dict, description="Processing metadata")
    confidence_breakdown: Dict[str, int] = Field(default_factory=dict, description="Confidence scores by component")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnalysisError(BaseModel):
    """Error response model for analysis failures."""
    
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    analysis_id: Optional[str] = Field(None, description="Analysis ID if available")


class BatchAnalysisRequest(BaseModel):
    """Request model for batch analysis of multiple documents."""
    
    analyses: List[AnalysisRequest] = Field(..., max_items=10, description="List of analysis requests")
    batch_id: Optional[str] = Field(None, description="Optional batch identifier")
    
    @validator('analyses')
    def validate_analyses_not_empty(cls, v):
        if not v:
            raise ValueError('At least one analysis request is required')
        return v


class BatchAnalysisResponse(BaseModel):
    """Response model for batch analysis."""
    
    batch_id: str = Field(..., description="Batch identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Batch processing timestamp")
    total_analyses: int = Field(..., description="Total number of analyses requested")
    successful_analyses: int = Field(..., description="Number of successful analyses")
    failed_analyses: int = Field(..., description="Number of failed analyses")
    
    results: List[AnalysisResponse] = Field(default_factory=list, description="Successful analysis results")
    errors: List[AnalysisError] = Field(default_factory=list, description="Analysis errors")
    
    processing_time_ms: int = Field(..., description="Total processing time in milliseconds")