"""
Enhanced Data Export API Endpoints

Provides comprehensive data export functionality with advanced filtering,
customization options, and multiple data sources for compliance monitoring.
"""

import io
import tempfile
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc
from pydantic import BaseModel, Field, field_validator

from ..database.connection import get_db
from ..database.models import FormChange, Form, Agency, MonitoringRun, Notification
from ..utils.export_utils import ExportManager, ExportScheduler
from ..utils.bulk_export_manager import BulkExportManager, bulk_export_manager
from ..scheduler.advanced_export_scheduler import AdvancedExportScheduler, advanced_export_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/data-export", tags=["data-export"])

# Initialize export components
export_manager = ExportManager()
export_scheduler = ExportScheduler(export_manager)


class AdvancedFilterRequest(BaseModel):
    """Advanced filtering options for data export."""
    
    # Date filtering
    date_from: Optional[str] = Field(None, description="Start date (ISO format)")
    date_to: Optional[str] = Field(None, description="End date (ISO format)")
    date_range: Optional[str] = Field(None, description="Predefined range: 24h, 7d, 30d, 90d, 1y")
    
    # Entity filtering
    agency_ids: Optional[List[int]] = Field(None, description="List of agency IDs")
    agency_names: Optional[List[str]] = Field(None, description="List of agency names")
    agency_types: Optional[List[str]] = Field(None, description="federal, state, local")
    form_ids: Optional[List[int]] = Field(None, description="List of form IDs")
    form_names: Optional[List[str]] = Field(None, description="List of form names")
    
    # Change characteristics
    severities: Optional[List[str]] = Field(None, description="low, medium, high, critical")
    statuses: Optional[List[str]] = Field(None, description="detected, reviewed, resolved, etc.")
    change_types: Optional[List[str]] = Field(None, description="form_update, field_change, etc.")
    
    # AI analysis filtering
    ai_confidence_min: Optional[int] = Field(None, ge=0, le=100, description="Minimum AI confidence score")
    ai_confidence_max: Optional[int] = Field(None, ge=0, le=100, description="Maximum AI confidence score")
    ai_categories: Optional[List[str]] = Field(None, description="AI change categories")
    include_cosmetic: Optional[bool] = Field(True, description="Include cosmetic changes")
    
    # Content filtering
    description_contains: Optional[str] = Field(None, description="Text search in descriptions")
    url_contains: Optional[str] = Field(None, description="Text search in URLs")
    
    # Sorting and pagination
    sort_by: Optional[str] = Field("detected_at", description="Field to sort by")
    sort_order: Optional[str] = Field("desc", description="asc or desc")
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Maximum records to return")
    offset: Optional[int] = Field(0, ge=0, description="Number of records to skip")


class ExportCustomization(BaseModel):
    """Customization options for export output."""
    
    # Format options
    format: str = Field(..., description="Export format: csv, excel, pdf")
    filename: Optional[str] = Field(None, description="Custom filename")
    
    # Column selection
    columns: Optional[List[str]] = Field(None, description="Specific columns to include")
    include_headers: bool = Field(True, description="Include column headers")
    include_metadata: bool = Field(True, description="Include export metadata")
    
    # Content options
    include_ai_analysis: bool = Field(True, description="Include AI analysis fields")
    include_impact_assessment: bool = Field(True, description="Include impact assessment")
    include_related_data: bool = Field(False, description="Include related form and agency data")
    
    # Formatting options
    date_format: Optional[str] = Field("%Y-%m-%d %H:%M:%S", description="Date format string")
    timezone: Optional[str] = Field("UTC", description="Timezone for dates")
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v):
        if v not in ['csv', 'excel', 'pdf']:
            raise ValueError('Format must be csv, excel, or pdf')
        return v


class DataExportRequest(BaseModel):
    """Complete data export request."""
    filters: Optional[AdvancedFilterRequest] = None
    customization: ExportCustomization
    data_source: Optional[str] = Field("form_changes", description="Data source to export")


class ExportJobResponse(BaseModel):
    """Response for export job creation."""
    job_id: str
    status: str
    estimated_records: int
    estimated_size_mb: float
    download_url: Optional[str] = None
    expires_at: datetime
    created_at: datetime


class ExportStatusResponse(BaseModel):
    """Response for export job status."""
    job_id: str
    status: str  # pending, processing, completed, failed, expired
    progress_percent: Optional[int] = None
    records_processed: Optional[int] = None
    total_records: Optional[int] = None
    file_size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: datetime


class BulkExportRequest(BaseModel):
    """Request for bulk export with multiple data sources."""
    exports: List[DataExportRequest]
    combined_output: bool = Field(False, description="Combine all exports into single file")
    archive_format: Optional[str] = Field("zip", description="Archive format for multiple files")
    use_streaming: Optional[bool] = Field(None, description="Force streaming mode for large datasets")
    chunk_size: Optional[int] = Field(5000, ge=1000, le=50000, description="Records per chunk for streaming")


class LargeBulkExportRequest(BaseModel):
    """Request for very large bulk exports with advanced options."""
    exports: List[DataExportRequest]
    max_records_per_file: Optional[int] = Field(100000, description="Maximum records per output file")
    compression_level: Optional[int] = Field(6, ge=0, le=9, description="Compression level for archives")
    priority: Optional[str] = Field("normal", description="Job priority: low, normal, high")
    notification_email: Optional[str] = Field(None, description="Email for completion notification")


class DeliveryChannelConfig(BaseModel):
    """Configuration for delivery channels."""
    type: str = Field(..., description="Channel type: email, ftp, s3")
    name: str = Field(..., description="Channel name")
    enabled: bool = Field(True, description="Whether channel is enabled")
    
    # Email settings
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    recipients: Optional[List[str]] = None
    use_tls: Optional[bool] = True
    
    # FTP settings
    server: Optional[str] = None
    remote_path: Optional[str] = None
    
    # S3 settings
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    bucket_name: Optional[str] = None
    region: Optional[str] = None
    prefix: Optional[str] = None


