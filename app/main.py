# app/main.py

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks # Added BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse 
from contextlib import asynccontextmanager
import markdown 
import asyncio 
# --- Project Structure Imports ---
from app.core.config import settings
from app.api.v1.api import api_router_v1
from app.services.bland import bland_manager # Removed sync_bland_pathway_on_startup import, will call method directly
from app.services.hubspot import HubSpotManager
from app.services.email import EmailManager
from app.services.quote.sync import lifespan_startup as sheet_sync_startup 
from app.services.quote.sync import lifespan_shutdown as sheet_sync_shutdown 
from app.services.mongo.mongo import startup_mongo_service, shutdown_mongo_service, get_mongo_service # Added get_mongo_service
from app.services.auth.auth import startup_auth_service 
from app.services.redis.redis import startup_redis_service, shutdown_redis_service
from app.services.n8n import close_n8n_client 
import logfire
from dotenv import load_dotenv 
from app.core.middleware import LoggingMiddleware 
from app.core.middleware import http_exception_handler, generic_exception_handler

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
    
    mongo_service_instance = None # Initialize to None
    try:
        # Initialize Redis
        await startup_redis_service()

        # Initialize MongoDB (connects, creates indexes)
        await startup_mongo_service() 
        # Get MongoService instance for other services that need it during startup
        mongo_service_instance = await get_mongo_service()
        
        # Initialize Auth Service (creates initial user if needed)
        # Pass mongo_service_instance if auth service needs it directly for startup logic
        await startup_auth_service(mongo_service=mongo_service_instance) # Assuming startup_auth_service can take it
        
        # Initialize Sheet Sync Service 
        # Pass mongo_service_instance if sheet_sync_startup needs it
        await sheet_sync_startup(mongo_service=mongo_service_instance) # Assuming sheet_sync_startup can take it
        logfire.info("Sheet Sync service startup initiated.")

        # Initialize other managers/services if needed
        app.state.bland_manager = bland_manager # bland_manager is already initialized globally
        app.state.hubspot_manager = HubSpotManager(settings.HUBSPOT_API_KEY)
        app.state.email_manager = EmailManager()
        logfire.info("HubSpotManager and EmailManager initialized.")

        # Trigger initial Bland pathway sync (non-blocking)
        if app.state.bland_manager and mongo_service_instance:
             # Pass mongo_service_instance and None for background_tasks
             asyncio.create_task(app.state.bland_manager._sync_pathway(
                 mongo_service=mongo_service_instance, 
                 background_tasks=None # Startup tasks can log synchronously
             )) 
             logfire.info("Bland pathway sync task scheduled.")
        elif not mongo_service_instance:
            logfire.error("Mongo service not available, skipping Bland pathway sync.")
        else:
             logfire.warning("Bland manager not initialized, skipping pathway sync task.")

    except Exception as e:
        logfire.error(f"Critical error during application startup sequence: {e}", exc_info=True)
        # If mongo_service_instance is available, try to log this critical startup error
        if mongo_service_instance:
            try:
                await mongo_service_instance.log_error_to_db(
                    service_name="ApplicationStartup",
                    error_type="CriticalStartupError",
                    message=f"Critical error during application startup: {str(e)}",
                    details={"exception_type": type(e).__name__, "args": e.args}
                )
            except Exception as log_e:
                logfire.error(f"Failed to log critical startup error to DB: {log_e}", exc_info=True)
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

# --- Register Exception Handlers ---
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

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