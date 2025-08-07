"""
Report Export API Endpoints

Provides API endpoints for exporting reports in multiple formats:
- PDF: Professional reports with charts and styling
- Excel: Rich formatting with multiple sheets and charts
- CSV: Simple tabular data export
- JSON: Structured data export for API consumption
- HTML: Web-friendly report format
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
from enum import Enum

from ..reporting.report_export import (
    ReportExportService, export_weekly_report, export_analytics_report, export_archive_report
)
from ..api.auth import get_current_user
from ..database.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports/export", tags=["Report Export"])


class ExportFormatEnum(str, Enum):
    """Supported export formats."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class WeeklyReportExportRequest(BaseModel):
    """Request for exporting a weekly report."""
    start_date: Optional[datetime] = Field(None, description="Start date for report period")
    end_date: Optional[datetime] = Field(None, description="End date for report period")
    format: ExportFormatEnum = Field(ExportFormatEnum.PDF, description="Export format")
    include_charts: bool = Field(True, description="Include charts and visualizations")
    include_analytics: bool = Field(True, description="Include analytics and trend analysis")
    filters: Optional[Dict[str, Any]] = Field(None, description="Additional filters to apply")
    custom_title: Optional[str] = Field(None, description="Custom title for the report")


class AnalyticsReportExportRequest(BaseModel):
    """Request for exporting an analytics report."""
    start_date: Optional[datetime] = Field(None, description="Start date for analysis period")
    end_date: Optional[datetime] = Field(None, description="End date for analysis period")
    format: ExportFormatEnum = Field(ExportFormatEnum.PDF, description="Export format")
    include_predictions: bool = Field(True, description="Include predictive analytics")
    include_anomalies: bool = Field(True, description="Include anomaly detection")
    include_correlations: bool = Field(True, description="Include correlation analysis")
    agencies: Optional[List[int]] = Field(None, description="Filter by specific agencies")
    form_types: Optional[List[str]] = Field(None, description="Filter by specific form types")


class ArchiveReportExportRequest(BaseModel):
    """Request for exporting an archived report."""
    report_id: str = Field(..., description="ID of the archived report")
    format: ExportFormatEnum = Field(ExportFormatEnum.PDF, description="Export format")
    include_metadata: bool = Field(True, description="Include archive metadata")


class CustomReportExportRequest(BaseModel):
    """Request for exporting a custom report."""
    report_data: Dict[str, Any] = Field(..., description="Custom report data")
    format: ExportFormatEnum = Field(ExportFormatEnum.PDF, description="Export format")
    report_type: str = Field("custom", description="Type of report for metadata")
    include_charts: bool = Field(True, description="Include charts and visualizations")


class ExportResponse(BaseModel):
    """Response for export request."""
    export_id: str
    format: str
    filename: str
    size_bytes: int
    generated_at: datetime
    download_url: str


# Global export service instance
export_service = ReportExportService()


