"""
FastAPI endpoints for AI-powered document analysis.

This module provides REST API endpoints for document change detection,
analysis, and batch processing with comprehensive error handling.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse

from ..analysis import (
    AnalysisService, AnalysisRequest, AnalysisResponse, AnalysisError,
    BatchAnalysisRequest, BatchAnalysisResponse,
    AnalysisTimeoutError, AnalysisProcessingError
)

logger = logging.getLogger(__name__)

# Create router for analysis endpoints
router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Global analysis service instance
_analysis_service: AnalysisService = None


def get_analysis_service() -> AnalysisService:
    """Get or create the analysis service instance."""
    global _analysis_service
    if _analysis_service is None:
        _analysis_service = AnalysisService()
    return _analysis_service


@router.post("/compare", response_model=AnalysisResponse)
async def analyze_document_changes(
    request: AnalysisRequest,
    service: AnalysisService = Depends(get_analysis_service)
) -> AnalysisResponse:
    """
    Analyze changes between two document versions.
    
    This endpoint performs comprehensive AI-powered analysis including:
    - Semantic similarity detection
    - Change classification and categorization
    - Severity scoring and priority assessment
    - LLM-based reasoning (when confidence thresholds are met)
    
    **Example Request:**
    ```json
    {
        "old_content": "Original form content...",
        "new_content": "Updated form content...",
        "form_name": "WH-347",
        "agency_name": "Department of Labor",
        "confidence_threshold": 75,
        "use_llm_fallback": true
    }
    ```
    
    **Response includes:**
    - Change classification (form_update, requirement_change, etc.)
    - Severity level (low, medium, high, critical)
    - Semantic similarity scores
    - Detailed reasoning and recommendations
    - Processing metadata and confidence scores
    """
    try:
        logger.info(f"Received analysis request for {request.form_name or 'unknown form'}")
        
        # Validate request content
        if not request.old_content.strip() or not request.new_content.strip():
            raise HTTPException(
                status_code=400,
                detail="Both old_content and new_content must be non-empty"
            )
        
        # Perform analysis
        result = await service.analyze_document_changes(request)
        
        logger.info(f"Analysis completed successfully: {result.analysis_id}")
        return result
        
    except AnalysisTimeoutError as e:
        logger.error(f"Analysis timeout: {e}")
        raise HTTPException(status_code=408, detail=str(e))
        
    except AnalysisProcessingError as e:
        logger.error(f"Analysis processing error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during analysis")


@router.post("/batch", response_model=BatchAnalysisResponse)
async def analyze_batch_documents(
    batch_request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    service: AnalysisService = Depends(get_analysis_service)
) -> BatchAnalysisResponse:
    """
    Analyze multiple document pairs in parallel.
    
    This endpoint processes up to 10 document comparisons simultaneously,
    providing efficient batch processing for bulk analysis operations.
    
    **Example Request:**
    ```json
    {
        "batch_id": "batch_2024_001",
        "analyses": [
            {
                "old_content": "Form version 1...",
                "new_content": "Form version 2...",
                "form_name": "WH-347"
            },
            {
                "old_content": "Another form v1...",
                "new_content": "Another form v2...",
                "form_name": "CA_A1131"
            }
        ]
    }
    ```
    
    **Performance Notes:**
    - Maximum 10 analyses per batch
    - Parallel processing for optimal performance
    - Individual analysis failures don't affect other results
    """
    try:
        logger.info(f"Received batch analysis request with {len(batch_request.analyses)} items")
        
        # Validate batch size
        if len(batch_request.analyses) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 analyses allowed per batch"
            )
        
        # Process batch
        result = await service.analyze_batch(batch_request)
        
        logger.info(f"Batch analysis completed: {result.successful_analyses} successful, {result.failed_analyses} failed")
        return result
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during batch analysis")


@router.get("/health")
async def health_check(
    service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, Any]:
    """
    Check the health status of all analysis components.
    
    Returns the operational status of:
    - Overall analysis service
    - Semantic similarity analyzer
    - LLM classifier
    - Component availability and performance
    
    **Response Status Meanings:**
    - `healthy`: Component fully operational
    - `degraded`: Component operational with limitations
    - `unhealthy`: Component not functioning
    """
    try:
        health_status = await service.health_check()
        
        # Set HTTP status based on overall health
        if health_status["service"] == "unhealthy":
            return JSONResponse(status_code=503, content=health_status)
        elif health_status["service"] == "degraded":
            return JSONResponse(status_code=200, content=health_status)  # Still usable
        else:
            return health_status
            
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "service": "unhealthy",
                "error": str(e),
                "timestamp": "unknown"
            }
        )


@router.get("/stats")
async def get_service_statistics(
    service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, Any]:
    """
    Get performance statistics and metrics for the analysis service.
    
    Returns detailed metrics including:
    - Total analyses performed
    - Success/failure rates
    - Average processing times
    - Cache hit rates
    - LLM fallback usage
    
    **Useful for:**
    - Performance monitoring
    - Capacity planning
    - Service optimization
    """
    try:
        stats = service.get_service_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving service stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving service statistics")


@router.post("/cache/clear")
async def clear_analysis_cache(
    service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, str]:
    """
    Clear the analysis result cache.
    
    This endpoint clears all cached analysis results, which may be useful:
    - After model updates or configuration changes
    - To free memory in resource-constrained environments
    - For testing purposes
    
    **Note:** Clearing cache will impact performance for subsequent
    analyses of previously processed document pairs.
    """
    try:
        service.clear_cache()
        return {"status": "success", "message": "Analysis cache cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error clearing analysis cache")


@router.get("/models/info")
async def get_model_information(
    service: AnalysisService = Depends(get_analysis_service)
) -> Dict[str, Any]:
    """
    Get information about the AI models currently in use.
    
    Returns details about:
    - Semantic similarity model name and version
    - LLM model configuration
    - Model availability status
    - Capability information
    """
    try:
        model_info = {
            "semantic_model": {
                "name": service.change_analyzer.model_name,
                "similarity_threshold": service.change_analyzer.similarity_threshold,
                "status": "loaded" if service.change_analyzer.model else "not_loaded"
            },
            "llm_model": {
                "name": service.llm_classifier.model_name,
                "temperature": service.llm_classifier.temperature,
                "max_tokens": service.llm_classifier.max_tokens,
                "status": "available" if service.llm_classifier.client else "fallback_only"
            },
            "service_config": {
                "confidence_threshold": service.default_confidence_threshold,
                "max_processing_time": service.max_processing_time_seconds,
                "caching_enabled": service.enable_caching
            }
        }
        
        return model_info
        
    except Exception as e:
        logger.error(f"Error retrieving model info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving model information")


@router.get("/examples")
async def get_api_examples() -> Dict[str, Any]:
    """
    Get example requests and responses for the analysis API.
    
    Provides comprehensive examples for:
    - Single document analysis
    - Batch processing
    - Different form types and scenarios
    - Expected response formats
    
    **Useful for:**
    - API integration testing
    - Understanding request/response formats
    - Development and debugging
    """
    examples = {
        "single_analysis": {
            "request": {
                "old_content": "Employee Name: ________________\nHours Worked: ________\nRate: $15.00/hour",
                "new_content": "Employee Name: ________________\nRegular Hours: ________\nOvertime Hours: ________\nBase Rate: $15.50/hour\nOvertime Rate: $23.25/hour",
                "form_name": "WH-347",
                "agency_name": "Department of Labor",
                "confidence_threshold": 70,
                "use_llm_fallback": True
            },
            "response_example": {
                "analysis_id": "analysis_abc123_1234567890",
                "timestamp": "2024-01-15T10:30:00Z",
                "has_meaningful_changes": True,
                "classification": {
                    "category": "requirement_change",
                    "subcategory": "field_modification",
                    "severity": "medium",
                    "priority_score": 65,
                    "is_cosmetic": False,
                    "confidence": 85
                },
                "semantic_analysis": {
                    "similarity_score": 72,
                    "significant_differences": [
                        "New overtime tracking fields added",
                        "Rate structure modified to include overtime rates"
                    ],
                    "change_indicators": [
                        "New important terms: overtime, base rate",
                        "Structural change: 3 -> 5 lines"
                    ],
                    "model_name": "all-MiniLM-L6-v2",
                    "processing_time_ms": 245
                }
            }
        },
        "batch_analysis": {
            "request": {
                "batch_id": "batch_monthly_review",
                "analyses": [
                    {
                        "old_content": "Form content 1...",
                        "new_content": "Updated form content 1...",
                        "form_name": "WH-347"
                    },
                    {
                        "old_content": "Form content 2...",
                        "new_content": "Updated form content 2...",
                        "form_name": "CA_A1131"
                    }
                ]
            }
        },
        "error_responses": {
            "400_bad_request": {
                "detail": "Both old_content and new_content must be non-empty"
            },
            "408_timeout": {
                "detail": "Analysis analysis_xyz789_1234567890 timed out after 180 seconds"
            },
            "500_internal_error": {
                "detail": "Internal server error during analysis"
            }
        }
    }
    
    return examples