#!/usr/bin/env python3
"""
Debug script to run multiple notification system tests and capture errors
"""

import subprocess
import sys
import os

def run_multiple_tests():
    """Run multiple notification system tests and capture the output."""
    test_classes = [
        'TestEnhancedNotificationManagerComprehensive',
        'TestChannelIntegrationManagerComprehensive', 
        'TestEnhancedNotificationPreferenceManagerComprehensive',
        'TestEnhancedEmailTemplatesComprehensive',
        'TestNotificationDeliveryTrackerComprehensive',
        'TestNotificationHistoryManagerComprehensive',
        'TestNotificationTestingToolsComprehensive',
        'TestNotificationBatchingThrottlingManagerComprehensive'
    ]
    
    for test_class in test_classes:
        print(f"\n{'='*80}")
        print(f"Testing: {test_class}")
        print(f"{'='*80}")
        
        try:
            result = subprocess.run([
                sys.executable, '-m', 'pytest', 
                f'tests/test_enhanced_notification_system.py::{test_class}',
                '-v', '--tb=short'
            ], capture_output=True, text=True, cwd=os.getcwd())
            
            print("STDOUT:")
            print(result.stdout)
            if result.stderr:
                print("\nSTDERR:")
                print(result.stderr)
            print(f"Return code: {result.returncode}")
            
        except Exception as e:
            print(f"Error running test {test_class}: {e}")

if __name__ == "__main__":
    run_multiple_tests()
