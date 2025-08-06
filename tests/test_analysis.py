"""
Unit tests for AI-powered change detection analysis.

Tests cover semantic similarity detection, change classification,
LLM integration, and the overall analysis service workflow.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Import models that should always be available
from src.analysis import (
    AnalysisRequest, AnalysisResponse, ChangeClassification, SemanticAnalysis
)

# Try to import service classes that may have dependencies
try:
    from src.analysis import (
        AnalysisService, ChangeAnalyzer, LLMClassifier
    )
    from src.analysis.llm_classifier import ChangeCategory, SeverityLevel
    ANALYSIS_SERVICES_AVAILABLE = True
except ImportError:
    ANALYSIS_SERVICES_AVAILABLE = False
    AnalysisService = None
    ChangeAnalyzer = None
    LLMClassifier = None
    ChangeCategory = None
    SeverityLevel = None


@pytest.fixture
def sample_content():
    """Sample document content for testing."""
    return {
        "old_content": """
        Employee Information Form WH-347
        
        Employee Name: ________________________
        Hours Worked: _________
        Hourly Rate: $15.00
        
        Instructions:
        1. Fill out all required fields
        2. Submit by deadline
        """,
        "new_content": """
        Employee Information Form WH-347 (Revised)
        
        Employee Name: ________________________
        Regular Hours: _________
        Overtime Hours: _________
        Base Rate: $15.50
        Overtime Rate: $23.25
        
        Instructions:
        1. Fill out all required fields completely
        2. Submit by updated deadline
        3. Include overtime calculations
        """,
        "cosmetic_old": "Employee Name:    John Doe\nHours: 40",
        "cosmetic_new": "Employee Name: John Doe\nHours:   40"
    }


@pytest.fixture
def analysis_request(sample_content):
    """Sample analysis request."""
    return AnalysisRequest(
        old_content=sample_content["old_content"],
        new_content=sample_content["new_content"],
        form_name="WH-347",
        agency_name="Department of Labor",
        confidence_threshold=70,
        use_llm_fallback=True
    )


class TestAnalysisModels:
    """Test cases for the analysis models that are always available."""
    
    def test_analysis_request_creation(self, sample_content):
        """Test AnalysisRequest model creation and validation."""
        request = AnalysisRequest(
            old_content=sample_content["old_content"],
            new_content=sample_content["new_content"],
            form_name="WH-347",
            agency_name="Department of Labor",
            confidence_threshold=75,
            use_llm_fallback=True
        )
        
        assert request.old_content == sample_content["old_content"]
        assert request.new_content == sample_content["new_content"]
        assert request.form_name == "WH-347"
        assert request.agency_name == "Department of Labor"
        assert request.confidence_threshold == 75
        assert request.use_llm_fallback is True
    
    def test_analysis_request_validation(self):
        """Test AnalysisRequest validation."""
        # Test confidence threshold validation
        with pytest.raises(Exception):  # Pydantic validation error
            AnalysisRequest(
                old_content="old",
                new_content="new",
                confidence_threshold=150
            )
        
        with pytest.raises(Exception):  # Pydantic validation error
            AnalysisRequest(
                old_content="old",
                new_content="new",
                confidence_threshold=-10
            )
    
    def test_change_classification_creation(self):
        """Test ChangeClassification model creation."""
        classification = ChangeClassification(
            category="form_update",
            subcategory="field_addition",
            severity="high",
            priority_score=85,
            is_cosmetic=False,
            confidence=90
        )
        
        assert classification.category == "form_update"
        assert classification.subcategory == "field_addition"
        assert classification.severity == "high"
        assert classification.priority_score == 85
        assert classification.is_cosmetic is False
        assert classification.confidence == 90
    
    def test_semantic_analysis_creation(self):
        """Test SemanticAnalysis model creation."""
        semantic = SemanticAnalysis(
            similarity_score=75,
            significant_differences=["Added overtime field", "Updated hourly rate"],
            change_indicators=["rate_change", "field_addition"],
            model_name="all-MiniLM-L6-v2",
            processing_time_ms=150
        )
        
        assert semantic.similarity_score == 75
        assert len(semantic.significant_differences) == 2
        assert len(semantic.change_indicators) == 2
        assert semantic.model_name == "all-MiniLM-L6-v2"
        assert semantic.processing_time_ms == 150
    
    def test_analysis_response_creation(self):
        """Test AnalysisResponse model creation."""
        classification = ChangeClassification(
            category="form_update",
            severity="high",
            priority_score=85,
            is_cosmetic=False,
            confidence=90
        )
        
        semantic = SemanticAnalysis(
            similarity_score=75,
            significant_differences=["Added overtime field"],
            change_indicators=["field_addition"],
            model_name="all-MiniLM-L6-v2",
            processing_time_ms=150
        )
        
        response = AnalysisResponse(
            analysis_id="test-123",
            has_meaningful_changes=True,
            classification=classification,
            semantic_analysis=semantic
        )
        
        assert response.analysis_id == "test-123"
        assert response.has_meaningful_changes is True
        assert response.classification == classification
        assert response.semantic_analysis == semantic
        assert isinstance(response.timestamp, datetime)


@pytest.mark.skipif(not ANALYSIS_SERVICES_AVAILABLE, reason="Analysis services not available")
class TestChangeAnalyzer:
    """Test cases for the ChangeAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create a ChangeAnalyzer instance for testing."""
        with patch('src.analysis.change_analyzer.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.15, 0.25, 0.35]]
            mock_transformer.return_value = mock_model
            
            analyzer = ChangeAnalyzer()
            analyzer.model = mock_model
            return analyzer
    
    def test_initialization(self, analyzer):
        """Test ChangeAnalyzer initialization."""
        assert analyzer.model_name == "all-MiniLM-L6-v2"
        assert analyzer.similarity_threshold == 0.85
        assert analyzer.model is not None
    
    def test_preprocess_document(self, analyzer, sample_content):
        """Test document preprocessing and section extraction."""
        content, sections = analyzer.preprocess_document(sample_content["old_content"])
        
        assert isinstance(content, str)
        assert isinstance(sections, list)
        assert len(sections) > 0
        
        # Check that sections have required attributes
        for section in sections:
            assert hasattr(section, 'content')
            assert hasattr(section, 'section_type')
            assert hasattr(section, 'line_start')
            assert hasattr(section, 'line_end')
    
    @patch('src.analysis.change_analyzer.cosine_similarity')
    def test_semantic_similarity_calculation(self, mock_cosine, analyzer):
        """Test semantic similarity calculation."""
        mock_cosine.return_value = [[0.85]]
        
        similarity = analyzer.calculate_semantic_similarity("text1", "text2")
        
        assert isinstance(similarity, float)
        assert 0 <= similarity <= 1
        assert similarity == 0.85
    
    def test_cosmetic_change_detection(self, analyzer, sample_content):
        """Test cosmetic change detection."""
        # Test cosmetic changes
        is_cosmetic = analyzer.is_cosmetic_change(
            sample_content["cosmetic_old"], 
            sample_content["cosmetic_new"]
        )
        assert is_cosmetic is True
        
        # Test meaningful changes
        is_cosmetic = analyzer.is_cosmetic_change(
            sample_content["old_content"], 
            sample_content["new_content"]
        )
        assert is_cosmetic is False
    
    def test_change_detection(self, analyzer, sample_content):
        """Test significant change detection."""
        changes = analyzer.detect_significant_changes(
            sample_content["old_content"],
            sample_content["new_content"]
        )
        
        assert isinstance(changes, list)
        assert len(changes) > 0
        
        # Check that changes contain meaningful information
        change_text = " ".join(changes).lower()
        assert any(keyword in change_text for keyword in ["overtime", "rate", "modified"])
    
    def test_change_indicators(self, analyzer, sample_content):
        """Test change indicator generation."""
        indicators = analyzer.generate_change_indicators(
            sample_content["old_content"],
            sample_content["new_content"]
        )
        
        assert isinstance(indicators, list)
        assert len(indicators) > 0
        
        # Should detect new terms like "overtime"
        indicators_text = " ".join(indicators).lower()
        assert "overtime" in indicators_text or "new important terms" in indicators_text
    
    def test_complete_analysis(self, analyzer, sample_content):
        """Test complete semantic analysis workflow."""
        result = analyzer.analyze(
            sample_content["old_content"],
            sample_content["new_content"]
        )
        
        assert isinstance(result, SemanticAnalysis)
        assert 0 <= result.similarity_score <= 100
        assert isinstance(result.significant_differences, list)
        assert isinstance(result.change_indicators, list)
        assert result.model_name == analyzer.model_name
        assert result.processing_time_ms > 0


@pytest.mark.skipif(not ANALYSIS_SERVICES_AVAILABLE, reason="Analysis services not available")
class TestLLMClassifier:
    """Test cases for the LLMClassifier class."""
    
    @pytest.fixture
    def classifier(self):
        """Create an LLMClassifier instance for testing."""
        with patch('src.analysis.llm_classifier.openai') as mock_openai:
            classifier = LLMClassifier()
            classifier.client = Mock()
            return classifier
    
    def test_initialization_without_api_key(self):
        """Test LLMClassifier initialization without API key."""
        with patch('src.analysis.llm_classifier.openai', None):
            classifier = LLMClassifier()
            assert classifier.client is None
    
    def test_fallback_classification(self, classifier, sample_content):
        """Test rule-based fallback classification."""
        classification, analysis = classifier._fallback_classification(
            sample_content["old_content"],
            sample_content["new_content"],
            "WH-347",
            "Department of Labor"
        )
        
        assert isinstance(classification, ChangeClassification)
        assert classification.category in [cat.value for cat in ChangeCategory]
        assert classification.severity in [sev.value for sev in SeverityLevel]
        assert 0 <= classification.priority_score <= 100
        assert 0 <= classification.confidence <= 100
        
        assert analysis.model_used == "rule_based_fallback"
        assert isinstance(analysis.key_changes, list)
    
    def test_classification_validation(self, classifier):
        """Test classification result validation."""
        valid_classification = ChangeClassification(
            category="form_update",
            severity="medium",
            priority_score=50,
            is_cosmetic=False,
            confidence=75
        )
        
        assert classifier.validate_classification(valid_classification) is True
        
        # Test invalid classification
        invalid_classification = ChangeClassification(
            category="invalid_category",
            severity="medium",
            priority_score=150,  # Invalid score
            is_cosmetic=False,
            confidence=75
        )
        
        assert classifier.validate_classification(invalid_classification) is False
    
    @pytest.mark.asyncio
    async def test_classify_with_fallback(self, classifier, sample_content):
        """Test classification with fallback to rule-based method."""
        classifier.client = None  # Simulate no LLM available
        
        classification, analysis = await classifier.classify(
            sample_content["old_content"],
            sample_content["new_content"],
            "WH-347",
            "Department of Labor",
            use_llm=True
        )
        
        assert isinstance(classification, ChangeClassification)
        assert analysis.model_used == "rule_based_fallback"
    
    @pytest.mark.asyncio
    async def test_llm_classification_success(self, classifier, sample_content):
        """Test successful LLM classification."""
        # Mock successful LLM response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        {
            "category": "requirement_change",
            "subcategory": "field_modification",
            "severity": "medium",
            "priority_score": 65,
            "is_cosmetic": false,
            "confidence": 85,
            "reasoning": "Added overtime tracking requirements",
            "key_changes": ["Overtime fields added", "Rate structure changed"],
            "impact_assessment": "Medium impact on reporting process",
            "recommendations": ["Update forms", "Train staff"]
        }
        """
        mock_response.usage.total_tokens = 150
        
        classifier.client.chat.completions.create.return_value = mock_response
        
        classification, analysis = await classifier.classify_with_llm(
            sample_content["old_content"],
            sample_content["new_content"],
            "WH-347",
            "Department of Labor"
        )
        
        assert classification.category == "requirement_change"
        assert classification.severity == "medium"
        assert classification.confidence == 85
        assert analysis.tokens_used == 150


