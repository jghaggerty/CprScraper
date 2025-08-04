"""
Enhanced Error Handling and Retry Mechanisms for Government Website Monitoring

This module provides robust error handling, retry logic, and circuit breaker patterns
specifically designed for monitoring government websites that may experience downtime,
rate limiting, and other reliability issues.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable, TypeVar, Union
from dataclasses import dataclass, field
from enum import Enum
import aiohttp
from aiohttp import ClientTimeout, ClientError
from selenium.common.exceptions import TimeoutException, WebDriverException
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorSeverity(Enum):
    """Classification of error severity levels."""
    LOW = "low"           # Minor issues, can retry immediately
    MEDIUM = "medium"     # Moderate issues, use exponential backoff
    HIGH = "high"         # Serious issues, longer delays
    CRITICAL = "critical" # Critical issues, circuit breaker


class ErrorType(Enum):
    """Classification of error types for government websites."""
    # Network/Connectivity Issues
    CONNECTION_TIMEOUT = "connection_timeout"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    CONNECTION_REFUSED = "connection_refused"
    NETWORK_UNREACHABLE = "network_unreachable"
    
    # HTTP Status Errors
    HTTP_404 = "http_404"
    HTTP_500 = "http_500"
    HTTP_502 = "http_502"
    HTTP_503 = "http_503"
    HTTP_504 = "http_504"
    HTTP_429 = "http_429"  # Rate limiting
    
    # Government Website Specific
    MAINTENANCE_MODE = "maintenance_mode"
    SSL_CERTIFICATE_ERROR = "ssl_certificate_error"
    CONTENT_CHANGED = "content_changed"
    REDIRECT_LOOP = "redirect_loop"
    
    # Selenium/WebDriver Issues
    SELENIUM_TIMEOUT = "selenium_timeout"
    WEBDRIVER_ERROR = "webdriver_error"
    ELEMENT_NOT_FOUND = "element_not_found"
    
    # Content/Processing Issues
    CONTENT_TOO_LARGE = "content_too_large"
    INVALID_CONTENT = "invalid_content"
    ENCODING_ERROR = "encoding_error"
    
    # Unknown/Generic
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ErrorContext:
    """Context information for error handling."""
    url: str
    agency_name: Optional[str] = None
    form_name: Optional[str] = None
    attempt_number: int = 0
    total_attempts: int = 0
    error_type: Optional[ErrorType] = None
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter_factor: float = 0.1
    timeout_multiplier: float = 1.5
    
    # Circuit breaker settings
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: float = 300.0  # 5 minutes
    circuit_breaker_half_open_timeout: float = 60.0  # 1 minute


@dataclass
class CircuitBreakerState:
    """State management for circuit breaker pattern."""
    failure_count: int = 0
    last_failure_time: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    next_attempt_time: Optional[datetime] = None


class CircuitBreaker:
    """Circuit breaker implementation for preventing cascading failures."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.states: Dict[str, CircuitBreakerState] = {}
        self._lock = asyncio.Lock()
    
    async def is_open(self, key: str) -> bool:
        """Check if circuit breaker is open for the given key."""
        async with self._lock:
            state = self.states.get(key, CircuitBreakerState())
            
            if state.state == "open":
                if state.next_attempt_time and datetime.utcnow() >= state.next_attempt_time:
                    # Transition to half-open
                    state.state = "half-open"
                    state.next_attempt_time = None
                    return False
                return True
            
            return False
    
    async def on_success(self, key: str) -> None:
        """Record a successful operation."""
        async with self._lock:
            if key not in self.states:
                self.states[key] = CircuitBreakerState()
            
            state = self.states[key]
            state.failure_count = 0
            state.state = "closed"
            state.last_failure_time = None
            state.next_attempt_time = None
    
    async def on_failure(self, key: str) -> None:
        """Record a failed operation."""
        async with self._lock:
            if key not in self.states:
                self.states[key] = CircuitBreakerState()
            
            state = self.states[key]
            state.failure_count += 1
            state.last_failure_time = datetime.utcnow()
            
            if state.failure_count >= self.config.circuit_breaker_threshold:
                state.state = "open"
                state.next_attempt_time = datetime.utcnow() + timedelta(
                    seconds=self.config.circuit_breaker_timeout
                )
                logger.warning(f"Circuit breaker opened for {key} after {state.failure_count} failures")
    
    async def get_state(self, key: str) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        async with self._lock:
            return self.states.get(key, CircuitBreakerState())


