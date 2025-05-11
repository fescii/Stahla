# filepath: /home/femar/AO3/Stahla/app/api/v1/endpoints/bland_calls.py
import logfire
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional
from pymongo import ASCENDING, DESCENDING # For sort_order mapping

from app.services.mongo.mongo import MongoService
from app.services.bland import BlandAIManager, BlandApiResult
from app.core.dependencies import get_mongo_service_dep, get_bland_manager_dep
from app.models.bland import BlandCallbackRequest # For initiating calls
from app.models.bland_call_log import ( # For responses and request bodies
    BlandCallLog, 
    PaginatedBlandCallResponse, 
    BlandCallStats,
    BlandCallStatus
)

router = APIRouter()

@router.post("/initiate", response_model=BlandApiResult, status_code=202)
async def initiate_bland_call(
    call_request: BlandCallbackRequest, # Moved before contact_id
    contact_id: str = Query(..., description="HubSpot Contact ID to associate with the call. This will be the ID of the call log."),
    mongo_service: MongoService = Depends(get_mongo_service_dep),
    bland_manager: BlandAIManager = Depends(get_bland_manager_dep),
    background_tasks: BackgroundTasks = BackgroundTasks() # Correctly placed
):
    """
    Initiates a new call via Bland.ai.
    The `contact_id` will be used as the primary identifier for logging in MongoDB.
    """
    logfire.info(f"API: Received request to initiate call for HubSpot Contact ID: {contact_id}")
    
    # Check if a log already exists and is in a final state, might influence decision or just log
    existing_log = await mongo_service.get_bland_call_log(contact_id)
    if existing_log and existing_log.get("status") in [BlandCallStatus.COMPLETED.value, BlandCallStatus.PENDING.value]: # PENDING means one is already active
        logfire.warn(f"API: Initiating new call for contact_id {contact_id} which already has a log in status: {existing_log.get('status')}.")
        # Depending on policy, we might prevent this or allow overwriting/new attempt.
        # For now, proceeding.

    api_result = await bland_manager.initiate_callback(
        request_data=call_request,
        mongo_service=mongo_service,
        background_tasks=background_tasks,
        contact_id=contact_id
    )
    if api_result.status == "error":
        # Map Bland's error to an HTTP exception if appropriate
        # For now, BlandAIManager handles logging the error to the call log.
        # The response model BlandApiResult will convey the error.
        logfire.error(f"API: Call initiation failed for contact_id {contact_id}. Bland API Error: {api_result.message}")
        # We might want to return a different HTTP status code based on api_result.message or details
        # For example, if it's a validation error from Bland, maybe 400. If Bland server error, 502/503.
        # For now, 202 is returned and the body indicates error, or we could raise HTTPException here.
        # Let's return 502 if it's an error to better reflect a downstream issue.
        raise HTTPException(status_code=502, detail={"message": "Bland API error during call initiation.", "bland_error": api_result.model_dump()})

    return api_result


@router.post("/retry/{contact_id}", response_model=BlandApiResult, status_code=202)
async def retry_bland_call(
    contact_id: str,
    mongo_service: MongoService = Depends(get_mongo_service_dep), # Moved before retry_reason
    bland_manager: BlandAIManager = Depends(get_bland_manager_dep), # Moved before retry_reason
    retry_reason: Optional[str] = Query("User initiated retry via API", description="Reason for retrying the call."),
    background_tasks: BackgroundTasks = BackgroundTasks() # Correctly placed
):
    """
    Retries a previously logged call for the given HubSpot Contact ID.
    """
    logfire.info(f"API: Received request to retry call for HubSpot Contact ID: {contact_id} with reason: '{retry_reason}'")
    
    original_log = await mongo_service.get_bland_call_log(contact_id)
    if not original_log:
        raise HTTPException(status_code=404, detail=f"No call log found for contact_id: {contact_id} to retry.")

    # Optional: Check if the call is in a retryable state (e.g., FAILED)
    # if original_log.get("status") not in [BlandCallStatus.FAILED.value, ...]: # Add other retryable statuses
    #     raise HTTPException(status_code=400, detail=f"Call for contact_id: {contact_id} is not in a retryable state (status: {original_log.get('status')}).")

    api_result = await bland_manager.retry_call(
        contact_id=contact_id,
        mongo_service=mongo_service,
        background_tasks=background_tasks,
        retry_reason=retry_reason
    )

    if api_result.status == "error":
        logfire.error(f"API: Call retry failed for contact_id {contact_id}. Error: {api_result.message}")
        if "Original call log not found" in api_result.message: # Should be caught by pre-check
             raise HTTPException(status_code=404, detail=f"Original call log for contact_id {contact_id} disappeared before retry.")
        elif "missing phone number" in api_result.message:
             raise HTTPException(status_code=400, detail=f"Original call log for contact_id {contact_id} is incomplete for retry (missing phone number).")
        # Generic downstream error for other Bland issues
        raise HTTPException(status_code=502, detail={"message": "Bland API error during call retry.", "bland_error": api_result.model_dump()})
        
    return api_result