@pytest.mark.skipif(not ANALYSIS_SERVICES_AVAILABLE, reason="Analysis services not available")
class TestAnalysisService:
    """Test cases for the AnalysisService orchestration."""
    
    @pytest.fixture
    def service(self):
        """Create an AnalysisService instance for testing."""
        with patch('src.analysis.analysis_service.ChangeAnalyzer') as mock_analyzer, \
             patch('src.analysis.analysis_service.LLMClassifier') as mock_classifier:
            
            # Mock ChangeAnalyzer
            mock_analyzer_instance = Mock()
            mock_analyzer_instance.model_name = "test-model"
            mock_analyzer_instance.analyze.return_value = SemanticAnalysis(
                similarity_score=75,
                significant_differences=["Test change detected"],
                change_indicators=["New terms added"],
                model_name="test-model",
                processing_time_ms=100
            )
            mock_analyzer_instance.is_cosmetic_change.return_value = False
            mock_analyzer.return_value = mock_analyzer_instance
            
            # Mock LLMClassifier
            mock_classifier_instance = Mock()
            mock_classifier_instance.classify = AsyncMock(return_value=(
                ChangeClassification(
                    category="form_update",
                    severity="medium",
                    priority_score=60,
                    is_cosmetic=False,
                    confidence=80
                ),
                None
            ))
            mock_classifier.return_value = mock_classifier_instance
            
            return AnalysisService()
    
    @pytest.mark.asyncio
    async def test_document_analysis_workflow(self, service, analysis_request):
        """Test complete document analysis workflow."""
        result = await service.analyze_document_changes(analysis_request)
        
        assert isinstance(result, AnalysisResponse)
        assert result.analysis_id.startswith("analysis_")
        assert isinstance(result.timestamp, datetime)
        assert isinstance(result.has_meaningful_changes, bool)
        assert isinstance(result.classification, ChangeClassification)
        assert isinstance(result.semantic_analysis, SemanticAnalysis)
        assert isinstance(result.processing_summary, dict)
        assert isinstance(result.confidence_breakdown, dict)
    
    def test_llm_decision_logic(self, service):
        """Test logic for deciding when to use LLM analysis."""
        # Mock semantic analysis with many changes (should trigger LLM)
        semantic_analysis = SemanticAnalysis(
            similarity_score=60,  # Uncertain range
            significant_differences=["Change 1", "Change 2", "Change 3", "Change 4"],
            change_indicators=["Indicator 1", "Indicator 2", "Indicator 3"],
            model_name="test",
            processing_time_ms=100
        )
        
        request = AnalysisRequest(
            old_content="test",
            new_content="test",
            use_llm_fallback=True
        )
        
        should_use_llm = service._should_use_llm(semantic_analysis, 70, request)
        assert should_use_llm is True
        
        # Test case where LLM should not be used
        semantic_analysis.similarity_score = 95  # Very similar
        semantic_analysis.significant_differences = []
        semantic_analysis.change_indicators = []
        request.use_llm_fallback = False
        
        should_use_llm = service._should_use_llm(semantic_analysis, 70, request)
        assert should_use_llm is False
    
    def test_results_combination(self, service):
        """Test combination of analysis results."""
        semantic_analysis = SemanticAnalysis(
            similarity_score=75,
            significant_differences=["Test change"],
            change_indicators=["Test indicator"],
            model_name="test",
            processing_time_ms=100
        )
        
        classification = ChangeClassification(
            category="form_update",
            severity="medium",
            priority_score=60,
            is_cosmetic=False,
            confidence=80
        )
        
        has_changes, confidence = service._combine_analysis_results(
            semantic_analysis, classification
        )
        
        assert isinstance(has_changes, bool)
        assert isinstance(confidence, dict)
        assert "overall" in confidence
        assert "semantic_similarity" in confidence
        assert "classification_confidence" in confidence
    
    def test_cache_key_generation(self, service):
        """Test cache key generation for content."""
        key1 = service._calculate_cache_key("content1", "content2")
        key2 = service._calculate_cache_key("content1", "content2")
        key3 = service._calculate_cache_key("content1", "different")
        
        assert key1 == key2  # Same content should generate same key
        assert key1 != key3  # Different content should generate different key
        assert key1.startswith("analysis_")
    
    def test_statistics_tracking(self, service):
        """Test service statistics tracking."""
        initial_stats = service.get_service_stats()
        
        assert "total_analyses" in initial_stats
        assert "successful_analyses" in initial_stats
        assert "failed_analyses" in initial_stats
        assert "avg_processing_time_ms" in initial_stats
        
        # Test processing time update
        service._update_avg_processing_time(100)
        service.analysis_stats["successful_analyses"] = 1
        
        service._update_avg_processing_time(200)
        service.analysis_stats["successful_analyses"] = 2
        
        assert service.analysis_stats["avg_processing_time_ms"] == 150
    
    @pytest.mark.asyncio
    async def test_health_check(self, service):
        """Test service health check functionality."""
        health = await service.health_check()
        
        assert isinstance(health, dict)
        assert "service" in health
        assert "semantic_analyzer" in health
        assert "llm_classifier" in health
        assert "timestamp" in health
    
    def test_cache_operations(self, service):
        """Test cache clear and management."""
        # Add something to cache
        if service.analysis_cache is not None:
            service.analysis_cache["test_key"] = "test_value"
            
            stats_before = service.get_service_stats()
            service.clear_cache()
            stats_after = service.get_service_stats()
            
            assert stats_after["cache_size"] == 0


