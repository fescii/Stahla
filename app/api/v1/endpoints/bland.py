# filepath: /home/femar/AO3/Stahla/app/api/v1/endpoints/bland_calls.py
import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from pymongo import ASCENDING, DESCENDING  # For sort_order mapping

from app.services.mongo.mongo import MongoService
from app.services.bland import BlandAIManager, BlandApiResult
from app.core.dependencies import get_bland_manager_dep
from app.services.mongo.mongo import get_mongo_service
from app.core.security import get_current_user
from app.models.user import User
from app.models.bland import BlandCallbackRequest  # Models from bland.py
# Models from bland_call_log.py -> blandlog.py
from app.models.blandlog import BlandCallStatus, BlandCallStats, PaginatedBlandCallResponse, BlandCallLog
from app.models.common import GenericResponse  # Added import
from datetime import datetime

router = APIRouter()


# Updated response_model
@router.post("/initiate", response_model=GenericResponse[BlandApiResult], status_code=202)
async def initiate_bland_call(
    call_request: BlandCallbackRequest,
    contact_id: str = Query(
        ..., description="HubSpot Contact ID to associate with the call. This will be the ID of the call log."),
    mongo_service: MongoService = Depends(get_mongo_service),
    bland_manager: BlandAIManager = Depends(get_bland_manager_dep),
    # Added current_user dependency
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  try:
    logfire.info(
        f"API: Received request to initiate call for HubSpot Contact ID: {contact_id}")

    # Check if a log already exists and is in a final state, might influence decision or just log
    existing_log = await mongo_service.get_bland_call_log(contact_id)
    # PENDING means one is already active
    if existing_log and existing_log.get("status") in [BlandCallStatus.COMPLETED.value, BlandCallStatus.PENDING.value]:
      logfire.warn(
          f"API: Initiating new call for contact_id {contact_id} which already has a log in status: {existing_log.get('status')}.")
      # Depending on policy, we might prevent this or allow overwriting/new attempt.
      # For now, proceeding.

    api_result = await bland_manager.initiate_callback(
        request_data=call_request,
        mongo_service=mongo_service,
        background_tasks=background_tasks,
        contact_id=contact_id
    )
    if api_result.status == "error":
      logfire.error(
          f"API: Call initiation failed for contact_id {contact_id}. Bland API Error: {api_result.message}")
      return GenericResponse.error(message="Bland API error during call initiation.", details=api_result.model_dump(), status_code=502)

    # Wrapped in GenericResponse
    return GenericResponse(data=api_result, status_code=202)
  except Exception as e:
    logfire.error(
        f"API: Unexpected error initiating call for {contact_id}: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred during call initiation.", details=str(e), status_code=500)


# Updated response_model
@router.post("/retry/{contact_id}", response_model=GenericResponse[BlandApiResult], status_code=202)
async def retry_bland_call(
    contact_id: str,
    mongo_service: MongoService = Depends(get_mongo_service),
    bland_manager: BlandAIManager = Depends(get_bland_manager_dep),
    retry_reason: Optional[str] = Query(
        "User initiated retry via API", description="Reason for retrying the call."),
    # Added current_user dependency
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
  try:
    logfire.info(
        f"API: Received request to retry call for HubSpot Contact ID: {contact_id} with reason: '{retry_reason}'")

    original_log = await mongo_service.get_bland_call_log(contact_id)
    if not original_log:
      return GenericResponse.error(message=f"No call log found for contact_id: {contact_id} to retry.", status_code=404)

    api_result = await bland_manager.retry_call(
        contact_id=contact_id,
        mongo_service=mongo_service,
        background_tasks=background_tasks,
        retry_reason=retry_reason
    )

    if api_result.status == "error":
      logfire.error(
          f"API: Call retry failed for contact_id {contact_id}. Error: {api_result.message}")
      error_message = "Bland API error during call retry."
      status_code = 502
      if "Original call log not found" in api_result.message:
        error_message = f"Original call log for contact_id {contact_id} disappeared before retry."
        status_code = 404
      elif "missing phone number" in api_result.message:
        error_message = f"Original call log for contact_id {contact_id} is incomplete for retry (missing phone number)."
        status_code = 400
      return GenericResponse.error(message=error_message, details=api_result.model_dump(), status_code=status_code)

    # Wrapped in GenericResponse
    return GenericResponse(data=api_result, status_code=202)
  except Exception as e:
    logfire.error(
        f"API: Unexpected error retrying call for {contact_id}: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred during call retry.", details=str(e), status_code=500)


# Updated response_model
@router.get("/stats", response_model=GenericResponse[BlandCallStats])
async def get_call_stats(
    mongo_service: MongoService = Depends(get_mongo_service),
    # Added current_user dependency
    current_user: User = Depends(get_current_user)
):
  try:
    stats_data = await mongo_service.get_bland_call_stats()
    return GenericResponse(data=BlandCallStats(**stats_data))
  except Exception as e:
    logfire.error(
        f"API: Unexpected error getting call stats: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred while retrieving call statistics.", details=str(e), status_code=500)


# Updated response_model
@router.get("/logs", response_model=GenericResponse[PaginatedBlandCallResponse])
async def list_all_bland_calls(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        10, ge=1, le=100, description="Number of items per page"),
    status: Optional[BlandCallStatus] = Query(
        None, description="Filter calls by status"),
    sort_field: str = Query(
        "created_at", description="Field to sort by (e.g., 'created_at', 'updated_at', 'status')"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    mongo_service: MongoService = Depends(get_mongo_service),
    # Added current_user dependency
    current_user: User = Depends(get_current_user)
):
  try:
    mongo_sort_order = DESCENDING if sort_order.lower() == "desc" else ASCENDING

    status_filter_value = status.value if status else None

    items_dict, total_items = await mongo_service.get_bland_calls(
        page=page,
        page_size=page_size,
        status_filter=status_filter_value,
        sort_field=sort_field,
        sort_order=mongo_sort_order
    )

    call_logs = [BlandCallLog(**item) for item in items_dict]

    response_data = PaginatedBlandCallResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=(total_items + page_size -
                     1) // page_size if total_items > 0 else 0,
        items=call_logs
    )
    return GenericResponse(data=response_data)
  except Exception as e:
    logfire.error(
        f"API: Unexpected error listing all bland calls: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred while listing bland calls.", details=str(e), status_code=500)


# Updated response_model
@router.get("/logs/failed", response_model=GenericResponse[PaginatedBlandCallResponse])
async def list_failed_bland_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mongo_service: MongoService = Depends(get_mongo_service),
    # Added current_user dependency
    current_user: User = Depends(get_current_user)
):
  try:
    items_dict, total_items = await mongo_service.get_bland_calls(
        page=page, page_size=page_size, status_filter=BlandCallStatus.FAILED.value, sort_field="updated_at", sort_order=DESCENDING
    )
    call_logs = [BlandCallLog(**item) for item in items_dict]
    response_data = PaginatedBlandCallResponse(
        page=page, page_size=page_size, total_items=total_items,
        total_pages=(total_items + page_size - 1) // page_size if total_items > 0 else 0, items=call_logs
    )
    return GenericResponse(data=response_data)
  except Exception as e:
    logfire.error(
        f"API: Unexpected error listing failed bland calls: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred while listing failed bland calls.", details=str(e), status_code=500)


# Updated response_model
@router.get("/logs/completed", response_model=GenericResponse[PaginatedBlandCallResponse])
async def list_completed_bland_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mongo_service: MongoService = Depends(get_mongo_service),
    # Added current_user dependency
    current_user: User = Depends(get_current_user)
):
  try:
    items_dict, total_items = await mongo_service.get_bland_calls(
        page=page, page_size=page_size, status_filter=BlandCallStatus.COMPLETED.value, sort_field="updated_at", sort_order=DESCENDING
    )
    call_logs = [BlandCallLog(**item) for item in items_dict]
    response_data = PaginatedBlandCallResponse(
        page=page, page_size=page_size, total_items=total_items,
        total_pages=(total_items + page_size - 1) // page_size if total_items > 0 else 0, items=call_logs
    )
    return GenericResponse(data=response_data)
  except Exception as e:
    logfire.error(
        f"API: Unexpected error listing completed bland calls: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred while listing completed bland calls.", details=str(e), status_code=500)
