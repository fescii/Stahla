# filepath: app/services/location/distance/calculator.py
import asyncio
import logfire
from typing import Optional, List
from app.models.location import BranchLocation, DistanceResult
from app.services.location.cache import LocationCacheOperations
from app.services.location.google import GoogleMapsOperations
from app.services.location.areas import ServiceAreaChecker
from app.core.keys import MAPS_CACHE_HITS_KEY, MAPS_CACHE_MISSES_KEY
from app.services.background import increment_request_counter_bg
from app.services.background.util import add_task_safely

CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
LOCATION_LOOKUP_STAT_NAME = "location_lookups"


class DistanceCalculator:
  """Handles distance calculations between delivery locations and branches."""

  def __init__(
      self,
      cache_ops: LocationCacheOperations,
      google_ops: GoogleMapsOperations,
      area_checker: ServiceAreaChecker
  ):
    self.cache_ops = cache_ops
    self.google_ops = google_ops
    self.area_checker = area_checker

  async def get_distance_to_nearest_branch(
      self, delivery_location: str
  ) -> Optional[DistanceResult]:
    """
    Finds the nearest Stahla branch (loaded from Redis) to a delivery location
    and calculates the driving distance using Google Maps API and Redis caching.
    Logs errors to MongoDB and increments location lookup stats.

    Note: 
      Make sure to attach background tasks before calling this method using:
      app.services.background.util.attach_background_tasks(calculator, background_tasks)
    """
    success = False  # Initialize success flag for stat tracking
    try:
      # Check service area first
      within_service_area = await self.area_checker.check_service_area(delivery_location)

      branches = await self.cache_ops.get_branches_from_cache()
      if not branches:
        # Error already logged in get_branches_from_cache.
        # Additional log here for context of this specific function call.
        msg = f"Cannot determine nearest branch for '{delivery_location}': No branches loaded."
        logfire.error(msg)
        await self.cache_ops.mongo_service.log_error_to_db(
            service_name="DistanceCalculator.get_distance_to_nearest_branch",
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
        cache_key = self.cache_ops.get_cache_key(
            branch.address, delivery_location)
        cached_data = await self.cache_ops.redis_service.get_json(cache_key)

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
                  self.cache_ops.redis_service, MAPS_CACHE_HITS_KEY
              )
              api_call_needed = False
            else:
              logfire.warning(
                  f"Cached data for key {cache_key} has mismatched branch info ({distance_result.nearest_branch}) vs current ({branch}). Will refetch."
              )
              await self.cache_ops.redis_service.delete(cache_key)
          except Exception as e:
            logfire.warning(
                f"Error parsing cached data for key {cache_key}: {e}. Will refetch."
            )
            await self.cache_ops.redis_service.delete(cache_key)
            # Log this specific cache parsing error to MongoDB
            await self.cache_ops.mongo_service.log_error_to_db(
                service_name="DistanceCalculator.get_distance_to_nearest_branch.check_branch",
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
              self.cache_ops.redis_service, MAPS_CACHE_MISSES_KEY
          )
          distance_info = await self.google_ops.get_distance_from_google(
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
                geocoded_coordinates=distance_info.get("geocoded_coordinates"),
                is_distance_estimated=False,
            )
            potential_results.append(result)
            await self.cache_ops.redis_service.set_json(
                cache_key, result.model_dump(), ttl=CACHE_TTL_SECONDS
            )
          # else: get_distance_from_google already logged the error to DB

      await asyncio.gather(*(check_branch(branch) for branch in branches))

      if not potential_results:
        msg = f"Could not determine distance to any branch for location: {delivery_location}. All Google Maps API calls may have failed or returned no valid data."
        logfire.error(msg)
        await self.cache_ops.mongo_service.log_error_to_db(
            service_name="DistanceCalculator.get_distance_to_nearest_branch",
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
      # Use our utility function to safely add a background task
      from app.services.background.util import add_task_safely

      # Increment location lookup stats in a background task if available
      add_task_safely(
          self,
          self.cache_ops.mongo_service.increment_request_stat,
          LOCATION_LOOKUP_STAT_NAME,
          success)

  async def prefetch_distance(self, delivery_location: str):
    """
    Triggers the distance calculation and caching in the background.
    Used by the early location lookup webhook. Logs errors to MongoDB.
    The stat incrementation is handled by get_distance_to_nearest_branch.

    Note: 
      Make sure to attach background tasks before calling this method using:
      app.services.background.util.attach_background_tasks(calculator, background_tasks)
    """
    logfire.info(f"Prefetching distance for location: {delivery_location}")
    try:
      # The success/failure of this operation will be recorded by get_distance_to_nearest_branch's finally block.
      await self.get_distance_to_nearest_branch(delivery_location)
    except Exception as e:
      msg = (
          f"Error prefetching distance for location {delivery_location}: {str(e)}"
      )
      logfire.error(msg, exc_info=True)
      # Log the error specific to the prefetch operation itself to MongoDB
      await self.cache_ops.mongo_service.log_error_to_db(
          service_name="DistanceCalculator.prefetch_distance",
          error_type="PrefetchException",
          message=msg,
          details={
              "delivery_location": delivery_location,
              "exception_type": type(e).__name__,
              "args": e.args,
          },
      )
