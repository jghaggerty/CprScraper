"""
Comprehensive unit tests for export utilities

Tests the ExportManager and ExportScheduler classes with comprehensive coverage
for PDF, CSV, and Excel export functionality.
"""

import pytest
import json
import io
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

from src.utils.export_utils import ExportManager, ExportScheduler


class TestExportManager:
    """Test the ExportManager class with comprehensive coverage."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.export_manager = ExportManager()
        self.sample_data = [
            {
                'id': 1,
                'form_name': 'WH-347',
                'agency_name': 'Department of Labor',
                'agency_type': 'federal',
                'change_type': 'form_update',
                'severity': 'critical',
                'status': 'pending',
                'detected_at': datetime(2024, 1, 15, 10, 30, 0),
                'ai_confidence_score': 95,
                'ai_change_category': 'requirement_change',
                'is_cosmetic_change': False,
                'impact_assessment': {'impact': 'high', 'affected_clients': 150},
                'description': 'Updated prevailing wage requirements for construction workers',
                'url': 'https://www.dol.gov/forms/wh-347'
            },
            {
                'id': 2,
                'form_name': 'A1-131',
                'agency_name': 'California DIR',
                'agency_type': 'state',
                'change_type': 'field_modification',
                'severity': 'high',
                'status': 'reviewed',
                'detected_at': datetime(2024, 1, 14, 14, 15, 0),
                'ai_confidence_score': 87,
                'ai_change_category': 'form_update',
                'is_cosmetic_change': False,
                'impact_assessment': {'impact': 'medium', 'affected_clients': 75},
                'description': 'New certification requirements for public works projects',
                'url': 'https://www.dir.ca.gov/forms/A1-131'
            },
            {
                'id': 3,
                'form_name': 'MW-3',
                'agency_name': 'Texas TWC',
                'agency_type': 'state',
                'change_type': 'cosmetic_change',
                'severity': 'low',
                'status': 'ignored',
                'detected_at': datetime(2024, 1, 13, 9, 45, 0),
                'ai_confidence_score': 65,
                'ai_change_category': 'cosmetic',
                'is_cosmetic_change': True,
                'impact_assessment': {'impact': 'low', 'affected_clients': 0},
                'description': 'Updated header logo and formatting',
                'url': 'https://www.twc.texas.gov/forms/MW-3'
            }
        ]
        self.export_config = {
            'columns': ['id', 'form_name', 'agency_name', 'severity', 'status', 'detected_at'],
            'include_headers': True,
            'filters': {}
        }
    
    def test_initialization(self):
        """Test ExportManager initialization."""
        assert self.export_manager.supported_formats == ['csv', 'excel', 'pdf']
        assert self.export_manager.max_export_size == 10000
        assert 'csv' in self.export_manager.export_metadata
        assert 'excel' in self.export_manager.export_metadata
        assert 'pdf' in self.export_manager.export_metadata
    
    def test_export_data_invalid_format(self):
        """Test export with invalid format raises error."""
        with pytest.raises(ValueError, match="Unsupported format: invalid"):
            self.export_manager.export_data(
                self.sample_data, 'invalid', self.export_config
            )
    
    def test_export_data_exceeds_size_limit(self):
        """Test export with data exceeding size limit raises error."""
        large_data = [{'id': i} for i in range(10001)]
        
        with pytest.raises(ValueError, match="Export size exceeds maximum limit"):
            self.export_manager.export_data(
                large_data, 'csv', self.export_config
            )
    
    def test_export_data_empty_data(self):
        """Test export with empty data."""
        # CSV export
        result_csv = self.export_manager.export_data([], 'csv', self.export_config)
        assert result_csv == ""
        
        # Excel export
        result_excel = self.export_manager.export_data([], 'excel', self.export_config)
        assert result_excel == b""
        
        # PDF export
        result_pdf = self.export_manager.export_data([], 'pdf', self.export_config)
        assert result_pdf == b""
    
    def test_csv_export(self):
        """Test CSV export functionality."""
        result = self.export_manager.export_data(
            self.sample_data, 'csv', self.export_config
        )
        
        assert isinstance(result, str)
        lines = result.replace('\r', '').strip().split('\n')
        
        # Check header
        assert lines[0] == 'id,form_name,agency_name,severity,status,detected_at'
        
        # Check data rows
        assert '1,WH-347,Department of Labor,critical,pending,2024-01-15 10:30:00' in lines[1]
        assert '2,A1-131,California DIR,high,reviewed,2024-01-14 14:15:00' in lines[2]
        assert '3,MW-3,Texas TWC,low,ignored,2024-01-13 09:45:00' in lines[3]
    
    def test_csv_export_no_headers(self):
        """Test CSV export without headers."""
        config = self.export_config.copy()
        config['include_headers'] = False
        
        result = self.export_manager.export_data(
            self.sample_data, 'csv', config
        )
        
        lines = result.replace('\r', '').strip().split('\n')
        assert not lines[0].startswith('id,form_name')  # No header line
        assert '1,WH-347,Department of Labor,critical,pending,2024-01-15 10:30:00' in lines[0]
    
    def test_csv_export_custom_columns(self):
        """Test CSV export with custom column selection."""
        config = self.export_config.copy()
        config['columns'] = ['id', 'form_name', 'severity']
        
        result = self.export_manager.export_data(
            self.sample_data, 'csv', config
        )
        
        lines = result.replace('\r', '').strip().split('\n')
        assert lines[0] == 'id,form_name,severity'
        assert lines[1] == '1,WH-347,critical'
    
    def test_excel_export(self):
        """Test Excel export functionality."""
        result = self.export_manager.export_data(
            self.sample_data, 'excel', self.export_config
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Verify it's a valid Excel file by trying to read it
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
            tmp.write(result)
            tmp.flush()
            
            try:
                # Read the Excel file to verify structure
                df = pd.read_excel(tmp.name, sheet_name='Data')
                assert len(df) == 3
                assert 'id' in df.columns
                assert 'form_name' in df.columns
                assert 'severity' in df.columns
                
                # Check data
                assert df.iloc[0]['id'] == 1
                assert df.iloc[0]['form_name'] == 'WH-347'
                assert df.iloc[0]['severity'] == 'critical'
            finally:
                try:
                    os.unlink(tmp.name)
                except (PermissionError, OSError):
                    # On Windows, sometimes the file is still locked
                    pass
    
    def test_pdf_export(self):
        """Test PDF export functionality."""
        result = self.export_manager.export_data(
            self.sample_data, 'pdf', self.export_config
        )
        
        assert isinstance(result, bytes)
        assert len(result) > 0
        
        # Check for PDF signature
        assert result.startswith(b'%PDF-')
    
    def test_get_export_metadata(self):
        """Test getting export metadata for specific format."""
        csv_metadata = self.export_manager.get_export_metadata('csv')
        assert csv_metadata['mime_type'] == 'text/csv'
        assert csv_metadata['extension'] == '.csv'
        assert 'description' in csv_metadata
        
        excel_metadata = self.export_manager.get_export_metadata('excel')
        assert excel_metadata['extension'] == '.xlsx'
        
        with pytest.raises(ValueError, match="Unsupported format: invalid"):
            self.export_manager.get_export_metadata('invalid')
    
    def test_get_supported_formats(self):
        """Test getting all supported formats."""
        formats = self.export_manager.get_supported_formats()
        assert len(formats) == 3
        
        format_names = [f['format'] for f in formats]
        assert 'csv' in format_names
        assert 'excel' in format_names
        assert 'pdf' in format_names
        
        for format_info in formats:
            assert 'format' in format_info
            assert 'mime_type' in format_info
            assert 'extension' in format_info
            assert 'description' in format_info
    
    def test_validate_export_data_success(self):
        """Test successful data validation."""
        result = self.export_manager.validate_export_data(self.sample_data, self.export_config)
        assert result is True
    
    def test_validate_export_data_missing_columns(self):
        """Test validation with missing columns."""
        config = {
            'columns': ['id', 'nonexistent_column'],
            'include_headers': True
        }
        
        with pytest.raises(ValueError, match="Requested columns not found in data"):
            self.export_manager.validate_export_data(self.sample_data, config)
    
    def test_format_row_for_csv(self):
        """Test CSV row formatting."""
        row = {
            'date': datetime(2024, 1, 15, 10, 30, 0),
            'dict_field': {'key': 'value'},
            'string_field': 'test',
            'none_field': None,
            'number_field': 42
        }
        
        formatted = self.export_manager._format_row_for_csv(row)
        
        assert formatted['date'] == '2024-01-15 10:30:00'
        assert formatted['dict_field'] == '{"key": "value"}'
        assert formatted['string_field'] == 'test'
        assert formatted['none_field'] == ''
        assert formatted['number_field'] == '42'
    
    def test_generate_filename(self):
        """Test automatic filename generation."""
        result = self.export_manager.export_data(
            self.sample_data, 'csv', self.export_config, filename=None
        )
        
        # Should not raise an error and should generate a valid filename
        assert isinstance(result, str)
    
    @patch('src.utils.export_utils.logger')
    def test_export_error_handling(self, mock_logger):
        """Test error handling during export."""
        # Mock an error in the export process
        with patch.object(self.export_manager, '_export_csv', side_effect=Exception('Test error')):
            with pytest.raises(Exception, match='Test error'):
                self.export_manager.export_data(
                    self.sample_data, 'csv', self.export_config
                )
            
            mock_logger.error.assert_called_once()


class TestExportScheduler:
    """Test the ExportScheduler class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.export_manager = Mock()
        self.scheduler = ExportScheduler(self.export_manager)
        
        self.schedule_config = {
            'frequency': 'daily',
            'recipients': ['test@example.com'],
            'time': '09:00'
        }
        
        self.export_config = {
            'format': 'csv',
            'columns': ['id', 'form_name', 'severity'],
            'filters': {'severity': 'high'}
        }
    
    def test_initialization(self):
        """Test ExportScheduler initialization."""
        assert self.scheduler.export_manager == self.export_manager
        assert self.scheduler.scheduled_exports == {}
    
    def test_schedule_export_success(self):
        """Test successful export scheduling."""
        result = self.scheduler.schedule_export(
            'test_export_1', self.schedule_config, self.export_config
        )
        
        assert result is True
        assert 'test_export_1' in self.scheduler.scheduled_exports
        
        export_info = self.scheduler.scheduled_exports['test_export_1']
        assert export_info['schedule'] == self.schedule_config
        assert export_info['export_config'] == self.export_config
        assert 'created_at' in export_info
        assert 'next_run' in export_info
    
    def test_schedule_export_error(self):
        """Test export scheduling with error."""
        # Mock an error in the scheduling process
        with patch.object(self.scheduler, '_calculate_next_run', side_effect=Exception('Test error')):
            result = self.scheduler.schedule_export(
                'test_export_error', self.schedule_config, self.export_config
            )
            
            assert result is False
            assert 'test_export_error' not in self.scheduler.scheduled_exports
    
    def test_calculate_next_run_daily(self):
        """Test next run calculation for daily frequency."""
        config = {'frequency': 'daily'}
        next_run = self.scheduler._calculate_next_run(config)
        
        expected = datetime.now() + timedelta(days=1)
        assert abs((next_run - expected).total_seconds()) < 60  # Within 1 minute
    
    def test_calculate_next_run_weekly(self):
        """Test next run calculation for weekly frequency."""
        config = {'frequency': 'weekly'}
        next_run = self.scheduler._calculate_next_run(config)
        
        expected = datetime.now() + timedelta(weeks=1)
        assert abs((next_run - expected).total_seconds()) < 60  # Within 1 minute
    
    def test_calculate_next_run_monthly(self):
        """Test next run calculation for monthly frequency."""
        config = {'frequency': 'monthly'}
        next_run = self.scheduler._calculate_next_run(config)
        
        expected = datetime.now() + timedelta(days=30)
        assert abs((next_run - expected).total_seconds()) < 60  # Within 1 minute
    
    def test_calculate_next_run_unknown_frequency(self):
        """Test next run calculation for unknown frequency defaults to daily."""
        config = {'frequency': 'unknown'}
        next_run = self.scheduler._calculate_next_run(config)
        
        expected = datetime.now() + timedelta(days=1)
        assert abs((next_run - expected).total_seconds()) < 60  # Within 1 minute
    
    def test_get_scheduled_exports(self):
        """Test getting scheduled exports."""
        # Schedule a few exports
        self.scheduler.schedule_export('export_1', self.schedule_config, self.export_config)
        self.scheduler.schedule_export('export_2', self.schedule_config, self.export_config)
        
        exports = self.scheduler.get_scheduled_exports()
        
        assert len(exports) == 2
        assert 'export_1' in exports
        assert 'export_2' in exports
        
        # Ensure it returns a copy
        exports['export_3'] = {}
        assert 'export_3' not in self.scheduler.scheduled_exports
    
    def test_cancel_export_success(self):
        """Test successful export cancellation."""
        # Schedule an export first
        self.scheduler.schedule_export('test_export', self.schedule_config, self.export_config)
        assert 'test_export' in self.scheduler.scheduled_exports
        
        # Cancel the export
        result = self.scheduler.cancel_export('test_export')
        
        assert result is True
        assert 'test_export' not in self.scheduler.scheduled_exports
    
    def test_cancel_export_not_found(self):
        """Test cancelling non-existent export."""
        result = self.scheduler.cancel_export('non_existent')
        assert result is False