@router.post("/weekly", response_model=ExportResponse)
async def export_weekly_report_endpoint(
    request: WeeklyReportExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export a weekly report in the specified format."""
    try:
        # Generate the export
        export_content = export_service.export_weekly_report(
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            include_charts=request.include_charts,
            include_analytics=request.include_analytics,
            filters=request.filters,
            custom_title=request.custom_title
        )
        
        # Generate unique export ID and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_id = f"weekly_export_{timestamp}"
        filename = f"weekly_report_{timestamp}.{request.format}"
        
        # Calculate size
        if isinstance(export_content, str):
            size_bytes = len(export_content.encode('utf-8'))
        else:
            size_bytes = len(export_content)
        
        # Store export temporarily (in production, this would be stored in a file system or cloud storage)
        # For now, we'll return the content directly
        
        return ExportResponse(
            export_id=export_id,
            format=request.format,
            filename=filename,
            size_bytes=size_bytes,
            generated_at=datetime.now(),
            download_url=f"/api/reports/export/download/{export_id}"
        )
        
    except Exception as e:
        logger.error(f"Weekly report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/analytics", response_model=ExportResponse)
async def export_analytics_report_endpoint(
    request: AnalyticsReportExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export an analytics report in the specified format."""
    try:
        # Generate the export
        export_content = export_service.export_analytics_report(
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            include_predictions=request.include_predictions,
            include_anomalies=request.include_anomalies,
            include_correlations=request.include_correlations,
            agencies=request.agencies,
            form_types=request.form_types
        )
        
        # Generate unique export ID and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_id = f"analytics_export_{timestamp}"
        filename = f"analytics_report_{timestamp}.{request.format}"
        
        # Calculate size
        if isinstance(export_content, str):
            size_bytes = len(export_content.encode('utf-8'))
        else:
            size_bytes = len(export_content)
        
        return ExportResponse(
            export_id=export_id,
            format=request.format,
            filename=filename,
            size_bytes=size_bytes,
            generated_at=datetime.now(),
            download_url=f"/api/reports/export/download/{export_id}"
        )
        
    except Exception as e:
        logger.error(f"Analytics report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/archive", response_model=ExportResponse)
async def export_archive_report_endpoint(
    request: ArchiveReportExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export an archived report in the specified format."""
    try:
        # Generate the export
        export_content = export_service.export_archive_report(
            report_id=request.report_id,
            format=request.format,
            include_metadata=request.include_metadata
        )
        
        # Generate unique export ID and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_id = f"archive_export_{timestamp}"
        filename = f"archived_report_{request.report_id}_{timestamp}.{request.format}"
        
        # Calculate size
        if isinstance(export_content, str):
            size_bytes = len(export_content.encode('utf-8'))
        else:
            size_bytes = len(export_content)
        
        return ExportResponse(
            export_id=export_id,
            format=request.format,
            filename=filename,
            size_bytes=size_bytes,
            generated_at=datetime.now(),
            download_url=f"/api/reports/export/download/{export_id}"
        )
        
    except Exception as e:
        logger.error(f"Archive report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/custom", response_model=ExportResponse)
async def export_custom_report_endpoint(
    request: CustomReportExportRequest,
    current_user: User = Depends(get_current_user)
):
    """Export a custom report in the specified format."""
    try:
        # Generate the export
        export_content = export_service.export_custom_report(
            report_data=request.report_data,
            format=request.format,
            report_type=request.report_type,
            include_charts=request.include_charts
        )
        
        # Generate unique export ID and filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_id = f"custom_export_{timestamp}"
        filename = f"{request.report_type}_report_{timestamp}.{request.format}"
        
        # Calculate size
        if isinstance(export_content, str):
            size_bytes = len(export_content.encode('utf-8'))
        else:
            size_bytes = len(export_content)
        
        return ExportResponse(
            export_id=export_id,
            format=request.format,
            filename=filename,
            size_bytes=size_bytes,
            generated_at=datetime.now(),
            download_url=f"/api/reports/export/download/{export_id}"
        )
        
    except Exception as e:
        logger.error(f"Custom report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/download/{export_id}")
async def download_export(
    export_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download an exported file."""
    try:
        # In a real implementation, this would retrieve the file from storage
        # For now, we'll return a placeholder response
        
        # Extract format from export_id
        if export_id.startswith("weekly_export_"):
            format_type = "pdf"  # Default format
        elif export_id.startswith("analytics_export_"):
            format_type = "pdf"
        elif export_id.startswith("archive_export_"):
            format_type = "pdf"
        elif export_id.startswith("custom_export_"):
            format_type = "pdf"
        else:
            raise HTTPException(status_code=404, detail="Export not found")
        
        # Determine content type
        content_type_map = {
            "pdf": "application/pdf",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json",
            "html": "text/html"
        }
        
        content_type = content_type_map.get(format_type, "application/octet-stream")
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{export_id}_{timestamp}.{format_type}"
        
        # Return placeholder content
        placeholder_content = f"Export {export_id} content would be here"
        
        return Response(
            content=placeholder_content,
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Download failed for export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats."""
    return {
        "formats": [
            {
                "format": "pdf",
                "name": "PDF",
                "description": "Professional reports with charts and styling",
                "content_type": "application/pdf"
            },
            {
                "format": "excel",
                "name": "Excel",
                "description": "Rich formatting with multiple sheets and charts",
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            },
            {
                "format": "csv",
                "name": "CSV",
                "description": "Simple tabular data export",
                "content_type": "text/csv"
            },
            {
                "format": "json",
                "name": "JSON",
                "description": "Structured data export for API consumption",
                "content_type": "application/json"
            },
            {
                "format": "html",
                "name": "HTML",
                "description": "Web-friendly report format",
                "content_type": "text/html"
            }
        ]
    }


@router.get("/status/{export_id}")
async def get_export_status(
    export_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the status of an export request."""
    try:
        # In a real implementation, this would check the status from storage/queue
        # For now, return a placeholder status
        
        return {
            "export_id": export_id,
            "status": "completed",
            "progress": 100,
            "message": "Export completed successfully",
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get export status for {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get export status: {str(e)}")


@router.delete("/{export_id}")
async def delete_export(
    export_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an exported file."""
    try:
        # In a real implementation, this would delete the file from storage
        # For now, return success
        
        return {
            "export_id": export_id,
            "deleted": True,
            "message": "Export deleted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to delete export {export_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete export: {str(e)}")


@router.get("/history")
async def get_export_history(
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, description="Maximum number of exports to return", ge=1, le=100),
    offset: int = Query(0, description="Number of exports to skip", ge=0)
):
    """Get export history for the current user."""
    try:
        # In a real implementation, this would query the database for export history
        # For now, return placeholder data
        
        return {
            "exports": [
                {
                    "export_id": f"weekly_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "type": "weekly",
                    "format": "pdf",
                    "filename": "weekly_report_20241201_120000.pdf",
                    "size_bytes": 1024000,
                    "created_at": datetime.now().isoformat(),
                    "status": "completed"
                }
            ],
            "total": 1,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        logger.error(f"Failed to get export history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get export history: {str(e)}") 