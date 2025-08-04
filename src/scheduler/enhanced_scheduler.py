"""
Enhanced Monitoring Scheduler

This module extends the existing monitoring scheduler with AI-enhanced capabilities
and improved frequency management for daily/weekly monitoring based on form requirements.
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor
import threading

from ..database.connection import get_db
from ..database.models import Agency, Form, MonitoringRun, FormChange
from ..monitors.ai_enhanced_monitor import AIEnhancedMonitor, monitor_agency_with_ai
from ..notifications.notifier import NotificationManager
from ..utils.config_loader import get_monitoring_settings

logger = logging.getLogger(__name__)


class EnhancedMonitoringScheduler:
    """
    Enhanced monitoring scheduler with AI-powered change detection.
    
    Features:
    - AI-enhanced monitoring with semantic analysis
    - Flexible frequency scheduling (daily, weekly, monthly)
    - Intelligent frequency adjustment based on form activity
    - Performance monitoring and optimization
    - Comprehensive audit logging
    """
    
    def __init__(self, 
                 confidence_threshold: int = 70,
                 enable_llm_analysis: bool = True,
                 batch_size: int = 5):
        """
        Initialize the enhanced monitoring scheduler.
        
        Args:
            confidence_threshold: AI analysis confidence threshold
            enable_llm_analysis: Whether to use LLM for detailed analysis
            batch_size: Number of forms to process in parallel
        """
        self.ai_monitor = AIEnhancedMonitor(
            confidence_threshold=confidence_threshold,
            enable_llm_analysis=enable_llm_analysis,
            batch_size=batch_size
        )
        self.notification_manager = NotificationManager()
        self.monitoring_settings = get_monitoring_settings()
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=6)  # Increased for AI processing
        self._schedule_thread = None
        
        # Performance tracking
        self.stats = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "changes_detected": 0,
            "ai_analyses_performed": 0,
            "avg_processing_time_ms": 0,
            "last_run": None
        }
        
        # Frequency management
        self.frequency_settings = {
            "daily": {
                "time": "06:00",
                "priority": "high",
                "max_retries": 3
            },
            "weekly": {
                "time": "07:00",
                "day": "monday",
                "priority": "medium",
                "max_retries": 2
            },
            "monthly": {
                "time": "06:30",
                "day": "monday",
                "priority": "low",
                "max_retries": 1
            }
        }
    
    def start(self):
        """Start the enhanced monitoring scheduler."""
        if self.running:
            logger.warning("Enhanced scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting enhanced monitoring scheduler with AI capabilities...")
        
        # Set up schedules based on form requirements
        self._setup_enhanced_schedules()
        
        # Start the scheduler in a separate thread
        self._schedule_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._schedule_thread.start()
        
        logger.info("Enhanced monitoring scheduler started successfully")
    
    def stop(self):
        """Stop the enhanced monitoring scheduler."""
        if not self.running:
            logger.warning("Enhanced scheduler is not running")
            return
        
        self.running = False
        
        # Clear all scheduled jobs
        schedule.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        if self._schedule_thread:
            self._schedule_thread.join(timeout=5)
        
        logger.info("Enhanced monitoring scheduler stopped")
    
    def _setup_enhanced_schedules(self):
        """Set up enhanced monitoring schedules based on form requirements."""
        # Clear any existing schedules
        schedule.clear()
        
        with get_db() as db:
            agencies = db.query(Agency).filter(Agency.is_active == True).all()
            
            for agency in agencies:
                for form in agency.forms:
                    if not form.is_active:
                        continue
                    
                    frequency = form.check_frequency or self.monitoring_settings.get('default_check_frequency', 'weekly')
                    self._schedule_enhanced_form_monitoring(agency.id, form.id, frequency)
        
        # Schedule enhanced daily summary with AI insights
        schedule.every().day.at("08:00").do(self._generate_enhanced_daily_summary)
        
        # Schedule enhanced weekly detailed report
        schedule.every().monday.at("09:00").do(self._generate_enhanced_weekly_report)
        
        # Schedule AI model performance monitoring
        schedule.every().day.at("03:00").do(self._monitor_ai_performance)
        
        # Schedule database cleanup
        schedule.every().day.at("02:00").do(self._cleanup_old_data)
        
        # Schedule frequency optimization
        schedule.every().sunday.at("04:00").do(self._optimize_monitoring_frequencies)
        
        logger.info(f"Enhanced scheduler configured for {len(schedule.jobs)} tasks")
    
    def _schedule_enhanced_form_monitoring(self, agency_id: int, form_id: int, frequency: str):
        """Schedule enhanced monitoring for a specific form with AI capabilities."""
        job_name = f"ai_monitor_form_{agency_id}_{form_id}"
        
        if frequency == "daily":
            schedule.every().day.at(self.frequency_settings["daily"]["time"]).do(
                self._ai_monitor_form_wrapper, agency_id, form_id, "daily"
            ).tag(job_name)
        elif frequency == "weekly":
            schedule.every().monday.at(self.frequency_settings["weekly"]["time"]).do(
                self._ai_monitor_form_wrapper, agency_id, form_id, "weekly"
            ).tag(job_name)
        elif frequency == "monthly":
            schedule.every().day.at(self.frequency_settings["monthly"]["time"]).do(
                self._check_monthly_schedule, agency_id, form_id
            ).tag(job_name)
        else:
            # Default to weekly
            schedule.every().monday.at(self.frequency_settings["weekly"]["time"]).do(
                self._ai_monitor_form_wrapper, agency_id, form_id, "weekly"
            ).tag(job_name)
    
    def _run_scheduler(self):
        """Run the enhanced scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Enhanced scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _ai_monitor_form_wrapper(self, agency_id: int, form_id: int, frequency: str):
        """Wrapper to run AI-enhanced async monitoring in the scheduler."""
        start_time = time.time()
        
        try:
            # Run the async AI monitoring function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._ai_monitor_single_form(agency_id, form_id, frequency)
            )
            
            loop.close()
            
            # Update statistics
            processing_time = int((time.time() - start_time) * 1000)
            self._update_stats(True, processing_time, result)
            
            logger.info(f"AI-enhanced monitoring completed for agency {agency_id}, form {form_id} "
                       f"(frequency: {frequency}, time: {processing_time}ms)")
            return result
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            self._update_stats(False, processing_time, None)
            
            logger.error(f"Error in AI-enhanced monitoring for agency {agency_id}, form {form_id}: {e}")
    
    async def _ai_monitor_single_form(self, agency_id: int, form_id: int, frequency: str):
        """Monitor a single form with AI-enhanced capabilities."""
        with get_db() as db:
            agency = db.query(Agency).filter(Agency.id == agency_id).first()
            form = db.query(Form).filter(Form.id == form_id).first()
            
            if not agency or not form:
                logger.error(f"Agency {agency_id} or form {form_id} not found")
                return None
            
            logger.info(f"AI-enhanced monitoring {agency.name} - {form.name} (frequency: {frequency})")
            
            # Use AI-enhanced monitoring
            try:
                result = await self.ai_monitor.monitor_agency_with_ai(agency_id)
                
                # Check if changes were detected
                if result and result.get("changes_detected", 0) > 0:
                    logger.info(f"AI detected {result['changes_detected']} changes for {form.name}")
                    
                    # Send notifications for changes
                    await self._send_ai_enhanced_notifications(form_id, result, db)
                    
                    # Update form's last checked time
                    form.last_checked = datetime.utcnow()
                    db.commit()
                    
                    # Consider frequency adjustment based on activity
                    await self._consider_frequency_adjustment(form, result, frequency)
                else:
                    logger.info(f"No AI-detected changes for {form.name}")
                
                return result
                
            except Exception as e:
                logger.error(f"AI monitoring failed for {form.name}: {e}")
                return None
    
    async def _send_ai_enhanced_notifications(self, form_id: int, result: Dict[str, Any], db):
        """Send AI-enhanced notifications for detected changes."""
        try:
            # Get the latest form change
            latest_change = db.query(FormChange).filter(
                FormChange.form_id == form_id
            ).order_by(FormChange.detected_at.desc()).first()
            
            if latest_change:
                await self.notification_manager.send_change_notification(latest_change.id)
                logger.info(f"AI-enhanced notifications sent for change {latest_change.id}")
        except Exception as e:
            logger.error(f"Failed to send AI-enhanced notifications: {e}")
    
    async def _consider_frequency_adjustment(self, form: Form, result: Dict[str, Any], current_frequency: str):
        """Consider adjusting monitoring frequency based on AI analysis results."""
        try:
            # Analyze recent activity patterns
            recent_changes = result.get("changes_detected", 0)
            ai_confidence = result.get("analysis_summary", {}).get("avg_confidence_score", 0)
            
            # Adjust frequency based on activity level
            if current_frequency == "weekly" and recent_changes > 2:
                # High activity - consider daily monitoring
                logger.info(f"High activity detected for {form.name}, considering daily monitoring")
                await self._suggest_frequency_change(form.id, "daily", "high_activity")
            
            elif current_frequency == "daily" and recent_changes == 0:
                # Low activity - consider weekly monitoring
                logger.info(f"Low activity detected for {form.name}, considering weekly monitoring")
                await self._suggest_frequency_change(form.id, "weekly", "low_activity")
                
        except Exception as e:
            logger.error(f"Error in frequency adjustment analysis: {e}")
    
    async def _suggest_frequency_change(self, form_id: int, new_frequency: str, reason: str):
        """Suggest a frequency change for a form."""
        # In a real implementation, this would create a suggestion record
        # and notify administrators for approval
        logger.info(f"Frequency change suggestion: Form {form_id} -> {new_frequency} (reason: {reason})")
    
    def _check_monthly_schedule(self, agency_id: int, form_id: int):
        """Check if it's time for monthly monitoring (first Monday of the month)."""
        today = datetime.now().date()
        
        # Check if it's the first Monday of the month
        if today.weekday() == 0 and today.day <= 7:  # Monday and first week
            self._ai_monitor_form_wrapper(agency_id, form_id, "monthly")
        else:
            logger.debug(f"Skipping monthly monitoring for agency {agency_id}, form {form_id} - not first Monday")
    
    async def _generate_enhanced_daily_summary(self):
        """Generate enhanced daily summary with AI insights."""
        logger.info("Generating enhanced daily summary with AI insights...")
        
        try:
            with get_db() as db:
                # Get today's changes
                today = datetime.now().date()
                changes = db.query(FormChange).filter(
                    FormChange.detected_at >= today
                ).all()
                
                # Generate AI-enhanced summary
                summary = {
                    "date": today.isoformat(),
                    "total_changes": len(changes),
                    "ai_analyses": 0,
                    "high_priority_changes": 0,
                    "medium_priority_changes": 0,
                    "low_priority_changes": 0,
                    "cosmetic_changes": 0,
                    "avg_confidence": 0,
                    "forms_affected": set(),
                    "agencies_affected": set()
                }
                
                for change in changes:
                    if change.ai_confidence_score:
                        summary["ai_analyses"] += 1
                        summary["avg_confidence"] += change.ai_confidence_score
                    
                    if change.severity == "high":
                        summary["high_priority_changes"] += 1
                    elif change.severity == "medium":
                        summary["medium_priority_changes"] += 1
                    else:
                        summary["low_priority_changes"] += 1
                    
                    if change.is_cosmetic_change:
                        summary["cosmetic_changes"] += 1
                    
                    summary["forms_affected"].add(change.form_id)
                    summary["agencies_affected"].add(change.form.agency_id)
                
                # Calculate averages
                if summary["ai_analyses"] > 0:
                    summary["avg_confidence"] = int(summary["avg_confidence"] / summary["ai_analyses"])
                
                summary["forms_affected"] = len(summary["forms_affected"])
                summary["agencies_affected"] = len(summary["agencies_affected"])
                
                logger.info(f"Enhanced daily summary: {summary}")
                
                # TODO: Send enhanced summary to stakeholders
                
        except Exception as e:
            logger.error(f"Error generating enhanced daily summary: {e}")
    
    async def _generate_enhanced_weekly_report(self):
        """Generate enhanced weekly report with AI insights and trends."""
        logger.info("Generating enhanced weekly report with AI insights...")
        
        try:
            with get_db() as db:
                # Get last week's changes
                week_ago = datetime.now() - timedelta(days=7)
                changes = db.query(FormChange).filter(
                    FormChange.detected_at >= week_ago
                ).all()
                
                # Generate comprehensive weekly report
                report = {
                    "period": f"{week_ago.date()} to {datetime.now().date()}",
                    "total_changes": len(changes),
                    "ai_analyses_performed": 0,
                    "avg_confidence_score": 0,
                    "severity_breakdown": {"high": 0, "medium": 0, "low": 0},
                    "change_types": {},
                    "top_affected_forms": [],
                    "frequency_recommendations": []
                }
                
                # Analyze changes
                form_changes = {}
                for change in changes:
                    if change.ai_confidence_score:
                        report["ai_analyses_performed"] += 1
                        report["avg_confidence_score"] += change.ai_confidence_score
                    
                    report["severity_breakdown"][change.severity] += 1
                    
                    change_type = change.ai_change_category or change.change_type
                    report["change_types"][change_type] = report["change_types"].get(change_type, 0) + 1
                    
                    form_changes[change.form_id] = form_changes.get(change.form_id, 0) + 1
                
                # Calculate averages
                if report["ai_analyses_performed"] > 0:
                    report["avg_confidence_score"] = int(report["avg_confidence_score"] / report["ai_analyses_performed"])
                
                # Get top affected forms
                sorted_forms = sorted(form_changes.items(), key=lambda x: x[1], reverse=True)
                report["top_affected_forms"] = sorted_forms[:5]
                
                logger.info(f"Enhanced weekly report: {report}")
                
                # TODO: Send enhanced weekly report to stakeholders
                
        except Exception as e:
            logger.error(f"Error generating enhanced weekly report: {e}")
    
    async def _monitor_ai_performance(self):
        """Monitor AI model performance and health."""
        logger.info("Monitoring AI model performance...")
        
        try:
            # Get AI service health
            ai_health = await self.ai_monitor.get_service_health()
            
            # Get performance statistics
            ai_stats = self.ai_monitor.analysis_service.get_service_stats() if self.ai_monitor.analysis_service else {}
            
            performance_report = {
                "ai_service_health": ai_health,
                "performance_stats": ai_stats,
                "scheduler_stats": self.stats,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"AI performance report: {performance_report}")
            
            # Alert if AI service is degraded
            if ai_health.get("status") == "degraded":
                logger.warning("AI service is degraded - consider investigation")
                
        except Exception as e:
            logger.error(f"Error monitoring AI performance: {e}")
    
    async def _optimize_monitoring_frequencies(self):
        """Optimize monitoring frequencies based on historical data."""
        logger.info("Optimizing monitoring frequencies...")
        
        try:
            with get_db() as db:
                # Analyze change patterns for each form
                forms = db.query(Form).filter(Form.is_active == True).all()
                
                for form in forms:
                    # Get last 30 days of changes
                    thirty_days_ago = datetime.now() - timedelta(days=30)
                    recent_changes = db.query(FormChange).filter(
                        FormChange.form_id == form.id,
                        FormChange.detected_at >= thirty_days_ago
                    ).all()
                    
                    change_count = len(recent_changes)
                    current_frequency = form.check_frequency or "weekly"
                    
                    # Suggest frequency optimization
                    if change_count > 5 and current_frequency != "daily":
                        logger.info(f"Suggesting daily monitoring for {form.name} (high activity: {change_count} changes)")
                    elif change_count == 0 and current_frequency == "daily":
                        logger.info(f"Suggesting weekly monitoring for {form.name} (low activity)")
                
        except Exception as e:
            logger.error(f"Error optimizing monitoring frequencies: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        logger.info("Cleaning up old monitoring data...")
        
        try:
            with get_db() as db:
                # Keep monitoring runs for 90 days
                ninety_days_ago = datetime.now() - timedelta(days=90)
                old_runs = db.query(MonitoringRun).filter(
                    MonitoringRun.completed_at < ninety_days_ago
                ).all()
                
                for run in old_runs:
                    db.delete(run)
                
                db.commit()
                logger.info(f"Cleaned up {len(old_runs)} old monitoring runs")
                
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")
    
    def _update_stats(self, success: bool, processing_time_ms: int, result: Optional[Dict[str, Any]]):
        """Update scheduler statistics."""
        self.stats["total_runs"] += 1
        
        if success:
            self.stats["successful_runs"] += 1
            if result:
                self.stats["changes_detected"] += result.get("changes_detected", 0)
                self.stats["ai_analyses_performed"] += result.get("ai_analyses_performed", 0)
        else:
            self.stats["failed_runs"] += 1
        
        # Update average processing time
        current_avg = self.stats["avg_processing_time_ms"]
        total_runs = self.stats["total_runs"]
        self.stats["avg_processing_time_ms"] = int(
            (current_avg * (total_runs - 1) + processing_time_ms) / total_runs
        )
        
        self.stats["last_run"] = datetime.utcnow()
    
    def get_enhanced_schedule_status(self) -> Dict[str, Any]:
        """Get enhanced scheduler status with AI metrics."""
        status = {
            "scheduler_running": self.running,
            "total_scheduled_jobs": len(schedule.jobs),
            "ai_monitor_available": self.ai_monitor.analysis_service is not None,
            "performance_stats": self.stats.copy(),
            "frequency_settings": self.frequency_settings,
            "last_run": self.stats["last_run"].isoformat() if self.stats["last_run"] else None
        }
        
        # Add AI service health if available
        if self.ai_monitor.analysis_service:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                ai_health = loop.run_until_complete(self.ai_monitor.get_service_health())
                loop.close()
                status["ai_service_health"] = ai_health
            except Exception as e:
                status["ai_service_health"] = {"error": str(e)}
        
        return status
    
    def reschedule_form_with_ai(self, form_id: int, new_frequency: str):
        """Reschedule a form with AI-enhanced monitoring."""
        try:
            with get_db() as db:
                form = db.query(Form).filter(Form.id == form_id).first()
                if not form:
                    logger.error(f"Form {form_id} not found for rescheduling")
                    return False
                
                # Update form frequency
                form.check_frequency = new_frequency
                db.commit()
                
                # Remove old schedule and add new one
                old_job_name = f"ai_monitor_form_{form.agency_id}_{form_id}"
                schedule.clear(old_job_name)
                
                self._schedule_enhanced_form_monitoring(form.agency_id, form_id, new_frequency)
                
                logger.info(f"Rescheduled form {form.name} to {new_frequency} monitoring")
                return True
                
        except Exception as e:
            logger.error(f"Error rescheduling form {form_id}: {e}")
            return False
    
    async def run_immediate_ai_check(self, agency_id: Optional[int] = None, form_id: Optional[int] = None):
        """Run immediate AI-enhanced monitoring check."""
        logger.info(f"Running immediate AI-enhanced check (agency: {agency_id}, form: {form_id})")
        
        try:
            if agency_id:
                result = await self.ai_monitor.monitor_agency_with_ai(agency_id)
                return result
            else:
                # Run for all active agencies
                with get_db() as db:
                    agencies = db.query(Agency).filter(Agency.is_active == True).all()
                    results = {}
                    
                    for agency in agencies:
                        result = await self.ai_monitor.monitor_agency_with_ai(agency.id)
                        results[agency.id] = result
                    
                    return results
                    
        except Exception as e:
            logger.error(f"Error in immediate AI check: {e}")
            return None


# Global scheduler instance
_enhanced_scheduler = None

def get_enhanced_scheduler() -> EnhancedMonitoringScheduler:
    """Get the global enhanced scheduler instance."""
    global _enhanced_scheduler
    if _enhanced_scheduler is None:
        _enhanced_scheduler = EnhancedMonitoringScheduler()
    return _enhanced_scheduler

def start_enhanced_scheduler():
    """Start the enhanced monitoring scheduler."""
    scheduler = get_enhanced_scheduler()
    scheduler.start()

def stop_enhanced_scheduler():
    """Stop the enhanced monitoring scheduler."""
    scheduler = get_enhanced_scheduler()
    scheduler.stop() 