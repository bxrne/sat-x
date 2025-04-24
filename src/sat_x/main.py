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

    # Start Background Tasks conditionally
    logger.info("Starting background tasks...")
    task = None
    if settings.tasks.metrics.enabled:
        task = asyncio.create_task(run_metrics_collector_task(settings))
        logger.info("Metrics collector task started.")
    else:
        logger.info("Metrics collector task is disabled in settings.")

    yield # Application runs here

    # --- Shutdown --- 
    logger.info("Application shutdown...")
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Metrics collector task cancelled.")
    await engine.dispose() # Correctly dispose of the engine's connections
    logger.info("Database connection pool closed.")

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