@router.get("/stats", response_model=BlandCallStats)
async def get_call_stats(
    mongo_service: MongoService = Depends(get_mongo_service_dep)
):
    """
    Retrieves statistics for all Bland.ai calls, categorized by status.
    """
    stats_data = await mongo_service.get_bland_call_stats()
    # The BlandCallStats model expects fields like PENDING, COMPLETED, FAILED, RETRYING, total_calls
    # mongo_service.get_bland_call_stats() returns a dict like {"PENDING": count, ..., "total_calls": total}
    # This should map directly if keys match enum values.
    return BlandCallStats(**stats_data)


@router.get("/logs", response_model=PaginatedBlandCallResponse)
async def list_all_bland_calls(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    status: Optional[BlandCallStatus] = Query(None, description="Filter calls by status"),
    sort_field: str = Query("created_at", description="Field to sort by (e.g., 'created_at', 'updated_at', 'status')"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    mongo_service: MongoService = Depends(get_mongo_service_dep)
):
    """
    Retrieves a paginated list of all Bland.ai call logs, with optional status filtering and sorting.
    """
    mongo_sort_order = DESCENDING if sort_order.lower() == "desc" else ASCENDING
    
    status_filter_value = status.value if status else None
    
    items_dict, total_items = await mongo_service.get_bland_calls(
        page=page,
        page_size=page_size,
        status_filter=status_filter_value,
        sort_field=sort_field,
        sort_order=mongo_sort_order
    )
    
    # Convert dict items to BlandCallLog model instances
    call_logs = [BlandCallLog(**item) for item in items_dict]
    
    return PaginatedBlandCallResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=(total_items + page_size - 1) // page_size if total_items > 0 else 0,
        items=call_logs
    )


@router.get("/logs/failed", response_model=PaginatedBlandCallResponse)
async def list_failed_bland_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mongo_service: MongoService = Depends(get_mongo_service_dep)
):
    """Retrieves a paginated list of FAILED Bland.ai call logs."""
    items_dict, total_items = await mongo_service.get_bland_calls(
        page=page, page_size=page_size, status_filter=BlandCallStatus.FAILED.value, sort_field="updated_at", sort_order=DESCENDING
    )
    call_logs = [BlandCallLog(**item) for item in items_dict]
    return PaginatedBlandCallResponse(
        page=page, page_size=page_size, total_items=total_items,
        total_pages=(total_items + page_size - 1) // page_size if total_items > 0 else 0, items=call_logs
    )


@router.get("/logs/completed", response_model=PaginatedBlandCallResponse)
async def list_completed_bland_calls(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    mongo_service: MongoService = Depends(get_mongo_service_dep)
):
    """Retrieves a paginated list of COMPLETED Bland.ai call logs."""
    items_dict, total_items = await mongo_service.get_bland_calls(
        page=page, page_size=page_size, status_filter=BlandCallStatus.COMPLETED.value, sort_field="updated_at", sort_order=DESCENDING
    )
    call_logs = [BlandCallLog(**item) for item in items_dict]
    return PaginatedBlandCallResponse(
        page=page, page_size=page_size, total_items=total_items,
        total_pages=(total_items + page_size - 1) // page_size if total_items > 0 else 0, items=call_logs
    )
