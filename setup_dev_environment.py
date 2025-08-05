#!/usr/bin/env python3
"""
Setup script for development environment.
This script helps install dependencies and resolve import issues.
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        print(f"Error: {e.stderr}")
        return False

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print("✅ Python version is compatible")
    return True

def install_dependencies():
    """Install project dependencies."""
    print("\n=== Installing Dependencies ===")
    
    # Try different pip commands
    pip_commands = [
        "pip install -r requirements.txt",
        "python -m pip install -r requirements.txt",
        "py -m pip install -r requirements.txt",
        "python3 -m pip install -r requirements.txt"
    ]
    
    for command in pip_commands:
        if run_command(command, f"Installing dependencies with: {command}"):
            return True
    
    print("❌ Failed to install dependencies with any pip command")
    print("\nManual installation instructions:")
    print("1. Ensure Python is installed and in your PATH")
    print("2. Run: pip install -r requirements.txt")
    print("3. Or run: python -m pip install -r requirements.txt")
    return False

def verify_pytest_installation():
    """Verify that pytest is properly installed."""
    print("\n=== Verifying pytest installation ===")
    
    try:
        import pytest
        print(f"✅ pytest is installed (version: {pytest.__version__})")
        return True
    except ImportError:
        print("❌ pytest is not installed")
        return False

def run_test_import():
    """Test importing the test file."""
    print("\n=== Testing import ===")
    
    try:
        # Add src to path
        sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
        
        # Try to import the test file
        from notifications.email_templates.test import TestEnhancedEmailTemplates
        print("✅ Test file imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Test file import failed: {e}")
        return False

def main():
    """Main setup function."""
    print("=== CPR Scraper Development Environment Setup ===")
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install dependencies
    if not install_dependencies():
        return False
    
    # Verify pytest installation
    if not verify_pytest_installation():
        return False
    
    # Test import
    if not run_test_import():
        return False
    
    print("\n✅ Setup completed successfully!")
    print("\nYou can now run tests with:")
    print("pytest tests/")
    print("Or run specific test files:")
    print("pytest src/notifications/email_templates.test.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 