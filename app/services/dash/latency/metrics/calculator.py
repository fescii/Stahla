import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

from app.services.redis.instrumented import InstrumentedRedisService
from app.core.cachekeys import (
    QUOTE_LATENCY_SORTED_SET,
    LOCATION_LATENCY_SORTED_SET,
    HUBSPOT_LATENCY_SORTED_SET,
    BLAND_LATENCY_SORTED_SET,
    GMAPS_LATENCY_SORTED_SET,
    REDIS_LATENCY_SORTED_SET,
    QUOTE_LATENCY_SUM_KEY,
    QUOTE_LATENCY_COUNT_KEY,
    LOCATION_LATENCY_SUM_KEY,
    LOCATION_LATENCY_COUNT_KEY,
    HUBSPOT_LATENCY_SUM_KEY,
    HUBSPOT_LATENCY_COUNT_KEY,
    BLAND_LATENCY_SUM_KEY,
    BLAND_LATENCY_COUNT_KEY,
    GMAPS_LATENCY_SUM_KEY,
    GMAPS_LATENCY_COUNT_KEY,
    REDIS_LATENCY_SUM_KEY,
    REDIS_LATENCY_COUNT_KEY,
    LATENCY_THRESHOLD_P95_MS,
    LATENCY_THRESHOLD_P99_MS,
)

logger = logging.getLogger(__name__)


