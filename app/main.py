# app/main.py

from app.core.middleware import http_exception_handler, generic_exception_handler
from app.core.middleware import LoggingMiddleware
from app.services.dash.background_check import (
    initialize_service_monitor,
    shutdown_service_monitor,
)
from app.services.n8n import close_n8n_client
from app.services.redis.redis import (
    startup_redis_service,
    shutdown_redis_service,
    get_redis_service,
)
from app.services.auth.auth import startup_auth_service
from app.services.mongo.mongo import (
    startup_mongo_service,
    shutdown_mongo_service,
    get_mongo_service,
)
from app.services.quote.sync import lifespan_shutdown as sheet_sync_shutdown
from app.services.quote.sync import lifespan_startup as sheet_sync_startup
from app.services.hubspot import HubSpotManager
from app.services.bland import bland_manager
from app.api.v1.api import api_router_v1
from app.api.v1.endpoints import home  # Import home router
from app.core.config import settings
import logfire
import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# --- Logfire Configuration ---

# Configure Logfire using environment variables directly or defaults
# This ensures Logfire is configured before any other module (like config.py) might use it.
_logfire_project_name = os.getenv(
    "PROJECT_NAME", "Stahla AI SDR"
)  # Default from config.py
_logfire_dev_mode_str = os.getenv("DEV", "False")  # Default from config.py
_logfire_dev_mode = _logfire_dev_mode_str.lower() in ("true", "1", "yes", "t")

_logfire_config = {
    "send_to_logfire": True,  # Consistent with previous direct configuration
    "service_name": _logfire_project_name,
}

# If not in DEV mode, disable console logging for Logfire.
# Otherwise, Logfire's default (console=True) will apply.
if not _logfire_dev_mode:
  _logfire_config["console"] = False

# Note: LOGFIRE_TOKEN is typically picked up by Logfire automatically from the environment.
# If it needed to be explicitly passed, you would get it from os.getenv("LOGFIRE_TOKEN")
# and add it to _logfire_config if present.

logfire.configure(**_logfire_config)
logfire.instrument_pydantic()
# --- End Logfire Configuration ---

# --- Project Structure Imports (Now that Logfire is configured) ---


# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
  # Startup: Initialize connections, load models, etc.
  logfire.info("Application startup: Initializing resources.")

  mongo_service_instance = None  # Initialize to None
  try:
    # Initialize Redis
    await startup_redis_service()

    # Initialize MongoDB (connects, creates indexes)
    await startup_mongo_service()
    # Get MongoService instance for other services that need it during startup
    mongo_service_instance = await get_mongo_service()

    # Initialize Auth Service (creates initial user if needed)
    # startup_auth_service will get the mongo_service instance itself
    await startup_auth_service()  # Removed mongo_service argument

    # Initialize Sheet Sync Service
    # sheet_sync_startup will get the mongo_service instance itself
    await sheet_sync_startup()  # Removed mongo_service argument
    logfire.info("Sheet Sync service startup initiated.")

    # Initialize other managers/services if needed
    app.state.bland_manager = (
        bland_manager  # bland_manager is already initialized globally
    )
    app.state.hubspot_manager = HubSpotManager(settings.HUBSPOT_API_KEY)
    logfire.info("HubSpotManager initialized.")

    # Trigger initial Bland pathway sync (non-blocking)
    if app.state.bland_manager and mongo_service_instance:
      # Pass mongo_service_instance and None for background_tasks
      # Update attributes on the manager instance first
      app.state.bland_manager.mongo_service = mongo_service_instance
      # Startup tasks can log synchronously
      app.state.bland_manager.background_tasks = None
      asyncio.create_task(
          app.state.bland_manager._sync_bland()  # Call without arguments
      )
      logfire.info("Bland pathway sync task scheduled.")
    elif not mongo_service_instance:
      logfire.error(
          "Mongo service not available, skipping Bland pathway sync.")
    else:
      logfire.warning(
          "Bland manager not initialized, skipping pathway sync task."
      )

    # Initialize Service Status Monitor
    redis_service = await get_redis_service()
    if mongo_service_instance and redis_service and app.state.bland_manager:
      # Get the instance of the sheet sync service
      from app.services.quote.sync import _sheet_sync_service_instance

      logfire.info("Initializing service status monitor...")
      try:
        await initialize_service_monitor(
            mongo_service=mongo_service_instance,
            redis_service=redis_service,
            bland_ai_manager=app.state.bland_manager,
            sheet_sync_service=_sheet_sync_service_instance,
        )
        logfire.info("Service status monitor initialized successfully.")
      except Exception as monitor_err:
        logfire.error(
            f"Failed to initialize service status monitor: {str(monitor_err)}",
            exc_info=True,
        )
    else:
      logfire.warning(
          "Missing required services for status monitoring. Monitor will not be initialized."
      )

  except Exception as e:
    logfire.error(
        f"Critical error during application startup sequence: {e}", exc_info=True
    )
    # If mongo_service_instance is available, try to log this critical startup error
    if mongo_service_instance:
      try:
        await mongo_service_instance.log_error_to_db(
            service_name="ApplicationStartup",
            error_type="CriticalStartupError",
            message=f"Critical error during application startup: {str(e)}",
            details={"exception_type": type(e).__name__, "args": e.args},
        )
      except Exception as log_e:
        logfire.error(
            f"Failed to log critical startup error to DB: {log_e}",
            exc_info=True,
        )
    raise e

  logfire.info("Application startup sequence complete.")
  yield
  # Shutdown: Clean up connections, etc.
  logfire.info("Application shutdown: Cleaning up resources.")

  # Consolidate shutdown calls into a single try block
  try:
    logfire.debug("Attempting sheet_sync_shutdown...")
    await sheet_sync_shutdown()

    logfire.debug("Attempting close_n8n_client...")
    await close_n8n_client()

    logfire.debug("Attempting shutdown_mongo_service...")
    await shutdown_mongo_service()

    logfire.debug("Attempting shutdown_redis_service...")
    await shutdown_redis_service()  # Call redis shutdown

    # Close other services stored in app.state
    logfire.debug("Attempting bland_manager.close...")
    if hasattr(app.state, "bland_manager") and app.state.bland_manager:
      await app.state.bland_manager.close()

    logfire.debug("Attempting hubspot_manager.close...")
    if hasattr(app.state, "hubspot_manager") and app.state.hubspot_manager:
      await app.state.hubspot_manager.close()

    # Shutdown the service status monitor
    logfire.debug("Attempting service status monitor shutdown...")
    try:
      await shutdown_service_monitor()
      logfire.info("Service status monitor shutdown complete.")
    except Exception as monitor_err:
      logfire.error(
          f"Error shutting down service status monitor: {monitor_err}",
          exc_info=True,
      )

  except Exception as e:
    # Log any error that occurs during any shutdown step
    logfire.error(
        f"Error during application shutdown sequence: {e}", exc_info=True)
    # Continue shutdown despite errors in one part if possible

  logfire.info("Application shutdown complete.")


# --- FastAPI Application Initialization ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",  # Default Swagger UI
    redoc_url="/redoc",  # Default ReDoc
    lifespan=lifespan,
)

# --- Register Exception Handlers ---
app.add_exception_handler(
    HTTPException, http_exception_handler)  # type: ignore
app.add_exception_handler(Exception, generic_exception_handler)

# --- Add Middleware ---
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)
# --- End Middleware ---

# Mount the API router
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include the home router at the root
app.include_router(home.router)  # Added home router at root


# Root endpoint (optional)
@app.get("/", tags=["Root"])
async def read_root():
  return {"message": f"Welcome to {settings.PROJECT_NAME}"}
