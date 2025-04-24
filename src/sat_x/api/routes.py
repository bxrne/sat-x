# src/sat_x/api/routes.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import datetime

from ..database import get_db_session
from ..repositories import MetricRepository
from . import schemas # Import the schemas we just defined

# Create an API router
router = APIRouter()

# --- Health Check Endpoint ---

@router.get(
    "/health",
    response_model=schemas.HealthCheckResponse,
    summary="Health Check",
    description="Simple endpoint to check if the API is running.",
    tags=["Health"] # Tag for OpenAPI documentation grouping
)
async def health_check():
    """Returns a simple 'OK' status."""
    return schemas.HealthCheckResponse(status="OK")

# --- Metrics Endpoints ---

@router.get(
    "/metrics/latest",
    response_model=Optional[schemas.MetricRead], # Can be None if no metrics yet
    summary="Get Latest Metric",
    description="Retrieves the most recently recorded system metric.",
    tags=["Metrics"]
)
async def get_latest_metric(
    session: AsyncSession = Depends(get_db_session)
) -> Optional[schemas.MetricRead]:
    """
    Fetches the latest metric record from the database.
    Returns `null` if no metrics have been recorded yet.
    """
    repo = MetricRepository(session)
    latest_metric = await repo.get_latest()
    if not latest_metric:
        # Return None or raise 404, depending on desired behavior
        # Returning None allows frontend to handle 'no data yet' gracefully
        return None
    # Pydantic will automatically convert the ORM model to the schema
    return latest_metric


@router.get(
    "/metrics/range",
    response_model=List[schemas.MetricRead],
    summary="Get Metrics in Time Range",
    description="Retrieves system metrics recorded within a specific time window.",
    tags=["Metrics"]
)
async def get_metrics_in_range(
    start_time: datetime.datetime = Query(..., description="Start timestamp (ISO 8601 format)"),
    end_time: datetime.datetime = Query(..., description="End timestamp (ISO 8601 format)"),
    limit: int = Query(100, gt=0, le=1000, description="Maximum number of metrics to return"),
    session: AsyncSession = Depends(get_db_session)
) -> List[schemas.MetricRead]:
    """
    Fetches metrics recorded between `start_time` and `end_time`.
    Results are ordered by timestamp ascending.
    """
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="Start time must be before end time.")

    repo = MetricRepository(session)
    metrics = await repo.get_range(start_time=start_time, end_time=end_time, limit=limit)
    # Pydantic automatically converts the list of ORM models
    return metrics

# Add more endpoints as needed, e.g., get metric by ID, list all (paginated)
