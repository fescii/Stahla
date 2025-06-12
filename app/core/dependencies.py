# app/core/dependencies.py
"""
DEPRECATED: This module has been reorganized for better maintainability.

All dependency functions have been moved to app.core.dependencies/ folder
for better organization and maintainability. This file now re-exports
all dependencies from the new structure for backward compatibility.

Please update your imports to use the new structure directly when possible.
"""

from app.core.dependencies.redis import get_redis_service_dep
from app.core.dependencies.mongo import get_mongo_service_dep
from app.core.dependencies.location import get_location_service_dep
from app.core.dependencies.dashboard import get_dashboard_service_dep
from app.core.dependencies.quote import get_quote_service_dep
from app.core.dependencies.bland import get_bland_manager_dep
from app.core.dependencies.auth import get_auth_service_dep

__all__ = [
    "get_redis_service_dep",
    "get_mongo_service_dep",
    "get_location_service_dep",
    "get_dashboard_service_dep",
    "get_quote_service_dep",
    "get_bland_manager_dep",
    "get_auth_service_dep",
]
