# filepath: app/services/mongo/bland/operations.py
import logfire
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from app.models.blandlog import BlandCallStatus
from app.services.mongo.collections.names import BLAND_CALL_LOGS_COLLECTION


class BlandOperations:
  """Handles MongoDB operations for Bland AI call logs."""

  def __init__(self, db):
    self.db = db

  async def get_bland_calls(
      self,
      page: int,
      page_size: int,
      status_filter: Optional[str],
      sort_field: str,
      sort_order: int,
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves a paginated list of Bland call logs, optionally filtered by status
    and sorted by a specified field and order.
    """
    collection = self.db[BLAND_CALL_LOGS_COLLECTION]
    query = {}
    if status_filter:
      query["status"] = status_filter

    # Calculate skip for pagination
    skip = (page - 1) * page_size

    try:
      cursor = (
          collection.find(query)
          .sort(sort_field, sort_order)
          .skip(skip)
          .limit(page_size)
      )
      items = await cursor.to_list(length=page_size)

      # Convert ObjectId to string for JSON serialization if needed
      # and ensure all necessary fields are present or defaulted.
      processed_items = []
      for item_from_db in items:
        # Create a new dictionary to avoid modifying the original item_from_db if it's used elsewhere
        item_for_model = dict(item_from_db)
        # Map _id to id and convert to string
        item_for_model["id"] = str(item_for_model.pop("_id"))

        # Ensure other fields expected by BlandCallLog model are present
        item_for_model.setdefault("call_id_bland", None)
        item_for_model.setdefault("retry_of_call_id", None)
        item_for_model.setdefault("retry_reason", None)
        item_for_model.setdefault("pathway_id_used", None)
        item_for_model.setdefault("voice_id", None)
        item_for_model.setdefault("transfer_phone_number", None)
        item_for_model.setdefault("webhook_url", None)
        item_for_model.setdefault(
            "request_data_variables", {})  # Default to empty dict
        item_for_model.setdefault("max_duration", None)
        item_for_model.setdefault("analysis", None)
        item_for_model.setdefault("summary", None)
        item_for_model.setdefault("transcript", None)
        item_for_model.setdefault("recordings", [])  # Default to empty list
        item_for_model.setdefault("error_message", None)
        item_for_model.setdefault("duration", 0.0)  # Default to 0.0
        item_for_model.setdefault("cost", 0.0)  # Default to 0.0
        item_for_model.setdefault("answered_by", None)
        item_for_model.setdefault("ended_reason", None)
        item_for_model.setdefault("external_id", None)
        item_for_model.setdefault("from_number", None)
        item_for_model.setdefault(
            "to_number", item_for_model.get("phone_number"))
        item_for_model.setdefault("batch_id", None)
        # Ensure all fields from BlandCallStatus are potentially present or defaulted if not already
        for status_member in BlandCallStatus:
          # Example, adjust if model uses different naming
          item_for_model.setdefault(status_member.name.lower(), None)

        processed_items.append(item_for_model)

      total_items = await collection.count_documents(query)
      logfire.debug(
          f"Retrieved {len(processed_items)} bland call logs from DB. Total matching query: {total_items}. Page: {page}, PageSize: {page_size}"
      )
      return processed_items, total_items
    except Exception as e:
      logfire.error(
          f"Failed to retrieve bland call logs from MongoDB: {e}", exc_info=True
      )
      return [], 0

  async def get_bland_call_log(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single Bland call log by contact_id.

    Args:
        contact_id: The HubSpot Contact ID used as _id in MongoDB

    Returns:
        A dictionary with the call log data or None if not found
    """
    if self.db is None:
      logfire.error("get_bland_call_log: MongoDB database is not initialized.")
      return None

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]

    try:
      item = await collection.find_one({"_id": contact_id})
      if item:
        # Create a new dictionary to avoid modifying the original item if it's used elsewhere
        item_dict = dict(item)
        # Map _id to id and convert to string
        item_dict["id"] = str(item_dict.pop("_id"))

        # Ensure other fields expected by BlandCallLog model are present
        item_dict.setdefault("call_id_bland", None)
        item_dict.setdefault("retry_of_call_id", None)
        item_dict.setdefault("retry_reason", None)
        item_dict.setdefault("pathway_id_used", None)
        item_dict.setdefault("voice_id", None)
        item_dict.setdefault("transfer_phone_number", None)
        item_dict.setdefault("webhook_url", None)
        item_dict.setdefault("request_data_variables", {})
        item_dict.setdefault("max_duration", None)
        item_dict.setdefault("analysis", None)
        item_dict.setdefault("summary", None)
        item_dict.setdefault("transcript", None)
        item_dict.setdefault("recordings", [])
        item_dict.setdefault("error_message", None)
        item_dict.setdefault("duration", 0.0)
        item_dict.setdefault("cost", 0.0)
        item_dict.setdefault("answered_by", None)
        item_dict.setdefault("ended_reason", None)
        item_dict.setdefault("external_id", None)
        item_dict.setdefault("from_number", None)
        item_dict.setdefault("to_number", item_dict.get("phone_number"))
        item_dict.setdefault("batch_id", None)

        # Ensure all fields from BlandCallStatus are potentially present or defaulted
        for status_member in BlandCallStatus:
          item_dict.setdefault(status_member.name.lower(), None)

        logfire.debug(f"Retrieved bland call log for contact_id: {contact_id}")
        return item_dict

      logfire.info(f"No bland call log found for contact_id: {contact_id}")
      return None

    except Exception as e:
      logfire.error(
          f"Failed to retrieve bland call log from MongoDB for contact_id {contact_id}: {e}",
          exc_info=True
      )
      return None

  async def get_bland_call_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about Bland call logs, including counts by status.
    Returns a dictionary with total_calls and counts for each status in BlandCallStatus.

    Returns:
        Dictionary with keys: total_calls, pending_calls, completed_calls, failed_calls, retrying_calls
    """
    if self.db is None:
      logfire.error(
          "get_bland_call_stats: MongoDB database is not initialized.")
      return {
          "total_calls": 0,
          "pending_calls": 0,
          "completed_calls": 0,
          "failed_calls": 0,
          "retrying_calls": 0
      }

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]

    try:
      # Get total count of calls
      total_calls = await collection.count_documents({})

      # Get count for each status
      pending_calls = await collection.count_documents(
          {"status": BlandCallStatus.PENDING.value})
      completed_calls = await collection.count_documents(
          {"status": BlandCallStatus.COMPLETED.value})
      failed_calls = await collection.count_documents(
          {"status": BlandCallStatus.FAILED.value})
      retrying_calls = await collection.count_documents(
          {"status": BlandCallStatus.RETRYING.value})

      stats = {
          "total_calls": total_calls,
          "pending_calls": pending_calls,
          "completed_calls": completed_calls,
          "failed_calls": failed_calls,
          "retrying_calls": retrying_calls
      }

      logfire.info(f"Retrieved Bland call statistics: {stats}")
      return stats
    except Exception as e:
      logfire.error(
          f"Failed to retrieve Bland call statistics from MongoDB: {e}", exc_info=True)
      # Return zeroes for all counts in case of error
      return {
          "total_calls": 0,
          "pending_calls": 0,
          "completed_calls": 0,
          "failed_calls": 0,
          "retrying_calls": 0
      }
