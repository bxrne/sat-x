import logging
import sys
from pathlib import Path

from loguru import logger

# Default log level (can be overridden by config later if needed)
LOG_LEVEL = "INFO"
LOG_FILE = Path("logs/sat-x.log") # Example file path

# Intercept standard logging
class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def setup_logging():
    """Configures Loguru logger."""
    # Remove default handlers
    logger.remove()

    # Add console sink with coloring
    logger.add(
        sys.stderr,
        level=LOG_LEVEL.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True # Set diagnose=False in production for performance
    )

    # Optional: Add file sink for structured JSON logging
    # Ensure the logs directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.add(
        LOG_FILE,
        level=LOG_LEVEL.upper(),
        rotation="10 MB", # Rotate log file when it reaches 10 MB
        retention="7 days", # Keep logs for 7 days
        compression="zip", # Compress rotated logs
        serialize=True, # Output logs as JSON objects
        enqueue=True, # Asynchronous logging for performance
        backtrace=True,
        diagnose=False # Keep diagnose False for file logs usually
    )

    # Intercept standard logging messages
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    # Configure specific loggers if needed (e.g., uvicorn)
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    # Propagate false to prevent uvicorn default handler
    logging.getLogger("uvicorn.error").propagate = False

    logger.info("Loguru logging configured.")
    logger.info(f"Console log level: {LOG_LEVEL}")
    logger.info(f"File log level: {LOG_LEVEL}, Path: {LOG_FILE}")

# Initial setup on import (can be called explicitly if preferred)
# setup_logging()