class LatencyCalculator:
  """Calculates latency metrics from Redis data structures."""

  def __init__(self, redis_service: InstrumentedRedisService):
    self.redis = redis_service

    self.sorted_set_keys = {
        "quote": QUOTE_LATENCY_SORTED_SET,
        "location": LOCATION_LATENCY_SORTED_SET,
        "hubspot": HUBSPOT_LATENCY_SORTED_SET,
        "bland": BLAND_LATENCY_SORTED_SET,
        "gmaps": GMAPS_LATENCY_SORTED_SET,
        "redis": REDIS_LATENCY_SORTED_SET,
    }

    self.sum_keys = {
        "quote": QUOTE_LATENCY_SUM_KEY,
        "location": LOCATION_LATENCY_SUM_KEY,
        "hubspot": HUBSPOT_LATENCY_SUM_KEY,
        "bland": BLAND_LATENCY_SUM_KEY,
        "gmaps": GMAPS_LATENCY_SUM_KEY,
        "redis": REDIS_LATENCY_SUM_KEY,
    }

    self.count_keys = {
        "quote": QUOTE_LATENCY_COUNT_KEY,
        "location": LOCATION_LATENCY_COUNT_KEY,
        "hubspot": HUBSPOT_LATENCY_COUNT_KEY,
        "bland": BLAND_LATENCY_COUNT_KEY,
        "gmaps": GMAPS_LATENCY_COUNT_KEY,
        "redis": REDIS_LATENCY_COUNT_KEY,
    }

  async def get_percentiles(
      self,
      service_type: str,
      percentiles: List[float] = [50.0, 90.0, 95.0, 99.0]
  ) -> Dict[str, Optional[float]]:
    """
    Calculate percentiles from the sorted set.
    Returns a dict with percentile as key and latency_ms as value.
    """
    try:
      if service_type not in self.sorted_set_keys:
        logger.warning(
            f"Unknown service type for latency calculation: {service_type}")
        return {f"p{p}": None for p in percentiles}

      sorted_set_key = self.sorted_set_keys[service_type]

      # Get total count using Redis client directly
      redis_client = await self.redis.get_client()
      total_count = await redis_client.zcard(sorted_set_key)

      if total_count == 0:
        logger.debug(f"No latency data available for {service_type}")
        return {f"p{p}": None for p in percentiles}

      results = {}

      try:
        for percentile in percentiles:
          # Calculate the rank for this percentile
          rank = int((percentile / 100.0) * total_count) - 1
          rank = max(0, min(rank, total_count - 1))  # Clamp to valid range

          # Get the latency value at this rank
          latency_data = await redis_client.zrange(
              sorted_set_key,
              rank,
              rank,
              withscores=True
          )

          if latency_data:
            latency_ms = latency_data[0][1]  # Score is the latency
            results[f"p{percentile}"] = float(latency_ms)
          else:
            results[f"p{percentile}"] = None

      finally:
        await redis_client.close()

      logger.debug(f"Calculated percentiles for {service_type}: {results}")
      return results

    except Exception as e:
      logger.error(
          f"Failed to calculate percentiles for {service_type}: {e}", exc_info=True)
      return {f"p{p}": None for p in percentiles}

  async def get_average_latency(self, service_type: str) -> Optional[float]:
    """Calculate the average latency from sum and count counters."""
    try:
      if service_type not in self.sum_keys:
        logger.warning(
            f"Unknown service type for average calculation: {service_type}")
        return None

      sum_value = await self.redis.get(self.sum_keys[service_type])
      count_value = await self.redis.get(self.count_keys[service_type])

      if sum_value is None or count_value is None:
        logger.debug(
            f"No latency data for average calculation: {service_type}")
        return None

      total_sum = float(sum_value)
      total_count = int(count_value)

      if total_count == 0:
        return None

      average = total_sum / total_count
      logger.debug(f"Average latency for {service_type}: {average}ms")
      return average

    except Exception as e:
      logger.error(
          f"Failed to calculate average latency for {service_type}: {e}", exc_info=True)
      return None

  async def get_latency_summary(self, service_type: str) -> Dict[str, Any]:
    """Get a comprehensive latency summary for a service."""
    try:
      # Get percentiles and average in parallel
      percentiles_task = self.get_percentiles(service_type)
      average_task = self.get_average_latency(service_type)

      percentiles = await percentiles_task
      average = await average_task

      # Get total count
      total_count = 0
      if service_type in self.count_keys:
        count_value = await self.redis.get(self.count_keys[service_type])
        total_count = int(count_value) if count_value else 0

      # Determine status based on P95 threshold
      p95 = percentiles.get("p95.0")
      status = "unknown"
      if p95 is not None:
        if p95 <= LATENCY_THRESHOLD_P95_MS:
          status = "good"
        elif p95 <= LATENCY_THRESHOLD_P99_MS:
          status = "warning"
        else:
          status = "critical"

      summary = {
          "service_type": service_type,
          "average_ms": average,
          "percentiles": percentiles,
          "total_measurements": total_count,
          "status": status,
          "thresholds": {
              "p95_target_ms": LATENCY_THRESHOLD_P95_MS,
              "p99_alert_ms": LATENCY_THRESHOLD_P99_MS,
          },
          "timestamp": datetime.now(timezone.utc).isoformat(),
      }

      return summary

    except Exception as e:
      logger.error(
          f"Failed to get latency summary for {service_type}: {e}", exc_info=True)
      return {
          "service_type": service_type,
          "error": str(e),
          "timestamp": datetime.now(timezone.utc).isoformat(),
      }

  async def get_all_latency_summaries(self) -> Dict[str, Dict[str, Any]]:
    """Get latency summaries for all tracked services."""
    summaries = {}

    for service_type in self.sorted_set_keys.keys():
      summaries[service_type] = await self.get_latency_summary(service_type)

    return summaries

  async def check_latency_alerts(self) -> List[Dict[str, Any]]:
    """Check for latency alerts based on thresholds."""
    alerts = []

    for service_type in self.sorted_set_keys.keys():
      summary = await self.get_latency_summary(service_type)

      if summary.get("status") in ["warning", "critical"]:
        p95 = summary.get("percentiles", {}).get("p95.0")

        alert = {
            "service_type": service_type,
            "severity": summary["status"],
            "current_p95_ms": p95,
            "threshold_ms": LATENCY_THRESHOLD_P95_MS,
            "message": f"{service_type} P95 latency ({p95}ms) exceeds threshold ({LATENCY_THRESHOLD_P95_MS}ms)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        alerts.append(alert)

    return alerts

  async def reset_latency_counters(self, service_type: str) -> bool:
    """Reset the sum and count counters for a service (useful for testing or maintenance)."""
    try:
      if service_type not in self.sum_keys:
        logger.warning(f"Unknown service type for reset: {service_type}")
        return False

      redis_client = await self.redis.get_client()

      async with redis_client.pipeline(transaction=False) as pipe:
        pipe.delete(self.sum_keys[service_type])
        pipe.delete(self.count_keys[service_type])
        await pipe.execute()

      await redis_client.close()

      logger.info(f"Reset latency counters for {service_type}")
      return True

    except Exception as e:
      logger.error(
          f"Failed to reset latency counters for {service_type}: {e}", exc_info=True)
      return False
