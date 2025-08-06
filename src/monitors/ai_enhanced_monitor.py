"""
AI-Enhanced Monitoring Service

This module extends the existing web scraper functionality with AI-powered
change detection, semantic analysis, and intelligent classification of
document modifications for regulatory compliance monitoring.

Enhanced with comprehensive support for all 50 states plus federal agencies.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import asdict

from ..database.connection import get_db
from ..database.models import Agency, Form, FormChange, MonitoringRun
from ..analysis import AnalysisService, AnalysisRequest
from ..analysis.enhanced_analysis_service import EnhancedAnalysisService
from ..analysis.change_classifier import get_change_classifier
from ..utils.enhanced_config_manager import EnhancedConfigManager, get_enhanced_config_manager
from .web_scraper import WebScraper
from .error_handler import get_error_handler, create_retry_config
from .monitoring_statistics import get_monitoring_statistics, record_monitoring_event

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
                 batch_size: int = 5,
                 config_path: Optional[str] = None):
        """
        Initialize the AI-enhanced monitoring service.
        
        Args:
            confidence_threshold: Minimum confidence threshold for AI analysis
            enable_llm_analysis: Whether to use LLM for detailed analysis
            batch_size: Number of forms to process in parallel
            config_path: Path to configuration file for comprehensive coverage
        """
        self.confidence_threshold = confidence_threshold
        self.enable_llm_analysis = enable_llm_analysis
        self.batch_size = batch_size
        
        # Initialize enhanced configuration manager
        try:
            self.config_manager = get_enhanced_config_manager(config_path)
            logger.info("Enhanced configuration manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced configuration manager: {e}")
            self.config_manager = None
        
        # Initialize enhanced AI analysis service
        try:
            self.analysis_service = EnhancedAnalysisService(
                default_confidence_threshold=confidence_threshold,
                false_positive_threshold=0.15,
                semantic_similarity_threshold=0.85
            )
            logger.info("Enhanced AI analysis service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced AI analysis service: {e}")
            # Fallback to standard analysis service
            try:
                self.analysis_service = AnalysisService(
                    default_confidence_threshold=confidence_threshold
                )
                logger.info("Standard AI analysis service initialized as fallback")
            except Exception as e2:
                logger.error(f"Failed to initialize standard AI analysis service: {e2}")
                self.analysis_service = None
        
        # Initialize change classifier
        try:
            self.change_classifier = get_change_classifier()
            logger.info("Change classifier initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize change classifier: {e}")
            self.change_classifier = None
        
        # Content cache for storing previous versions
        self.content_cache = {}
        
        # Initialize enhanced error handling
        retry_config = create_retry_config(
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            circuit_breaker_threshold=5,
            circuit_breaker_timeout=300.0
        )
        self.error_handler = get_error_handler(retry_config)
        
        # Initialize monitoring statistics
        self.monitoring_stats = get_monitoring_statistics()
    
    async def monitor_agency_with_ai(self, agency_id: int) -> Dict[str, Any]:
        """
        Monitor an agency with AI-enhanced change detection.
        
        Args:
            agency_id: ID of the agency to monitor
            
        Returns:
            Dictionary containing monitoring results and AI analysis summary
        """
        start_time = datetime.utcnow()
        
        # Start monitoring session for statistics tracking
        session_id = await self.monitoring_stats.start_monitoring_session()
        
        results = {
            "agency_id": agency_id,
            "agency_name": None,
            "session_id": session_id,
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
                    
                    # Record performance metric for agency monitoring
                    agency_start_time = datetime.utcnow()
                    
                    for i in range(0, len(active_forms), self.batch_size):
                        batch = active_forms[i:i + self.batch_size]
                        batch_start_time = datetime.utcnow()
                        
                        batch_results = await self._process_form_batch(batch, scraper, db)
                        
                        # Record batch performance metric
                        batch_processing_time = int((datetime.utcnow() - batch_start_time).total_seconds() * 1000)
                        await record_monitoring_event("performance", 
                                                    operation_type="form_batch_processing",
                                                    processing_time_ms=batch_processing_time,
                                                    additional_data={
                                                        "batch_size": len(batch),
                                                        "agency_id": agency_id,
                                                        "agency_name": agency.name
                                                    })
                        
                        # Aggregate batch results
                        for form_result in batch_results:
                            results["forms_analyzed"] += 1
                            
                            if form_result.get("has_changes"):
                                results["changes_detected"] += 1
                                results["forms_with_changes"].append(form_result)
                                
                                # Record change metric
                                change_data = form_result.get("ai_analysis", {})
                                await record_monitoring_event("change",
                                                            change_severity=change_data.get("severity", "medium"),
                                                            change_type=change_data.get("change_type", "unknown"),
                                                            agency_name=agency.name,
                                                            confidence_score=change_data.get("confidence_score", 0.0),
                                                            has_ai_analysis=bool(change_data))
                                
                                # Update analysis summary
                                if form_result.get("ai_analysis"):
                                    results["ai_analyses_performed"] += 1
                                    self._update_analysis_summary(
                                        results["analysis_summary"], 
                                        form_result["ai_analysis"]
                                    )
                            
                            if form_result.get("errors"):
                                results["errors"].extend(form_result["errors"])
                                
                                # Record error metrics
                                for error in form_result["errors"]:
                                    await record_monitoring_event("error",
                                                                error_type=error.get("type", "unknown"),
                                                                error_severity=error.get("severity", "low"))
                    
                    # Record overall agency monitoring performance
                    agency_processing_time = int((datetime.utcnow() - agency_start_time).total_seconds() * 1000)
                    await record_monitoring_event("performance",
                                                operation_type="agency_monitoring",
                                                processing_time_ms=agency_processing_time,
                                                additional_data={
                                                    "agency_id": agency_id,
                                                    "agency_name": agency.name,
                                                    "total_forms": len(active_forms),
                                                    "forms_analyzed": results["forms_analyzed"],
                                                    "changes_detected": results["changes_detected"]
                                                })
                
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
            content, status_code, _ = await scraper.fetch_page_content(
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
        Perform enhanced AI analysis on content changes with false positive reduction.
        
        Args:
            old_content: Previous content
            new_content: Current content
            form: Form object
            
        Returns:
            Enhanced AI analysis result or None if analysis fails
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
            
            # Perform analysis with timing
            start_time = datetime.utcnow()
            
            # Use enhanced analysis if available, fallback to standard
            if hasattr(self.analysis_service, 'analyze_document_changes_enhanced'):
                result = await self.analysis_service.analyze_document_changes_enhanced(request)
                analysis_type = "enhanced_analysis"
                logger.info(f"Enhanced AI analysis completed for form {form.name}")
            else:
                result = await self.analysis_service.analyze_document_changes(request)
                analysis_type = "standard_analysis"
                logger.info(f"Standard AI analysis completed for form {form.name}")
            
            processing_time = datetime.utcnow() - start_time
            processing_time_ms = int(processing_time.total_seconds() * 1000)
            
            # Record AI analysis metric
            confidence_score = result.confidence_score if result else 0.0
            enhanced_features = []
            model_version = ""
            
            if result and hasattr(result, 'processing_summary'):
                enhanced_features = result.processing_summary.get('enhanced_features', [])
                model_version = result.processing_summary.get('model_version', '')
            
            await record_monitoring_event("ai_analysis",
                                        analysis_type=analysis_type,
                                        processing_time_ms=processing_time_ms,
                                        confidence_score=confidence_score,
                                        success=True,
                                        enhanced_features=enhanced_features,
                                        model_version=model_version)
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed for form {form.name}: {e}")
            
            # Record failed AI analysis metric
            await record_monitoring_event("ai_analysis",
                                        analysis_type="failed_analysis",
                                        processing_time_ms=0,
                                        confidence_score=0.0,
                                        success=False,
                                        model_version="")
            
            return None
    
    def _serialize_ai_analysis(self, ai_result) -> Dict[str, Any]:
        """Convert enhanced AI analysis result to serializable dictionary."""
        base_serialization = {
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
        
        # Add enhanced features if available
        if hasattr(ai_result, 'processing_summary') and ai_result.processing_summary:
            enhanced_features = {
                "false_positive_detected": ai_result.processing_summary.get("false_positive_detected", False),
                "false_positive_confidence": ai_result.processing_summary.get("false_positive_confidence", 0),
                "false_positive_patterns": ai_result.processing_summary.get("false_positive_patterns", []),
                "semantic_changes": ai_result.processing_summary.get("semantic_changes", {}),
                "content_relevance": ai_result.processing_summary.get("content_relevance", {}),
                "compliance_validation": ai_result.processing_summary.get("compliance_validation", {}),
                "structure_validation": ai_result.processing_summary.get("structure_validation", {}),
                "analysis_version": ai_result.processing_summary.get("analysis_version", "1.0")
            }
            base_serialization["enhanced_features"] = enhanced_features
        
        return base_serialization
    
    async def _create_ai_enhanced_change_record(self, 
                                               form: Form,
                                               old_content: str,
                                               new_content: str,
                                               ai_result,
                                               db) -> Dict[str, Any]:
        """
        Create a comprehensive change record with AI analysis metadata and enhanced classification.
        
        Args:
            form: Form object
            old_content: Previous content
            new_content: Current content
            ai_result: AI analysis result
            db: Database session
            
        Returns:
            Dictionary describing the change record created
        """
        # Generate change description
        change_description = f"AI-detected {ai_result.classification.category}: " \
                           f"{', '.join(ai_result.semantic_analysis.significant_differences[:2])}"
        
        # Perform enhanced change classification
        classification_result = None
        if self.change_classifier:
            try:
                # Rule-based classification
                classification_result = self.change_classifier.classify_change(
                    old_content=old_content,
                    new_content=new_content,
                    change_description=change_description,
                    form_name=form.name,
                    agency_name=form.agency.name
                )
                
                # Enhance with AI analysis if available
                ai_classification_data = {
                    "severity": ai_result.classification.severity,
                    "severity_confidence": ai_result.classification.confidence,
                    "change_type": ai_result.classification.category,
                    "type_confidence": ai_result.classification.confidence,
                    "compliance_impact_score": ai_result.classification.priority_score,
                    "is_cosmetic": ai_result.classification.is_cosmetic,
                    "reasoning": ai_result.llm_analysis.reasoning if ai_result.llm_analysis else "Semantic analysis only"
                }
                
                classification_result = self.change_classifier.enhance_with_ai_classification(
                    classification_result, ai_classification_data
                )
                
                logger.info(f"Enhanced classification for form {form.name}: "
                           f"severity={classification_result['severity']}, "
                           f"type={classification_result['change_type']}, "
                           f"confidence={classification_result['severity_confidence']}")
                
            except Exception as e:
                logger.error(f"Error in change classification for form {form.name}: {e}")
                classification_result = None
        
        # Use classification result or fall back to AI analysis
        if classification_result:
            severity = classification_result["severity"]
            change_type = classification_result["change_type"]
            ai_confidence = classification_result["severity_confidence"]
            ai_change_category = classification_result["change_type"]
            ai_severity_score = classification_result["compliance_impact_score"]
            ai_reasoning = classification_result["reasoning"]
            is_cosmetic = classification_result["is_cosmetic"]
        else:
            # Fallback to original AI analysis
            severity = ai_result.classification.severity
            change_type = "content"
            ai_confidence = ai_result.classification.confidence
            ai_change_category = ai_result.classification.category
            ai_severity_score = ai_result.classification.priority_score
            ai_reasoning = ai_result.llm_analysis.reasoning if ai_result.llm_analysis else "Semantic analysis only"
            is_cosmetic = ai_result.classification.is_cosmetic
        
        # Create FormChange record with enhanced classification
        change = FormChange(
            form_id=form.id,
            change_type=change_type,
            change_description=change_description,
            old_value=old_content[:1000],  # Truncate for storage
            new_value=new_content[:1000],  # Truncate for storage
            severity=severity,
            
            # AI Analysis Fields
            ai_confidence_score=ai_confidence,
            ai_change_category=ai_change_category,
            ai_severity_score=ai_severity_score,
            ai_reasoning=ai_reasoning,
            ai_semantic_similarity=ai_result.semantic_analysis.similarity_score,
            ai_analysis_metadata={
                "analysis_id": ai_result.analysis_id,
                "model_used": ai_result.processing_summary.get("semantic_model", "unknown"),
                "processing_time_ms": ai_result.processing_summary.get("processing_time_ms", 0),
                "confidence_breakdown": ai_result.confidence_breakdown,
                "classification_method": classification_result.get("classification_method", "ai_only") if classification_result else "ai_only",
                "enhanced_classification": classification_result is not None
            },
            ai_analysis_timestamp=datetime.utcnow(),
            is_cosmetic_change=is_cosmetic
        )
        
        db.add(change)
        db.commit()
        
        return {
            "change_id": change.id,
            "category": ai_change_category,
            "severity": severity,
            "confidence": ai_confidence,
            "description": change_description,
            "classification_method": classification_result.get("classification_method", "ai_only") if classification_result else "ai_only"
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
            "enhanced_analysis_available": hasattr(self.analysis_service, 'analyze_document_changes_enhanced') if self.analysis_service else False,
            "change_classifier_available": self.change_classifier is not None,
            "cache_size": len(self.content_cache),
            "configuration": {
                "confidence_threshold": self.confidence_threshold,
                "llm_analysis_enabled": self.enable_llm_analysis,
                "batch_size": self.batch_size
            }
        }
        
        if self.analysis_service:
            try:
                # Try enhanced health check first
                if hasattr(self.analysis_service, 'health_check_enhanced'):
                    ai_health = await self.analysis_service.health_check_enhanced()
                    health["ai_service_health"] = ai_health
                    health["enhanced_features"] = ai_health.get("enhanced_features", {})
                    
                    if ai_health.get("service") != "healthy":
                        health["status"] = "degraded"
                else:
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
        
        # Error handling statistics
        try:
            error_stats = await self.error_handler.get_error_stats()
            health["error_handling"] = {
                "status": "healthy",
                "total_urls_monitored": error_stats.get("total_urls", 0),
                "circuit_breaker_states": len(error_stats.get("circuit_breaker_states", {})),
                "url_stats": error_stats.get("url_stats", {})
            }
        except Exception as e:
            health["error_handling"] = {"status": "error", "error": str(e)}
        
        # Monitoring statistics summary
        try:
            stats_summary = await self.monitoring_stats.get_comprehensive_statistics()
            health["monitoring_statistics"] = {
                "status": "healthy",
                "session_active": stats_summary["monitoring_session"]["start_time"] is not None,
                "total_operations": stats_summary["current_metrics"]["performance"]["total_requests_made"],
                "ai_analyses_performed": stats_summary["current_metrics"]["ai_analysis"]["total_analyses_performed"],
                "changes_detected": stats_summary["current_metrics"]["changes"]["total_changes_detected"],
                "total_errors": stats_summary["current_metrics"]["error_rates"]["total_errors"]
            }
        except Exception as e:
            health["monitoring_statistics"] = {"status": "error", "error": str(e)}
        
        return health
    
    async def get_monitoring_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive monitoring statistics.
        
        Returns:
            Dictionary containing all monitoring statistics and metrics
        """
        try:
            return await self.monitoring_stats.get_comprehensive_statistics()
        except Exception as e:
            logger.error(f"Error getting monitoring statistics: {e}")
            return {"error": str(e)}
    
    async def monitor_all_agencies_comprehensive(self) -> Dict[str, Any]:
        """
        Monitor all agencies comprehensively using the enhanced configuration.
        
        Returns:
            Dictionary containing comprehensive monitoring results
        """
        start_time = datetime.utcnow()
        
        # Start comprehensive monitoring session
        session_id = await self.monitoring_stats.start_monitoring_session()
        
        if not self.config_manager:
            return {
                "error": "Configuration manager not available",
                "session_id": session_id,
                "started_at": start_time.isoformat(),
                "completed_at": datetime.utcnow().isoformat()
            }
        
        results = {
            "session_id": session_id,
            "started_at": start_time,
            "completed_at": None,
            "total_agencies": 0,
            "agencies_processed": 0,
            "agencies_failed": 0,
            "total_forms": 0,
            "forms_processed": 0,
            "forms_failed": 0,
            "changes_detected": 0,
            "ai_analyses_performed": 0,
            "coverage_report": self.config_manager.get_coverage_report(),
            "agency_results": [],
            "performance_stats": {},
            "monitoring_statistics": {},
            "recommendations": []
        }
        
        try:
            # Get optimized monitoring batches
            batches = self.config_manager.get_optimized_monitoring_batches()
            
            # Process batches with enhanced error handling
            total_processing_time = 0
            
            async with WebScraper() as scraper:
                for batch in batches:
                    batch_start = datetime.utcnow()
                    
                    # Process forms in batch
                    batch_results = await self._process_comprehensive_batch(batch, scraper)
                    
                    # Update results
                    results["agency_results"].extend(batch_results.get("agency_results", []))
                    results["forms_processed"] += batch_results.get("forms_processed", 0)
                    results["forms_failed"] += batch_results.get("forms_failed", 0)
                    results["changes_detected"] += batch_results.get("changes_detected", 0)
                    results["ai_analyses_performed"] += batch_results.get("ai_analyses_performed", 0)
                    
                    batch_time = (datetime.utcnow() - batch_start).total_seconds() * 1000
                    total_processing_time += batch_time
                    
                    logger.info(f"Batch {batch['batch_id']} completed in {batch_time:.2f}ms")
            
            # Calculate totals
            results["total_agencies"] = len(self.config_manager.get_state_coverage_status()) + len(self.config_manager.get_federal_coverage_status())
            results["agencies_processed"] = len([r for r in results["agency_results"] if r.get("status") == "success"])
            results["agencies_failed"] = len([r for r in results["agency_results"] if r.get("status") == "failed"])
            results["total_forms"] = sum(len(batch["forms"]) for batch in batches)
            
            # Performance stats
            results["performance_stats"] = {
                "total_processing_time_ms": total_processing_time,
                "avg_batch_time_ms": total_processing_time / len(batches) if batches else 0,
                "forms_per_second": results["forms_processed"] / (total_processing_time / 1000) if total_processing_time > 0 else 0,
                "coverage_percentage": self.config_manager.coverage_metrics.coverage_percentage if self.config_manager.coverage_metrics else 0
            }
            
            # Record comprehensive monitoring performance
            comprehensive_processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            await record_monitoring_event("performance",
                                        operation_type="comprehensive_monitoring",
                                        processing_time_ms=comprehensive_processing_time,
                                        additional_data={
                                            "total_agencies": results["total_agencies"],
                                            "total_forms": results["total_forms"],
                                            "forms_processed": results["forms_processed"],
                                            "changes_detected": results["changes_detected"],
                                            "ai_analyses_performed": results["ai_analyses_performed"]
                                        })
            
            # Update coverage metrics
            coverage_report = self.config_manager.get_coverage_report()
            await self.monitoring_stats.update_coverage_metrics(
                total_agencies=results["total_agencies"],
                active_agencies=results["agencies_processed"],
                total_forms=results["total_forms"],
                active_forms=results["forms_processed"],
                states_covered=coverage_report.get("states_covered", 0),
                federal_agencies_covered=coverage_report.get("federal_agencies_covered", 0),
                frequency_distribution=coverage_report.get("frequency_distribution", {})
            )
            
            # Get recommendations
            results["recommendations"] = self.config_manager.get_monitoring_recommendations()
            
            # Add error handling statistics
            try:
                error_stats_after = await self.error_handler.get_error_stats()
                results["error_handling"] = {
                    "urls_monitored": error_stats_after.get("total_urls", 0),
                    "circuit_breakers_active": len([s for s in error_stats_after.get("circuit_breaker_states", {}).values() 
                                                  if s.get("state") == "open"]),
                    "total_errors": sum(len(stats.get("errors", {})) for stats in error_stats_after.get("url_stats", {}).values()),
                    "success_rate": self._calculate_success_rate(error_stats_after)
                }
            except Exception as e:
                logger.error(f"Error getting error handling statistics: {e}")
                results["error_handling"] = {"error": str(e)}
            
            # Get comprehensive monitoring statistics
            try:
                results["monitoring_statistics"] = await self.monitoring_stats.get_comprehensive_statistics()
            except Exception as e:
                logger.error(f"Error getting monitoring statistics: {e}")
                results["monitoring_statistics"] = {"error": str(e)}
            
        except Exception as e:
            logger.error(f"Comprehensive monitoring failed: {e}")
            results["error"] = str(e)
            results["recommendations"].append(f"Fix comprehensive monitoring: {e}")
        
        finally:
            results["completed_at"] = datetime.utcnow()
            # WebScraper cleanup is handled by its async context manager
        
        return results
    
    def _calculate_success_rate(self, error_stats: Dict[str, Any]) -> float:
        """Calculate success rate from error statistics."""
        total_requests = 0
        successful_requests = 0
        
        for url_stats in error_stats.get("url_stats", {}).values():
            successful_requests += url_stats.get("success", 0)
            total_requests += url_stats.get("success", 0)
            total_requests += sum(url_stats.get("errors", {}).values())
        
        if total_requests == 0:
            return 100.0
        
        return (successful_requests / total_requests) * 100.0
    
    async def _process_comprehensive_batch(self, batch: Dict[str, Any], scraper: WebScraper) -> Dict[str, Any]:
        """
        Process a comprehensive monitoring batch.
        
        Args:
            batch: Batch configuration
            scraper: Web scraper instance
            
        Returns:
            Batch processing results
        """
        batch_results = {
            "batch_id": batch["batch_id"],
            "forms_processed": 0,
            "forms_failed": 0,
            "changes_detected": 0,
            "ai_analyses_performed": 0,
            "agency_results": []
        }
        
        forms = batch.get("forms", [])
        
        # Process forms in parallel (limited by batch size)
        semaphore = asyncio.Semaphore(self.batch_size)
        
        async def process_form(form_data):
            async with semaphore:
                try:
                    # Extract agency and form information
                    agency_key = form_data.get("agency_key")
                    agency_type = form_data.get("agency_type")
                    form_name = form_data.get("name")
                    
                    # Find corresponding agency in database
                    with get_db() as db:
                        agency = db.query(Agency).filter(
                            Agency.name.ilike(f"%{agency_key}%")
                        ).first()
                        
                        if not agency:
                            logger.warning(f"Agency not found in database: {agency_key}")
                            return {
                                "agency_key": agency_key,
                                "form_name": form_name,
                                "status": "failed",
                                "error": "Agency not found in database"
                            }
                        
                        # Find form
                        form = db.query(Form).filter(
                            Form.agency_id == agency.id,
                            Form.name == form_name
                        ).first()
                        
                        if not form:
                            logger.warning(f"Form not found: {form_name} for agency {agency_key}")
                            return {
                                "agency_key": agency_key,
                                "form_name": form_name,
                                "status": "failed",
                                "error": "Form not found in database"
                            }
                        
                        # Monitor the form
                        form_result = await self._analyze_form_changes(form, scraper, db)
                        
                        batch_results["forms_processed"] += 1
                        if form_result.get("changes_detected", 0) > 0:
                            batch_results["changes_detected"] += form_result["changes_detected"]
                        if form_result.get("ai_analysis_performed"):
                            batch_results["ai_analyses_performed"] += 1
                        
                        return {
                            "agency_key": agency_key,
                            "agency_type": agency_type,
                            "form_name": form_name,
                            "status": "success",
                            "result": form_result
                        }
                        
                except Exception as e:
                    logger.error(f"Error processing form {form_data.get('name', 'unknown')}: {e}")
                    batch_results["forms_failed"] += 1
                    return {
                        "agency_key": form_data.get("agency_key", "unknown"),
                        "form_name": form_data.get("name", "unknown"),
                        "status": "failed",
                        "error": str(e)
                    }
        
        # Process all forms in the batch
        tasks = [process_form(form) for form in forms]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and collect results
        for result in results:
            if isinstance(result, Exception):
                batch_results["forms_failed"] += 1
                batch_results["agency_results"].append({
                    "status": "failed",
                    "error": str(result)
                })
            else:
                batch_results["agency_results"].append(result)
        
        return batch_results


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