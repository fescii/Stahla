# filepath: app/services/dash/stats/collector.py
import logging
from typing import Dict, Any, Optional
from app.services.redis.service import RedisService
from app.services.mongo import MongoService
from app.models.dash.dashboard import CacheStats, CacheHitMissRatio
from app.core.keys import (
    PRICING_CATALOG_CACHE_KEY,
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY,
    PRICING_CACHE_HITS_KEY,
    PRICING_CACHE_MISSES_KEY,
    MAPS_CACHE_HITS_KEY,
    MAPS_CACHE_MISSES_KEY,
)

logger = logging.getLogger(__name__)


class StatsCollector:
  """Collects statistics from Redis and MongoDB for dashboard."""

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis = redis_service
    self.mongo = mongo_service

  async def get_redis_counters(self) -> Dict[str, Any]:
    """Fetches counters from Redis."""
    try:
      keys_to_fetch = [
          TOTAL_QUOTE_REQUESTS_KEY,
          SUCCESS_QUOTE_REQUESTS_KEY,
          ERROR_QUOTE_REQUESTS_KEY,
          TOTAL_LOCATION_LOOKUPS_KEY,
          GMAPS_API_CALLS_KEY,
          GMAPS_API_ERRORS_KEY,
      ]
      results = await self.redis.mget(keys_to_fetch)

      redis_counters = {}
      for key, value in zip(keys_to_fetch, results):
        short_key = key.split(":")[-1]  # e.g., 'total', 'success', 'error'
        if key.startswith("dash:requests:quote:"):
          group = "quote_requests"
        elif key.startswith("dash:requests:location:"):
          group = "location_lookups"
        elif key.startswith("dash:gmaps:"):
          group = "gmaps_api"
        elif key.startswith("dash:sync:sheets:"):
          group = "sheet_sync_counters"
        else:
          group = "other"

        if group not in redis_counters:
          redis_counters[group] = {}
        redis_counters[group][short_key] = (
            int(value) if value is not None else 0
        )

      logger.debug(f"Redis Counters: {redis_counters}")
      return redis_counters

    except Exception as e:
      logger.error(f"Failed to fetch counters from Redis: {e}", exc_info=True)
      return {}

  async def get_cache_stats(self) -> CacheStats:
    """Collects cache statistics from Redis."""
    total_redis_keys = -1
    redis_memory_used_human = "N/A"
    pricing_catalog_size_bytes = None
    maps_cache_key_count = 0
    pricing_ratio_obj: Optional[CacheHitMissRatio] = None
    maps_ratio_obj: Optional[CacheHitMissRatio] = None

    try:
      redis_info = await self.redis.get_redis_info()
      if redis_info:
        total_redis_keys = redis_info.get("db0", {}).get("keys", -1)
        redis_memory_used_human = redis_info.get("used_memory_human", "N/A")

      pricing_catalog_size_bytes = await self.redis.get_key_memory_usage(
          PRICING_CATALOG_CACHE_KEY
      )

      maps_keys = await self.redis.scan_keys(match="maps:distance:*")
      maps_cache_key_count = len(maps_keys)

      # Calculate Pricing Cache Hit/Miss Ratio
      pricing_hits_raw = await self.redis.get(PRICING_CACHE_HITS_KEY)
      pricing_misses_raw = await self.redis.get(PRICING_CACHE_MISSES_KEY)
      pricing_hits = int(
          pricing_hits_raw) if pricing_hits_raw is not None else 0
      pricing_misses = int(
          pricing_misses_raw) if pricing_misses_raw is not None else 0
      pricing_total = pricing_hits + pricing_misses

      if pricing_total > 0:
        pricing_percentage = pricing_hits / pricing_total
        pricing_ratio_obj = CacheHitMissRatio(
            percentage=pricing_percentage,
            hits=pricing_hits,
            misses=pricing_misses,
            total=pricing_total,
            status=f"{pricing_percentage:.2%} ({pricing_hits} hits / {pricing_misses} misses)",
        )
      else:
        pricing_ratio_obj = CacheHitMissRatio(
            percentage=0.0,
            hits=0,
            misses=0,
            total=0,
            status="N/A (No data)"
        )

      # Calculate Maps Cache Hit/Miss Ratio
      maps_hits_raw = await self.redis.get(MAPS_CACHE_HITS_KEY)
      maps_misses_raw = await self.redis.get(MAPS_CACHE_MISSES_KEY)
      maps_hits = int(maps_hits_raw) if maps_hits_raw is not None else 0
      maps_misses = int(maps_misses_raw) if maps_misses_raw is not None else 0
      maps_total = maps_hits + maps_misses

      if maps_total > 0:
        maps_percentage = maps_hits / maps_total
        maps_ratio_obj = CacheHitMissRatio(
            percentage=maps_percentage,
            hits=maps_hits,
            misses=maps_misses,
            total=maps_total,
            status=f"{maps_percentage:.2%} ({maps_hits} hits / {maps_misses} misses)",
        )
      else:
        maps_ratio_obj = CacheHitMissRatio(
            percentage=0.0,
            hits=0,
            misses=0,
            total=0,
            status="N/A (No data)"
        )

    except Exception as e:
      logger.error(
          f"Failed to fetch some cache statistics: {e}", exc_info=True)
      # Ensure defaults if error occurs
      if pricing_ratio_obj is None:
        pricing_ratio_obj = CacheHitMissRatio(
            percentage=0.0,
            hits=0,
            misses=0,
            total=0,
            status="Error fetching data"
        )
      if maps_ratio_obj is None:
        maps_ratio_obj = CacheHitMissRatio(
            percentage=0.0,
            hits=0,
            misses=0,
            total=0,
            status="Error fetching data"
        )

    return CacheStats(
        total_redis_keys=total_redis_keys,
        redis_memory_used_human=redis_memory_used_human,
        pricing_catalog_size_bytes=pricing_catalog_size_bytes,
        maps_cache_key_count=maps_cache_key_count,
        hit_miss_ratio_pricing=pricing_ratio_obj,
        hit_miss_ratio_maps=maps_ratio_obj,
    )
