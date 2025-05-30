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
    SHEET_STATES_COLLECTION,
)  # Added MongoService, get_mongo_service, and SHEET_STATES_COLLECTION
from app.services.quote.sync import BRANCH_LIST_CACHE_KEY, STATES_LIST_CACHE_KEY
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

  async def _get_states_from_cache_or_mongo(self) -> List[Dict[str, Any]]:
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
          service_name="LocationService._get_states_from_cache_or_mongo",
          error_type="StateDataFetchError",
          message=f"Failed to fetch states data: {str(e)}",
          details={"exception_type": type(e).__name__},
      )
      return []

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
    tried_normalized = False
    final_result_data: Optional[Dict[str, Any]] = None

    # Attempt 1: Original destination
    try:
      logfire.info(
          f"Attempting Google Maps API call for origin: '{origin}', destination: '{destination}' (original)")
      await increment_request_counter_bg(
          self.redis_service, GMAPS_API_CALLS_KEY
      )
      func_call_orig = functools.partial(
          self.gmaps.distance_matrix,  # type: ignore
          origins=[origin],
          destinations=[destination],  # Original destination
          mode="driving",
      )
      result_orig = await loop.run_in_executor(None, func_call_orig)

      gmaps_status_orig = result_orig.get("status")
      element_status_orig = (
          result_orig["rows"][0]["elements"][0].get("status")
          if gmaps_status_orig == "OK" and result_orig.get("rows") and result_orig["rows"][0].get("elements")
          # if gmaps_status itself is an error
          else "N/A" if gmaps_status_orig == "OK" else gmaps_status_orig
      )

      if gmaps_status_orig == "OK" and element_status_orig == "OK":
        element = result_orig["rows"][0]["elements"][0]
        distance_meters = element["distance"]["value"]
        duration_seconds = element["duration"]["value"]
        distance_miles = distance_meters * MILES_PER_METER
        logfire.info(
            f"Google Maps distance (original): {distance_miles:.2f} miles, Duration: {duration_seconds}s for {origin} -> {destination}"
        )
        final_result_data = {
            "distance_miles": round(distance_miles, 2),
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "origin": origin,
            "destination": destination,
        }
      elif element_status_orig == "ZERO_RESULTS":
        logfire.warning(
            f"Google Maps API returned ZERO_RESULTS for original destination: '{destination}'. Attempting normalization.")
        normalized_destination = destination.split(',')[0].strip()
        if normalized_destination and normalized_destination.lower() != destination.lower():
          tried_normalized = True
          logfire.info(
              f"Attempting Google Maps API call for origin: '{origin}', destination: '{normalized_destination}' (normalized)")
          # Increment API call counter again for the second distinct API call
          await increment_request_counter_bg(
              self.redis_service, GMAPS_API_CALLS_KEY
          )
          func_call_norm = functools.partial(
              self.gmaps.distance_matrix,  # type: ignore
              origins=[origin],
              destinations=[normalized_destination],
              mode="driving",
          )
          result_norm = await loop.run_in_executor(None, func_call_norm)
          gmaps_status_norm = result_norm.get("status")
          element_status_norm = (
              result_norm["rows"][0]["elements"][0].get("status")
              if gmaps_status_norm == "OK" and result_norm.get("rows") and result_norm["rows"][0].get("elements")
              else "N/A" if gmaps_status_norm == "OK" else gmaps_status_norm
          )

          if gmaps_status_norm == "OK" and element_status_norm == "OK":
            element_norm = result_norm["rows"][0]["elements"][0]
            distance_meters_norm = element_norm["distance"]["value"]
            duration_seconds_norm = element_norm["duration"]["value"]
            distance_miles_norm = distance_meters_norm * MILES_PER_METER
            logfire.info(
                f"Google Maps distance (normalized): {distance_miles_norm:.2f} miles, Duration: {duration_seconds_norm}s for {origin} -> {normalized_destination}"
            )
            final_result_data = {
                "distance_miles": round(distance_miles_norm, 2),
                "distance_meters": distance_meters_norm,
                "duration_seconds": duration_seconds_norm,
                "origin": origin,
                "destination": destination,  # Return original destination for consistency
            }
          else:
            # Normalized attempt also failed
            msg = f"Google Maps API error for normalized_destination '{normalized_destination}' (original: '{destination}'): GMaps Status: {gmaps_status_norm}, Element Status: {element_status_norm}"
            logfire.warning(msg)
            await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
            await self.mongo_service.log_error_to_db(
                service_name="LocationService._get_distance_from_google",
                error_type="GoogleMapsAPINormalizedFailed",
                message=msg,
                details={
                    "origin": origin,
                    "original_destination": destination,
                    "normalized_destination_attempt": normalized_destination,
                    "gmaps_status_normalized": gmaps_status_norm,
                    "element_status_normalized": element_status_norm,
                    "full_response_normalized": result_norm,
                    "gmaps_status_original": gmaps_status_orig,  # from first attempt
                    "element_status_original": element_status_orig,  # from first attempt
                    "full_response_original": result_orig,  # from first attempt
                },
            )
        else:  # Original was ZERO_RESULTS, and normalized is same or empty
          msg = f"Google Maps API error for '{destination}': GMaps Status: {gmaps_status_orig}, Element Status: {element_status_orig}. No distinct normalized version to try or normalized is empty."
          logfire.warning(msg)
          await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
          await self.mongo_service.log_error_to_db(
              service_name="LocationService._get_distance_from_google",
              error_type="GoogleMapsAPIError",  # Keep as general API error
              message=msg,
              details={
                  "origin": origin,
                  "destination": destination,
                  "gmaps_status": gmaps_status_orig,
                  "element_status": element_status_orig,
                  "full_response": result_orig,
              },
          )
      else:  # Original attempt failed with something other than ZERO_RESULTS or OK/OK
        msg = f"Google Maps API error for '{destination}': GMaps Status: {gmaps_status_orig}, Element Status: {element_status_orig}"
        logfire.warning(msg)
        await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
        await self.mongo_service.log_error_to_db(
            service_name="LocationService._get_distance_from_google",
            error_type="GoogleMapsAPIError",
            message=msg,
            details={
                "origin": origin,
                "destination": destination,
                "gmaps_status": gmaps_status_orig,
                "element_status": element_status_orig,
                "full_response": result_orig,
            },
        )

      return final_result_data

    except (ApiError, HTTPError, Timeout, TransportError) as e:
      msg = f"Google Maps API client error for '{origin}' -> '{destination}': {type(e).__name__} - {str(e)}"
      logfire.error(msg, exc_info=True)
      # Increment error counter if it hasn't been for this specific attempt path
      # The GMAPS_API_CALLS_KEY is incremented at the start of each attempt.
      # GMAPS_API_ERRORS_KEY should be incremented if an attempt fails.
      # If an ApiError occurs, it implies the attempt failed before we could check status codes.
      await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
      await self.mongo_service.log_error_to_db(
          service_name="LocationService._get_distance_from_google",
          error_type=f"GoogleMapsClient{type(e).__name__}",
          message=msg,
          details={
              "origin": origin,
              "destination": destination,
              "tried_normalized": tried_normalized,
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
              "tried_normalized": tried_normalized,
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
      # Check service area first
      within_service_area = await self._check_service_area(delivery_location)

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
            # Handle legacy cached data that might not have within_service_area field
            if 'within_service_area' not in cached_data:
              cached_data['within_service_area'] = within_service_area

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
                within_service_area=within_service_area,
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

  async def _check_service_area(self, delivery_location: str) -> bool:
    """
    Checks if the delivery location is within the service area by extracting the state
    from the address and comparing it against the cached states data.
    """
    try:
      # Get states data from cache or MongoDB
      states_data = await self._get_states_from_cache_or_mongo()
      if not states_data:
        logfire.warning("No states data available for service area check")
        return False

      # Create sets of valid states and state codes for fast lookup
      valid_states = set()
      valid_codes = set()

      for state_entry in states_data:
        if isinstance(state_entry, dict):
          state_name = state_entry.get("state", "").strip().lower()
          state_code = state_entry.get("code", "").strip().upper()

          if state_name:
            valid_states.add(state_name)
          if state_code:
            valid_codes.add(state_code)

      # Extract state information from delivery location
      # Look for state patterns in the address
      location_upper = delivery_location.upper()
      location_lower = delivery_location.lower()

      # Check for state codes (e.g., "CA", "TX", "NY")
      import re
      state_code_pattern = r'\b([A-Z]{2})\b'
      code_matches = re.findall(state_code_pattern, location_upper)

      for code in code_matches:
        if code in valid_codes:
          logfire.info(
              f"Location '{delivery_location}' is in service area (state code: {code})")
          return True

      # Check for full state names
      for state in valid_states:
        if state in location_lower:
          logfire.info(
              f"Location '{delivery_location}' is in service area (state name: {state})")
          return True

      logfire.info(f"Location '{delivery_location}' is NOT in service area")
      return False

    except Exception as e:
      logfire.error(
          f"Error checking service area for '{delivery_location}': {e}", exc_info=True)
      await self.mongo_service.log_error_to_db(
          service_name="LocationService._check_service_area",
          error_type="ServiceAreaCheckError",
          message=f"Failed to check service area: {str(e)}",
          details={
              "delivery_location": delivery_location,
              "exception_type": type(e).__name__,
          },
      )
      # Return False on error for safety
      return False


# Dependency for FastAPI
async def get_location_service(
    redis_service: RedisService = Depends(get_redis_service),
    mongo_service: MongoService = Depends(
        get_mongo_service
    ),  # Added mongo_service dependency
) -> LocationService:
  return LocationService(redis_service, mongo_service)  # Pass mongo_service
