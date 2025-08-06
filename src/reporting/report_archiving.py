"""
Report Archiving and Historical Access System

This module provides comprehensive report archiving capabilities including:
- Automated report storage and indexing
- Historical report retrieval and search
- Report versioning and metadata management
- Archive cleanup and retention policies
- Access control and audit logging
"""

import logging
import json
import hashlib
import gzip
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import shutil

from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import joinedload

from ..database.connection import get_db
from ..database.models import User, UserRole, Role
from ..utils.export_utils import ExportManager

logger = logging.getLogger(__name__)


class ArchiveStatus(Enum):
    """Status of archived reports."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    EXPIRED = "expired"


class ReportType(Enum):
    """Types of reports that can be archived."""
    WEEKLY_SUMMARY = "weekly_summary"
    DAILY_SUMMARY = "daily_summary"
    MONTHLY_DETAILED = "monthly_detailed"
    CUSTOM_REPORT = "custom_report"
    EXECUTIVE_SUMMARY = "executive_summary"
    COMPLIANCE_AUDIT = "compliance_audit"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class ArchiveMetadata:
    """Metadata for archived reports."""
    report_id: str
    report_type: ReportType
    title: str
    description: Optional[str]
    generated_at: datetime
    report_period_start: datetime
    report_period_end: datetime
    generated_by: int
    file_size_bytes: int
    file_hash: str
    format: str
    version: str
    tags: List[str]
    filters_applied: Dict[str, Any]
    status: ArchiveStatus
    retention_days: int
    access_level: str
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = asdict(self)
        data['report_type'] = self.report_type.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArchiveMetadata':
        """Create from dictionary."""
        data['report_type'] = ReportType(data['report_type'])
        data['status'] = ArchiveStatus(data['status'])
        return cls(**data)


class ReportArchiver:
    """Main report archiving service."""
    
    def __init__(self, archive_path: str = "archives", max_file_size_mb: int = 100):
        """
        Initialize the report archiver.
        
        Args:
            archive_path: Base path for storing archived reports
            max_file_size_mb: Maximum file size in MB before compression
        """
        self.archive_path = Path(archive_path)
        self.archive_path.mkdir(exist_ok=True)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.export_utils = ExportManager()
        
        # Initialize archive database
        self._init_archive_db()
    
    def _init_archive_db(self):
        """Initialize the archive metadata database."""
        db_path = self.archive_path / "archive_metadata.db"
        
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS archive_metadata (
                    report_id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    generated_at TEXT NOT NULL,
                    report_period_start TEXT NOT NULL,
                    report_period_end TEXT NOT NULL,
                    generated_by INTEGER NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    format TEXT NOT NULL,
                    version TEXT NOT NULL,
                    tags TEXT,
                    filters_applied TEXT,
                    status TEXT NOT NULL,
                    retention_days INTEGER NOT NULL,
                    access_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for better query performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_report_type ON archive_metadata(report_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generated_at ON archive_metadata(generated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON archive_metadata(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_generated_by ON archive_metadata(generated_by)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_access_level ON archive_metadata(access_level)")
    
    def archive_report(
        self,
        report_data: Dict[str, Any],
        report_type: ReportType,
        title: str,
        description: Optional[str] = None,
        generated_by: int = None,
        format: str = 'json',
        tags: Optional[List[str]] = None,
        retention_days: int = 2555,  # 7 years default
        access_level: str = 'standard'
    ) -> ArchiveMetadata:
        """
        Archive a report with metadata.
        
        Args:
            report_data: The report data to archive
            report_type: Type of report being archived
            title: Human-readable title for the report
            description: Optional description
            generated_by: User ID who generated the report
            format: Format of the archived data
            tags: Optional tags for categorization
            retention_days: Number of days to retain the report
            access_level: Access level required to view the report
            
        Returns:
            ArchiveMetadata object for the archived report
        """
        # Generate unique report ID
        report_id = self._generate_report_id(report_type, title, datetime.now())
        
        # Determine report period from data
        report_period_start = report_data.get('report_metadata', {}).get('start_date')
        report_period_end = report_data.get('report_metadata', {}).get('end_date')
        
        if not report_period_start:
            report_period_start = datetime.now() - timedelta(days=7)
        if not report_period_end:
            report_period_end = datetime.now()
        
        # Serialize and compress report data
        serialized_data = json.dumps(report_data, default=str)
        compressed_data = gzip.compress(serialized_data.encode('utf-8'))
        
        # Calculate file hash for integrity
        file_hash = hashlib.sha256(compressed_data).hexdigest()
        
        # Determine file path and save
        file_path = self._get_file_path(report_id, format)
        with open(file_path, 'wb') as f:
            f.write(compressed_data)
        
        # Create metadata
        metadata = ArchiveMetadata(
            report_id=report_id,
            report_type=report_type,
            title=title,
            description=description,
            generated_at=datetime.now(),
            report_period_start=report_period_start,
            report_period_end=report_period_end,
            generated_by=generated_by or 0,
            file_size_bytes=len(compressed_data),
            file_hash=file_hash,
            format=format,
            version="1.0",
            tags=tags or [],
            filters_applied=report_data.get('report_metadata', {}).get('filters_applied', {}),
            status=ArchiveStatus.ACTIVE,
            retention_days=retention_days,
            access_level=access_level,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Save metadata to database
        self._save_metadata(metadata)
        
        logger.info(f"Report archived successfully: {report_id}")
        return metadata
    
    def retrieve_report(self, report_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve an archived report.
        
        Args:
            report_id: ID of the report to retrieve
            user_id: ID of the user requesting the report (for access control)
            
        Returns:
            Report data if found and accessible, None otherwise
        """
        metadata = self._get_metadata(report_id)
        if not metadata:
            logger.warning(f"Report not found: {report_id}")
            return None
        
        # Check access permissions
        if not self._check_access_permissions(metadata, user_id):
            logger.warning(f"Access denied to report {report_id} for user {user_id}")
            return None
        
        # Check if file exists
        file_path = self._get_file_path(report_id, metadata.format)
        if not file_path.exists():
            logger.error(f"Archive file not found: {file_path}")
            return None
        
        # Verify file integrity
        if not self._verify_file_integrity(file_path, metadata.file_hash):
            logger.error(f"File integrity check failed for report {report_id}")
            return None
        
        # Read and decompress data
        try:
            with open(file_path, 'rb') as f:
                compressed_data = f.read()
            
            decompressed_data = gzip.decompress(compressed_data)
            report_data = json.loads(decompressed_data.decode('utf-8'))
            
            # Update access timestamp
            self._update_access_timestamp(report_id)
            
            logger.info(f"Report retrieved successfully: {report_id}")
            return report_data
            
        except Exception as e:
            logger.error(f"Error retrieving report {report_id}: {e}")
            return None
    
    def search_reports(
        self,
        report_type: Optional[ReportType] = None,
        title_search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tags: Optional[List[str]] = None,
        generated_by: Optional[int] = None,
        access_level: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ArchiveMetadata]:
        """
        Search archived reports based on various criteria.
        
        Args:
            report_type: Filter by report type
            title_search: Search in report titles
            date_from: Start date for search
            date_to: End date for search
            tags: Filter by tags
            generated_by: Filter by user who generated the report
            access_level: Filter by access level
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching ArchiveMetadata objects
        """
        query = "SELECT * FROM archive_metadata WHERE status != 'deleted'"
        params = []
        
        if report_type:
            query += " AND report_type = ?"
            params.append(report_type.value)
        
        if title_search:
            query += " AND title LIKE ?"
            params.append(f"%{title_search}%")
        
        if date_from:
            query += " AND generated_at >= ?"
            params.append(date_from.isoformat())
        
        if date_to:
            query += " AND generated_at <= ?"
            params.append(date_to.isoformat())
        
        if generated_by:
            query += " AND generated_by = ?"
            params.append(generated_by)
        
        if access_level:
            query += " AND access_level = ?"
            params.append(access_level)
        
        if tags:
            # Simple tag matching - in production, you might want more sophisticated search
            for tag in tags:
                query += " AND tags LIKE ?"
                params.append(f"%{tag}%")
        
        query += " ORDER BY generated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        db_path = self.archive_path / "archive_metadata.db"
        results = []
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(query, params)
            for row in cursor.fetchall():
                metadata = self._row_to_metadata(row)
                results.append(metadata)
        
        return results
    
    def get_archive_statistics(self) -> Dict[str, Any]:
        """Get statistics about the archive."""
        db_path = self.archive_path / "archive_metadata.db"
        
        with sqlite3.connect(db_path) as conn:
            # Total reports
            total_reports = conn.execute(
                "SELECT COUNT(*) FROM archive_metadata WHERE status != 'deleted'"
            ).fetchone()[0]
            
            # Reports by type
            type_stats = {}
            cursor = conn.execute(
                "SELECT report_type, COUNT(*) FROM archive_metadata WHERE status != 'deleted' GROUP BY report_type"
            )
            for row in cursor.fetchall():
                type_stats[row[0]] = row[1]
            
            # Total storage used
            total_size = conn.execute(
                "SELECT SUM(file_size_bytes) FROM archive_metadata WHERE status != 'deleted'"
            ).fetchone()[0] or 0
            
            # Reports by status
            status_stats = {}
            cursor = conn.execute(
                "SELECT status, COUNT(*) FROM archive_metadata GROUP BY status"
            )
            for row in cursor.fetchall():
                status_stats[row[0]] = row[1]
            
            # Oldest and newest reports
            oldest = conn.execute(
                "SELECT generated_at FROM archive_metadata WHERE status != 'deleted' ORDER BY generated_at ASC LIMIT 1"
            ).fetchone()
            
            newest = conn.execute(
                "SELECT generated_at FROM archive_metadata WHERE status != 'deleted' ORDER BY generated_at DESC LIMIT 1"
            ).fetchone()
        
        return {
            'total_reports': total_reports,
            'reports_by_type': type_stats,
            'total_storage_bytes': total_size,
            'total_storage_mb': round(total_size / (1024 * 1024), 2),
            'reports_by_status': status_stats,
            'oldest_report': oldest[0] if oldest else None,
            'newest_report': newest[0] if newest else None
        }
    
    def cleanup_expired_reports(self) -> Dict[str, int]:
        """
        Clean up expired reports based on retention policies.
        
        Returns:
            Dictionary with cleanup statistics
        """
        db_path = self.archive_path / "archive_metadata.db"
        expired_reports = []
        
        # Find expired reports
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT report_id, file_size_bytes, format 
                FROM archive_metadata 
                WHERE status != 'deleted' 
                AND generated_at < datetime('now', '-' || retention_days || ' days')
            """)
            expired_reports = cursor.fetchall()
        
        deleted_count = 0
        failed_count = 0
        
        for report_id, file_size, format in expired_reports:
            try:
                # Delete file
                file_path = self._get_file_path(report_id, format)
                if file_path.exists():
                    file_path.unlink()
                
                # Update metadata status
                with sqlite3.connect(db_path) as conn:
                    conn.execute(
                        "UPDATE archive_metadata SET status = 'expired', updated_at = ? WHERE report_id = ?",
                        (datetime.now().isoformat(), report_id)
                    )
                
                deleted_count += 1
                logger.info(f"Expired report cleaned up: {report_id}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to cleanup expired report {report_id}: {e}")
        
        return {
            'expired_reports_found': len(expired_reports),
            'successfully_deleted': deleted_count,
            'failed_deletions': failed_count
        }
    
    def export_archive_metadata(self, format: str = 'json') -> bytes:
        """
        Export archive metadata for backup or analysis.
        
        Args:
            format: Export format ('json', 'csv')
            
        Returns:
            Exported data as bytes
        """
        db_path = self.archive_path / "archive_metadata.db"
        metadata_list = []
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT * FROM archive_metadata")
            for row in cursor.fetchall():
                metadata = self._row_to_metadata(row)
                metadata_list.append(metadata.to_dict())
        
        if format == 'json':
            return json.dumps(metadata_list, default=str, indent=2).encode('utf-8')
        elif format == 'csv':
            # Convert to CSV format
            if not metadata_list:
                return b""
            
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=metadata_list[0].keys())
            writer.writeheader()
            writer.writerows(metadata_list)
            
            return output.getvalue().encode('utf-8')
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _generate_report_id(self, report_type: ReportType, title: str, timestamp: datetime) -> str:
        """Generate a unique report ID."""
        base = f"{report_type.value}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        title_slug = "".join(c.lower() if c.isalnum() else "_" for c in title)[:20]
        return f"{base}_{title_slug}"
    
    def _get_file_path(self, report_id: str, format: str) -> Path:
        """Get the file path for a report."""
        return self.archive_path / f"{report_id}.{format}.gz"
    
    def _save_metadata(self, metadata: ArchiveMetadata):
        """Save metadata to the database."""
        db_path = self.archive_path / "archive_metadata.db"
        
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO archive_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metadata.report_id,
                metadata.report_type.value,
                metadata.title,
                metadata.description,
                metadata.generated_at.isoformat(),
                metadata.report_period_start.isoformat(),
                metadata.report_period_end.isoformat(),
                metadata.generated_by,
                metadata.file_size_bytes,
                metadata.file_hash,
                metadata.format,
                metadata.version,
                json.dumps(metadata.tags),
                json.dumps(metadata.filters_applied),
                metadata.status.value,
                metadata.retention_days,
                metadata.access_level,
                metadata.created_at.isoformat(),
                metadata.updated_at.isoformat()
            ))
    
    def _get_metadata(self, report_id: str) -> Optional[ArchiveMetadata]:
        """Get metadata for a report."""
        db_path = self.archive_path / "archive_metadata.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT * FROM archive_metadata WHERE report_id = ?", (report_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_metadata(row)
            return None
    
    def _row_to_metadata(self, row) -> ArchiveMetadata:
        """Convert database row to ArchiveMetadata object."""
        return ArchiveMetadata(
            report_id=row[0],
            report_type=ReportType(row[1]),
            title=row[2],
            description=row[3],
            generated_at=datetime.fromisoformat(row[4]),
            report_period_start=datetime.fromisoformat(row[5]),
            report_period_end=datetime.fromisoformat(row[6]),
            generated_by=row[7],
            file_size_bytes=row[8],
            file_hash=row[9],
            format=row[10],
            version=row[11],
            tags=json.loads(row[12]) if row[12] else [],
            filters_applied=json.loads(row[13]) if row[13] else {},
            status=ArchiveStatus(row[14]),
            retention_days=row[15],
            access_level=row[16],
            created_at=datetime.fromisoformat(row[17]),
            updated_at=datetime.fromisoformat(row[18])
        )
    
    def _check_access_permissions(self, metadata: ArchiveMetadata, user_id: Optional[int]) -> bool:
        """Check if user has access to the report."""
        # Public reports
        if metadata.access_level == 'public':
            return True
        
        # Standard reports - basic access
        if metadata.access_level == 'standard':
            return True
        
        # Restricted reports - require user authentication
        if metadata.access_level == 'restricted':
            return user_id is not None
        
        # Admin reports - require admin role
        if metadata.access_level == 'admin':
            if not user_id:
                return False
            
            # Check if user has admin role
            with get_db() as db:
                user_role = db.query(UserRole).filter(
                    UserRole.user_id == user_id,
                    UserRole.role.has(Role.name == 'admin')
                ).first()
                return user_role is not None
        
        return False
    
    def _verify_file_integrity(self, file_path: Path, expected_hash: str) -> bool:
        """Verify file integrity using hash."""
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            actual_hash = hashlib.sha256(file_data).hexdigest()
            return actual_hash == expected_hash
        except Exception:
            return False
    
    def _update_access_timestamp(self, report_id: str):
        """Update the last access timestamp for a report."""
        db_path = self.archive_path / "archive_metadata.db"
        
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE archive_metadata SET updated_at = ? WHERE report_id = ?",
                (datetime.now().isoformat(), report_id)
            )


# Global archiver instance
_archiver = None

def get_archiver() -> ReportArchiver:
    """Get the global archiver instance."""
    global _archiver
    if _archiver is None:
        _archiver = ReportArchiver()
    return _archiver


def archive_weekly_report(
    report_data: Dict[str, Any],
    title: str,
    description: Optional[str] = None,
    generated_by: int = None,
    tags: Optional[List[str]] = None
) -> ArchiveMetadata:
    """
    Convenience function to archive a weekly report.
    
    Args:
        report_data: Weekly report data
        title: Report title
        description: Optional description
        generated_by: User ID who generated the report
        tags: Optional tags
        
    Returns:
        ArchiveMetadata for the archived report
    """
    archiver = get_archiver()
    return archiver.archive_report(
        report_data=report_data,
        report_type=ReportType.WEEKLY_SUMMARY,
        title=title,
        description=description,
        generated_by=generated_by,
        tags=tags,
        retention_days=2555,  # 7 years for weekly reports
        access_level='standard'
    )


def retrieve_archived_report(report_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    Convenience function to retrieve an archived report.
    
    Args:
        report_id: ID of the report to retrieve
        user_id: ID of the user requesting the report
        
    Returns:
        Report data if found and accessible
    """
    archiver = get_archiver()
    return archiver.retrieve_report(report_id, user_id)


def search_archived_reports(
    report_type: Optional[ReportType] = None,
    title_search: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50
) -> List[ArchiveMetadata]:
    """
    Convenience function to search archived reports.
    
    Args:
        report_type: Filter by report type
        title_search: Search in report titles
        date_from: Start date for search
        date_to: End date for search
        tags: Filter by tags
        limit: Maximum number of results
        
    Returns:
        List of matching ArchiveMetadata objects
    """
    archiver = get_archiver()
    return archiver.search_reports(
        report_type=report_type,
        title_search=title_search,
        date_from=date_from,
        date_to=date_to,
        tags=tags,
        limit=limit
    ) 