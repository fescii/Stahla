# filepath: app/services/mongo/mongo.py
"""
MongoDB service - Backward compatibility module.

This module maintains backward compatibility with the original mongo.py interface
while using the new refactored structure underneath.
"""

# Import everything from the refactored modules for backward compatibility
from . import lifecycle
from .service import MongoService
from .lifecycle import startup_mongo_service, shutdown_mongo_service, get_mongo_service
from .collections.names import *

# Global instance variable for backward compatibility
mongo_service_instance = None

# Re-export all the functions and classes that were in the original mongo.py
__all__ = [
    "MongoService",
    "startup_mongo_service",
    "shutdown_mongo_service",
    "get_mongo_service",
    "mongo_service_instance",
    # Collection names
    "REPORTS_COLLECTION",
    "USERS_COLLECTION",
    "SHEET_PRODUCTS_COLLECTION",
    "SHEET_GENERATORS_COLLECTION",
    "SHEET_BRANCHES_COLLECTION",
    "SHEET_CONFIG_COLLECTION",
    "SHEET_STATES_COLLECTION",
    "BLAND_CALL_LOGS_COLLECTION",
    "ERROR_LOGS_COLLECTION",
    "STATS_COLLECTION",
    "SERVICE_STATUS_COLLECTION",
]

# Update the global instance reference to point to the lifecycle module
lifecycle.mongo_service_instance = mongo_service_instance
