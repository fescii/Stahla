# filepath: /home/femar/AO3/Stahla/app/services/location/location.py
import asyncio
import logging
import time
from typing import List, Optional, Tuple

import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
from fastapi import Depends, BackgroundTasks # Ensure Depends and BackgroundTasks are imported

from app.core.config import settings
from app.models.location import BranchLocation, DistanceResult
from app.services.redis.redis import RedisService, get_redis_service # Import dependency function
from app.services.quote.sync import BRANCH_LIST_CACHE_KEY # Import branch cache key
from app.services.dash.background import (
    increment_request_counter_bg,
    log_error_bg,
    GMAPS_API_CALLS_KEY,
    GMAPS_API_ERRORS_KEY
)

logger = logging.getLogger(__name__)

# Constants
MILES_PER_METER = 0.000621371
CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours

class LocationService:
    """
    Service for calculating distances between delivery locations and Stahla branches,
    utilizing Google Maps API and Redis caching. Branches are loaded dynamically from Redis.
    """

    def __init__(self, redis_service: RedisService):
        self.redis_service = redis_service
        self.gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
        # Branches are no longer loaded from settings here

    async def _get_branches_from_cache(self) -> List[BranchLocation]:
        """Loads the list of branches from Redis cache."""
        branches_data = await self.redis_service.get_json(BRANCH_LIST_CACHE_KEY)
        if branches_data is None: # Check for None specifically, as empty list is valid
            logger.error(f"Branch list key '{BRANCH_LIST_CACHE_KEY}' not found in Redis cache. Run sheet sync. Cannot calculate distances.")
            return []
        if not isinstance(branches_data, list):
            logger.error(f"Branch list data in Redis cache key '{BRANCH_LIST_CACHE_KEY}' is not a list. Cannot calculate distances.")
            return []
        if not branches_data: # Log if the list is empty, but proceed
             logger.warning(f"Branch list loaded from Redis cache key '{BRANCH_LIST_CACHE_KEY}' is empty.")
             return []

        branches = []
        try:
            for i, branch_dict in enumerate(branches_data):
                 # Validate each item before appending
                try:
                    branches.append(BranchLocation(**branch_dict))
                except Exception as validation_error:
                     logger.warning(f"Skipping invalid branch data at index {i} from Redis cache: {branch_dict}. Error: {validation_error}")
            logger.info(f"Loaded {len(branches)} branches from Redis cache.")
            return branches
        except Exception as e:
            logger.exception(f"Unexpected error parsing branch data from Redis cache key '{BRANCH_LIST_CACHE_KEY}'", exc_info=e)
            return []

    def _get_cache_key(self, branch_address: str, delivery_location: str) -> str:
        """Generates a standardized cache key for distance results."""
        # ... (implementation remains the same) ...
        norm_branch = "".join(filter(str.isalnum, branch_address)).lower()
        norm_delivery = "".join(filter(str.isalnum, delivery_location)).lower()
        return f"maps:distance:{norm_branch}:{norm_delivery}"

    async def _get_distance_from_google(self, origin: str, destination: str, background_tasks: BackgroundTasks) -> Optional[Tuple[int, int]]:
        """
        Calls the Google Maps Distance Matrix API and increments counters via background tasks.
        """
        # Increment total calls counter in the background
        background_tasks.add_task(increment_request_counter_bg, self.redis_service, GMAPS_API_CALLS_KEY)
        
        try:
            logger.info(f"Calling Google Maps API for distance: '{origin}' -> '{destination}'")
            start_time = time.monotonic()
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                self.gmaps.distance_matrix,
                origins=[origin],
                destinations=[destination],
                mode="driving"
            )
            duration = time.monotonic() - start_time
            logger.info(f"Google Maps API call took {duration:.3f} seconds.")

            if result['status'] == 'OK' and result['rows'][0]['elements'][0]['status'] == 'OK':
                distance_meters = result['rows'][0]['elements'][0]['distance']['value']
                duration_seconds = result['rows'][0]['elements'][0]['duration']['value']
                return distance_meters, duration_seconds
            else:
                error_status = result['rows'][0]['elements'][0].get('status', result['status'])
                logger.error(f"Google Maps API error for '{origin}' -> '{destination}': {error_status}")
                # Increment error counter and log error in background
                background_tasks.add_task(increment_request_counter_bg, self.redis_service, GMAPS_API_ERRORS_KEY)
                background_tasks.add_task(log_error_bg, self.redis_service, "GoogleMapsAPIError", error_status, {"origin": origin, "destination": destination})
                return None

        except (ApiError, HTTPError, Timeout, TransportError) as e:
            error_msg = f"Google Maps API request failed for '{origin}' -> '{destination}': {e}"
            logger.error(error_msg, exc_info=True)
            # Increment error counter and log error in background
            background_tasks.add_task(increment_request_counter_bg, self.redis_service, GMAPS_API_ERRORS_KEY)
            background_tasks.add_task(log_error_bg, self.redis_service, type(e).__name__, str(e), {"origin": origin, "destination": destination})
            return None
        except Exception as e:
            error_msg = f"Unexpected error during Google Maps API call for '{origin}' -> '{destination}'"
            logger.exception(error_msg, exc_info=e)
            # Increment error counter and log error in background
            background_tasks.add_task(increment_request_counter_bg, self.redis_service, GMAPS_API_ERRORS_KEY)
            background_tasks.add_task(log_error_bg, self.redis_service, type(e).__name__, str(e), {"origin": origin, "destination": destination})
            return None

    async def get_distance_to_nearest_branch(self, delivery_location: str, background_tasks: BackgroundTasks) -> Optional[DistanceResult]:
        """
        Finds the nearest Stahla branch (loaded from Redis) to a delivery location
        and calculates the driving distance using Google Maps API and Redis caching.
        Propagates BackgroundTasks to _get_distance_from_google.
        """
        # Load branches dynamically on each call
        branches = await self._get_branches_from_cache()
        if not branches:
            # Error already logged in _get_branches_from_cache or warning if empty
            return None # Cannot proceed without branches

        # --- Calculation logic remains largely the same --- 
        min_distance_meters = float('inf')
        nearest_branch: Optional[BranchLocation] = None
        best_duration_seconds: Optional[int] = None
        cached_result_found = False
        potential_results = []

        # Check cache and make API calls concurrently using the loaded branches
        async def check_branch(branch: BranchLocation):
            nonlocal min_distance_meters, nearest_branch, best_duration_seconds, cached_result_found
            cache_key = self._get_cache_key(branch.address, delivery_location)
            cached_data = await self.redis_service.get_json(cache_key)

            if cached_data:
                logger.info(f"Cache hit for distance: '{branch.address}' -> '{delivery_location}'")
                try:
                    distance_result = DistanceResult(**cached_data)
                    # Ensure the branch info in cache matches the current branch being checked
                    if distance_result.nearest_branch and distance_result.nearest_branch.name == branch.name and distance_result.nearest_branch.address == branch.address:
                        potential_results.append(distance_result)
                        cached_result_found = True
                        return
                    else:
                         logger.warning(f"Cached data for key {cache_key} has mismatched branch info ({distance_result.nearest_branch}) vs current ({branch}). Will refetch.")
                         await self.redis_service.delete(cache_key) # Delete potentially stale cache entry

                except Exception as e:
                    logger.warning(f"Error parsing cached data for key {cache_key}: {e}. Will refetch.")
                    await self.redis_service.delete(cache_key) # Delete invalid cache entry

            # If not cached or cache invalid/stale, call Google Maps API
            distance_info = await self._get_distance_from_google(branch.address, delivery_location, background_tasks)
            if distance_info:
                distance_meters, duration_seconds = distance_info
                distance_miles = distance_meters * MILES_PER_METER
                result = DistanceResult(
                    nearest_branch=branch, # Store the current branch being checked
                    delivery_location=delivery_location,
                    distance_miles=distance_miles,
                    distance_meters=distance_meters,
                    duration_seconds=duration_seconds
                )
                potential_results.append(result)
                # Cache the full result including the branch info
                await self.redis_service.set_json(cache_key, result.model_dump(), ttl=CACHE_TTL_SECONDS)

        # Run checks for all dynamically loaded branches concurrently
        await asyncio.gather(*(check_branch(branch) for branch in branches))

        # Find the minimum distance among all results (cached or newly fetched)
        if not potential_results:
            logger.error(f"Could not determine distance to any branch for location: {delivery_location}")
            return None

        # Find the result with the minimum distance
        final_result = min(potential_results, key=lambda r: r.distance_meters)

        # Ensure the final result has the correct nearest branch assigned
        logger.info(f"Nearest branch to '{delivery_location}' is '{final_result.nearest_branch.name}' ({final_result.distance_miles:.2f} miles)")
        return final_result

    async def prefetch_distance(self, delivery_location: str):
        """
        Triggers the distance calculation and caching in the background.
        Used by the early location lookup webhook.
        """
        logger.info(f"Prefetching distance for location: {delivery_location}")
        try:
            # Create a new BackgroundTasks instance for this background job
            bg_tasks = BackgroundTasks()
            # Pass the new BackgroundTasks instance down
            await self.get_distance_to_nearest_branch(delivery_location, bg_tasks)
            # Note: The tasks added within get_distance_to_nearest_branch will run
            # but their execution isn't awaited here, which is the point.
            logger.info(f"Prefetch task initiated (including background counters) for: {delivery_location}")
        except Exception as e:
            logger.exception(f"Error during background distance prefetch initiation for '{delivery_location}'", exc_info=e)


# Dependency for FastAPI
async def get_location_service(redis_service: RedisService = Depends(get_redis_service)) -> LocationService:
    return LocationService(redis_service)
