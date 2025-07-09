# filepath: app/services/mongo/errors/operations.py
import logfire
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from pymongo import ASCENDING, DESCENDING
from app.services.mongo.collections.names import ERROR_LOGS_COLLECTION


class ErrorOperations:
  """Handles MongoDB operations for error logging."""

  def __init__(self, db):
    self.db = db

  async def log_error_to_db(
      self,
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None,
      stack_trace: Optional[str] = None,
      request_context: Optional[Dict[str, Any]] = None
  ) -> Optional[str]:
    """
    Logs an error to the error_logs collection in MongoDB.

    Args:
        service_name: Name of the service where the error occurred
        error_type: Type of error (e.g., ValueError, HTTPException, CacheMiss)
        message: The error message
        details: Specific details about the error for debugging
        stack_trace: Optional stack trace if available
        request_context: Optional contextual information about the request

    Returns:
        String ID of the created error log document, or None if operation failed
    """
    if self.db is None:
      logfire.error("log_error_to_db: MongoDB database is not initialized.")
      return None

    collection = self.db[ERROR_LOGS_COLLECTION]
    current_time = datetime.now(timezone.utc)

    # Create error document based on ErrorLog model structure
    error_doc = {
        "_id": uuid.uuid4(),  # Generate a unique ID
        "timestamp": current_time,
        "service_name": service_name,
        "error_type": error_type,
        "error_message": message,
        "stack_trace": stack_trace,
        "request_context": request_context,
        "additional_data": details  # Use details parameter for additional_data field
    }

    try:
      result = await collection.insert_one(error_doc)
      error_id = str(result.inserted_id)
      logfire.info(
          f"Logged error to MongoDB: type={error_type}, service={service_name}, id={error_id}"
      )
      return error_id
    except Exception as e:
      logfire.error(
          f"Failed to log error to MongoDB: {e}. Original error: {message}",
          exc_info=True
      )
      return None

  async def get_error_logs(
      self,
      page: int = 1,
      page_size: int = 10,
      service_name_filter: Optional[str] = None,
      error_type_filter: Optional[str] = None,
      sort_field: str = "timestamp",
      sort_order: int = DESCENDING
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves error logs from MongoDB with pagination and filtering.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        service_name_filter: Optional service name filter
        error_type_filter: Optional error type filter
        sort_field: Field to sort by
        sort_order: Sort order (ASCENDING or DESCENDING)

    Returns:
        Tuple of (list of error log documents, total count)
    """
    if self.db is None:
      logfire.error("get_error_logs: MongoDB database is not initialized.")
      return [], 0

    collection = self.db[ERROR_LOGS_COLLECTION]

    # Build filter query
    filter_query = {}
    if service_name_filter:
      filter_query["service_name"] = {
          "$regex": service_name_filter, "$options": "i"}
    if error_type_filter:
      filter_query["error_type"] = {
          "$regex": error_type_filter, "$options": "i"}

    try:
      # Get total count
      total_count = await collection.count_documents(filter_query)

      # Calculate skip value
      skip = (page - 1) * page_size

      # Get paginated results
      cursor = collection.find(filter_query).sort(
          sort_field, sort_order).skip(skip).limit(page_size)
      error_logs = await cursor.to_list(length=page_size)

      # Convert ObjectId to string and rename _id to id for consistency with ErrorLog model
      for log in error_logs:
        log["id"] = str(log["_id"])
        del log["_id"]

      logfire.info(
          f"Retrieved {len(error_logs)} error logs (page {page}, total: {total_count})")
      return error_logs, total_count

    except Exception as e:
      logfire.error(f"Failed to retrieve error logs: {e}", exc_info=True)
      return [], 0
