#!/usr/bin/env python3
"""
Debug script to run pytest and capture errors
"""

import subprocess
import sys
import os

def run_pytest_with_output():
    """Run pytest and capture the output."""
    try:
        # Run pytest with verbose output and capture stderr
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_enhanced_notification_system.py::TestEnhancedNotificationManagerComprehensive::test_send_role_based_notification_success',
            '-v', '--tb=long'
        ], capture_output=True, text=True, cwd=os.getcwd())
        
        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")
        
    except Exception as e:
        print(f"Error running pytest: {e}")

if __name__ == "__main__":
    run_pytest_with_output()
