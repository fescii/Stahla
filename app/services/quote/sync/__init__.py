# app/services/quote/sync/__init__.py

"""
Exports for the sync module to maintain compatibility with existing imports.
"""

# Import constants from the new shared location - no circular dependency
from ..utils.constants import (
    PRICING_CATALOG_CACHE_KEY,
    BRANCH_LIST_CACHE_KEY,
    STATES_LIST_CACHE_KEY,
    SYNC_INTERVAL_SECONDS,
    PRODUCT_HEADER_MAP,
    GENERATOR_HEADER_MAP,
    KNOWN_PRODUCT_EXTRAS_HEADERS,
)

# For functions and classes, use lazy imports to avoid circular import


def __getattr__(name):
  if name in [
      "SheetSyncService",
      "lifespan_startup",
      "lifespan_shutdown",
      "get_sheet_sync_service",
      "set_sheet_sync_service",
      "_sheet_sync_service_instance",
      "_run_initial_sync_after_delay",
      "_run_priority_full_sync",
      "_clean_currency",
  ]:
    # Import from the new service module
    from .service import (
        SheetSyncService,
        lifespan_startup,
        lifespan_shutdown,
        get_sheet_sync_service,
        set_sheet_sync_service,
        _sheet_sync_service_instance,
        _run_initial_sync_after_delay,
        _run_priority_full_sync,
        _clean_currency,
    )
    # Return the requested attribute
    locals_dict = locals()
    if name in locals_dict:
      return locals_dict[name]
  raise AttributeError(
      f"module 'app.services.quote.sync' has no attribute '{name}'")


# Re-export constants and functions
__all__ = [
    "PRICING_CATALOG_CACHE_KEY",
    "BRANCH_LIST_CACHE_KEY",
    "STATES_LIST_CACHE_KEY",
    "SYNC_INTERVAL_SECONDS",
    "PRODUCT_HEADER_MAP",
    "GENERATOR_HEADER_MAP",
    "KNOWN_PRODUCT_EXTRAS_HEADERS",
    "SheetSyncService",
    "lifespan_startup",
    "lifespan_shutdown",
    "get_sheet_sync_service",
    "set_sheet_sync_service",
    "_sheet_sync_service_instance",
    "_run_initial_sync_after_delay",
    "_run_priority_full_sync",
    "_clean_currency",
]
