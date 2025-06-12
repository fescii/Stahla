import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta

from app.services.redis.redis import RedisService
from app.core.cachekeys import (
    QUOTE_LATENCY_STREAM,
    LOCATION_LATENCY_STREAM,
    HUBSPOT_LATENCY_STREAM,
    BLAND_LATENCY_STREAM,
    GMAPS_LATENCY_STREAM,
)

logger = logging.getLogger(__name__)


class LatencyAnalyzer:
  """Performs advanced latency analysis using Redis Streams."""

  def __init__(self, redis_service: RedisService):
    self.redis = redis_service

    self.stream_keys = {
        "quote": QUOTE_LATENCY_STREAM,
        "location": LOCATION_LATENCY_STREAM,
        "hubspot": HUBSPOT_LATENCY_STREAM,
        "bland": BLAND_LATENCY_STREAM,
        "gmaps": GMAPS_LATENCY_STREAM,
    }

  async def get_recent_latency_trend(
      self,
      service_type: str,
      minutes: int = 60
  ) -> Dict[str, Any]:
    """
    Analyze latency trends over the recent time period using Redis Streams.
    """
    try:
      if service_type not in self.stream_keys:
        logger.warning(
            f"Unknown service type for trend analysis: {service_type}")
        return {}

      stream_key = self.stream_keys[service_type]

      # Calculate time range (Redis stream IDs are timestamp-based)
      end_time = datetime.now(timezone.utc)
      start_time = end_time - timedelta(minutes=minutes)

      # Convert to Redis stream ID format (milliseconds since epoch)
      start_id = str(int(start_time.timestamp() * 1000))
      end_id = str(int(end_time.timestamp() * 1000))

      redis_client = await self.redis.get_client()

      try:
        # Read from stream within time range
        stream_data = await redis_client.xrange(
            stream_key,
            min=start_id,
            max=end_id,
            count=1000  # Limit to prevent excessive memory usage
        )

        if not stream_data:
          return {
              "service_type": service_type,
              "time_range_minutes": minutes,
              "sample_count": 0,
              "trend": "no_data",
              "message": "No latency data in the specified time range"
          }

        # Extract latency values and timestamps
        latencies = []
        timestamps = []
        endpoints = {}

        for stream_id, fields in stream_data:
          try:
            latency_ms = float(fields.get(b'latency_ms', 0))
            latencies.append(latency_ms)

            # Parse timestamp from stream ID or field
            timestamp_ms = int(stream_id.decode().split('-')[0])
            timestamps.append(timestamp_ms)

            # Track endpoint distribution
            endpoint = fields.get(b'endpoint', b'unknown').decode()
            endpoints[endpoint] = endpoints.get(endpoint, 0) + 1

          except (ValueError, KeyError) as e:
            logger.debug(f"Skipping malformed stream entry: {e}")
            continue

        if not latencies:
          return {
              "service_type": service_type,
              "time_range_minutes": minutes,
              "sample_count": 0,
              "trend": "no_valid_data",
              "message": "No valid latency data found"
          }

        # Calculate statistics
        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        # Simple trend analysis (compare first half vs second half)
        mid_point = len(latencies) // 2
        if mid_point > 0:
          first_half_avg = sum(latencies[:mid_point]) / mid_point
          second_half_avg = sum(
              latencies[mid_point:]) / (len(latencies) - mid_point)

          if second_half_avg > first_half_avg * 1.2:
            trend = "increasing"
          elif second_half_avg < first_half_avg * 0.8:
            trend = "decreasing"
          else:
            trend = "stable"
        else:
          trend = "insufficient_data"
          first_half_avg = avg_latency
          second_half_avg = avg_latency

        return {
            "service_type": service_type,
            "time_range_minutes": minutes,
            "sample_count": len(latencies),
            "statistics": {
                "average_ms": round(avg_latency, 2),
                "min_ms": round(min_latency, 2),
                "max_ms": round(max_latency, 2),
                "first_half_avg_ms": round(first_half_avg, 2),
                "second_half_avg_ms": round(second_half_avg, 2),
            },
            "trend": trend,
            "endpoint_distribution": endpoints,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

      finally:
        await redis_client.close()

    except Exception as e:
      logger.error(
          f"Failed to analyze latency trend for {service_type}: {e}", exc_info=True)
      return {
          "service_type": service_type,
          "error": str(e),
          "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
      }

  async def get_latency_spikes(
      self,
      service_type: str,
      threshold_multiplier: float = 3.0,
      minutes: int = 60
  ) -> List[Dict[str, Any]]:
    """
    Identify latency spikes that exceed the threshold multiplier of average latency.
    """
    try:
      if service_type not in self.stream_keys:
        logger.warning(
            f"Unknown service type for spike analysis: {service_type}")
        return []

      stream_key = self.stream_keys[service_type]

      # Get recent data
      end_time = datetime.now(timezone.utc)
      start_time = end_time - timedelta(minutes=minutes)
      start_id = str(int(start_time.timestamp() * 1000))
      end_id = str(int(end_time.timestamp() * 1000))

      redis_client = await self.redis.get_client()

      try:
        stream_data = await redis_client.xrange(
            stream_key,
            min=start_id,
            max=end_id,
            count=1000
        )

        if not stream_data:
          return []

        # First pass: calculate average latency
        latencies = []
        entries = []

        for stream_id, fields in stream_data:
          try:
            latency_ms = float(fields.get(b'latency_ms', 0))
            latencies.append(latency_ms)

            entry = {
                "stream_id": stream_id.decode(),
                "latency_ms": latency_ms,
                "request_id": fields.get(b'request_id', b'unknown').decode(),
                "endpoint": fields.get(b'endpoint', b'unknown').decode(),
                "timestamp": fields.get(b'timestamp', b'unknown').decode(),
            }

            # Add context fields
            for field_name, field_value in fields.items():
              field_name_str = field_name.decode()
              if field_name_str.startswith('ctx_'):
                entry[field_name_str] = field_value.decode()

            entries.append(entry)

          except (ValueError, KeyError) as e:
            logger.debug(f"Skipping malformed entry in spike analysis: {e}")
            continue

        if not latencies:
          return []

        avg_latency = sum(latencies) / len(latencies)
        threshold = avg_latency * threshold_multiplier

        # Second pass: identify spikes
        spikes = []
        for entry in entries:
          if entry["latency_ms"] > threshold:
            spike = {
                **entry,
                "spike_factor": round(entry["latency_ms"] / avg_latency, 2),
                "threshold_ms": round(threshold, 2),
                "average_ms": round(avg_latency, 2),
            }
            spikes.append(spike)

        # Sort by latency (highest first)
        spikes.sort(key=lambda x: x["latency_ms"], reverse=True)

        return spikes

      finally:
        await redis_client.close()

    except Exception as e:
      logger.error(
          f"Failed to analyze latency spikes for {service_type}: {e}", exc_info=True)
      return []

  async def get_endpoint_latency_breakdown(
      self,
      service_type: str,
      minutes: int = 60
  ) -> Dict[str, Dict[str, Any]]:
    """
    Break down latency statistics by endpoint.
    """
    try:
      if service_type not in self.stream_keys:
        logger.warning(
            f"Unknown service type for endpoint breakdown: {service_type}")
        return {}

      stream_key = self.stream_keys[service_type]

      end_time = datetime.now(timezone.utc)
      start_time = end_time - timedelta(minutes=minutes)
      start_id = str(int(start_time.timestamp() * 1000))
      end_id = str(int(end_time.timestamp() * 1000))

      redis_client = await self.redis.get_client()

      try:
        stream_data = await redis_client.xrange(
            stream_key,
            min=start_id,
            max=end_id,
            count=1000
        )

        if not stream_data:
          return {}

        # Group by endpoint
        endpoint_data = {}

        for stream_id, fields in stream_data:
          try:
            latency_ms = float(fields.get(b'latency_ms', 0))
            endpoint = fields.get(b'endpoint', b'unknown').decode()

            if endpoint not in endpoint_data:
              endpoint_data[endpoint] = []

            endpoint_data[endpoint].append(latency_ms)

          except (ValueError, KeyError) as e:
            logger.debug(
                f"Skipping malformed entry in endpoint breakdown: {e}")
            continue

        # Calculate statistics for each endpoint
        breakdown = {}
        for endpoint, latencies in endpoint_data.items():
          if latencies:
            latencies.sort()
            count = len(latencies)

            breakdown[endpoint] = {
                "count": count,
                "average_ms": round(sum(latencies) / count, 2),
                "min_ms": round(min(latencies), 2),
                "max_ms": round(max(latencies), 2),
                "median_ms": round(latencies[count // 2], 2),
                "p95_ms": round(latencies[int(count * 0.95)], 2) if count > 20 else None,
            }

        return breakdown

      finally:
        await redis_client.close()

    except Exception as e:
      logger.error(
          f"Failed to analyze endpoint breakdown for {service_type}: {e}", exc_info=True)
      return {}

  async def cleanup_old_stream_data(self, days_to_keep: int = 7) -> Dict[str, int]:
    """
    Clean up old stream data to prevent unbounded growth.
    Returns count of entries removed per service.
    """
    cleanup_results = {}

    cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    cutoff_timestamp_ms = int(cutoff_time.timestamp() * 1000)

    redis_client = await self.redis.get_client()

    try:
      for service_type, stream_key in self.stream_keys.items():
        try:
          # Get count before cleanup
          before_count = await redis_client.xlen(stream_key)

          # Remove entries older than cutoff
          await redis_client.xtrim(
              stream_key,
              minid=cutoff_timestamp_ms,
              approximate=False
          )

          # Get count after cleanup
          after_count = await redis_client.xlen(stream_key)

          cleanup_results[service_type] = before_count - after_count

          logger.info(
              f"Cleaned up {cleanup_results[service_type]} old entries "
              f"from {service_type} latency stream"
          )

        except Exception as e:
          logger.error(f"Failed to cleanup stream for {service_type}: {e}")
          cleanup_results[service_type] = -1

    finally:
      await redis_client.close()

    return cleanup_results
