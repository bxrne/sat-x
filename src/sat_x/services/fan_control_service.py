import math

from loguru import logger

from ..config import FanControlSettings

_FAN_MAX_PWM = 255

class FanControlService:
    """Service responsible for adjusting fan speed based on temperature."""

    def __init__(self):
        self._last_pwm_written: int | None = None

    def _write_to_sysfs(self, path: str | None, value: str) -> bool:
        """Helper to write a value to a sysfs path."""
        if not path:
            logger.debug("Sysfs path is None, skipping write.")
            return False
        try:
            with open(path, 'w') as f:
                f.write(value)
            logger.debug(f"Successfully wrote '{value}' to '{path}'")
            return True
        except FileNotFoundError:
            logger.error(f"Sysfs path not found: '{path}'. Cannot control fan.")
        except PermissionError:
            logger.error(f"Permission denied writing '{value}' to '{path}'. Check user permissions/groups (e.g., hwmon) or udev rules.")
        except Exception as e:
            logger.error(f"Failed to write '{value}' to '{path}': {e}")
        return False

    def set_fan_manual_mode(self, config: FanControlSettings) -> bool:
        """Attempts to set the fan to manual PWM control mode."""
        logger.debug(f"Attempting to set fan manual mode using enable_path: {config.enable_path}")
        # Typically, '1' enables manual PWM control
        return self._write_to_sysfs(config.enable_path, "1")

    def adjust_fan_speed(self, current_temp: float, config: FanControlSettings):
        """Determines and sets the fan speed based on the temp curve."""
        if not config.enabled or not config.curve:
            logger.debug("Fan control disabled or curve is empty. Skipping adjustment.")
            return

        target_speed_percent = 0.0
        # Find the appropriate speed from the curve (must be sorted)
        for point in config.curve:
            if current_temp >= point.temp:
                target_speed_percent = point.speed
            else:
                # Since curve is sorted, we found the first point ABOVE current temp
                break

        # Convert percentage to PWM value (0-255)
        target_pwm = max(0, min(_FAN_MAX_PWM, int(math.ceil((target_speed_percent / 100.0) * _FAN_MAX_PWM))))

        # Only write if the PWM value needs to change
        if target_pwm != self._last_pwm_written:
            logger.info(f"CPU Temp: {current_temp:.1f}°C. Setting fan speed to {target_speed_percent:.0f}% (PWM: {target_pwm})")

            # Ensure manual mode is set (might be optional depending on hardware)
            # Doing this every time ensures it stays in manual mode
            if not self.set_fan_manual_mode(config):
                 logger.warning("Failed to set fan to manual mode. PWM write might fail or be ignored.")
                 # Continue anyway, maybe manual mode isn't needed or was already set

            if self._write_to_sysfs(config.control_path, str(target_pwm)):
                self._last_pwm_written = target_pwm # Update last written value only on success
            else:
                # Failed to write PWM, clear last written value to force retry next time
                self._last_pwm_written = None
        else:
             logger.debug(f"CPU Temp: {current_temp:.1f}°C. Target PWM {target_pwm} is same as last written. No change needed.")


# Singleton instance
fan_control_service = FanControlService()
