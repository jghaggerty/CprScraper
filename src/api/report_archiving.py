"""
Report Archiving API Endpoints

This module provides REST API endpoints for report archiving and historical access,
including archive management, search, retrieval, and cleanup operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from enum import Enum

from ..reporting.report_archiving import (
    ReportArchiver, ArchiveMetadata, ReportType, ArchiveStatus,
    get_archiver, archive_weekly_report, retrieve_archived_report, search_archived_reports
)
from ..auth.auth import get_current_user
from ..database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/archiving", tags=["Report Archiving"])


# Pydantic Models
class ReportTypeEnum(str, Enum):
    """Report type enumeration for API."""
    WEEKLY_SUMMARY = "weekly_summary"
    DAILY_SUMMARY = "daily_summary"
    MONTHLY_DETAILED = "monthly_detailed"
    CUSTOM_REPORT = "custom_report"
    EXECUTIVE_SUMMARY = "executive_summary"
    COMPLIANCE_AUDIT = "compliance_audit"
    TREND_ANALYSIS = "trend_analysis"


class ArchiveStatusEnum(str, Enum):
    """Archive status enumeration for API."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    EXPIRED = "expired"


class ArchiveReportRequest(BaseModel):
    """Request model for archiving a report."""
    report_data: Dict[str, Any] = Field(..., description="Report data to archive")
    report_type: ReportTypeEnum = Field(..., description="Type of report")
    title: str = Field(..., description="Report title", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="Report description", max_length=1000)
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    retention_days: int = Field(2555, description="Days to retain the report", ge=1, le=3650)
    access_level: str = Field("standard", description="Access level required", pattern="^(public|standard|restricted|admin)$")


class ArchiveMetadataResponse(BaseModel):
    """Response model for archive metadata."""
    report_id: str
    report_type: ReportTypeEnum
    title: str
    description: Optional[str]
    generated_at: datetime
    report_period_start: datetime
    report_period_end: datetime
    generated_by: int
    file_size_bytes: int
    file_size_mb: float
    file_hash: str
    format: str
    version: str
    tags: List[str]
    filters_applied: Dict[str, Any]
    status: ArchiveStatusEnum
    retention_days: int
    access_level: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SearchReportsRequest(BaseModel):
    """Request model for searching archived reports."""
    report_type: Optional[ReportTypeEnum] = None
    title_search: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[List[str]] = None
    generated_by: Optional[int] = None
    access_level: Optional[str] = None
    limit: int = Field(50, ge=1, le=100)
    offset: int = Field(0, ge=0)


class SearchReportsResponse(BaseModel):
    """Response model for search results."""
    reports: List[ArchiveMetadataResponse]
    total_count: int
    limit: int
    offset: int
    has_more: bool


class ArchiveStatisticsResponse(BaseModel):
    """Response model for archive statistics."""
    total_reports: int
    reports_by_type: Dict[str, int]
    total_storage_bytes: int
    total_storage_mb: float
    reports_by_status: Dict[str, int]
    oldest_report: Optional[datetime]
    newest_report: Optional[datetime]


class CleanupResponse(BaseModel):
    """Response model for cleanup operation."""
    expired_reports_found: int
    successfully_deleted: int
    failed_deletions: int
    cleanup_timestamp: datetime


# Helper function to convert internal models to API models
def _metadata_to_response(metadata: ArchiveMetadata) -> ArchiveMetadataResponse:
    """Convert ArchiveMetadata to ArchiveMetadataResponse."""
    return ArchiveMetadataResponse(
        report_id=metadata.report_id,
        report_type=ReportTypeEnum(metadata.report_type.value),
        title=metadata.title,
        description=metadata.description,
        generated_at=metadata.generated_at,
        report_period_start=metadata.report_period_start,
        report_period_end=metadata.report_period_end,
        generated_by=metadata.generated_by,
        file_size_bytes=metadata.file_size_bytes,
        file_size_mb=round(metadata.file_size_bytes / (1024 * 1024), 2),
        file_hash=metadata.file_hash,
        format=metadata.format,
        version=metadata.version,
        tags=metadata.tags,
        filters_applied=metadata.filters_applied,
        status=ArchiveStatusEnum(metadata.status.value),
        retention_days=metadata.retention_days,
        access_level=metadata.access_level,
        created_at=metadata.created_at,
        updated_at=metadata.updated_at
    )


