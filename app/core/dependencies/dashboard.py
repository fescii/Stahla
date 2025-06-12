"""
Core dependency injection module for dashboard services.
"""

from fastapi import Depends
from app.services.mongo.dependency import MongoService, get_mongo_service
from app.core.dependencies.redis import get_redis_service_dep


async def get_dashboard_service_dep(
    mongo_service: MongoService = Depends(get_mongo_service),
):
  """
  Get DashboardService with instrumented Redis for automatic latency monitoring.
  Note: BackgroundTasks should be injected directly in endpoints that need them.
  """
  # Import here to avoid circular dependency
  from app.services.dash import DashboardService

  redis_service = await get_redis_service_dep()
  return DashboardService(redis_service=redis_service, mongo_service=mongo_service)
