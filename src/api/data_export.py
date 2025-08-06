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
from pydantic import BaseModel, Field, validator

from ..database.connection import get_db
from ..database.models import FormChange, Form, Agency, MonitoringRun, Notification
from ..utils.export_utils import ExportManager, ExportScheduler
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
    
    @validator('format')
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
        # Generate unique job ID
        job_id = f"bulk_export_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Estimate total size
        total_records = 0
        total_size_mb = 0.0
        
        for export_request in request.exports:
            records, size_mb = await _estimate_export_size(export_request, db)
            total_records += records
            total_size_mb += size_mb
        
        # Validate bulk export limits
        if total_records > 500000:
            raise HTTPException(
                status_code=400,
                detail=f"Bulk export too large: {total_records} records (max: 500,000)"
            )
        
        if total_size_mb > 500:
            raise HTTPException(
                status_code=400,
                detail=f"Bulk export too large: {total_size_mb:.1f}MB (max: 500MB)"
            )
        
        # Create bulk export job
        export_jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "type": "bulk",
            "request": request.dict(),
            "estimated_records": total_records,
            "estimated_size_mb": total_size_mb,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(hours=48),  # Longer expiry for bulk exports
            "progress_percent": 0,
            "records_processed": 0
        }
        
        # Start background processing
        background_tasks.add_task(_process_bulk_export_job, job_id, request, db)
        
        return ExportJobResponse(
            job_id=job_id,
            status="pending",
            estimated_records=total_records,
            estimated_size_mb=total_size_mb,
            expires_at=datetime.now() + timedelta(hours=48),
            created_at=datetime.now()
        )
    
    except Exception as e:
        logger.error(f"Error creating bulk export job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create bulk export job: {str(e)}")


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


async def _process_bulk_export_job(job_id: str, request: BulkExportRequest, db: Session):
    """Background task to process a bulk export job."""
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