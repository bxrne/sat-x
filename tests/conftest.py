from collections.abc import Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from sat_x.api.routes import router as api_router
from sat_x.config import Settings, get_settings
from sat_x.database import Base


# --- Test App Instance (without lifespan) ---
@pytest.fixture(scope="session")
def test_app() -> FastAPI:
    """Creates a FastAPI instance for testing without the main lifespan."""
    app = FastAPI(title="Test Sat-X API")
    app.include_router(api_router, prefix="/api/v1")
    return app

# --- Settings Override ---
# Use a separate in-memory SQLite DB for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Overrides settings for testing, notably the database URL."""
    original_settings = get_settings()
    settings_override = Settings(
        api=original_settings.api,
        database=original_settings.database.model_copy(update={"url": TEST_DATABASE_URL, "echo": False}),
        tasks=original_settings.tasks.model_copy(update={"metrics": {"enabled": False}})
    )
    return settings_override

# --- API Test Client Fixture ---

@pytest.fixture(scope="function")
def test_client(
    test_app: FastAPI,
    test_settings: Settings,
    setup_database
) -> Generator[TestClient, None, None]:
    """Provides a synchronous TestClient using a lifespan-free app."""

    def get_override_settings() -> Settings:
        return test_settings

    test_app.dependency_overrides.clear()
    test_app.dependency_overrides[get_settings] = get_override_settings

    with TestClient(test_app) as client:
        yield client

    test_app.dependency_overrides.clear()

# --- Database Fixtures ---

@pytest.fixture(scope="session")
def test_engine():
    """Creates a test database engine (in-memory SQLite)."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    return engine

@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Creates a session factory bound to the test engine."""
    TestSessionFactory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
        class_=AsyncSession
    )
    return TestSessionFactory

@pytest_asyncio.fixture(scope="function")
async def setup_database(test_engine):
    """Ensures tables are created clean before a test and dropped after."""
    async with test_engine.begin() as conn:
        # Drop tables first to ensure a clean state, then create
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield # Run the test function
    # Drop after is still good practice
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