class ErrorClassifier:
    """Classifies errors and determines appropriate handling strategies."""
    
    @staticmethod
    def classify_error(error: Exception, context: ErrorContext) -> Tuple[ErrorType, ErrorSeverity]:
        """Classify an error and determine its severity."""
        
        # HTTP Status Code Classification
        if context.status_code:
            if context.status_code == 404:
                return ErrorType.HTTP_404, ErrorSeverity.MEDIUM
            elif context.status_code == 429:
                return ErrorType.HTTP_429, ErrorSeverity.HIGH
            elif context.status_code in [500, 502, 503, 504]:
                return ErrorType.HTTP_500, ErrorSeverity.HIGH
            elif context.status_code == 503:
                return ErrorType.MAINTENANCE_MODE, ErrorSeverity.HIGH
        
        # Network/Connection Errors
        if isinstance(error, asyncio.TimeoutError):
            return ErrorType.CONNECTION_TIMEOUT, ErrorSeverity.MEDIUM
        elif isinstance(error, ClientError):
            error_str = str(error).lower()
            if "dns" in error_str or "name resolution" in error_str:
                return ErrorType.DNS_RESOLUTION_FAILED, ErrorSeverity.HIGH
            elif "connection refused" in error_str:
                return ErrorType.CONNECTION_REFUSED, ErrorSeverity.HIGH
            elif "unreachable" in error_str:
                return ErrorType.NETWORK_UNREACHABLE, ErrorSeverity.HIGH
            else:
                return ErrorType.CONNECTION_TIMEOUT, ErrorSeverity.MEDIUM
        
        # Selenium/WebDriver Errors
        if isinstance(error, TimeoutException):
            return ErrorType.SELENIUM_TIMEOUT, ErrorSeverity.MEDIUM
        elif isinstance(error, WebDriverException):
            return ErrorType.WEBDRIVER_ERROR, ErrorSeverity.HIGH
        
        # Content/Processing Errors
        if "content too large" in str(error).lower():
            return ErrorType.CONTENT_TOO_LARGE, ErrorSeverity.LOW
        elif "encoding" in str(error).lower():
            return ErrorType.ENCODING_ERROR, ErrorSeverity.LOW
        
        # Government Website Specific Patterns
        error_str = str(error).lower()
        if any(term in error_str for term in ["maintenance", "scheduled", "down for maintenance"]):
            return ErrorType.MAINTENANCE_MODE, ErrorSeverity.HIGH
        elif "ssl" in error_str or "certificate" in error_str:
            return ErrorType.SSL_CERTIFICATE_ERROR, ErrorSeverity.HIGH
        elif "redirect" in error_str and "loop" in error_str:
            return ErrorType.REDIRECT_LOOP, ErrorSeverity.MEDIUM
        
        return ErrorType.UNKNOWN_ERROR, ErrorSeverity.MEDIUM
    
    @staticmethod
    def should_retry(error_type: ErrorType, severity: ErrorSeverity, attempt: int, max_attempts: int) -> bool:
        """Determine if an error should be retried."""
        if attempt >= max_attempts:
            return False
        
        # Never retry certain error types
        if error_type in [ErrorType.HTTP_404, ErrorType.CONTENT_CHANGED]:
            return False
        
        # Retry based on severity
        if severity == ErrorSeverity.LOW:
            return True
        elif severity == ErrorSeverity.MEDIUM:
            return attempt < max_attempts
        elif severity == ErrorSeverity.HIGH:
            return attempt < max_attempts - 1
        else:  # CRITICAL
            return attempt < max_attempts // 2


