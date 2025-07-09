# filepath: app/services/mongo/location/operations.py
import logfire
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from app.models.mongo.location import LocationDocument, LocationStatus
from app.services.mongo.collections.names import LOCATION_COLLECTION


class LocationOperations:
  """Handles MongoDB operations for location collection."""

  def __init__(self, db):
    self.db = db

  async def create_location(self, location_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates a new location document in the location collection.

    Args:
        location_data: Dictionary containing location data

    Returns:
        Location ID if successful, None otherwise
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      # Create LocationDocument to validate data
      location_doc = LocationDocument(**location_data)

      # Prepare document for insertion (use model_dump for Pydantic v2)
      doc_dict = location_doc.model_dump()
      doc_dict["_id"] = doc_dict.pop("id")  # Use id as _id
      doc_dict["created_at"] = datetime.now(timezone.utc)
      doc_dict["updated_at"] = datetime.now(timezone.utc)

      # Insert the document
      result = await collection.insert_one(doc_dict)

      if result.inserted_id:
        logfire.info(f"Location created successfully",
                     location_id=str(result.inserted_id))
        return str(result.inserted_id)
      else:
        logfire.error("Failed to create location: no ID returned")
        return None

    except Exception as e:
      logfire.error(f"Error creating location: {e}", exc_info=True)
      return None

  async def update_location(self, location_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Updates an existing location document.

    Args:
        location_id: Location ID to update
        update_data: Dictionary containing fields to update

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      # Add updated_at timestamp
      update_data["updated_at"] = datetime.now(timezone.utc)

      # Perform the update
      result = await collection.update_one(
          {"_id": location_id},
          {"$set": update_data}
      )

      if result.matched_count > 0:
        logfire.info(f"Location updated successfully", location_id=location_id)
        return True
      else:
        logfire.warn(f"No location found with ID: {location_id}")
        return False

    except Exception as e:
      logfire.error(
          f"Error updating location {location_id}: {e}", exc_info=True)
      return False

  async def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a location by ID.

    Args:
        location_id: Location ID to retrieve

    Returns:
        Location document if found, None otherwise
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      doc = await collection.find_one({"_id": location_id})

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved location", location_id=location_id)
        return doc
      else:
        logfire.info(f"Location not found", location_id=location_id)
        return None

    except Exception as e:
      logfire.error(
          f"Error retrieving location {location_id}: {e}", exc_info=True)
      return None

  async def get_location_by_address(self, delivery_location: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a location by delivery address (for caching purposes).

    Args:
        delivery_location: Delivery address to search for

    Returns:
        Location document if found, None otherwise
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      doc = await collection.find_one(
          {"delivery_location": delivery_location},
          sort=[("created_at", -1)]
      )

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved location by address",
                      delivery_location=delivery_location, location_id=doc["id"])
        return doc
      else:
        logfire.info(f"No location found for address",
                     delivery_location=delivery_location)
        return None

    except Exception as e:
      logfire.error(
          f"Error retrieving location by address {delivery_location}: {e}", exc_info=True)
      return None

  async def get_locations_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves locations for a specific contact.

    Args:
        contact_id: HubSpot contact ID
        limit: Maximum number of locations to return

    Returns:
        List of location documents
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      cursor = collection.find(
          {"contact_id": contact_id}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} locations for contact", contact_id=contact_id)
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving locations for contact {contact_id}: {e}", exc_info=True)
      return []

  async def get_locations_by_status(self, status: LocationStatus, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves locations by status.

    Args:
        status: Location status to filter by
        limit: Maximum number of locations to return

    Returns:
        List of location documents
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      cursor = collection.find(
          {"status": status.value}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} locations with status {status.value}")
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving locations by status {status.value}: {e}", exc_info=True)
      return []

  async def get_locations_by_service_area(self, within_service_area: bool, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves locations by service area status.

    Args:
        within_service_area: Whether to get locations within or outside service area
        limit: Maximum number of locations to return

    Returns:
        List of location documents
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      cursor = collection.find(
          {"within_service_area": within_service_area}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} locations within service area: {within_service_area}")
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving locations by service area {within_service_area}: {e}", exc_info=True)
      return []

  async def get_locations_paginated(
      self,
      page: int = 1,
      page_size: int = 10,
      status_filter: Optional[str] = None,
      within_service_area: Optional[bool] = None,
      sort_field: str = "created_at",
      sort_order: int = -1
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves paginated locations with optional filtering and sorting.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        status_filter: Optional status filter
        within_service_area: Optional service area filter
        sort_field: Field to sort by
        sort_order: Sort order (1 for ascending, -1 for descending)

    Returns:
        Tuple of (location documents, total count)
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      # Build query
      query = {}
      if status_filter:
        query["status"] = status_filter
      if within_service_area is not None:
        query["within_service_area"] = within_service_area

      # Calculate skip
      skip = (page - 1) * page_size

      # Get documents
      cursor = collection.find(query).sort(
          sort_field, sort_order).skip(skip).limit(page_size)
      docs = await cursor.to_list(length=page_size)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      # Get total count
      total_count = await collection.count_documents(query)

      logfire.debug(
          f"Retrieved {len(docs)} locations (page {page}, total {total_count})")
      return docs, total_count

    except Exception as e:
      logfire.error(
          f"Error retrieving paginated locations: {e}", exc_info=True)
      return [], 0

  async def update_location_status(self, location_id: str, status: LocationStatus, error_message: Optional[str] = None) -> bool:
    """
    Updates a location's status.

    Args:
        location_id: Location ID to update
        status: New status
        error_message: Error message if status is FAILED

    Returns:
        True if successful, False otherwise
    """
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == LocationStatus.SUCCESS:
      update_data["lookup_completed_at"] = datetime.now(timezone.utc)
      update_data["lookup_successful"] = True
    elif status == LocationStatus.FAILED:
      update_data["lookup_successful"] = False
    elif status == LocationStatus.FALLBACK_USED:
      update_data["fallback_used"] = True
      update_data["lookup_completed_at"] = datetime.now(timezone.utc)

    return await self.update_location(location_id, update_data)

  async def get_location_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about locations.

    Returns:
        Dictionary with location statistics
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      total_locations = await collection.count_documents({})

      # Count by status
      stats = {"total_locations": total_locations}

      for status in LocationStatus:
        count = await collection.count_documents({"status": status.value})
        stats[f"{status.value}_locations"] = count

      # Count by service area
      within_service_area = await collection.count_documents({"within_service_area": True})
      outside_service_area = await collection.count_documents({"within_service_area": False})
      stats["within_service_area"] = within_service_area
      stats["outside_service_area"] = outside_service_area

      # Count with fallback used
      fallback_used = await collection.count_documents({"fallback_used": True})
      stats["fallback_used"] = fallback_used

      logfire.debug(f"Retrieved location statistics", stats=stats)
      return stats

    except Exception as e:
      logfire.error(
          f"Error retrieving location statistics: {e}", exc_info=True)
      return {"total_locations": 0}

  async def delete_location(self, location_id: str) -> bool:
    """
    Deletes a location by ID.

    Args:
        location_id: Location ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[LOCATION_COLLECTION]

      result = await collection.delete_one({"_id": location_id})

      if result.deleted_count > 0:
        logfire.info(f"Location deleted successfully", location_id=location_id)
        return True
      else:
        logfire.warn(f"No location found to delete", location_id=location_id)
        return False

    except Exception as e:
      logfire.error(
          f"Error deleting location {location_id}: {e}", exc_info=True)
      return False

  # === Pagination Methods ===
  async def get_recent_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Gets recent locations with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting recent locations: {str(e)}")
      return []

  async def get_oldest_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Gets oldest locations with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({})
      cursor = cursor.sort("created_at", 1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting oldest locations: {str(e)}")
      return []

  async def get_successful_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Gets successful locations with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({"status": "success"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting successful locations: {str(e)}")
      return []

  async def get_failed_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Gets failed locations with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({"status": "failed"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting failed locations: {str(e)}")
      return []

  async def get_pending_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Gets pending locations with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({"status": "pending"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting pending locations: {str(e)}")
      return []

  async def get_locations_by_distance(self, ascending: bool = True, offset: int = 0) -> List[LocationDocument]:
    """Gets locations sorted by distance with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find(
          {"distance_miles": {"$exists": True, "$ne": None}})
      cursor = cursor.sort("distance_miles", 1 if ascending else -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting locations by distance: {str(e)}")
      return []

  async def get_locations_by_branch(self, branch: str, offset: int = 0) -> List[LocationDocument]:
    """Gets locations by branch with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({"nearest_branch": branch})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting locations by branch: {str(e)}")
      return []

  async def get_locations_with_fallback(self, offset: int = 0) -> List[LocationDocument]:
    """Gets locations that used fallback method with pagination."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      cursor = collection.find({"fallback_used": True})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      locations = []
      async for result in cursor:
        result.pop("_id", None)
        locations.append(LocationDocument(**result))

      return locations
    except Exception as e:
      logfire.error(f"Error getting locations with fallback: {str(e)}")
      return []

  async def get_location_by_id(self, location_id: str) -> Optional[LocationDocument]:
    """Gets a single location by ID."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      result = await collection.find_one({"id": location_id})

      if result:
        result.pop("_id", None)
        return LocationDocument(**result)
      return None
    except Exception as e:
      logfire.error(f"Error getting location by ID: {str(e)}")
      return None

  # === Count Methods ===
  async def count_all_locations(self) -> int:
    """Counts all locations."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      return await collection.count_documents({})
    except Exception as e:
      logfire.error(f"Error counting all locations: {str(e)}")
      return 0

  async def count_locations_by_status(self, status: str) -> int:
    """Counts locations by status."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      return await collection.count_documents({"status": status})
    except Exception as e:
      logfire.error(f"Error counting locations by status: {str(e)}")
      return 0

  async def count_locations_by_branch(self, branch: str) -> int:
    """Counts locations by branch."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      return await collection.count_documents({"nearest_branch": branch})
    except Exception as e:
      logfire.error(f"Error counting locations by branch: {str(e)}")
      return 0

  async def count_locations_with_fallback(self) -> int:
    """Counts locations that used fallback method."""
    try:
      collection = self.db[LOCATION_COLLECTION]
      return await collection.count_documents({"fallback_used": True})
    except Exception as e:
      logfire.error(f"Error counting locations with fallback: {str(e)}")
      return 0
