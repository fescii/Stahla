# app/api/v1/endpoints/hubspot/__init__.py

from fastapi import APIRouter

# Import all sub-routers
from .contacts import router as contacts_router
from .leads import router as leads_router
from .properties import router as properties_router
from .sync import router as sync_router
from .forms import router as forms_router
from .operations import router as operations_router

# Create the main hubspot router
router = APIRouter()

# Include all sub-routers
router.include_router(contacts_router, tags=["HubSpot Contacts"])
router.include_router(leads_router, tags=["HubSpot Leads"])
router.include_router(properties_router, tags=["HubSpot Properties"])
router.include_router(sync_router, tags=["HubSpot Sync"])
router.include_router(forms_router, tags=["HubSpot Forms"])
router.include_router(operations_router, tags=["HubSpot Operations"])

# Export for individual access if needed
__all__ = ["router", "contacts_router", "leads_router",
           "properties_router", "sync_router", "forms_router", "operations_router"]
