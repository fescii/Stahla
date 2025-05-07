# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
from .endpoints import health, classify, hubspot, documentation
# Import individual webhook routers
from .endpoints.webhooks import form as webhooks_form
from .endpoints.webhooks import hubspot as webhooks_hubspot
from .endpoints.webhooks import voice as webhooks_voice
from .endpoints.webhooks import pricing as webhooks_pricing
# Import the new dashboard router
from .endpoints.dash import dashboard as dashboard_router


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

# Include the webhook_router under /webhook prefix
api_router_v1.include_router(webhook_router, prefix="/webhook", tags=["Webhooks"])

# Include the dashboard router
api_router_v1.include_router(dashboard_router.router, prefix="/dashboard", tags=["Dashboard"])
