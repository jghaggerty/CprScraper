import os
import pytest
from src.database.connection import DATABASE_URL, test_connection, init_db
from src.database.models import Base

def test_database_url_setting():
    """Test that the database URL is set correctly for testing."""
    assert DATABASE_URL == "sqlite:///:memory:"

def test_database_initialization():
    """Test that database initialization works in test environment."""
    try:
        init_db()
        assert test_connection() is True
    except Exception as e:
        pytest.fail(f"Database initialization failed: {e}")

def test_environment_variables():
    """Test that environment variables are set correctly."""
    assert os.getenv("SKIP_DB_INIT") == "true"
    assert os.getenv("USE_TEST_DB") == "true"
