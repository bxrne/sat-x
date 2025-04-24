import psutil
from typing import Optional, Dict, Any
from loguru import logger

# Define the expected path for RPi5 fan speed PWM value
# This might need adjustment depending on the exact kernel/OS setup
_FAN_PWM_SYSFS_PATH = "/sys/class/thermal/cooling_device0/cur_state"
_FAN_MAX_PWM = 255.0 # Standard max PWM value

class MetricsService:
    """Service responsible for collecting system metrics."""

    def get_system_metrics(self) -> Dict[str, Optional[float]]:
        """Collects CPU, Memory, Disk usage, Temp, and Fan speed."""
        metrics: Dict[str, Optional[float]] = {
            "cpu_percent": None,
            "memory_percent": None,
            "disk_usage_percent": None,
            "cpu_temp_celsius": None,
            "fan_speed_percent": None,
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

        # --- Collect CPU Temperature ---
        try:
            if hasattr(psutil, "sensors_temperatures"):
                temps = psutil.sensors_temperatures()
                # RPi typically uses 'cpu_thermal' or similar
                # Adapt key if necessary based on `print(temps)`
                sensor_key = None
                if 'cpu_thermal' in temps:
                    sensor_key = 'cpu_thermal'
                elif 'coretemp' in temps: # Fallback for other systems
                    sensor_key = 'coretemp'
                # Add other potential keys if needed

                if sensor_key and temps[sensor_key]:
                    # Take the first sensor reading for the key
                    metrics["cpu_temp_celsius"] = temps[sensor_key][0].current
                else:
                    logger.debug(f"Could not find a known CPU temperature sensor key in {list(temps.keys())}")
            else:
                 logger.debug("psutil.sensors_temperatures not available on this system.")
        except Exception as e:
            logger.warning(f"Could not collect CPU Temperature metrics: {e}")
            
        # --- Collect Fan Speed Percentage (RPi specific) ---
        try:
            with open(_FAN_PWM_SYSFS_PATH, 'r') as f:
                pwm_value_str = f.read().strip()
                try:
                    pwm_value = int(pwm_value_str)
                    # Convert PWM value (0-255) to percentage
                    metrics["fan_speed_percent"] = max(0.0, min(100.0, (pwm_value / _FAN_MAX_PWM) * 100.0))
                except ValueError:
                     logger.warning(f"Could not parse fan PWM value from '{_FAN_PWM_SYSFS_PATH}': '{pwm_value_str}' is not an integer.")
        except FileNotFoundError:
            logger.debug(f"Fan speed sysfs path not found: '{_FAN_PWM_SYSFS_PATH}'. Fan speed monitoring disabled.")
        except PermissionError:
            logger.warning(f"Permission denied reading fan speed from '{_FAN_PWM_SYSFS_PATH}'.")
        except Exception as e:
            logger.warning(f"Could not collect Fan Speed metrics from '{_FAN_PWM_SYSFS_PATH}': {e}")


        logger.debug(f"Collected metrics: {metrics}")
        return metrics

# Instance for easy use (could use dependency injection later)
metrics_service = MetricsService()
