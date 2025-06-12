# filepath: app/services/mongo/errors/operations.py
import logfire
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
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
