import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
import typer
import uvicorn
from fastapi import FastAPI
from .logging_config import setup_logging, logger
setup_logging()

# --- App Initialization --- 
from .config import Settings, get_settings
from .api import routes as api_routes
from .database import init_db, engine
from .tasks.metrics_collector import run_metrics_collector_task
from .tasks.fan_control_task import run_fan_control_task

# List to keep track of background tasks
background_tasks = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Get settings *within* the lifespan context to respect overrides
    settings: Settings = get_settings() # Use a direct call
    
    logger.info("Application startup...")
    logger.info(f"Using database: {settings.database.url}")
    
    # Initialize Database
    logger.info("Initializing database...")
    await init_db(engine)
    logger.info("Database initialized.")

    # --- Start Background Tasks --- 
    logger.info("Starting background tasks...")
    background_tasks.clear() # Ensure list is clear before starting

    # Start Metrics Collector Task
    if settings.tasks and settings.tasks.metrics.enabled:
        metrics_task = asyncio.create_task(run_metrics_collector_task(settings))
        background_tasks.add(metrics_task)
        logger.info("Metrics collector task scheduled.")
        # Keep track of the task to cancel it properly on shutdown
        metrics_task.add_done_callback(background_tasks.discard)
    else:
        logger.info("Metrics collector task is disabled in settings.")

    # Start Fan Control Task
    if settings.fan_control and settings.fan_control.enabled:
        fan_task = asyncio.create_task(run_fan_control_task(settings))
        background_tasks.add(fan_task)
        logger.info("Fan control task scheduled.")
        # Keep track of the task to cancel it properly on shutdown
        fan_task.add_done_callback(background_tasks.discard)
    else:
        logger.info("Fan control task is disabled in settings.")

    yield # Application runs here

    # --- Shutdown --- 
    logger.info("Application shutdown initiated...")
    logger.info(f"Cancelling {len(background_tasks)} background tasks...")
    for task in list(background_tasks): # Iterate over a copy
        if not task.done():
            task.cancel()
            try:
                # Wait for the task to acknowledge cancellation
                await asyncio.wait_for(task, timeout=5.0) 
            except asyncio.CancelledError:
                logger.info(f"Task {task.get_name()} cancelled successfully.")
            except asyncio.TimeoutError:
                logger.warning(f"Task {task.get_name()} did not cancel within timeout.")
            except Exception as e:
                logger.error(f"Error during cancellation of task {task.get_name()}: {e}")
        else:
            # Log if task already finished (e.g., due to an error)
            exception = task.exception()
            if exception:
                logger.warning(f"Background task {task.get_name()} finished with exception: {exception}")
            else:
                 logger.info(f"Background task {task.get_name()} already finished.")
                 
    # Explicitly wait for all tasks to ensure they are cleaned up
    if background_tasks: # Check if set is not empty after callbacks
        await asyncio.gather(*background_tasks, return_exceptions=True)
        logger.info("All background tasks awaited.")
        
    await engine.dispose() # Correctly dispose of the engine's connections
    logger.info("Database connection pool closed.")
    logger.info("Application shutdown complete.")

# Create FastAPI app instance
app_instance = FastAPI(
    title="sat-x API",
    description="API for monitoring and managing sat-x tasks and data.",
    version="0.1.0",
    lifespan=lifespan, # Use the lifespan context manager
    # Add other FastAPI options like docs_url, redoc_url if needed
    openapi_url="/api/v1/openapi.json" # Default OpenAPI spec location
)

# --- Request Logging Middleware ---
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests and their processing time."""
    idem = f"{request.client.host}:{request.client.port} - " \
           f"{request.method} {request.url.path}"
    logger.info(f"===> Request started: {idem}")
    start_time = time.time()
    
    try:
        response: Response = await call_next(request)
    except Exception as e:
        logger.exception(f"!!! Request failed: {idem}")
        # Re-raise the exception to let FastAPI handle it (e.g., return 500)
        raise e 
    finally:
        process_time = (time.time() - start_time) * 1000
        # This part runs even if an exception occurred before response was formed
        formatted_process_time = f"{process_time:.2f}ms"
        logger.info(f"<=== Request finished: {idem} in {formatted_process_time}")
        
    return response

# Add the logging middleware
app_instance.add_middleware(BaseHTTPMiddleware, dispatch=log_requests)

# --- Middleware --- (Example: CORS)
# if settings.api.cors_origins:
#     app_instance.add_middleware(
#         CORSMiddleware,
#         allow_origins=[str(origin) for origin in settings.api.cors_origins],
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )
# else:
#     # Allow all origins if not specified (adjust for security as needed)
#     app_instance.add_middleware(
#         CORSMiddleware,
#         allow_origins=["*"], 
#         allow_credentials=True,
#         allow_methods=["*"],
#         allow_headers=["*"],
#     )

# --- API Routers --- 
app_instance.include_router(api_routes.router, prefix="/api/v1", tags=["APIv1"])

# --- Typer CLI App --- 
cli_app = typer.Typer()

@cli_app.command()
def run_server(
    host: str = typer.Option(default=None, help="Host to bind the server to."),
    port: int = typer.Option(default=None, help="Port to bind the server to."),
    reload: bool = typer.Option(default=False, help="Enable auto-reload.")
):
    """Runs the sat-x FastAPI web server."""
    # Get settings to use for default host/port if not provided
    # This call should happen at runtime, not module load time
    runtime_settings = get_settings()
    final_host = host if host is not None else runtime_settings.api.host
    final_port = port if port is not None else runtime_settings.api.port
    
    logger.info(f"Starting server on {final_host}:{final_port} {'with reload' if reload else ''}")
    uvicorn.run(
        "sat_x.main:app_instance", 
        host=final_host,
        port=final_port, 
        reload=reload,
        log_config=None # Use our configured loguru logger
    )

@cli_app.command()
def init_db_cli():
    """Initializes the database (creates tables)."""
    async def _init():
        logger.info("Running database initialization via CLI...")
        await init_db()
        logger.info("Database initialization complete.")
        await engine.dispose() # Dispose engine after CLI task
    asyncio.run(_init())

# Add other CLI commands here (e.g., run tasks manually, manage users)

# --- Main execution --- 
# This makes `python -m sat_x.main` work if needed, 
# but `typer` is the primary entry point via `pyproject.toml` script.
if __name__ == "__main__":
    cli_app()

# Define the entry point for the script defined in pyproject.toml
app = cli_app # Typer app is the main entry point
