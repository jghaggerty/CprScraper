"""
Bulk Export Manager for Large Datasets

Provides advanced bulk export capabilities with chunking, streaming,
progress tracking, and resource management for large compliance datasets.
"""

import asyncio
import os
import tempfile
import zipfile
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from pathlib import Path
import logging
import json
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from .export_utils import ExportManager

logger = logging.getLogger(__name__)


class BulkExportConfig:
    """Configuration for bulk export operations."""
    
    def __init__(self):
        self.chunk_size = 5000  # Records per chunk
        self.max_concurrent_exports = 3  # Maximum concurrent export jobs
        self.memory_limit_mb = 512  # Memory limit per export job
        self.streaming_threshold = 50000  # Use streaming for datasets larger than this
        self.temp_retention_hours = 48  # How long to keep temporary files
        self.compression_level = 6  # ZIP compression level (0-9)
        
        # Format-specific limits for bulk operations
        self.format_limits = {
            'csv': {
                'max_records_per_file': 1000000,
                'max_file_size_mb': 200,
                'supports_streaming': True
            },
            'excel': {
                'max_records_per_file': 100000,
                'max_file_size_mb': 100,
                'supports_streaming': False
            },
            'pdf': {
                'max_records_per_file': 5000,
                'max_file_size_mb': 50,
                'supports_streaming': False
            }
        }


