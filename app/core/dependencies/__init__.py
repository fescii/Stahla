"""
Unified dependency injection module for the application.

This module re-exports all dependency injectors from their respective submodules.
All dependencies use InstrumentedRedisService by default for automatic latency monitoring.
"""

from .redis import get_redis_service_dep
from .mongo import get_mongo_service_dep
from .location import get_location_service_dep
from .dashboard import get_dashboard_service_dep
from .quote import get_quote_service_dep
from .auth import get_auth_service_dep
from .bland import get_bland_manager_dep

__all__ = [
    "get_redis_service_dep",
    "get_mongo_service_dep",
    "get_location_service_dep",
    "get_dashboard_service_dep",
    "get_quote_service_dep",
    "get_auth_service_dep",
    "get_bland_manager_dep",
]
