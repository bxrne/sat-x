# sat-x

System Agent Task orchestrator with monitoring and API.

This application monitors system metrics (CPU, RAM, Disk) and stores them in a database. It provides a JSON API for accessing this data and includes a background task system for periodic operations.

## Features

*   **System Metrics Monitoring**: Collects CPU, Memory, and Disk usage.
*   **SQLite Database**: Uses SQLAlchemy with `aiosqlite` for asynchronous database operations.
*   **FastAPI Backend**: Provides a robust, async JSON API based on OpenAPI standards.
*   **YAML Configuration**: Highly configurable via `config/settings.yaml`.
*   **Background Tasks**: Uses `asyncio` for running periodic tasks (e.g., metrics collection).
*   **uv Build System**: Managed with the `uv` package manager.
*   **Typed Code**: Uses Python type hints throughout.
*   **Repository Pattern**: Organizes database interactions.

## Setup

1.  **Prerequisites**:
    *   Python 3.9+
    *   `uv` (Install via `pip install uv` or see [uv documentation](https://github.com/astral-sh/uv))

2.  **Clone the repository (if applicable)**:
    ```bash
    git clone <repository-url>
    cd sat-x
    ```

3.  **Create a virtual environment and install dependencies using `uv`**:
    ```bash
    # Create and activate a virtual environment named .venv using uv
    uv venv 

    # Install dependencies using uv (creates requirements.lock if none exists)
    # Use 'uv pip sync requirements.lock' if lock file exists and you want exact versions
    uv pip install -e . 
    ```
    *Note: `uv venv` creates a `.venv` directory by default. `uv pip install -e .` installs the project in editable mode.* 

4.  **Configure the application**:
    *   Copy or rename `config/settings.yaml.example` to `config/settings.yaml` (if an example exists).
    *   Edit `config/settings.yaml`:
        *   Verify the `database.url`. The default `sqlite+aiosqlite:///./satx.db` will create a `satx.db` file in the directory where you run the application.
        *   Adjust `api.host`, `api.port`, and `tasks.metrics.interval_seconds` as needed.

5.  **Initialize the Database**:
    *   Run the database initialization command using the `sat-x` CLI entry point:
    ```bash
    sat-x init-db-cli 
    ```
    *   This will create the `satx.db` file (if it doesn't exist) and set up the necessary tables (e.g., `metrics`).

## Running the Application

*   **Start the FastAPI server and background tasks**:
    ```bash
    sat-x run-server
    ```
*   **For development with auto-reload**:
    ```bash
    sat-x run-server --reload
    ```

## Running in dev 

Testing can be triggered by `uv run pytest` or `uv run pytest --cov` for coverage reports.

Linting can be used with `ruff` by running:
```bash
uv run ruff check .
```