@pytest.mark.skipif(not ANALYSIS_SERVICES_AVAILABLE, reason="Analysis services not available")
@pytest.mark.integration
class TestAnalysisIntegration:
    """Integration tests for the complete analysis system."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_analysis(self, sample_content):
        """Test end-to-end analysis without mocks."""
        # Skip if required dependencies not available
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            pytest.skip("sentence-transformers not available")
        
        # Use real components but with lightweight models
        service = AnalysisService(
            semantic_model="all-MiniLM-L6-v2",
            llm_model="gpt-3.5-turbo",
            enable_caching=False  # Disable caching for test
        )
        
        request = AnalysisRequest(
            old_content=sample_content["old_content"],
            new_content=sample_content["new_content"],
            form_name="WH-347",
            agency_name="Department of Labor",
            confidence_threshold=70,
            use_llm_fallback=False  # Don't use LLM to avoid API costs
        )
        
        result = await service.analyze_document_changes(request)
        
        # Verify result structure and content
        assert isinstance(result, AnalysisResponse)
        assert result.has_meaningful_changes is True  # Should detect real changes
        assert result.semantic_analysis.similarity_score < 90  # Should be different
        assert len(result.semantic_analysis.significant_differences) > 0
        
        # Verify classification makes sense
        assert result.classification.category in ["form_update", "requirement_change", "logic_modification"]
        assert result.classification.severity in ["low", "medium", "high", "critical"]
    
    @pytest.mark.asyncio
    async def test_cosmetic_vs_meaningful_changes(self, sample_content):
        """Test distinction between cosmetic and meaningful changes."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            pytest.skip("sentence-transformers not available")
        
        service = AnalysisService(enable_caching=False)
        
        # Test cosmetic changes
        cosmetic_request = AnalysisRequest(
            old_content=sample_content["cosmetic_old"],
            new_content=sample_content["cosmetic_new"],
            use_llm_fallback=False
        )
        
        cosmetic_result = await service.analyze_document_changes(cosmetic_request)
        
        # Test meaningful changes
        meaningful_request = AnalysisRequest(
            old_content=sample_content["old_content"],
            new_content=sample_content["new_content"],
            use_llm_fallback=False
        )
        
        meaningful_result = await service.analyze_document_changes(meaningful_request)
        
        # Cosmetic changes should have higher similarity and lower priority
        assert cosmetic_result.semantic_analysis.similarity_score > meaningful_result.semantic_analysis.similarity_score
        assert cosmetic_result.classification.priority_score <= meaningful_result.classification.priority_score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])