class TestExportManagerEdgeCases:
    """Test edge cases and error conditions for ExportManager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.export_manager = ExportManager()
    
    def test_export_with_special_characters(self):
        """Test export handling special characters in data."""
        data = [
            {
                'id': 1,
                'name': 'Test with "quotes" and ,commas,',
                'description': 'Line 1\nLine 2\nLine 3',
                'unicode': 'Special chars: é, ñ, 中文, 🎉'
            }
        ]
        
        config = {
            'columns': ['id', 'name', 'description', 'unicode'],
            'include_headers': True
        }
        
        # Test CSV export with special characters
        result_csv = self.export_manager.export_data(data, 'csv', config)
        assert isinstance(result_csv, str)
        assert 'Special chars: é, ñ, 中文, 🎉' in result_csv
        
        # Test Excel export with special characters
        result_excel = self.export_manager.export_data(data, 'excel', config)
        assert isinstance(result_excel, bytes)
        assert len(result_excel) > 0
        
        # Test PDF export with special characters
        result_pdf = self.export_manager.export_data(data, 'pdf', config)
        assert isinstance(result_pdf, bytes)
        assert len(result_pdf) > 0
    
    def test_export_with_mixed_data_types(self):
        """Test export with mixed data types."""
        data = [
            {
                'string_field': 'text',
                'int_field': 42,
                'float_field': 3.14,
                'bool_field': True,
                'date_field': datetime(2024, 1, 15),
                'none_field': None,
                'list_field': [1, 2, 3],
                'dict_field': {'nested': 'value'}
            }
        ]
        
        config = {
            'columns': list(data[0].keys()),
            'include_headers': True
        }
        
        # Test CSV export (should handle all data types)
        result_csv = self.export_manager.export_data(data, 'csv', config)
        assert isinstance(result_csv, str)
        assert len(result_csv) > 0
        assert '[1, 2, 3]' in result_csv  # List should be converted to JSON string
        assert 'nested' in result_csv and 'value' in result_csv  # Dict should be converted to JSON string (with possible escaping)
        
        # Test Excel export (should handle all data types after conversion)
        result_excel = self.export_manager.export_data(data, 'excel', config)
        assert isinstance(result_excel, bytes)
        assert len(result_excel) > 0
        
        # Test PDF export (should handle all data types)
        result_pdf = self.export_manager.export_data(data, 'pdf', config)
        assert isinstance(result_pdf, bytes)
        assert len(result_pdf) > 0
    
    def test_export_large_dataset_within_limit(self):
        """Test export with large dataset within size limit."""
        # Create data with 1000 records (within limit) 
        large_data = []
        for i in range(1000):
            large_data.append({
                'id': i,
                'name': f'Record {i}',
                'value': i * 2,
                'date': datetime.now() + timedelta(days=i)
            })
        
        config = {
            'columns': ['id', 'name', 'value'],
            'include_headers': True
        }
        
        # Test CSV export
        result_csv = self.export_manager.export_data(large_data, 'csv', config)
        assert isinstance(result_csv, str)
        lines = result_csv.replace('\r', '').strip().split('\n')
        assert len(lines) == 1001  # 1000 data rows + 1 header
        
        # Test Excel export (should work but be slower)
        result_excel = self.export_manager.export_data(large_data, 'excel', config)
        assert isinstance(result_excel, bytes)
        assert len(result_excel) > 0


if __name__ == '__main__':
    pytest.main([__file__])