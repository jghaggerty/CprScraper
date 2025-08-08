#!/usr/bin/env python3
"""
Debug script to test specific notification system tests
"""

import subprocess
import sys
import os

def run_specific_tests():
    """Run specific tests that were failing."""
    test_methods = [
        'tests/test_enhanced_notification_system.py::TestEnhancedNotificationManagerComprehensive::test_send_role_based_notification_not_found',
        'tests/test_enhanced_notification_system.py::TestChannelIntegrationManagerComprehensive::test_channel_connectivity_test'
    ]
    
    for test_method in test_methods:
        print(f"\n{'='*80}")
        print(f"Testing: {test_method}")
        print(f"{'='*80}")
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                test_method,
                '-v', '--tb=short'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("\nSTDERR:")
                print(result.stderr)
            print(f"Return code: {result.returncode}")
            
        except Exception as e:
            print(f"Error running test {test_method}: {e}")

if __name__ == "__main__":
    run_specific_tests()
