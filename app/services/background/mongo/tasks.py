# filepath: app/services/background/mongo/tasks.py
"""Background tasks for MongoDB operations."""

import logging
import uuid
from typing import Any, Optional, Dict
from datetime import datetime, timezone

from app.models.mongo.quotes import QuoteStatus
from app.models.mongo.calls import CallStatus
from app.models.mongo.classify import ClassifyStatus
from app.models.mongo.location import LocationStatus
from app.models.mongo.emails import EmailStatus, EmailCategory

logger = logging.getLogger(__name__)


async def log_quote_bg(mongo_service, quote_data: Dict[str, Any], background_task_id: Optional[str] = None):
  """Background task to log a quote to MongoDB."""
  try:
    if not quote_data.get("id"):
      quote_data["id"] = f"quote_{uuid.uuid4()}"

    if background_task_id:
      quote_data["background_task_id"] = background_task_id

    result = await mongo_service.create_quote(quote_data)
    if result:
      logger.info(f"Quote logged successfully in background: {result}")
    else:
      logger.error("Failed to log quote in background")
  except Exception as e:
    logger.error(f"Error logging quote in background: {e}", exc_info=True)


async def log_call_bg(mongo_service, call_data: Dict[str, Any], background_task_id: Optional[str] = None):
  """Background task to log a call to MongoDB."""
  try:
    if not call_data.get("id"):
      call_data["id"] = str(uuid.uuid4())

    if background_task_id:
      call_data["background_task_id"] = background_task_id

    result = await mongo_service.create_call(call_data)
    if result:
      logger.info(f"Call logged successfully in background: {result}")
    else:
      logger.error("Failed to log call in background")
  except Exception as e:
    logger.error(f"Error logging call in background: {e}", exc_info=True)


async def log_classify_bg(mongo_service, classify_data: Dict[str, Any], background_task_id: Optional[str] = None):
  """Background task to log a classification to MongoDB."""
  try:
    if not classify_data.get("id"):
      classify_data["id"] = str(uuid.uuid4())

    if background_task_id:
      classify_data["background_task_id"] = background_task_id

    result = await mongo_service.create_classify(classify_data)
    if result:
      logger.info(
          f"Classification logged successfully in background: {result}")
    else:
      logger.error("Failed to log classification in background")
  except Exception as e:
    logger.error(
        f"Error logging classification in background: {e}", exc_info=True)


async def log_location_bg(mongo_service, location_data: Dict[str, Any], background_task_id: Optional[str] = None):
  """Background task to log a location lookup to MongoDB."""
  try:
    if not location_data.get("id"):
      location_data["id"] = str(uuid.uuid4())

    if background_task_id:
      location_data["background_task_id"] = background_task_id

    result = await mongo_service.create_location(location_data)
    if result:
      logger.info(f"Location logged successfully in background: {result}")
    else:
      logger.error("Failed to log location in background")
  except Exception as e:
    logger.error(f"Error logging location in background: {e}", exc_info=True)


async def log_email_bg(mongo_service, email_data: Dict[str, Any], background_task_id: Optional[str] = None):
  """Background task to log an email to MongoDB."""
  try:
    if not email_data.get("id"):
      email_data["id"] = str(uuid.uuid4())

    if background_task_id:
      email_data["background_task_id"] = background_task_id

    result = await mongo_service.create_email(email_data)
    if result:
      logger.info(f"Email logged successfully in background: {result}")
    else:
      logger.error("Failed to log email in background")
  except Exception as e:
    logger.error(f"Error logging email in background: {e}", exc_info=True)


async def update_quote_status_bg(mongo_service, quote_id: str, status: QuoteStatus, error_message: Optional[str] = None):
  """Background task to update quote status in MongoDB."""
  try:
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == QuoteStatus.COMPLETED:
      update_data["processing_completed_at"] = datetime.now(timezone.utc)

    result = await mongo_service.update_quote(quote_id, update_data)
    if result:
      logger.info(
          f"Quote status updated successfully in background: {quote_id} -> {status.value}")
    else:
      logger.error(f"Failed to update quote status in background: {quote_id}")
  except Exception as e:
    logger.error(
        f"Error updating quote status in background: {e}", exc_info=True)


async def update_call_status_bg(mongo_service, call_id: str, status: CallStatus, error_message: Optional[str] = None):
  """Background task to update call status in MongoDB."""
  try:
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == CallStatus.COMPLETED:
      update_data["call_completed_at"] = datetime.now(timezone.utc)

    result = await mongo_service.update_call(call_id, update_data)
    if result:
      logger.info(
          f"Call status updated successfully in background: {call_id} -> {status.value}")
    else:
      logger.error(f"Failed to update call status in background: {call_id}")
  except Exception as e:
    logger.error(
        f"Error updating call status in background: {e}", exc_info=True)


async def update_classify_status_bg(mongo_service, classify_id: str, status: ClassifyStatus, error_message: Optional[str] = None):
  """Background task to update classification status in MongoDB."""
  try:
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == ClassifyStatus.COMPLETED:
      update_data["classified_at"] = datetime.now(timezone.utc)

    result = await mongo_service.update_classify(classify_id, update_data)
    if result:
      logger.info(
          f"Classification status updated successfully in background: {classify_id} -> {status.value}")
    else:
      logger.error(
          f"Failed to update classification status in background: {classify_id}")
  except Exception as e:
    logger.error(
        f"Error updating classification status in background: {e}", exc_info=True)


async def update_location_status_bg(mongo_service, location_id: str, status: LocationStatus, error_message: Optional[str] = None):
  """Background task to update location status in MongoDB."""
  try:
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

    result = await mongo_service.update_location(location_id, update_data)
    if result:
      logger.info(
          f"Location status updated successfully in background: {location_id} -> {status.value}")
    else:
      logger.error(
          f"Failed to update location status in background: {location_id}")
  except Exception as e:
    logger.error(
        f"Error updating location status in background: {e}", exc_info=True)


async def update_email_status_bg(mongo_service, email_id: str, status: EmailStatus, error_message: Optional[str] = None):
  """Background task to update email status in MongoDB."""
  try:
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == EmailStatus.DELIVERED:
      update_data["delivery_timestamp"] = datetime.now(timezone.utc)
    elif status == EmailStatus.SUCCESS:
      update_data["processed_at"] = datetime.now(timezone.utc)

    result = await mongo_service.update_email(email_id, update_data)
    if result:
      logger.info(
          f"Email status updated successfully in background: {email_id} -> {status.value}")
    else:
      logger.error(f"Failed to update email status in background: {email_id}")
  except Exception as e:
    logger.error(
        f"Error updating email status in background: {e}", exc_info=True)
