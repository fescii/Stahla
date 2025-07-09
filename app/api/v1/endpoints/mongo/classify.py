# app/api/v1/endpoints/mongo/classify.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logfire
from app.services.mongo import MongoService, get_mongo_service
from app.models.mongo.classify import ClassifyDocument, ClassifyStatus
from app.models.common import GenericResponse, PaginatedResponse
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/classify", tags=["classify"])

# Hardcoded pagination limit
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_recent_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get recent classifications ordered by creation date (newest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_recent_classifications(offset=offset)
    total_count = await mongo_service.count_all_classifications()

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching recent classifications: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/oldest", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_oldest_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get oldest classifications ordered by creation date (oldest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_oldest_classifications(offset=offset)
    total_count = await mongo_service.count_all_classifications()

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching oldest classifications: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/successful", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_successful_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get successfully completed classifications."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_successful_classifications(offset=offset)
    total_count = await mongo_service.count_classifications_by_status("success")

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(
        f"Error fetching successful classifications: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/failed", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_failed_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get failed classifications."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_failed_classifications(offset=offset)
    total_count = await mongo_service.count_classifications_by_status("failed")

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(f"Error fetching failed classifications: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/disqualified", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_disqualified_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get disqualified classifications."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_disqualified_classifications(offset=offset)
    total_count = await mongo_service.count_classifications_by_lead_type("Disqualify")

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(
        f"Error fetching disqualified classifications: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-lead-type", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_classifications_by_lead_type(
    lead_type: str = Query(..., description="Lead type to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get classifications by lead type (Services, Logistics, Leads, Disqualify)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_classifications_by_lead_type(
        lead_type=lead_type,
        offset=offset
    )
    total_count = await mongo_service.count_classifications_by_lead_type(lead_type)

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(
        f"Error fetching classifications by lead type: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-confidence", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_classifications_by_confidence(
    min_confidence: float = Query(..., description="Minimum confidence level"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get classifications by minimum confidence level."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_classifications_by_confidence(
        min_confidence=min_confidence,
        offset=offset
    )
    total_count = await mongo_service.count_classifications_by_confidence(min_confidence)

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(
        f"Error fetching classifications by confidence: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-source", response_model=GenericResponse[PaginatedResponse[ClassifyDocument]])
async def get_classifications_by_source(
    source: str = Query(..., description="Source to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get classifications by source (webform, voice, email, hubspot)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_classifications_by_source(
        source=source,
        offset=offset
    )
    total_count = await mongo_service.count_classifications_by_source(source)

    pagination_response = PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )

    return GenericResponse(data=pagination_response)
  except Exception as e:
    logfire.error(
        f"Error fetching classifications by source: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classifications",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/{classify_id}", response_model=GenericResponse[ClassifyDocument])
async def get_classification_by_id(
    classify_id: str,
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get a single classification by ID."""
  try:
    classification = await mongo_service.get_classification_by_id(classify_id)
    if not classification:
      return GenericResponse.error(
          message="Classification not found",
          status_code=404
      )

    return GenericResponse(data=classification)
  except Exception as e:
    logfire.error(f"Error fetching classification by ID: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch classification",
        details={"error": str(e)},
        status_code=500
    )
