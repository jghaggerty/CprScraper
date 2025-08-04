"""
AI-Enhanced Monitoring Service

This module extends the existing web scraper functionality with AI-powered
change detection, semantic analysis, and intelligent classification of
document modifications for regulatory compliance monitoring.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict

from ..database.connection import get_db
from ..database.models import Agency, Form, FormChange, MonitoringRun
from ..analysis import AnalysisService, AnalysisRequest
from .web_scraper import WebScraper

logger = logging.getLogger(__name__)


class AIEnhancedMonitor:
    """
    Enhanced monitoring service with AI-powered change detection.
    
    Features:
    - Semantic similarity analysis for meaningful change detection
    - Automated change classification and severity scoring  
    - Integration with existing monitoring workflow
    - Comprehensive audit trails with AI analysis metadata
    - Performance-optimized batch processing
    """
    
    def __init__(self, 
                 confidence_threshold: int = 70,
                 enable_llm_analysis: bool = True,
                 batch_size: int = 5):
        """
        Initialize the AI-enhanced monitoring service.
        
        Args:
            confidence_threshold: Minimum confidence threshold for AI analysis
            enable_llm_analysis: Whether to use LLM for detailed analysis
            batch_size: Number of forms to process in parallel
        """
        self.confidence_threshold = confidence_threshold
        self.enable_llm_analysis = enable_llm_analysis
        self.batch_size = batch_size
        
        # Initialize AI analysis service
        try:
            self.analysis_service = AnalysisService(
                default_confidence_threshold=confidence_threshold
            )
            logger.info("AI analysis service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI analysis service: {e}")
            self.analysis_service = None
        
        # Content cache for storing previous versions
        self.content_cache = {}
    
    async def monitor_agency_with_ai(self, agency_id: int) -> Dict[str, Any]:
        """
        Monitor an agency with AI-enhanced change detection.
        
        Args:
            agency_id: ID of the agency to monitor
            
        Returns:
            Dictionary containing monitoring results and AI analysis summary
        """
        start_time = datetime.utcnow()
        results = {
            "agency_id": agency_id,
            "agency_name": None,
            "started_at": start_time,
            "completed_at": None,
            "total_forms": 0,
            "forms_analyzed": 0,
            "changes_detected": 0,
            "ai_analyses_performed": 0,
            "forms_with_changes": [],
            "analysis_summary": {
                "high_priority_changes": 0,
                "medium_priority_changes": 0,
                "low_priority_changes": 0,
                "cosmetic_changes": 0,
                "avg_confidence_score": 0
            },
            "errors": []
        }
        
        with get_db() as db:
            agency = db.query(Agency).filter(Agency.id == agency_id).first()
            if not agency:
                error_msg = f"Agency {agency_id} not found"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                return results
            
            results["agency_name"] = agency.name
            results["total_forms"] = len([f for f in agency.forms if f.is_active])
            
            logger.info(f"Starting AI-enhanced monitoring for {agency.name} ({results['total_forms']} forms)")
            
            # Create monitoring run record
            monitoring_run = MonitoringRun(
                agency_id=agency_id,
                status="running"
            )
            db.add(monitoring_run)
            db.commit()
            
            try:
                async with WebScraper() as scraper:
                    # Process forms in batches for optimal performance
                    active_forms = [f for f in agency.forms if f.is_active]
                    
                    for i in range(0, len(active_forms), self.batch_size):
                        batch = active_forms[i:i + self.batch_size]
                        batch_results = await self._process_form_batch(batch, scraper, db)
                        
                        # Aggregate batch results
                        for form_result in batch_results:
                            results["forms_analyzed"] += 1
                            
                            if form_result.get("has_changes"):
                                results["changes_detected"] += 1
                                results["forms_with_changes"].append(form_result)
                                
                                # Update analysis summary
                                if form_result.get("ai_analysis"):
                                    results["ai_analyses_performed"] += 1
                                    self._update_analysis_summary(
                                        results["analysis_summary"], 
                                        form_result["ai_analysis"]
                                    )
                            
                            if form_result.get("errors"):
                                results["errors"].extend(form_result["errors"])
                
                # Update monitoring run
                monitoring_run.completed_at = datetime.utcnow()
                monitoring_run.status = "completed"
                monitoring_run.changes_detected = results["changes_detected"]
                db.commit()
                
                # Calculate final statistics
                if results["ai_analyses_performed"] > 0:
                    results["analysis_summary"]["avg_confidence_score"] = int(
                        results["analysis_summary"]["avg_confidence_score"] / results["ai_analyses_performed"]
                    )
                
                results["completed_at"] = monitoring_run.completed_at
                
                logger.info(f"Completed AI monitoring for {agency.name}: "
                          f"{results['changes_detected']} changes detected, "
                          f"{results['ai_analyses_performed']} AI analyses performed")
                
            except Exception as e:
                error_msg = f"Error during AI monitoring of {agency.name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                results["errors"].append(error_msg)
                
                monitoring_run.status = "failed"
                monitoring_run.error_message = error_msg
                monitoring_run.completed_at = datetime.utcnow()
                db.commit()
        
        return results
    
    async def _process_form_batch(self, forms: List[Form], scraper: WebScraper, db) -> List[Dict[str, Any]]:
        """
        Process a batch of forms for change detection and AI analysis.
        
        Args:
            forms: List of forms to process
            scraper: WebScraper instance
            db: Database session
            
        Returns:
            List of form processing results
        """
        batch_results = []
        
        # Create tasks for parallel processing
        tasks = []
        for form in forms:
            task = asyncio.create_task(
                self._analyze_form_changes(form, scraper, db),
                name=f"analyze_form_{form.id}"
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    "form_id": forms[i].id,
                    "form_name": forms[i].name,
                    "has_changes": False,
                    "errors": [f"Processing error: {str(result)}"]
                }
                batch_results.append(error_result)
                logger.error(f"Error processing form {forms[i].name}: {result}")
            else:
                batch_results.append(result)
        
        return batch_results
    
    async def _analyze_form_changes(self, form: Form, scraper: WebScraper, db) -> Dict[str, Any]:
        """
        Analyze changes for a specific form using AI.
        
        Args:
            form: Form object to analyze
            scraper: WebScraper instance
            db: Database session
            
        Returns:
            Dictionary containing analysis results
        """
        result = {
            "form_id": form.id,
            "form_name": form.name,
            "agency_name": form.agency.name,
            "has_changes": False,
            "change_records": [],
            "ai_analysis": None,
            "errors": []
        }
        
        try:
            # Fetch current content
            content, status_code, metadata = await scraper.fetch_page_content(
                form.form_url or form.agency.base_url
            )
            
            if status_code != 200:
                result["errors"].append(f"Failed to fetch content: HTTP {status_code}")
                return result
            
            # Get previous content from last successful monitoring run
            previous_content = await self._get_previous_content(form.id, db)
            
            if previous_content:
                # Perform AI analysis to detect meaningful changes
                ai_result = await self._perform_ai_analysis(
                    previous_content, content, form
                )
                
                if ai_result and ai_result.has_meaningful_changes:
                    result["has_changes"] = True
                    result["ai_analysis"] = self._serialize_ai_analysis(ai_result)
                    
                    # Create detailed change record with AI metadata
                    change_record = await self._create_ai_enhanced_change_record(
                        form, previous_content, content, ai_result, db
                    )
                    result["change_records"].append(change_record)
                    
                    logger.info(f"AI detected meaningful changes in {form.name}: "
                              f"{ai_result.classification.category} "
                              f"(confidence: {ai_result.classification.confidence}%)")
                else:
                    logger.debug(f"No meaningful changes detected in {form.name}")
            else:
                logger.debug(f"No previous content found for {form.name} - storing baseline")
            
            # Update form's last checked time and store current content
            form.last_checked = datetime.utcnow()
            await self._store_current_content(form.id, content)
            
            # Create monitoring run record for this form
            form_run = MonitoringRun(
                agency_id=form.agency_id,
                form_id=form.id,
                status="completed",
                completed_at=datetime.utcnow(),
                content_hash=scraper.calculate_content_hash(content),
                http_status_code=status_code
            )
            db.add(form_run)
            db.commit()
            
        except Exception as e:
            error_msg = f"Error analyzing form {form.name}: {str(e)}"
            result["errors"].append(error_msg)
            logger.error(error_msg, exc_info=True)
        
        return result
    
    async def _get_previous_content(self, form_id: int, db) -> Optional[str]:
        """
        Retrieve previous content for a form from cache or database.
        
        Args:
            form_id: ID of the form
            db: Database session
            
        Returns:
            Previous content string or None if not available
        """
        # Try cache first
        cache_key = f"form_content_{form_id}"
        if cache_key in self.content_cache:
            return self.content_cache[cache_key]
        
        # TODO: In production, retrieve from proper content storage
        # For now, we'll return None to indicate no previous content
        return None
    
    async def _store_current_content(self, form_id: int, content: str) -> None:
        """
        Store current content for future comparison.
        
        Args:
            form_id: ID of the form
            content: Content to store
        """
        # Store in cache
        cache_key = f"form_content_{form_id}"
        self.content_cache[cache_key] = content
        
        # TODO: In production, store in persistent storage (S3, database BLOB, etc.)
    
    async def _perform_ai_analysis(self, 
                                  old_content: str, 
                                  new_content: str, 
                                  form: Form) -> Optional[Any]:
        """
        Perform AI analysis on content changes.
        
        Args:
            old_content: Previous content
            new_content: Current content
            form: Form object
            
        Returns:
            AI analysis result or None if analysis fails
        """
        if not self.analysis_service:
            logger.warning("AI analysis service not available")
            return None
        
        try:
            request = AnalysisRequest(
                old_content=old_content,
                new_content=new_content,
                form_name=form.name,
                agency_name=form.agency.name,
                confidence_threshold=self.confidence_threshold,
                use_llm_fallback=self.enable_llm_analysis
            )
            
            result = await self.analysis_service.analyze_document_changes(request)
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed for form {form.name}: {e}")
            return None
    
    def _serialize_ai_analysis(self, ai_result) -> Dict[str, Any]:
        """Convert AI analysis result to serializable dictionary."""
        return {
            "analysis_id": ai_result.analysis_id,
            "has_meaningful_changes": ai_result.has_meaningful_changes,
            "classification": {
                "category": ai_result.classification.category,
                "severity": ai_result.classification.severity,
                "priority_score": ai_result.classification.priority_score,
                "confidence": ai_result.classification.confidence,
                "is_cosmetic": ai_result.classification.is_cosmetic
            },
            "semantic_analysis": {
                "similarity_score": ai_result.semantic_analysis.similarity_score,
                "significant_differences": ai_result.semantic_analysis.significant_differences[:3],  # Truncate for storage
                "change_indicators": ai_result.semantic_analysis.change_indicators[:3]
            },
            "confidence_breakdown": ai_result.confidence_breakdown,
            "processing_time_ms": ai_result.processing_summary.get("processing_time_ms", 0)
        }
    
    async def _create_ai_enhanced_change_record(self, 
                                               form: Form,
                                               old_content: str,
                                               new_content: str,
                                               ai_result,
                                               db) -> Dict[str, Any]:
        """
        Create a comprehensive change record with AI analysis metadata.
        
        Args:
            form: Form object
            old_content: Previous content
            new_content: Current content
            ai_result: AI analysis result
            db: Database session
            
        Returns:
            Dictionary describing the change record created
        """
        # Create FormChange record with AI metadata
        change = FormChange(
            form_id=form.id,
            change_type="content",
            change_description=f"AI-detected {ai_result.classification.category}: "
                             f"{', '.join(ai_result.semantic_analysis.significant_differences[:2])}",
            old_value=old_content[:1000],  # Truncate for storage
            new_value=new_content[:1000],  # Truncate for storage
            severity=ai_result.classification.severity,
            
            # AI Analysis Fields
            ai_confidence_score=ai_result.classification.confidence,
            ai_change_category=ai_result.classification.category,
            ai_severity_score=ai_result.classification.priority_score,
            ai_reasoning=ai_result.llm_analysis.reasoning if ai_result.llm_analysis else "Semantic analysis only",
            ai_semantic_similarity=ai_result.semantic_analysis.similarity_score,
            ai_analysis_metadata={
                "analysis_id": ai_result.analysis_id,
                "model_used": ai_result.processing_summary.get("semantic_model", "unknown"),
                "processing_time_ms": ai_result.processing_summary.get("processing_time_ms", 0),
                "confidence_breakdown": ai_result.confidence_breakdown
            },
            ai_analysis_timestamp=datetime.utcnow(),
            is_cosmetic_change=ai_result.classification.is_cosmetic
        )
        
        db.add(change)
        db.commit()
        
        return {
            "change_id": change.id,
            "category": ai_result.classification.category,
            "severity": ai_result.classification.severity,
            "confidence": ai_result.classification.confidence,
            "description": change.change_description
        }
    
    def _update_analysis_summary(self, summary: Dict[str, Any], ai_analysis: Dict[str, Any]) -> None:
        """Update the analysis summary with results from a single analysis."""
        priority_score = ai_analysis["classification"]["priority_score"]
        
        if priority_score >= 80:
            summary["high_priority_changes"] += 1
        elif priority_score >= 50:
            summary["medium_priority_changes"] += 1
        else:
            summary["low_priority_changes"] += 1
        
        if ai_analysis["classification"]["is_cosmetic"]:
            summary["cosmetic_changes"] += 1
        
        # Running average for confidence score
        summary["avg_confidence_score"] += ai_analysis["classification"]["confidence"]
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get health status of the AI monitoring service."""
        health = {
            "service": "ai_enhanced_monitor",
            "status": "healthy",
            "ai_analysis_available": self.analysis_service is not None,
            "cache_size": len(self.content_cache),
            "configuration": {
                "confidence_threshold": self.confidence_threshold,
                "llm_analysis_enabled": self.enable_llm_analysis,
                "batch_size": self.batch_size
            }
        }
        
        if self.analysis_service:
            try:
                ai_health = await self.analysis_service.health_check()
                health["ai_service_health"] = ai_health
                
                if ai_health.get("service") != "healthy":
                    health["status"] = "degraded"
            except Exception as e:
                health["status"] = "degraded"
                health["ai_service_error"] = str(e)
        else:
            health["status"] = "degraded"
            health["error"] = "AI analysis service not available"
        
        return health


# Convenience function for backward compatibility
async def monitor_agency_with_ai(agency_id: int, **kwargs) -> Dict[str, Any]:
    """
    Convenience function to monitor an agency with AI enhancement.
    
    Args:
        agency_id: ID of the agency to monitor
        **kwargs: Additional configuration options
        
    Returns:
        Monitoring results with AI analysis
    """
    monitor = AIEnhancedMonitor(**kwargs)
    return await monitor.monitor_agency_with_ai(agency_id)