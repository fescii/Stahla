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
# Ensure the sync function and manager are imported
from app.services.bland import bland_manager, sync_bland_pathway_on_startup
from app.services.hubspot import HubSpotManager
from app.services.email import EmailManager
from app.services.redis.redis import RedisService, get_redis_service # Update import path
from app.services.quote.sync import lifespan_startup as sheet_sync_startup # Update import path
from app.services.quote.sync import lifespan_shutdown as sheet_sync_shutdown # Update import path
from app.services.n8n import close_n8n_client # Import the close function
import logfire
from dotenv import load_dotenv # Make sure python-dotenv is in requirements.txt
from app.core.middleware import LoggingMiddleware # Import the middleware

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
    # Use the singleton instance directly
    app.state.bland_manager = bland_manager
    # Provide the required api_key from settings
    app.state.hubspot_manager = HubSpotManager(api_key=settings.HUBSPOT_API_KEY)
    app.state.email_manager = EmailManager()

    # Initialize Redis pool
    try:
        await RedisService.get_pool()
        logfire.info("Redis connection pool initialized.")
        # Initialize and start Sheet Sync Service
        redis_service_instance = await get_redis_service() # Uses updated import
        await sheet_sync_startup(redis_service_instance) # Uses updated import
    except Exception as e:
        logfire.exception("Error during startup initialization (Redis or Sheet Sync)", exc_info=e)
        # Consider raising the exception if Redis/Sync is critical
        # raise

    # Call the sync function during startup (Re-added)
    await sync_bland_pathway_on_startup()

    yield
    # Shutdown: Clean up resources
    logfire.info("Application shutdown: Closing resources.")
    # Access managers from app state and close clients
    await app.state.bland_manager.close_client()
    await app.state.hubspot_manager.close_client()
    await app.state.email_manager.close_client()
    await close_n8n_client() # Add call to close n8n client
    await sheet_sync_shutdown() # Uses updated import
    await RedisService.close_pool()
    logfire.info("Redis connection pool closed.")

# --- FastAPI Application Initialization ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs", # Default Swagger UI
    redoc_url="/redoc", # Default ReDoc
    lifespan=lifespan
)

# --- Add Middleware --- 
# IMPORTANT: Add middleware BEFORE routes are included
app.add_middleware(LoggingMiddleware)
# Add other middleware like CORS if needed AFTER logging middleware
# from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(CORSMiddleware, ...)
# --- End Middleware --- 

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
