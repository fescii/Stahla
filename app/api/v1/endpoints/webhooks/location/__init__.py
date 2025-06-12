# app/api/v1/endpoints/webhooks/location/__init__.py

"""
Location webhook endpoints.
"""

from .background import router as background_router
from .sync import router as sync_router

__all__ = ["background_router", "sync_router"]
