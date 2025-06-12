# app/api/v1/endpoints/webhooks/pricing.py

"""
Main pricing webhooks router.
Aggregates all pricing-related webhook endpoints from modular sub-routers.

Available endpoints:
- POST /location/sync - Synchronous location distance calculation
- POST /location/async - Asynchronous location distance prefetching  
- POST /quote/ - Quote generation and pricing calculation

All endpoints require API key authentication and return structured responses.
"""

from fastapi import APIRouter

# Import sub-routers from modular webhook directories
from .location.sync import router as location_sync_router
from .location.background import router as location_async_router
from .quote.generator import router as quote_router

# Create main pricing router
router = APIRouter()

# Include location webhooks with proper documentation
router.include_router(
    location_sync_router,
    prefix="/location/lookup",
    tags=["Location Webhooks"],
    dependencies=[]
)

router.include_router(
    location_async_router,
    prefix="/location/lookup",
    tags=["Location Webhooks"],
    dependencies=[]
)

# Include quote webhooks with proper documentation
router.include_router(
    quote_router,
    prefix="/quote",
    tags=["Quote Webhooks"],
    dependencies=[]
)
