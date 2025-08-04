"""
Unit tests for the enhanced error handling and retry mechanisms.

This module tests the comprehensive error handling system designed for
government website monitoring, including error classification, retry logic,
circuit breaker patterns, and statistical tracking.
"""

import pytest
import asyncio
import aiohttp
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from selenium.common.exceptions import TimeoutException, WebDriverException

from src.monitors.error_handler import (
    ErrorSeverity,
    ErrorType,
    ErrorContext,
    RetryConfig,
    CircuitBreakerState,
    CircuitBreaker,
    ErrorClassifier,
    RetryHandler,
    GovernmentWebsiteErrorHandler,
    get_error_handler,
    create_retry_config
)


class TestErrorSeverity:
    """Test error severity enumeration."""
    
    def test_error_severity_values(self):
        """Test that error severity values are correctly defined."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorType:
    """Test error type enumeration."""
    
    def test_error_type_values(self):
        """Test that error type values are correctly defined."""
        assert ErrorType.CONNECTION_TIMEOUT.value == "connection_timeout"
        assert ErrorType.HTTP_404.value == "http_404"
        assert ErrorType.HTTP_429.value == "http_429"
        assert ErrorType.MAINTENANCE_MODE.value == "maintenance_mode"
        assert ErrorType.SELENIUM_TIMEOUT.value == "selenium_timeout"
        assert ErrorType.UNKNOWN_ERROR.value == "unknown_error"


class TestErrorContext:
    """Test error context dataclass."""
    
    def test_error_context_creation(self):
        """Test creating an error context with basic information."""
        context = ErrorContext(url="https://example.com")
        assert context.url == "https://example.com"
        assert context.attempt_number == 0
        assert context.total_attempts == 0
        assert context.error_type is None
        assert context.error_message is None
        assert context.status_code is None
        assert context.response_time is None
        assert isinstance(context.timestamp, datetime)
        assert context.metadata == {}
    
    def test_error_context_with_optional_fields(self):
        """Test creating an error context with optional fields."""
        context = ErrorContext(
            url="https://example.com",
            agency_name="Test Agency",
            form_name="Test Form",
            attempt_number=2,
            total_attempts=3,
            error_type=ErrorType.CONNECTION_TIMEOUT,
            error_message="Connection failed",
            status_code=500,
            response_time=1.5,
            metadata={"key": "value"}
        )
        
        assert context.agency_name == "Test Agency"
        assert context.form_name == "Test Form"
        assert context.attempt_number == 2
        assert context.total_attempts == 3
        assert context.error_type == ErrorType.CONNECTION_TIMEOUT
        assert context.error_message == "Connection failed"
        assert context.status_code == 500
        assert context.response_time == 1.5
        assert context.metadata == {"key": "value"}


class TestRetryConfig:
    """Test retry configuration dataclass."""
    
    def test_retry_config_defaults(self):
        """Test retry configuration with default values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter_factor == 0.1
        assert config.timeout_multiplier == 1.5
        assert config.circuit_breaker_threshold == 5
        assert config.circuit_breaker_timeout == 300.0
        assert config.circuit_breaker_half_open_timeout == 60.0
    
    def test_retry_config_custom_values(self):
        """Test retry configuration with custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter_factor=0.2,
            timeout_multiplier=2.0,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=600.0,
            circuit_breaker_half_open_timeout=120.0
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter_factor == 0.2
        assert config.timeout_multiplier == 2.0
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 600.0
        assert config.circuit_breaker_half_open_timeout == 120.0


class TestCircuitBreakerState:
    """Test circuit breaker state dataclass."""
    
    def test_circuit_breaker_state_defaults(self):
        """Test circuit breaker state with default values."""
        state = CircuitBreakerState()
        assert state.failure_count == 0
        assert state.last_failure_time is None
        assert state.state == "closed"
        assert state.next_attempt_time is None
    
    def test_circuit_breaker_state_with_values(self):
        """Test circuit breaker state with custom values."""
        now = datetime.utcnow()
        state = CircuitBreakerState(
            failure_count=3,
            last_failure_time=now,
            state="open",
            next_attempt_time=now + timedelta(minutes=5)
        )
        
        assert state.failure_count == 3
        assert state.last_failure_time == now
        assert state.state == "open"
        assert state.next_attempt_time == now + timedelta(minutes=5)


class TestCircuitBreaker:
    """Test circuit breaker implementation."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker instance for testing."""
        config = RetryConfig()
        return CircuitBreaker(config)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self, circuit_breaker):
        """Test that circuit breaker starts in closed state."""
        assert not await circuit_breaker.is_open("test_key")
        state = await circuit_breaker.get_state("test_key")
        assert state.state == "closed"
        assert state.failure_count == 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_on_success(self, circuit_breaker):
        """Test recording successful operations."""
        await circuit_breaker.on_success("test_key")
        state = await circuit_breaker.get_state("test_key")
        assert state.state == "closed"
        assert state.failure_count == 0
        assert state.last_failure_time is None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_on_failure(self, circuit_breaker):
        """Test recording failed operations."""
        await circuit_breaker.on_failure("test_key")
        state = await circuit_breaker.get_state("test_key")
        assert state.failure_count == 1
        assert state.last_failure_time is not None
        assert state.state == "closed"  # Not enough failures to open
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self, circuit_breaker):
        """Test that circuit breaker opens after reaching failure threshold."""
        # Fail multiple times to reach threshold
        for _ in range(5):
            await circuit_breaker.on_failure("test_key")
        
        assert await circuit_breaker.is_open("test_key")
        state = await circuit_breaker.get_state("test_key")
        assert state.state == "open"
        assert state.failure_count == 5
        assert state.next_attempt_time is not None
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_transitions_to_half_open(self, circuit_breaker):
        """Test circuit breaker transition from open to half-open."""
        # Open the circuit breaker
        for _ in range(5):
            await circuit_breaker.on_failure("test_key")
        
        # Manually set next attempt time to past
        state = await circuit_breaker.get_state("test_key")
        state.next_attempt_time = datetime.utcnow() - timedelta(seconds=1)
        
        # Should transition to half-open
        assert not await circuit_breaker.is_open("test_key")
        state = await circuit_breaker.get_state("test_key")
        assert state.state == "half-open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self, circuit_breaker):
        """Test that circuit breaker resets on successful operation."""
        # Open the circuit breaker
        for _ in range(5):
            await circuit_breaker.on_failure("test_key")
        
        # Success should reset the circuit breaker
        await circuit_breaker.on_success("test_key")
        assert not await circuit_breaker.is_open("test_key")
        state = await circuit_breaker.get_state("test_key")
        assert state.state == "closed"
        assert state.failure_count == 0


