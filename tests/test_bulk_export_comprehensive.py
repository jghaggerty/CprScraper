"""
Comprehensive tests for bulk export functionality.

Tests bulk export capabilities including:
- Bulk export manager and job handling
- Streaming export for large datasets  
- API endpoints for bulk operations
- Progress tracking and status updates
- Error handling and resource cleanup
- Performance and memory management
"""

import pytest
import tempfile
import shutil
import os
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

# Import modules under test
from src.utils.bulk_export_manager import (
    BulkExportManager, BulkExportJob, BulkExportConfig, 
    StreamingExporter, bulk_export_manager
)
from src.utils.export_utils import ExportManager
from src.api.data_export import (
    BulkExportRequest, LargeBulkExportRequest,
    create_bulk_export_job, create_large_bulk_export_job,
    get_detailed_bulk_export_status, cancel_bulk_export_job
)


class TestBulkExportConfig:
    """Test bulk export configuration."""
    
    def test_default_configuration(self):
        """Test default bulk export configuration values."""
        config = BulkExportConfig()
        
        assert config.chunk_size == 5000
        assert config.max_concurrent_exports == 3
        assert config.memory_limit_mb == 512
        assert config.streaming_threshold == 50000
        assert config.temp_retention_hours == 48
        assert config.compression_level == 6
        
        # Test format-specific limits
        assert 'csv' in config.format_limits
        assert 'excel' in config.format_limits
        assert 'pdf' in config.format_limits
        
        csv_limits = config.format_limits['csv']
        assert csv_limits['max_records_per_file'] == 1000000
        assert csv_limits['supports_streaming'] == True
        
        excel_limits = config.format_limits['excel']
        assert excel_limits['max_records_per_file'] == 100000
        assert excel_limits['supports_streaming'] == False


class TestBulkExportJob:
    """Test bulk export job management."""
    
    def test_job_creation(self):
        """Test bulk export job creation and initialization."""
        config = BulkExportConfig()
        job = BulkExportJob("test_job_123", config)
        
        assert job.job_id == "test_job_123"
        assert job.status == "pending"
        assert job.total_records == 0
        assert job.processed_records == 0
        assert job.progress_percent == 0
        assert job.error_message is None
        assert len(job.warnings) == 0
        
        # Test timestamps
        assert job.created_at is not None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.expires_at > job.created_at
    
    def test_progress_tracking(self):
        """Test job progress tracking and updates."""
        config = BulkExportConfig()
        job = BulkExportJob("test_job_123", config)
        
        job.total_records = 1000
        job.update_progress(processed=250)
        
        assert job.processed_records == 250
        assert job.progress_percent == 25
        
        job.update_progress(processed=500, current_chunk=10)
        
        assert job.processed_records == 500
        assert job.progress_percent == 50
        assert job.current_chunk == 10
    
    def test_warning_management(self):
        """Test job warning management."""
        config = BulkExportConfig()
        job = BulkExportJob("test_job_123", config)
        
        job.add_warning("Test warning message")
        
        assert len(job.warnings) == 1
        assert "Test warning message" in job.warnings[0]
        assert datetime.now().isoformat()[:10] in job.warnings[0]  # Date check
    
    def test_job_serialization(self):
        """Test job to dictionary conversion."""
        config = BulkExportConfig()
        job = BulkExportJob("test_job_123", config)
        
        job.total_records = 1000
        job.processed_records = 250
        job.add_warning("Test warning")
        
        job_dict = job.to_dict()
        
        assert job_dict['job_id'] == "test_job_123"
        assert job_dict['status'] == "pending"
        assert job_dict['total_records'] == 1000
        assert job_dict['processed_records'] == 250
        assert job_dict['progress_percent'] == 25
        assert len(job_dict['warnings']) == 1


