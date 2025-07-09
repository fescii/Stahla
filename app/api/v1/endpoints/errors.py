import logfire
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from pymongo import ASCENDING, DESCENDING
from datetime import datetime, timezone

from app.services.mongo import MongoService, get_mongo_service
from app.models.common import GenericResponse  # Added import
# Changed from error_log
from app.models.error import ErrorLog, PaginatedErrorLogResponse

router = APIRouter()


# Updated response_model
@router.get("/logs", response_model=GenericResponse[PaginatedErrorLogResponse])
async def list_error_logs(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(
        10, ge=1, le=100, description="Number of items per page"),
    service_name: Optional[str] = Query(
        None, description="Filter by service name"),
    error_type: Optional[str] = Query(
        None, description="Filter by error type"),
    sort_field: str = Query(
        "timestamp", description="Field to sort by (e.g., 'timestamp', 'service_name', 'error_type')"),
    sort_order: str = Query("desc", description="Sort order: 'asc' or 'desc'"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  try:
    logfire.info(
        f"API: Received request to list error logs. Page: {page}, PageSize: {page_size}, Service: {service_name}, Type: {error_type}")

    mongo_sort_order = DESCENDING if sort_order.lower() == "desc" else ASCENDING

    items_dict, total_items = await mongo_service.get_error_logs(
        page=page,
        page_size=page_size,
        service_name_filter=service_name,
        error_type_filter=error_type,
        sort_field=sort_field,
        sort_order=mongo_sort_order
    )

    # Convert dict items to ErrorLog model instances
    # The _id from MongoDB (which is a UUID) will be mapped to id field in ErrorLog model.
    error_logs = [ErrorLog(**item) for item in items_dict]

    response_data = PaginatedErrorLogResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=(total_items + page_size -
                     1) // page_size if total_items > 0 else 0,
        items=error_logs
    )
    return GenericResponse(data=response_data)
  except Exception as e:
    logfire.error(
        f"API: Unexpected error listing error logs: {e}", exc_info=True)
    return GenericResponse.error(message="An unexpected error occurred while listing error logs.", details=str(e), status_code=500)