class TestErrorClassifier:
    """Test error classification logic."""
    
    @pytest.fixture
    def context(self):
        """Create a basic error context for testing."""
        return ErrorContext(url="https://example.com")
    
    def test_classify_http_404_error(self, context):
        """Test classification of HTTP 404 errors."""
        context.status_code = 404
        error = Exception("Not Found")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.HTTP_404
        assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_http_429_error(self, context):
        """Test classification of HTTP 429 (rate limiting) errors."""
        context.status_code = 429
        error = Exception("Too Many Requests")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.HTTP_429
        assert severity == ErrorSeverity.HIGH
    
    def test_classify_http_500_error(self, context):
        """Test classification of HTTP 500 errors."""
        context.status_code = 500
        error = Exception("Internal Server Error")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.HTTP_500
        assert severity == ErrorSeverity.HIGH
    
    def test_classify_connection_timeout(self, context):
        """Test classification of connection timeout errors."""
        error = asyncio.TimeoutError()
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.CONNECTION_TIMEOUT
        assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_selenium_timeout(self, context):
        """Test classification of Selenium timeout errors."""
        error = TimeoutException("Element not found")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.SELENIUM_TIMEOUT
        assert severity == ErrorSeverity.MEDIUM
    
    def test_classify_webdriver_error(self, context):
        """Test classification of WebDriver errors."""
        error = WebDriverException("WebDriver error")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.WEBDRIVER_ERROR
        assert severity == ErrorSeverity.HIGH
    
    def test_classify_maintenance_mode(self, context):
        """Test classification of maintenance mode errors."""
        error = Exception("Site is down for maintenance")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.MAINTENANCE_MODE
        assert severity == ErrorSeverity.HIGH
    
    def test_classify_ssl_certificate_error(self, context):
        """Test classification of SSL certificate errors."""
        error = Exception("SSL certificate error")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.SSL_CERTIFICATE_ERROR
        assert severity == ErrorSeverity.HIGH
    
    def test_classify_unknown_error(self, context):
        """Test classification of unknown errors."""
        error = Exception("Some random error")
        error_type, severity = ErrorClassifier.classify_error(error, context)
        
        assert error_type == ErrorType.UNKNOWN_ERROR
        assert severity == ErrorSeverity.MEDIUM
    
    def test_should_retry_logic(self):
        """Test retry decision logic."""
        # Should retry low severity errors
        assert ErrorClassifier.should_retry(
            ErrorType.CONNECTION_TIMEOUT, ErrorSeverity.LOW, 0, 3
        )
        
        # Should not retry HTTP 404 errors
        assert not ErrorClassifier.should_retry(
            ErrorType.HTTP_404, ErrorSeverity.MEDIUM, 0, 3
        )
        
        # Should not retry after max attempts
        assert not ErrorClassifier.should_retry(
            ErrorType.CONNECTION_TIMEOUT, ErrorSeverity.MEDIUM, 3, 3
        )
        
        # Should retry high severity errors fewer times
        assert ErrorClassifier.should_retry(
            ErrorType.HTTP_500, ErrorSeverity.HIGH, 1, 3
        )
        assert not ErrorClassifier.should_retry(
            ErrorType.HTTP_500, ErrorSeverity.HIGH, 2, 3
        )