class AdvancedScheduleRequest(BaseModel):
    """Request for advanced export scheduling."""
    name: str = Field(..., description="Schedule name")
    description: Optional[str] = Field(None, description="Schedule description")
    schedule: str = Field(..., description="Schedule pattern (e.g., 'daily at 09:00', 'weekly on monday at 10:30')")
    export_config: DataExportRequest = Field(..., description="Export configuration")
    delivery_channels: List[DeliveryChannelConfig] = Field(..., description="Delivery channels")
    enabled: bool = Field(True, description="Whether schedule is active")
    template_name: Optional[str] = Field(None, description="Use predefined template")


class ScheduleUpdateRequest(BaseModel):
    """Request for updating scheduled exports."""
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    export_config: Optional[DataExportRequest] = None
    delivery_channels: Optional[List[DeliveryChannelConfig]] = None
    enabled: Optional[bool] = None


class ScheduledExportResponse(BaseModel):
    """Response for scheduled export operations."""
    export_id: str
    name: str
    description: Optional[str] = None
    schedule: str
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int
    failure_count: int
    status: str
    created_at: datetime
    delivery_channels: int


class ExportHistoryResponse(BaseModel):
    """Response for export history."""
    export_id: str
    export_name: str
    last_run: datetime
    run_count: int
    status: str
    last_error: Optional[str] = None


# Global export job storage (in production, use Redis or database)
export_jobs: Dict[str, Dict] = {}


@router.get("/formats")
async def get_export_formats():
    """Get available export formats with their capabilities."""
    try:
        formats = export_manager.get_supported_formats()
        
        # Add additional metadata for each format
        for format_info in formats:
            if format_info['format'] == 'csv':
                format_info.update({
                    'max_records': 100000,
                    'supports_multiple_sheets': False,
                    'supports_charts': False,
                    'supports_formatting': False
                })
            elif format_info['format'] == 'excel':
                format_info.update({
                    'max_records': 50000,
                    'supports_multiple_sheets': True,
                    'supports_charts': True,
                    'supports_formatting': True
                })
            elif format_info['format'] == 'pdf':
                format_info.update({
                    'max_records': 1000,
                    'supports_multiple_sheets': False,
                    'supports_charts': True,
                    'supports_formatting': True
                })
        
        return {
            "formats": formats,
            "default_format": "csv",
            "max_file_size_mb": 100
        }
    except Exception as e:
        logger.error(f"Error getting export formats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve export formats")


@router.get("/data-sources")
async def get_available_data_sources():
    """Get available data sources for export."""
    return {
        "data_sources": [
            {
                "name": "form_changes",
                "description": "Compliance form changes and modifications",
                "available_columns": [
                    "id", "form_name", "agency_name", "agency_type", "change_type",
                    "severity", "status", "detected_at", "effective_date",
                    "ai_confidence_score", "ai_change_category", "is_cosmetic_change",
                    "impact_assessment", "description", "url", "change_hash"
                ]
            },
            {
                "name": "monitoring_runs",
                "description": "Monitoring execution history and statistics",
                "available_columns": [
                    "id", "agency_name", "form_name", "started_at", "completed_at",
                    "status", "changes_detected", "response_time_ms", "http_status_code",
                    "error_message", "content_hash"
                ]
            },
            {
                "name": "agencies",
                "description": "Government agencies being monitored",
                "available_columns": [
                    "id", "name", "abbreviation", "agency_type", "base_url",
                    "prevailing_wage_url", "contact_phone", "contact_email",
                    "is_active", "created_at", "updated_at"
                ]
            },
            {
                "name": "forms",
                "description": "Forms and documents being tracked",
                "available_columns": [
                    "id", "agency_name", "name", "title", "form_url",
                    "instructions_url", "upload_portal_url", "check_frequency",
                    "contact_email", "cpr_report_id", "is_active", "last_checked"
                ]
            },
            {
                "name": "notifications",
                "description": "Notification delivery history",
                "available_columns": [
                    "id", "form_change_id", "notification_type", "recipient",
                    "subject", "sent_at", "delivery_status", "delivery_response",
                    "created_at", "updated_at"
                ]
            }
        ]
    }


@router.get("/filter-options")
async def get_filter_options(
    data_source: str = Query("form_changes", description="Data source for filter options"),
    db: Session = Depends(get_db)
):
    """Get available filter options for a specific data source."""
    try:
        if data_source == "form_changes":
            return await _get_form_changes_filter_options(db)
        elif data_source == "agencies":
            return await _get_agencies_filter_options(db)
        elif data_source == "forms":
            return await _get_forms_filter_options(db)
        elif data_source == "monitoring_runs":
            return await _get_monitoring_runs_filter_options(db)
        elif data_source == "notifications":
            return await _get_notifications_filter_options(db)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown data source: {data_source}")
    
    except Exception as e:
        logger.error(f"Error getting filter options for {data_source}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve filter options")


