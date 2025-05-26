import datetime
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import Base
from .models import Metric

ModelType = TypeVar("ModelType", bound=Base)

# --- Generic Base Repository --- (Optional but good practice)
class BaseRepository(Generic[ModelType], ABC):
    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self._session = session
        self._model = model

    @abstractmethod
    async def add(self, entity: ModelType) -> ModelType:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> ModelType | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[ModelType]:
        raise NotImplementedError

# --- Concrete Metric Repository ---
class MetricRepository:
    """Handles database operations for Metric objects."""
    def __init__(self, session: AsyncSession):
        self._session = session

    async def add(self, metric: Metric) -> Metric:
        """Adds a new metric record to the database."""
        self._session.add(metric)
        await self._session.flush() # Assigns ID without full commit
        await self._session.refresh(metric)
        return metric

    async def get_latest(self) -> Metric | None:
        """Retrieves the most recent metric record."""
        stmt = select(Metric).order_by(Metric.timestamp.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def get_range(
        self,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        limit: int = 100
    ) -> list[Metric]:
        """Retrieves metrics within a specified time range."""
        stmt = (
            select(Metric)
            .where(Metric.timestamp >= start_time, Metric.timestamp <= end_time)
            .order_by(Metric.timestamp.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, limit: int = 100) -> list[Metric]:
        """Lists all metrics, limited by `limit`."""
        stmt = select(Metric).order_by(Metric.timestamp.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
