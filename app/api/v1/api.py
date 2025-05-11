# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
from .endpoints import health, classify, hubspot, documentation
from .endpoints import bland_calls
from .endpoints import test_services
from .endpoints import error_logs # Added error_logs router
# Import individual webhook routers
from .endpoints.webhooks import form as webhooks_form
from .endpoints.webhooks import hubspot as webhooks_hubspot
from .endpoints.webhooks import voice as webhooks_voice
from .endpoints.webhooks import pricing as webhooks_pricing
# from .endpoints.webhooks import bland as webhooks_bland # Removed problematic import
# Import the new dashboard router
from .endpoints.dash import dashboard as dashboard_router
# Import auth router - Correctly import 'router' and alias it
from .endpoints.auth import router as auth_endpoints


# Create the main router for API v1
api_router_v1 = APIRouter()

# Include standard endpoint routers
api_router_v1.include_router(health.router, prefix="/health", tags=["Health"])
api_router_v1.include_router(classify.router, prefix="/classify", tags=["Classification"])
api_router_v1.include_router(hubspot.router, prefix="/hubspot", tags=["HubSpot"])
api_router_v1.include_router(documentation.router, tags=["Documentation"])

# Create a sub-router for all webhooks for better organization
webhook_router = APIRouter()
webhook_router.include_router(webhooks_form.router) # Path defined in form.router (e.g., /form)
webhook_router.include_router(webhooks_hubspot.router) # Path defined in hubspot.router
webhook_router.include_router(webhooks_voice.router)   # Path defined in voice.router
webhook_router.include_router(webhooks_pricing.router) # Paths /location_lookup and /quote are relative to this
# webhook_router.include_router(webhooks_bland.router, prefix="/bland") # Path defined in bland.router # Commented out as bland.py doesn't exist

# Include the webhook_router under /webhook prefix
api_router_v1.include_router(webhook_router, prefix="/webhook", tags=["Webhooks"])

# Include the dashboard router
api_router_v1.include_router(dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])

# Include auth router
api_router_v1.include_router(auth_endpoints, prefix="/auth", tags=["Authentication"])

# Include Bland AI calls router
api_router_v1.include_router(bland_calls.router, prefix="/bland-calls", tags=["Bland AI Calls"])

# Include Test Services router
api_router_v1.include_router(test_services.router, prefix="/test", tags=["Test Services"])

# Include Error Logs router
api_router_v1.include_router(error_logs.router, prefix="/error-logs", tags=["Error Logs"])