@router.post("/export", response_model=ExportJobResponse)
async def create_export_job(
    request: DataExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new export job with advanced filtering and customization."""
    try:
        # Generate unique job ID
        job_id = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Estimate export size and records
        estimated_records, estimated_size_mb = await _estimate_export_size(request, db)
        
        # Validate export size limits
        if estimated_records > 100000:
            raise HTTPException(
                status_code=400, 
                detail=f"Export too large: {estimated_records} records (max: 100,000)"
            )
        
        if estimated_size_mb > 100:
            raise HTTPException(
                status_code=400,
                detail=f"Export too large: {estimated_size_mb:.1f}MB (max: 100MB)"
            )
        
        # Create export job
        export_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "request": request.dict(),
            "estimated_records": estimated_records,
            "estimated_size_mb": estimated_size_mb,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=24),
            "progress_percent": 0,
            "records_processed": 0
        }
        
        # Start background processing
        background_tasks.add_task(_process_export_job, job_id, request, db)
        
        return ExportJobResponse(
            job_id=job_id,
            status="pending",
            estimated_records=estimated_records,
            estimated_size_mb=estimated_size_mb,
            expires_at=datetime.now() + timedelta(hours=24),
            created_at=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error creating export job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create export job: {str(e)}")


@router.get("/export/{job_id}/status", response_model=ExportStatusResponse)
async def get_export_status(job_id: str):
    """Get the status of an export job."""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = export_jobs[job_id]
    
    # Check if job has expired
    if datetime.now() > job["expires_at"]:
        job["status"] = "expired"
    
    return ExportStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress_percent=job.get("progress_percent"),
        records_processed=job.get("records_processed"),
        total_records=job.get("total_records"),
        file_size_bytes=job.get("file_size_bytes"),
        download_url=job.get("download_url"),
        error_message=job.get("error_message"),
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        expires_at=job["expires_at"]
    )


@router.get("/export/{job_id}/download")
async def download_export(job_id: str):
    """Download the exported file."""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = export_jobs[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail=f"Export not ready. Status: {job['status']}")
    
    if datetime.now() > job["expires_at"]:
        raise HTTPException(status_code=410, detail="Export has expired")
    
    file_path = job.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Get file info
    filename = job.get("filename", f"export_{job_id}")
    format_type = job["request"]["customization"]["format"]
    
    # Set appropriate content type
    content_type_map = {
        "csv": "text/csv",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"
    }
    content_type = content_type_map.get(format_type, "application/octet-stream")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=content_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/export/{job_id}")
async def cancel_export_job(job_id: str):
    """Cancel an export job and clean up resources."""
    if job_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = export_jobs[job_id]
    
    # Clean up file if it exists
    file_path = job.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
        except OSError:
            pass
    
    # Remove from job storage
    del export_jobs[job_id]
    
    return {"message": "Export job cancelled and cleaned up"}


@router.post("/bulk-export", response_model=ExportJobResponse)
async def create_bulk_export_job(
    request: BulkExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a bulk export job for multiple data sources."""
    try:
        # Convert request to format expected by bulk export manager
        export_requests = [export.dict() for export in request.exports]
        
        # Estimate total size using bulk export manager
        total_records, total_size_mb, breakdown = await bulk_export_manager.estimate_bulk_export_size(
            export_requests, db
        )
        
        # Validate bulk export limits (increased for enhanced bulk export)
        if total_records > 1000000:  # 1M records for bulk exports
            raise HTTPException(
                status_code=400,
                detail=f"Bulk export too large: {total_records} records (max: 1,000,000)"
            )
        
        if total_size_mb > 1000:  # 1GB for bulk exports
            raise HTTPException(
                status_code=400,
                detail=f"Bulk export too large: {total_size_mb:.1f}MB (max: 1,000MB)"
            )
        
        # Create bulk export job using enhanced manager
        job = bulk_export_manager.create_bulk_export_job(
            export_requests,
            combined_output=request.combined_output,
            archive_format=request.archive_format
        )
        
        # Apply custom configuration if provided
        if request.chunk_size:
            job.config.chunk_size = request.chunk_size
        
        # Store in legacy format for API compatibility
        export_jobs[job.job_id] = job.to_dict()
        
        # Start background processing with enhanced manager
        background_tasks.add_task(
            _process_enhanced_bulk_export,
            job.job_id,
            export_requests,
            db,
            request.combined_output
        )
        
        return ExportJobResponse(
            job_id=job.job_id,
            status="pending",
            estimated_records=total_records,
            estimated_size_mb=total_size_mb,
            expires_at=job.expires_at,
            created_at=job.created_at
        )
    
    except Exception as e:
        logger.error(f"Error creating bulk export job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create bulk export job: {str(e)}")


@router.post("/large-bulk-export", response_model=ExportJobResponse)
async def create_large_bulk_export_job(
    request: LargeBulkExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a large bulk export job with advanced streaming capabilities."""
    try:
        # Convert request to format expected by bulk export manager
        export_requests = [export.dict() for export in request.exports]
        
        # Estimate total size
        total_records, total_size_mb, breakdown = await bulk_export_manager.estimate_bulk_export_size(
            export_requests, db
        )
        
        # Increased limits for large bulk exports
        if total_records > 10000000:  # 10M records for large bulk exports
            raise HTTPException(
                status_code=400,
                detail=f"Large bulk export too large: {total_records} records (max: 10,000,000)"
            )
        
        if total_size_mb > 5000:  # 5GB for large bulk exports
            raise HTTPException(
                status_code=400,
                detail=f"Large bulk export too large: {total_size_mb:.1f}MB (max: 5,000MB)"
            )
        
        # Create enhanced bulk export job
        job = bulk_export_manager.create_bulk_export_job(
            export_requests,
            combined_output=True,  # Always use combined output for large exports
            archive_format="zip"
        )
        
        # Apply advanced configuration
        if request.max_records_per_file:
            for format_type in job.config.format_limits:
                job.config.format_limits[format_type]['max_records_per_file'] = request.max_records_per_file
        
        if request.compression_level:
            job.config.compression_level = request.compression_level
        
        # Store notification email if provided
        if request.notification_email:
            job.to_dict()['notification_email'] = request.notification_email
        
        # Store in legacy format for API compatibility
        export_jobs[job.job_id] = job.to_dict()
        
        # Start background processing
        background_tasks.add_task(
            _process_enhanced_bulk_export,
            job.job_id,
            export_requests,
            db,
            True  # Always use combined output
        )
        
        return ExportJobResponse(
            job_id=job.job_id,
            status="pending",
            estimated_records=total_records,
            estimated_size_mb=total_size_mb,
            expires_at=job.expires_at,
            created_at=job.created_at
        )
    
    except Exception as e:
        logger.error(f"Error creating large bulk export job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create large bulk export job: {str(e)}")


@router.get("/bulk-export/{job_id}/detailed-status")
async def get_detailed_bulk_export_status(job_id: str):
    """Get detailed status of a bulk export job including chunk progress."""
    job = bulk_export_manager.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Bulk export job not found")
    
    # Check if job has expired
    if datetime.now() > job.expires_at:
        job.status = "expired"
    
    detailed_status = job.to_dict()
    
    # Add additional runtime information
    if job.started_at:
        runtime = datetime.now() - job.started_at
        detailed_status['runtime_seconds'] = int(runtime.total_seconds())
        
        if job.status == "processing" and job.total_records > 0:
            records_per_second = job.processed_records / runtime.total_seconds() if runtime.total_seconds() > 0 else 0
            remaining_records = job.total_records - job.processed_records
            estimated_completion = datetime.now() + timedelta(
                seconds=remaining_records / records_per_second if records_per_second > 0 else 0
            )
            detailed_status['estimated_completion'] = estimated_completion
            detailed_status['processing_rate_records_per_second'] = records_per_second
    
    return detailed_status


@router.post("/bulk-export/{job_id}/cancel")
async def cancel_bulk_export_job(job_id: str):
    """Cancel a bulk export job and cleanup resources."""
    success = bulk_export_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bulk export job not found")
    
    # Remove from legacy storage
    if job_id in export_jobs:
        del export_jobs[job_id]
    
    return {"message": f"Bulk export job {job_id} cancelled successfully"}


@router.get("/bulk-export/cleanup")
async def cleanup_expired_bulk_exports():
    """Cleanup expired bulk export jobs (admin endpoint)."""
    cleaned_count = bulk_export_manager.cleanup_expired_jobs()
    
    # Also cleanup legacy export jobs
    now = datetime.now()
    expired_legacy = []
    
    for job_id, job_data in export_jobs.items():
        expires_at = job_data.get('expires_at')
        if expires_at and isinstance(expires_at, datetime) and now > expires_at:
            expired_legacy.append(job_id)
    
    for job_id in expired_legacy:
        del export_jobs[job_id]
    
    total_cleaned = cleaned_count + len(expired_legacy)
    
    return {
        "message": f"Cleaned up {total_cleaned} expired export jobs",
        "bulk_exports_cleaned": cleaned_count,
        "legacy_exports_cleaned": len(expired_legacy)
    }


# Advanced Scheduling Endpoints

@router.post("/schedule/advanced", response_model=ScheduledExportResponse)
async def create_advanced_schedule(
    request: AdvancedScheduleRequest,
    db: Session = Depends(get_db)
):
    """Create an advanced scheduled export with delivery automation."""
    try:
        # Convert request to scheduler format
        schedule_config = {
            'name': request.name,
            'description': request.description,
            'schedule': request.schedule,
            'export_config': request.export_config.dict(),
            'delivery_channels': [channel.dict() for channel in request.delivery_channels],
            'enabled': request.enabled
        }
        
        # Apply template if specified
        if request.template_name:
            templates = advanced_export_scheduler.get_export_templates()
            if request.template_name in templates:
                template = templates[request.template_name]
                # Merge template config with request config
                schedule_config['export_config'].update(template.get('export_config', {}))
                if not request.name:
                    schedule_config['name'] = template.get('name', request.template_name)
        
        # Create scheduled export
        export_id = advanced_export_scheduler.schedule_export(schedule_config)
        
        # Get created export details
        scheduled_exports = advanced_export_scheduler.get_scheduled_exports()
        export_details = scheduled_exports.get(export_id)
        
        if not export_details:
            raise HTTPException(status_code=500, detail="Failed to create scheduled export")
        
        return ScheduledExportResponse(
            export_id=export_id,
            name=export_details['config']['name'],
            description=export_details['config'].get('description'),
            schedule=export_details['config']['schedule'],
            next_run=export_details['next_run'],
            last_run=export_details['last_run'],
            run_count=export_details['run_count'],
            failure_count=export_details['failure_count'],
            status=export_details['status'],
            created_at=export_details['created_at'],
            delivery_channels=export_details['delivery_channels']
        )
    
    except Exception as e:
        logger.error(f"Failed to create advanced schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create scheduled export: {str(e)}")


@router.get("/schedule/advanced")
async def list_advanced_schedules():
    """List all advanced scheduled exports."""
    try:
        scheduled_exports = advanced_export_scheduler.get_scheduled_exports()
        
        schedules = []
        for export_id, details in scheduled_exports.items():
            schedules.append(ScheduledExportResponse(
                export_id=export_id,
                name=details['config']['name'],
                description=details['config'].get('description'),
                schedule=details['config']['schedule'],
                next_run=details['next_run'],
                last_run=details['last_run'],
                run_count=details['run_count'],
                failure_count=details['failure_count'],
                status=details['status'],
                created_at=details['created_at'],
                delivery_channels=details['delivery_channels']
            ))
        
        return {"scheduled_exports": schedules}
    
    except Exception as e:
        logger.error(f"Failed to list scheduled exports: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduled exports")


@router.get("/schedule/advanced/{export_id}")
async def get_advanced_schedule(export_id: str):
    """Get details of a specific scheduled export."""
    try:
        scheduled_exports = advanced_export_scheduler.get_scheduled_exports()
        
        if export_id not in scheduled_exports:
            raise HTTPException(status_code=404, detail="Scheduled export not found")
        
        details = scheduled_exports[export_id]
        
        return ScheduledExportResponse(
            export_id=export_id,
            name=details['config']['name'],
            description=details['config'].get('description'),
            schedule=details['config']['schedule'],
            next_run=details['next_run'],
            last_run=details['last_run'],
            run_count=details['run_count'],
            failure_count=details['failure_count'],
            status=details['status'],
            created_at=details['created_at'],
            delivery_channels=details['delivery_channels']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scheduled export {export_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduled export")


@router.put("/schedule/advanced/{export_id}", response_model=ScheduledExportResponse)
async def update_advanced_schedule(
    export_id: str,
    request: ScheduleUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update an advanced scheduled export."""
    try:
        # Get current schedule
        scheduled_exports = advanced_export_scheduler.get_scheduled_exports()
        
        if export_id not in scheduled_exports:
            raise HTTPException(status_code=404, detail="Scheduled export not found")
        
        current_config = scheduled_exports[export_id]['config']
        
        # Update configuration with provided fields
        updated_config = current_config.copy()
        
        if request.name is not None:
            updated_config['name'] = request.name
        if request.description is not None:
            updated_config['description'] = request.description
        if request.schedule is not None:
            updated_config['schedule'] = request.schedule
        if request.export_config is not None:
            updated_config['export_config'] = request.export_config.dict()
        if request.delivery_channels is not None:
            updated_config['delivery_channels'] = [channel.dict() for channel in request.delivery_channels]
        if request.enabled is not None:
            updated_config['enabled'] = request.enabled
        
        # Update the scheduled export
        success = advanced_export_scheduler.update_scheduled_export(export_id, updated_config)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update scheduled export")
        
        # Return updated details
        updated_exports = advanced_export_scheduler.get_scheduled_exports()
        details = updated_exports[export_id]
        
        return ScheduledExportResponse(
            export_id=export_id,
            name=details['config']['name'],
            description=details['config'].get('description'),
            schedule=details['config']['schedule'],
            next_run=details['next_run'],
            last_run=details['last_run'],
            run_count=details['run_count'],
            failure_count=details['failure_count'],
            status=details['status'],
            created_at=details['created_at'],
            delivery_channels=details['delivery_channels']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update scheduled export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update scheduled export: {str(e)}")


@router.delete("/schedule/advanced/{export_id}")
async def delete_advanced_schedule(export_id: str):
    """Delete an advanced scheduled export."""
    try:
        success = advanced_export_scheduler.cancel_scheduled_export(export_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Scheduled export not found")
        
        return {"message": f"Scheduled export {export_id} deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete scheduled export {export_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete scheduled export")


@router.get("/schedule/templates")
async def get_export_templates():
    """Get available export templates."""
    try:
        templates = advanced_export_scheduler.get_export_templates()
        return {"templates": templates}
    
    except Exception as e:
        logger.error(f"Failed to get export templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve export templates")


@router.get("/schedule/history")
async def get_export_history(
    export_id: Optional[str] = Query(None, description="Filter by specific export ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records")
):
    """Get export execution history."""
    try:
        history = advanced_export_scheduler.get_export_history(export_id, limit)
        
        history_responses = []
        for record in history:
            history_responses.append(ExportHistoryResponse(
                export_id=record['export_id'],
                export_name=record['export_name'],
                last_run=record['last_run'],
                run_count=record['run_count'],
                status=record['status'],
                last_error=record['last_error']
            ))
        
        return {"history": history_responses}
    
    except Exception as e:
        logger.error(f"Failed to get export history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve export history")


@router.post("/schedule/start")
async def start_scheduler():
    """Start the advanced export scheduler (admin endpoint)."""
    try:
        advanced_export_scheduler.start()
        return {"message": "Advanced export scheduler started successfully"}
    
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scheduler")


@router.post("/schedule/stop")
async def stop_scheduler():
    """Stop the advanced export scheduler (admin endpoint)."""
    try:
        advanced_export_scheduler.stop()
        return {"message": "Advanced export scheduler stopped successfully"}
    
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop scheduler")


@router.get("/schedule/status")
async def get_scheduler_status():
    """Get scheduler status and statistics."""
    try:
        scheduled_exports = advanced_export_scheduler.get_scheduled_exports()
        
        active_count = sum(1 for export in scheduled_exports.values() if export['status'] == 'active')
        total_runs = sum(export['run_count'] for export in scheduled_exports.values())
        total_failures = sum(export['failure_count'] for export in scheduled_exports.values())
        
        return {
            "scheduler_running": advanced_export_scheduler.running,
            "total_schedules": len(scheduled_exports),
            "active_schedules": active_count,
            "total_runs": total_runs,
            "total_failures": total_failures,
            "success_rate": (total_runs - total_failures) / total_runs * 100 if total_runs > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scheduler status")


# Helper functions
async def _get_form_changes_filter_options(db: Session):
    """Get filter options for form changes data source."""
    # Get unique values for various fields
    agencies = db.query(Agency.id, Agency.name).filter(Agency.is_active == True).all()
    forms = db.query(Form.id, Form.name).filter(Form.is_active == True).all()
    severities = db.query(FormChange.severity).distinct().all()
    statuses = db.query(FormChange.status).distinct().all()
    change_types = db.query(FormChange.change_type).distinct().all()
    ai_categories = db.query(FormChange.ai_change_category).distinct().all()
    
    return {
        "agencies": [{"id": a.id, "name": a.name} for a in agencies],
        "forms": [{"id": f.id, "name": f.name} for f in forms],
        "severities": [s[0] for s in severities if s[0]],
        "statuses": [s[0] for s in statuses if s[0]],
        "change_types": [ct[0] for ct in change_types if ct[0]],
        "ai_categories": [ac[0] for ac in ai_categories if ac[0]],
        "date_ranges": ["24h", "7d", "30d", "90d", "1y"],
        "ai_confidence_range": {"min": 0, "max": 100}
    }


async def _get_agencies_filter_options(db: Session):
    """Get filter options for agencies data source."""
    agency_types = db.query(Agency.agency_type).distinct().all()
    
    return {
        "agency_types": [at[0] for at in agency_types if at[0]],
        "active_status": [True, False]
    }


async def _get_forms_filter_options(db: Session):
    """Get filter options for forms data source."""
    check_frequencies = db.query(Form.check_frequency).distinct().all()
    
    return {
        "check_frequencies": [cf[0] for cf in check_frequencies if cf[0]],
        "active_status": [True, False]
    }


async def _get_monitoring_runs_filter_options(db: Session):
    """Get filter options for monitoring runs data source."""
    statuses = db.query(MonitoringRun.status).distinct().all()
    
    return {
        "run_statuses": [s[0] for s in statuses if s[0]],
        "date_ranges": ["24h", "7d", "30d", "90d", "1y"]
    }


async def _get_notifications_filter_options(db: Session):
    """Get filter options for notifications data source."""
    notification_types = db.query(Notification.notification_type).distinct().all()
    delivery_statuses = db.query(Notification.delivery_status).distinct().all()
    
    return {
        "notification_types": [nt[0] for nt in notification_types if nt[0]],
        "delivery_statuses": [ds[0] for ds in delivery_statuses if ds[0]],
        "date_ranges": ["24h", "7d", "30d", "90d", "1y"]
    }


async def _estimate_export_size(request: DataExportRequest, db: Session) -> tuple[int, float]:
    """Estimate the number of records and file size for an export."""
    try:
        data_source = request.data_source or "form_changes"
        
        # Build query based on data source
        if data_source == "form_changes":
            query = db.query(FormChange)
            if request.filters:
                query = _apply_advanced_filters(query, request.filters, data_source)
        elif data_source == "agencies":
            query = db.query(Agency)
            if request.filters:
                query = _apply_advanced_filters(query, request.filters, data_source)
        elif data_source == "forms":
            query = db.query(Form)
            if request.filters:
                query = _apply_advanced_filters(query, request.filters, data_source)
        elif data_source == "monitoring_runs":
            query = db.query(MonitoringRun)
            if request.filters:
                query = _apply_advanced_filters(query, request.filters, data_source)
        elif data_source == "notifications":
            query = db.query(Notification)
            if request.filters:
                query = _apply_advanced_filters(query, request.filters, data_source)
        else:
            raise ValueError(f"Unknown data source: {data_source}")
        
        # Count records
        record_count = query.count()
        
        # Estimate file size (rough calculation)
        # Average bytes per record by format
        bytes_per_record_map = {
            "csv": 200,      # ~200 bytes per record for CSV
            "excel": 300,    # ~300 bytes per record for Excel
            "pdf": 500       # ~500 bytes per record for PDF
        }
        
        format_type = request.customization.format
        bytes_per_record = bytes_per_record_map.get(format_type, 250)
        estimated_bytes = record_count * bytes_per_record
        estimated_mb = estimated_bytes / (1024 * 1024)
        
        return record_count, estimated_mb
    
    except Exception as e:
        logger.error(f"Error estimating export size: {e}")
        return 0, 0.0


def _apply_advanced_filters(query, filters: AdvancedFilterRequest, data_source: str):
    """Apply advanced filters to a query based on data source."""
    # This is a placeholder - implementation would depend on the specific data source
    # and would apply the appropriate filters to the query
    
    if data_source == "form_changes":
        return _apply_form_changes_filters(query, filters)
    elif data_source == "agencies":
        return _apply_agencies_filters(query, filters)
    elif data_source == "forms":
        return _apply_forms_filters(query, filters)
    elif data_source == "monitoring_runs":
        return _apply_monitoring_runs_filters(query, filters)
    elif data_source == "notifications":
        return _apply_notifications_filters(query, filters)
    
    return query


def _apply_form_changes_filters(query, filters: AdvancedFilterRequest):
    """Apply filters specific to form changes."""
    # Date filtering
    if filters.date_from:
        try:
            date_from = datetime.fromisoformat(filters.date_from)
            query = query.filter(FormChange.detected_at >= date_from)
        except ValueError:
            pass
    
    if filters.date_to:
        try:
            date_to = datetime.fromisoformat(filters.date_to)
            query = query.filter(FormChange.detected_at <= date_to)
        except ValueError:
            pass
    
    # Entity filtering
    if filters.agency_ids:
        query = query.join(Form).filter(Form.agency_id.in_(filters.agency_ids))
    
    if filters.form_ids:
        query = query.filter(FormChange.form_id.in_(filters.form_ids))
    
    # Change characteristics
    if filters.severities:
        query = query.filter(FormChange.severity.in_(filters.severities))
    
    if filters.statuses:
        query = query.filter(FormChange.status.in_(filters.statuses))
    
    if filters.change_types:
        query = query.filter(FormChange.change_type.in_(filters.change_types))
    
    # AI analysis filtering
    if filters.ai_confidence_min is not None:
        query = query.filter(FormChange.ai_confidence_score >= filters.ai_confidence_min)
    
    if filters.ai_confidence_max is not None:
        query = query.filter(FormChange.ai_confidence_score <= filters.ai_confidence_max)
    
    if filters.ai_categories:
        query = query.filter(FormChange.ai_change_category.in_(filters.ai_categories))
    
    if filters.include_cosmetic is False:
        query = query.filter(FormChange.is_cosmetic_change == False)
    
    # Content filtering
    if filters.description_contains:
        query = query.filter(FormChange.description.contains(filters.description_contains))
    
    if filters.url_contains:
        query = query.filter(FormChange.url.contains(filters.url_contains))
    
    return query


def _apply_agencies_filters(query, filters: AdvancedFilterRequest):
    """Apply filters specific to agencies."""
    if filters.agency_types:
        query = query.filter(Agency.agency_type.in_(filters.agency_types))
    
    if filters.agency_names:
        query = query.filter(Agency.name.in_(filters.agency_names))
    
    return query


def _apply_forms_filters(query, filters: AdvancedFilterRequest):
    """Apply filters specific to forms."""
    if filters.agency_ids:
        query = query.filter(Form.agency_id.in_(filters.agency_ids))
    
    if filters.form_names:
        query = query.filter(Form.name.in_(filters.form_names))
    
    return query


def _apply_monitoring_runs_filters(query, filters: AdvancedFilterRequest):
    """Apply filters specific to monitoring runs."""
    if filters.date_from:
        try:
            date_from = datetime.fromisoformat(filters.date_from)
            query = query.filter(MonitoringRun.started_at >= date_from)
        except ValueError:
            pass
    
    if filters.date_to:
        try:
            date_to = datetime.fromisoformat(filters.date_to)
            query = query.filter(MonitoringRun.started_at <= date_to)
        except ValueError:
            pass
    
    if filters.agency_ids:
        query = query.filter(MonitoringRun.agency_id.in_(filters.agency_ids))
    
    return query


def _apply_notifications_filters(query, filters: AdvancedFilterRequest):
    """Apply filters specific to notifications."""
    if filters.date_from:
        try:
            date_from = datetime.fromisoformat(filters.date_from)
            query = query.filter(Notification.sent_at >= date_from)
        except ValueError:
            pass
    
    if filters.date_to:
        try:
            date_to = datetime.fromisoformat(filters.date_to)
            query = query.filter(Notification.sent_at <= date_to)
        except ValueError:
            pass
    
    return query


async def _process_export_job(job_id: str, request: DataExportRequest, db: Session):
    """Background task to process an export job."""
    try:
        # Update job status
        export_jobs[job_id]["status"] = "processing"
        export_jobs[job_id]["progress_percent"] = 10
        
        # Get data based on data source
        data_source = request.data_source or "form_changes"
        data = await _fetch_export_data(request, db)
        
        export_jobs[job_id]["progress_percent"] = 50
        export_jobs[job_id]["total_records"] = len(data)
        
        # Generate export
        export_content = export_manager.export_data(
            data=data,
            format_type=request.customization.format,
            export_config=_build_export_config(request)
        )
        
        export_jobs[job_id]["progress_percent"] = 80
        
        # Save to temporary file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        format_ext = export_manager.get_export_metadata(request.customization.format)['extension']
        
        filename = request.customization.filename or f"export_{timestamp}{format_ext}"
        
        # Create temporary file
        temp_dir = Path(tempfile.gettempdir()) / "compliance_exports"
        temp_dir.mkdir(exist_ok=True)
        
        file_path = temp_dir / f"{job_id}_{filename}"
        
        # Write content to file
        if request.customization.format == 'csv':
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(export_content)
        else:
            with open(file_path, 'wb') as f:
                f.write(export_content)
        
        # Update job with completion info
        export_jobs[job_id].update({
            "status": "completed",
            "progress_percent": 100,
            "records_processed": len(data),
            "file_path": str(file_path),
            "filename": filename,
            "file_size_bytes": os.path.getsize(file_path),
            "download_url": f"/api/data-export/export/{job_id}/download",
            "completed_at": datetime.now()
        })
        
        logger.info(f"Export job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Export job {job_id} failed: {e}")
        export_jobs[job_id].update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.now()
        })


async def _process_enhanced_bulk_export(
    job_id: str,
    export_requests: List[Dict[str, Any]],
    db: Session,
    combined_output: bool = False
):
    """Enhanced background task to process bulk export jobs with streaming support."""
    try:
        # Use the bulk export manager for processing
        await bulk_export_manager.process_bulk_export(
            job_id, export_requests, db, combined_output
        )
        
        # Update legacy export jobs storage for API compatibility
        job = bulk_export_manager.get_job_status(job_id)
        if job:
            export_jobs[job_id] = job.to_dict()
            
            # Add download URL for API compatibility
            if job.final_archive_path:
                export_jobs[job_id]["download_url"] = f"/api/data-export/export/{job_id}/download"
                export_jobs[job_id]["file_path"] = job.final_archive_path
                export_jobs[job_id]["file_size_bytes"] = os.path.getsize(job.final_archive_path) if os.path.exists(job.final_archive_path) else 0
    
    except Exception as e:
        logger.error(f"Enhanced bulk export job {job_id} failed: {e}")
        # Update both storages with error
        if job_id in export_jobs:
            export_jobs[job_id].update({
                "status": "failed",
                "error_message": str(e),
                "completed_at": datetime.now()
            })


async def _process_bulk_export_job(job_id: str, request: BulkExportRequest, db: Session):
    """Legacy background task to process a bulk export job."""
    try:
        export_jobs[job_id]["status"] = "processing"
        
        # Process each export
        export_files = []
        total_exports = len(request.exports)
        
        for i, export_request in enumerate(request.exports):
            # Update progress
            progress = int((i / total_exports) * 80)  # Reserve 20% for final processing
            export_jobs[job_id]["progress_percent"] = progress
            
            # Process individual export
            data = await _fetch_export_data(export_request, db)
            
            export_content = export_manager.export_data(
                data=data,
                format_type=export_request.customization.format,
                export_config=_build_export_config(export_request)
            )
            
            # Save individual file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            format_ext = export_manager.get_export_metadata(export_request.customization.format)['extension']
            filename = f"export_{i+1}_{timestamp}{format_ext}"
            
            temp_dir = Path(tempfile.gettempdir()) / "compliance_exports"
            temp_dir.mkdir(exist_ok=True)
            file_path = temp_dir / f"{job_id}_{filename}"
            
            if export_request.customization.format == 'csv':
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(export_content)
            else:
                with open(file_path, 'wb') as f:
                    f.write(export_content)
            
            export_files.append((str(file_path), filename))
        
        # Create archive if requested
        if len(export_files) > 1 and request.archive_format:
            import zipfile
            
            archive_filename = f"bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            archive_path = temp_dir / f"{job_id}_{archive_filename}"
            
            with zipfile.ZipFile(archive_path, 'w') as zip_file:
                for file_path, filename in export_files:
                    zip_file.write(file_path, filename)
                    # Clean up individual files
                    os.unlink(file_path)
            
            final_file_path = str(archive_path)
            final_filename = archive_filename
        else:
            # Use first file if only one export or no archiving requested
            final_file_path, final_filename = export_files[0]
        
        # Update job completion
        export_jobs[job_id].update({
            "status": "completed",
            "progress_percent": 100,
            "file_path": final_file_path,
            "filename": final_filename,
            "file_size_bytes": os.path.getsize(final_file_path),
            "download_url": f"/api/data-export/export/{job_id}/download",
            "completed_at": datetime.now()
        })
        
        logger.info(f"Bulk export job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Bulk export job {job_id} failed: {e}")
        export_jobs[job_id].update({
            "status": "failed",
            "error_message": str(e),
            "completed_at": datetime.now()
        })


async def _fetch_export_data(request: DataExportRequest, db: Session) -> List[Dict]:
    """Fetch data for export based on request parameters."""
    data_source = request.data_source or "form_changes"
    
    if data_source == "form_changes":
        return await _fetch_form_changes_data(request, db)
    elif data_source == "agencies":
        return await _fetch_agencies_data(request, db)
    elif data_source == "forms":
        return await _fetch_forms_data(request, db)
    elif data_source == "monitoring_runs":
        return await _fetch_monitoring_runs_data(request, db)
    elif data_source == "notifications":
        return await _fetch_notifications_data(request, db)
    else:
        raise ValueError(f"Unknown data source: {data_source}")


async def _fetch_form_changes_data(request: DataExportRequest, db: Session) -> List[Dict]:
    """Fetch form changes data for export."""
    query = db.query(FormChange).options(
        joinedload(FormChange.form).joinedload(Form.agency)
    )
    
    if request.filters:
        query = _apply_form_changes_filters(query, request.filters)
    
    # Apply sorting
    if request.filters and request.filters.sort_by:
        sort_field = getattr(FormChange, request.filters.sort_by, None)
        if sort_field:
            if request.filters.sort_order == "desc":
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(asc(sort_field))
    
    # Apply pagination
    if request.filters and request.filters.limit:
        query = query.limit(request.filters.limit)
        if request.filters.offset:
            query = query.offset(request.filters.offset)
    
    changes = query.all()
    
    # Convert to dictionary format
    export_data = []
    for change in changes:
        change_dict = {
            'id': change.id,
            'form_name': change.form.name if change.form else 'Unknown',
            'agency_name': change.form.agency.name if change.form and change.form.agency else 'Unknown',
            'agency_type': change.form.agency.agency_type if change.form and change.form.agency else 'Unknown',
            'change_type': change.change_type,
            'severity': change.severity,
            'status': change.status,
            'detected_at': change.detected_at,
            'effective_date': change.effective_date,
            'description': change.description,
            'url': change.url,
            'change_hash': change.change_hash
        }
        
        # Add AI analysis fields if requested
        if request.customization.include_ai_analysis:
            change_dict.update({
                'ai_confidence_score': change.ai_confidence_score,
                'ai_change_category': change.ai_change_category,
                'ai_severity_score': change.ai_severity_score,
                'ai_reasoning': change.ai_reasoning,
                'ai_semantic_similarity': change.ai_semantic_similarity,
                'is_cosmetic_change': change.is_cosmetic_change
            })
        
        # Add impact assessment if requested
        if request.customization.include_impact_assessment:
            change_dict['impact_assessment'] = change.impact_assessment
        
        # Add related data if requested
        if request.customization.include_related_data:
            if change.form:
                change_dict.update({
                    'form_title': change.form.title,
                    'form_url': change.form.form_url,
                    'instructions_url': change.form.instructions_url,
                    'check_frequency': change.form.check_frequency
                })
                
                if change.form.agency:
                    change_dict.update({
                        'agency_abbreviation': change.form.agency.abbreviation,
                        'agency_base_url': change.form.agency.base_url,
                        'agency_contact_email': change.form.agency.contact_email,
                        'agency_contact_phone': change.form.agency.contact_phone
                    })
        
        export_data.append(change_dict)
    
    return export_data


async def _fetch_agencies_data(request: DataExportRequest, db: Session) -> List[Dict]:
    """Fetch agencies data for export."""
    query = db.query(Agency)
    
    if request.filters:
        query = _apply_agencies_filters(query, request.filters)
    
    agencies = query.all()
    
    export_data = []
    for agency in agencies:
        export_data.append({
            'id': agency.id,
            'name': agency.name,
            'abbreviation': agency.abbreviation,
            'agency_type': agency.agency_type,
            'base_url': agency.base_url,
            'prevailing_wage_url': agency.prevailing_wage_url,
            'contact_phone': agency.contact_phone,
            'contact_email': agency.contact_email,
            'is_active': agency.is_active,
            'created_at': agency.created_at,
            'updated_at': agency.updated_at
        })
    
    return export_data


async def _fetch_forms_data(request: DataExportRequest, db: Session) -> List[Dict]:
    """Fetch forms data for export."""
    query = db.query(Form).options(joinedload(Form.agency))
    
    if request.filters:
        query = _apply_forms_filters(query, request.filters)
    
    forms = query.all()
    
    export_data = []
    for form in forms:
        export_data.append({
            'id': form.id,
            'agency_name': form.agency.name if form.agency else 'Unknown',
            'name': form.name,
            'title': form.title,
            'form_url': form.form_url,
            'instructions_url': form.instructions_url,
            'upload_portal_url': form.upload_portal_url,
            'check_frequency': form.check_frequency,
            'contact_email': form.contact_email,
            'cpr_report_id': form.cpr_report_id,
            'is_active': form.is_active,
            'created_at': form.created_at,
            'updated_at': form.updated_at,
            'last_checked': form.last_checked,
            'last_modified': form.last_modified
        })
    
    return export_data


async def _fetch_monitoring_runs_data(request: DataExportRequest, db: Session) -> List[Dict]:
    """Fetch monitoring runs data for export."""
    query = db.query(MonitoringRun).options(
        joinedload(MonitoringRun.agency),
        joinedload(MonitoringRun.form)
    )
    
    if request.filters:
        query = _apply_monitoring_runs_filters(query, request.filters)
    
    runs = query.all()
    
    export_data = []
    for run in runs:
        export_data.append({
            'id': run.id,
            'agency_name': run.agency.name if run.agency else 'Unknown',
            'form_name': run.form.name if run.form else 'N/A',
            'started_at': run.started_at,
            'completed_at': run.completed_at,
            'status': run.status,
            'changes_detected': run.changes_detected,
            'error_message': run.error_message,
            'response_time_ms': run.response_time_ms,
            'http_status_code': run.http_status_code,
            'content_hash': run.content_hash
        })
    
    return export_data


async def _fetch_notifications_data(request: DataExportRequest, db: Session) -> List[Dict]:
    """Fetch notifications data for export."""
    query = db.query(Notification).options(
        joinedload(Notification.form_change)
    )
    
    if request.filters:
        query = _apply_notifications_filters(query, request.filters)
    
    notifications = query.all()
    
    export_data = []
    for notification in notifications:
        export_data.append({
            'id': notification.id,
            'form_change_id': notification.form_change_id,
            'notification_type': notification.notification_type,
            'recipient': notification.recipient,
            'subject': notification.subject,
            'sent_at': notification.sent_at,
            'delivery_status': notification.delivery_status,
            'delivery_response': notification.delivery_response,
            'created_at': notification.created_at,
            'updated_at': notification.updated_at
        })
    
    return export_data


def _build_export_config(request: DataExportRequest) -> Dict[str, Any]:
    """Build export configuration from request."""
    return {
        'columns': request.customization.columns,
        'include_headers': request.customization.include_headers,
        'include_metadata': request.customization.include_metadata,
        'date_format': request.customization.date_format,
        'timezone': request.customization.timezone
    }