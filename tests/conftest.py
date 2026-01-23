"""Pytest configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, patch, MagicMock
import io

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

@pytest.fixture(autouse=True)
def mock_storage():
    """Mock the storage service."""
    storage_data = {}

    async def mock_upload(key, data, content_type=None, length=None):
        # data can be bytes or file-like
        if hasattr(data, 'read'):
            if hasattr(data, 'seek'):
                data.seek(0)
            content = data.read()
        else:
            content = data
        storage_data[key] = content
        return key

    async def mock_download(key):
        return storage_data.get(key, b"")

    async def mock_download_stream(key):
        content = storage_data.get(key, b"")
        mock_resp = MagicMock()
        mock_resp.read = lambda: content
        # stream returns a generator yielding bytes
        def stream_gen(chunk_size=1024):
            yield content
        mock_resp.stream = stream_gen
        mock_resp.close = lambda: None
        mock_resp.release_conn = lambda: None
        return mock_resp

    async def mock_copy(source_key, dest_key):
        storage_data[dest_key] = storage_data.get(source_key, b"")

    with patch("backend.main.storage_service") as mock:
        mock.upload = AsyncMock(side_effect=mock_upload)
        mock.download = AsyncMock(side_effect=mock_download)
        mock.download_stream = AsyncMock(side_effect=mock_download_stream)
        mock.copy = AsyncMock(side_effect=mock_copy)
        mock.delete = AsyncMock()
        mock.ensure_bucket = lambda: None
        yield mock

@pytest.fixture(scope="function")
def client(db):
    """Create a test client with test database."""
    def override_get_db():
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

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
