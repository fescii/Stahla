# app/api/v1/endpoints/mongo/classify.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logfire
from app.services.mongo import MongoService, get_mongo_service
from app.models.mongo.classify import ClassifyDocument, ClassifyStatus
from app.models.common import GenericResponse, PaginatedResponse

router = APIRouter(prefix="/classify", tags=["classify"])

# Hardcoded pagination limit
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=PaginatedResponse[ClassifyDocument])
async def get_recent_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get recent classifications ordered by creation date (newest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_recent_classifications(offset=offset)
    total_count = await mongo_service.count_all_classifications()

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(f"Error fetching recent classifications: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/oldest", response_model=PaginatedResponse[ClassifyDocument])
async def get_oldest_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get oldest classifications ordered by creation date (oldest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_oldest_classifications(offset=offset)
    total_count = await mongo_service.count_all_classifications()

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(f"Error fetching oldest classifications: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/successful", response_model=PaginatedResponse[ClassifyDocument])
async def get_successful_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get successfully completed classifications."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_successful_classifications(offset=offset)
    total_count = await mongo_service.count_classifications_by_status("success")

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(
        f"Error fetching successful classifications: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/failed", response_model=PaginatedResponse[ClassifyDocument])
async def get_failed_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get failed classifications."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_failed_classifications(offset=offset)
    total_count = await mongo_service.count_classifications_by_status("failed")

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(f"Error fetching failed classifications: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/disqualified", response_model=PaginatedResponse[ClassifyDocument])
async def get_disqualified_classifications(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get disqualified classifications."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_disqualified_classifications(offset=offset)
    total_count = await mongo_service.count_classifications_by_lead_type("Disqualify")

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(
        f"Error fetching disqualified classifications: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/by-lead-type", response_model=PaginatedResponse[ClassifyDocument])
async def get_classifications_by_lead_type(
    lead_type: str = Query(..., description="Lead type to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get classifications by lead type (Services, Logistics, Leads, Disqualify)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_classifications_by_lead_type(
        lead_type=lead_type,
        offset=offset
    )
    total_count = await mongo_service.count_classifications_by_lead_type(lead_type)

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(
        f"Error fetching classifications by lead type: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/by-confidence", response_model=PaginatedResponse[ClassifyDocument])
async def get_classifications_by_confidence(
    min_confidence: float = Query(..., description="Minimum confidence level"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get classifications by minimum confidence level."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_classifications_by_confidence(
        min_confidence=min_confidence,
        offset=offset
    )
    total_count = await mongo_service.count_classifications_by_confidence(min_confidence)

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(
        f"Error fetching classifications by confidence: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/by-source", response_model=PaginatedResponse[ClassifyDocument])
async def get_classifications_by_source(
    source: str = Query(..., description="Source to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get classifications by source (webform, voice, email, hubspot)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    classifications = await mongo_service.get_classifications_by_source(
        source=source,
        offset=offset
    )
    total_count = await mongo_service.count_classifications_by_source(source)

    return PaginatedResponse(
        items=classifications,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total_count,
        has_more=(offset + PAGINATION_LIMIT) < total_count
    )
  except Exception as e:
    logfire.error(
        f"Error fetching classifications by source: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classifications")


@router.get("/{classify_id}", response_model=GenericResponse[ClassifyDocument])
async def get_classification_by_id(
    classify_id: str,
    mongo_service: MongoService = Depends(get_mongo_service)
):
  """Get a single classification by ID."""
  try:
    classification = await mongo_service.get_classification_by_id(classify_id)
    if not classification:
      raise HTTPException(status_code=404, detail="Classification not found")

    return GenericResponse(
        success=True,
        data=classification
    )
  except HTTPException:
    raise
  except Exception as e:
    logfire.error(f"Error fetching classification by ID: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to fetch classification")
