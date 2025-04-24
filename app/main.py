# app/main.py

from fastapi import FastAPI, Request, HTTPException # Added Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse # Added HTMLResponse
from contextlib import asynccontextmanager
import markdown # Added markdown import
# --- Project Structure Imports ---
# Import settings from core/config.py
# Use absolute imports now that WORKDIR is /code
from app.core.config import settings
# Correctly import the router from app.api.v1.api
from app.api.v1.api import api_router_v1
# Import service managers using the correct class names
from app.services.bland import BlandAIManager # Corrected class name
from app.services.hubspot import HubSpotManager
from app.services.email import EmailManager
import logfire
from dotenv import load_dotenv # Make sure python-dotenv is in requirements.txt

# --- Logfire Configuration ---
# Load environment variables (especially for LOGFIRE_TOKEN if set)
load_dotenv()

# Configure Logfire
# Make sure LOGFIRE_TOKEN is set in your environment or .env file
logfire_config = {
    "send_to_logfire": True, # Send logs to Logfire cloud
    "service_name": settings.PROJECT_NAME, # Use project name from settings
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
    # Instantiate managers using correct class name and store them in app state
    app.state.bland_manager = BlandAIManager(api_key=settings.BLAND_API_KEY, base_url=settings.BLAND_API_URL)
    # Provide the required api_key from settings
    app.state.hubspot_manager = HubSpotManager(api_key=settings.HUBSPOT_API_KEY)
    app.state.email_manager = EmailManager()
    # If managers needed async initialization, it would go here.
    yield
    # Shutdown: Clean up resources
    logfire.info("Application shutdown: Closing resources.")
    # Access managers from app state and close clients
    await app.state.bland_manager.close_client()
    await app.state.hubspot_manager.close_client()
    await app.state.email_manager.close_client()

# --- FastAPI Application Initialization ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs", # Default Swagger UI
    redoc_url="/redoc", # Default ReDoc
    lifespan=lifespan
)

# Mount the API router
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

# Root endpoint (optional)
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# Add other middleware if needed (e.g., CORS)
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Adjust in production!
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
