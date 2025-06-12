# filepath: app/services/location/cache/operations.py
import logfire
from typing import List, Dict, Any, Optional
from app.models.location import BranchLocation
from app.services.redis.service import RedisService
from app.services.mongo import MongoService, SHEET_STATES_COLLECTION
from app.core.cachekeys import BRANCH_LIST_CACHE_KEY, STATES_LIST_CACHE_KEY


class LocationCacheOperations:
  """Handles caching operations for location service."""

  def __init__(self, redis_service: RedisService, mongo_service: MongoService):
    self.redis_service = redis_service
    self.mongo_service = mongo_service

  async def get_branches_from_cache(self) -> List[BranchLocation]:
    """Loads the list of branches from Redis cache. Logs errors to MongoDB."""
    try:
      branches_data = await self.redis_service.get_json(BRANCH_LIST_CACHE_KEY)
      if branches_data is None:
        msg = f"Branch list key '{BRANCH_LIST_CACHE_KEY}' not found in Redis cache. Run sheet sync."
        logfire.error(msg)
        await self.mongo_service.log_error_to_db(
            service_name="LocationCacheOperations.get_branches_from_cache",
            error_type="CacheMiss",
            message=msg,
            details={"cache_key": BRANCH_LIST_CACHE_KEY},
        )
        return []

      if not isinstance(branches_data, list):
        msg = f"Branch list data in Redis cache key '{BRANCH_LIST_CACHE_KEY}' is not a list."
        logfire.error(msg)
        await self.mongo_service.log_error_to_db(
            service_name="LocationCacheOperations.get_branches_from_cache",
            error_type="CacheFormatError",
            message=msg,
            details={
                "cache_key": BRANCH_LIST_CACHE_KEY,
                "data_type": str(type(branches_data)),
            },
        )
        return []

      if not branches_data:
        logfire.warning(
            f"Branch list loaded from Redis cache key '{BRANCH_LIST_CACHE_KEY}' is empty."
        )
        return []

      branches = []
      for i, branch_dict in enumerate(branches_data):
        try:
          branches.append(BranchLocation(**branch_dict))
        except Exception as validation_error:
          msg = f"Skipping invalid branch data at index {i} from Redis cache: {branch_dict}. Error: {validation_error}"
          logfire.warning(msg)
          await self.mongo_service.log_error_to_db(
              service_name="LocationCacheOperations.get_branches_from_cache",
              error_type="ValidationError",
              message="Invalid branch data in cache.",
              details={
                  "index": i,
                  "data": branch_dict,
                  "error": str(validation_error),
              },
          )

      logfire.info(f"Loaded {len(branches)} branches from Redis cache.")
      return branches
    except Exception as e:
      msg = f"Unexpected error parsing branch data from Redis cache key '{BRANCH_LIST_CACHE_KEY}'"
      logfire.exception(msg, exc_info=e)
      await self.mongo_service.log_error_to_db(
          service_name="LocationCacheOperations.get_branches_from_cache",
          error_type="UnexpectedException",
          message=f"{msg}: {str(e)}",
          details={
              "cache_key": BRANCH_LIST_CACHE_KEY,
              "exception_type": type(e).__name__,
              "args": e.args,
          },
      )
      return []

  async def get_states_from_cache_or_mongo(self) -> List[Dict[str, Any]]:
    """Gets states data from Redis cache, falls back to MongoDB if cache miss."""
    try:
      # Try Redis cache first
      states_data = await self.redis_service.get_json(STATES_LIST_CACHE_KEY)
      if states_data is not None:
        logfire.debug(
            f"States data loaded from Redis cache ({len(states_data)} states)")
        return states_data if isinstance(states_data, list) else []

      # Cache miss - get from MongoDB
      logfire.info("States cache miss - fetching from MongoDB")
      db = await self.mongo_service.get_db()
      collection = db[SHEET_STATES_COLLECTION]

      cursor = collection.find({})
      states_data = await cursor.to_list(length=None)

      # Cache the data in Redis for next time (72h TTL)
      if states_data:
        await self.redis_service.set_json(STATES_LIST_CACHE_KEY, states_data, ttl=259200)
        logfire.info(f"Cached {len(states_data)} states in Redis with 72h TTL")

      return states_data

    except Exception as e:
      logfire.error(
          f"Failed to get states data from cache or MongoDB: {e}", exc_info=True)
      await self.mongo_service.log_error_to_db(
          service_name="LocationCacheOperations.get_states_from_cache_or_mongo",
          error_type="StateDataFetchError",
          message=f"Failed to fetch states data: {str(e)}",
          details={"exception_type": type(e).__name__},
      )
      return []

  def get_cache_key(self, branch_address: str, delivery_location: str) -> str:
    """Generate cache key for distance calculations."""
    norm_branch = "".join(filter(str.isalnum, branch_address)).lower()
    norm_delivery = "".join(filter(str.isalnum, delivery_location)).lower()
    return f"maps:distance:{norm_branch}:{norm_delivery}"
