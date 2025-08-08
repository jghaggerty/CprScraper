#!/usr/bin/env python3
"""
Debug script for preference manager tests
"""

import subprocess
import sys
import os

def run_preference_manager_tests():
    """Run preference manager tests and capture errors."""
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_enhanced_notification_system.py::TestEnhancedNotificationPreferenceManagerComprehensive',
            '-v', '--tb=long'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        print(f"Return code: {result.returncode}")
        
    except Exception as e:
        print(f"Error running preference manager tests: {e}")

if __name__ == "__main__":
    run_preference_manager_tests()
