#!/usr/bin/env python3
"""
Test script to verify pytest import and test file functionality.
"""

import sys
import os

def test_pytest_import():
    """Test if pytest can be imported."""
    try:
        import pytest
        print(f"✅ pytest imported successfully (version: {pytest.__version__})")
        return True
    except ImportError as e:
        print(f"❌ pytest import failed: {e}")
        return False

def test_test_file_import():
    """Test if the test file can be imported."""
    try:
        # Add src to path
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        sys.path.insert(0, src_path)
        
        # Try to import the test file
        from notifications.email_templates.test import TestEnhancedEmailTemplates
        print("✅ Test file imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Test file import failed: {e}")
        return False

def test_email_templates_import():
    """Test if the email templates module can be imported."""
    try:
        # Add src to path
        src_path = os.path.join(os.path.dirname(__file__), 'src')
        sys.path.insert(0, src_path)
        
        # Try to import the email templates module
        from notifications.email_templates import EnhancedEmailTemplates
        print("✅ Email templates module imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Email templates module import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Testing pytest and module imports ===\n")
    
    # Test pytest import
    pytest_ok = test_pytest_import()
    
    # Test email templates module import
    templates_ok = test_email_templates_import()
    
    # Test test file import
    test_file_ok = test_test_file_import()
    
    print("\n=== Summary ===")
    if pytest_ok and templates_ok and test_file_ok:
        print("✅ All tests passed! The pytest import error is resolved.")
        print("\nYou can now run tests with:")
        print("  pytest src/notifications/email_templates.test.py")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        if not pytest_ok:
            print("\nTo fix pytest import error:")
            print("  pip install pytest")
            print("  or run: fix_pytest_import.bat")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 