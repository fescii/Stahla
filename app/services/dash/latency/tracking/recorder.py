import logging
import time
from typing import Dict, Any, Optional, cast
from datetime import datetime, timezone

from app.services.redis.service import RedisService
from app.core.cachekeys import (
    QUOTE_LATENCY_SORTED_SET,
    LOCATION_LATENCY_SORTED_SET,
    GMAPS_LATENCY_SORTED_SET,
    REDIS_LATENCY_SORTED_SET,
    QUOTE_LATENCY_STREAM,
    LOCATION_LATENCY_STREAM,
    GMAPS_LATENCY_STREAM,
    REDIS_LATENCY_STREAM,
    QUOTE_LATENCY_SUM_KEY,
    QUOTE_LATENCY_COUNT_KEY,
    LOCATION_LATENCY_SUM_KEY,
    LOCATION_LATENCY_COUNT_KEY,
    GMAPS_LATENCY_SUM_KEY,
    GMAPS_LATENCY_COUNT_KEY,
    REDIS_LATENCY_SUM_KEY,
    REDIS_LATENCY_COUNT_KEY,
)

logger = logging.getLogger(__name__)


class LatencyRecorder:
  """Records latency data to Redis using Sorted Sets and Streams."""

  def __init__(self, redis_service: RedisService):
    self.redis = redis_service

    # Mapping of service types to their corresponding Redis keys
    self.sorted_set_keys = {
        "quote": QUOTE_LATENCY_SORTED_SET,
        "location": LOCATION_LATENCY_SORTED_SET,
        "gmaps": GMAPS_LATENCY_SORTED_SET,
        "redis": REDIS_LATENCY_SORTED_SET,
    }

    self.stream_keys = {
        "quote": QUOTE_LATENCY_STREAM,
        "location": LOCATION_LATENCY_STREAM,
        "gmaps": GMAPS_LATENCY_STREAM,
        "redis": REDIS_LATENCY_STREAM,
    }

    self.sum_keys = {
        "quote": QUOTE_LATENCY_SUM_KEY,
        "location": LOCATION_LATENCY_SUM_KEY,
        "gmaps": GMAPS_LATENCY_SUM_KEY,
        "redis": REDIS_LATENCY_SUM_KEY,
    }

    self.count_keys = {
        "quote": QUOTE_LATENCY_COUNT_KEY,
        "location": LOCATION_LATENCY_COUNT_KEY,
        "gmaps": GMAPS_LATENCY_COUNT_KEY,
        "redis": REDIS_LATENCY_COUNT_KEY,
    }

  async def record_latency(
      self,
      service_type: str,
      latency_ms: float,
      request_id: Optional[str] = None,
      endpoint: Optional[str] = None,
      context: Optional[Dict[str, Any]] = None
  ) -> bool:
    """
    Records latency data to Redis using multiple data structures:
    1. Sorted Set for percentile calculations
    2. Stream for detailed time-series data
    3. Counters for moving averages
    """
    try:
      if service_type not in self.sorted_set_keys:
        logger.warning(
            f"Unknown service type for latency tracking: {service_type}")
        return False

      timestamp = datetime.now(timezone.utc)
      timestamp_ms = int(timestamp.timestamp() * 1000)
      member_id = f"{timestamp_ms}:{request_id or 'unknown'}"

      redis_client = await self.redis.get_client()

      async with redis_client.pipeline(transaction=False) as pipe:
        # 1. Add to Sorted Set (for percentiles)
        pipe.zadd(
            self.sorted_set_keys[service_type],
            {member_id: latency_ms}
        )

        # 2. Add to Stream (for time-series analysis)
        stream_data: Dict[str, Any] = {
            "latency_ms": str(latency_ms),
            "request_id": request_id or "unknown",
            "endpoint": endpoint or "unknown",
            "timestamp": timestamp.isoformat(),
            "service_type": service_type,
        }

        # Add context data if provided
        if context:
          for key, value in context.items():
            stream_data[f"ctx_{key}"] = str(value)

        pipe.xadd(self.stream_keys[service_type], stream_data)  # type: ignore

        # 3. Update moving average counters
        pipe.incrbyfloat(self.sum_keys[service_type], latency_ms)
        pipe.incr(self.count_keys[service_type])

        # 4. Cleanup old data (keep last 10000 entries in sorted set)
        pipe.zremrangebyrank(self.sorted_set_keys[service_type], 0, -10001)

        # 5. Cleanup old stream data (keep last 24 hours approximately)
        # Calculate timestamp for 24 hours ago
        cutoff_timestamp = timestamp_ms - (24 * 60 * 60 * 1000)
        pipe.xtrim(
            self.stream_keys[service_type],
            minid=cutoff_timestamp,
            approximate=True
        )

        await pipe.execute()

      await redis_client.close()

      logger.debug(
          f"Recorded latency for {service_type}: {latency_ms}ms "
          f"(request_id: {request_id})"
      )
      return True

    except Exception as e:
      logger.error(
          f"Failed to record latency for {service_type}: {e}",
          exc_info=True
      )
      return False

  async def record_quote_latency(
      self,
      latency_ms: float,
      request_id: Optional[str] = None,
      quote_type: Optional[str] = None,
      location: Optional[str] = None
  ) -> bool:
    """Records latency specifically for quote operations."""
    context = {}
    if quote_type:
      context["quote_type"] = quote_type
    if location:
      context["location"] = location

    return await self.record_latency(
        "quote",
        latency_ms,
        request_id,
        "/webhook/pricing/quote",
        context
    )

  async def record_location_latency(
      self,
      latency_ms: float,
      request_id: Optional[str] = None,
      lookup_type: Optional[str] = None,
      address: Optional[str] = None
  ) -> bool:
    """Records latency specifically for location operations."""
    context = {}
    if lookup_type:
      context["lookup_type"] = lookup_type
    if address:
      context["address"] = address[:100]  # Truncate long addresses

    return await self.record_latency(
        "location",
        latency_ms,
        request_id,
        "/location/lookup",
        context
    )

  async def record_external_api_latency(
      self,
      service_type: str,
      latency_ms: float,
      request_id: Optional[str] = None,
      api_endpoint: Optional[str] = None,
      response_status: Optional[int] = None
  ) -> bool:
    """Records latency for external API calls (Quote, Location, Google Maps, Redis)."""
    context = {}
    if api_endpoint:
      context["api_endpoint"] = api_endpoint
    if response_status:
      context["response_status"] = str(response_status)

    return await self.record_latency(
        service_type,
        latency_ms,
        request_id,
        api_endpoint,
        context
    )
