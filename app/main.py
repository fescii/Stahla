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
from app.services.hubspot import hubspot_manager # Import HubSpot manager
from app.services.email import email_manager # Import Email manager

# --- Logfire Configuration ---
# Load environment variables (especially for LOGFIRE_TOKEN if set)
load_dotenv()

# Configure Logfire
# Make sure LOGFIRE_TOKEN is set in your environment or .env file
logfire_config = {
    "send_to_logfire": True, # Send logs to Logfire cloud
    "service_name": settings.PROJECT_NAME, # Use project name from settings
    # "pydantic_plugin": logfire.PydanticPlugin(), # Removed deprecated argument
    # "fastapi_instrumentation": True
}

# Only set console=False if DEV is False, otherwise rely on the default (True)
if not settings.DEV:
    logfire_config["console"] = False

logfire.configure(**logfire_config)
logfire.instrument_pydantic() # Instrument Pydantic models

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize connections, load models, etc.
    logfire.info("Application startup: Initializing resources.")
    # No explicit startup needed for managers using httpx.AsyncClient currently,
    # as the client is initialized in their __init__ method.
    # If they needed async initialization, it would go here.
    yield
    # Shutdown: Clean up resources
    logfire.info("Application shutdown: Closing resources.")
    await bland_manager.close_client()
    await hubspot_manager.close_client()
    await email_manager.close_client() # Add closing for email_manager

# --- FastAPI Application Initialization ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for automating lead intake, classification, and HubSpot integration.",
    version="1.0.0", # Consider making version dynamic or part of settings
    lifespan=lifespan, # Register the lifespan context manager
    # You can configure the docs URL based on settings if needed
    # openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- Exception Handlers ---
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """ Catch-all exception handler for unexpected errors."""
    logfire.error(f"Unhandled exception: {exc}", exc_info=True, path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )

# --- Middleware (Optional) ---
# Example: Add CORS middleware if needed
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[\"*\"], # Adjust in production!
#     allow_credentials=True,
#     allow_methods=[\"*\"],
#     allow_headers=[\"*\"],
# )

# --- API Routers ---
# Include the API router
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

# --- Root Endpoint ---
@app.get("/", summary="Root endpoint", tags=["General"])
async def read_root():
    """Provides a simple response for the root path."""
    logfire.info("Root endpoint accessed.")
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

# --- Run Instruction (for local debugging without uvicorn command) ---
# if __name__ == "__main__":
#     import uvicorn
#     # Note: Lifespan events might not trigger correctly when running this way
#     # compared to running directly with `uvicorn app.main:app` command.
#     uvicorn.run(app, host="0.0.0.0", port=8000)
