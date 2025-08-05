# Troubleshooting Guide

This guide helps resolve common issues with the CPR Scraper project.

## Pytest Import Error

If you encounter the error:
```
Import "pytest" could not be resolved
```

### Solution 1: Install Dependencies

The most common cause is that project dependencies haven't been installed yet.

**Windows:**
```bash
# Option 1: Use the batch file
install_dependencies.bat

# Option 2: Manual installation
pip install -r requirements.txt

# Option 3: If pip not found
python -m pip install -r requirements.txt
```

**macOS/Linux:**
```bash
pip install -r requirements.txt
# or
python3 -m pip install -r requirements.txt
```

### Solution 2: Use the Setup Script

Run the automated setup script:
```bash
python setup_dev_environment.py
```

### Solution 3: Verify Installation

After installing dependencies, verify everything works:
```bash
python test_pytest_import.py
```

## Python Not Found

If you get "Python was not found" errors:

1. **Install Python**: Download from [python.org](https://www.python.org/downloads/)
2. **Add to PATH**: During installation, check "Add Python to PATH"
3. **Verify installation**:
   ```bash
   python --version
   # or
   py --version
   ```

## Virtual Environment (Recommended)

For isolated development:

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Running Tests

Once dependencies are installed:

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest src/notifications/email_templates.test.py

# Run with verbose output
pytest -v src/notifications/email_templates.test.py
```

## Common Issues

### ImportError: No module named 'pytest'
- **Cause**: Dependencies not installed
- **Solution**: Run `pip install -r requirements.txt`

### ModuleNotFoundError: No module named 'src'
- **Cause**: Python path not set correctly
- **Solution**: Run from project root directory

### PermissionError: [Errno 13] Permission denied
- **Cause**: Insufficient permissions
- **Solution**: Run as administrator or use virtual environment

## Getting Help

If you continue to have issues:

1. Check that you're in the correct directory (project root)
2. Verify Python version (3.8+ required)
3. Try the setup script: `python setup_dev_environment.py`
4. Check the test script: `python test_pytest_import.py`

## Development Environment Setup

For a complete development environment:

1. Install Python 3.8+
2. Clone the repository
3. Create virtual environment
4. Install dependencies
5. Run tests to verify setup

```bash
git clone <repository-url>
cd CprScraper
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
pytest tests/
``` 