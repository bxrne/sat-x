from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from sat_x.database import get_db_session  # Import the original dependency getter
from sat_x.models import Metric
from sat_x.repositories import MetricRepository

# Mark all tests in this module as async
# pytestmark = pytest.mark.asyncio

# --- Test Health Endpoint ---

def test_health_check(test_client: TestClient):
    """Test the /health endpoint."""
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "OK"}

# --- Test Metrics Endpoints ---

@pytest.mark.asyncio
async def test_get_latest_metric_empty(
    test_client: TestClient,
    setup_database, # Explicitly request DB setup
    test_session_factory: async_sessionmaker[AsyncSession], # Inject factory
    test_app: FastAPI # Inject test_app to override dependency
):
    """Test getting latest metric when database is empty."""
    async with test_session_factory() as session:
        # Override the db session dependency for *this specific test's session*
        async def get_override_session() -> AsyncGenerator[AsyncSession, None]:
            yield session
        test_app.dependency_overrides[get_db_session] = get_override_session

        # --- Debugging: Check DB state before API call ---
        count_result = await session.execute(select(func.count(Metric.id)))
        initial_count = count_result.scalar_one_or_none()
        print(f"\nDEBUG: Initial metric count in test_get_latest_metric_empty: {initial_count}")
        assert initial_count == 0, f"Database not empty at start of test! Count: {initial_count}"
        # --- End Debugging ---

        response = test_client.get("/api/v1/metrics/latest")
        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response JSON: {response.text}")
        assert response.status_code == 200
        assert response.json() is None

    # Clean up override after test
    del test_app.dependency_overrides[get_db_session]


@pytest.mark.asyncio
async def test_get_latest_metric_with_data(
    test_client: TestClient,
    setup_database, # Explicitly request DB setup
    test_session_factory: async_sessionmaker[AsyncSession], # Inject factory
    test_app: FastAPI # Inject test_app to override dependency
):
    """Test getting latest metric after adding some data."""
    async with test_session_factory() as session:
        # Override the db session dependency
        async def get_override_session() -> AsyncGenerator[AsyncSession, None]:
            yield session
        test_app.dependency_overrides[get_db_session] = get_override_session

        repo = MetricRepository(session) # Use local session
        now = datetime.now(UTC)
        metric1 = Metric(timestamp=now - timedelta(minutes=10), cpu_percent=10.0, memory_percent=20.0, disk_usage_percent=30.0)
        metric2 = Metric(timestamp=now - timedelta(minutes=5), cpu_percent=15.0, memory_percent=25.0, disk_usage_percent=35.0) # Newer

        await repo.add(metric1)
        await repo.add(metric2)
        await session.commit() # Commit after adding
        await session.refresh(metric1)
        await session.refresh(metric2)

        # Act: Call the API endpoint (sync call)
        response = test_client.get("/api/v1/metrics/latest")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data is not None
        assert data["id"] == metric2.id
        assert data["cpu_percent"] == 15.0
        assert "timestamp" in data

@pytest.mark.asyncio
async def test_get_metrics_range(
    test_client: TestClient,
    setup_database, # Explicitly request DB setup
    test_session_factory: async_sessionmaker[AsyncSession], # Inject factory
    test_app: FastAPI # Inject test_app to override dependency
):
    """Test getting metrics within a time range."""
    async with test_session_factory() as session:
        # Override the db session dependency
        async def get_override_session() -> AsyncGenerator[AsyncSession, None]:
            yield session
        test_app.dependency_overrides[get_db_session] = get_override_session

        # Arrange: Add metrics (timestamps are auto-generated on add/commit)
        now = datetime.now(UTC)
        metric1 = Metric(timestamp=now - timedelta(minutes=10), cpu_percent=10.0, memory_percent=20.0, disk_usage_percent=30.0)
        metric2 = Metric(timestamp=now - timedelta(minutes=5), cpu_percent=15.0, memory_percent=25.0, disk_usage_percent=35.0)
        metric3 = Metric(timestamp=now - timedelta(minutes=1), cpu_percent=12.0, memory_percent=22.0, disk_usage_percent=32.0)

        repo = MetricRepository(session) # Use local session
        await repo.add(metric1)
        await repo.add(metric2)
        await repo.add(metric3)
        await session.commit()
        await session.refresh(metric1)
        await session.refresh(metric2)
        await session.refresh(metric3)

        # Need accurate start/end times - get from DB or construct carefully
        start_time = metric1.timestamp
        # Ensure end_time includes m3 but potentially excludes anything later
        # Add a small delta to m3's timestamp for safety
        end_time = metric3.timestamp + timedelta(seconds=1)

        # Act (sync call)
        response = test_client.get(
            f"/api/v1/metrics/range?start_time={start_time.isoformat()}&end_time={end_time.isoformat()}"
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["id"] == metric1.id
        assert data[1]["id"] == metric2.id
        assert data[2]["id"] == metric3.id
        assert data[0]["cpu_percent"] == 10.0

@pytest.mark.asyncio
async def test_get_metrics_range_invalid_times(
    test_client: TestClient,
    setup_database, # Explicitly request DB setup
    test_session_factory: async_sessionmaker[AsyncSession], # Inject factory
    test_app: FastAPI # Inject test_app to override dependency
):
    """Test getting metrics with start time after end time."""
    async with test_session_factory() as session:
        # Override the db session dependency
        async def get_override_session() -> AsyncGenerator[AsyncSession, None]:
            yield session
        test_app.dependency_overrides[get_db_session] = get_override_session

        # No need to add data for this test, just check the response
        end_time = datetime.utcnow().replace(tzinfo=UTC)
        start_time = end_time + timedelta(minutes=10) # Start time after end time

        # Format timestamps for URL query (simple format, no timezone)
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')

        response = test_client.get(
            f"/api/v1/metrics/range?start_time={start_str}&end_time={end_str}"
        )
        # Now expect a 400 Bad Request from our custom validation, not 422 from Pydantic parsing
        assert response.status_code == 400
        response_data = response.json()
        assert "detail" in response_data
        # Check for the specific string detail from the HTTPException
        assert response_data["detail"] == "Start time must be before end time."

    # Clean up override after test
    del test_app.dependency_overrides[get_db_session]
