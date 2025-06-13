"""Background tasks for latency recording and tracking."""

import logging
from typing import Any, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


async def record_latency_bg(
    redis,
    service_type: str,
    latency_ms: float,
    request_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
):
  """Background task to record latency data using the comprehensive latency tracking system."""
  try:
    # Import at runtime to avoid circular imports
    from app.services.dash.latency import LatencyRecorder
    latency_recorder = LatencyRecorder(redis)
    success = await latency_recorder.record_latency(
        service_type=service_type,
        latency_ms=latency_ms,
        request_id=request_id,
        endpoint=endpoint,
        context=context
    )
    if not success:
      logger.warning(
          f"Failed to record {service_type} latency ({latency_ms}ms)")
  except Exception as e:
    logger.error(
        f"Error recording {service_type} latency: {str(e)}",
        exc_info=True
    )


async def record_quote_latency_bg(
    redis,
    latency_ms: float,
    request_id: Optional[str] = None,
    quote_type: Optional[str] = None,
    location: Optional[str] = None
):
  """Background task specifically for quote latency recording."""
  context = {}
  if quote_type:
    context["quote_type"] = quote_type
  if location:
    context["location"] = location[:100]  # Truncate long locations

  await record_latency_bg(
      redis=redis,
      service_type="quote",
      latency_ms=latency_ms,
      request_id=request_id,
      endpoint="quote_generation",
      context=context
  )


async def record_location_latency_bg(
    redis,
    latency_ms: float,
    request_id: Optional[str] = None,
    lookup_type: Optional[str] = None,
    address: Optional[str] = None
):
  """Background task specifically for location latency recording."""
  context = {}
  if lookup_type:
    context["lookup_type"] = lookup_type
  if address:
    context["address"] = address[:100]  # Truncate long addresses

  await record_latency_bg(
      redis=redis,
      service_type="location",
      latency_ms=latency_ms,
      request_id=request_id,
      endpoint="location_lookup",
      context=context
  )


async def record_external_api_latency_bg(
    redis,
    service_type: str,  # 'quote', 'location', 'gmaps', 'redis'
    latency_ms: float,
    request_id: Optional[str] = None,
    api_endpoint: Optional[str] = None,
    response_status: Optional[int] = None
):
  """Background task for external API latency recording."""
  context = {}
  if api_endpoint:
    context["api_endpoint"] = api_endpoint
  if response_status:
    context["response_status"] = str(response_status)

  await record_latency_bg(
      redis=redis,
      service_type=service_type,
      latency_ms=latency_ms,
      request_id=request_id,
      endpoint=api_endpoint,
      context=context
  )
