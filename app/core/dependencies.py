# filepath: app/core/dependencies.py
from fastapi import Request, HTTPException, status, Depends  # Keep Depends
from typing import Optional

# Import Service Classes and their *actual* injectors
from app.services.mongo.mongo import MongoService, get_mongo_service
from app.services.auth.auth import AuthService, get_auth_service
from app.services.redis.redis import RedisService, get_redis_service
from app.services.dash.dashboard import (
    DashboardService,
)  # Import DashboardService class
from app.services.location.location import (
    LocationService,
)  # Import LocationService class
from app.services.bland import (
    bland_manager,
    BlandAIManager,
)  # Import the singleton instance and the class


# Dependency to get the LocationService instance
# This service needs its own dependencies injected
def get_location_service_dep(
    redis_service: RedisService = Depends(get_redis_service),  # Use direct injector
    mongo_service: MongoService = Depends(
        get_mongo_service
    ),  # Add mongo_service dependency
) -> LocationService:
    # Instantiate LocationService with its dependencies
    return LocationService(redis_service, mongo_service)


# Dependency to get the DashboardService instance
# This service needs its own dependencies injected
def get_dashboard_service_dep(
    redis_service: RedisService = Depends(get_redis_service),  # Use direct injector
    mongo_service: MongoService = Depends(get_mongo_service),  # Use direct injector
    # Removed sync_service from here, it's internal to DashboardService now
) -> DashboardService:
    # Instantiate DashboardService with its dependencies
    # sync_service will be initialized within DashboardService if needed
    return DashboardService(redis_service=redis_service, mongo_service=mongo_service)


# Dependency to get the BlandAIManager instance (the singleton)
def get_bland_manager_dep() -> BlandAIManager:
    return bland_manager


# Dependency to get the QuoteService instance
# This injector is defined in quote.py itself to avoid circular imports
# from app.services.quote.quote import get_quote_service # Example if it were here
