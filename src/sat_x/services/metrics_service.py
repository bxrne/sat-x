import psutil
from typing import Optional, Dict, Any
from loguru import logger

class MetricsService:
    """Service responsible for collecting system metrics."""

    def get_system_metrics(self) -> Dict[str, Optional[float]]:
        """Collects CPU, Memory, and Disk usage percentages."""
        metrics: Dict[str, Optional[float]] = {
            "cpu_percent": None,
            "memory_percent": None,
            "disk_usage_percent": None,
            # Add keys for other metrics like temperature here
        }
        try:
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1) # Short interval for responsiveness
        except Exception as e:
            logger.warning(f"Could not collect CPU metrics: {e}")

        try:
            vm = psutil.virtual_memory()
            metrics["memory_percent"] = vm.percent
        except Exception as e:
            logger.warning(f"Could not collect Memory metrics: {e}")

        try:
            # Get disk usage for the root partition ('/')
            # Adjust path if needed for other partitions
            disk = psutil.disk_usage('/')
            metrics["disk_usage_percent"] = disk.percent
        except Exception as e:
            logger.warning(f"Could not collect Disk usage metrics: {e}")

        # Example placeholder for temperature (requires platform-specific libraries)
        # try:
        #     temps = psutil.sensors_temperatures()
        #     # Find relevant temperature sensor (e.g., 'coretemp')
        #     # This part is highly system-dependent
        #     if 'coretemp' in temps:
        #         # Average or take the first core temp
        #         metrics["temperature_celsius"] = temps['coretemp'][0].current
        # except AttributeError:
        #      logger.debug("sensors_temperatures not available on this system.")
        # except Exception as e:
        #     logger.warning(f"Could not collect Temperature metrics: {e}")

        logger.debug(f"Collected metrics: {metrics}")
        return metrics

# Instance for easy use (could use dependency injection later)
metrics_service = MetricsService()
