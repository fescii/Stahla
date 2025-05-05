# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
# These files need to be created in the endpoints directory
from .endpoints import health, classify, hubspot, documentation, pricing # Added pricing import
# Import individual webhook routers
from .endpoints.webhooks import form as webhooks_form
from .endpoints.webhooks import hubspot as webhooks_hubspot
from .endpoints.webhooks import voice as webhooks_voice
# Removed email webhook import
# Import the new dashboard router
from .endpoints.dash import dashboard as dashboard_router


# Create the main router for API v1
api_router_v1 = APIRouter()

# Include routers from endpoint files
# Each router will manage a specific set of related endpoints
api_router_v1.include_router(health.router, prefix="/health", tags=["Health"])
api_router_v1.include_router(classify.router, prefix="/classify", tags=["Classification"])
api_router_v1.include_router(hubspot.router, prefix="/hubspot", tags=["HubSpot"])
api_router_v1.include_router(documentation.router, tags=["Documentation"])
# Include individual webhook routers under the /webhook prefix
api_router_v1.include_router(
    webhooks_form.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(
    webhooks_hubspot.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(
    webhooks_voice.router, prefix="/webhook", tags=["Webhooks"])
# Include the pricing router
api_router_v1.include_router(pricing.router, prefix="/pricing", tags=["Pricing"])
# Include the dashboard router
api_router_v1.include_router(dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])
