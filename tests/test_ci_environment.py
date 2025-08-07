import os
import sys
import pytest

def test_python_path_includes_project_root():
    """Test that the project root is in the Python path."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert project_root in sys.path, f"Project root {project_root} not in sys.path"

def test_environment_variables_set():
    """Test that required environment variables are set."""
    assert os.getenv("SKIP_DB_INIT") == "true"
    assert os.getenv("USE_TEST_DB") == "true"

def test_src_import_works():
    """Test that src module can be imported."""
    try:
        import src
        assert src is not None
    except ImportError as e:
        pytest.fail(f"Failed to import src module: {e}")

def test_database_connection_import():
    """Test that database connection can be imported."""
    try:
        from src.database.connection import DATABASE_URL
        assert DATABASE_URL == "sqlite:///:memory:"
    except ImportError as e:
        pytest.fail(f"Failed to import database connection: {e}")
