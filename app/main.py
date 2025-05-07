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
from app.services.mongo.mongo import mongo_service # Import mongo service instance
from app.services.n8n import close_n8n_client # Import the close function
from app.services.auth.auth import AuthService # Import AuthService
from app.models.user import UserCreate # Import UserCreate
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
    # Connect to Redis
    redis_service = await get_redis_service()
    # Connect to MongoDB
    try:
        await mongo_service.connect_to_mongo()

        # Create initial superuser if configured and doesn't exist
        if settings.FIRST_SUPERUSER_EMAIL and settings.FIRST_SUPERUSER_PASSWORD:
            auth_service = AuthService(mongo_service) # Create instance
            existing_user = await auth_service.get_user_by_email(settings.FIRST_SUPERUSER_EMAIL)
            if not existing_user:
                logfire.info(f"Creating initial superuser: {settings.FIRST_SUPERUSER_EMAIL}")
                user_in = UserCreate(
                    email=settings.FIRST_SUPERUSER_EMAIL,
                    password=settings.FIRST_SUPERUSER_PASSWORD,
                    role="admin", # Ensure role is admin
                    is_active=True,
                    name="Initial Admin" # Add a default name
                )
                await auth_service.create_user(user_in)
                logfire.info("Initial superuser created successfully.")
            else:
                logfire.info("Initial superuser already exists.")

    except Exception as e:
        logfire.critical(f"Failed to connect to MongoDB or create superuser during startup: {e}", exc_info=True)
        # Decide if app should proceed without MongoDB or raise error
        # For now, we log critical and continue, dashboard/auth features might fail

    # Initialize Sheet Sync Service (which depends on Redis)
    # This now runs service creation in executor and schedules initial sync
    await sheet_sync_startup(redis_service)

    # Initialize other managers/services if needed
    app.state.bland_manager = bland_manager
    app.state.hubspot_manager = HubSpotManager(settings.HUBSPOT_API_KEY)
    app.state.email_manager = EmailManager()
    logfire.info("HubSpotManager initialized.")
    logfire.info("EmailManager initialized.")

    # Trigger initial Bland pathway sync (non-blocking)
    # Ensure redis_service is available
    asyncio.create_task(sync_bland_pathway_on_startup(redis_service))

    logfire.info("Application startup sequence complete.")
    yield
    # Shutdown: Clean up connections, etc.
    logfire.info("Application shutdown: Cleaning up resources.")
    await sheet_sync_shutdown()
    await close_n8n_client()
    await mongo_service.close_mongo_connection() # Close mongo connection
    if redis_service:
        await redis_service.close()
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
