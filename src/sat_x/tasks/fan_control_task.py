import asyncio
from loguru import logger

from ..config import Settings
# Import the services needed
from ..services.metrics_service import metrics_service
from ..services.fan_control_service import fan_control_service

async def run_fan_control_task(settings: Settings):
    """Periodically checks CPU temp and adjusts fan speed based on config."""
    if not settings.fan_control or not settings.fan_control.enabled:
        logger.info("Fan control task is disabled in settings.")
        return

    if not settings.fan_control.control_path or not settings.fan_control.enable_path:
         logger.warning("Fan control enabled, but 'control_path' or 'enable_path' is not set in config. Task will not run.")
         return

    interval = settings.fan_control.interval_seconds
    logger.info(f"Starting fan control task with interval: {interval}s")
    logger.info(f"Fan control using control_path: {settings.fan_control.control_path}")
    logger.info(f"Fan control using enable_path: {settings.fan_control.enable_path}")

    # Initial attempt to set manual mode when starting
    # This might fail due to permissions, the service will log errors
    fan_control_service.set_fan_manual_mode(settings.fan_control)

    while True:
        try:
            # Get current CPU temperature
            # We get all metrics, but only need temp here
            current_metrics = metrics_service.get_system_metrics()
            cpu_temp = current_metrics.get("cpu_temp_celsius")

            if cpu_temp is not None:
                # Adjust fan speed based on the current temperature
                fan_control_service.adjust_fan_speed(cpu_temp, settings.fan_control)
            else:
                logger.warning("Could not get CPU temperature. Skipping fan adjustment.")

        except Exception as e:
            # Catch broad exceptions here to prevent the loop from crashing
            logger.error(f"Unhandled error in fan control loop: {e}", exc_info=True)
        
        await asyncio.sleep(interval)
