# app/core/dependencies.py

"""
Unified dependency injection module for the application.
All dependencies use InstrumentedRedisService by default for automatic latency monitoring.
"""

from fastapi import Request, HTTPException, status, Depends, BackgroundTasks
from typing import Optional

# Import Service Classes and their injectors
from app.services.mongo.dependency import MongoService, get_mongo_service
from app.services.auth.auth import AuthService, get_auth_service
from app.services.redis.instrumented import InstrumentedRedisService
from app.services.redis.factory import get_instrumented_redis_service
from app.services.location import LocationService
from app.services.bland import (
    bland_manager,
    BlandAIManager,
)  # Import the singleton instance and the class


# Core Redis Service Dependency (Instrumented by default)
async def get_redis_service_dep(
    background_tasks: BackgroundTasks
) -> InstrumentedRedisService:
    """
    Get instrumented Redis service with automatic latency tracking.
    This is the default Redis service for all application components.
    """
    return await get_instrumented_redis_service(background_tasks)


# Location Service Dependency
async def get_location_service_dep(
    background_tasks: BackgroundTasks,
    mongo_service: MongoService = Depends(get_mongo_service),
) -> LocationService:
    """
    Get LocationService with instrumented Redis for automatic latency monitoring.
    """
    redis_service = await get_instrumented_redis_service(background_tasks)
    return LocationService(redis_service, mongo_service)


# Dashboard Service Dependency
async def get_dashboard_service_dep(
    background_tasks: BackgroundTasks,
    mongo_service: MongoService = Depends(get_mongo_service),
):
    """
    Get DashboardService with instrumented Redis for automatic latency monitoring.
    """
    # Import here to avoid circular dependency
    from app.services.dash import DashboardService
    
    redis_service = await get_instrumented_redis_service(background_tasks)
    return DashboardService(redis_service=redis_service, mongo_service=mongo_service)


# Quote Service Dependency
async def get_quote_service_dep(
    background_tasks: BackgroundTasks,
    mongo_service: MongoService = Depends(get_mongo_service),
):
    """
    Get QuoteService with instrumented Redis for automatic latency monitoring.
    """
    from app.services.quote import QuoteService
    
    redis_service = await get_instrumented_redis_service(background_tasks)
    location_service = LocationService(redis_service, mongo_service)
    
    return QuoteService(
        redis_service=redis_service,
        location_service=location_service,
        mongo_service=mongo_service,
    )


# BlandAI Manager Dependency (Singleton)
def get_bland_manager_dep() -> BlandAIManager:
    """
    Get the BlandAI manager singleton instance.
    """
    return bland_manager


# Auth Service Dependency
def get_auth_service_dep(
    mongo_service: MongoService = Depends(get_mongo_service)
) -> AuthService:
    """
    Get AuthService instance.
    """
    return AuthService(mongo_service)


# Mongo Service Dependency (Re-export for convenience)
async def get_mongo_service_dep() -> MongoService:
    """
    Get MongoService instance.
    """
    return await get_mongo_service()


__all__ = [
    "get_redis_service_dep",
    "get_location_service_dep", 
    "get_dashboard_service_dep",
    "get_quote_service_dep",
    "get_bland_manager_dep",
    "get_auth_service_dep",
    "get_mongo_service_dep",
]
