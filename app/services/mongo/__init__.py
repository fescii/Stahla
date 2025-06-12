# filepath: app/services/mongo/__init__.py
"""
MongoDB service module - reorganized for better maintainability.

This module provides MongoDB operations organized into focused submodules:
- connection: Database connection and index management
- stats: Dashboard statistics operations
- reports: Report logging and retrieval
- bland: Bland AI call log operations
- errors: Error logging operations
- sheets: Google Sheets synchronization operations
"""

# Main service class and lifecycle management
from .service import MongoService
from .lifecycle import startup_mongo_service, shutdown_mongo_service, get_mongo_service

# Collection names for backward compatibility
from .collections.names import *

# Re-export the main classes for backward compatibility
__all__ = [
    "MongoService",
    "startup_mongo_service",
    "shutdown_mongo_service",
    "get_mongo_service",
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
