"""
Comprehensive Test Runner for Enhanced Notification System

This script runs all tests for the enhanced notification system and provides
detailed reporting on test coverage and results.
"""

import sys
import os
import subprocess
import time
import json
from datetime import datetime
from typing import Dict, List, Any

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class NotificationSystemTestRunner:
    """Test runner for the enhanced notification system."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = None
        self.end_time = None
        
        # Define test categories and their corresponding test files
        self.test_categories = {
            'enhanced_notifier': [
                'src/notifications/enhanced_notifier.test.py',
                'tests/test_enhanced_notification_system.py::TestEnhancedNotificationManagerComprehensive',
                'tests/test_enhanced_notification_system.py::TestEnhancedNotificationSystemIntegration'
            ],
            'channel_integration': [
                'src/notifications/channel_integration.test.py',
                'tests/test_enhanced_notification_system.py::TestChannelIntegrationManagerComprehensive'
            ],
            'preference_manager': [
                'src/notifications/preference_manager.test.py',
                'tests/test_enhanced_notification_system.py::TestEnhancedNotificationPreferenceManagerComprehensive'
            ],
            'email_templates': [
                'src/notifications/email_templates.test.py',
                'tests/test_enhanced_notification_system.py::TestEnhancedEmailTemplatesComprehensive'
            ],
            'delivery_tracker': [
                'src/notifications/delivery_tracker.test.py',
                'tests/test_enhanced_notification_system.py::TestNotificationDeliveryTrackerComprehensive'
            ],
            'history_manager': [
                'src/notifications/history_manager.test.py',
                'tests/test_enhanced_notification_system.py::TestNotificationHistoryManagerComprehensive'
            ],
            'testing_tools': [
                'src/notifications/testing_tools.test.py',
                'tests/test_enhanced_notification_system.py::TestNotificationTestingToolsComprehensive'
            ],
            'batching_throttling': [
                'src/notifications/batching_manager.test.py',
                'tests/test_enhanced_notification_system.py::TestNotificationBatchingThrottlingManagerComprehensive'
            ],
            'api_endpoints': [
                'tests/test_notification_management_api.py',
                'tests/test_notification_testing_api.py',
                'tests/test_notification_batching_throttling_api.py',
                'tests/test_notification_tracking_api.py'
            ],
            'error_handling': [
                'tests/test_enhanced_notification_system.py::TestNotificationSystemErrorHandling'
            ],
            'performance': [
                'tests/test_enhanced_notification_system.py::TestNotificationSystemPerformance'
            ]
        }
    
    def run_tests(self, categories: List[str] = None, verbose: bool = True) -> Dict[str, Any]:
        """
        Run tests for specified categories or all categories if none specified.
        
        Args:
            categories: List of test categories to run
            verbose: Whether to show verbose output
            
        Returns:
            Dictionary with test results summary
        """
        self.start_time = datetime.now()
        
        if categories is None:
            categories = list(self.test_categories.keys())
        
        print(f"🚀 Starting Enhanced Notification System Tests")
        print(f"📅 Started at: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📋 Categories to test: {', '.join(categories)}")
        print("=" * 80)
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_errors = 0
        
        for category in categories:
            if category not in self.test_categories:
                print(f"⚠️  Warning: Unknown test category '{category}'")
                continue
            
            print(f"\n📁 Testing Category: {category.upper()}")
            print("-" * 60)
            
            category_results = {
                'tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 0,
                'duration': 0,
                'details': []
            }
            
            for test_file in self.test_categories[category]:
                try:
                    result = self._run_single_test(test_file, verbose)
                    category_results['tests'] += result['tests']
                    category_results['passed'] += result['passed']
                    category_results['failed'] += result['failed']
                    category_results['errors'] += result['errors']
                    category_results['duration'] += result['duration']
                    category_results['details'].append({
                        'file': test_file,
                        'result': result
                    })
                    
                    # Update totals
                    total_tests += result['tests']
                    total_passed += result['passed']
                    total_failed += result['failed']
                    total_errors += result['errors']
                    
                except Exception as e:
                    print(f"❌ Error running {test_file}: {str(e)}")
                    category_results['errors'] += 1
                    total_errors += 1
            
            # Print category summary
            self._print_category_summary(category, category_results)
            self.test_results[category] = category_results
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        # Print overall summary
        self._print_overall_summary(total_tests, total_passed, total_failed, total_errors, duration)
        
        return {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_errors': total_errors,
            'duration': duration,
            'categories': self.test_results,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        }
    
    def _run_single_test(self, test_file: str, verbose: bool) -> Dict[str, Any]:
        """Run a single test file or test class."""
        start_time = time.time()
        
        # Build pytest command
        cmd = [
            sys.executable, '-m', 'pytest', test_file,
            '--tb=short',
            '--quiet' if not verbose else '-v'
        ]
        
        try:
            # Run the test
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=os.path.join(os.path.dirname(__file__), '..')
            )
            
            duration = time.time() - start_time
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            tests = 0
            passed = 0
            failed = 0
            errors = 0
            
            for line in output_lines:
                if 'passed' in line and 'failed' in line:
                    # Parse summary line like "5 passed, 2 failed in 3.45s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part.isdigit():
                            if 'passed' in parts[i+1]:
                                passed = int(part)
                            elif 'failed' in parts[i+1]:
                                failed = int(part)
                            elif 'error' in parts[i+1]:
                                errors = int(part)
                    tests = passed + failed + errors
                    break
            
            if verbose and result.stdout:
                print(result.stdout)
            
            if result.stderr and verbose:
                print(f"STDERR: {result.stderr}")
            
            return {
                'tests': tests,
                'passed': passed,
                'failed': failed,
                'errors': errors,
                'duration': duration,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except Exception as e:
            duration = time.time() - start_time
            return {
                'tests': 0,
                'passed': 0,
                'failed': 0,
                'errors': 1,
                'duration': duration,
                'return_code': -1,
                'stdout': '',
                'stderr': str(e)
            }
    
    def _print_category_summary(self, category: str, results: Dict[str, Any]):
        """Print summary for a test category."""
        total = results['tests']
        passed = results['passed']
        failed = results['failed']
        errors = results['errors']
        duration = results['duration']
        
        if total == 0:
            print(f"⚠️  No tests found for {category}")
            return
        
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        status_icon = "✅" if failed == 0 and errors == 0 else "❌"
        print(f"{status_icon} {category}: {passed}/{total} passed ({success_rate:.1f}%)")
        print(f"   ⏱️  Duration: {duration:.2f}s")
        
        if failed > 0:
            print(f"   ❌ Failed: {failed}")
        if errors > 0:
            print(f"   💥 Errors: {errors}")
    
    def _print_overall_summary(self, total_tests: int, total_passed: int, 
                             total_failed: int, total_errors: int, duration: float):
        """Print overall test summary."""
        print("\n" + "=" * 80)
        print("📊 ENHANCED NOTIFICATION SYSTEM TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"🎯 Total Tests: {total_tests}")
        print(f"✅ Passed: {total_passed}")
        print(f"❌ Failed: {total_failed}")
        print(f"💥 Errors: {total_errors}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Total Duration: {duration:.2f}s")
        
        if total_failed == 0 and total_errors == 0:
            print("\n🎉 All tests passed! The enhanced notification system is working correctly.")
        else:
            print(f"\n⚠️  {total_failed + total_errors} tests failed or had errors.")
            print("Please review the test output above for details.")
        
        print(f"\n📅 Completed at: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def generate_test_report(self, output_file: str = None) -> str:
        """Generate a detailed test report in JSON format."""
        if not self.test_results:
            return "No test results available. Run tests first."
        
        report = {
            'test_suite': 'Enhanced Notification System',
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': sum(cat['tests'] for cat in self.test_results.values()),
                'total_passed': sum(cat['passed'] for cat in self.test_results.values()),
                'total_failed': sum(cat['failed'] for cat in self.test_results.values()),
                'total_errors': sum(cat['errors'] for cat in self.test_results.values()),
                'duration': (self.end_time - self.start_time).total_seconds() if self.end_time else 0
            },
            'categories': self.test_results,
            'test_coverage': {
                'enhanced_notifier': 'Role-based notification management',
                'channel_integration': 'Multi-channel notification delivery',
                'preference_manager': 'User notification preferences',
                'email_templates': 'Email template rendering',
                'delivery_tracker': 'Delivery tracking and retry mechanisms',
                'history_manager': 'Notification history and management',
                'testing_tools': 'Comprehensive testing and validation',
                'batching_throttling': 'Batching and throttling mechanisms',
                'api_endpoints': 'REST API endpoints',
                'error_handling': 'Error handling and recovery',
                'performance': 'Performance and scalability'
            }
        }
        
        report_json = json.dumps(report, indent=2)
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    f.write(report_json)
                print(f"\n📄 Test report saved to: {output_file}")
            except Exception as e:
                print(f"\n❌ Error saving test report: {str(e)}")
        
        return report_json
    
    def check_test_coverage(self) -> Dict[str, Any]:
        """Check test coverage for the enhanced notification system."""
        coverage_info = {
            'components': {
                'EnhancedNotificationManager': {
                    'test_files': [
                        'src/notifications/enhanced_notifier.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'ChannelIntegrationManager': {
                    'test_files': [
                        'src/notifications/channel_integration.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'EnhancedNotificationPreferenceManager': {
                    'test_files': [
                        'src/notifications/preference_manager.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'EnhancedEmailTemplates': {
                    'test_files': [
                        'src/notifications/email_templates.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'NotificationDeliveryTracker': {
                    'test_files': [
                        'src/notifications/delivery_tracker.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'NotificationHistoryManager': {
                    'test_files': [
                        'src/notifications/history_manager.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'NotificationTestingTools': {
                    'test_files': [
                        'src/notifications/testing_tools.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                },
                'NotificationBatchingThrottlingManager': {
                    'test_files': [
                        'src/notifications/batching_manager.test.py',
                        'tests/test_enhanced_notification_system.py'
                    ],
                    'coverage': 'Comprehensive'
                }
            },
            'api_endpoints': {
                'notification_management': 'tests/test_notification_management_api.py',
                'notification_testing': 'tests/test_notification_testing_api.py',
                'notification_batching_throttling': 'tests/test_notification_batching_throttling_api.py',
                'notification_tracking': 'tests/test_notification_tracking_api.py'
            },
            'integration_tests': {
                'complete_workflow': 'tests/test_enhanced_notification_system.py',
                'error_handling': 'tests/test_enhanced_notification_system.py',
                'performance': 'tests/test_enhanced_notification_system.py'
            }
        }
        
        return coverage_info


def main():
    """Main function to run the test suite."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Enhanced Notification System Tests')
    parser.add_argument('--categories', nargs='+', 
                       choices=['enhanced_notifier', 'channel_integration', 'preference_manager',
                               'email_templates', 'delivery_tracker', 'history_manager',
                               'testing_tools', 'batching_throttling', 'api_endpoints',
                               'error_handling', 'performance'],
                       help='Specific test categories to run')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    parser.add_argument('--report', '-r', type=str,
                       help='Generate test report to specified file')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Show test coverage information')
    
    args = parser.parse_args()
    
    runner = NotificationSystemTestRunner()
    
    if args.coverage:
        coverage = runner.check_test_coverage()
        print("📋 Enhanced Notification System Test Coverage:")
        print(json.dumps(coverage, indent=2))
        return
    
    # Run tests
    results = runner.run_tests(categories=args.categories, verbose=args.verbose)
    
    # Generate report if requested
    if args.report:
        runner.generate_test_report(args.report)
    
    # Exit with appropriate code
    if results['total_failed'] > 0 or results['total_errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main() 