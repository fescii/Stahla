\
# filepath: app/core/dependencies.py
from fastapi import Request, HTTPException, status, Depends # Keep Depends
from typing import Optional

# Import Service Classes and their *actual* injectors
from app.services.mongo.mongo import MongoService, get_mongo_service 
from app.services.auth.auth import AuthService, get_auth_service 
from app.services.redis.redis import RedisService, get_redis_service 
from app.services.dash.dashboard import DashboardService # Import DashboardService class
from app.services.location.location import LocationService # Import LocationService class

# Dependency to get the LocationService instance
# This service needs its own dependencies injected
def get_location_service_dep(
    redis_service: RedisService = Depends(get_redis_service) # Use direct injector
) -> LocationService:
    # Instantiate LocationService with its dependencies
    return LocationService(redis_service)

# Dependency to get the DashboardService instance
# This service needs its own dependencies injected
def get_dashboard_service_dep(
    redis_service: RedisService = Depends(get_redis_service), # Use direct injector
    mongo_service: MongoService = Depends(get_mongo_service)  # Use direct injector
) -> DashboardService:
    # Instantiate DashboardService with its dependencies
    return DashboardService(redis_service=redis_service, mongo_service=mongo_service)

# Dependency to get the QuoteService instance
# This injector is defined in quote.py itself to avoid circular imports
# from app.services.quote.quote import get_quote_service # Example if it were here
