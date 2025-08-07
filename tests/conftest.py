import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set test environment variables before any imports
os.environ["SKIP_DB_INIT"] = "true"
os.environ["USE_TEST_DB"] = "true"

# Import after setting environment variables
try:
    from src.database.connection import engine, SessionLocal
    from src.database.models import Base
except ImportError as e:
    # If import fails, create mock objects for testing
    print(f"Warning: Could not import src modules: {e}")
    engine = None
    SessionLocal = None
    Base = None

@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine."""
    # Use in-memory SQLite for testing
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    if Base is not None:
        Base.metadata.create_all(bind=test_engine)
    return test_engine

@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create a test session factory."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    return TestingSessionLocal

@pytest.fixture
def db_session(test_session_factory):
    """Create a test database session."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(autouse=True)
def mock_database():
    """Mock database connections for tests that don't need real database."""
    with patch('src.database.connection.get_db') as mock_get_db:
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None
        yield mock_session