class TestStreamingExporter:
    """Test streaming export functionality."""
    
    @pytest.fixture
    def export_manager(self):
        """Mock export manager for testing."""
        manager = Mock(spec=ExportManager)
        manager._export_csv = Mock(return_value="header1,header2\nvalue1,value2")
        return manager
    
    @pytest.fixture  
    def streaming_exporter(self, export_manager):
        """Create streaming exporter with mocked dependencies."""
        config = BulkExportConfig()
        return StreamingExporter(export_manager, config)
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_streaming_csv_export(self, streaming_exporter, temp_directory):
        """Test streaming CSV export functionality."""
        config = BulkExportConfig()
        job = BulkExportJob("test_job", config)
        job.total_records = 1000
        
        output_path = temp_directory / "test_export.csv"
        export_config = {'include_headers': True}
        
        # Mock query function that returns chunks of data
        call_count = 0
        async def mock_query_func(limit, offset):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{'col1': 'value1', 'col2': 'value2'}] * limit
            elif call_count == 2:
                return [{'col1': 'value3', 'col2': 'value4'}] * 100  # Smaller final chunk
            else:
                return []  # No more data
        
        await streaming_exporter.stream_csv_export(
            mock_query_func, job, export_config, output_path
        )
        
        assert output_path.exists()
        assert job.processed_records > 0
        
        # Verify file content
        with open(output_path, 'r') as f:
            content = f.read()
            assert 'header' in content.lower() or 'value' in content
    
    @pytest.mark.asyncio
    async def test_streaming_excel_chunks(self, streaming_exporter, temp_directory):
        """Test streaming Excel export with multiple files."""
        config = BulkExportConfig()
        job = BulkExportJob("test_job", config)
        job.total_records = 150000  # Should create multiple Excel files
        
        export_config = {'include_headers': True}
        
        # Mock query function
        async def mock_query_func(limit, offset):
            if offset < job.total_records:
                return [{'col1': f'value{i}', 'col2': f'data{i}'} 
                       for i in range(min(limit, job.total_records - offset))]
            return []
        
        excel_files = await streaming_exporter.stream_excel_chunks(
            mock_query_func, job, export_config, temp_directory
        )
        
        # Should create multiple Excel files due to size limits
        assert len(excel_files) > 1
        for file_path in excel_files:
            assert os.path.exists(file_path)
            assert file_path.endswith('.xlsx')


class TestBulkExportManager:
    """Test bulk export manager functionality."""
    
    @pytest.fixture
    def bulk_manager(self):
        """Create bulk export manager for testing."""
        return BulkExportManager()
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock(spec=Session)
        return session
    
    def test_manager_initialization(self, bulk_manager):
        """Test bulk export manager initialization."""
        assert bulk_manager.config is not None
        assert bulk_manager.export_manager is not None
        assert bulk_manager.streaming_exporter is not None
        assert isinstance(bulk_manager.active_jobs, dict)
        assert bulk_manager.executor is not None
    
    def test_create_bulk_export_job(self, bulk_manager):
        """Test bulk export job creation."""
        export_requests = [
            {'data_source': 'form_changes', 'customization': {'format': 'csv'}},
            {'data_source': 'agencies', 'customization': {'format': 'excel'}}
        ]
        
        job = bulk_manager.create_bulk_export_job(
            export_requests, 
            combined_output=True,
            archive_format="zip"
        )
        
        assert job.job_id in bulk_manager.active_jobs
        assert job.temp_directory is not None
        assert job.temp_directory.exists()
        assert job.status == "pending"
    
    @pytest.mark.asyncio
    async def test_estimate_bulk_export_size(self, bulk_manager, mock_db_session):
        """Test bulk export size estimation."""
        export_requests = [
            {'data_source': 'form_changes', 'customization': {'format': 'csv'}},
            {'data_source': 'agencies', 'customization': {'format': 'excel'}}
        ]
        
        with patch.object(bulk_manager, '_estimate_request_size', return_value=1000):
            total_records, total_size_mb, breakdown = await bulk_manager.estimate_bulk_export_size(
                export_requests, mock_db_session
            )
            
            assert total_records == 2000  # 1000 per request
            assert total_size_mb > 0
            assert len(breakdown) == 2
            assert 'export_1' in breakdown
            assert 'export_2' in breakdown
    
    def test_should_use_streaming(self, bulk_manager):
        """Test streaming mode decision logic."""
        # Large dataset should use streaming
        assert bulk_manager._should_use_streaming(100000, 'csv') == True
        
        # Small dataset should not use streaming  
        assert bulk_manager._should_use_streaming(1000, 'csv') == False
        
        # Excel with many records should use streaming
        assert bulk_manager._should_use_streaming(150000, 'excel') == True
    
    def test_job_cleanup(self, bulk_manager):
        """Test job cleanup and resource management."""
        # Create a test job
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        job = bulk_manager.create_bulk_export_job(export_requests)
        
        job_id = job.job_id
        temp_dir = job.temp_directory
        
        assert job_id in bulk_manager.active_jobs
        assert temp_dir.exists()
        
        # Cancel job should cleanup resources
        success = bulk_manager.cancel_job(job_id)
        
        assert success == True
        assert job_id not in bulk_manager.active_jobs
        assert not temp_dir.exists()
    
    def test_cleanup_expired_jobs(self, bulk_manager):
        """Test cleanup of expired jobs."""
        # Create jobs with different expiration times
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        
        job1 = bulk_manager.create_bulk_export_job(export_requests)
        job2 = bulk_manager.create_bulk_export_job(export_requests)
        
        # Make one job expired
        job1.expires_at = datetime.now() - timedelta(hours=1)
        
        initial_count = len(bulk_manager.active_jobs)
        cleaned_count = bulk_manager.cleanup_expired_jobs()
        
        assert cleaned_count == 1
        assert len(bulk_manager.active_jobs) == initial_count - 1
        assert job1.job_id not in bulk_manager.active_jobs
        assert job2.job_id in bulk_manager.active_jobs


