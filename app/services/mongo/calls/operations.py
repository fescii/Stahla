# filepath: app/services/mongo/calls/operations.py
import logfire
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from app.models.mongo.calls import CallDocument, CallStatus
from app.services.mongo.collections.names import CALLS_COLLECTION


class CallsOperations:
  """Handles MongoDB operations for calls collection."""

  def __init__(self, db):
    self.db = db

  async def create_call(self, call_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates a new call document in the calls collection.

    Args:
        call_data: Dictionary containing call data

    Returns:
        Call ID if successful, None otherwise
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      # Create CallDocument to validate data
      call_doc = CallDocument(**call_data)

      # Prepare document for insertion
      doc_dict = call_doc.model_dump()
      doc_dict["_id"] = doc_dict.pop("id")  # Use id as _id
      doc_dict["created_at"] = datetime.now(timezone.utc)
      doc_dict["updated_at"] = datetime.now(timezone.utc)

      # Insert the document
      result = await collection.insert_one(doc_dict)

      if result.inserted_id:
        logfire.info(f"Call created successfully",
                     call_id=str(result.inserted_id))
        return str(result.inserted_id)
      else:
        logfire.error("Failed to create call: no ID returned")
        return None

    except Exception as e:
      logfire.error(f"Error creating call: {e}", exc_info=True)
      return None

  async def update_call(self, call_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Updates an existing call document.

    Args:
        call_id: Call ID to update
        update_data: Dictionary containing fields to update

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      # Add updated_at timestamp
      update_data["updated_at"] = datetime.now(timezone.utc)

      # Perform the update
      result = await collection.update_one(
          {"_id": call_id},
          {"$set": update_data}
      )

      if result.matched_count > 0:
        logfire.info(f"Call updated successfully", call_id=call_id)
        return True
      else:
        logfire.warn(f"No call found with ID: {call_id}")
        return False

    except Exception as e:
      logfire.error(f"Error updating call {call_id}: {e}", exc_info=True)
      return False

  async def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a call by ID.

    Args:
        call_id: Call ID to retrieve

    Returns:
        Call document if found, None otherwise
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      doc = await collection.find_one({"_id": call_id})

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved call", call_id=call_id)
        return doc
      else:
        logfire.info(f"Call not found", call_id=call_id)
        return None

    except Exception as e:
      logfire.error(f"Error retrieving call {call_id}: {e}", exc_info=True)
      return None

  async def get_call_by_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent call for a contact.

    Args:
        contact_id: HubSpot contact ID

    Returns:
        Call document if found, None otherwise
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      doc = await collection.find_one(
          {"contact_id": contact_id},
          sort=[("created_at", -1)]
      )

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved call for contact",
                      contact_id=contact_id, call_id=doc["id"])
        return doc
      else:
        logfire.info(f"No call found for contact", contact_id=contact_id)
        return None

    except Exception as e:
      logfire.error(
          f"Error retrieving call for contact {contact_id}: {e}", exc_info=True)
      return None

  async def get_calls_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves calls for a specific contact.

    Args:
        contact_id: HubSpot contact ID
        limit: Maximum number of calls to return

    Returns:
        List of call documents
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      cursor = collection.find(
          {"contact_id": contact_id}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} calls for contact", contact_id=contact_id)
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving calls for contact {contact_id}: {e}", exc_info=True)
      return []

  async def get_calls_by_status(self, status: CallStatus, limit: int = 10, offset: int = 0) -> List[CallDocument]:
    """
    Retrieves calls by status with pagination.

    Args:
        status: Call status to filter by
        limit: Maximum number of calls to return
        offset: Number of calls to skip

    Returns:
        List of CallDocument objects
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      cursor = collection.find(
          {"status": status.value}
      ).sort("created_at", -1).skip(offset).limit(limit)

      results = await cursor.to_list(length=limit)

      calls = []
      for result in results:
        result.pop("_id", None)
        calls.append(CallDocument(**result))

      logfire.debug(f"Retrieved {len(calls)} calls with status {status.value}")
      return calls

    except Exception as e:
      logfire.error(
          f"Error retrieving calls by status {status.value}: {e}", exc_info=True)
      return []

  async def get_calls_paginated(
      self,
      page: int = 1,
      page_size: int = 10,
      status_filter: Optional[str] = None,
      sort_field: str = "created_at",
      sort_order: int = -1
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves paginated calls with optional filtering and sorting.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        status_filter: Optional status filter
        sort_field: Field to sort by
        sort_order: Sort order (1 for ascending, -1 for descending)

    Returns:
        Tuple of (call documents, total count)
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      # Build query
      query = {}
      if status_filter:
        query["status"] = status_filter

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
          f"Retrieved {len(docs)} calls (page {page}, total {total_count})")
      return docs, total_count

    except Exception as e:
      logfire.error(f"Error retrieving paginated calls: {e}", exc_info=True)
      return [], 0

  async def update_call_status(self, call_id: str, status: CallStatus, error_message: Optional[str] = None) -> bool:
    """
    Updates a call's status.

    Args:
        call_id: Call ID to update
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

    if status == CallStatus.COMPLETED:
      update_data["call_completed_at"] = datetime.now(timezone.utc)

    return await self.update_call(call_id, update_data)

  async def get_call_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about calls.

    Returns:
        Dictionary with call statistics
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      total_calls = await collection.count_documents({})

      # Count by status
      stats = {"total_calls": total_calls}

      for status in CallStatus:
        count = await collection.count_documents({"status": status.value})
        stats[f"{status.value}_calls"] = count

      logfire.debug(f"Retrieved call statistics", stats=stats)
      return stats

    except Exception as e:
      logfire.error(f"Error retrieving call statistics: {e}", exc_info=True)
      return {"total_calls": 0}

  async def delete_call(self, call_id: str) -> bool:
    """
    Deletes a call by ID.

    Args:
        call_id: Call ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[CALLS_COLLECTION]

      result = await collection.delete_one({"_id": call_id})

      if result.deleted_count > 0:
        logfire.info(f"Call deleted successfully", call_id=call_id)
        return True
      else:
        logfire.warn(f"No call found to delete", call_id=call_id)
        return False

    except Exception as e:
      logfire.error(f"Error deleting call {call_id}: {e}", exc_info=True)
      return False

  # Pagination query methods
  async def get_recent_calls(self, limit: int = 10, offset: int = 0) -> List[CallDocument]:
    """Get recent calls ordered by creation date (newest first)."""
    try:
      collection = self.db[CALLS_COLLECTION]
      cursor = collection.find().sort("created_at", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      calls = []
      for result in results:
        result.pop("_id", None)
        calls.append(CallDocument(**result))
      return calls
    except Exception as e:
      logfire.error(f"Error fetching recent calls: {e}", exc_info=True)
      return []

  async def get_oldest_calls(self, limit: int = 10, offset: int = 0) -> List[CallDocument]:
    """Get oldest calls ordered by creation date (oldest first)."""
    try:
      collection = self.db[CALLS_COLLECTION]
      cursor = collection.find().sort("created_at", 1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      calls = []
      for result in results:
        result.pop("_id", None)
        calls.append(CallDocument(**result))
      return calls
    except Exception as e:
      logfire.error(f"Error fetching oldest calls: {e}", exc_info=True)
      return []

  async def get_calls_by_duration(self, limit: int = 10, offset: int = 0, ascending: bool = True) -> List[CallDocument]:
    """Get calls ordered by duration."""
    try:
      collection = self.db[CALLS_COLLECTION]
      sort_direction = 1 if ascending else -1
      cursor = collection.find().sort(
          "call_duration", sort_direction).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      calls = []
      for result in results:
        result.pop("_id", None)
        calls.append(CallDocument(**result))
      return calls
    except Exception as e:
      logfire.error(f"Error fetching calls by duration: {e}", exc_info=True)
      return []

  async def get_calls_by_source(self, source: str, limit: int = 10, offset: int = 0) -> List[CallDocument]:
    """Get calls filtered by source."""
    try:
      collection = self.db[CALLS_COLLECTION]
      cursor = collection.find({"source": source}).sort(
          "created_at", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      calls = []
      for result in results:
        result.pop("_id", None)
        calls.append(CallDocument(**result))
      return calls
    except Exception as e:
      logfire.error(f"Error fetching calls by source: {e}", exc_info=True)
      return []

  async def get_call_by_id(self, call_id: str) -> Optional[CallDocument]:
    """Get a single call by ID."""
    try:
      collection = self.db[CALLS_COLLECTION]
      result = await collection.find_one({"id": call_id})

      if result:
        result.pop("_id", None)
        return CallDocument(**result)
      return None
    except Exception as e:
      logfire.error(f"Error retrieving call by ID: {e}", exc_info=True)
      return None

  # Count methods for pagination
  async def count_calls(self) -> int:
    """Count total calls."""
    try:
      collection = self.db[CALLS_COLLECTION]
      return await collection.count_documents({})
    except Exception as e:
      logfire.error(f"Error counting calls: {e}", exc_info=True)
      return 0

  async def count_calls_by_status(self, status: CallStatus) -> int:
    """Count calls by status."""
    try:
      collection = self.db[CALLS_COLLECTION]
      return await collection.count_documents({"status": status.value})
    except Exception as e:
      logfire.error(f"Error counting calls by status: {e}", exc_info=True)
      return 0

  async def count_calls_by_source(self, source: str) -> int:
    """Count calls by source."""
    try:
      collection = self.db[CALLS_COLLECTION]
      return await collection.count_documents({"source": source})
    except Exception as e:
      logfire.error(f"Error counting calls by source: {e}", exc_info=True)
      return 0
