# app/api/v1/api.py

from fastapi import APIRouter

# Import endpoint routers
# These files need to be created in the endpoints directory
from .endpoints import health, webhooks, classify, hubspot

# Create the main router for API v1
api_router_v1 = APIRouter()

# Include routers from endpoint files
# Each router will manage a specific set of related endpoints
api_router_v1.include_router(health.router, prefix="/health", tags=["Health"])
api_router_v1.include_router(webhooks.router, prefix="/webhook", tags=["Webhooks"])
api_router_v1.include_router(classify.router, prefix="/classify", tags=["Classification"])
api_router_v1.include_router(hubspot.router, prefix="/hubspot", tags=["HubSpot"])
