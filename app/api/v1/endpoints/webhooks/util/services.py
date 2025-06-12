# app/api/v1/endpoints/webhooks/util/services.py

"""
Shared utilities for webhook service configuration.
Handles common patterns like background task attachment.
"""

from typing import Optional
from fastapi import BackgroundTasks
from app.services.location import LocationService
from app.services.redis.service import RedisService
from app.services.quote import QuoteService
from app.services.background.util import attach_background_tasks


def setup_webhook_services(
    background_tasks: BackgroundTasks,
    location_service: Optional[LocationService] = None,
    redis_service: Optional[RedisService] = None,
    quote_service: Optional[QuoteService] = None,
) -> None:
  """
  Attach background tasks to provided services.

  Args:
      background_tasks: FastAPI background tasks instance
      location_service: Optional location service to configure
      redis_service: Optional Redis service to configure  
      quote_service: Optional quote service to configure
  """
  services = [
      ("location", location_service),
      ("redis", redis_service),
      ("quote", quote_service)
  ]

  for service_name, service in services:
    if service is not None:
      attach_background_tasks(service, background_tasks)


def setup_location_services(
    background_tasks: BackgroundTasks,
    location_service: LocationService,
    redis_service: RedisService,
) -> None:
  """
  Quick setup for location-related webhook endpoints.

  Args:
      background_tasks: FastAPI background tasks instance
      location_service: Location service instance
      redis_service: Redis service instance
  """
  setup_webhook_services(
      background_tasks=background_tasks,
      location_service=location_service,
      redis_service=redis_service
  )


def setup_quote_services(
    background_tasks: BackgroundTasks,
    quote_service: QuoteService,
    redis_service: RedisService,
) -> None:
  """
  Quick setup for quote-related webhook endpoints.

  Args:
      background_tasks: FastAPI background tasks instance
      quote_service: Quote service instance
      redis_service: Redis service instance
  """
  setup_webhook_services(
      background_tasks=background_tasks,
      quote_service=quote_service,
      redis_service=redis_service
  )
