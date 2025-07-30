import asyncio
import logging
import schedule
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

from ..database.connection import get_db
from ..database.models import Agency, Form, MonitoringRun
from ..monitors.web_scraper import AgencyMonitor
from ..notifications.notifier import NotificationManager
from ..utils.config_loader import get_monitoring_settings

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """Automated scheduler for payroll form monitoring."""
    
    def __init__(self):
        self.monitor = AgencyMonitor()
        self.notification_manager = NotificationManager()
        self.monitoring_settings = get_monitoring_settings()
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._schedule_thread = None
        
    def start(self):
        """Start the monitoring scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting monitoring scheduler...")
        
        # Set up schedules based on configuration
        self._setup_schedules()
        
        # Start the scheduler in a separate thread
        self._schedule_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._schedule_thread.start()
        
        logger.info("Monitoring scheduler started successfully")
    
    def stop(self):
        """Stop the monitoring scheduler."""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        self.running = False
        
        # Clear all scheduled jobs
        schedule.clear()
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        if self._schedule_thread:
            self._schedule_thread.join(timeout=5)
        
        logger.info("Monitoring scheduler stopped")
    
    def _setup_schedules(self):
        """Set up monitoring schedules based on agency configurations."""
        # Clear any existing schedules
        schedule.clear()
        
        with get_db() as db:
            agencies = db.query(Agency).filter(Agency.is_active == True).all()
            
            for agency in agencies:
                for form in agency.forms:
                    if not form.is_active:
                        continue
                    
                    frequency = form.check_frequency or self.monitoring_settings.get('default_check_frequency', 'weekly')
                    self._schedule_form_monitoring(agency.id, form.id, frequency)
        
        # Schedule daily summary report
        schedule.every().day.at("08:00").do(self._generate_daily_summary)
        
        # Schedule weekly detailed report
        schedule.every().monday.at("09:00").do(self._generate_weekly_report)
        
        # Schedule database cleanup
        schedule.every().day.at("02:00").do(self._cleanup_old_data)
        
        logger.info(f"Scheduled monitoring for {len(schedule.jobs)} tasks")
    
    def _schedule_form_monitoring(self, agency_id: int, form_id: int, frequency: str):
        """Schedule monitoring for a specific form."""
        job_name = f"monitor_form_{agency_id}_{form_id}"
        
        if frequency == "daily":
            schedule.every().day.at("06:00").do(
                self._monitor_form_wrapper, agency_id, form_id
            ).tag(job_name)
        elif frequency == "weekly":
            schedule.every().monday.at("07:00").do(
                self._monitor_form_wrapper, agency_id, form_id
            ).tag(job_name)
        elif frequency == "monthly":
            schedule.every().day.at("06:30").do(
                self._check_monthly_schedule, agency_id, form_id
            ).tag(job_name)
        else:
            # Default to weekly
            schedule.every().monday.at("07:00").do(
                self._monitor_form_wrapper, agency_id, form_id
            ).tag(job_name)
    
    def _run_scheduler(self):
        """Run the scheduler loop."""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def _monitor_form_wrapper(self, agency_id: int, form_id: int):
        """Wrapper to run async monitoring in the scheduler."""
        try:
            # Run the async monitoring function
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._monitor_single_form(agency_id, form_id)
            )
            
            loop.close()
            
            logger.info(f"Scheduled monitoring completed for agency {agency_id}, form {form_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error in scheduled monitoring for agency {agency_id}, form {form_id}: {e}")
    
    async def _monitor_single_form(self, agency_id: int, form_id: int):
        """Monitor a single form and handle notifications."""
        with get_db() as db:
            agency = db.query(Agency).filter(Agency.id == agency_id).first()
            form = db.query(Form).filter(Form.id == form_id).first()
            
            if not agency or not form:
                logger.error(f"Agency {agency_id} or form {form_id} not found")
                return
            
            logger.info(f"Monitoring {agency.name} - {form.name}")
            
            # Monitor the specific form
            changes = await self.monitor._monitor_form(form, db)
            
            # Send notifications for any changes detected
            if changes:
                logger.info(f"Changes detected for {form.name}: {len(changes)} changes")
                
                # Get the latest form change
                latest_change = db.query(FormChange).filter(
                    FormChange.form_id == form_id
                ).order_by(FormChange.detected_at.desc()).first()
                
                if latest_change:
                    try:
                        await self.notification_manager.send_change_notification(latest_change.id)
                        logger.info(f"Notifications sent for change {latest_change.id}")
                    except Exception as e:
                        logger.error(f"Failed to send notifications for change {latest_change.id}: {e}")
            else:
                logger.info(f"No changes detected for {form.name}")
    
    def _check_monthly_schedule(self, agency_id: int, form_id: int):
        """Check if it's time for monthly monitoring (first Monday of the month)."""
        today = datetime.now().date()
        
        # Check if today is the first Monday of the month
        first_day = today.replace(day=1)
        first_monday = first_day + timedelta(days=(7 - first_day.weekday()) % 7)
        
        if today == first_monday:
            self._monitor_form_wrapper(agency_id, form_id)
    
    def _generate_daily_summary(self):
        """Generate daily monitoring summary."""
        try:
            logger.info("Generating daily monitoring summary...")
            
            with get_db() as db:
                # Get monitoring runs from the last 24 hours
                yesterday = datetime.utcnow() - timedelta(days=1)
                
                recent_runs = db.query(MonitoringRun).filter(
                    MonitoringRun.started_at >= yesterday
                ).all()
                
                # Get changes detected in the last 24 hours
                recent_changes = db.query(FormChange).filter(
                    FormChange.detected_at >= yesterday
                ).all()
                
                summary = {
                    'date': datetime.utcnow().strftime('%Y-%m-%d'),
                    'monitoring_runs': len(recent_runs),
                    'successful_runs': len([r for r in recent_runs if r.status == 'completed']),
                    'failed_runs': len([r for r in recent_runs if r.status == 'failed']),
                    'changes_detected': len(recent_changes),
                    'high_priority_changes': len([c for c in recent_changes if c.severity in ['high', 'critical']])
                }
                
                logger.info(f"Daily summary: {summary}")
                
                # TODO: Store summary in database or send to stakeholders
                
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
    
    def _generate_weekly_report(self):
        """Generate weekly monitoring report."""
        try:
            logger.info("Generating weekly monitoring report...")
            
            with get_db() as db:
                # Get data from the last 7 days
                week_ago = datetime.utcnow() - timedelta(days=7)
                
                weekly_runs = db.query(MonitoringRun).filter(
                    MonitoringRun.started_at >= week_ago
                ).all()
                
                weekly_changes = db.query(FormChange).filter(
                    FormChange.detected_at >= week_ago
                ).all()
                
                # Group by agency
                agency_stats = {}
                for run in weekly_runs:
                    agency_name = run.agency.name
                    if agency_name not in agency_stats:
                        agency_stats[agency_name] = {
                            'total_runs': 0,
                            'successful_runs': 0,
                            'failed_runs': 0,
                            'changes': 0
                        }
                    
                    agency_stats[agency_name]['total_runs'] += 1
                    if run.status == 'completed':
                        agency_stats[agency_name]['successful_runs'] += 1
                    elif run.status == 'failed':
                        agency_stats[agency_name]['failed_runs'] += 1
                
                for change in weekly_changes:
                    agency_name = change.form.agency.name
                    if agency_name in agency_stats:
                        agency_stats[agency_name]['changes'] += 1
                
                report = {
                    'week_ending': datetime.utcnow().strftime('%Y-%m-%d'),
                    'total_monitoring_runs': len(weekly_runs),
                    'total_changes_detected': len(weekly_changes),
                    'agency_statistics': agency_stats
                }
                
                logger.info(f"Weekly report: {report}")
                
                # TODO: Generate detailed report and send to stakeholders
                
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
    
    def _cleanup_old_data(self):
        """Clean up old monitoring data."""
        try:
            logger.info("Cleaning up old monitoring data...")
            
            with get_db() as db:
                # Remove monitoring runs older than 90 days
                cutoff_date = datetime.utcnow() - timedelta(days=90)
                
                old_runs = db.query(MonitoringRun).filter(
                    MonitoringRun.started_at < cutoff_date
                ).count()
                
                if old_runs > 0:
                    db.query(MonitoringRun).filter(
                        MonitoringRun.started_at < cutoff_date
                    ).delete()
                    
                    logger.info(f"Cleaned up {old_runs} old monitoring runs")
                
                # Remove old notifications (older than 180 days)
                notification_cutoff = datetime.utcnow() - timedelta(days=180)
                
                old_notifications = db.query(Notification).filter(
                    Notification.sent_at < notification_cutoff
                ).count()
                
                if old_notifications > 0:
                    db.query(Notification).filter(
                        Notification.sent_at < notification_cutoff
                    ).delete()
                    
                    logger.info(f"Cleaned up {old_notifications} old notifications")
                
                db.commit()
                
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
    
    def run_immediate_check(self, agency_id: Optional[int] = None, form_id: Optional[int] = None):
        """Run an immediate monitoring check."""
        try:
            if form_id:
                # Monitor specific form
                with get_db() as db:
                    form = db.query(Form).filter(Form.id == form_id).first()
                    if form:
                        self._monitor_form_wrapper(form.agency_id, form_id)
                    else:
                        logger.error(f"Form {form_id} not found")
            elif agency_id:
                # Monitor all forms for specific agency
                with get_db() as db:
                    agency = db.query(Agency).filter(Agency.id == agency_id).first()
                    if agency:
                        for form in agency.forms:
                            if form.is_active:
                                self._monitor_form_wrapper(agency_id, form.id)
                    else:
                        logger.error(f"Agency {agency_id} not found")
            else:
                # Monitor all agencies
                with get_db() as db:
                    agencies = db.query(Agency).filter(Agency.is_active == True).all()
                    for agency in agencies:
                        for form in agency.forms:
                            if form.is_active:
                                self._monitor_form_wrapper(agency.id, form.id)
                                
        except Exception as e:
            logger.error(f"Error in immediate check: {e}")
    
    def get_schedule_status(self) -> Dict:
        """Get current schedule status."""
        return {
            'running': self.running,
            'scheduled_jobs': len(schedule.jobs),
            'next_run': schedule.next_run() if schedule.jobs else None,
            'job_details': [
                {
                    'job': str(job.job_func),
                    'next_run': job.next_run,
                    'interval': job.interval,
                    'unit': job.unit
                }
                for job in schedule.jobs
            ]
        }
    
    def reschedule_form(self, form_id: int, new_frequency: str):
        """Reschedule monitoring for a specific form."""
        with get_db() as db:
            form = db.query(Form).filter(Form.id == form_id).first()
            if not form:
                logger.error(f"Form {form_id} not found")
                return
            
            # Remove existing schedule for this form
            job_tag = f"monitor_form_{form.agency_id}_{form_id}"
            schedule.clear(job_tag)
            
            # Update form frequency
            form.check_frequency = new_frequency
            db.commit()
            
            # Reschedule with new frequency
            self._schedule_form_monitoring(form.agency_id, form_id, new_frequency)
            
            logger.info(f"Rescheduled form {form_id} with frequency: {new_frequency}")


# Global scheduler instance
_scheduler = None


def get_scheduler() -> MonitoringScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = MonitoringScheduler()
    return _scheduler


def start_scheduler():
    """Start the global scheduler."""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
        _scheduler = None


if __name__ == "__main__":
    # Test the scheduler
    logging.basicConfig(level=logging.INFO)
    
    scheduler = MonitoringScheduler()
    
    try:
        scheduler.start()
        print("Scheduler started. Press Ctrl+C to stop...")
        
        # Keep the main thread alive
        while True:
            time.sleep(10)
            status = scheduler.get_schedule_status()
            print(f"Status: {status['running']}, Jobs: {status['scheduled_jobs']}")
            
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
        print("Scheduler stopped.")