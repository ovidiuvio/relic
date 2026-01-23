"""Pytest configuration and fixtures."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.main import app
from backend.database import Base, get_db
from backend.config import settings


# Use in-memory SQLite for tests
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client with test database."""
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Mock storage service to avoid MinIO connection
    with patch("backend.main.storage_service") as mock_storage:
        # Simple in-memory storage for tests
        storage_data = {}

        async def mock_upload(key, data, content_type="application/octet-stream"):
            storage_data[key] = data
            return key

        async def mock_download(key):
            return storage_data.get(key, b"")

        async def mock_delete(key):
            storage_data.pop(key, None)

        async def mock_exists(key):
            return key in storage_data

        mock_storage.ensure_bucket = MagicMock()
        mock_storage.upload = AsyncMock(side_effect=mock_upload)
        mock_storage.download = AsyncMock(side_effect=mock_download)
        mock_storage.delete = AsyncMock(side_effect=mock_delete)
        mock_storage.exists = AsyncMock(side_effect=mock_exists)

        with TestClient(app) as test_client:
            yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_file_content():
    """Sample file content for testing."""
    return b"Hello, World! This is a test relic."


@pytest.fixture
def test_file_dict(test_file_content):
    """Sample file dict for testing."""
    return {
        "name": "test.txt",
        "content_type": "text/plain",
        "content": test_file_content
    }
