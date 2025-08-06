"""
Advanced Export Scheduler with Automated Delivery

Provides sophisticated export scheduling capabilities including:
- Flexible scheduling with cron-like expressions
- Multiple delivery channels (email, FTP, cloud storage)
- Retry mechanisms and failure handling
- Performance monitoring and optimization
- Template-based export configurations
"""

import asyncio
import logging
import schedule
import time
import smtplib
import ftplib
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import tempfile
import shutil

# Cloud storage imports (optional)
try:
    import boto3
    from google.cloud import storage as gcs
    CLOUD_STORAGE_AVAILABLE = True
except ImportError:
    CLOUD_STORAGE_AVAILABLE = False

from sqlalchemy.orm import Session
from ..database.connection import get_db
from ..database.models import FormChange, Form, Agency
from ..utils.export_utils import ExportManager
from ..utils.bulk_export_manager import BulkExportManager

logger = logging.getLogger(__name__)


class SchedulePattern:
    """Represents a schedule pattern with cron-like functionality."""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
        self.parsed_pattern = self._parse_pattern(pattern)
    
    def _parse_pattern(self, pattern: str) -> Dict[str, Any]:
        """Parse cron-like pattern string."""
        # Support patterns like:
        # "daily at 09:00"
        # "weekly on monday at 10:30"
        # "monthly on 1st at 08:00"
        # "every 2 hours"
        # "weekdays at 14:00"
        
        pattern = pattern.lower().strip()
        parsed = {
            'type': 'unknown',
            'frequency': 1,
            'time': None,
            'day': None,
            'date': None
        }
        
        if 'daily' in pattern:
            parsed['type'] = 'daily'
            if 'at' in pattern:
                time_part = pattern.split('at')[1].strip()
                parsed['time'] = self._parse_time(time_part)
        
        elif 'weekly' in pattern:
            parsed['type'] = 'weekly'
            if 'on' in pattern and 'at' in pattern:
                parts = pattern.split('on')[1].split('at')
                parsed['day'] = parts[0].strip()
                parsed['time'] = self._parse_time(parts[1].strip())
        
        elif 'monthly' in pattern:
            parsed['type'] = 'monthly'
            if 'on' in pattern and 'at' in pattern:
                parts = pattern.split('on')[1].split('at')
                date_part = parts[0].strip()
                parsed['date'] = self._parse_date(date_part)
                parsed['time'] = self._parse_time(parts[1].strip())
        
        elif 'every' in pattern and 'hours' in pattern:
            parsed['type'] = 'hourly'
            # Extract number: "every 2 hours" -> 2
            try:
                num_part = pattern.split('every')[1].split('hours')[0].strip()
                parsed['frequency'] = int(num_part)
            except (ValueError, IndexError):
                parsed['frequency'] = 1
        
        elif 'weekdays' in pattern:
            parsed['type'] = 'weekdays'
            if 'at' in pattern:
                time_part = pattern.split('at')[1].strip()
                parsed['time'] = self._parse_time(time_part)
        
        return parsed
    
    def _parse_time(self, time_str: str) -> Optional[str]:
        """Parse time string like '09:00' or '2:30 PM'."""
        try:
            # Handle 24-hour format
            if ':' in time_str and len(time_str) <= 5:
                return time_str
            
            # Handle 12-hour format with AM/PM
            if 'pm' in time_str.lower() or 'am' in time_str.lower():
                # Convert to 24-hour format
                time_part = time_str.replace('am', '').replace('pm', '').replace('AM', '').replace('PM', '').strip()
                hour, minute = map(int, time_part.split(':'))
                
                if 'pm' in time_str.lower() and hour != 12:
                    hour += 12
                elif 'am' in time_str.lower() and hour == 12:
                    hour = 0
                
                return f"{hour:02d}:{minute:02d}"
        except:
            pass
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[int]:
        """Parse date string like '1st', '15th', etc."""
        try:
            # Extract number from ordinals
            import re
            match = re.search(r'\d+', date_str)
            if match:
                return int(match.group())
        except:
            pass
        
        return None
    
    def next_run_time(self, from_time: datetime = None) -> datetime:
        """Calculate next run time based on pattern."""
        if from_time is None:
            from_time = datetime.now()
        
        pattern = self.parsed_pattern
        
        if pattern['type'] == 'daily':
            next_run = from_time + timedelta(days=1)
            if pattern['time']:
                hour, minute = map(int, pattern['time'].split(':'))
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        elif pattern['type'] == 'weekly':
            days_ahead = 7
            if pattern['day']:
                day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                if pattern['day'] in day_names:
                    target_day = day_names.index(pattern['day'])
                    current_day = from_time.weekday()
                    days_ahead = (target_day - current_day) % 7
                    if days_ahead == 0:
                        days_ahead = 7
            
            next_run = from_time + timedelta(days=days_ahead)
            if pattern['time']:
                hour, minute = map(int, pattern['time'].split(':'))
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        elif pattern['type'] == 'monthly':
            # Simple monthly - add 30 days
            next_run = from_time + timedelta(days=30)
            if pattern['time']:
                hour, minute = map(int, pattern['time'].split(':'))
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        elif pattern['type'] == 'hourly':
            next_run = from_time + timedelta(hours=pattern['frequency'])
        
        elif pattern['type'] == 'weekdays':
            # Next weekday
            days_ahead = 1
            next_run = from_time + timedelta(days=days_ahead)
            while next_run.weekday() >= 5:  # Saturday = 5, Sunday = 6
                next_run += timedelta(days=1)
            
            if pattern['time']:
                hour, minute = map(int, pattern['time'].split(':'))
                next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        else:
            # Default to daily
            next_run = from_time + timedelta(days=1)
        
        return next_run


