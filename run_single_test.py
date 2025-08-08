#!/usr/bin/env python3
"""
Simple test runner to debug notification system tests
"""

import sys
import os
import traceback

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_single_test():
    """Run a single test to see what the actual error is."""
    try:
        # Import the test module
        from tests.test_enhanced_notification_system import TestEnhancedNotificationManagerComprehensive
        
        # Create an instance and run a test
        test_instance = TestEnhancedNotificationManagerComprehensive()
        
        # Try to run the notification_manager fixture
        notification_manager = test_instance.notification_manager()
        print("✅ notification_manager fixture works")
        
        # Try to run a simple test
        print("✅ Test setup successful")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    run_single_test()
