#!/usr/bin/env python3
"""
Comprehensive Test Runner for Dashboard API Endpoints and Frontend Components

This script runs all comprehensive tests for subtask 2.9 and provides a detailed report
of test coverage and results.
"""

import subprocess
import sys
import os
import time
from datetime import datetime
from pathlib import Path


class ComprehensiveTestRunner:
    """Test runner for comprehensive dashboard testing."""
    
    def __init__(self):
        self.test_files = [
            "tests/test_dashboard_comprehensive.py",
            "tests/test_frontend_comprehensive.py",
            "tests/test_dashboard_api.py",
            "tests/test_realtime_api.py",
            "tests/test_analytics_api.py",
            "tests/test_user_management.py",
            "tests/test_widgets.py",
            "tests/test_export_functionality.py",
            "tests/test_export_utils_comprehensive.py",
            "tests/test_data_export_api.py",
            "tests/test_bulk_export_comprehensive.py",
            "tests/test_advanced_scheduling_comprehensive.py",
            "tests/test_mobile_responsiveness.py"
        ]
        
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_tests(self):
        """Run all comprehensive tests."""
        print("=" * 80)
        print("COMPREHENSIVE TEST SUITE FOR DASHBOARD API ENDPOINTS AND FRONTEND COMPONENTS")
        print("=" * 80)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        self.start_time = time.time()
        
        # Check if pytest is available
        try:
            subprocess.run([sys.executable, "-m", "pytest", "--version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("ERROR: pytest is not available. Please install pytest first:")
            print("pip install pytest")
            return False
        
        # Run each test file
        for test_file in self.test_files:
            if os.path.exists(test_file):
                print(f"Running tests in: {test_file}")
                print("-" * 60)
                
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"
                    ], capture_output=True, text=True, timeout=300)
                    
                    self.results[test_file] = {
                        'returncode': result.returncode,
                        'stdout': result.stdout,
                        'stderr': result.stderr,
                        'success': result.returncode == 0
                    }
                    
                    if result.returncode == 0:
                        print("✓ PASSED")
                    else:
                        print("✗ FAILED")
                        print("Error output:")
                        print(result.stderr)
                    
                except subprocess.TimeoutExpired:
                    print("✗ TIMEOUT (300 seconds)")
                    self.results[test_file] = {
                        'returncode': -1,
                        'stdout': '',
                        'stderr': 'Test timed out after 300 seconds',
                        'success': False
                    }
                except Exception as e:
                    print(f"✗ ERROR: {str(e)}")
                    self.results[test_file] = {
                        'returncode': -1,
                        'stdout': '',
                        'stderr': str(e),
                        'success': False
                    }
                
                print()
            else:
                print(f"WARNING: Test file not found: {test_file}")
                print()
        
        self.end_time = time.time()
        self.generate_report()
        
        return True
    
    def generate_report(self):
        """Generate comprehensive test report."""
        print("=" * 80)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        
        # Calculate statistics
        total_tests = len(self.test_files)
        passed_tests = sum(1 for result in self.results.values() if result['success'])
        failed_tests = total_tests - passed_tests
        duration = self.end_time - self.start_time
        
        print(f"Test Duration: {duration:.2f} seconds")
        print(f"Total Test Files: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%")
        print()
        
        # Detailed results
        print("DETAILED RESULTS:")
        print("-" * 60)
        
        for test_file, result in self.results.items():
            status = "✓ PASSED" if result['success'] else "✗ FAILED"
            print(f"{test_file:<50} {status}")
            
            if not result['success'] and result['stderr']:
                print(f"  Error: {result['stderr'][:100]}...")
        
        print()
        
        # Test coverage summary
        print("TEST COVERAGE SUMMARY:")
        print("-" * 60)
        
        coverage_areas = {
            "Dashboard API Endpoints": [
                "test_dashboard_comprehensive.py",
                "test_dashboard_api.py"
            ],
            "Real-time Communication": [
                "test_realtime_api.py"
            ],
            "Analytics and Historical Data": [
                "test_analytics_api.py"
            ],
            "User Management and Authentication": [
                "test_user_management.py"
            ],
            "Dashboard Widgets": [
                "test_widgets.py"
            ],
            "Export Functionality": [
                "test_export_functionality.py"
            ],
            "Frontend Components": [
                "test_frontend_comprehensive.py"
            ],
            "Mobile Responsiveness": [
                "test_mobile_responsiveness.py"
            ]
        }
        
        for area, files in coverage_areas.items():
            area_tests = [f for f in files if f in self.results]
            area_passed = sum(1 for f in area_tests if self.results[f]['success'])
            area_total = len(area_tests)
            
            if area_total > 0:
                coverage = (area_passed / area_total) * 100
                status = "✓" if area_passed == area_total else "⚠" if area_passed > 0 else "✗"
                print(f"{status} {area:<35} {area_passed}/{area_total} ({coverage:.1f}%)")
        
        print()
        
        # Recommendations
        print("RECOMMENDATIONS:")
        print("-" * 60)
        
        if failed_tests > 0:
            print("• Review and fix failing tests before deployment")
            print("• Check for missing dependencies or configuration issues")
            print("• Verify database connectivity and test data setup")
        else:
            print("• All tests passed! Ready for deployment")
            print("• Consider adding performance benchmarks")
            print("• Add integration tests with real browser automation")
        
        print()
        print("=" * 80)
        print(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
    
    def save_report(self, filename="comprehensive_test_report.txt"):
        """Save test report to file."""
        with open(filename, 'w') as f:
            # Redirect stdout to capture the report
            original_stdout = sys.stdout
            sys.stdout = f
            
            self.generate_report()
            
            sys.stdout = original_stdout
        
        print(f"Detailed report saved to: {filename}")


def main():
    """Main function to run comprehensive tests."""
    runner = ComprehensiveTestRunner()
    
    try:
        success = runner.run_tests()
        
        # Save report
        runner.save_report()
        
        if success:
            print("\nComprehensive test suite completed successfully!")
            return 0
        else:
            print("\nComprehensive test suite encountered errors.")
            return 1
            
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 