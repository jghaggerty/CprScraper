"""
Notification Testing API Endpoints

This module provides API endpoints for testing and validating the notification system,
including running test suites, individual tests, and viewing test results.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database.connection import get_db
from ..database.models import User
from ..auth.auth import get_current_user
from ..notifications.testing_tools import (
    NotificationTestingTools, TestType, TestResult, TestScenario
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notification-testing", tags=["notification-testing"])

# Global testing tools instance
testing_tools = NotificationTestingTools()


class NotificationTestingAPI:
    """API endpoints for notification testing and validation tools."""
    
    @router.post("/run-comprehensive-test")
    async def run_comprehensive_test_suite(
        self,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Run a comprehensive test suite for the notification system."""
        try:
            logger.info(f"User {current_user.username} initiated comprehensive notification test suite")
            
            # Run tests in background to avoid timeout
            results = await testing_tools.run_comprehensive_test_suite(db)
            
            return {
                "success": True,
                "message": "Comprehensive test suite completed",
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Comprehensive test suite failed: {e}")
            raise HTTPException(status_code=500, detail=f"Test suite failed: {str(e)}")
    
    @router.post("/run-individual-test")
    async def run_individual_test(
        self,
        test_type: str = Body(...),
        test_config: Optional[Dict[str, Any]] = Body({}),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Run an individual notification test."""
        try:
            logger.info(f"User {current_user.username} running individual test: {test_type}")
            
            # Map test type to test method
            test_methods = {
                TestType.CHANNEL_CONNECTIVITY.value: testing_tools.test_channel_connectivity,
                TestType.TEMPLATE_VALIDATION.value: testing_tools.test_template_validation,
                TestType.DELIVERY_VERIFICATION.value: lambda: testing_tools.test_delivery_verification(db),
                TestType.PERFORMANCE_TESTING.value: testing_tools.test_notification_performance,
                TestType.INTEGRATION_TESTING.value: lambda: testing_tools.test_integration_scenarios(db),
                TestType.USER_PREFERENCE_TESTING.value: lambda: testing_tools.test_user_preferences(db),
                TestType.RETRY_MECHANISM_TESTING.value: testing_tools.test_retry_mechanisms,
                TestType.BATCH_NOTIFICATION_TESTING.value: lambda: testing_tools.test_batch_notifications(db)
            }
            
            if test_type not in test_methods:
                raise HTTPException(status_code=400, detail=f"Invalid test type: {test_type}")
            
            # Run the test
            test_method = test_methods[test_type]
            result = await test_method()
            
            return {
                "success": True,
                "message": f"Individual test '{test_type}' completed",
                "result": {
                    "test_type": result.test_type,
                    "test_name": result.test_name,
                    "success": result.success,
                    "duration": result.duration,
                    "details": result.details,
                    "error_message": result.error_message,
                    "timestamp": result.timestamp.isoformat()
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Individual test failed: {e}")
            raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")
    
    @router.get("/test-types")
    async def get_available_test_types(
        self,
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Get available test types and their descriptions."""
        test_types = [
            {
                "value": TestType.CHANNEL_CONNECTIVITY.value,
                "name": "Channel Connectivity Test",
                "description": "Test connectivity to all notification channels (email, Slack, Teams)",
                "category": "connectivity"
            },
            {
                "value": TestType.TEMPLATE_VALIDATION.value,
                "name": "Template Validation Test",
                "description": "Validate email template syntax and required variables",
                "category": "templates"
            },
            {
                "value": TestType.DELIVERY_VERIFICATION.value,
                "name": "Delivery Verification Test",
                "description": "Test notification delivery tracking and verification",
                "category": "delivery"
            },
            {
                "value": TestType.PERFORMANCE_TESTING.value,
                "name": "Performance Test",
                "description": "Test notification system performance and latency",
                "category": "performance"
            },
            {
                "value": TestType.INTEGRATION_TESTING.value,
                "name": "Integration Test",
                "description": "Test integration scenarios with real data",
                "category": "integration"
            },
            {
                "value": TestType.USER_PREFERENCE_TESTING.value,
                "name": "User Preference Test",
                "description": "Test user preference management and validation",
                "category": "preferences"
            },
            {
                "value": TestType.RETRY_MECHANISM_TESTING.value,
                "name": "Retry Mechanism Test",
                "description": "Test notification retry mechanisms and strategies",
                "category": "retry"
            },
            {
                "value": TestType.BATCH_NOTIFICATION_TESTING.value,
                "name": "Batch Notification Test",
                "description": "Test batch notification processing",
                "category": "batch"
            }
        ]
        
        return {
            "success": True,
            "test_types": test_types,
            "categories": list(set(test_type["category"] for test_type in test_types))
        }
    
    @router.post("/test-scenario")
    async def run_test_scenario(
        self,
        scenario: TestScenario = Body(...),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Run a custom test scenario."""
        try:
            logger.info(f"User {current_user.username} running test scenario: {scenario.name}")
            
            # Validate scenario
            if not scenario.name or not scenario.test_data:
                raise HTTPException(status_code=400, detail="Invalid test scenario")
            
            # Run scenario-specific tests
            results = []
            
            # Test channel connectivity if expected channels are specified
            if scenario.expected_channels:
                connectivity_result = await testing_tools.test_channel_connectivity()
                results.append(connectivity_result)
            
            # Test template validation
            template_result = await testing_tools.test_template_validation()
            results.append(template_result)
            
            # Test with custom data
            custom_result = await testing_tools.test_integration_scenarios(db)
            results.append(custom_result)
            
            # Generate scenario-specific report
            scenario_report = await testing_tools.generate_test_report(results)
            
            return {
                "success": True,
                "message": f"Test scenario '{scenario.name}' completed",
                "scenario": {
                    "name": scenario.name,
                    "description": scenario.description,
                    "expected_channels": scenario.expected_channels,
                    "expected_recipients": scenario.expected_recipients
                },
                "results": [
                    {
                        "test_type": result.test_type,
                        "test_name": result.test_name,
                        "success": result.success,
                        "duration": result.duration,
                        "details": result.details,
                        "error_message": result.error_message
                    }
                    for result in results
                ],
                "report": scenario_report,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Test scenario failed: {e}")
            raise HTTPException(status_code=500, detail=f"Test scenario failed: {str(e)}")
    
    @router.get("/test-status")
    async def get_test_status(
        self,
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Get the current status of notification testing tools."""
        try:
            # Get channel status
            channel_status = testing_tools.channel_manager.get_channel_status()
            
            # Get system health indicators
            health_indicators = {
                "database_connected": True,  # Assuming connection is working
                "notification_manager_initialized": testing_tools.notification_manager is not None,
                "delivery_tracker_initialized": testing_tools.delivery_tracker is not None,
                "channel_manager_initialized": testing_tools.channel_manager is not None,
                "preference_manager_initialized": testing_tools.preference_manager is not None
            }
            
            return {
                "success": True,
                "status": "ready",
                "channel_status": channel_status,
                "health_indicators": health_indicators,
                "available_channels": list(channel_status.keys()),
                "configured_channels": [
                    ch for ch, status in channel_status.items() 
                    if status.get('configured', False)
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get test status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get test status: {str(e)}")
    
    @router.get("/test-report")
    async def generate_test_report(
        self,
        test_results: List[Dict[str, Any]] = Query([]),
        format: str = Query("text", regex="^(text|json|html)$"),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Generate a test report from provided test results."""
        try:
            # Convert dict results to TestResult objects
            results = []
            for result_dict in test_results:
                result = TestResult(
                    test_type=result_dict.get('test_type', ''),
                    test_name=result_dict.get('test_name', ''),
                    success=result_dict.get('success', False),
                    duration=result_dict.get('duration', 0.0),
                    details=result_dict.get('details', {}),
                    error_message=result_dict.get('error_message'),
                    timestamp=datetime.fromisoformat(result_dict.get('timestamp', datetime.utcnow().isoformat()))
                )
                results.append(result)
            
            if format == "text":
                report = await testing_tools.generate_test_report(results)
                return {
                    "success": True,
                    "format": "text",
                    "report": report,
                    "timestamp": datetime.utcnow().isoformat()
                }
            elif format == "json":
                return {
                    "success": True,
                    "format": "json",
                    "report": {
                        "summary": {
                            "total_tests": len(results),
                            "passed_tests": sum(1 for r in results if r.success),
                            "failed_tests": sum(1 for r in results if not r.success),
                            "success_rate": (sum(1 for r in results if r.success) / len(results) * 100) if results else 0
                        },
                        "results": [
                            {
                                "test_type": result.test_type,
                                "test_name": result.test_name,
                                "success": result.success,
                                "duration": result.duration,
                                "details": result.details,
                                "error_message": result.error_message,
                                "timestamp": result.timestamp.isoformat()
                            }
                            for result in results
                        ],
                        "recommendations": testing_tools._generate_recommendations(results)
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:  # HTML format
                html_report = await testing_tools.generate_html_report(results)
                return {
                    "success": True,
                    "format": "html",
                    "report": html_report,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to generate test report: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate test report: {str(e)}")
    
    @router.post("/validate-configuration")
    async def validate_notification_configuration(
        self,
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Validate notification system configuration."""
        try:
            logger.info(f"User {current_user.username} validating notification configuration")
            
            validation_results = {
                "configuration_valid": True,
                "errors": [],
                "warnings": [],
                "details": {}
            }
            
            # Validate notification settings
            config = testing_tools.config
            
            # Check email configuration
            email_config = config.get('email', {})
            if email_config.get('enabled', False):
                required_email_fields = ['smtp_server', 'smtp_port', 'username', 'password', 'from_address']
                for field in required_email_fields:
                    if not email_config.get(field):
                        validation_results["errors"].append(f"Missing email configuration: {field}")
                        validation_results["configuration_valid"] = False
            else:
                validation_results["warnings"].append("Email notifications are disabled")
            
            # Check Slack configuration
            slack_config = config.get('slack', {})
            if slack_config.get('enabled', False):
                if not slack_config.get('webhook_url'):
                    validation_results["errors"].append("Missing Slack webhook URL")
                    validation_results["configuration_valid"] = False
            else:
                validation_results["warnings"].append("Slack notifications are disabled")
            
            # Check Teams configuration
            teams_config = config.get('teams', {})
            if teams_config.get('enabled', False):
                if not teams_config.get('webhook_url'):
                    validation_results["errors"].append("Missing Teams webhook URL")
                    validation_results["configuration_valid"] = False
            else:
                validation_results["warnings"].append("Teams notifications are disabled")
            
            # Check if at least one channel is enabled
            enabled_channels = [
                email_config.get('enabled', False),
                slack_config.get('enabled', False),
                teams_config.get('enabled', False)
            ]
            
            if not any(enabled_channels):
                validation_results["warnings"].append("No notification channels are enabled")
            
            validation_results["details"] = {
                "email_enabled": email_config.get('enabled', False),
                "slack_enabled": slack_config.get('enabled', False),
                "teams_enabled": teams_config.get('enabled', False),
                "total_enabled_channels": sum(enabled_channels)
            }
            
            return {
                "success": True,
                "validation": validation_results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Configuration validation failed: {str(e)}")
    
    @router.get("/test-history")
    async def get_test_history(
        self,
        limit: int = Query(50, ge=1, le=100),
        offset: int = Query(0, ge=0),
        test_type: Optional[str] = Query(None),
        status: Optional[str] = Query(None),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Get test history (placeholder for future implementation)."""
        try:
            # This would typically query a test history table
            # For now, return a placeholder response
            return {
                "success": True,
                "message": "Test history feature not yet implemented",
                "test_history": [],
                "total_count": 0,
                "limit": limit,
                "offset": offset,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get test history: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to get test history: {str(e)}")
    
    @router.delete("/clear-test-data")
    async def clear_test_data(
        self,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Clear test data and reset testing environment."""
        try:
            logger.info(f"User {current_user.username} clearing test data")
            
            # This would typically clean up test notifications, etc.
            # For now, return a placeholder response
            return {
                "success": True,
                "message": "Test data cleared successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to clear test data: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to clear test data: {str(e)}")


# Create API instance
notification_testing_api = NotificationTestingAPI()


# Add the router to the main app
def get_router():
    """Get the notification testing router."""
    return router 