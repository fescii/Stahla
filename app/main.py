# app/main.py

from fastapi import FastAPI, Request, HTTPException # Added Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse # Added HTMLResponse
from contextlib import asynccontextmanager
import markdown # Added markdown import
import asyncio # Import asyncio
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
from app.services.quote.sync import lifespan_startup as sheet_sync_startup # Update import path
from app.services.quote.sync import lifespan_shutdown as sheet_sync_shutdown # Update import path
# Import mongo and auth lifespan functions
from app.services.mongo.mongo import startup_mongo_service, shutdown_mongo_service 
from app.services.auth.auth import startup_auth_service 
from app.services.redis.redis import startup_redis_service, shutdown_redis_service
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
    
    try:
        # Initialize Redis
        await startup_redis_service()

        # Initialize MongoDB (connects, creates indexes)
        await startup_mongo_service() 
        # Note: startup_mongo_service logs its own errors but doesn't raise by default
        # We proceed, but subsequent services might fail if mongo connection failed.
        
        # Initialize Auth Service (creates initial user if needed)
        await startup_auth_service() 
        # Note: startup_auth_service logs its own errors and handles mongo failure gracefully.

        # Initialize Sheet Sync Service 
        await sheet_sync_startup() 
        logfire.info("Sheet Sync service startup initiated.")

        # Initialize other managers/services if needed
        app.state.bland_manager = bland_manager
        app.state.hubspot_manager = HubSpotManager(settings.HUBSPOT_API_KEY)
        app.state.email_manager = EmailManager()
        logfire.info("HubSpotManager and EmailManager initialized.")

        # Trigger initial Bland pathway sync (non-blocking)
        if hasattr(app.state, 'bland_manager') and app.state.bland_manager:
             asyncio.create_task(app.state.bland_manager._sync_pathway()) 
             logfire.info("Bland pathway sync task scheduled.")
        else:
             logfire.warning("Bland manager not initialized, skipping pathway sync task.")

    except Exception as e:
        # Catch any exception during the entire startup sequence
        logfire.error(f"Critical error during application startup sequence: {e}", exc_info=True)
        # Depending on the severity, you might want to raise the exception
        # here to prevent the application from starting in a broken state.
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
        await shutdown_redis_service() # Call redis shutdown

        # Close other services stored in app.state
        logfire.debug("Attempting bland_manager.close...")
        if hasattr(app.state, 'bland_manager') and app.state.bland_manager:
            await app.state.bland_manager.close()

        logfire.debug("Attempting hubspot_manager.close...")
        if hasattr(app.state, 'hubspot_manager') and app.state.hubspot_manager:
            await app.state.hubspot_manager.close()

        logfire.debug("Attempting email_manager.close...")
        if hasattr(app.state, 'email_manager') and app.state.email_manager:
            await app.state.email_manager.close()

    except Exception as e:
        # Log any error that occurs during any shutdown step
        logfire.error(f"Error during application shutdown sequence: {e}", exc_info=True)
        # Continue shutdown despite errors in one component if possible
        
    logfire.info("Application shutdown complete.")

# --- FastAPI Application Initialization ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs", # Default Swagger UI
    redoc_url="/redoc", # Default ReDoc
    lifespan=lifespan
)

# --- Add Middleware --- 
app.add_middleware(LoggingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
# --- End Middleware ---

# Mount the API router
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

# Root endpoint (optional)
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}