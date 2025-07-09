# filepath: app/api/v1/endpoints/mongo/location.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.mongo import MongoService, get_mongo_service
from app.models.common import GenericResponse, PaginatedResponse
from app.models.mongo.location import LocationDocument, LocationStatus
from typing import Optional
import logfire
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/location", tags=["location"])

# Pagination constant
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_recent_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get recent locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_recent_locations(offset)
    total = await service.count_all_locations()

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching recent locations: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch recent locations",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/oldest", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_oldest_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get oldest locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_oldest_locations(offset)
    total = await service.count_all_locations()

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching oldest locations: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch oldest locations",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/successful", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_successful_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get successful locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_successful_locations(offset)
    total = await service.count_locations_by_status("success")

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching successful locations: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch successful locations",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/failed", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_failed_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get failed locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_failed_locations(offset)
    total = await service.count_locations_by_status("failed")

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching failed locations: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch failed locations",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/pending", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_pending_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get pending locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_pending_locations(offset)
    total = await service.count_locations_by_status("pending")

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching pending locations: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch pending locations",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-distance", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_locations_by_distance(
    ascending: bool = Query(
        True, description="Sort by distance ascending (nearest first)"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get locations sorted by distance with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_locations_by_distance(ascending, offset)
    total = await service.count_all_locations()

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching locations by distance: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch locations by distance",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-branch", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_locations_by_branch(
    branch: str = Query(..., description="Branch name to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get locations by branch with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_locations_by_branch(branch, offset)
    total = await service.count_locations_by_branch(branch)

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching locations by branch: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch locations by branch",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/with-fallback", response_model=GenericResponse[PaginatedResponse[LocationDocument]])
async def get_locations_with_fallback(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get locations that used fallback method with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_locations_with_fallback(offset)
    total = await service.count_locations_with_fallback()

    pagination_response = PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching locations with fallback: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch locations with fallback",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/{location_id}", response_model=GenericResponse[LocationDocument])
async def get_location_by_id(
    location_id: str,
    service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get a single location by ID."""
  try:
    location = await service.get_location_by_id(location_id)
    if not location:
      return GenericResponse.error(
          message="Location not found",
          status_code=404
      )

    return GenericResponse(data=location)
  except Exception as e:
    logfire.error(f"Error fetching location by ID: {str(e)}")
    return GenericResponse.error(
        message="Failed to fetch location",
        details={"error": str(e)},
        status_code=500
    )
