from pathlib import Path

import yaml
from pydantic import BaseModel, Field, validator

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "settings.yaml"

class ApiSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    # Example for CORS origins
    # cors_origins: Optional[List[HttpUrl]] = None

class DatabaseSettings(BaseModel):
    url: str
    echo: bool = False

class MetricsTaskSettings(BaseModel):
    enabled: bool = True
    interval_seconds: int = Field(60, gt=0) # Ensure interval is positive

# --- Fan Control Settings ---
class FanCurvePoint(BaseModel):
    temp: float = Field(..., description="Temperature threshold in Celsius.")
    # Speed as percentage (0-100)
    speed: float = Field(..., ge=0, le=100, description="Fan speed percentage (0-100).")

class FanControlSettings(BaseModel):
    enabled: bool = Field(False, description="Enable/disable automatic fan control.")
    interval_seconds: int = Field(10, gt=0, description="How often to check temp and adjust fan.")
    # Note: These paths are typical but might need verification on the target system
    control_path: str | None = Field("/sys/class/hwmon/hwmon0/pwm1", description="Sysfs path to write PWM value (0-255).")
    enable_path: str | None = Field("/sys/class/hwmon/hwmon0/pwm1_enable", description="Sysfs path to enable/disable manual PWM control (e.g., write '1').")
    curve: list[FanCurvePoint] = Field(
        default_factory=list,
        description="List of temp (°C) to speed (%) points, sorted by temp."
    )

    @validator('curve')
    def check_curve_sorted(cls, v):
        if not v:
            # Allow empty curve if disabled, maybe log warning if enabled?
            return v
        temps = [p.temp for p in v]
        if temps != sorted(temps):
            raise ValueError('Fan curve points must be sorted by temperature.')
        return v

class TasksSettings(BaseModel):
    metrics: MetricsTaskSettings
    # Add other task configurations here
    # other_task: OtherTaskSettings

class Settings(BaseModel):
    api: ApiSettings
    database: DatabaseSettings
    tasks: TasksSettings
    fan_control: FanControlSettings | None = None # Added Fan Control
    # Add other top-level settings here
    # logging: LoggingSettings

    @classmethod
    def load_from_yaml(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Settings":
        """Loads configuration from a YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found at {path}")

        try:
            with open(path) as f:
                yaml_data = yaml.safe_load(f)
            return cls.model_validate(yaml_data)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {path}: {e}")
            raise
        except Exception as e:
            print(f"Error loading configuration from {path}: {e}")
            raise

# Load settings globally on import
# Consider dependency injection for more complex scenarios
try:
    # Ensure the config directory exists before trying to load
    if not DEFAULT_CONFIG_PATH.parent.exists():
        DEFAULT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        print(f"Created config directory at {DEFAULT_CONFIG_PATH.parent}")
        # Optionally, create a default settings.yaml here if it doesn't exist

    settings = Settings.load_from_yaml()
except FileNotFoundError as e:
    print(f"Error: {e}")
    print(f"Please ensure '{DEFAULT_CONFIG_PATH}' exists and is configured.")
    # Provide default settings or raise an error depending on desired behavior
    # For now, let's raise to make missing config explicit
    raise SystemExit(1)
except Exception as e:
    print(f"Unexpected error loading settings: {e}")
    raise SystemExit(1)

def get_settings() -> Settings:
    """Dependency function to get settings (useful for FastAPI)."""
    return settings
