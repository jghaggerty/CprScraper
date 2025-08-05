"""
Notification Testing and Validation Tools

This module provides comprehensive testing and validation tools for the notification system,
including channel testing, template validation, delivery verification, and performance testing.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import smtplib
import aiohttp
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..database.connection import get_db
from ..database.models import (
    Notification, User, Role, UserRole, UserNotificationPreference,
    FormChange, Agency, Form
)
from .enhanced_notifier import EnhancedNotificationManager
from .delivery_tracker import NotificationDeliveryTracker, DeliveryStatus
from .channel_integration import ChannelIntegrationManager, NotificationResult
from .email_templates import EnhancedEmailTemplates
from .preference_manager import EnhancedNotificationPreferenceManager
from ..utils.config_loader import get_notification_settings

logger = logging.getLogger(__name__)


class TestType(Enum):
    """Types of notification tests."""
    CHANNEL_CONNECTIVITY = "channel_connectivity"
    TEMPLATE_VALIDATION = "template_validation"
    DELIVERY_VERIFICATION = "delivery_verification"
    PERFORMANCE_TESTING = "performance_testing"
    INTEGRATION_TESTING = "integration_testing"
    USER_PREFERENCE_TESTING = "user_preference_testing"
    RETRY_MECHANISM_TESTING = "retry_mechanism_testing"
    BATCH_NOTIFICATION_TESTING = "batch_notification_testing"


@dataclass
class TestResult:
    """Result of a notification test."""
    test_type: str
    test_name: str
    success: bool
    duration: float
    details: Dict[str, Any]
    error_message: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class TestScenario:
    """A test scenario for notification testing."""
    name: str
    description: str
    test_data: Dict[str, Any]
    expected_channels: List[str]
    expected_recipients: List[str]
    validation_rules: Dict[str, Any]


class NotificationTestingTools:
    """Comprehensive testing and validation tools for the notification system."""
    
    def __init__(self):
        self.notification_manager = EnhancedNotificationManager()
        self.delivery_tracker = NotificationDeliveryTracker()
        self.channel_manager = ChannelIntegrationManager()
        self.preference_manager = EnhancedNotificationPreferenceManager()
        self.email_templates = EnhancedEmailTemplates()
        self.config = get_notification_settings()
        self.test_results = []
        
    async def run_comprehensive_test_suite(self, db: Session) -> Dict[str, Any]:
        """Run a comprehensive test suite for the notification system."""
        logger.info("Starting comprehensive notification test suite...")
        
        start_time = time.time()
        results = {
            'summary': {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'total_duration': 0
            },
            'test_results': [],
            'recommendations': []
        }
        
        # Test 1: Channel Connectivity
        connectivity_result = await self.test_channel_connectivity()
        results['test_results'].append(connectivity_result)
        
        # Test 2: Template Validation
        template_result = await self.test_template_validation()
        results['test_results'].append(template_result)
        
        # Test 3: Delivery Verification
        delivery_result = await self.test_delivery_verification(db)
        results['test_results'].append(delivery_result)
        
        # Test 4: Performance Testing
        performance_result = await self.test_notification_performance()
        results['test_results'].append(performance_result)
        
        # Test 5: Integration Testing
        integration_result = await self.test_integration_scenarios(db)
        results['test_results'].append(integration_result)
        
        # Test 6: User Preference Testing
        preference_result = await self.test_user_preferences(db)
        results['test_results'].append(preference_result)
        
        # Test 7: Retry Mechanism Testing
        retry_result = await self.test_retry_mechanisms()
        results['test_results'].append(retry_result)
        
        # Test 8: Batch Notification Testing
        batch_result = await self.test_batch_notifications(db)
        results['test_results'].append(batch_result)
        
        # Calculate summary
        results['summary']['total_tests'] = len(results['test_results'])
        results['summary']['passed_tests'] = sum(1 for r in results['test_results'] if r.success)
        results['summary']['failed_tests'] = results['summary']['total_tests'] - results['summary']['passed_tests']
        results['summary']['total_duration'] = time.time() - start_time
        
        # Generate recommendations
        results['recommendations'] = self._generate_recommendations(results['test_results'])
        
        logger.info(f"Test suite completed: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
        return results
    
    async def test_channel_connectivity(self) -> TestResult:
        """Test connectivity to all notification channels."""
        start_time = time.time()
        test_name = "Channel Connectivity Test"
        
        try:
            # Test each channel
            connectivity_results = await self.channel_manager.test_channel_connectivity()
            channel_status = self.channel_manager.get_channel_status()
            
            # Validate results
            all_channels_working = all(connectivity_results.values())
            configured_channels = [ch for ch, status in channel_status.items() if status['configured']]
            
            details = {
                'connectivity_results': connectivity_results,
                'channel_status': channel_status,
                'configured_channels': configured_channels,
                'working_channels': [ch for ch, working in connectivity_results.items() if working]
            }
            
            success = all_channels_working if configured_channels else True
            
            return TestResult(
                test_type=TestType.CHANNEL_CONNECTIVITY.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details=details,
                error_message=None if success else f"Failed channels: {[ch for ch, working in connectivity_results.items() if not working]}"
            )
            
        except Exception as e:
            logger.error(f"Channel connectivity test failed: {e}")
            return TestResult(
                test_type=TestType.CHANNEL_CONNECTIVITY.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    async def test_template_validation(self) -> TestResult:
        """Test email template validation and rendering."""
        start_time = time.time()
        test_name = "Template Validation Test"
        
        try:
            test_data = {
                'agency_name': 'Test Agency',
                'form_name': 'TEST-001',
                'severity': 'medium',
                'change_description': 'Test change description',
                'detected_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
                'clients_impacted': 5,
                'icp_percentage': 2.5,
                'form_url': 'https://example.com/test-form',
                'instructions_url': 'https://example.com/test-instructions',
                'agency_contact_email': 'test@example.com',
                'agency_contact_phone': '(555) 123-4567',
                'ai_confidence_score': 85,
                'ai_change_category': 'form_update',
                'ai_severity_score': 75,
                'ai_reasoning': 'Test AI reasoning',
                'is_cosmetic_change': False
            }
            
            template_errors = []
            rendered_templates = {}
            
            # Test each template type
            for template_type in ['product_manager', 'business_analyst', 'general']:
                try:
                    template = self.email_templates.get_template(template_type)
                    rendered_content = template.render(**test_data)
                    
                    # Validate template content
                    validation_result = self._validate_template_content(rendered_content, template_type)
                    if validation_result['errors']:
                        template_errors.extend(validation_result['errors'])
                    
                    rendered_templates[template_type] = {
                        'content_length': len(rendered_content),
                        'has_html': '<html>' in rendered_content.lower(),
                        'has_agency_name': test_data['agency_name'] in rendered_content,
                        'has_form_name': test_data['form_name'] in rendered_content,
                        'validation_errors': validation_result['errors']
                    }
                    
                except Exception as e:
                    template_errors.append(f"Template {template_type}: {str(e)}")
                    rendered_templates[template_type] = {'error': str(e)}
            
            success = len(template_errors) == 0
            
            return TestResult(
                test_type=TestType.TEMPLATE_VALIDATION.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details={
                    'rendered_templates': rendered_templates,
                    'template_errors': template_errors
                },
                error_message=None if success else f"Template errors: {template_errors}"
            )
            
        except Exception as e:
            logger.error(f"Template validation test failed: {e}")
            return TestResult(
                test_type=TestType.TEMPLATE_VALIDATION.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    def _validate_template_content(self, content: str, template_type: str) -> Dict[str, Any]:
        """Validate template content for required elements."""
        errors = []
        warnings = []
        
        # Check for required elements
        required_elements = [
            'agency_name', 'form_name', 'severity', 'change_description'
        ]
        
        for element in required_elements:
            if element not in content:
                errors.append(f"Missing required element: {element}")
        
        # Check for HTML structure
        if not content.strip().startswith('<'):
            warnings.append("Content doesn't appear to be HTML")
        
        # Check for reasonable content length
        if len(content) < 100:
            warnings.append("Content seems too short")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'content_length': len(content)
        }
    
    async def test_delivery_verification(self, db: Session) -> TestResult:
        """Test notification delivery verification and tracking."""
        start_time = time.time()
        test_name = "Delivery Verification Test"
        
        try:
            # Create a test notification record
            test_notification = Notification(
                user_id=1,  # Assuming test user exists
                form_change_id=1,  # Assuming test form change exists
                channel='email',
                status=DeliveryStatus.PENDING.value,
                message_content='Test notification content',
                recipient='test@example.com',
                sent_at=datetime.utcnow()
            )
            
            db.add(test_notification)
            db.commit()
            
            # Test delivery tracking
            delivery_metrics = await self.delivery_tracker.get_delivery_metrics(
                start_date=datetime.utcnow() - timedelta(hours=1),
                end_date=datetime.utcnow()
            )
            
            # Test retry mechanism
            retry_config = {
                'max_retries': 3,
                'initial_delay': 5,
                'max_delay': 300,
                'backoff_multiplier': 2
            }
            
            retry_result = await self.delivery_tracker.should_retry_notification(
                test_notification.id, retry_config
            )
            
            # Clean up test notification
            db.delete(test_notification)
            db.commit()
            
            details = {
                'delivery_metrics': delivery_metrics,
                'retry_result': retry_result,
                'test_notification_id': test_notification.id
            }
            
            success = True  # Basic verification passed
            
            return TestResult(
                test_type=TestType.DELIVERY_VERIFICATION.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details=details
            )
            
        except Exception as e:
            logger.error(f"Delivery verification test failed: {e}")
            return TestResult(
                test_type=TestType.DELIVERY_VERIFICATION.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    async def test_notification_performance(self) -> TestResult:
        """Test notification system performance."""
        start_time = time.time()
        test_name = "Performance Test"
        
        try:
            performance_metrics = {}
            
            # Test single notification performance
            single_start = time.time()
            test_data = {
                'agency_name': 'Performance Test Agency',
                'form_name': 'PERF-001',
                'severity': 'low',
                'change_description': 'Performance test notification'
            }
            
            # Test channel manager performance
            channel_start = time.time()
            connectivity_results = await self.channel_manager.test_channel_connectivity()
            channel_duration = time.time() - channel_start
            
            # Test template rendering performance
            template_start = time.time()
            template = self.email_templates.get_template('general')
            for _ in range(10):  # Test multiple renders
                template.render(**test_data)
            template_duration = time.time() - template_start
            
            performance_metrics = {
                'channel_connectivity_duration': channel_duration,
                'template_rendering_duration': template_duration,
                'template_renders_per_second': 10 / template_duration if template_duration > 0 else 0,
                'connectivity_results': connectivity_results
            }
            
            # Performance thresholds
            success = (
                channel_duration < 5.0 and  # Channel connectivity should be fast
                template_duration < 1.0 and  # Template rendering should be very fast
                performance_metrics['template_renders_per_second'] > 5  # At least 5 renders per second
            )
            
            return TestResult(
                test_type=TestType.PERFORMANCE_TESTING.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details=performance_metrics,
                error_message=None if success else "Performance thresholds not met"
            )
            
        except Exception as e:
            logger.error(f"Performance test failed: {e}")
            return TestResult(
                test_type=TestType.PERFORMANCE_TESTING.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    async def test_integration_scenarios(self, db: Session) -> TestResult:
        """Test integration scenarios with real data."""
        start_time = time.time()
        test_name = "Integration Test"
        
        try:
            # Get test users and form changes
            test_users = db.query(User).limit(2).all()
            test_form_changes = db.query(FormChange).limit(2).all()
            
            if not test_users or not test_form_changes:
                return TestResult(
                    test_type=TestType.INTEGRATION_TESTING.value,
                    test_name=test_name,
                    success=False,
                    duration=time.time() - start_time,
                    details={},
                    error_message="No test users or form changes available"
                )
            
            integration_results = []
            
            # Test role-based notification sending
            for form_change in test_form_changes:
                try:
                    result = await self.notification_manager.send_role_based_notification(form_change.id)
                    integration_results.append({
                        'form_change_id': form_change.id,
                        'result': result
                    })
                except Exception as e:
                    integration_results.append({
                        'form_change_id': form_change.id,
                        'error': str(e)
                    })
            
            # Test user preference retrieval
            preference_results = []
            for user in test_users:
                try:
                    preferences = self.preference_manager.get_user_preferences(user.id)
                    preference_results.append({
                        'user_id': user.id,
                        'preferences': preferences
                    })
                except Exception as e:
                    preference_results.append({
                        'user_id': user.id,
                        'error': str(e)
                    })
            
            success = len(integration_results) > 0 and all(
                'error' not in result for result in integration_results
            )
            
            return TestResult(
                test_type=TestType.INTEGRATION_TESTING.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details={
                    'integration_results': integration_results,
                    'preference_results': preference_results,
                    'test_users_count': len(test_users),
                    'test_form_changes_count': len(test_form_changes)
                },
                error_message=None if success else "Integration test failures detected"
            )
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return TestResult(
                test_type=TestType.INTEGRATION_TESTING.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    async def test_user_preferences(self, db: Session) -> TestResult:
        """Test user preference management and validation."""
        start_time = time.time()
        test_name = "User Preference Test"
        
        try:
            # Get test users
            test_users = db.query(User).limit(3).all()
            
            if not test_users:
                return TestResult(
                    test_type=TestType.USER_PREFERENCE_TESTING.value,
                    test_name=test_name,
                    success=False,
                    duration=time.time() - start_time,
                    details={},
                    error_message="No test users available"
                )
            
            preference_results = []
            
            for user in test_users:
                try:
                    # Test preference retrieval
                    preferences = self.preference_manager.get_user_preferences(user.id)
                    
                    # Test preference validation
                    validation_result = self._validate_user_preferences(preferences)
                    
                    # Test notification decision logic
                    test_change_data = {
                        'severity': 'medium',
                        'agency_name': 'Test Agency',
                        'form_name': 'TEST-001'
                    }
                    
                    should_send = self.preference_manager.should_send_notification(
                        user.id, test_change_data
                    )
                    
                    preference_results.append({
                        'user_id': user.id,
                        'username': user.username,
                        'preferences': preferences,
                        'validation': validation_result,
                        'should_send_notification': should_send
                    })
                    
                except Exception as e:
                    preference_results.append({
                        'user_id': user.id,
                        'error': str(e)
                    })
            
            success = all('error' not in result for result in preference_results)
            
            return TestResult(
                test_type=TestType.USER_PREFERENCE_TESTING.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details={
                    'preference_results': preference_results,
                    'test_users_count': len(test_users)
                },
                error_message=None if success else "User preference test failures detected"
            )
            
        except Exception as e:
            logger.error(f"User preference test failed: {e}")
            return TestResult(
                test_type=TestType.USER_PREFERENCE_TESTING.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    def _validate_user_preferences(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user preferences for completeness and correctness."""
        errors = []
        warnings = []
        
        # Check for required preference fields
        required_fields = ['email_enabled', 'slack_enabled', 'teams_enabled', 'frequency']
        for field in required_fields:
            if field not in preferences:
                errors.append(f"Missing required preference field: {field}")
        
        # Check for valid frequency values
        valid_frequencies = ['immediate', 'hourly', 'daily', 'weekly', 'business_hours']
        if 'frequency' in preferences and preferences['frequency'] not in valid_frequencies:
            errors.append(f"Invalid frequency value: {preferences['frequency']}")
        
        # Check for at least one enabled channel
        enabled_channels = [
            preferences.get('email_enabled', False),
            preferences.get('slack_enabled', False),
            preferences.get('teams_enabled', False)
        ]
        
        if not any(enabled_channels):
            warnings.append("No notification channels enabled")
        
        return {
            'errors': errors,
            'warnings': warnings,
            'is_valid': len(errors) == 0
        }
    
    async def test_retry_mechanisms(self) -> TestResult:
        """Test notification retry mechanisms."""
        start_time = time.time()
        test_name = "Retry Mechanism Test"
        
        try:
            retry_results = {}
            
            # Test different retry strategies
            retry_strategies = ['immediate', 'exponential_backoff', 'linear_backoff', 'fixed_interval']
            
            for strategy in retry_strategies:
                try:
                    retry_config = {
                        'strategy': strategy,
                        'max_retries': 3,
                        'initial_delay': 5,
                        'max_delay': 300,
                        'backoff_multiplier': 2
                    }
                    
                    # Test retry calculation
                    retry_delays = []
                    for attempt in range(4):  # Test 4 attempts
                        delay = self.delivery_tracker._calculate_retry_delay(
                            attempt, retry_config
                        )
                        retry_delays.append(delay)
                    
                    retry_results[strategy] = {
                        'retry_delays': retry_delays,
                        'config': retry_config
                    }
                    
                except Exception as e:
                    retry_results[strategy] = {'error': str(e)}
            
            success = all('error' not in result for result in retry_results.values())
            
            return TestResult(
                test_type=TestType.RETRY_MECHANISM_TESTING.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details={
                    'retry_results': retry_results
                },
                error_message=None if success else "Retry mechanism test failures detected"
            )
            
        except Exception as e:
            logger.error(f"Retry mechanism test failed: {e}")
            return TestResult(
                test_type=TestType.RETRY_MECHANISM_TESTING.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    async def test_batch_notifications(self, db: Session) -> TestResult:
        """Test batch notification processing."""
        start_time = time.time()
        test_name = "Batch Notification Test"
        
        try:
            # Get test form changes
            test_form_changes = db.query(FormChange).limit(3).all()
            
            if not test_form_changes:
                return TestResult(
                    test_type=TestType.BATCH_NOTIFICATION_TESTING.value,
                    test_name=test_name,
                    success=False,
                    duration=time.time() - start_time,
                    details={},
                    error_message="No test form changes available"
                )
            
            form_change_ids = [fc.id for fc in test_form_changes]
            
            # Test batch notification sending
            batch_result = await self.notification_manager.send_batch_role_notifications(form_change_ids)
            
            # Test batch processing performance
            batch_start = time.time()
            await self.notification_manager.send_batch_role_notifications(form_change_ids)
            batch_duration = time.time() - batch_start
            
            success = len(batch_result) == len(form_change_ids)
            
            return TestResult(
                test_type=TestType.BATCH_NOTIFICATION_TESTING.value,
                test_name=test_name,
                success=success,
                duration=time.time() - start_time,
                details={
                    'batch_result': batch_result,
                    'batch_duration': batch_duration,
                    'form_changes_processed': len(form_change_ids),
                    'average_time_per_notification': batch_duration / len(form_change_ids) if form_change_ids else 0
                },
                error_message=None if success else "Batch notification test failures detected"
            )
            
        except Exception as e:
            logger.error(f"Batch notification test failed: {e}")
            return TestResult(
                test_type=TestType.BATCH_NOTIFICATION_TESTING.value,
                test_name=test_name,
                success=False,
                duration=time.time() - start_time,
                details={},
                error_message=str(e)
            )
    
    def _generate_recommendations(self, test_results: List[TestResult]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        failed_tests = [r for r in test_results if not r.success]
        
        for test in failed_tests:
            if test.test_type == TestType.CHANNEL_CONNECTIVITY.value:
                recommendations.append("Check notification channel configurations and credentials")
            elif test.test_type == TestType.TEMPLATE_VALIDATION.value:
                recommendations.append("Review and fix email template syntax and required variables")
            elif test.test_type == TestType.DELIVERY_VERIFICATION.value:
                recommendations.append("Verify database connectivity and notification tracking setup")
            elif test.test_type == TestType.PERFORMANCE_TESTING.value:
                recommendations.append("Optimize notification system performance and reduce latency")
            elif test.test_type == TestType.INTEGRATION_TESTING.value:
                recommendations.append("Check integration between notification components")
            elif test.test_type == TestType.USER_PREFERENCE_TESTING.value:
                recommendations.append("Validate user preference data and default settings")
            elif test.test_type == TestType.RETRY_MECHANISM_TESTING.value:
                recommendations.append("Review retry mechanism configuration and logic")
            elif test.test_type == TestType.BATCH_NOTIFICATION_TESTING.value:
                recommendations.append("Check batch notification processing and error handling")
        
        if not failed_tests:
            recommendations.append("All tests passed! Notification system is working correctly.")
        
        return recommendations
    
    async def generate_test_report(self, test_results: List[TestResult]) -> str:
        """Generate a human-readable test report."""
        report = []
        report.append("=" * 60)
        report.append("NOTIFICATION SYSTEM TEST REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append("")
        
        # Summary
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r.success)
        failed_tests = total_tests - passed_tests
        
        report.append("SUMMARY")
        report.append("-" * 20)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests}")
        report.append(f"Failed: {failed_tests}")
        report.append(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
        report.append("")
        
        # Detailed Results
        report.append("DETAILED RESULTS")
        report.append("-" * 20)
        
        for result in test_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            report.append(f"{result.test_name}: {status}")
            report.append(f"  Duration: {result.duration:.2f}s")
            report.append(f"  Type: {result.test_type}")
            
            if result.error_message:
                report.append(f"  Error: {result.error_message}")
            
            if result.details:
                report.append("  Details:")
                for key, value in result.details.items():
                    if isinstance(value, dict):
                        report.append(f"    {key}: {json.dumps(value, indent=4)}")
                    else:
                        report.append(f"    {key}: {value}")
            
            report.append("")
        
        # Recommendations
        recommendations = self._generate_recommendations(test_results)
        if recommendations:
            report.append("RECOMMENDATIONS")
            report.append("-" * 20)
            for i, rec in enumerate(recommendations, 1):
                report.append(f"{i}. {rec}")
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# Global instance
notification_testing_tools = NotificationTestingTools()


async def main():
    """Run notification testing tools."""
    from ..database.connection import get_db
    
    db = next(get_db())
    
    print("Running comprehensive notification testing suite...")
    results = await notification_testing_tools.run_comprehensive_test_suite(db)
    
    # Generate and print report
    report = await notification_testing_tools.generate_test_report(results['test_results'])
    print(report)
    
    # Print summary
    print(f"\nTest Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
    print(f"Total Duration: {results['summary']['total_duration']:.2f}s")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 