# app/api/v1/endpoints/mongo/calls.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logfire
from app.services.mongo import MongoService, get_mongo_service
from app.models.mongo.calls import CallDocument, CallStatus
from app.models.common import GenericResponse, PaginatedResponse
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/calls", tags=["calls"])

# Hardcoded pagination limit
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_recent_calls(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get recent calls ordered by creation date (newest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_recent_calls(limit=PAGINATION_LIMIT, offset=offset)
    total_count = await mongo_service.count_calls()

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching recent calls: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/oldest", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_oldest_calls(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get oldest calls ordered by creation date (oldest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_oldest_calls(limit=PAGINATION_LIMIT, offset=offset)
    total_count = await mongo_service.count_calls()

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching oldest calls: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/successful", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_successful_calls(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get successfully completed calls."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_calls_by_status(
        status=CallStatus.COMPLETED,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_calls_by_status(CallStatus.COMPLETED)

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching successful calls: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/failed", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_failed_calls(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get failed calls."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_calls_by_status(
        status=CallStatus.FAILED,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_calls_by_status(CallStatus.FAILED)

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching failed calls: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/longest", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_longest_calls(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get calls ordered by duration (longest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_calls_by_duration(limit=PAGINATION_LIMIT, offset=offset, ascending=False)
    total_count = await mongo_service.count_calls()

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching longest calls: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/shortest", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_shortest_calls(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get calls ordered by duration (shortest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_calls_by_duration(limit=PAGINATION_LIMIT, offset=offset, ascending=True)
    total_count = await mongo_service.count_calls()

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching shortest calls: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-source/{source}", response_model=GenericResponse[PaginatedResponse[CallDocument]])
async def get_calls_by_source(
    source: str,
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get calls by source."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    calls = await mongo_service.get_calls_by_source(
        source=source,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_calls_by_source(source)

    return GenericResponse(
        data=PaginatedResponse(
            items=calls,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching calls by source: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch calls",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/{call_id}", response_model=GenericResponse[CallDocument])
async def get_call_by_id(
    call_id: str,
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get a single call by ID."""
  try:
    call = await mongo_service.get_call_by_id(call_id)
    if not call:
      return GenericResponse.error(
          message="Call not found",
          status_code=404
      )

    return GenericResponse(data=call)
  except Exception as e:
    logfire.error(f"Error fetching call by ID: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch call",
        details={"error": str(e)},
        status_code=500
    )
