# app/api/v1/endpoints/webhooks/quote/__init__.py

"""
Quote webhook endpoints.
"""

from .generator import router as generator_router

__all__ = ["generator_router"]
