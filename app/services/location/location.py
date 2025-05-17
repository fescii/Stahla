# filepath: /home/femar/AO3/Stahla/app/services/location/location.py
import asyncio
import functools
import logging
import time
from typing import List, Optional, Tuple, Dict, Any

import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
from fastapi import Depends, BackgroundTasks, Request, HTTPException, status
import logfire

from app.core.config import settings
from app.models.location import BranchLocation, DistanceResult
from app.services.redis.redis import (
    RedisService,
    get_redis_service,
)  # Added get_redis_service for dependency
from app.services.mongo.mongo import (
    MongoService,
    get_mongo_service,
)  # Added MongoService and get_mongo_service
from app.services.quote.sync import BRANCH_LIST_CACHE_KEY
from app.services.dash.background import (
    increment_request_counter_bg,
    log_error_bg,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY,
)
from app.services.dash.dashboard import MAPS_CACHE_HITS_KEY, MAPS_CACHE_MISSES_KEY

MILES_PER_METER = 0.000621371
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
# Constants for stats
LOCATION_LOOKUP_STAT_NAME = "location_lookups"


class LocationService:
  """
  Service for calculating distances between delivery locations and Stahla branches,
  utilizing Google Maps API and Redis caching. Branches are loaded dynamically from Redis.
  Integrates with MongoService for error logging.
  """

  def __init__(
      self, redis_service: RedisService, mongo_service: MongoService
  ):  # Added mongo_service
    self.redis_service = redis_service
    self.mongo_service = mongo_service  # Store mongo_service
    self.gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)

  async def _get_branches_from_cache(self) -> List[BranchLocation]:
    """Loads the list of branches from Redis cache. Logs errors to MongoDB."""
    try:
      branches_data = await self.redis_service.get_json(BRANCH_LIST_CACHE_KEY)
      if branches_data is None:
        msg = f"Branch list key '{BRANCH_LIST_CACHE_KEY}' not found in Redis cache. Run sheet sync."
        logfire.error(msg)
        await self.mongo_service.log_error_to_db(
            service_name="LocationService._get_branches_from_cache",
            error_type="CacheMiss",
            message=msg,
            details={"cache_key": BRANCH_LIST_CACHE_KEY},
        )
        return []
      if not isinstance(branches_data, list):
        msg = f"Branch list data in Redis cache key '{BRANCH_LIST_CACHE_KEY}' is not a list."
        logfire.error(msg)
        await self.mongo_service.log_error_to_db(
            service_name="LocationService._get_branches_from_cache",
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
        # Not necessarily an error to log to DB, but a warning.
        return []

      branches = []
      for i, branch_dict in enumerate(branches_data):
        try:
          branches.append(BranchLocation(**branch_dict))
        except Exception as validation_error:
          msg = f"Skipping invalid branch data at index {i} from Redis cache: {branch_dict}. Error: {validation_error}"
          logfire.warning(msg)
          await self.mongo_service.log_error_to_db(
              service_name="LocationService._get_branches_from_cache",
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
          service_name="LocationService._get_branches_from_cache",
          error_type="UnexpectedException",
          message=f"{msg}: {str(e)}",
          details={
              "cache_key": BRANCH_LIST_CACHE_KEY,
              "exception_type": type(e).__name__,
              "args": e.args,
          },
      )
      return []

  def _get_cache_key(self, branch_address: str, delivery_location: str) -> str:
    norm_branch = "".join(filter(str.isalnum, branch_address)).lower()
    norm_delivery = "".join(filter(str.isalnum, delivery_location)).lower()
    return f"maps:distance:{norm_branch}:{norm_delivery}"

  async def _get_distance_from_google(
      self, origin: str, destination: str
  ) -> Optional[Dict[str, Any]]:
    """Helper to get distance using Google Maps API, run in executor. Logs errors to MongoDB."""
    if not self.gmaps:
      msg = "Google Maps client not initialized."
      logfire.error(msg)
      await self.mongo_service.log_error_to_db(
          service_name="LocationService._get_distance_from_google",
          error_type="ConfigurationError",
          message=msg,
          details={"origin": origin, "destination": destination},
      )
      return None

    loop = asyncio.get_running_loop()
    try:
      await increment_request_counter_bg(
          self.redis_service, GMAPS_API_CALLS_KEY
      )  # Increment API call counter
      func_call = functools.partial(
          self.gmaps.distance_matrix,
          origins=[origin],
          destinations=[destination],
          mode="driving",
      )
      result = await loop.run_in_executor(None, func_call)

      if (
          result.get("status") == "OK"
          and result["rows"][0]["elements"][0]["status"] == "OK"
      ):
        element = result["rows"][0]["elements"][0]
        distance_meters = element["distance"]["value"]
        duration_seconds = element["duration"]["value"]
        distance_miles = distance_meters * MILES_PER_METER
        logfire.info(
            f"Google Maps distance: {distance_miles:.2f} miles, Duration: {duration_seconds}s for {origin} -> {destination}"
        )
        return {
            "distance_miles": round(distance_miles, 2),
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "origin": origin,
            "destination": destination,
        }
      else:
        gmaps_status = result.get("status")
        element_status = (
            result["rows"][0]["elements"][0].get("status")
            if result.get("rows") and result["rows"][0].get("elements")
            else "N/A"
        )
        msg = f"Google Maps API error for '{origin}' -> '{destination}': GMaps Status: {gmaps_status}, Element Status: {element_status}"
        logfire.warning(msg)
        await increment_request_counter_bg(
            self.redis_service, GMAPS_API_ERRORS_KEY
        )  # Increment API error counter
        await self.mongo_service.log_error_to_db(
            service_name="LocationService._get_distance_from_google",
            error_type="GoogleMapsAPIError",
            message=msg,
            details={
                "origin": origin,
                "destination": destination,
                "gmaps_status": gmaps_status,
                "element_status": element_status,
                "full_response": result,
            },
        )
        return None
    except (
        ApiError,
        HTTPError,
        Timeout,
        TransportError,
    ) as e:  # Catch specific Google Maps client errors
      msg = f"Google Maps API client error for '{origin}' -> '{destination}': {type(e).__name__} - {str(e)}"
      logfire.error(msg, exc_info=True)
      await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
      await self.mongo_service.log_error_to_db(
          service_name="LocationService._get_distance_from_google",
          error_type=f"GoogleMapsClient{type(e).__name__}",
          message=msg,
          details={
              "origin": origin,
              "destination": destination,
              "exception_type": type(e).__name__,
              "args": e.args,
          },
      )
      return None
    except Exception as e:
      msg = f"Unexpected error during Google Maps API call for '{origin}' -> '{destination}': {str(e)}"
      logfire.error(msg, exc_info=True)
      await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
      await self.mongo_service.log_error_to_db(
          service_name="LocationService._get_distance_from_google",
          error_type="UnexpectedException",
          message=msg,
          details={
              "origin": origin,
              "destination": destination,
              "exception_type": type(e).__name__,
              "args": e.args,
          },
      )
      return None

  async def get_distance_to_nearest_branch(
      # Ensure BackgroundTasks is injected
      self, delivery_location: str, background_tasks: BackgroundTasks
  ) -> Optional[DistanceResult]:
    """
    Finds the nearest Stahla branch (loaded from Redis) to a delivery location
    and calculates the driving distance using Google Maps API and Redis caching.
    Logs errors to MongoDB and increments location lookup stats.
    """
    success = False  # Initialize success flag for stat tracking
    try:
      branches = await self._get_branches_from_cache()
      if not branches:
        # Error already logged in _get_branches_from_cache.
        # Additional log here for context of this specific function call.
        msg = f"Cannot determine nearest branch for '{delivery_location}': No branches loaded."
        logfire.error(msg)
        await self.mongo_service.log_error_to_db(
            service_name="LocationService.get_distance_to_nearest_branch",
            error_type="NoBranchesLoaded",
            message=msg,
            details={"delivery_location": delivery_location},
        )
        # success remains False
        return None

      min_distance_meters = float("inf")
      nearest_branch: Optional[BranchLocation] = None
      best_duration_seconds: Optional[int] = None
      potential_results = []

      async def check_branch(branch: BranchLocation):
        nonlocal min_distance_meters, nearest_branch, best_duration_seconds, potential_results
        cache_key = self._get_cache_key(branch.address, delivery_location)
        cached_data = await self.redis_service.get_json(cache_key)

        api_call_needed = True

        if cached_data:
          logfire.info(
              f"Cache hit for distance: '{branch.address}' -> '{delivery_location}'"
          )
          try:
            distance_result = DistanceResult(**cached_data)
            if (
                distance_result.nearest_branch
                and distance_result.nearest_branch.name == branch.name
                and distance_result.nearest_branch.address == branch.address
            ):
              potential_results.append(distance_result)
              await increment_request_counter_bg(
                  self.redis_service, MAPS_CACHE_HITS_KEY
              )
              api_call_needed = False
            else:
              logfire.warning(
                  f"Cached data for key {cache_key} has mismatched branch info ({distance_result.nearest_branch}) vs current ({branch}). Will refetch."
              )
              await self.redis_service.delete(cache_key)
          except Exception as e:
            logfire.warning(
                f"Error parsing cached data for key {cache_key}: {e}. Will refetch."
            )
            await self.redis_service.delete(cache_key)
            # Log this specific cache parsing error to MongoDB
            await self.mongo_service.log_error_to_db(
                service_name="LocationService.get_distance_to_nearest_branch.check_branch",
                error_type="CacheParseError",
                message=f"Error parsing cached distance data for key {cache_key}: {str(e)}",
                details={
                    "cache_key": cache_key,
                    "branch_address": branch.address,
                    "delivery_location": delivery_location,
                    "exception_type": type(e).__name__,
                },
            )

        if api_call_needed:
          await increment_request_counter_bg(
              self.redis_service, MAPS_CACHE_MISSES_KEY
          )
          distance_info = await self._get_distance_from_google(
              branch.address, delivery_location
          )
          if distance_info:
            distance_meters = distance_info["distance_meters"]
            duration_seconds = distance_info["duration_seconds"]
            distance_miles = distance_info["distance_miles"]

            result = DistanceResult(
                nearest_branch=branch,
                delivery_location=delivery_location,
                distance_miles=distance_miles,
                distance_meters=distance_meters,
                duration_seconds=duration_seconds,
            )
            potential_results.append(result)
            await self.redis_service.set_json(
                cache_key, result.model_dump(), ttl=CACHE_TTL_SECONDS
            )
          # else: _get_distance_from_google already logged the error to DB

      await asyncio.gather(*(check_branch(branch) for branch in branches))

      if not potential_results:
        msg = f"Could not determine distance to any branch for location: {delivery_location}. All Google Maps API calls may have failed or returned no valid data."
        logfire.error(msg)
        await self.mongo_service.log_error_to_db(
            service_name="LocationService.get_distance_to_nearest_branch",
            error_type="NoDistanceCalculated",
            message=msg,
            details={
                "delivery_location": delivery_location,
                "num_branches_checked": len(branches),
            },
        )
        # success remains False
        return None

      final_result = min(potential_results, key=lambda r: r.distance_meters)
      logfire.info(
          f"Nearest branch to '{delivery_location}' is '{final_result.nearest_branch.name}' ({final_result.distance_miles:.2f} miles)"
      )
      success = True  # Set success to True as we have a result
      return final_result
    finally:
      # Increment location lookup stats in a background task
      # This task will run after the response has been sent if called from an endpoint
      background_tasks.add_task(
          self.mongo_service.increment_request_stat, LOCATION_LOOKUP_STAT_NAME, success)

  # Ensure BackgroundTasks is injected
  async def prefetch_distance(self, delivery_location: str, background_tasks: BackgroundTasks):
    """
    Triggers the distance calculation and caching in the background.
    Used by the early location lookup webhook. Logs errors to MongoDB.
    The stat incrementation is handled by get_distance_to_nearest_branch.
    """
    logfire.info(f"Prefetching distance for location: {delivery_location}")
    try:
      # Pass background_tasks to get_distance_to_nearest_branch
      # The success/failure of this operation will be recorded by get_distance_to_nearest_branch's finally block.
      await self.get_distance_to_nearest_branch(delivery_location, background_tasks)
    except Exception as e:
      msg = (
          f"Error prefetching distance for location {delivery_location}: {str(e)}"
      )
      logfire.error(msg, exc_info=True)
      # Log the error specific to the prefetch operation itself to MongoDB
      await self.mongo_service.log_error_to_db(
          service_name="LocationService.prefetch_distance",
          error_type="PrefetchException",
          message=msg,
          details={
              "delivery_location": delivery_location,
              "exception_type": type(e).__name__,
              "args": e.args,
          },
      )
      # It's important to consider if an additional stat increment is needed here.
      # If get_distance_to_nearest_branch's finally block always runs, it will record the outcome.
      # If an exception here means get_distance_to_nearest_branch didn't run or its finally block was skipped (unlikely),
      # then a manual increment for failure might be needed.
      # For now, relying on get_distance_to_nearest_branch to handle its own stat.
      # If this prefetch_distance itself is considered a "request" that can fail independently
      # of the underlying get_distance_to_nearest_branch, then a separate stat might be warranted.
      # However, the current setup implies prefetch_distance is just a trigger.


# Dependency for FastAPI
async def get_location_service(
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(
        get_mongo_service
    ),  # Added mongo_service dependency
) -> LocationService:
  return LocationService(redis_service, mongo_service)  # Pass mongo_service
