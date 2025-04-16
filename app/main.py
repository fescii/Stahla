# app/main.py

import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
import logfire # Import logfire
from contextlib import asynccontextmanager # Import for lifespan management

# --- Project Structure Imports ---
# Import the main API router from api/v1/api.py
from app.api.v1.api import api_router_v1
# Import settings from core/config.py
from app.core.config import settings
# Import service managers needed for lifespan events (e.g., closing clients)
from app.services.bland import bland_manager

# --- Logfire Configuration ---
# Load environment variables (especially for LOGFIRE_TOKEN if set)
load_dotenv()

# Configure Logfire
# Make sure LOGFIRE_TOKEN is set in your environment or .env file
logfire.configure(
    send_to_logfire=True, # Send logs to Logfire cloud
    service_name=settings.PROJECT_NAME, # Use project name from settings
    # pydantic_plugin=logfire.PydanticPlugin(patch_models=True), # Optional: Auto-instrument Pydantic models
    # fastapi_instrumentation=True # Automatically instrument FastAPI
)
# If using auto-instrumentation, ensure it's configured before creating FastAPI instance

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    Used here to gracefully close HTTP clients.
    """
    # Startup actions (if any needed beyond global initializations)
    logfire.info(f"Application startup: {settings.PROJECT_NAME} - v{app.version}")
    yield
    # Shutdown actions
    logfire.info("Application shutdown initiated.")
    await bland_manager.close_client() # Close the BlandAI HTTP client
    # Add other cleanup actions here if needed (e.g., closing DB connections)
    logfire.info("Application shutdown complete.")


# --- FastAPI Application Initialization ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for automating lead intake, classification, and HubSpot integration.",
    version="1.0.0", # Consider making version dynamic or part of settings
    lifespan=lifespan, # Register the lifespan context manager
    # You can configure the docs URL based on settings if needed
    # openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- Logfire Middleware (if not using auto-instrumentation) ---
# If fastapi_instrumentation=False or you need custom middleware logic
# @app.middleware("http")
# async def logfire_middleware(request: Request, call_next):
#     # You can add custom spans or logging here if needed
#     response = await call_next(request)
#     return response

# --- Exception Handlers ---
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles request validation errors for cleaner responses."""
    # Log the detailed validation error
    logfire.error(f"Request Validation Error: {exc.errors()}", url=str(request.url), method=request.method, errors=exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handles unexpected server errors."""
    # Log the generic exception
    logfire.error(f"Unhandled Exception: {type(exc).__name__}: {exc}", url=str(request.url), method=request.method, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )

# --- API Routers ---
# Include the API router for version 1
# All routes defined in api_router_v1 will be prefixed with /api/v1
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

# --- Root Endpoint (Optional) ---
@app.get("/", summary="Root endpoint", tags=["General"])
async def read_root():
    """Provides a simple response for the root path."""
    logfire.info("Root endpoint accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

# --- Removed Placeholder Endpoints ---
# The old placeholder endpoints (@app.post('/api/v1/webhook/form', etc.))
# have been removed as they are now handled by the routers in app/api/v1/endpoints/.

# --- Run Instruction (for local debugging without uvicorn command) ---
# if __name__ == "__main__":
#     import uvicorn
#     # Note: Lifespan events might not trigger correctly when running this way
#     # compared to running directly with `uvicorn app.main:app` command.
#     uvicorn.run(app, host="0.0.0.0", port=8000)

"""
**Summary of Changes:**

* Added the `lifespan` context manager using `@asynccontextmanager`.
* Imported `bland_manager` to call `close_client()` during shutdown within the `lifespan` manager.
* Registered the `lifespan` manager with the `FastAPI` application instance.
* Uncommented the import for `settings` from `app.core.config`.
* Used `settings.PROJECT_NAME` for Logfire configuration and the root endpoint message.
* Used `settings.API_V1_STR` for the API router prefix.
* Removed the large block of commented-out placeholder endpoints previously defined directly in `main.py`.
* Improved logging in exception handlers to include URL and meth
"""