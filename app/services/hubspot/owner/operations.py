# app/services/hubspot/owner/operations.py

import asyncio
import logging
from typing import Any, Dict, List, Optional

from hubspot.crm.objects.exceptions import ApiException as ObjectApiException

from app.models.hubspot import HubSpotOwner
from app.services.hubspot.utils.helpers import _handle_api_error

logger = logging.getLogger(__name__)


class OwnerOperations:
  def __init__(self, manager):
    self.manager = manager

  async def get_all(self, limit: int = 100) -> List[HubSpotOwner]:
    """Get all owners from HubSpot."""
    return await self.get_owners(limit)

  async def get_owners(self, limit: int = 100) -> List[HubSpotOwner]:
    """Get all owners with caching."""
    # Caching strategy: cache the full list if fetched.
    # If called frequently with different limits, this might not be optimal.
    # For now, assumes one primary call to get all owners.
    full_list_cache_key = "all_owners_complete_list"
    if full_list_cache_key in self.manager.owners_cache:
      logger.debug("Returning full cached list of owners")
      return self.manager.owners_cache[full_list_cache_key]

    logger.debug(f"Fetching all owners (paginating with limit: {limit})")
    all_owners_list = []
    current_after = None

    try:
      while True:
        api_response = await asyncio.to_thread(
            self.manager.client.crm.owners.owners_api.get_page,
            limit=limit, after=current_after
        )
        owners_page = [
            HubSpotOwner(**owner.to_dict()) for owner in api_response.results
        ]
        all_owners_list.extend(owners_page)

        if (
            api_response.paging
            and api_response.paging.next
            and api_response.paging.next.after
        ):
          current_after = api_response.paging.next.after
          logger.debug(
              f"Fetching next page of owners, after: {current_after}"
          )
        else:
          break

      self.manager.owners_cache[full_list_cache_key] = all_owners_list
      logger.info(f"Fetched and cached {len(all_owners_list)} owners.")
      return all_owners_list
    except ObjectApiException as e:
      await _handle_api_error(e, "owners retrieval")
      return []
    except Exception as e:
      await _handle_api_error(e, "owners retrieval")
      return []

  async def get_by_email(self, email: str) -> Optional[HubSpotOwner]:
    """Get an owner by email address."""
    return await self.get_owner_by_email(email)

  async def get_owner_by_email(self, email: str) -> Optional[HubSpotOwner]:
    """Get an owner by email with caching."""
    logger.debug(f"Getting owner by email: {email}")
    cache_key = f"owner_email_{email.lower()}"  # Normalize email for cache key
    cached_owner = self.manager.owners_cache.get(cache_key)
    if cached_owner:
      logger.debug(f"Returning cached owner for email: {email}")
      return cached_owner

    try:
      api_response = await asyncio.to_thread(
          self.manager.client.crm.owners.owners_api.get_page,
          email=email, limit=1
      )
      if api_response.results:
        owner_data = HubSpotOwner(**api_response.results[0].to_dict())
        self.manager.owners_cache[cache_key] = owner_data
        logger.info(
            f"Found owner by email via API: {email} -> ID {owner_data.id}"
        )
        return owner_data
      else:
        logger.warning(
            f"Owner with email '{email}' not found via direct API query. Consider checking all owners if necessary."
        )
        return None
    except ObjectApiException as e:
      await _handle_api_error(e, "get owner by email", email)
    except Exception as e:
      await _handle_api_error(e, "get owner by email", email)

    return None

  async def get_by_id(self, owner_id: str) -> Optional[HubSpotOwner]:
    """Get an owner by ID."""
    return await self.get_owner_by_id(owner_id)

  async def get_owner_by_id(self, owner_id: str) -> Optional[HubSpotOwner]:
    """Get an owner by ID with caching."""
    logger.debug(f"Getting owner by ID: {owner_id}")
    cache_key = f"owner_id_{owner_id}"
    cached_owner = self.manager.owners_cache.get(cache_key)
    if cached_owner:
      logger.debug(f"Returning cached owner for ID: {owner_id}")
      return cached_owner

    try:
      # First try to get from all owners cache
      all_owners = await self.get_owners()
      for owner in all_owners:
        if owner.id == owner_id:
          self.manager.owners_cache[cache_key] = owner
          logger.info(f"Found owner by ID: {owner_id}")
          return owner

      logger.warning(f"Owner with ID '{owner_id}' not found.")
      return None
    except Exception as e:
      await _handle_api_error(e, "get owner by id", owner_id)
      return None

  async def get_owner(self, identifier: str) -> Optional[HubSpotOwner]:
    """Get an owner by ID or email (auto-detect)."""
    if "@" in identifier:
      # Looks like an email
      return await self.get_owner_by_email(identifier)
    else:
      # Assume it's an ID
      return await self.get_owner_by_id(identifier)

  async def search_by_name(self, name: str) -> List[HubSpotOwner]:
    """Search owners by name (first name, last name, or full name)."""
    try:
      all_owners = await self.get_owners()
      matching_owners = []

      name_lower = name.lower()
      for owner in all_owners:
        # Check first name, last name, and full name
        first_name = getattr(owner, 'first_name', '') or ''
        last_name = getattr(owner, 'last_name', '') or ''
        full_name = f"{first_name} {last_name}".strip()

        if (name_lower in first_name.lower() or
            name_lower in last_name.lower() or
                name_lower in full_name.lower()):
          matching_owners.append(owner)

      logger.info(f"Found {len(matching_owners)} owners matching name: {name}")
      return matching_owners
    except Exception as e:
      await _handle_api_error(e, "search owners by name", name)
      return []

  async def get_active_owners(self) -> List[HubSpotOwner]:
    """Get only active owners."""
    try:
      all_owners = await self.get_owners()
      active_owners = [
          owner for owner in all_owners
          if getattr(owner, 'archived', False) is False
      ]
      logger.info(
          f"Found {len(active_owners)} active owners out of {len(all_owners)} total")
      return active_owners
    except Exception as e:
      await _handle_api_error(e, "get active owners")
      return []

  async def clear_cache(self) -> bool:
    """Clear the owners cache."""
    try:
      # Clear all owner-related cache entries
      keys_to_remove = [
          key for key in self.manager.owners_cache.keys()
          if key.startswith(('owner_', 'all_owners_'))
      ]
      for key in keys_to_remove:
        del self.manager.owners_cache[key]

      logger.info(f"Cleared {len(keys_to_remove)} owner cache entries")
      return True
    except Exception as e:
      logger.error(f"Error clearing owner cache: {e}")
      return False

  async def refresh_cache(self, limit: int = 100) -> List[HubSpotOwner]:
    """Clear cache and fetch fresh owner data."""
    await self.clear_cache()
    return await self.get_owners(limit)

  async def search_by_criteria(self, criteria: Dict[str, Any]) -> List[HubSpotOwner]:
    """Search owners by various criteria."""
    try:
      # Get all owners and filter them based on criteria
      all_owners = await self.get_owners()

      if not criteria:
        return all_owners

      filtered_owners = []
      for owner in all_owners:
        match = True
        for key, value in criteria.items():
          owner_value = getattr(owner, key, None)
          if owner_value is None:
            match = False
            break

          # Handle different comparison types
          if isinstance(value, str):
            # Case-insensitive string matching
            if str(owner_value).lower() != value.lower():
              match = False
              break
          elif owner_value != value:
            match = False
            break

        if match:
          filtered_owners.append(owner)

      logger.info(
          f"Found {len(filtered_owners)} owners matching criteria: {criteria}")
      return filtered_owners

    except Exception as e:
      logger.error(f"Error searching owners by criteria: {e}", exc_info=True)
      return []
