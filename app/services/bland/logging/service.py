"""Bland AI logging service for call attempts and results."""

import logfire
from typing import Optional
from datetime import datetime, timezone
from fastapi import BackgroundTasks
from app.models.mongo.calls import CallStatus
from app.services.mongo import MongoService


class BlandLogService:
  """Handles logging for Bland AI call operations."""

  def __init__(
      self,
      mongo_service: MongoService,
      background_tasks: BackgroundTasks
  ):
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks

  def log_call_attempt(
      self,
      contact_id: str,
      phone_number: str,
      task: Optional[str] = None,
      pathway_id_used: Optional[str] = None,
      initial_status: CallStatus = CallStatus.PENDING,
      call_id_bland: Optional[str] = None,
      retry_of_call_id: Optional[str] = None,
      retry_reason: Optional[str] = None,
      voice_id: Optional[str] = None,
      webhook_url: Optional[str] = None
  ) -> bool:
    """
    Log a call attempt before making the API call.
    Returns True if logging was successful or scheduled, False otherwise.
    """
    try:
      self.background_tasks.add_task(
          self.mongo_service.log_bland_call_attempt,
          contact_id=contact_id,
          phone_number=phone_number,
          task=task,
          pathway_id_used=pathway_id_used,
          initial_status=initial_status,
          call_id_bland=call_id_bland,
          retry_of_call_id=retry_of_call_id,
          retry_reason=retry_reason,
          voice_id=voice_id,
          webhook_url=webhook_url
      )
      logfire.debug(
          f"Call attempt logging scheduled for contact_id: {contact_id}")
      return True
    except Exception as e:
      logfire.error(
          f"Failed to schedule call attempt logging for contact_id: {contact_id}: {e}")
      return False

  def log_call_failure(
      self,
      contact_id: str,
      error_message: str,
      error_details: Optional[dict] = None
  ) -> bool:
    """
    Log a call failure after API call.
    Returns True if logging was successful or scheduled, False otherwise.
    """
    try:
      current_time = datetime.now(timezone.utc)
      failure_update_data = {
          "$set": {
              "status": CallStatus.FAILED.value,
              "error_message": error_message,
              "updated_at": current_time,
              "bland_error_details": error_details,
          }
      }

      self.background_tasks.add_task(
          self.mongo_service.update_bland_call_log_internal,
          contact_id=contact_id,
          update_data=failure_update_data,
      )
      logfire.debug(
          f"Call failure logging scheduled for contact_id: {contact_id}")
      return True
    except Exception as e:
      logfire.error(
          f"Failed to schedule call failure logging for contact_id: {contact_id}: {e}")
      return False

  def log_call_success(
      self,
      contact_id: str,
      call_id_bland: str
  ) -> bool:
    """
    Log a successful call initiation after API call.
    Returns True if logging was successful or scheduled, False otherwise.
    """
    try:
      current_time = datetime.now(timezone.utc)
      success_init_update_data = {
          "$set": {
              "call_id_bland": call_id_bland,
              "status": CallStatus.PENDING.value,
              "updated_at": current_time,
              "error_message": None,
          },
          "$unset": {"bland_error_details": ""},
      }

      self.background_tasks.add_task(
          self.mongo_service.update_bland_call_log_internal,
          contact_id=contact_id,
          update_data=success_init_update_data,
      )
      logfire.debug(
          f"Call success logging scheduled for contact_id: {contact_id}")
      return True
    except Exception as e:
      logfire.error(
          f"Failed to schedule call success logging for contact_id: {contact_id}: {e}")
      return False

  def is_ready(self) -> bool:
    """Check if the logging service is ready (always True since services are required)."""
    return True

  def update_services(
      self,
      mongo_service: MongoService,
      background_tasks: BackgroundTasks
  ):
    """Update the service dependencies."""
    self.mongo_service = mongo_service
    self.background_tasks = background_tasks
