# filepath: /home/femar/AO3/Stahla/app/services/location/location.py
import asyncio
import functools
import logging
import time
import re
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
from app.services.quote.shared.constants import BRANCH_LIST_CACHE_KEY, STATES_LIST_CACHE_KEY
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


def parse_and_normalize_address(address: str) -> List[str]:
  """
  Parse and normalize an address to generate multiple variations for Google Maps API.

  For addresses like "47 W 13th St, New York, NY 10011, USA", this generates:
  1. Original address
  2. Without country: "47 W 13th St, New York, NY 10011"
  3. Street + City + State: "47 W 13th St, New York, NY"
  4. City + State + ZIP: "New York, NY 10011"
  5. City + State: "New York, NY"
  6. Just the street address: "47 W 13th St"

  Args:
      address: The input address string

  Returns:
      List of normalized address variations ordered by specificity (most to least)
  """
  if not address or not address.strip():
    return []

  address = address.strip()
  variations = [address]  # Start with original

  # Split by commas and clean up parts
  parts = [part.strip() for part in address.split(',') if part.strip()]

  if len(parts) <= 1:
    return variations

  # Common patterns to identify address components
  zip_pattern = r'\b\d{5}(-\d{4})?\b'  # ZIP codes
  state_pattern = r'\b[A-Z]{2}\b'  # State codes like NY, CA, TX
  country_pattern = r'\b(USA|US|United States|America)\b'

  # Identify components
  has_zip = any(re.search(zip_pattern, part) for part in parts)
  has_state = any(re.search(state_pattern, part) for part in parts)
  has_country = any(re.search(country_pattern, part, re.IGNORECASE)
                    for part in parts)

  # Generate variations based on structure
  if len(parts) >= 2:
    # Without last part (often country or redundant info)
    variation = ', '.join(parts[:-1])
    if variation != address and variation not in variations:
      variations.append(variation)

  if len(parts) >= 3:
    # First part + last two parts (street + city/state info)
    if has_state or has_zip:
      variation = ', '.join([parts[0]] + parts[-2:])
      if variation not in variations:
        variations.append(variation)

    # Without first part (city/state/zip without street)
    variation = ', '.join(parts[1:])
    if variation not in variations:
      variations.append(variation)

  if len(parts) >= 4:
    # Street + City + State (without ZIP and country)
    # Look for the pattern: street, city, state, zip
    if has_state and has_zip:
      # Assume: street, city, state+zip or zip, country
      variation = ', '.join(parts[:3])
      if variation not in variations:
        variations.append(variation)

    # First and last two parts
    variation = ', '.join([parts[0]] + parts[-2:])
    if variation not in variations:
      variations.append(variation)

  # Add just the first part (street address)
  if len(parts) > 1 and parts[0] not in variations:
    variations.append(parts[0])

  # Add city + state combinations
  for i, part in enumerate(parts):
    if re.search(state_pattern, part):  # Found state
      if i > 0:  # Has city before state
        city_state = ', '.join(parts[i-1:i+1])
        if city_state not in variations:
          variations.append(city_state)
      break

  # Remove duplicates while preserving order
  seen = set()
  unique_variations = []
  for var in variations:
    if var not in seen:
      seen.add(var)
      unique_variations.append(var)

  return unique_variations


