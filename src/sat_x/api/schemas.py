# src/sat_x/api/schemas.py
import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

# --- Metric Schemas ---

class MetricBase(BaseModel):
    """Base schema for metric data, used for creation and reading."""
    cpu_percent: Optional[float] = Field(None, example=15.5, description="CPU utilization percentage")
    memory_percent: Optional[float] = Field(None, example=45.2, description="RAM utilization percentage")
    disk_usage_percent: Optional[float] = Field(None, example=60.1, description="Root disk usage percentage")
    cpu_temp_celsius: Optional[float] = Field(None, example=55.0, description="CPU temperature in Celsius")
    fan_speed_percent: Optional[float] = Field(None, example=30.0, description="Fan speed percentage")
    # Add other metrics here if collected

class MetricCreate(MetricBase):
    """Schema used when creating a new metric internally (not via API)."""
    pass # Currently identical to base, but could diverge

class MetricRead(MetricBase):
    """Schema used when returning metric data via the API."""
    id: int = Field(..., example=1, description="Unique ID of the metric record")
    timestamp: datetime.datetime = Field(..., example="2025-04-24T16:30:00+01:00", description="Timestamp when the metric was recorded")

    class Config:
        # Pydantic V2 uses 'from_attributes' instead of 'orm_mode'
        from_attributes = True # Allows creating schema from ORM model

# --- API Response Schemas ---

class HealthCheckResponse(BaseModel):
    """Schema for the health check endpoint response."""
    status: str = Field("OK", example="OK", description="Indicates the service status")

# You might add schemas for pagination or bulk responses later
class PaginatedMetricsResponse(BaseModel):
    total: int
    items: List[MetricRead]
