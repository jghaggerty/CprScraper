"""
Unit tests for AI-Enhanced Monitoring Service

Tests the integration between web scraping, AI analysis, and change detection
for the certified payroll compliance monitoring system.

Extended to cover all new functionality including enhanced analysis service,
change classifier, error handling, monitoring statistics, and comprehensive
agency monitoring.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any

from src.monitors.ai_enhanced_monitor import AIEnhancedMonitor, monitor_agency_with_ai
from src.database.models import Agency, Form, FormChange, MonitoringRun
from src.analysis import AnalysisService, AnalysisRequest, AnalysisResponse
from src.analysis.enhanced_analysis_service import EnhancedAnalysisService
from src.analysis.change_classifier import ChangeClassifier
from src.utils.enhanced_config_manager import EnhancedConfigManager
from src.monitors.error_handler import GovernmentWebsiteErrorHandler
from src.monitors.monitoring_statistics import MonitoringStatistics


class TestAIEnhancedMonitor:
    """Test suite for AI-Enhanced Monitoring Service."""
    
    @pytest.fixture
    def mock_enhanced_analysis_service(self):
        """Mock enhanced analysis service for testing."""
        mock_service = Mock(spec=EnhancedAnalysisService)
        mock_service.analyze_document_changes = AsyncMock()
        mock_service.analyze_document_changes_enhanced = AsyncMock()
        mock_service.health_check = AsyncMock()
        mock_service.health_check_enhanced = AsyncMock()
        return mock_service
    
    @pytest.fixture
    def mock_analysis_service(self):
        """Mock standard analysis service for testing."""
        mock_service = Mock(spec=AnalysisService)
        mock_service.analyze_document_changes = AsyncMock()
        mock_service.health_check = AsyncMock()
        return mock_service
    
    @pytest.fixture
    def mock_change_classifier(self):
        """Mock change classifier for testing."""
        mock_classifier = Mock(spec=ChangeClassifier)
        mock_classifier.classify_change = Mock()
        mock_classifier.enhance_with_ai_classification = Mock()
        return mock_classifier
    
    @pytest.fixture
    def mock_enhanced_config_manager(self):
        """Mock enhanced configuration manager for testing."""
        mock_manager = Mock(spec=EnhancedConfigManager)
        mock_manager.get_coverage_report = Mock()
        mock_manager.get_optimized_monitoring_batches = Mock()
        mock_manager.validate_configuration_health = Mock()
        return mock_manager
    
    @pytest.fixture
    def mock_error_handler(self):
        """Mock error handler for testing."""
        mock_handler = Mock(spec=GovernmentWebsiteErrorHandler)
        mock_handler.get_error_stats = Mock()
        mock_handler.reset_error_statistics = Mock()
        return mock_handler
    
    @pytest.fixture
    def mock_monitoring_statistics(self):
        """Mock monitoring statistics for testing."""
        mock_stats = Mock(spec=MonitoringStatistics)
        mock_stats.start_monitoring_session = AsyncMock()
        mock_stats.get_comprehensive_statistics = AsyncMock()
        mock_stats.update_coverage_metrics = AsyncMock()
        return mock_stats
    
    @pytest.fixture
    def mock_web_scraper(self):
        """Mock web scraper for testing."""
        mock_scraper = Mock()
        mock_scraper.fetch_page_content = AsyncMock()
        mock_scraper.calculate_content_hash = Mock(return_value="test_hash_123")
        mock_scraper.__aenter__ = AsyncMock(return_value=mock_scraper)
        mock_scraper.__aexit__ = AsyncMock(return_value=None)
        return mock_scraper
    
    @pytest.fixture
    def sample_agency(self):
        """Sample agency for testing."""
        agency = Mock(spec=Agency)
        agency.id = 1
        agency.name = "Test Department of Labor"
        agency.base_url = "https://test.dol.gov"
        return agency
    
    @pytest.fixture
    def sample_form(self, sample_agency):
        """Sample form for testing."""
        form = Mock(spec=Form)
        form.id = 1
        form.name = "WH-347"
        form.title = "Statement of Compliance"
        form.form_url = "https://test.dol.gov/wh347.pdf"
        form.is_active = True
        form.agency = sample_agency
        form.agency_id = sample_agency.id
        form.last_checked = None
        return form
    
    @pytest.fixture
    def sample_ai_analysis_result(self):
        """Sample AI analysis result for testing."""
        mock_result = Mock(spec=AnalysisResponse)
        mock_result.analysis_id = "test_analysis_123"
        mock_result.has_meaningful_changes = True
        mock_result.timestamp = datetime.utcnow()
        
        # Mock classification
        mock_classification = Mock()
        mock_classification.category = "form_update"
        mock_classification.severity = "high"
        mock_classification.priority_score = 85
        mock_classification.confidence = 92
        mock_classification.is_cosmetic = False
        mock_result.classification = mock_classification
        
        # Mock semantic analysis
        mock_semantic = Mock()
        mock_semantic.similarity_score = 75
        mock_semantic.significant_differences = ["Updated field requirements", "New validation rules"]
        mock_semantic.change_indicators = ["form_fields", "validation"]
        mock_result.semantic_analysis = mock_semantic
        
        # Mock LLM analysis
        mock_llm = Mock()
        mock_llm.reasoning = "Significant changes detected in form requirements"
        mock_llm.tokens_used = 150
        mock_result.llm_analysis = mock_llm
        
        # Mock processing summary with enhanced features
        mock_result.processing_summary = {
            "processing_time_ms": 1250,
            "semantic_model": "all-MiniLM-L6-v2",
            "classification_method": "llm",
            "cache_used": False,
            "analysis_version": "1.0",
            "llm_tokens_used": 150,
            "enhanced_features": {
                "false_positive_detection": True,
                "semantic_change_detection": True,
                "content_relevance_validation": True,
                "compliance_validation": {
                    "overall_compliance_score": 85,
                    "wage_rate_requirements": 90,
                    "certification_requirements": 80
                },
                "structure_validation": {
                    "structure_integrity_score": 88,
                    "missing_required_elements": []
                }
            }
        }
        
        # Mock confidence breakdown
        mock_result.confidence_breakdown = {
            "semantic": 75,
            "classification": 92,
            "overall": 84
        }
        
        return mock_result
    
    @pytest.fixture
    def monitor(self, mock_enhanced_analysis_service, mock_change_classifier, 
                mock_enhanced_config_manager, mock_error_handler, mock_monitoring_statistics):
        """AI-enhanced monitor instance for testing."""
        with patch('src.monitors.ai_enhanced_monitor.EnhancedAnalysisService', return_value=mock_enhanced_analysis_service), \
             patch('src.monitors.ai_enhanced_monitor.get_change_classifier', return_value=mock_change_classifier), \
             patch('src.monitors.ai_enhanced_monitor.get_enhanced_config_manager', return_value=mock_enhanced_config_manager), \
             patch('src.monitors.ai_enhanced_monitor.get_error_handler', return_value=mock_error_handler), \
             patch('src.monitors.ai_enhanced_monitor.get_monitoring_statistics', return_value=mock_monitoring_statistics):
            return AIEnhancedMonitor(
                confidence_threshold=70,
                enable_llm_analysis=True,
                batch_size=3
            )
    
    def test_monitor_initialization_with_enhanced_services(self, mock_enhanced_analysis_service, 
                                                          mock_change_classifier, mock_enhanced_config_manager,
                                                          mock_error_handler, mock_monitoring_statistics):
        """Test monitor initialization with all enhanced services."""
        with patch('src.monitors.ai_enhanced_monitor.EnhancedAnalysisService', return_value=mock_enhanced_analysis_service), \
             patch('src.monitors.ai_enhanced_monitor.get_change_classifier', return_value=mock_change_classifier), \
             patch('src.monitors.ai_enhanced_monitor.get_enhanced_config_manager', return_value=mock_enhanced_config_manager), \
             patch('src.monitors.ai_enhanced_monitor.get_error_handler', return_value=mock_error_handler), \
             patch('src.monitors.ai_enhanced_monitor.get_monitoring_statistics', return_value=mock_monitoring_statistics):
            
            monitor = AIEnhancedMonitor(
                confidence_threshold=80,
                enable_llm_analysis=False,
                batch_size=5
            )
            
            assert monitor.confidence_threshold == 80
            assert monitor.enable_llm_analysis == False
            assert monitor.batch_size == 5
            assert monitor.analysis_service == mock_enhanced_analysis_service
            assert monitor.change_classifier == mock_change_classifier
            assert monitor.config_manager == mock_enhanced_config_manager
            assert monitor.error_handler == mock_error_handler
            assert monitor.monitoring_stats == mock_monitoring_statistics
            assert isinstance(monitor.content_cache, dict)
    
    def test_monitor_initialization_fallback_to_standard_analysis(self, mock_analysis_service):
        """Test monitor initialization when enhanced analysis service fails."""
        with patch('src.monitors.ai_enhanced_monitor.EnhancedAnalysisService', side_effect=Exception("Enhanced service error")), \
             patch('src.monitors.ai_enhanced_monitor.AnalysisService', return_value=mock_analysis_service), \
             patch('src.monitors.ai_enhanced_monitor.get_change_classifier', return_value=Mock()), \
             patch('src.monitors.ai_enhanced_monitor.get_enhanced_config_manager', return_value=Mock()), \
             patch('src.monitors.ai_enhanced_monitor.get_error_handler', return_value=Mock()), \
             patch('src.monitors.ai_enhanced_monitor.get_monitoring_statistics', return_value=Mock()):
            
            monitor = AIEnhancedMonitor()
            
            assert monitor.analysis_service == mock_analysis_service
            assert monitor.confidence_threshold == 70  # Default value
    
    def test_monitor_initialization_all_services_fail(self):
        """Test monitor initialization when all services fail."""
        with patch('src.monitors.ai_enhanced_monitor.EnhancedAnalysisService', side_effect=Exception("Enhanced service error")), \
             patch('src.monitors.ai_enhanced_monitor.AnalysisService', side_effect=Exception("Standard service error")), \
             patch('src.monitors.ai_enhanced_monitor.get_change_classifier', side_effect=Exception("Classifier error")), \
             patch('src.monitors.ai_enhanced_monitor.get_enhanced_config_manager', side_effect=Exception("Config error")), \
             patch('src.monitors.ai_enhanced_monitor.get_error_handler', side_effect=Exception("Error handler error")), \
             patch('src.monitors.ai_enhanced_monitor.get_monitoring_statistics', side_effect=Exception("Stats error")):
            
            monitor = AIEnhancedMonitor()
            
            assert monitor.analysis_service is None
            assert monitor.change_classifier is None
            assert monitor.config_manager is None
            assert monitor.error_handler is None
            assert monitor.monitoring_stats is None
            assert monitor.confidence_threshold == 70  # Default value
    
    @pytest.mark.asyncio
    async def test_monitor_agency_with_ai_success_with_enhanced_features(self, monitor, sample_agency, sample_form, 
                                                                       mock_web_scraper, sample_ai_analysis_result):
        """Test successful agency monitoring with enhanced AI analysis."""
        # Setup mocks
        sample_agency.forms = [sample_form]
        
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db, \
             patch('src.monitors.ai_enhanced_monitor.WebScraper', return_value=mock_web_scraper), \
             patch('src.monitors.ai_enhanced_monitor.record_monitoring_event') as mock_record_event:
            
            # Mock database session
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = sample_agency
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock web scraper responses
            mock_web_scraper.fetch_page_content.return_value = (
                "<html>Updated form content</html>", 200, {"content_type": "text/html"}
            )
            
            # Mock enhanced AI analysis
            monitor.analysis_service.analyze_document_changes_enhanced.return_value = sample_ai_analysis_result
            
            # Mock previous content retrieval
            monitor._get_previous_content = AsyncMock(return_value="<html>Old form content</html>")
            monitor._store_current_content = AsyncMock()
            
            # Mock monitoring session
            monitor.monitoring_stats.start_monitoring_session.return_value = "session_123"
            
            # Execute monitoring
            result = await monitor.monitor_agency_with_ai(sample_agency.id)
            
            # Verify results
            assert result["agency_id"] == sample_agency.id
            assert result["agency_name"] == sample_agency.name
            assert result["total_forms"] == 1
            assert result["forms_analyzed"] == 1
            assert result["changes_detected"] == 1
            assert result["ai_analyses_performed"] == 1
            assert len(result["forms_with_changes"]) == 1
            assert result["errors"] == []
            assert result["session_id"] == "session_123"
            
            # Verify analysis summary
            summary = result["analysis_summary"]
            assert summary["high_priority_changes"] == 1
            assert summary["cosmetic_changes"] == 0
            assert summary["avg_confidence_score"] == 92
            
            # Verify monitoring events were recorded
            assert mock_record_event.call_count >= 3  # performance, change, and potentially error events
    
    @pytest.mark.asyncio
    async def test_monitor_agency_not_found(self, monitor):
        """Test monitoring when agency is not found."""
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            result = await monitor.monitor_agency_with_ai(999)
            
            assert result["agency_id"] == 999
            assert result["agency_name"] is None
            assert len(result["errors"]) == 1
            assert "not found" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_monitor_form_batch_processing(self, monitor, sample_form, 
                                                mock_web_scraper, sample_ai_analysis_result):
        """Test batch processing of forms."""
        forms = [sample_form] * 3  # Create 3 identical forms for testing
        
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db, \
             patch('src.monitors.ai_enhanced_monitor.record_monitoring_event') as mock_record_event:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock web scraper responses
            mock_web_scraper.fetch_page_content.return_value = (
                "<html>Updated content</html>", 200, {}
            )
            
            # Mock AI analysis
            monitor.analysis_service.analyze_document_changes_enhanced.return_value = sample_ai_analysis_result
            
            # Mock content storage methods
            monitor._get_previous_content = AsyncMock(return_value="<html>Old content</html>")
            monitor._store_current_content = AsyncMock()
            
            # Execute batch processing
            results = await monitor._process_form_batch(forms, mock_web_scraper, mock_db)
            
            # Verify results
            assert len(results) == 3
            for result in results:
                assert result["form_id"] == sample_form.id
                assert result["form_name"] == sample_form.name
                assert result["has_changes"] == True
                assert result["ai_analysis"] is not None
                assert result["errors"] == []
            
            # Verify monitoring events were recorded
            assert mock_record_event.call_count >= 1  # form_batch_processing event
    
    @pytest.mark.asyncio
    async def test_analyze_form_changes_no_previous_content(self, monitor, sample_form, mock_web_scraper):
        """Test form analysis when no previous content exists."""
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock web scraper
            mock_web_scraper.fetch_page_content.return_value = (
                "<html>New content</html>", 200, {}
            )
            
            # Mock no previous content
            monitor._get_previous_content = AsyncMock(return_value=None)
            monitor._store_current_content = AsyncMock()
            
            # Execute analysis
            result = await monitor._analyze_form_changes(sample_form, mock_web_scraper, mock_db)
            
            # Verify results
            assert result["form_id"] == sample_form.id
            assert result["has_changes"] == False
            assert result["ai_analysis"] is None
            assert result["errors"] == []
            
            # Verify content was stored
            monitor._store_current_content.assert_called_once_with(sample_form.id, "<html>New content</html>")
    
    @pytest.mark.asyncio
    async def test_analyze_form_changes_http_error(self, monitor, sample_form, mock_web_scraper):
        """Test form analysis when HTTP request fails."""
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db, \
             patch('src.monitors.ai_enhanced_monitor.record_monitoring_event') as mock_record_event:
            mock_db = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock HTTP error
            mock_web_scraper.fetch_page_content.return_value = ("", 404, {})
            
            # Execute analysis
            result = await monitor._analyze_form_changes(sample_form, mock_web_scraper, mock_db)
            
            # Verify results
            assert result["form_id"] == sample_form.id
            assert result["has_changes"] == False
            assert len(result["errors"]) == 1
            assert "HTTP 404" in result["errors"][0]
            
            # Verify error event was recorded
            mock_record_event.assert_called_once()
            call_args = mock_record_event.call_args
            assert call_args[0][0] == "error"
            assert call_args[0][1]["error_type"] == "http_error"
    
    @pytest.mark.asyncio
    async def test_perform_ai_analysis_success_with_enhanced_service(self, monitor, sample_form, sample_ai_analysis_result):
        """Test successful AI analysis with enhanced service."""
        old_content = "<html>Old content</html>"
        new_content = "<html>New content</html>"
        
        monitor.analysis_service.analyze_document_changes_enhanced.return_value = sample_ai_analysis_result
        
        result = await monitor._perform_ai_analysis(old_content, new_content, sample_form)
        
        # Verify enhanced AI service was called correctly
        monitor.analysis_service.analyze_document_changes_enhanced.assert_called_once()
        call_args = monitor.analysis_service.analyze_document_changes_enhanced.call_args[0][0]
        assert isinstance(call_args, AnalysisRequest)
        assert call_args.old_content == old_content
        assert call_args.new_content == new_content
        assert call_args.form_name == sample_form.name
        assert call_args.agency_name == sample_form.agency.name
        assert call_args.confidence_threshold == monitor.confidence_threshold
        
        # Verify result
        assert result == sample_ai_analysis_result
    
    @pytest.mark.asyncio
    async def test_perform_ai_analysis_fallback_to_standard_service(self, monitor, sample_form, sample_ai_analysis_result):
        """Test AI analysis fallback to standard service when enhanced service fails."""
        old_content = "<html>Old content</html>"
        new_content = "<html>New content</html>"
        
        # Mock enhanced service failure
        monitor.analysis_service.analyze_document_changes_enhanced.side_effect = Exception("Enhanced service error")
        monitor.analysis_service.analyze_document_changes.return_value = sample_ai_analysis_result
        
        result = await monitor._perform_ai_analysis(old_content, new_content, sample_form)
        
        # Verify fallback to standard service
        monitor.analysis_service.analyze_document_changes.assert_called_once()
        assert result == sample_ai_analysis_result
    
    @pytest.mark.asyncio
    async def test_perform_ai_analysis_no_service(self, sample_form):
        """Test AI analysis when no service is available."""
        monitor = AIEnhancedMonitor()
        monitor.analysis_service = None  # No AI service
        
        result = await monitor._perform_ai_analysis("old", "new", sample_form)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_perform_ai_analysis_failure(self, monitor, sample_form):
        """Test AI analysis when service fails."""
        monitor.analysis_service.analyze_document_changes_enhanced.side_effect = Exception("AI service error")
        monitor.analysis_service.analyze_document_changes.side_effect = Exception("Standard service error")
        
        result = await monitor._perform_ai_analysis("old", "new", sample_form)
        
        assert result is None
    
    def test_serialize_ai_analysis_with_enhanced_features(self, monitor, sample_ai_analysis_result):
        """Test AI analysis result serialization with enhanced features."""
        serialized = monitor._serialize_ai_analysis(sample_ai_analysis_result)
        
        assert serialized["analysis_id"] == "test_analysis_123"
        assert serialized["has_meaningful_changes"] == True
        assert serialized["classification"]["category"] == "form_update"
        assert serialized["classification"]["severity"] == "high"
        assert serialized["classification"]["confidence"] == 92
        assert serialized["semantic_analysis"]["similarity_score"] == 75
        assert len(serialized["semantic_analysis"]["significant_differences"]) <= 3
        assert serialized["processing_time_ms"] == 1250
        
        # Verify enhanced features are included
        assert "enhanced_features" in serialized
        enhanced_features = serialized["enhanced_features"]
        assert enhanced_features["false_positive_detection"] == True
        assert enhanced_features["semantic_change_detection"] == True
        assert enhanced_features["content_relevance_validation"] == True
        assert "compliance_validation" in enhanced_features
        assert "structure_validation" in enhanced_features
    
    @pytest.mark.asyncio
    async def test_create_ai_enhanced_change_record_with_classifier(self, monitor, sample_form, sample_ai_analysis_result):
        """Test creation of AI-enhanced change record with change classifier."""
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock change classifier
            mock_classification = {
                "category": "form_update",
                "severity": "high",
                "confidence": 95,
                "reasoning": "Significant form changes detected"
            }
            monitor.change_classifier.classify_change.return_value = mock_classification
            
            old_content = "<html>Old content</html>"
            new_content = "<html>New content</html>"
            
            result = await monitor._create_ai_enhanced_change_record(
                sample_form, old_content, new_content, sample_ai_analysis_result, mock_db
            )
            
            # Verify change classifier was called
            monitor.change_classifier.classify_change.assert_called_once()
            
            # Verify FormChange was created
            mock_db.add.assert_called_once()
            change_record = mock_db.add.call_args[0][0]
            assert isinstance(change_record, FormChange)
            assert change_record.form_id == sample_form.id
            assert change_record.change_type == "content"
            assert change_record.severity == "high"
            assert change_record.ai_confidence_score == 92
            assert change_record.ai_change_category == "form_update"
            assert change_record.is_cosmetic_change == False
            
            # Verify result dictionary
            assert result["change_id"] is not None
            assert result["category"] == "form_update"
            assert result["severity"] == "high"
            assert result["confidence"] == 92
    
    @pytest.mark.asyncio
    async def test_create_ai_enhanced_change_record_no_classifier(self, monitor, sample_form, sample_ai_analysis_result):
        """Test creation of AI-enhanced change record when classifier is not available."""
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Remove classifier
            monitor.change_classifier = None
            
            old_content = "<html>Old content</html>"
            new_content = "<html>New content</html>"
            
            result = await monitor._create_ai_enhanced_change_record(
                sample_form, old_content, new_content, sample_ai_analysis_result, mock_db
            )
            
            # Verify FormChange was still created
            mock_db.add.assert_called_once()
            change_record = mock_db.add.call_args[0][0]
            assert isinstance(change_record, FormChange)
            assert change_record.form_id == sample_form.id
            assert change_record.ai_confidence_score == 92
    
    def test_update_analysis_summary(self, monitor):
        """Test analysis summary updates."""
        summary = {
            "high_priority_changes": 0,
            "medium_priority_changes": 0,
            "low_priority_changes": 0,
            "cosmetic_changes": 0,
            "avg_confidence_score": 0
        }
        
        ai_analysis = {
            "classification": {
                "priority_score": 85,
                "confidence": 90,
                "is_cosmetic": False
            }
        }
        
        monitor._update_analysis_summary(summary, ai_analysis)
        
        assert summary["high_priority_changes"] == 1
        assert summary["cosmetic_changes"] == 0
        assert summary["avg_confidence_score"] == 90
    
    @pytest.mark.asyncio
    async def test_get_service_health_with_enhanced_features(self, monitor, mock_enhanced_analysis_service, 
                                                           mock_error_handler, mock_monitoring_statistics):
        """Test service health check with enhanced features."""
        mock_enhanced_analysis_service.health_check_enhanced.return_value = {"service": "healthy", "enhanced": True}
        mock_error_handler.get_error_stats.return_value = {
            "total_requests": 100,
            "successful_requests": 95,
            "error_rate": 0.05,
            "active_circuit_breakers": 0
        }
        mock_monitoring_statistics.get_comprehensive_statistics.return_value = {
            "performance": {"avg_response_time": 150},
            "coverage": {"total_states": 50},
            "changes": {"total_detected": 25}
        }
        
        health = await monitor.get_service_health()
        
        assert health["service"] == "ai_enhanced_monitor"
        assert health["status"] == "healthy"
        assert health["ai_analysis_available"] == True
        assert health["enhanced_analysis_available"] == True
        assert health["configuration"]["confidence_threshold"] == 70
        assert health["configuration"]["llm_analysis_enabled"] == True
        assert health["configuration"]["batch_size"] == 3
        
        # Verify enhanced features
        assert "error_handling" in health
        assert "monitoring_statistics" in health
        assert health["error_handling"]["total_requests"] == 100
        assert health["error_handling"]["success_rate"] == 0.95
    
    @pytest.mark.asyncio
    async def test_get_service_health_degraded(self, monitor, mock_enhanced_analysis_service):
        """Test service health check when AI service is degraded."""
        mock_enhanced_analysis_service.health_check_enhanced.return_value = {"service": "degraded"}
        
        health = await monitor.get_service_health()
        
        assert health["status"] == "degraded"
        assert health["ai_service_health"]["service"] == "degraded"
    
    @pytest.mark.asyncio
    async def test_get_service_health_no_ai_service(self):
        """Test service health check when AI service is not available."""
        monitor = AIEnhancedMonitor()
        monitor.analysis_service = None
        
        health = await monitor.get_service_health()
        
        assert health["status"] == "degraded"
        assert health["ai_analysis_available"] == False
        assert "error" in health
    
    @pytest.mark.asyncio
    async def test_get_monitoring_statistics(self, monitor, mock_monitoring_statistics):
        """Test getting monitoring statistics."""
        mock_stats = {
            "performance": {"avg_response_time": 150},
            "coverage": {"total_states": 50},
            "changes": {"total_detected": 25}
        }
        mock_monitoring_statistics.get_comprehensive_statistics.return_value = mock_stats
        
        result = await monitor.get_monitoring_statistics()
        
        assert result == mock_stats
        mock_monitoring_statistics.get_comprehensive_statistics.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_all_agencies_comprehensive(self, monitor, mock_enhanced_config_manager, 
                                                     mock_web_scraper, mock_error_handler, mock_monitoring_statistics):
        """Test comprehensive monitoring of all agencies."""
        # Mock configuration manager
        mock_enhanced_config_manager.get_optimized_monitoring_batches.return_value = [
            {
                "batch_id": "batch_1",
                "agencies": [{"id": 1, "name": "Test Agency 1"}],
                "forms": [{"id": 1, "name": "WH-347", "agency_id": 1}],
                "estimated_duration": 30
            }
        ]
        
        # Mock database
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = Mock(spec=Agency)
            mock_db.query.return_value.filter.return_value.all.return_value = [Mock(spec=Form)]
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock web scraper
            with patch('src.monitors.ai_enhanced_monitor.WebScraper', return_value=mock_web_scraper):
                mock_web_scraper.fetch_page_content.return_value = ("<html>Content</html>", 200, {})
                
                # Mock error handler
                mock_error_handler.get_error_stats.return_value = {
                    "total_requests": 10,
                    "successful_requests": 9,
                    "error_rate": 0.1,
                    "active_circuit_breakers": 0
                }
                
                # Mock monitoring session
                mock_monitoring_statistics.start_monitoring_session.return_value = "session_456"
                mock_monitoring_statistics.get_comprehensive_statistics.return_value = {
                    "performance": {"avg_response_time": 150},
                    "coverage": {"total_states": 50}
                }
                
                # Execute comprehensive monitoring
                result = await monitor.monitor_all_agencies_comprehensive()
                
                # Verify results
                assert result["session_id"] == "session_456"
                assert result["total_batches"] == 1
                assert result["total_agencies"] == 1
                assert result["total_forms"] == 1
                assert "monitoring_statistics" in result
                assert "error_handling" in result
                assert result["error_handling"]["success_rate"] == 0.9
    
    @pytest.mark.asyncio
    async def test_process_comprehensive_batch(self, monitor, mock_web_scraper):
        """Test processing of comprehensive monitoring batches."""
        batch = {
            "batch_id": "batch_1",
            "agencies": [{"id": 1, "name": "Test Agency 1"}],
            "forms": [{"id": 1, "name": "WH-347", "agency_id": 1}],
            "estimated_duration": 30
        }
        
        with patch('src.monitors.ai_enhanced_monitor.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.query.return_value.filter.return_value.first.return_value = Mock(spec=Agency)
            mock_db.query.return_value.filter.return_value.all.return_value = [Mock(spec=Form)]
            mock_get_db.return_value.__enter__.return_value = mock_db
            
            # Mock web scraper
            mock_web_scraper.fetch_page_content.return_value = ("<html>Content</html>", 200, {})
            
            # Execute batch processing
            result = await monitor._process_comprehensive_batch(batch, mock_web_scraper)
            
            # Verify results
            assert result["batch_id"] == "batch_1"
            assert result["agencies_processed"] == 1
            assert result["forms_processed"] == 1
            assert "processing_time" in result
            assert "errors" in result
    
    def test_calculate_success_rate(self, monitor):
        """Test success rate calculation."""
        error_stats = {
            "total_requests": 100,
            "successful_requests": 85
        }
        
        success_rate = monitor._calculate_success_rate(error_stats)
        
        assert success_rate == 0.85
    
    def test_calculate_success_rate_zero_requests(self, monitor):
        """Test success rate calculation with zero requests."""
        error_stats = {
            "total_requests": 0,
            "successful_requests": 0
        }
        
        success_rate = monitor._calculate_success_rate(error_stats)
        
        assert success_rate == 0.0


class TestMonitorAgencyWithAI:
    """Test suite for the convenience function."""
    
    @pytest.mark.asyncio
    async def test_monitor_agency_with_ai_convenience_function(self):
        """Test the convenience function for backward compatibility."""
        with patch('src.monitors.ai_enhanced_monitor.AIEnhancedMonitor') as mock_monitor_class:
            mock_monitor = Mock()
            mock_monitor.monitor_agency_with_ai = AsyncMock(return_value={"status": "success"})
            mock_monitor_class.return_value = mock_monitor
            
            result = await monitor_agency_with_ai(1, confidence_threshold=80)
            
            # Verify monitor was created with correct parameters
            mock_monitor_class.assert_called_once_with(confidence_threshold=80)
            
            # Verify monitoring was called
            mock_monitor.monitor_agency_with_ai.assert_called_once_with(1)
            
            # Verify result
            assert result == {"status": "success"}


class TestAIEnhancedMonitorIntegration:
    """Integration tests for AI-Enhanced Monitor with real dependencies."""
    
    @pytest.mark.asyncio
    async def test_full_monitoring_workflow(self):
        """Test the complete monitoring workflow with all components."""
        # This test would require more complex setup with real database connections
        # and actual service instances. For now, we'll test the integration points.
        
        with patch('src.monitors.ai_enhanced_monitor.AIEnhancedMonitor') as mock_monitor_class:
            mock_monitor = Mock()
            mock_monitor.monitor_agency_with_ai = AsyncMock(return_value={
                "agency_id": 1,
                "agency_name": "Test Agency",
                "total_forms": 2,
                "forms_analyzed": 2,
                "changes_detected": 1,
                "ai_analyses_performed": 1,
                "session_id": "test_session"
            })
            mock_monitor_class.return_value = mock_monitor
            
            # Test the full workflow
            result = await monitor_agency_with_ai(1)
            
            assert result["agency_id"] == 1
            assert result["changes_detected"] == 1
            assert result["session_id"] == "test_session"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Test error handling integration across all components."""
        with patch('src.monitors.ai_enhanced_monitor.AIEnhancedMonitor') as mock_monitor_class:
            mock_monitor = Mock()
            mock_monitor.monitor_agency_with_ai = AsyncMock(side_effect=Exception("Integration error"))
            mock_monitor_class.return_value = mock_monitor
            
            # Test error handling
            with pytest.raises(Exception, match="Integration error"):
                await monitor_agency_with_ai(1)


if __name__ == "__main__":
    pytest.main([__file__]) 