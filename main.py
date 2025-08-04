#!/usr/bin/env python3
"""
Payroll Monitoring System - Main Entry Point

This is the main entry point for the AI-powered payroll monitoring system
that monitors all 50 states, federal, and other government agency certified
payroll reporting requirements.

Usage:
    python main.py [command] [options]

Commands:
    start       Start the monitoring system (scheduler + web dashboard)
    init-db     Initialize the database and load configuration
    load-data   Load agency and form data from configuration
    monitor     Run immediate monitoring check
    test        Run system tests
    dashboard   Start only the web dashboard
    scheduler   Start only the scheduler

Examples:
    python main.py init-db
    python main.py load-data
    python main.py start
    python main.py monitor
    python main.py test
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_db, get_db, close_db, test_connection
from src.database.models import Agency, Form
from src.scheduler.monitoring_scheduler import start_scheduler, stop_scheduler, get_scheduler
from src.notifications.notifier import NotificationManager
from src.utils.config_loader import (
    load_agency_config, get_all_forms, validate_environment_variables,
    get_monitoring_settings
)
from src.api.main import app

# Configure logging
def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            logging.FileHandler(logs_dir / 'payroll_monitor.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger(__name__)


class PayrollMonitor:
    """Main application class for the payroll monitoring system."""
    
    def __init__(self):
        self.running = False
        self.scheduler = None
        
    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.shutdown()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self) -> None:
        """Gracefully shutdown the application."""
        logger.info("Shutting down payroll monitoring system...")
        self.running = False
        
        if self.scheduler:
            stop_scheduler()
        
        close_db()
        logger.info("Shutdown complete")
    
    def init_database(self) -> bool:
        """Initialize database tables."""
        try:
            logger.info("Initializing database...")
            init_db()
            
            # Test database connection
            if not test_connection():
                raise Exception("Database connection test failed")
            
            logger.info("Database initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}", exc_info=True)
            return False
    
    def load_agency_data(self) -> bool:
        """Load agency and form data from configuration into database."""
        try:
            logger.info("Loading agency configuration...")
            config = load_agency_config()
            
            with get_db() as db:
                # Load federal agencies
                federal_agencies = config.get('federal', {})
                for agency_key, agency_data in federal_agencies.items():
                    self._load_agency(db, agency_data, 'federal', agency_key)
                
                # Load state agencies
                state_agencies = config.get('states', {})
                for state_key, state_data in state_agencies.items():
                    self._load_agency(db, state_data, 'state', state_key)
            
            logger.info("Agency data loaded successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load agency data: {e}", exc_info=True)
            return False
    
    def _load_agency(self, db, agency_data: dict, agency_type: str, agency_key: str) -> None:
        """Load a single agency and its forms."""
        # Check if agency already exists
        existing_agency = db.query(Agency).filter(
            Agency.name == agency_data['name']
        ).first()
        
        if existing_agency:
            logger.info(f"Agency already exists: {agency_data['name']}")
            agency = existing_agency
        else:
            # Create new agency
            agency = Agency(
                name=agency_data['name'],
                agency_type=agency_type,
                base_url=agency_data['base_url'],
                contact_phone=agency_data.get('contact', {}).get('phone'),
                contact_email=agency_data.get('contact', {}).get('email')
            )
            
            if agency_type == 'state':
                agency.abbreviation = agency_data.get('abbreviation')
                agency.prevailing_wage_url = agency_data.get('prevailing_wage_url')
            
            db.add(agency)
            db.flush()  # To get the agency ID
            logger.info(f"Created {agency_type} agency: {agency.name}")
        
        # Load forms for this agency
        forms = agency_data.get('forms', [])
        for form_data in forms:
            self._load_form(db, agency, form_data)
    
    def _load_form(self, db, agency: Agency, form_data: dict) -> None:
        """Load a single form."""
        existing_form = db.query(Form).filter(
            Form.agency_id == agency.id,
            Form.name == form_data['name']
        ).first()
        
        if existing_form:
            logger.info(f"Form already exists: {form_data['name']}")
        else:
            form = Form(
                agency_id=agency.id,
                name=form_data['name'],
                title=form_data['title'],
                form_url=form_data.get('form_url') or form_data.get('url'),
                instructions_url=form_data.get('instructions_url'),
                check_frequency=form_data.get('check_frequency', 'weekly'),
                contact_email=form_data.get('contact_email')
            )
            db.add(form)
            logger.info(f"Created form: {form.name} for {agency.name}")
    
    async def run_monitoring(self) -> bool:
        """Run immediate monitoring check."""
        try:
            logger.info("Starting immediate monitoring check...")
            scheduler = get_scheduler()
            scheduler.run_immediate_check()
            logger.info("Monitoring check completed!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to run monitoring: {e}", exc_info=True)
            return False
    
    async def test_system(self) -> bool:
        """Run comprehensive system tests."""
        try:
            logger.info("Running system tests...")
            
            # Test database connection
            logger.info("Testing database connection...")
            if not test_connection():
                raise Exception("Database connection test failed")
            
            with get_db() as db:
                agency_count = db.query(Agency).count()
                form_count = db.query(Form).count()
                logger.info(f"Database: {agency_count} agencies, {form_count} forms")
            
            # Test notification system
            logger.info("Testing notification system...")
            notification_manager = NotificationManager()
            results = await notification_manager.test_notifications()
            
            for channel, success in results.items():
                status = "✅ Success" if success else "❌ Failed"
                logger.info(f"Notification test - {channel}: {status}")
            
            # Test configuration loading
            logger.info("Testing configuration loading...")
            config = load_agency_config()
            all_forms = get_all_forms(config)
            logger.info(f"Configuration: {len(all_forms)} forms configured")
            
            logger.info("System tests completed!")
            return True
            
        except Exception as e:
            logger.error(f"System tests failed: {e}", exc_info=True)
            return False
    
    def start_dashboard(self) -> bool:
        """Start the web dashboard."""
        try:
            import uvicorn
            logger.info("Starting web dashboard on http://localhost:8000")
            uvicorn.run(app, host="0.0.0.0", port=8000)
            return True
            
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}", exc_info=True)
            return False
    
    def start_monitoring_scheduler(self) -> bool:
        """Start the monitoring scheduler."""
        try:
            logger.info("Starting monitoring scheduler...")
            start_scheduler()
            
            # Keep running
            while self.running:
                time.sleep(60)
                scheduler = get_scheduler()
                status = scheduler.get_schedule_status()
                logger.info(f"Scheduler status: Running={status['running']}, Jobs={status['scheduled_jobs']}")
            
            return True
            
        except KeyboardInterrupt:
            logger.info("Shutting down scheduler...")
            stop_scheduler()
            return True
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
            stop_scheduler()
            return False
    
    def start_full_system(self) -> bool:
        """Start both scheduler and dashboard."""
        try:
            logger.info("Starting full payroll monitoring system...")
            self.running = True
            
            # Start scheduler in background
            import threading
            scheduler_thread = threading.Thread(target=self.start_monitoring_scheduler, daemon=True)
            scheduler_thread.start()
            
            # Start dashboard (this blocks)
            return self.start_dashboard()
            
        except KeyboardInterrupt:
            logger.info("Shutting down system...")
            self.shutdown()
            return True
        except Exception as e:
            logger.error(f"System error: {e}", exc_info=True)
            self.shutdown()
            return False


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Payroll Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        'command',
        choices=['start', 'init-db', 'load-data', 'monitor', 'test', 'dashboard', 'scheduler'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    logger.info(f"🚨 Payroll Monitoring System - {args.command.upper()}")
    
    # Create application instance
    app = PayrollMonitor()
    app.setup_signal_handlers()
    
    success = False
    
    try:
        if args.command == 'init-db':
            success = app.init_database()
        
        elif args.command == 'load-data':
            if not app.init_database():
                logger.error("Database initialization failed")
                sys.exit(1)
            success = app.load_agency_data()
        
        elif args.command == 'monitor':
            success = asyncio.run(app.run_monitoring())
        
        elif args.command == 'test':
            success = asyncio.run(app.test_system())
        
        elif args.command == 'dashboard':
            success = app.start_dashboard()
        
        elif args.command == 'scheduler':
            success = app.start_monitoring_scheduler()
        
        elif args.command == 'start':
            # Initialize and load data if needed
            if not app.init_database():
                logger.error("Database initialization failed")
                sys.exit(1)
            
            with get_db() as db:
                if db.query(Agency).count() == 0:
                    logger.info("No agencies found, loading data...")
                    if not app.load_agency_data():
                        logger.error("Failed to load agency data")
                        sys.exit(1)
            
            success = app.start_full_system()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
        app.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        app.shutdown()
        sys.exit(1)
    
    if success:
        logger.info(f"Command '{args.command}' completed successfully!")
        sys.exit(0)
    else:
        logger.error(f"Command '{args.command}' failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()