class RetryHandler:
    """Handles retry logic with exponential backoff and jitter."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(config)
    
    def calculate_delay(self, attempt: int, error_severity: ErrorSeverity) -> float:
        """Calculate delay for retry with exponential backoff and jitter."""
        base_delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        # Adjust delay based on error severity
        if error_severity == ErrorSeverity.HIGH:
            base_delay *= 2
        elif error_severity == ErrorSeverity.CRITICAL:
            base_delay *= 4
        
        # Apply maximum delay limit
        delay = min(base_delay, self.config.max_delay)
        
        # Add jitter to prevent thundering herd
        jitter = delay * self.config.jitter_factor * (2 * asyncio.get_event_loop().time() % 1 - 1)
        delay += jitter
        
        return max(delay, 0.1)  # Minimum 0.1 second delay
    
    async def execute_with_retry(
        self,
        operation: Callable[[], Any],
        context: ErrorContext,
        operation_name: str = "operation"
    ) -> Tuple[Any, ErrorContext]:
        """Execute an operation with retry logic."""
        
        # Check circuit breaker
        circuit_key = f"{context.url}:{operation_name}"
        if await self.circuit_breaker.is_open(circuit_key):
            raise Exception(f"Circuit breaker is open for {circuit_key}")
        
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            context.attempt_number = attempt
            context.total_attempts = attempt + 1
            
            try:
                start_time = time.time()
                result = await operation()
                response_time = time.time() - start_time
                
                # Record success
                await self.circuit_breaker.on_success(circuit_key)
                context.response_time = response_time
                
                logger.debug(f"Operation {operation_name} succeeded on attempt {attempt + 1} "
                           f"for {context.url} in {response_time:.2f}s")
                
                return result, context
                
            except Exception as e:
                last_error = e
                context.error_message = str(e)
                
                # Classify the error
                error_type, severity = ErrorClassifier.classify_error(e, context)
                context.error_type = error_type
                
                logger.warning(f"Operation {operation_name} failed on attempt {attempt + 1} "
                             f"for {context.url}: {error_type.value} ({severity.value}) - {e}")
                
                # Check if we should retry
                if not ErrorClassifier.should_retry(error_type, severity, attempt, self.config.max_retries):
                    break
                
                # Calculate delay and wait
                delay = self.calculate_delay(attempt, severity)
                logger.info(f"Retrying {operation_name} for {context.url} in {delay:.2f}s "
                          f"(attempt {attempt + 1}/{self.config.max_retries + 1})")
                
                await asyncio.sleep(delay)
        
        # Record failure in circuit breaker
        await self.circuit_breaker.on_failure(circuit_key)
        
        # Log final failure
        logger.error(f"Operation {operation_name} failed after {self.config.max_retries + 1} attempts "
                    f"for {context.url}: {last_error}")
        
        raise last_error


class GovernmentWebsiteErrorHandler:
    """Specialized error handler for government website monitoring."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.retry_handler = RetryHandler(self.config)
        self.error_stats: Dict[str, Dict[str, int]] = {}
        self._stats_lock = asyncio.Lock()
    
    async def handle_http_request(
        self,
        session: aiohttp.ClientSession,
        url: str,
        method: str = "GET",
        **kwargs
    ) -> Tuple[aiohttp.ClientResponse, ErrorContext]:
        """Handle HTTP requests with comprehensive error handling."""
        
        context = ErrorContext(url=url)
        
        async def make_request():
            timeout = ClientTimeout(total=kwargs.get('timeout', 30) * self.config.timeout_multiplier)
            async with session.request(method, url, timeout=timeout, **kwargs) as response:
                # Read content to ensure connection is complete
                await response.read()
                context.status_code = response.status
                return response
        
        try:
            response, context = await self.retry_handler.execute_with_retry(
                make_request, context, "http_request"
            )
            await self._record_success(url)
            return response, context
            
        except Exception as e:
            await self._record_error(url, str(e))
            raise
    
    async def handle_selenium_operation(
        self,
        driver,
        operation: Callable[[], Any],
        url: str
    ) -> Tuple[Any, ErrorContext]:
        """Handle Selenium operations with error handling."""
        
        context = ErrorContext(url=url)
        
        async def execute_selenium():
            return operation()
        
        try:
            result, context = await self.retry_handler.execute_with_retry(
                execute_selenium, context, "selenium_operation"
            )
            await self._record_success(url)
            return result, context
            
        except Exception as e:
            await self._record_error(url, str(e))
            raise
    
    async def _record_success(self, url: str) -> None:
        """Record successful operation."""
        async with self._stats_lock:
            if url not in self.error_stats:
                self.error_stats[url] = {"success": 0, "errors": {}}
            self.error_stats[url]["success"] += 1
    
    async def _record_error(self, url: str, error: str) -> None:
        """Record error occurrence."""
        async with self._stats_lock:
            if url not in self.error_stats:
                self.error_stats[url] = {"success": 0, "errors": {}}
            if error not in self.error_stats[url]["errors"]:
                self.error_stats[url]["errors"][error] = 0
            self.error_stats[url]["errors"][error] += 1
    
    async def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        async with self._stats_lock:
            return {
                "total_urls": len(self.error_stats),
                "url_stats": self.error_stats.copy(),
                "circuit_breaker_states": {
                    key: asdict(state) for key, state in self.retry_handler.circuit_breaker.states.items()
                }
            }
    
    async def reset_stats(self) -> None:
        """Reset error statistics."""
        async with self._stats_lock:
            self.error_stats.clear()
        self.retry_handler.circuit_breaker.states.clear()


# Global error handler instance
_global_error_handler: Optional[GovernmentWebsiteErrorHandler] = None


def get_error_handler(config: Optional[RetryConfig] = None) -> GovernmentWebsiteErrorHandler:
    """Get or create global error handler instance."""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = GovernmentWebsiteErrorHandler(config)
    return _global_error_handler


def create_retry_config(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 300.0
) -> RetryConfig:
    """Create a retry configuration with common settings."""
    return RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        circuit_breaker_threshold=circuit_breaker_threshold,
        circuit_breaker_timeout=circuit_breaker_timeout
    ) 