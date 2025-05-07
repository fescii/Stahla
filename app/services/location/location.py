# filepath: /home/femar/AO3/Stahla/app/services/location/location.py
import asyncio
import functools # Import functools
import logging # Keep standard logging import for now, but don't initialize logger
import time
from typing import List, Optional, Tuple, Dict, Any

import googlemaps
from googlemaps.exceptions import ApiError, HTTPError, Timeout, TransportError
from fastapi import Depends, BackgroundTasks # Ensure Depends and BackgroundTasks are imported
import logfire # Import logfire

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

# logger = logging.getLogger(__name__) # Ensure standard logger is commented out or removed

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
            logfire.error(f"Branch list key '{BRANCH_LIST_CACHE_KEY}' not found in Redis cache. Run sheet sync. Cannot calculate distances.") # Use logfire
            return []
        if not isinstance(branches_data, list):
            logfire.error(f"Branch list data in Redis cache key '{BRANCH_LIST_CACHE_KEY}' is not a list. Cannot calculate distances.") # Use logfire
            return []
        if not branches_data: # Log if the list is empty, but proceed
             logfire.warning(f"Branch list loaded from Redis cache key '{BRANCH_LIST_CACHE_KEY}' is empty.") # Use logfire
             return []

        branches = []
        try:
            for i, branch_dict in enumerate(branches_data):
                 # Validate each item before appending
                try:
                    branches.append(BranchLocation(**branch_dict))
                except Exception as validation_error:
                     logfire.warning(f"Skipping invalid branch data at index {i} from Redis cache: {branch_dict}. Error: {validation_error}") # Use logfire
            logfire.info(f"Loaded {len(branches)} branches from Redis cache.") # Use logfire
            return branches
        except Exception as e:
            logfire.exception(f"Unexpected error parsing branch data from Redis cache key '{BRANCH_LIST_CACHE_KEY}'", exc_info=e) # Use logfire
            return []

    def _get_cache_key(self, branch_address: str, delivery_location: str) -> str:
        """Generates a standardized cache key for distance results."""
        # ... (implementation remains the same) ...
        norm_branch = "".join(filter(str.isalnum, branch_address)).lower()
        norm_delivery = "".join(filter(str.isalnum, delivery_location)).lower()
        return f"maps:distance:{norm_branch}:{norm_delivery}"

    async def _get_distance_from_google(self, origin: str, destination: str) -> Optional[Dict[str, Any]]:
        """Helper to get distance using Google Maps API, run in executor."""
        if not self.gmaps:
            logfire.error("Google Maps client not initialized.") # Use logfire
            return None
        
        loop = asyncio.get_running_loop()
        try:
            # Use functools.partial to wrap the function call with its arguments
            func_call = functools.partial(
                self.gmaps.distance_matrix, 
                origins=[origin], 
                destinations=[destination], 
                mode="driving"
            )
            # Now pass the executor (None for default) and the partial function
            result = await loop.run_in_executor(None, func_call)
            
            # Process result (check status, extract distance/duration)
            if result.get('status') == 'OK' and result['rows'][0]['elements'][0]['status'] == 'OK':
                element = result['rows'][0]['elements'][0]
                distance_meters = element['distance']['value']
                duration_seconds = element['duration']['value']
                # Convert meters to miles (1 meter ≈ 0.000621371 miles)
                distance_miles = distance_meters * MILES_PER_METER
                logfire.info(f"Google Maps distance: {distance_miles:.2f} miles, Duration: {duration_seconds}s for {origin} -> {destination}") # Use logfire
                return {
                    "distance_miles": round(distance_miles, 2),
                    "distance_meters": distance_meters, # Add distance_meters to the return dict
                    "duration_seconds": duration_seconds,
                    "origin": origin,
                    "destination": destination
                }
            else:
                logfire.warning(f"Google Maps API error for '{origin}' -> '{destination}': {result.get('status')}, Element Status: {result['rows'][0]['elements'][0].get('status')}") # Use logfire
                return None
        except Exception as e:
            logfire.error(f"Unexpected error during Google Maps API call for '{origin}' -> '{destination}': {e}", exc_info=True) # Use logfire
            return None

    async def get_distance_to_nearest_branch(self, delivery_location: str) -> Optional[DistanceResult]:
        """
        Finds the nearest Stahla branch (loaded from Redis) to a delivery location
        and calculates the driving distance using Google Maps API and Redis caching.
        NOTE: BackgroundTasks parameter removed as this is called from a background task context.
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
                logfire.info(f"Cache hit for distance: '{branch.address}' -> '{delivery_location}'") # Use logfire
                try:
                    distance_result = DistanceResult(**cached_data)
                    # Ensure the branch info in cache matches the current branch being checked
                    if distance_result.nearest_branch and distance_result.nearest_branch.name == branch.name and distance_result.nearest_branch.address == branch.address:
                        potential_results.append(distance_result)
                        cached_result_found = True
                        return
                    else:
                         logfire.warning(f"Cached data for key {cache_key} has mismatched branch info ({distance_result.nearest_branch}) vs current ({branch}). Will refetch.") # Use logfire
                         await self.redis_service.delete(cache_key) # Delete potentially stale cache entry

                except Exception as e:
                    logfire.warning(f"Error parsing cached data for key {cache_key}: {e}. Will refetch.") # Use logfire
                    await self.redis_service.delete(cache_key) # Delete invalid cache entry

            # If not cached or cache invalid/stale, call Google Maps API
            distance_info = await self._get_distance_from_google(branch.address, delivery_location)
            if distance_info:
                # Access values using dictionary keys instead of unpacking
                distance_meters = distance_info['distance_meters']
                duration_seconds = distance_info['duration_seconds']
                distance_miles = distance_info['distance_miles'] # Already calculated
                
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
            logfire.error(f"Could not determine distance to any branch for location: {delivery_location}") # Use logfire
            return None

        # Find the result with the minimum distance
        final_result = min(potential_results, key=lambda r: r.distance_meters)

        # Ensure the final result has the correct nearest branch assigned
        logfire.info(f"Nearest branch to '{delivery_location}' is '{final_result.nearest_branch.name}' ({final_result.distance_miles:.2f} miles)") # Use logfire
        return final_result

    async def prefetch_distance(self, delivery_location: str):
        """
        Triggers the distance calculation and caching in the background.
        Used by the early location lookup webhook.
        """
        # Use logfire directly for guaranteed output via configured pipeline
        logfire.info(f"Prefetching distance for location: {delivery_location}")
        try:
            # This method is already running as a background task.
            # It should directly call the core logic.
            await self.get_distance_to_nearest_branch(delivery_location)
            # Note: Any logging within get_distance_to_nearest_branch will now appear
            # in the main application logs associated with the background task execution.
        except Exception as e:
            # Use logfire directly for guaranteed output via configured pipeline
            logfire.error(f"Error prefetching distance for location {delivery_location}: {e}", exc_info=True)

# Dependency for FastAPI
async def get_location_service(redis_service: RedisService = Depends(get_redis_service)) -> LocationService:
    return LocationService(redis_service)