class TestRetryHandler:
    """Test retry handler implementation."""
    
    @pytest.fixture
    def retry_handler(self):
        """Create a retry handler instance for testing."""
        config = RetryConfig(max_retries=2, base_delay=0.1)
        return RetryHandler(config)
    
    def test_calculate_delay(self, retry_handler):
        """Test delay calculation with exponential backoff."""
        # Test base delay
        delay = retry_handler.calculate_delay(0, ErrorSeverity.MEDIUM)
        assert delay >= 0.1  # Minimum delay
        
        # Test exponential backoff
        delay1 = retry_handler.calculate_delay(1, ErrorSeverity.MEDIUM)
        delay2 = retry_handler.calculate_delay(2, ErrorSeverity.MEDIUM)
        assert delay2 > delay1
        
        # Test severity adjustment
        high_delay = retry_handler.calculate_delay(1, ErrorSeverity.HIGH)
        medium_delay = retry_handler.calculate_delay(1, ErrorSeverity.MEDIUM)
        assert high_delay > medium_delay
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, retry_handler):
        """Test successful operation execution."""
        context = ErrorContext(url="https://example.com")
        
        async def successful_operation():
            return "success"
        
        result, final_context = await retry_handler.execute_with_retry(
            successful_operation, context, "test_operation"
        )
        
        assert result == "success"
        assert final_context.response_time is not None
        assert final_context.attempt_number == 0
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_failure_then_success(self, retry_handler):
        """Test operation that fails then succeeds."""
        context = ErrorContext(url="https://example.com")
        attempt_count = 0
        
        async def failing_then_successful_operation():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count == 1:
                raise Exception("Temporary failure")
            return "success"
        
        result, final_context = await retry_handler.execute_with_retry(
            failing_then_successful_operation, context, "test_operation"
        )
        
        assert result == "success"
        assert final_context.attempt_number == 1
        assert final_context.error_type is not None
    
    @pytest.mark.asyncio
    async def test_execute_with_retry_all_failures(self, retry_handler):
        """Test operation that fails all attempts."""
        context = ErrorContext(url="https://example.com")
        
        async def always_failing_operation():
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception, match="Persistent failure"):
            await retry_handler.execute_with_retry(
                always_failing_operation, context, "test_operation"
            )
        
        # Check that circuit breaker was triggered
        circuit_key = f"{context.url}:test_operation"
        assert await retry_handler.circuit_breaker.is_open(circuit_key)