class DeliveryChannel:
    """Base class for delivery channels."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', 'unknown')
        self.enabled = config.get('enabled', True)
    
    async def deliver(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Deliver file through this channel."""
        raise NotImplementedError
    
    def validate_config(self) -> bool:
        """Validate channel configuration."""
        return True


class EmailDelivery(DeliveryChannel):
    """Email delivery channel."""
    
    def validate_config(self) -> bool:
        """Validate email configuration."""
        required_fields = ['smtp_server', 'smtp_port', 'username', 'password', 'recipients']
        return all(field in self.config for field in required_fields)
    
    async def deliver(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Send file via email."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config['username']
            msg['To'] = ', '.join(self.config['recipients'])
            msg['Subject'] = self._generate_subject(metadata)
            
            # Add body
            body = self._generate_email_body(metadata)
            msg.attach(MIMEText(body, 'html'))
            
            # Attach file
            with open(file_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {os.path.basename(file_path)}'
                )
                msg.attach(part)
            
            # Send email
            server = smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port'])
            if self.config.get('use_tls', True):
                server.starttls()
            
            server.login(self.config['username'], self.config['password'])
            server.sendmail(self.config['username'], self.config['recipients'], msg.as_string())
            server.quit()
            
            logger.info(f"Successfully sent export via email to {len(self.config['recipients'])} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Email delivery failed: {e}")
            return False
    
    def _generate_subject(self, metadata: Dict[str, Any]) -> str:
        """Generate email subject."""
        export_name = metadata.get('export_name', 'Compliance Export')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        return f"{export_name} - {timestamp}"
    
    def _generate_email_body(self, metadata: Dict[str, Any]) -> str:
        """Generate HTML email body."""
        return f"""
        <html>
        <body>
            <h2>Scheduled Compliance Export</h2>
            <p>Your scheduled export has been completed and is attached to this email.</p>
            
            <h3>Export Details:</h3>
            <ul>
                <li><strong>Export Name:</strong> {metadata.get('export_name', 'N/A')}</li>
                <li><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                <li><strong>Records:</strong> {metadata.get('record_count', 'N/A')}</li>
                <li><strong>Format:</strong> {metadata.get('format', 'N/A')}</li>
                <li><strong>File Size:</strong> {metadata.get('file_size', 'N/A')}</li>
            </ul>
            
            <p>This is an automated message from the Compliance Monitoring System.</p>
        </body>
        </html>
        """


class FTPDelivery(DeliveryChannel):
    """FTP delivery channel."""
    
    def validate_config(self) -> bool:
        """Validate FTP configuration."""
        required_fields = ['server', 'username', 'password', 'remote_path']
        return all(field in self.config for field in required_fields)
    
    async def deliver(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Upload file via FTP."""
        try:
            ftp = ftplib.FTP(self.config['server'])
            ftp.login(self.config['username'], self.config['password'])
            
            # Change to remote directory
            if self.config.get('remote_path'):
                ftp.cwd(self.config['remote_path'])
            
            # Upload file
            filename = os.path.basename(file_path)
            with open(file_path, 'rb') as file:
                ftp.storbinary(f'STOR {filename}', file)
            
            ftp.quit()
            
            logger.info(f"Successfully uploaded export to FTP: {self.config['server']}")
            return True
            
        except Exception as e:
            logger.error(f"FTP delivery failed: {e}")
            return False


class S3Delivery(DeliveryChannel):
    """Amazon S3 delivery channel."""
    
    def validate_config(self) -> bool:
        """Validate S3 configuration."""
        if not CLOUD_STORAGE_AVAILABLE:
            return False
        
        required_fields = ['aws_access_key', 'aws_secret_key', 'bucket_name']
        return all(field in self.config for field in required_fields)
    
    async def deliver(self, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Upload file to S3."""
        try:
            if not CLOUD_STORAGE_AVAILABLE:
                raise Exception("Cloud storage libraries not available")
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=self.config['aws_access_key'],
                aws_secret_access_key=self.config['aws_secret_key'],
                region_name=self.config.get('region', 'us-east-1')
            )
            
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y/%m/%d')
            filename = os.path.basename(file_path)
            s3_key = f"{self.config.get('prefix', 'exports')}/{timestamp}/{filename}"
            
            # Upload file
            s3_client.upload_file(file_path, self.config['bucket_name'], s3_key)
            
            logger.info(f"Successfully uploaded export to S3: s3://{self.config['bucket_name']}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"S3 delivery failed: {e}")
            return False


class ScheduledExport:
    """Represents a scheduled export with configuration and state."""
    
    def __init__(self, export_id: str, config: Dict[str, Any]):
        self.export_id = export_id
        self.config = config
        self.created_at = datetime.now()
        self.last_run = None
        self.next_run = None
        self.run_count = 0
        self.failure_count = 0
        self.status = 'active'
        self.last_error = None
        
        # Parse schedule pattern
        self.schedule_pattern = SchedulePattern(config.get('schedule', 'daily at 09:00'))
        self.next_run = self.schedule_pattern.next_run_time()
        
        # Setup delivery channels
        self.delivery_channels = []
        for channel_config in config.get('delivery_channels', []):
            channel = self._create_delivery_channel(channel_config)
            if channel and channel.validate_config():
                self.delivery_channels.append(channel)
    
    def _create_delivery_channel(self, config: Dict[str, Any]) -> Optional[DeliveryChannel]:
        """Create delivery channel from configuration."""
        channel_type = config.get('type', '').lower()
        
        if channel_type == 'email':
            return EmailDelivery(config)
        elif channel_type == 'ftp':
            return FTPDelivery(config)
        elif channel_type == 's3':
            return S3Delivery(config)
        else:
            logger.warning(f"Unknown delivery channel type: {channel_type}")
            return None
    
    def is_due(self) -> bool:
        """Check if export is due to run."""
        return self.next_run and datetime.now() >= self.next_run and self.status == 'active'
    
    def update_next_run(self):
        """Update next run time after execution."""
        self.next_run = self.schedule_pattern.next_run_time()
    
    def record_success(self):
        """Record successful execution."""
        self.last_run = datetime.now()
        self.run_count += 1
        self.failure_count = 0
        self.last_error = None
        self.update_next_run()
    
    def record_failure(self, error: str):
        """Record failed execution."""
        self.last_run = datetime.now()
        self.failure_count += 1
        self.last_error = error
        
        # Disable if too many failures
        if self.failure_count >= 5:
            self.status = 'disabled'
            logger.error(f"Disabled scheduled export {self.export_id} due to repeated failures")
        else:
            self.update_next_run()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            'export_id': self.export_id,
            'config': self.config,
            'created_at': self.created_at,
            'last_run': self.last_run,
            'next_run': self.next_run,
            'run_count': self.run_count,
            'failure_count': self.failure_count,
            'status': self.status,
            'last_error': self.last_error,
            'delivery_channels': len(self.delivery_channels)
        }


class AdvancedExportScheduler:
    """Advanced export scheduler with automated delivery."""
    
    def __init__(self):
        self.export_manager = ExportManager()
        self.bulk_export_manager = BulkExportManager()
        self.scheduled_exports: Dict[str, ScheduledExport] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=3)
        self._scheduler_thread = None
        self._stop_event = threading.Event()
        
        # Templates for common export configurations
        self.export_templates = self._load_export_templates()
        
        logger.info("Advanced Export Scheduler initialized")
    
    def _load_export_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load predefined export templates."""
        return {
            'daily_summary': {
                'name': 'Daily Compliance Summary',
                'description': 'Daily summary of compliance changes',
                'export_config': {
                    'data_source': 'form_changes',
                    'filters': {
                        'date_range': '24h'
                    },
                    'format': 'pdf',
                    'include_summary': True
                }
            },
            'weekly_detailed': {
                'name': 'Weekly Detailed Report',
                'description': 'Comprehensive weekly compliance report',
                'export_config': {
                    'data_source': 'form_changes',
                    'filters': {
                        'date_range': '7d'
                    },
                    'format': 'excel',
                    'include_charts': True
                }
            },
            'monthly_archive': {
                'name': 'Monthly Data Archive',
                'description': 'Complete monthly data export',
                'export_config': {
                    'data_source': 'form_changes',
                    'filters': {
                        'date_range': '30d'
                    },
                    'format': 'csv',
                    'include_all_fields': True
                }
            }
        }
    
    def start(self):
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self._stop_event.clear()
        
        # Start scheduler thread
        self._scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._scheduler_thread.start()
        
        logger.info("Advanced Export Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5.0)
        
        self.executor.shutdown(wait=True)
        logger.info("Advanced Export Scheduler stopped")
    
    def _run_scheduler(self):
        """Main scheduler loop."""
        while self.running and not self._stop_event.is_set():
            try:
                self._check_due_exports()
                # Check every minute
                self._stop_event.wait(60)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                self._stop_event.wait(60)
    
    def _check_due_exports(self):
        """Check for due exports and execute them."""
        due_exports = [export for export in self.scheduled_exports.values() if export.is_due()]
        
        if due_exports:
            logger.info(f"Found {len(due_exports)} due exports")
            
            # Submit due exports to thread pool
            futures = []
            for export in due_exports:
                future = self.executor.submit(self._execute_scheduled_export, export)
                futures.append(future)
            
            # Wait for completion (optional)
            for future in as_completed(futures, timeout=300):  # 5 minute timeout
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Export execution failed: {e}")
    
    def _execute_scheduled_export(self, scheduled_export: ScheduledExport):
        """Execute a scheduled export."""
        export_id = scheduled_export.export_id
        logger.info(f"Executing scheduled export: {export_id}")
        
        try:
            # Generate export based on configuration
            file_path = self._generate_export(scheduled_export)
            
            if file_path and os.path.exists(file_path):
                # Deliver through all configured channels
                metadata = self._generate_metadata(scheduled_export, file_path)
                delivery_success = self._deliver_export(scheduled_export, file_path, metadata)
                
                if delivery_success:
                    scheduled_export.record_success()
                    logger.info(f"Successfully completed scheduled export: {export_id}")
                else:
                    scheduled_export.record_failure("Delivery failed")
                    logger.error(f"Delivery failed for scheduled export: {export_id}")
                
                # Cleanup temporary file
                try:
                    os.unlink(file_path)
                except:
                    pass
            else:
                scheduled_export.record_failure("Export generation failed")
                logger.error(f"Export generation failed for: {export_id}")
        
        except Exception as e:
            scheduled_export.record_failure(str(e))
            logger.error(f"Scheduled export {export_id} failed: {e}")
    
    def _generate_export(self, scheduled_export: ScheduledExport) -> Optional[str]:
        """Generate export file based on configuration."""
        try:
            config = scheduled_export.config
            export_config = config.get('export_config', {})
            
            # Fetch data based on configuration
            with get_db() as db:
                data = self._fetch_export_data(export_config, db)
            
            if not data:
                logger.warning(f"No data found for scheduled export: {scheduled_export.export_id}")
                return None
            
            # Generate export using export manager
            format_type = export_config.get('format', 'csv')
            export_content = self.export_manager.export_data(
                data=data,
                format_type=format_type,
                export_config=export_config
            )
            
            # Save to temporary file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = self.export_manager.get_export_metadata(format_type)['extension']
            filename = f"scheduled_export_{scheduled_export.export_id}_{timestamp}{ext}"
            
            temp_dir = Path(tempfile.gettempdir()) / "scheduled_exports"
            temp_dir.mkdir(exist_ok=True)
            
            file_path = temp_dir / filename
            
            if format_type == 'csv':
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(export_content)
            
            return str(file_path)
        
        except Exception as e:
            logger.error(f"Export generation failed: {e}")
            return None
    
    def _fetch_export_data(self, export_config: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """Fetch data for export based on configuration."""
        data_source = export_config.get('data_source', 'form_changes')
        
        if data_source == 'form_changes':
            return self._fetch_form_changes_data(export_config, db)
        elif data_source == 'agencies':
            return self._fetch_agencies_data(export_config, db)
        elif data_source == 'forms':
            return self._fetch_forms_data(export_config, db)
        else:
            return []
    
    def _fetch_form_changes_data(self, config: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """Fetch form changes data."""
        query = db.query(FormChange)
        
        # Apply filters
        filters = config.get('filters', {})
        
        if 'date_range' in filters:
            date_range = filters['date_range']
            now = datetime.now()
            
            if date_range == '24h':
                cutoff = now - timedelta(hours=24)
            elif date_range == '7d':
                cutoff = now - timedelta(days=7)
            elif date_range == '30d':
                cutoff = now - timedelta(days=30)
            else:
                cutoff = now - timedelta(days=1)
            
            query = query.filter(FormChange.detected_at >= cutoff)
        
        if 'severity' in filters:
            query = query.filter(FormChange.severity.in_(filters['severity']))
        
        # Execute query and convert to dict
        changes = query.limit(10000).all()  # Limit for scheduled exports
        
        export_data = []
        for change in changes:
            export_data.append({
                'id': change.id,
                'form_name': change.form.name if change.form else 'Unknown',
                'agency_name': change.form.agency.name if change.form and change.form.agency else 'Unknown',
                'change_type': change.change_type,
                'severity': change.severity,
                'status': change.status,
                'detected_at': change.detected_at,
                'description': change.description,
                'url': change.url
            })
        
        return export_data
    
    def _fetch_agencies_data(self, config: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """Fetch agencies data."""
        agencies = db.query(Agency).filter(Agency.is_active == True).all()
        
        return [{
            'id': agency.id,
            'name': agency.name,
            'agency_type': agency.agency_type,
            'base_url': agency.base_url,
            'contact_email': agency.contact_email
        } for agency in agencies]
    
    def _fetch_forms_data(self, config: Dict[str, Any], db: Session) -> List[Dict[str, Any]]:
        """Fetch forms data."""
        forms = db.query(Form).filter(Form.is_active == True).all()
        
        return [{
            'id': form.id,
            'name': form.name,
            'agency_name': form.agency.name if form.agency else 'Unknown',
            'form_url': form.form_url,
            'check_frequency': form.check_frequency,
            'last_checked': form.last_checked
        } for form in forms]
    
    def _generate_metadata(self, scheduled_export: ScheduledExport, file_path: str) -> Dict[str, Any]:
        """Generate metadata for delivery."""
        file_size = os.path.getsize(file_path)
        
        return {
            'export_id': scheduled_export.export_id,
            'export_name': scheduled_export.config.get('name', 'Scheduled Export'),
            'format': scheduled_export.config.get('export_config', {}).get('format', 'csv'),
            'file_size': f"{file_size / 1024 / 1024:.2f} MB",
            'record_count': 'N/A',  # Could be calculated if needed
            'generated_at': datetime.now().isoformat()
        }
    
    def _deliver_export(self, scheduled_export: ScheduledExport, file_path: str, metadata: Dict[str, Any]) -> bool:
        """Deliver export through configured channels."""
        if not scheduled_export.delivery_channels:
            logger.warning(f"No delivery channels configured for export: {scheduled_export.export_id}")
            return False
        
        success_count = 0
        
        for channel in scheduled_export.delivery_channels:
            try:
                if asyncio.run(channel.deliver(file_path, metadata)):
                    success_count += 1
            except Exception as e:
                logger.error(f"Delivery failed for channel {channel.name}: {e}")
        
        return success_count > 0
    
    def schedule_export(self, export_config: Dict[str, Any]) -> str:
        """Schedule a new export."""
        export_id = f"export_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        scheduled_export = ScheduledExport(export_id, export_config)
        self.scheduled_exports[export_id] = scheduled_export
        
        logger.info(f"Scheduled export {export_id} with pattern: {export_config.get('schedule', 'daily')}")
        return export_id
    
    def get_scheduled_exports(self) -> Dict[str, Dict[str, Any]]:
        """Get all scheduled exports."""
        return {
            export_id: export.to_dict() 
            for export_id, export in self.scheduled_exports.items()
        }
    
    def get_export_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get available export templates."""
        return self.export_templates
    
    def cancel_scheduled_export(self, export_id: str) -> bool:
        """Cancel a scheduled export."""
        if export_id in self.scheduled_exports:
            del self.scheduled_exports[export_id]
            logger.info(f"Cancelled scheduled export: {export_id}")
            return True
        return False
    
    def update_scheduled_export(self, export_id: str, config: Dict[str, Any]) -> bool:
        """Update a scheduled export configuration."""
        if export_id in self.scheduled_exports:
            # Create new scheduled export with updated config
            self.scheduled_exports[export_id] = ScheduledExport(export_id, config)
            logger.info(f"Updated scheduled export: {export_id}")
            return True
        return False
    
    def get_export_history(self, export_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get export execution history."""
        history = []
        
        for eid, export in self.scheduled_exports.items():
            if export_id and eid != export_id:
                continue
                
            if export.last_run:
                history.append({
                    'export_id': eid,
                    'export_name': export.config.get('name', 'Unnamed'),
                    'last_run': export.last_run,
                    'run_count': export.run_count,
                    'status': 'success' if export.failure_count == 0 else 'failed',
                    'last_error': export.last_error
                })
        
        # Sort by last run time
        history.sort(key=lambda x: x['last_run'] or datetime.min, reverse=True)
        return history[:limit]


# Global scheduler instance
advanced_export_scheduler = AdvancedExportScheduler()