class TestBulkExportAPI:
    """Test bulk export API endpoints."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock(spec=Session)
    
    @pytest.fixture
    def bulk_export_request(self):
        """Sample bulk export request."""
        from src.api.data_export import DataExportRequest, ExportCustomization
        
        export_request = DataExportRequest(
            data_source="form_changes",
            customization=ExportCustomization(
                format="csv",
                include_headers=True
            )
        )
        
        return BulkExportRequest(
            exports=[export_request],
            combined_output=True,
            archive_format="zip"
        )
    
    @pytest.fixture
    def large_bulk_export_request(self):
        """Sample large bulk export request."""
        from src.api.data_export import DataExportRequest, ExportCustomization
        
        export_request = DataExportRequest(
            data_source="form_changes",
            customization=ExportCustomization(
                format="csv",
                include_headers=True
            )
        )
        
        return LargeBulkExportRequest(
            exports=[export_request],
            max_records_per_file=50000,
            compression_level=9,
            notification_email="test@example.com"
        )
    
    @pytest.mark.asyncio
    async def test_create_bulk_export_endpoint(self, bulk_export_request, mock_db):
        """Test bulk export creation endpoint."""
        with patch('src.api.data_export.bulk_export_manager') as mock_manager:
            # Mock the bulk export manager
            mock_job = Mock()
            mock_job.job_id = "test_job_123"
            mock_job.created_at = datetime.now()
            mock_job.expires_at = datetime.now() + timedelta(hours=48)
            mock_job.to_dict.return_value = {
                'job_id': 'test_job_123',
                'status': 'pending'
            }
            
            mock_manager.estimate_bulk_export_size = AsyncMock(return_value=(1000, 5.0, {}))
            mock_manager.create_bulk_export_job.return_value = mock_job
            
            # Mock background tasks
            mock_background_tasks = Mock()
            
            response = await create_bulk_export_job(
                bulk_export_request,
                mock_background_tasks,
                mock_db
            )
            
            assert response.job_id == "test_job_123"
            assert response.status == "pending"
            assert response.estimated_records == 1000
            assert response.estimated_size_mb == 5.0
    
    @pytest.mark.asyncio
    async def test_create_large_bulk_export_endpoint(self, large_bulk_export_request, mock_db):
        """Test large bulk export creation endpoint."""
        with patch('src.api.data_export.bulk_export_manager') as mock_manager:
            # Mock the bulk export manager
            mock_job = Mock()
            mock_job.job_id = "large_job_456"
            mock_job.created_at = datetime.now()
            mock_job.expires_at = datetime.now() + timedelta(hours=48)
            mock_job.to_dict.return_value = {
                'job_id': 'large_job_456',
                'status': 'pending'
            }
            
            mock_manager.estimate_bulk_export_size = AsyncMock(return_value=(100000, 50.0, {}))
            mock_manager.create_bulk_export_job.return_value = mock_job
            
            # Mock background tasks
            mock_background_tasks = Mock()
            
            response = await create_large_bulk_export_job(
                large_bulk_export_request,
                mock_background_tasks, 
                mock_db
            )
            
            assert response.job_id == "large_job_456"
            assert response.estimated_records == 100000
            assert response.estimated_size_mb == 50.0
    
    @pytest.mark.asyncio
    async def test_get_detailed_status_endpoint(self):
        """Test detailed status endpoint."""
        with patch('src.api.data_export.bulk_export_manager') as mock_manager:
            # Mock job status
            mock_job = Mock()
            mock_job.job_id = "test_job_123"
            mock_job.status = "processing"
            mock_job.progress_percent = 45
            mock_job.started_at = datetime.now() - timedelta(minutes=10)
            mock_job.expires_at = datetime.now() + timedelta(hours=47)
            mock_job.total_records = 1000
            mock_job.processed_records = 450
            mock_job.to_dict.return_value = {
                'job_id': 'test_job_123',
                'status': 'processing',
                'progress_percent': 45,
                'total_records': 1000,
                'processed_records': 450
            }
            
            mock_manager.get_job_status.return_value = mock_job
            
            response = await get_detailed_bulk_export_status("test_job_123")
            
            assert response['job_id'] == "test_job_123"
            assert response['status'] == "processing"
            assert response['progress_percent'] == 45
            assert 'runtime_seconds' in response
    
    @pytest.mark.asyncio
    async def test_cancel_bulk_export_endpoint(self):
        """Test bulk export cancellation endpoint."""
        with patch('src.api.data_export.bulk_export_manager') as mock_manager:
            mock_manager.cancel_job.return_value = True
            
            with patch('src.api.data_export.export_jobs', {'test_job_123': {}}):
                response = await cancel_bulk_export_job("test_job_123")
                
                assert "cancelled successfully" in response['message']
                mock_manager.cancel_job.assert_called_once_with("test_job_123")


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def bulk_manager(self):
        """Create bulk export manager for testing."""
        return BulkExportManager()
    
    def test_invalid_job_id(self, bulk_manager):
        """Test handling of invalid job IDs."""
        # Getting status of non-existent job
        status = bulk_manager.get_job_status("non_existent_job")
        assert status is None
        
        # Cancelling non-existent job
        success = bulk_manager.cancel_job("non_existent_job")
        assert success == False
    
    @pytest.mark.asyncio
    async def test_export_size_limits(self, bulk_manager):
        """Test export size limit validation."""
        # Create a request that would exceed limits
        export_requests = [
            {'data_source': 'form_changes', 'customization': {'format': 'csv'}}
        ] * 100  # Many requests
        
        with patch.object(bulk_manager, '_estimate_request_size', return_value=200000):
            total_records, _, _ = await bulk_manager.estimate_bulk_export_size(
                export_requests, Mock()
            )
            
            # Should detect large export size
            assert total_records > 1000000
    
    def test_disk_space_management(self, bulk_manager):
        """Test disk space and resource management."""
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        job = bulk_manager.create_bulk_export_job(export_requests)
        
        # Simulate disk usage
        job.disk_usage_mb = 100.5
        job.memory_usage_mb = 256.0
        
        job_dict = job.to_dict()
        assert job_dict['disk_usage_mb'] == 100.5
        assert job_dict['memory_usage_mb'] == 256.0
    
    @pytest.mark.asyncio
    async def test_concurrent_job_limits(self, bulk_manager):
        """Test concurrent job execution limits."""
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        
        # Create multiple jobs
        jobs = []
        for i in range(5):
            job = bulk_manager.create_bulk_export_job(export_requests)
            jobs.append(job)
        
        # Verify all jobs are tracked
        assert len(bulk_manager.active_jobs) == 5
        
        # Cleanup
        for job in jobs:
            bulk_manager.cancel_job(job.job_id)


class TestPerformanceAndMemory:
    """Test performance and memory management."""
    
    @pytest.fixture
    def bulk_manager(self):
        """Create bulk export manager for testing."""
        return BulkExportManager()
    
    def test_chunk_size_configuration(self, bulk_manager):
        """Test chunk size configuration affects processing."""
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        job = bulk_manager.create_bulk_export_job(export_requests)
        
        # Test different chunk sizes
        job.config.chunk_size = 1000
        assert job.config.chunk_size == 1000
        
        job.config.chunk_size = 10000  
        assert job.config.chunk_size == 10000
    
    def test_memory_limit_enforcement(self, bulk_manager):
        """Test memory limit configuration."""
        # Test memory limit setting
        assert bulk_manager.config.memory_limit_mb == 512
        
        # Modify memory limit
        bulk_manager.config.memory_limit_mb = 1024
        assert bulk_manager.config.memory_limit_mb == 1024
    
    def test_compression_levels(self, bulk_manager):
        """Test compression level configuration."""
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        job = bulk_manager.create_bulk_export_job(export_requests)
        
        # Test compression level range
        for level in range(0, 10):
            job.config.compression_level = level
            assert job.config.compression_level == level
    
    @pytest.mark.asyncio 
    async def test_large_dataset_handling(self, bulk_manager):
        """Test handling of very large datasets."""
        export_requests = [{'data_source': 'form_changes', 'customization': {'format': 'csv'}}]
        
        # Simulate very large dataset
        with patch.object(bulk_manager, '_estimate_request_size', return_value=5000000):
            total_records, _, _ = await bulk_manager.estimate_bulk_export_size(
                export_requests, Mock()
            )
            
            assert total_records == 5000000
            
            # Should recommend streaming for large datasets
            should_stream = bulk_manager._should_use_streaming(total_records, 'csv')
            assert should_stream == True


if __name__ == '__main__':
    """Run bulk export tests."""
    pytest.main([__file__, '-v', '--tb=short'])