# API Endpoints
@router.post("/archive", response_model=ArchiveMetadataResponse)
async def archive_report(
    request: ArchiveReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Archive a report with metadata.
    
    This endpoint allows users to archive reports with comprehensive metadata
    including retention policies and access controls.
    """
    try:
        archiver = get_archiver()
        
        # Convert API enum to internal enum
        report_type = ReportType(request.report_type.value)
        
        metadata = archiver.archive_report(
            report_data=request.report_data,
            report_type=report_type,
            title=request.title,
            description=request.description,
            generated_by=current_user.id,
            tags=request.tags,
            retention_days=request.retention_days,
            access_level=request.access_level
        )
        
        logger.info(f"Report archived successfully by user {current_user.id}: {metadata.report_id}")
        return _metadata_to_response(metadata)
        
    except Exception as e:
        logger.error(f"Failed to archive report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to archive report: {str(e)}")


@router.get("/reports/{report_id}", response_model=Dict[str, Any])
async def retrieve_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve an archived report by ID.
    
    This endpoint retrieves a specific archived report with access control
    based on the user's permissions and the report's access level.
    """
    try:
        archiver = get_archiver()
        report_data = archiver.retrieve_report(report_id, current_user.id)
        
        if not report_data:
            raise HTTPException(status_code=404, detail="Report not found or access denied")
        
        logger.info(f"Report retrieved by user {current_user.id}: {report_id}")
        return report_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {str(e)}")


@router.post("/search", response_model=SearchReportsResponse)
async def search_reports(
    request: SearchReportsRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Search archived reports based on various criteria.
    
    This endpoint provides comprehensive search functionality for archived reports
    with filtering by type, date range, tags, and other metadata.
    """
    try:
        archiver = get_archiver()
        
        # Convert API enum to internal enum if provided
        report_type = None
        if request.report_type:
            report_type = ReportType(request.report_type.value)
        
        # Perform search
        results = archiver.search_reports(
            report_type=report_type,
            title_search=request.title_search,
            date_from=request.date_from,
            date_to=request.date_to,
            tags=request.tags,
            generated_by=request.generated_by,
            access_level=request.access_level,
            limit=request.limit + 1,  # Get one extra to determine if there are more
            offset=request.offset
        )
        
        # Check if there are more results
        has_more = len(results) > request.limit
        if has_more:
            results = results[:request.limit]
        
        # Convert to response format
        report_responses = [_metadata_to_response(metadata) for metadata in results]
        
        logger.info(f"Archive search performed by user {current_user.id}: {len(results)} results")
        
        return SearchReportsResponse(
            reports=report_responses,
            total_count=len(report_responses),
            limit=request.limit,
            offset=request.offset,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Failed to search reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search reports: {str(e)}")


@router.get("/search", response_model=SearchReportsResponse)
async def search_reports_get(
    report_type: Optional[ReportTypeEnum] = Query(None, description="Filter by report type"),
    title_search: Optional[str] = Query(None, description="Search in report titles"),
    date_from: Optional[datetime] = Query(None, description="Start date for search"),
    date_to: Optional[datetime] = Query(None, description="End date for search"),
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    generated_by: Optional[int] = Query(None, description="Filter by user who generated"),
    access_level: Optional[str] = Query(None, description="Filter by access level"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user)
):
    """
    Search archived reports using GET parameters.
    
    This endpoint provides the same search functionality as POST but uses
    query parameters for easier integration with web browsers and simple clients.
    """
    try:
        archiver = get_archiver()
        
        # Convert API enum to internal enum if provided
        internal_report_type = None
        if report_type:
            internal_report_type = ReportType(report_type.value)
        
        # Parse tags from comma-separated string
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        
        # Perform search
        results = archiver.search_reports(
            report_type=internal_report_type,
            title_search=title_search,
            date_from=date_from,
            date_to=date_to,
            tags=tag_list,
            generated_by=generated_by,
            access_level=access_level,
            limit=limit + 1,  # Get one extra to determine if there are more
            offset=offset
        )
        
        # Check if there are more results
        has_more = len(results) > limit
        if has_more:
            results = results[:limit]
        
        # Convert to response format
        report_responses = [_metadata_to_response(metadata) for metadata in results]
        
        logger.info(f"Archive search performed by user {current_user.id}: {len(results)} results")
        
        return SearchReportsResponse(
            reports=report_responses,
            total_count=len(report_responses),
            limit=limit,
            offset=offset,
            has_more=has_more
        )
        
    except Exception as e:
        logger.error(f"Failed to search reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search reports: {str(e)}")


@router.get("/statistics", response_model=ArchiveStatisticsResponse)
async def get_archive_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive statistics about the archive.
    
    This endpoint provides detailed statistics including total reports,
    storage usage, and breakdowns by type and status.
    """
    try:
        archiver = get_archiver()
        stats = archiver.get_archive_statistics()
        
        logger.info(f"Archive statistics retrieved by user {current_user.id}")
        
        return ArchiveStatisticsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get archive statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get archive statistics: {str(e)}")


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_expired_reports(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Clean up expired reports based on retention policies.
    
    This endpoint removes reports that have exceeded their retention period.
    The cleanup operation runs in the background to avoid blocking the API.
    """
    try:
        archiver = get_archiver()
        
        # Run cleanup in background
        def run_cleanup():
            try:
                return archiver.cleanup_expired_reports()
            except Exception as e:
                logger.error(f"Background cleanup failed: {e}")
                return {"expired_reports_found": 0, "successfully_deleted": 0, "failed_deletions": 0}
        
        background_tasks.add_task(run_cleanup)
        
        # For immediate response, run a quick check
        quick_stats = archiver.get_archive_statistics()
        
        logger.info(f"Archive cleanup initiated by user {current_user.id}")
        
        return CleanupResponse(
            expired_reports_found=0,  # Will be updated by background task
            successfully_deleted=0,
            failed_deletions=0,
            cleanup_timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to initiate cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initiate cleanup: {str(e)}")


@router.get("/cleanup/status", response_model=CleanupResponse)
async def get_cleanup_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of the last cleanup operation.
    
    This endpoint provides information about the most recent cleanup operation
    including how many reports were processed and any failures.
    """
    try:
        archiver = get_archiver()
        cleanup_stats = archiver.cleanup_expired_reports()
        
        logger.info(f"Cleanup status retrieved by user {current_user.id}")
        
        return CleanupResponse(
            expired_reports_found=cleanup_stats["expired_reports_found"],
            successfully_deleted=cleanup_stats["successfully_deleted"],
            failed_deletions=cleanup_stats["failed_deletions"],
            cleanup_timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to get cleanup status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cleanup status: {str(e)}")


@router.get("/export/metadata")
async def export_archive_metadata(
    format: str = Query("json", description="Export format (json or csv)"),
    current_user: User = Depends(get_current_user)
):
    """
    Export archive metadata for backup or analysis.
    
    This endpoint allows administrators to export all archive metadata
    in JSON or CSV format for external analysis or backup purposes.
    """
    try:
        # Check if user has admin privileges
        if not any(role.role.name == 'admin' for role in current_user.roles):
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        archiver = get_archiver()
        export_data = archiver.export_archive_metadata(format)
        
        logger.info(f"Archive metadata exported by admin user {current_user.id}")
        
        # Determine content type
        content_type = "application/json" if format == "json" else "text/csv"
        filename = f"archive_metadata_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        
        return {
            "content": export_data,
            "content_type": content_type,
            "filename": filename
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export archive metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export metadata: {str(e)}")


@router.delete("/reports/{report_id}")
async def delete_archived_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Mark an archived report as deleted.
    
    This endpoint allows users to mark reports as deleted (soft delete).
    The actual file and metadata are preserved but marked as deleted.
    """
    try:
        # Check if user has admin privileges or is the report owner
        archiver = get_archiver()
        metadata = archiver._get_metadata(report_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check permissions
        is_admin = any(role.role.name == 'admin' for role in current_user.roles)
        is_owner = metadata.generated_by == current_user.id
        
        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Insufficient permissions to delete this report")
        
        # Mark as deleted
        db_path = archiver.archive_path / "archive_metadata.db"
        import sqlite3
        
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE archive_metadata SET status = 'deleted', updated_at = ? WHERE report_id = ?",
                (datetime.now().isoformat(), report_id)
            )
        
        logger.info(f"Report marked as deleted by user {current_user.id}: {report_id}")
        
        return {"message": "Report marked as deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete report: {str(e)}")


@router.get("/reports/{report_id}/metadata", response_model=ArchiveMetadataResponse)
async def get_report_metadata(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get metadata for a specific archived report.
    
    This endpoint returns the metadata for a report without retrieving
    the actual report data, useful for browsing and searching.
    """
    try:
        archiver = get_archiver()
        metadata = archiver._get_metadata(report_id)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Report not found")
        
        # Check access permissions
        if not archiver._check_access_permissions(metadata, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"Report metadata retrieved by user {current_user.id}: {report_id}")
        
        return _metadata_to_response(metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report metadata {report_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get report metadata: {str(e)}")


# Convenience endpoints for common operations
@router.post("/archive/weekly", response_model=ArchiveMetadataResponse)
async def archive_weekly_report_endpoint(
    report_data: Dict[str, Any],
    title: str,
    description: Optional[str] = None,
    tags: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Convenience endpoint to archive a weekly report.
    
    This endpoint provides a simplified interface for archiving weekly reports
    with sensible defaults for retention and access levels.
    """
    try:
        metadata = archive_weekly_report(
            report_data=report_data,
            title=title,
            description=description,
            generated_by=current_user.id,
            tags=tags
        )
        
        logger.info(f"Weekly report archived by user {current_user.id}: {metadata.report_id}")
        
        return _metadata_to_response(metadata)
        
    except Exception as e:
        logger.error(f"Failed to archive weekly report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to archive weekly report: {str(e)}")


@router.get("/recent", response_model=List[ArchiveMetadataResponse])
async def get_recent_reports(
    limit: int = Query(10, ge=1, le=50, description="Number of recent reports to retrieve"),
    current_user: User = Depends(get_current_user)
):
    """
    Get the most recently archived reports.
    
    This endpoint provides quick access to the most recent reports
    for dashboard displays and recent activity views.
    """
    try:
        archiver = get_archiver()
        recent_reports = archiver.search_reports(limit=limit)
        
        logger.info(f"Recent reports retrieved by user {current_user.id}: {len(recent_reports)} reports")
        
        return [_metadata_to_response(metadata) for metadata in recent_reports]
        
    except Exception as e:
        logger.error(f"Failed to get recent reports: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent reports: {str(e)}") 