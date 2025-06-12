# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
from .endpoints import health, classify, hubspot, documentation  # Removed home
from .endpoints import bland  # Changed from bland_calls
from .endpoints import testing  # Changed from test_services
from .endpoints import errors  # Added error_logs router -> Changed from error_logs
# Import main webhook router that aggregates all sub-routers
from .endpoints.webhooks import router as webhooks_router
# Import the new dashboard router
from .endpoints.dash import dashboard as dashboard_router
# Import the separate latency router
from .endpoints import latency as latency_router
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

# Include the webhooks router (already prefixed with /webhook)
api_router_v1.include_router(
    webhooks_router, tags=["Webhooks"])

# Include the dashboard router
api_router_v1.include_router(
    dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])

# Include the latency router separately
api_router_v1.include_router(
    latency_router.router, prefix="/latency", tags=["Latency"])

# Include auth router
api_router_v1.include_router(
    auth_endpoints, prefix="/auth", tags=["Authentication"])
