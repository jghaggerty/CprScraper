# Fixing pytest Import Error

## Problem
The error "Import 'pytest' could not be resolved" occurs because pytest is not installed in your Python environment.

## Solutions

### Option 1: Quick Fix - Install pytest only
If you just want to install pytest to resolve the import error:

```bash
# Try these commands in order until one works:
pip install pytest
python -m pip install pytest
py -m pip install pytest
python3 -m pip install pytest
```

### Option 2: Complete Setup - Install all dependencies
For a complete development environment setup:

1. **Install Python** (if not already installed):
   - Download from: https://www.python.org/downloads/
   - **Important**: Check "Add Python to PATH" during installation

2. **Install all project dependencies**:
   ```bash
   # Run the batch file (Windows)
   install_dependencies.bat
   
   # Or manually install requirements
   pip install -r requirements.txt
   python -m pip install -r requirements.txt
   py -m pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import pytest; print(f'pytest version: {pytest.__version__}')"
   ```

### Option 3: Virtual Environment (Recommended)
For isolated development environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Verify pytest
python -c "import pytest; print('pytest installed successfully')"
```

### Option 4: Use the setup script
The project includes a setup script that handles dependency installation:

```bash
# Run the setup script
python setup_dev_environment.py
py setup_dev_environment.py
```

## Troubleshooting

### If Python is not found:
1. **Check if Python is installed**:
   ```bash
   where python
   where py
   ```

2. **If not found, install Python**:
   - Download from https://www.python.org/downloads/
   - Make sure to check "Add Python to PATH" during installation
   - Restart your terminal/command prompt after installation

### If pip is not found:
1. **Try alternative commands**:
   ```bash
   python -m pip install pytest
   py -m pip install pytest
   ```

2. **Upgrade pip**:
   ```bash
   python -m pip install --upgrade pip
   ```

### If you get permission errors:
1. **Run as administrator** (Windows)
2. **Use user installation**:
   ```bash
   pip install --user pytest
   ```

## Verification

After installation, verify that pytest works:

```bash
# Check pytest version
pytest --version

# Run a simple test
python -c "import pytest; print('pytest imported successfully')"

# Run the specific test file
pytest src/notifications/email_templates.test.py
```

## IDE Configuration

If you're using an IDE (VS Code, PyCharm, etc.):

1. **Select the correct Python interpreter**:
   - Make sure it points to the Python installation with pytest
   - If using a virtual environment, select the venv's Python

2. **Reload the IDE** after installing dependencies

3. **Check the Python path** in your IDE settings

## Project Structure

The test file is located at:
```
src/notifications/email_templates.test.py
```

Dependencies are defined in:
```
requirements.txt
```

Setup scripts:
```
install_dependencies.bat
setup_dev_environment.py
```

## Next Steps

Once pytest is installed:

1. **Run all tests**:
   ```bash
   pytest tests/
   ```

2. **Run specific test file**:
   ```bash
   pytest src/notifications/email_templates.test.py
   ```

3. **Run with verbose output**:
   ```bash
   pytest -v src/notifications/email_templates.test.py
   ```

## Support

If you continue to have issues:

1. Check the `TROUBLESHOOTING.md` file in the project root
2. Ensure Python is properly installed and in your PATH
3. Try using a virtual environment for isolation
4. Check that your IDE is using the correct Python interpreter 