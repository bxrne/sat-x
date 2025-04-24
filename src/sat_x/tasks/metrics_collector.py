import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from loguru import logger

from ..config import Settings
from ..database import AsyncSessionFactory # Use the factory to create sessions
from ..models import Metric
from ..repositories import MetricRepository
from ..services.metrics_service import metrics_service # Import the service

async def collect_and_store_metrics(session: AsyncSession):
    """Collects metrics using the service and stores them using the repository."""
    collected_data = metrics_service.get_system_metrics()

    # Create a Metric ORM object from the collected data
    metric = Metric(
        cpu_percent=collected_data.get("cpu_percent"),
        memory_percent=collected_data.get("memory_percent"),
        disk_usage_percent=collected_data.get("disk_usage_percent"),
        # Add other fields as needed
    )

    # Use the session factory to get a session within the task
    repo = MetricRepository(session)
    try:
        await repo.add(metric)
        await session.commit() # Commit the transaction
        logger.info(f"Stored new metric record: ID {metric.id}")
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to store metrics: {e}", exc_info=True)

async def run_metrics_collector_task(settings: Settings): 
    """Periodically runs the metric collection and storage task."""
    if not settings.tasks.metrics.enabled:
        logger.info("Metrics collector task is disabled in settings.")
        return

    interval = settings.tasks.metrics.interval_seconds
    logger.info(f"Starting metrics collector task with interval: {interval}s")

    while True:
        try:
            async with AsyncSessionFactory() as session:
                await collect_and_store_metrics(session)
        except Exception as e:
            # Catch broad exceptions here to prevent the loop from crashing
            logger.error(f"Unhandled error in metrics collector loop: {e}", exc_info=True)
        
        await asyncio.sleep(interval)
