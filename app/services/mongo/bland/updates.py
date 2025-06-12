# filepath: app/services/mongo/bland/updates.py
import logfire
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.models.blandlog import BlandCallStatus
from app.services.mongo.collections.names import BLAND_CALL_LOGS_COLLECTION


class BlandUpdates:
  """Handles MongoDB update operations for Bland AI call logs."""

  def __init__(self, db):
    self.db = db

  async def update_bland_call_log_internal(
      self,
      contact_id: str,
      update_data: Dict[str, Any]
  ) -> bool:
    """
    Updates a Bland call log document in MongoDB based on the contact_id.
    Used internally by BlandAIManager to update call status, errors, and other details.

    Args:
        contact_id: The HubSpot Contact ID used as _id in MongoDB
        update_data: MongoDB update operation document (e.g., {"$set": {...}, "$inc": {...}})

    Returns:
        True if the update was successful (or document was found), False otherwise
    """
    if self.db is None:
      logfire.error(
          "update_bland_call_log_internal: MongoDB database is not initialized.")
      return False

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]

    try:
      # Use _id for querying since that's how we store contact_id in MongoDB
      result = await collection.update_one({"_id": contact_id}, update_data)

      if result.matched_count > 0:
        logfire.info(
            f"Updated Bland call log for contact_id: {contact_id}. "
            f"Modified: {result.modified_count}"
        )
        return True
      else:
        logfire.warning(
            f"No Bland call log found to update for contact_id: {contact_id}"
        )
        return False
    except Exception as e:
      logfire.error(
          f"Failed to update Bland call log for contact_id {contact_id}: {e}",
          exc_info=True
      )
      return False

  async def update_bland_call_log_completion(
      self,
      contact_id: str,
      call_id_bland: str,
      status: BlandCallStatus,
      transcript_payload: List[Dict[str, Any]],
      summary_text: Optional[str] = None,
      classification_payload: Optional[Dict[str, Any]] = None,
      full_webhook_payload: Optional[Dict[str, Any]] = None,
      call_completed_timestamp: Optional[datetime] = None,
      bland_processing_result_payload: Optional[Dict[str, Any]] = None,
      processing_status_message: Optional[str] = None
  ) -> bool:
    """
    Updates a Bland call log with completion data received from webhook.

    Args:
        contact_id: The HubSpot Contact ID used as _id in MongoDB
        call_id_bland: The Bland.ai call ID for verification
        status: The new status (typically COMPLETED)
        transcript_payload: The transcript data from Bland.ai
        summary_text: Optional summary text extracted from the transcript
        classification_payload: Optional classification data for the call
        full_webhook_payload: Optional full webhook payload for reference
        call_completed_timestamp: When the call was completed
        bland_processing_result_payload: Results from processing the transcript
        processing_status_message: Status message from transcript processing

    Returns:
        True if the update was successful, False otherwise
    """
    if self.db is None:
      logfire.error(
          "update_bland_call_log_completion: MongoDB database is not initialized.")
      return False

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]
    current_time = datetime.now(timezone.utc)
    completed_time = call_completed_timestamp or current_time

    # Build update document
    update_data = {
        "$set": {
            "status": status.value,
            "updated_at": current_time,
            "completed_at": completed_time,
            "transcript": transcript_payload,  # Store the full transcript payload
            "summary": summary_text,
            "analysis": {
                "classification": classification_payload,
                "processing_result": bland_processing_result_payload,
                "processing_status": processing_status_message
            },
            "full_webhook_payload": full_webhook_payload
        }
    }

    try:
      # Use both _id (contact_id) and call_id_bland for verification to ensure
      # we're updating the correct document
      query = {
          "_id": contact_id,
          "call_id_bland": call_id_bland
      }

      result = await collection.update_one(query, update_data)

      if result.matched_count > 0:
        logfire.info(
            f"Updated Bland call log completion for contact_id: {contact_id}, "
            f"call_id_bland: {call_id_bland}. Modified: {result.modified_count}"
        )
        return True
      else:
        # If no match with both fields, try with just contact_id (fallback)
        fallback_result = await collection.update_one(
            {"_id": contact_id}, update_data
        )

        if fallback_result.matched_count > 0:
          logfire.warning(
              f"Updated Bland call log with fallback query (contact_id only) for "
              f"contact_id: {contact_id}. The stored call_id_bland may not match "
              f"the provided call_id_bland: {call_id_bland}"
          )
          return True
        else:
          logfire.error(
              f"No Bland call log found to update for contact_id: {contact_id}, "
              f"call_id_bland: {call_id_bland}"
          )
          return False
    except Exception as e:
      logfire.error(
          f"Failed to update Bland call log completion for contact_id {contact_id}, "
          f"call_id_bland {call_id_bland}: {e}",
          exc_info=True
      )
      return False

  async def log_bland_call_attempt(
      self,
      contact_id: str,
      phone_number: str,
      task: Optional[str] = None,
      pathway_id_used: Optional[str] = None,
      initial_status: BlandCallStatus = BlandCallStatus.PENDING,
      call_id_bland: Optional[str] = None,
      retry_of_call_id: Optional[str] = None,
      retry_reason: Optional[str] = None,
      voice_id: Optional[str] = None,
      webhook_url: Optional[str] = None,
      max_duration: Optional[int] = 12,
      request_data_variables: Optional[Dict[str, Any]] = None,
      transfer_phone_number: Optional[str] = None
  ) -> bool:
    """
    Logs an initial Bland.ai call attempt to MongoDB.
    Creates a new document or updates an existing one if the contact_id already exists.

    Args:
        contact_id: The HubSpot Contact ID to use as _id in MongoDB
        phone_number: The phone number being called
        task: The task description if pathway_id is not used
        pathway_id_used: The Bland.ai pathway ID used for the call, if any
        initial_status: The initial status of the call (default: PENDING)
        call_id_bland: The Bland.ai call ID if already received
        retry_of_call_id: The original call ID if this is a retry
        retry_reason: Reason for retry if applicable
        voice_id: The voice ID used for the call
        webhook_url: The webhook URL configured for Bland.ai
        max_duration: Maximum duration of the call in minutes
        request_data_variables: Variables passed to Bland.ai in request_data
        transfer_phone_number: Transfer phone number for the call

    Returns:
        True if the log was created successfully, False otherwise
    """
    if self.db is None:
      logfire.error(
          "log_bland_call_attempt: MongoDB database is not initialized.")
      return False

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]
    current_time = datetime.now(timezone.utc)

    # Prepare document for insertion or update
    document = {
        "phone_number": phone_number,
        "status": initial_status.value,
        "created_at": current_time,
        "updated_at": current_time,
        "task": task,
        "pathway_id_used": pathway_id_used,
        "call_id_bland": call_id_bland,
        "webhook_url": webhook_url,
        "voice_id": voice_id,
        "max_duration": max_duration,
        "transfer_phone_number": transfer_phone_number,
        "request_data_variables": request_data_variables or {}
    }

    # Add retry information if this is a retry
    if retry_of_call_id:
      document["retry_of_call_id"] = retry_of_call_id
      document["retry_reason"] = retry_reason
      # Increment retry_count field if this is a retry
      update_operation = {
          "$set": document,
          "$inc": {"retry_count": 1},
          "$setOnInsert": {"_id": contact_id}
      }
    else:
      # For new calls (not retries), set retry_count to 0
      document["retry_count"] = 0
      document["retry_of_call_id"] = None
      document["retry_reason"] = None
      update_operation = {
          "$set": document,
          "$setOnInsert": {"_id": contact_id, "created_at": current_time}
      }

    try:
      # Use upsert to create a new document or update an existing one
      result = await collection.update_one(
          {"_id": contact_id},
          update_operation,
          upsert=True
      )

      if result.upserted_id:
        logfire.info(
            f"Created new Bland call log for contact_id: {contact_id}, "
            f"phone_number: {phone_number}, initial_status: {initial_status.value}"
        )
      else:
        logfire.info(
            f"Updated existing Bland call log for contact_id: {contact_id}, "
            f"phone_number: {phone_number}, status set to: {initial_status.value}"
        )

      return True
    except Exception as e:
      logfire.error(
          f"Failed to log Bland call attempt for contact_id {contact_id}: {e}",
          exc_info=True
      )
      return False