def extract_location_components(address: str) -> Dict[str, Optional[str]]:
  """
  Extract structured components from an address string.

  Args:
      address: Input address string

  Returns:
      Dictionary with components: street, city, state, zip_code, country
  """
  if not address:
    return {"street": None, "city": None, "state": None, "zip_code": None, "country": None}

  parts = [part.strip() for part in address.split(',') if part.strip()]

  # Initialize components with proper typing
  components: Dict[str, Optional[str]] = {
      "street": None,
      "city": None,
      "state": None,
      "zip_code": None,
      "country": None
  }

  # Patterns
  zip_pattern = r'\b(\d{5}(-\d{4})?)\b'
  state_pattern = r'\b([A-Z]{2})\b'
  country_pattern = r'\b(USA|US|United States|America)\b'

  # Process parts from right to left (more specific to less specific)
  for i, part in enumerate(reversed(parts)):
    reverse_idx = len(parts) - 1 - i

    # Check for country
    if re.search(country_pattern, part, re.IGNORECASE) and not components["country"]:
      components["country"] = part
      continue

    # Check for ZIP code
    zip_match = re.search(zip_pattern, part)
    if zip_match and not components["zip_code"]:
      components["zip_code"] = zip_match.group(1)
      # Remove ZIP from the part for further processing
      part_without_zip = re.sub(zip_pattern, '', part).strip()
      if part_without_zip:
        part = part_without_zip

    # Check for state
    state_match = re.search(state_pattern, part)
    if state_match and not components["state"]:
      components["state"] = state_match.group(1)
      # Remove state from the part for further processing
      part_without_state = re.sub(state_pattern, '', part).strip()
      if part_without_state:
        part = part_without_state

    # Assign remaining parts
    if reverse_idx == 0 and not components["street"]:
      components["street"] = parts[0]  # First part is usually street
    elif part and not components["city"] and reverse_idx > 0:
      components["city"] = part

  return components


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
    """Helper to get distance using Google Maps API with multiple address variations. Logs errors to MongoDB."""
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
    final_result_data: Optional[Dict[str, Any]] = None
    attempted_variations = []

    # Get multiple variations of the destination address
    destination_variations = parse_and_normalize_address(destination)
    logfire.info(
        f"Generated {len(destination_variations)} address variations for '{destination}': {destination_variations}")

    # Try each variation until we get a successful result
    for i, dest_variation in enumerate(destination_variations):
      try:
        logfire.info(
            f"Attempting Google Maps API call for origin: '{origin}', destination: '{dest_variation}' (variation {i+1}/{len(destination_variations)})")
        await increment_request_counter_bg(
            self.redis_service, GMAPS_API_CALLS_KEY
        )

        func_call = functools.partial(
            self.gmaps.distance_matrix,  # type: ignore
            origins=[origin],
            destinations=[dest_variation],
            mode="driving",
        )
        result = await loop.run_in_executor(None, func_call)
        attempted_variations.append(dest_variation)

        gmaps_status = result.get("status")
        element_status = (
            result["rows"][0]["elements"][0].get("status")
            if gmaps_status == "OK" and result.get("rows") and result["rows"][0].get("elements")
            else "N/A" if gmaps_status == "OK" else gmaps_status
        )

        if gmaps_status == "OK" and element_status == "OK":
          element = result["rows"][0]["elements"][0]
          distance_meters = element["distance"]["value"]
          duration_seconds = element["duration"]["value"]
          distance_miles = distance_meters * MILES_PER_METER
          logfire.info(
              f"Google Maps distance (variation {i+1}): {distance_miles:.2f} miles, Duration: {duration_seconds}s for {origin} -> {dest_variation}"
          )
          final_result_data = {
              "distance_miles": round(distance_miles, 2),
              "distance_meters": distance_meters,
              "duration_seconds": duration_seconds,
              "origin": origin,
              "destination": destination,  # Return original destination for consistency
              "successful_variation": dest_variation,
          }
          break  # Success! Stop trying other variations

        elif element_status == "ZERO_RESULTS":
          logfire.warning(
              f"Google Maps API returned ZERO_RESULTS for variation {i+1}: '{dest_variation}'. Trying next variation.")
          continue  # Try next variation

        else:
          # Other error status - log but continue trying
          logfire.warning(
              f"Google Maps API error for variation {i+1} '{dest_variation}': GMaps Status: {gmaps_status}, Element Status: {element_status}")
          continue  # Try next variation

      except (ApiError, HTTPError, Timeout, TransportError) as e:
        msg = f"Google Maps API client error for variation {i+1} '{dest_variation}': {type(e).__name__} - {str(e)}"
        logfire.warning(msg)
        attempted_variations.append(dest_variation)
        continue  # Try next variation

      except Exception as e:
        msg = f"Unexpected error during Google Maps API call for variation {i+1} '{dest_variation}': {str(e)}"
        logfire.warning(msg)
        attempted_variations.append(dest_variation)
        continue  # Try next variation

    # If we reach here and final_result_data is None, all variations failed
    if final_result_data is None:
      msg = f"Google Maps API failed for all {len(attempted_variations)} address variations of '{destination}'"
      logfire.error(msg)
      await increment_request_counter_bg(self.redis_service, GMAPS_API_ERRORS_KEY)
      await self.mongo_service.log_error_to_db(
          service_name="LocationService._get_distance_from_google",
          error_type="GoogleMapsAPIAllVariationsFailed",
          message=msg,
          details={
              "origin": origin,
              "original_destination": destination,
              "attempted_variations": attempted_variations,
              "total_variations_tried": len(attempted_variations),
          },
      )

    return final_result_data

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
    Enhanced to handle complex address formats.
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

      # Extract structured components from the address
      components = extract_location_components(delivery_location)

      # Check state component first (most reliable)
      if components["state"] and components["state"].upper() in valid_codes:
        logfire.info(
            f"Location '{delivery_location}' is in service area (extracted state code: {components['state']})")
        return True

      # Extract state information from delivery location using multiple approaches
      location_upper = delivery_location.upper()
      location_lower = delivery_location.lower()

      # Check for state codes (e.g., "CA", "TX", "NY") - enhanced pattern
      state_code_pattern = r'\b([A-Z]{2})\b'
      code_matches = re.findall(state_code_pattern, location_upper)

      for code in code_matches:
        if code in valid_codes:
          logfire.info(
              f"Location '{delivery_location}' is in service area (found state code: {code})")
          return True

      # Check for full state names (with word boundaries)
      for state in valid_states:
        # Use word boundary regex for more accurate matching
        state_pattern = r'\b' + re.escape(state) + r'\b'
        if re.search(state_pattern, location_lower):
          logfire.info(
              f"Location '{delivery_location}' is in service area (found state name: {state})")
          return True

      # Additional checks for abbreviated address parts
      address_parts = [part.strip() for part in delivery_location.split(',')]
      for part in address_parts:
        part_upper = part.upper().strip()
        part_lower = part.lower().strip()

        # Check if any part is exactly a state code
        if part_upper in valid_codes:
          logfire.info(
              f"Location '{delivery_location}' is in service area (address part state code: {part_upper})")
          return True

        # Check if any part contains a state name
        if part_lower in valid_states:
          logfire.info(
              f"Location '{delivery_location}' is in service area (address part state name: {part_lower})")
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
