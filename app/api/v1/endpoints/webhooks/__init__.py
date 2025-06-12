# app/api/v1/endpoints/webhooks/__init__.py

from fastapi import APIRouter

from .form import router as form_router
from .voice import router as voice_router
from .hubspot import router as hubspot_router

# Import location and quote routers
from .location.sync import router as location_sync_router
from .location.background import router as location_background_router
from .quote.generator import router as quote_router

# Import the main pricing router
from .pricing import router as pricing_router

# Create a main router for all webhooks
router = APIRouter(prefix="/webhook")

# Include all webhook subrouters
router.include_router(form_router)
router.include_router(voice_router)
router.include_router(hubspot_router)
# Include location routers
router.include_router(location_sync_router)
router.include_router(location_background_router)
# Include quote router
router.include_router(quote_router)
router.include_router(pricing_router)

# Export the router
__all__ = ["router"]
