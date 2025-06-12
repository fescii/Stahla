"""
Utilities for attaching background tasks to services.
Used for consistent background task handling across the application.
"""

from fastapi import BackgroundTasks
from app.services.redis.instrumented import InstrumentedRedisService
from typing import Any


def attach_background_tasks(service: Any, background_tasks: BackgroundTasks) -> None:
    """
    Attach background tasks to a service instance.
    This function detects service types and attaches background tasks accordingly.

    Args:
        service: The service instance to attach background tasks to
        background_tasks: The BackgroundTasks instance from FastAPI
    """
    # Handle InstrumentedRedisService directly
    if isinstance(service, InstrumentedRedisService):
        service.background_tasks = background_tasks
        return

    # If service has a redis_service attribute, attach background tasks to it
    redis_service = getattr(service, "redis_service", None)
    if redis_service is not None and isinstance(redis_service, InstrumentedRedisService):
        redis_service.background_tasks = background_tasks