class TestGovernmentWebsiteErrorHandler:
    """Test the main error handler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create an error handler instance for testing."""
        config = RetryConfig(max_retries=1, base_delay=0.1)
        return GovernmentWebsiteErrorHandler(config)
    
    @pytest.mark.asyncio
    async def test_handle_http_request_success(self, error_handler):
        """Test successful HTTP request handling."""
        session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.read = AsyncMock()
        session.request.return_value.__aenter__.return_value = response
        
        response, context = await error_handler.handle_http_request(
            session, "https://example.com"
        )
        
        assert response == response
        assert context.status_code == 200
        assert context.response_time is not None
    
    @pytest.mark.asyncio
    async def test_handle_http_request_failure(self, error_handler):
        """Test failed HTTP request handling."""
        session = AsyncMock()
        session.request.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            await error_handler.handle_http_request(session, "https://example.com")
    
    @pytest.mark.asyncio
    async def test_handle_selenium_operation_success(self, error_handler):
        """Test successful Selenium operation handling."""
        driver = Mock()
        
        async def successful_operation():
            return "selenium_success"
        
        result, context = await error_handler.handle_selenium_operation(
            driver, successful_operation, "https://example.com"
        )
        
        assert result == "selenium_success"
        assert context.response_time is not None
    
    @pytest.mark.asyncio
    async def test_handle_selenium_operation_failure(self, error_handler):
        """Test failed Selenium operation handling."""
        driver = Mock()
        
        async def failing_operation():
            raise WebDriverException("Selenium error")
        
        with pytest.raises(WebDriverException, match="Selenium error"):
            await error_handler.handle_selenium_operation(
                driver, failing_operation, "https://example.com"
            )
    
    @pytest.mark.asyncio
    async def test_error_statistics_tracking(self, error_handler):
        """Test error statistics tracking."""
        # Record some successes and errors
        await error_handler._record_success("https://example1.com")
        await error_handler._record_success("https://example1.com")
        await error_handler._record_error("https://example1.com", "Connection failed")
        await error_handler._record_error("https://example2.com", "Timeout")
        
        stats = await error_handler.get_error_stats()
        
        assert stats["total_urls"] == 2
        assert stats["url_stats"]["https://example1.com"]["success"] == 2
        assert stats["url_stats"]["https://example1.com"]["errors"]["Connection failed"] == 1
        assert stats["url_stats"]["https://example2.com"]["errors"]["Timeout"] == 1
    
    @pytest.mark.asyncio
    async def test_reset_statistics(self, error_handler):
        """Test statistics reset functionality."""
        # Add some statistics
        await error_handler._record_success("https://example.com")
        await error_handler._record_error("https://example.com", "Error")
        
        # Reset statistics
        await error_handler.reset_stats()
        
        stats = await error_handler.get_error_stats()
        assert stats["total_urls"] == 0
        assert len(stats["circuit_breaker_states"]) == 0


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_create_retry_config(self):
        """Test retry configuration creation utility."""
        config = create_retry_config(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            circuit_breaker_threshold=10,
            circuit_breaker_timeout=600.0
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.circuit_breaker_threshold == 10
        assert config.circuit_breaker_timeout == 600.0
    
    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns a singleton instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2
    
    def test_get_error_handler_with_config(self):
        """Test get_error_handler with custom configuration."""
        config = RetryConfig(max_retries=10)
        handler = get_error_handler(config)
        assert handler.config.max_retries == 10


class TestIntegrationScenarios:
    """Test integration scenarios for error handling."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retry_handler(self):
        """Test circuit breaker integration with retry handler."""
        config = RetryConfig(max_retries=2, circuit_breaker_threshold=2)
        retry_handler = RetryHandler(config)
        context = ErrorContext(url="https://example.com")
        
        # Fail enough times to open circuit breaker
        async def failing_operation():
            raise Exception("Persistent failure")
        
        # First two attempts should fail and open circuit breaker
        with pytest.raises(Exception):
            await retry_handler.execute_with_retry(
                failing_operation, context, "test_operation"
            )
        
        # Next attempt should be blocked by circuit breaker
        circuit_key = f"{context.url}:test_operation"
        assert await retry_handler.circuit_breaker.is_open(circuit_key)
    
    @pytest.mark.asyncio
    async def test_error_classification_with_retry(self):
        """Test error classification integration with retry logic."""
        config = RetryConfig(max_retries=1)
        retry_handler = RetryHandler(config)
        context = ErrorContext(url="https://example.com", status_code=429)
        
        async def rate_limited_operation():
            raise Exception("Rate limited")
        
        with pytest.raises(Exception):
            await retry_handler.execute_with_retry(
                rate_limited_operation, context, "test_operation"
            )
        
        # Should classify as rate limiting error
        assert context.error_type == ErrorType.HTTP_429
        assert context.error_message == "Rate limited" 