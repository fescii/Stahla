# filepath: app/api/v1/endpoints/mongo/location.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.mongo import MongoService, get_mongo_service
from app.models.common import GenericResponse, PaginatedResponse
from app.models.mongo.location import LocationDocument, LocationStatus
from typing import Optional
import logfire

router = APIRouter(prefix="/location", tags=["location"])

# Pagination constant
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=PaginatedResponse[LocationDocument])
async def get_recent_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get recent locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_recent_locations(offset)
    total = await service.count_all_locations()

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching recent locations: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch recent locations")


@router.get("/oldest", response_model=PaginatedResponse[LocationDocument])
async def get_oldest_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get oldest locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_oldest_locations(offset)
    total = await service.count_all_locations()

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching oldest locations: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch oldest locations")


@router.get("/successful", response_model=PaginatedResponse[LocationDocument])
async def get_successful_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get successful locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_successful_locations(offset)
    total = await service.count_locations_by_status("success")

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching successful locations: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch successful locations")


@router.get("/failed", response_model=PaginatedResponse[LocationDocument])
async def get_failed_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get failed locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_failed_locations(offset)
    total = await service.count_locations_by_status("failed")

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching failed locations: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch failed locations")


@router.get("/pending", response_model=PaginatedResponse[LocationDocument])
async def get_pending_locations(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get pending locations with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_pending_locations(offset)
    total = await service.count_locations_by_status("pending")

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching pending locations: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch pending locations")


@router.get("/by-distance", response_model=PaginatedResponse[LocationDocument])
async def get_locations_by_distance(
    ascending: bool = Query(
        True, description="Sort by distance ascending (nearest first)"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get locations sorted by distance with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_locations_by_distance(ascending, offset)
    total = await service.count_all_locations()

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching locations by distance: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch locations by distance")


@router.get("/by-branch", response_model=PaginatedResponse[LocationDocument])
async def get_locations_by_branch(
    branch: str = Query(..., description="Branch name to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get locations by branch with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_locations_by_branch(branch, offset)
    total = await service.count_locations_by_branch(branch)

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching locations by branch: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch locations by branch")


@router.get("/with-fallback", response_model=PaginatedResponse[LocationDocument])
async def get_locations_with_fallback(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get locations that used fallback method with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    locations = await service.get_locations_with_fallback(offset)
    total = await service.count_locations_with_fallback()

    return PaginatedResponse(
        items=locations,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching locations with fallback: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch locations with fallback")


@router.get("/{location_id}", response_model=GenericResponse[LocationDocument])
async def get_location_by_id(
    location_id: str,
    service: MongoService = Depends(get_mongo_service)
):
  """Get a single location by ID."""
  try:
    location = await service.get_location_by_id(location_id)
    if not location:
      raise HTTPException(status_code=404, detail="Location not found")

    return GenericResponse(
        success=True,
        data=location
    )
  except HTTPException:
    raise
  except Exception as e:
    logfire.error(f"Error fetching location by ID: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to fetch location")
