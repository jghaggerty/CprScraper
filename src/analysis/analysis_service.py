"""
AnalysisService: Orchestrates AI-powered change detection workflows.

This service coordinates semantic analysis and LLM classification to provide
comprehensive document change analysis with performance monitoring and audit trails.
"""

import uuid
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from .models import (
    AnalysisRequest, AnalysisResponse, AnalysisError,
    BatchAnalysisRequest, BatchAnalysisResponse,
    ChangeClassification, SemanticAnalysis, LLMAnalysis
)
from .change_analyzer import ChangeAnalyzer
from .llm_classifier import LLMClassifier

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    Main service for AI-powered document change analysis.
    
    Features:
    - Orchestrates semantic and LLM analysis
    - Confidence-based decision making
    - Performance monitoring and optimization
    - Comprehensive audit logging
    - Batch processing capabilities
    """
    
    def __init__(self,
                 semantic_model: str = "all-MiniLM-L6-v2",
                 llm_model: str = "gpt-3.5-turbo",
                 default_confidence_threshold: int = 70,
                 max_processing_time_seconds: int = 180,
                 enable_caching: bool = True):
        """
        Initialize the AnalysisService.
        
        Args:
            semantic_model: Sentence transformer model for semantic analysis
            llm_model: LLM model for classification
            default_confidence_threshold: Default threshold for analysis confidence
            max_processing_time_seconds: Maximum time allowed for analysis
            enable_caching: Whether to enable result caching
        """
        self.default_confidence_threshold = default_confidence_threshold
        self.max_processing_time_seconds = max_processing_time_seconds
        self.enable_caching = enable_caching
        
        # Initialize analyzers
        try:
            self.change_analyzer = ChangeAnalyzer(model_name=semantic_model)
            self.llm_classifier = LLMClassifier(model_name=llm_model)
            logger.info("AnalysisService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AnalysisService: {e}")
            raise
        
        # Performance tracking
        self.analysis_stats = {
            "total_analyses": 0,
            "successful_analyses": 0,
            "failed_analyses": 0,
            "avg_processing_time_ms": 0,
            "cache_hits": 0,
            "llm_fallback_count": 0
        }
        
        # Simple in-memory cache (in production, use Redis or similar)
        self.analysis_cache = {} if enable_caching else None
    
    def _generate_analysis_id(self) -> str:
        """Generate unique analysis ID."""
        return f"analysis_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    
    def _calculate_cache_key(self, old_content: str, new_content: str) -> str:
        """Calculate cache key for content comparison."""
        import hashlib
        content_hash = hashlib.sha256(f"{old_content}|||{new_content}".encode()).hexdigest()
        return f"analysis_{content_hash[:16]}"
    
    def _should_use_llm(self, 
                       semantic_analysis: SemanticAnalysis,
                       confidence_threshold: int,
                       request: AnalysisRequest) -> bool:
        """
        Determine if LLM analysis should be used based on confidence and request parameters.
        
        Args:
            semantic_analysis: Results from semantic analysis
            confidence_threshold: Confidence threshold
            request: Original analysis request
            
        Returns:
            True if LLM should be used, False otherwise
        """
        # Always use LLM if explicitly requested
        if request.use_llm_fallback:
            return True
        
        # Use LLM if semantic analysis indicates significant changes
        if len(semantic_analysis.significant_differences) > 3:
            return True
        
        # Use LLM if similarity is in the uncertain range (40-80%)
        if 40 <= semantic_analysis.similarity_score <= 80:
            return True
        
        # Use LLM if change indicators suggest complex changes
        if len(semantic_analysis.change_indicators) > 2:
            return True
        
        return False
    
    def _combine_analysis_results(self,
                                 semantic_analysis: SemanticAnalysis,
                                 classification: ChangeClassification,
                                 llm_analysis: Optional[LLMAnalysis] = None) -> Tuple[bool, Dict[str, int]]:
        """
        Combine results from different analysis components.
        
        Args:
            semantic_analysis: Semantic analysis results
            classification: Change classification
            llm_analysis: Optional LLM analysis results
            
        Returns:
            Tuple of (has_meaningful_changes, confidence_breakdown)
        """
        # Determine if there are meaningful changes
        has_meaningful_changes = (
            semantic_analysis.similarity_score < 85 or  # Less than 85% similar
            len(semantic_analysis.significant_differences) > 0 or
            not classification.is_cosmetic
        )
        
        # Calculate confidence breakdown
        confidence_breakdown = {
            "semantic_similarity": semantic_analysis.similarity_score,
            "classification_confidence": classification.confidence
        }
        
        if llm_analysis:
            # Weight LLM analysis higher if available
            confidence_breakdown["llm_analysis"] = 90  # LLM typically has high confidence
            confidence_breakdown["overall"] = int(
                (semantic_analysis.similarity_score * 0.3 +
                 classification.confidence * 0.3 +
                 90 * 0.4)
            )
        else:
            confidence_breakdown["overall"] = int(
                (semantic_analysis.similarity_score * 0.5 +
                 classification.confidence * 0.5)
            )
        
        return has_meaningful_changes, confidence_breakdown
    
    async def analyze_document_changes(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Perform comprehensive document change analysis.
        
        Args:
            request: Analysis request with document content and parameters
            
        Returns:
            Complete analysis response with results and metadata
        """
        analysis_id = self._generate_analysis_id()
        start_time = time.time()
        
        logger.info(f"Starting analysis {analysis_id} for {request.form_name or 'unknown form'}")
        
        try:
            # Check cache if enabled
            if self.analysis_cache:
                cache_key = self._calculate_cache_key(request.old_content, request.new_content)
                if cache_key in self.analysis_cache:
                    logger.info(f"Cache hit for analysis {analysis_id}")
                    self.analysis_stats["cache_hits"] += 1
                    cached_result = self.analysis_cache[cache_key]
                    cached_result.analysis_id = analysis_id  # Update ID for uniqueness
                    return cached_result
            
            # Step 1: Semantic Analysis
            logger.debug(f"Performing semantic analysis for {analysis_id}")
            semantic_analysis = self.change_analyzer.analyze(
                request.old_content, 
                request.new_content
            )
            
            # Step 2: Determine if we need LLM analysis
            use_llm = self._should_use_llm(
                semantic_analysis, 
                request.confidence_threshold, 
                request
            )
            
            llm_analysis = None
            classification = None
            
            # Step 3: Classification (with or without LLM)
            logger.debug(f"Performing classification for {analysis_id} (LLM: {use_llm})")
            classification, llm_analysis = await self.llm_classifier.classify(
                request.old_content,
                request.new_content,
                request.form_name,
                request.agency_name,
                use_llm=use_llm
            )
            
            # Step 4: Check for cosmetic changes using semantic analyzer
            if classification.is_cosmetic:
                is_cosmetic_semantic = self.change_analyzer.is_cosmetic_change(
                    request.old_content, request.new_content
                )
                # Override classification if semantic analysis disagrees
                if not is_cosmetic_semantic:
                    classification.is_cosmetic = False
                    logger.info(f"Overrode cosmetic classification based on semantic analysis for {analysis_id}")
            
            # Step 5: Combine results
            has_meaningful_changes, confidence_breakdown = self._combine_analysis_results(
                semantic_analysis, classification, llm_analysis
            )
            
            # Step 6: Create processing summary
            processing_time_ms = int((time.time() - start_time) * 1000)
            processing_summary = {
                "processing_time_ms": processing_time_ms,
                "semantic_model": self.change_analyzer.model_name,
                "classification_method": "llm" if use_llm and llm_analysis else "rule_based",
                "cache_used": False,
                "analysis_version": "1.0"
            }
            
            if llm_analysis and llm_analysis.tokens_used:
                processing_summary["llm_tokens_used"] = llm_analysis.tokens_used
            
            # Step 7: Create response
            response = AnalysisResponse(
                analysis_id=analysis_id,
                timestamp=datetime.now(timezone.utc),
                has_meaningful_changes=has_meaningful_changes,
                classification=classification,
                semantic_analysis=semantic_analysis,
                llm_analysis=llm_analysis,
                processing_summary=processing_summary,
                confidence_breakdown=confidence_breakdown
            )
            
            # Cache result if enabled
            if self.analysis_cache and cache_key:
                self.analysis_cache[cache_key] = response
                logger.debug(f"Cached analysis result for {analysis_id}")
            
            # Update statistics
            self.analysis_stats["total_analyses"] += 1
            self.analysis_stats["successful_analyses"] += 1
            self._update_avg_processing_time(processing_time_ms)
            
            if not use_llm or not llm_analysis or llm_analysis.model_used == "rule_based_fallback":
                self.analysis_stats["llm_fallback_count"] += 1
            
            logger.info(f"Analysis {analysis_id} completed successfully in {processing_time_ms}ms")
            return response
            
        except asyncio.TimeoutError:
            error_msg = f"Analysis {analysis_id} timed out after {self.max_processing_time_seconds} seconds"
            logger.error(error_msg)
            self.analysis_stats["failed_analyses"] += 1
            raise AnalysisTimeoutError(error_msg)
            
        except Exception as e:
            error_msg = f"Analysis {analysis_id} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.analysis_stats["failed_analyses"] += 1
            raise AnalysisProcessingError(error_msg) from e
    
    def _update_avg_processing_time(self, new_time_ms: int) -> None:
        """Update running average of processing times."""
        current_avg = self.analysis_stats["avg_processing_time_ms"]
        total_analyses = self.analysis_stats["successful_analyses"]
        
        if total_analyses == 1:
            self.analysis_stats["avg_processing_time_ms"] = new_time_ms
        else:
            # Calculate running average
            new_avg = ((current_avg * (total_analyses - 1)) + new_time_ms) / total_analyses
            self.analysis_stats["avg_processing_time_ms"] = int(new_avg)
    
    async def analyze_batch(self, batch_request: BatchAnalysisRequest) -> BatchAnalysisResponse:
        """
        Process multiple document analyses in parallel.
        
        Args:
            batch_request: Batch of analysis requests
            
        Returns:
            Batch analysis response with all results
        """
        batch_id = batch_request.batch_id or f"batch_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        logger.info(f"Starting batch analysis {batch_id} with {len(batch_request.analyses)} requests")
        
        # Process analyses in parallel
        tasks = []
        for i, request in enumerate(batch_request.analyses):
            task = asyncio.create_task(
                self.analyze_document_changes(request),
                name=f"analysis_{batch_id}_{i}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Separate successful results from errors
        successful_results = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error = AnalysisError(
                    error_code="ANALYSIS_FAILED",
                    error_message=str(result),
                    details={"request_index": i},
                    analysis_id=f"failed_{batch_id}_{i}"
                )
                errors.append(error)
            else:
                successful_results.append(result)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        batch_response = BatchAnalysisResponse(
            batch_id=batch_id,
            timestamp=datetime.now(timezone.utc),
            total_analyses=len(batch_request.analyses),
            successful_analyses=len(successful_results),
            failed_analyses=len(errors),
            results=successful_results,
            errors=errors,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"Batch analysis {batch_id} completed: {len(successful_results)} successful, {len(errors)} failed")
        return batch_response
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service performance statistics."""
        return {
            **self.analysis_stats,
            "cache_size": len(self.analysis_cache) if self.analysis_cache else 0,
            "service_uptime_seconds": int(time.time() - getattr(self, '_start_time', time.time()))
        }
    
    def clear_cache(self) -> None:
        """Clear the analysis cache."""
        if self.analysis_cache:
            cache_size = len(self.analysis_cache)
            self.analysis_cache.clear()
            logger.info(f"Cleared analysis cache ({cache_size} entries)")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components."""
        health_status = {
            "service": "healthy",
            "semantic_analyzer": "unknown",
            "llm_classifier": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            # Test semantic analyzer
            test_similarity = self.change_analyzer.calculate_semantic_similarity(
                "test content", "test content"
            )
            health_status["semantic_analyzer"] = "healthy" if test_similarity > 0.9 else "degraded"
        except Exception as e:
            health_status["semantic_analyzer"] = f"unhealthy: {str(e)}"
        
        try:
            # Test LLM classifier (basic validation)
            if self.llm_classifier.client:
                health_status["llm_classifier"] = "healthy"
            else:
                health_status["llm_classifier"] = "degraded (fallback mode)"
        except Exception as e:
            health_status["llm_classifier"] = f"unhealthy: {str(e)}"
        
        # Overall service health
        if any("unhealthy" in str(status) for status in health_status.values()):
            health_status["service"] = "unhealthy"
        elif any("degraded" in str(status) for status in health_status.values()):
            health_status["service"] = "degraded"
        
        return health_status


class AnalysisTimeoutError(Exception):
    """Raised when analysis takes too long to complete."""
    pass


class AnalysisProcessingError(Exception):
    """Raised when analysis processing fails."""
    pass