"""
Utilities for background task management.

This module provides utility functions for managing background tasks and service instances
that require access to background task queues.
"""

from typing import Any, Optional, Callable
from fastapi.background import BackgroundTasks
from .safe import get_background_tasks, add_task_safely

__all__ = ["attach_background_tasks",
           "get_background_tasks", "add_task_safely"]


def attach_background_tasks(service_instance: Any, background_tasks: BackgroundTasks) -> None:
  """
  Attach background tasks to a service instance that supports them.

  This utility function checks if a service instance has a set_background_tasks method,
  and if so, attaches the provided background tasks object. It also handles 
  nested services that may have background task support.

  Args:
      service_instance: Any service instance that might support background tasks
      background_tasks: The BackgroundTasks instance from the FastAPI endpoint

  Example:
      ```python
      @router.get("/example")
      async def example_endpoint(
          background_tasks: BackgroundTasks,
          redis_service: InstrumentedRedisService = Depends(get_redis_service_dep),
          location_service: LocationService = Depends(get_location_service_dep)
      ):
          # Attach background tasks to the service(s)
          attach_background_tasks(redis_service, background_tasks)
          attach_background_tasks(location_service, background_tasks)

          # Now all services can use background tasks for latency recording, etc.
          result = await location_service.get_distance_to_nearest_branch("123 Main St")

          return {"result": result}
      ```
  """
  # Direct attachment if service has set_background_tasks method
  if hasattr(service_instance, 'set_background_tasks') and callable(getattr(service_instance, 'set_background_tasks')):
    service_instance.set_background_tasks(background_tasks)

  # For RedisService with background_tasks attribute
  if hasattr(service_instance, 'background_tasks') and service_instance.background_tasks is None:
    service_instance.background_tasks = background_tasks

  # Handle nested services with redis_service attribute
  if hasattr(service_instance, 'redis_service') and service_instance.redis_service is not None:
    attach_background_tasks(service_instance.redis_service, background_tasks)

  # Handle nested services like distance_calc, etc.
  for attr_name in ['distance_calc', 'cache_ops', 'google_ops', 'area_checker']:
    if hasattr(service_instance, attr_name):
      nested_service = getattr(service_instance, attr_name)
      if nested_service is not None:
        attach_background_tasks(nested_service, background_tasks)
