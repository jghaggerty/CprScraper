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
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database.connection import init_db, get_db
from src.database.models import Agency, Form
from src.scheduler.monitoring_scheduler import start_scheduler, stop_scheduler, get_scheduler
from src.notifications.notifier import NotificationManager
from src.utils.config_loader import load_agency_config, get_all_forms
from src.api.main import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/payroll_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def init_database():
    """Initialize database tables."""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def load_agency_data():
    """Load agency and form data from configuration into database."""
    try:
        logger.info("Loading agency configuration...")
        config = load_agency_config()
        
        with get_db() as db:
            # Load federal agencies
            federal_agencies = config.get('federal', {})
            for agency_key, agency_data in federal_agencies.items():
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
                        agency_type='federal',
                        base_url=agency_data['base_url'],
                        contact_phone=agency_data.get('contact', {}).get('phone'),
                        contact_email=agency_data.get('contact', {}).get('email')
                    )
                    db.add(agency)
                    db.flush()  # To get the agency ID
                    logger.info(f"Created federal agency: {agency.name}")
                
                # Load forms for this agency
                forms = agency_data.get('forms', [])
                for form_data in forms:
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
                            form_url=form_data.get('form_url'),
                            instructions_url=form_data.get('instructions_url'),
                            check_frequency=form_data.get('check_frequency', 'weekly'),
                            contact_email=form_data.get('contact_email')
                        )
                        db.add(form)
                        logger.info(f"Created form: {form.name} for {agency.name}")
            
            # Load state agencies
            state_agencies = config.get('states', {})
            for state_key, state_data in state_agencies.items():
                # Check if agency already exists
                existing_agency = db.query(Agency).filter(
                    Agency.name == state_data['name']
                ).first()
                
                if existing_agency:
                    logger.info(f"Agency already exists: {state_data['name']}")
                    agency = existing_agency
                else:
                    # Create new agency
                    agency = Agency(
                        name=state_data['name'],
                        abbreviation=state_data.get('abbreviation'),
                        agency_type='state',
                        base_url=state_data['base_url'],
                        prevailing_wage_url=state_data.get('prevailing_wage_url'),
                        contact_phone=state_data.get('contact', {}).get('phone'),
                        contact_email=state_data.get('contact', {}).get('email')
                    )
                    db.add(agency)
                    db.flush()  # To get the agency ID
                    logger.info(f"Created state agency: {agency.name}")
                
                # Load forms for this agency
                forms = state_data.get('forms', [])
                for form_data in forms:
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
                            form_url=form_data.get('url'),
                            check_frequency=form_data.get('check_frequency', 'weekly'),
                            contact_email=form_data.get('contact_email')
                        )
                        db.add(form)
                        logger.info(f"Created form: {form.name} for {agency.name}")
            
            db.commit()
        
        logger.info("Agency data loaded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load agency data: {e}")
        return False


async def run_monitoring():
    """Run immediate monitoring check."""
    try:
        logger.info("Starting immediate monitoring check...")
        scheduler = get_scheduler()
        scheduler.run_immediate_check()
        logger.info("Monitoring check completed!")
        return True
    except Exception as e:
        logger.error(f"Failed to run monitoring: {e}")
        return False


async def test_system():
    """Run comprehensive system tests."""
    try:
        logger.info("Running system tests...")
        
        # Test database connection
        logger.info("Testing database connection...")
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
        logger.error(f"System tests failed: {e}")
        return False


def start_dashboard():
    """Start the web dashboard."""
    try:
        import uvicorn
        logger.info("Starting web dashboard on http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}")
        return False


def start_monitoring_scheduler():
    """Start the monitoring scheduler."""
    try:
        logger.info("Starting monitoring scheduler...")
        start_scheduler()
        
        # Keep running
        import time
        while True:
            time.sleep(60)
            scheduler = get_scheduler()
            status = scheduler.get_schedule_status()
            logger.info(f"Scheduler status: Running={status['running']}, Jobs={status['scheduled_jobs']}")
            
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        stop_scheduler()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        stop_scheduler()


def start_full_system():
    """Start both scheduler and dashboard."""
    try:
        logger.info("Starting full payroll monitoring system...")
        
        # Start scheduler in background
        import threading
        scheduler_thread = threading.Thread(target=start_monitoring_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Start dashboard (this blocks)
        start_dashboard()
        
    except KeyboardInterrupt:
        logger.info("Shutting down system...")
        stop_scheduler()
    except Exception as e:
        logger.error(f"System error: {e}")
        stop_scheduler()


def main():
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
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info(f"🚨 Payroll Monitoring System - {args.command.upper()}")
    
    success = False
    
    if args.command == 'init-db':
        success = init_database()
    
    elif args.command == 'load-data':
        if not init_database():
            logger.error("Database initialization failed")
            sys.exit(1)
        success = load_agency_data()
    
    elif args.command == 'monitor':
        success = asyncio.run(run_monitoring())
    
    elif args.command == 'test':
        success = asyncio.run(test_system())
    
    elif args.command == 'dashboard':
        success = start_dashboard()
    
    elif args.command == 'scheduler':
        success = start_monitoring_scheduler()
    
    elif args.command == 'start':
        # Initialize and load data if needed
        if not init_database():
            logger.error("Database initialization failed")
            sys.exit(1)
        
        with get_db() as db:
            if db.query(Agency).count() == 0:
                logger.info("No agencies found, loading data...")
                if not load_agency_data():
                    logger.error("Failed to load agency data")
                    sys.exit(1)
        
        success = start_full_system()
    
    if success:
        logger.info(f"Command '{args.command}' completed successfully!")
        sys.exit(0)
    else:
        logger.error(f"Command '{args.command}' failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()