class BulkExportJob:
    """Represents a bulk export job with progress tracking."""
    
    def __init__(self, job_id: str, config: BulkExportConfig):
        self.job_id = job_id
        self.config = config
        self.status = "pending"
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.expires_at = datetime.now() + timedelta(hours=config.temp_retention_hours)
        
        # Progress tracking
        self.total_records = 0
        self.processed_records = 0
        self.current_chunk = 0
        self.total_chunks = 0
        self.progress_percent = 0
        
        # File management
        self.temp_directory: Optional[Path] = None
        self.output_files: List[str] = []
        self.final_archive_path: Optional[str] = None
        
        # Error handling
        self.error_message: Optional[str] = None
        self.warnings: List[str] = []
        
        # Resource tracking
        self.memory_usage_mb = 0
        self.disk_usage_mb = 0
    
    def update_progress(self, processed: int = None, current_chunk: int = None):
        """Update job progress."""
        if processed is not None:
            self.processed_records = processed
        if current_chunk is not None:
            self.current_chunk = current_chunk
        
        if self.total_records > 0:
            self.progress_percent = min(100, int((self.processed_records / self.total_records) * 100))
    
    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(f"{datetime.now().isoformat()}: {message}")
        logger.warning(f"Bulk export {self.job_id}: {message}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API responses."""
        return {
            'job_id': self.job_id,
            'status': self.status,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'expires_at': self.expires_at,
            'total_records': self.total_records,
            'processed_records': self.processed_records,
            'current_chunk': self.current_chunk,
            'total_chunks': self.total_chunks,
            'progress_percent': self.progress_percent,
            'output_files': self.output_files,
            'final_archive_path': self.final_archive_path,
            'error_message': self.error_message,
            'warnings': self.warnings,
            'memory_usage_mb': self.memory_usage_mb,
            'disk_usage_mb': self.disk_usage_mb
        }


class StreamingExporter:
    """Handles streaming export for very large datasets."""
    
    def __init__(self, export_manager: ExportManager, config: BulkExportConfig):
        self.export_manager = export_manager
        self.config = config
    
    async def stream_csv_export(
        self,
        query_func,
        job: BulkExportJob,
        export_config: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Stream CSV export with chunked processing."""
        try:
            with open(output_path, 'w', encoding='utf-8', newline='') as csv_file:
                header_written = False
                chunk_offset = 0
                
                while True:
                    # Fetch chunk of data
                    chunk_data = await query_func(
                        limit=self.config.chunk_size,
                        offset=chunk_offset
                    )
                    
                    if not chunk_data:
                        break
                    
                    # Convert chunk to CSV
                    if chunk_data:
                        chunk_csv = self.export_manager._export_csv(
                            chunk_data, 
                            export_config, 
                            f"chunk_{chunk_offset}"
                        )
                        
                        # Write header only once
                        if not header_written:
                            csv_file.write(chunk_csv)
                            header_written = True
                        else:
                            # Skip header line for subsequent chunks
                            lines = chunk_csv.split('\n')
                            if len(lines) > 1:
                                csv_file.write('\n'.join(lines[1:]))
                        
                        csv_file.flush()
                    
                    # Update progress
                    job.processed_records += len(chunk_data)
                    job.update_progress()
                    
                    chunk_offset += self.config.chunk_size
                    
                    # Check if we've reached the end
                    if len(chunk_data) < self.config.chunk_size:
                        break
        
        except Exception as e:
            logger.error(f"Streaming CSV export failed: {e}")
            raise
    
    async def stream_excel_chunks(
        self,
        query_func,
        job: BulkExportJob,
        export_config: Dict[str, Any],
        output_dir: Path
    ) -> List[str]:
        """Create multiple Excel files for large datasets."""
        excel_files = []
        chunk_offset = 0
        file_index = 1
        
        max_records_per_file = self.config.format_limits['excel']['max_records_per_file']
        
        while True:
            # Determine how many records to fetch for this file
            records_for_file = min(max_records_per_file, 
                                 job.total_records - chunk_offset)
            
            if records_for_file <= 0:
                break
            
            # Fetch data for this Excel file
            file_data = []
            records_fetched = 0
            
            while records_fetched < records_for_file:
                chunk_limit = min(self.config.chunk_size, 
                                records_for_file - records_fetched)
                
                chunk_data = await query_func(
                    limit=chunk_limit,
                    offset=chunk_offset + records_fetched
                )
                
                if not chunk_data:
                    break
                
                file_data.extend(chunk_data)
                records_fetched += len(chunk_data)
                
                if len(chunk_data) < chunk_limit:
                    break
            
            if file_data:
                # Generate Excel file for this chunk
                excel_content = self.export_manager._export_excel(
                    file_data,
                    export_config,
                    f"bulk_export_part_{file_index}.xlsx"
                )
                
                # Save Excel file
                excel_path = output_dir / f"bulk_export_part_{file_index}.xlsx"
                with open(excel_path, 'wb') as f:
                    f.write(excel_content)
                
                excel_files.append(str(excel_path))
                
                # Update progress
                job.processed_records += len(file_data)
                job.update_progress()
                
                file_index += 1
                chunk_offset += records_fetched
            else:
                break
        
        return excel_files


class BulkExportManager:
    """Manages bulk export operations for large datasets."""
    
    def __init__(self):
        self.config = BulkExportConfig()
        self.export_manager = ExportManager()
        self.streaming_exporter = StreamingExporter(self.export_manager, self.config)
        self.active_jobs: Dict[str, BulkExportJob] = {}
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_exports)
    
    def create_bulk_export_job(
        self,
        export_requests: List[Dict[str, Any]],
        combined_output: bool = False,
        archive_format: str = "zip"
    ) -> BulkExportJob:
        """Create a new bulk export job."""
        job_id = f"bulk_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        job = BulkExportJob(job_id, self.config)
        
        # Create temporary directory for this job
        job.temp_directory = Path(tempfile.mkdtemp(prefix=f"bulk_export_{job_id}_"))
        
        self.active_jobs[job_id] = job
        
        logger.info(f"Created bulk export job {job_id} with {len(export_requests)} exports")
        return job
    
    async def estimate_bulk_export_size(
        self,
        export_requests: List[Dict[str, Any]],
        db: Session
    ) -> Tuple[int, float, Dict[str, Any]]:
        """Estimate total records and size for bulk export."""
        total_records = 0
        total_size_mb = 0.0
        breakdown = {}
        
        for i, request in enumerate(export_requests):
            # Simplified estimation - in production, this would use the actual query
            estimated_records = await self._estimate_request_size(request, db)
            
            format_type = request.get('customization', {}).get('format', 'csv')
            bytes_per_record = self._get_bytes_per_record(format_type)
            size_mb = (estimated_records * bytes_per_record) / (1024 * 1024)
            
            total_records += estimated_records
            total_size_mb += size_mb
            
            breakdown[f"export_{i+1}"] = {
                'records': estimated_records,
                'size_mb': size_mb,
                'format': format_type
            }
        
        return total_records, total_size_mb, breakdown
    
    async def process_bulk_export(
        self,
        job_id: str,
        export_requests: List[Dict[str, Any]],
        db: Session,
        combined_output: bool = False
    ) -> None:
        """Process a bulk export job asynchronously."""
        if job_id not in self.active_jobs:
            raise ValueError(f"Job {job_id} not found")
        
        job = self.active_jobs[job_id]
        
        try:
            job.status = "processing"
            job.started_at = datetime.now()
            
            # Estimate total work
            await self._estimate_job_size(job, export_requests, db)
            
            # Process each export request
            export_files = []
            
            for i, request in enumerate(export_requests):
                job.add_warning(f"Processing export {i+1} of {len(export_requests)}")
                
                # Determine if we need streaming based on size
                estimated_records = await self._estimate_request_size(request, db)
                format_type = request.get('customization', {}).get('format', 'csv')
                
                if self._should_use_streaming(estimated_records, format_type):
                    files = await self._process_streaming_export(job, request, db, i+1)
                else:
                    files = await self._process_standard_export(job, request, db, i+1)
                
                export_files.extend(files)
            
            # Create final output
            if combined_output and len(export_files) > 1:
                job.final_archive_path = await self._create_combined_archive(job, export_files)
            elif len(export_files) == 1:
                job.final_archive_path = export_files[0]
            else:
                job.final_archive_path = await self._create_archive(job, export_files)
            
            # Cleanup individual files if we created an archive
            if job.final_archive_path != export_files[0]:
                for file_path in export_files:
                    try:
                        os.unlink(file_path)
                    except OSError:
                        pass
            
            job.status = "completed"
            job.completed_at = datetime.now()
            job.progress_percent = 100
            
            logger.info(f"Bulk export job {job_id} completed successfully")
        
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now()
            logger.error(f"Bulk export job {job_id} failed: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[BulkExportJob]:
        """Get the status of a bulk export job."""
        return self.active_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a bulk export job and cleanup resources."""
        if job_id not in self.active_jobs:
            return False
        
        job = self.active_jobs[job_id]
        job.status = "cancelled"
        
        # Cleanup temporary files
        if job.temp_directory and job.temp_directory.exists():
            try:
                shutil.rmtree(job.temp_directory)
            except OSError as e:
                logger.warning(f"Failed to cleanup temp directory for job {job_id}: {e}")
        
        del self.active_jobs[job_id]
        logger.info(f"Cancelled bulk export job {job_id}")
        return True
    
    def cleanup_expired_jobs(self) -> int:
        """Cleanup expired jobs and their files."""
        now = datetime.now()
        expired_jobs = []
        
        for job_id, job in self.active_jobs.items():
            if now > job.expires_at:
                expired_jobs.append(job_id)
        
        for job_id in expired_jobs:
            self.cancel_job(job_id)
        
        return len(expired_jobs)
    
    async def _estimate_job_size(
        self,
        job: BulkExportJob,
        export_requests: List[Dict[str, Any]],
        db: Session
    ) -> None:
        """Estimate the total size of the bulk export job."""
        total_records = 0
        
        for request in export_requests:
            records = await self._estimate_request_size(request, db)
            total_records += records
        
        job.total_records = total_records
        job.total_chunks = (total_records + self.config.chunk_size - 1) // self.config.chunk_size
    
    async def _estimate_request_size(self, request: Dict[str, Any], db: Session) -> int:
        """Estimate the number of records for a single export request."""
        # Simplified estimation - in production, this would build and count the actual query
        data_source = request.get('data_source', 'form_changes')
        
        if data_source == 'form_changes':
            return db.execute(text("SELECT COUNT(*) FROM form_changes")).scalar() or 0
        elif data_source == 'agencies':
            return db.execute(text("SELECT COUNT(*) FROM agencies")).scalar() or 0
        elif data_source == 'forms':
            return db.execute(text("SELECT COUNT(*) FROM forms")).scalar() or 0
        else:
            return 1000  # Default estimate
    
    def _should_use_streaming(self, estimated_records: int, format_type: str) -> bool:
        """Determine if streaming should be used for this export."""
        if estimated_records > self.config.streaming_threshold:
            return True
        
        format_limits = self.config.format_limits.get(format_type, {})
        max_records = format_limits.get('max_records_per_file', float('inf'))
        
        return estimated_records > max_records
    
    async def _process_streaming_export(
        self,
        job: BulkExportJob,
        request: Dict[str, Any],
        db: Session,
        export_index: int
    ) -> List[str]:
        """Process an export using streaming for large datasets."""
        format_type = request.get('customization', {}).get('format', 'csv')
        
        if format_type == 'csv':
            return await self._process_streaming_csv(job, request, db, export_index)
        elif format_type == 'excel':
            return await self._process_streaming_excel(job, request, db, export_index)
        else:
            # Fallback to standard export for other formats
            return await self._process_standard_export(job, request, db, export_index)
    
    async def _process_streaming_csv(
        self,
        job: BulkExportJob,
        request: Dict[str, Any],
        db: Session,
        export_index: int
    ) -> List[str]:
        """Process a streaming CSV export."""
        output_path = job.temp_directory / f"export_{export_index}.csv"
        
        # Create a query function for streaming
        async def query_func(limit: int, offset: int):
            # This would be replaced with actual query logic
            # For now, return empty to demonstrate structure
            return []
        
        export_config = self._build_export_config(request)
        
        await self.streaming_exporter.stream_csv_export(
            query_func, job, export_config, output_path
        )
        
        return [str(output_path)]
    
    async def _process_streaming_excel(
        self,
        job: BulkExportJob,
        request: Dict[str, Any],
        db: Session,
        export_index: int
    ) -> List[str]:
        """Process a streaming Excel export (creates multiple files)."""
        output_dir = job.temp_directory / f"excel_export_{export_index}"
        output_dir.mkdir(exist_ok=True)
        
        # Create a query function for streaming
        async def query_func(limit: int, offset: int):
            # This would be replaced with actual query logic
            return []
        
        export_config = self._build_export_config(request)
        
        excel_files = await self.streaming_exporter.stream_excel_chunks(
            query_func, job, export_config, output_dir
        )
        
        return excel_files
    
    async def _process_standard_export(
        self,
        job: BulkExportJob,
        request: Dict[str, Any],
        db: Session,
        export_index: int
    ) -> List[str]:
        """Process a standard export (load all data into memory)."""
        # This would use the existing export logic for smaller datasets
        format_type = request.get('customization', {}).get('format', 'csv')
        output_path = job.temp_directory / f"export_{export_index}.{format_type}"
        
        # Placeholder - would fetch actual data and use export_manager
        data = []  # Fetch data based on request
        export_config = self._build_export_config(request)
        
        if data:
            export_content = self.export_manager.export_data(
                data=data,
                format_type=format_type,
                export_config=export_config
            )
            
            # Write to file
            if format_type == 'csv':
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(export_content)
            else:
                with open(output_path, 'wb') as f:
                    f.write(export_content)
        
        job.processed_records += len(data)
        job.update_progress()
        
        return [str(output_path)]
    
    async def _create_combined_archive(
        self,
        job: BulkExportJob,
        file_paths: List[str]
    ) -> str:
        """Create a combined archive from multiple export files."""
        archive_path = job.temp_directory / f"combined_export_{job.job_id}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED,
                           compresslevel=self.config.compression_level) as zipf:
            for file_path in file_paths:
                if os.path.exists(file_path):
                    # Use just the filename in the archive
                    arcname = os.path.basename(file_path)
                    zipf.write(file_path, arcname)
        
        return str(archive_path)
    
    async def _create_archive(
        self,
        job: BulkExportJob,
        file_paths: List[str]
    ) -> str:
        """Create an archive from export files."""
        if len(file_paths) == 1:
            return file_paths[0]
        
        return await self._create_combined_archive(job, file_paths)
    
    def _build_export_config(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Build export configuration from request."""
        customization = request.get('customization', {})
        return {
            'columns': customization.get('columns'),
            'include_headers': customization.get('include_headers', True),
            'include_metadata': customization.get('include_metadata', True),
            'date_format': customization.get('date_format', '%Y-%m-%d %H:%M:%S'),
            'timezone': customization.get('timezone', 'UTC')
        }
    
    def _get_bytes_per_record(self, format_type: str) -> int:
        """Get estimated bytes per record for different formats."""
        bytes_per_record_map = {
            'csv': 200,
            'excel': 300,
            'pdf': 500
        }
        return bytes_per_record_map.get(format_type, 250)


# Global bulk export manager instance
bulk_export_manager = BulkExportManager()