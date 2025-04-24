import yaml
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
import os
from pathlib import Path

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

class TasksSettings(BaseModel):
    metrics: MetricsTaskSettings
    # Add other task configurations here
    # other_task: OtherTaskSettings

class Settings(BaseModel):
    api: ApiSettings
    database: DatabaseSettings
    tasks: TasksSettings
    # Add other top-level settings here
    # logging: LoggingSettings

    @classmethod
    def load_from_yaml(cls, path: Path = DEFAULT_CONFIG_PATH) -> "Settings":
        """Loads configuration from a YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found at {path}")
        
        try:
            with open(path, 'r') as f:
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
