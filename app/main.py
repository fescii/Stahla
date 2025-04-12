# app/main.py

import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv
import logfire # Import logfire

# --- Project Structure Imports ---
# Assuming the structure outlined previously.
# These imports will work once the files/directories are created.
# from app.api.v1.api import api_router_v1
# from app.core.config import settings # Example: Load settings if needed

# --- Logfire Configuration ---
# Load environment variables (especially for LOGFIRE_TOKEN if set)
load_dotenv()

# Configure Logfire
# Make sure LOGFIRE_TOKEN is set in your environment or .env file
# You might want to configure service_name, etc. based on your environment
logfire.configure(
    send_to_logfire=True, # Send logs to Logfire cloud
    # pydantic_plugin=logfire.PydanticPlugin(patch_models=True), # Optional: Auto-instrument Pydantic models
    # fastapi_instrumentation=True # Automatically instrument FastAPI
)

# --- FastAPI Application Initialization ---
app = FastAPI(
    title="Stahla AI SDR",
    description="API for automating lead intake, classification, and HubSpot integration.",
    version="1.0.0",
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
    logfire.error(f"Request Validation Error: {exc.errors()}", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handles unexpected server errors."""
    # Log the generic exception
    logfire.error(f"Unhandled Exception: {exc}", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )

# --- API Routers ---
# Include the API router(s) - Uncomment and adjust once api.py is created
# from app.api.v1.api import api_router_v1 # Example import
# app.include_router(api_router_v1, prefix="/api/v1")

# --- Root Endpoint (Optional) ---
@app.get("/", summary="Root endpoint", tags=["General"])
async def read_root():
    """Provides a simple response for the root path."""
    logfire.info("Root endpoint accessed.")
    return {"message": "Welcome to the Stahla AI SDR API"}

# --- Placeholder Endpoints (Illustrative - Move to api/v1/endpoints/) ---
# These are placeholders based on the documentation.
# They should be moved to their respective files (e.g., webhooks.py, health.py)
# and implemented using APIRouter.

# @app.post("/api/v1/webhook/form", summary="Receive form submissions", tags=["Webhooks"])
# async def webhook_form(payload: dict): # Replace dict with Pydantic model
#     logfire.info("Received form webhook", data=payload)
#     # Add processing logic here...
#     return {"status": "received", "source": "form"}

# @app.post("/api/v1/webhook/voice", summary="Receive voice transcripts", tags=["Webhooks"])
# async def webhook_voice(payload: dict): # Replace dict with Pydantic model
#     logfire.info("Received voice webhook", data=payload)
#     # Add processing logic here...
#     return {"status": "received", "source": "voice"}

# @app.post("/api/v1/webhook/email", summary="Process incoming emails", tags=["Webhooks"])
# async def webhook_email(payload: dict): # Replace dict with Pydantic model
#     logfire.info("Received email webhook", data=payload)
#     # Add processing logic here...
#     return {"status": "received", "source": "email"}

# @app.post("/api/v1/classify", summary="Classify lead data", tags=["Internal"])
# async def classify_lead(data: dict): # Replace dict with Pydantic model
#     logfire.info("Received classification request", data=data)
#     # Add classification logic here...
#     return {"status": "classified", "result": "example_classification"}

# @app.post("/api/v1/hubspot/contact", summary="Create/update HubSpot contact", tags=["Internal"])
# async def hubspot_contact(contact_data: dict): # Replace dict with Pydantic model
#     logfire.info("Received HubSpot contact request", data=contact_data)
#     # Add HubSpot contact logic here...
#     return {"status": "processed", "entity": "contact"}

# @app.post("/api/v1/hubspot/deal", summary="Create/update HubSpot deal", tags=["Internal"])
# async def hubspot_deal(deal_data: dict): # Replace dict with Pydantic model
#     logfire.info("Received HubSpot deal request", data=deal_data)
#     # Add HubSpot deal logic here...
#     return {"status": "processed", "entity": "deal"}

# @app.get("/api/v1/health", summary="System health check", tags=["Internal"])
# async def health_check():
#     logfire.info("Health check performed.")
#     # Add checks for a database, external services etc.
#     return {"status": "ok"}

# --- Run Instruction (for local debugging without uvicorn command) ---
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)

# **Note:** Remember to create the referenced directories and files (`api/v1/api.py`, etc.) and move the placeholder endpoint logic into the appropriate endpoint files using `APIRouter`. You'll also need to define Pydantic models for request/response bodi