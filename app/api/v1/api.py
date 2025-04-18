# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
# These files need to be created in the endpoints directory
from .endpoints import health, classify, hubspot  # Removed webhooks import
# Import individual webhook routers
from .endpoints.webhooks import form as webhooks_form
from .endpoints.webhooks import hubspot as webhooks_hubspot
from .endpoints.webhooks import voice as webhooks_voice
from .endpoints.webhooks import email as webhooks_email


# Create the main router for API v1
api_router_v1 = APIRouter()

# Include routers from endpoint files
# Each router will manage a specific set of related endpoints
api_router_v1.include_router(health.router, prefix="/health", tags=["Health"])
# Include individual webhook routers under the /webhook prefix
api_router_v1.include_router(
    webhooks_form.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(
    webhooks_hubspot.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(
    webhooks_voice.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(
    webhooks_email.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(
    classify.router, prefix="/classify", tags=["Classification"])
api_router_v1.include_router(
    hubspot.router, prefix="/hubspot", tags=["HubSpot"])
