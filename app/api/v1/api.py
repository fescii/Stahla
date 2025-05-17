# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
from .endpoints import health, classify, hubspot, documentation  # Removed home
from .endpoints import bland  # Changed from bland_calls
from .endpoints import testing  # Changed from test_services
from .endpoints import errors  # Added error_logs router -> Changed from error_logs
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
api_router_v1.include_router(
    classify.router, prefix="/classify", tags=["Classification"])
api_router_v1.include_router(
    hubspot.router, prefix="/hubspot", tags=["HubSpot"])
api_router_v1.include_router(
    documentation.router, prefix="/docs", tags=["Documentation"])
api_router_v1.include_router(
    bland.router, prefix="/bland", tags=["Bland AI Calls"])
api_router_v1.include_router(testing.router, prefix="/test", tags=["Testing"])
api_router_v1.include_router(
    errors.router, prefix="/errors", tags=["Error Logs"])
# api_router_v1.include_router(home.router, tags=["Home"]) # Removed home router

# Create a sub-router for all webhooks for better organization
webhook_router = APIRouter()
# Path defined in form.router (e.g., /form)
webhook_router.include_router(webhooks_form.router)
# Path defined in hubspot.router
webhook_router.include_router(webhooks_hubspot.router)
# Path defined in voice.router
webhook_router.include_router(webhooks_voice.router)
# Paths /location_lookup and /quote are relative to this
webhook_router.include_router(webhooks_pricing.router)
# webhook_router.include_router(webhooks_bland.router, prefix="/bland") # Path defined in bland.router # Commented out as bland.py doesn't exist

# Include the webhook_router under /webhook prefix
api_router_v1.include_router(
    webhook_router, prefix="/webhook", tags=["Webhooks"])

# Include the dashboard router
api_router_v1.include_router(
    dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])

# Include auth router
api_router_v1.include_router(
    auth_endpoints, prefix="/auth", tags=["Authentication"])
