# filepath: app/api/v1/endpoints/mongo/emails.py
from fastapi import APIRouter, Depends, HTTPException, Query
from app.services.mongo import MongoService, get_mongo_service
from app.models.common import GenericResponse, PaginatedResponse
from app.models.mongo.emails import EmailDocument, EmailStatus, EmailCategory
from typing import Optional
import logfire

router = APIRouter(prefix="/emails", tags=["emails"])

# Pagination constant
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=PaginatedResponse[EmailDocument])
async def get_recent_emails(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get recent emails with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_recent_emails(offset)
    total = await service.count_all_emails()

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching recent emails: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch recent emails")


@router.get("/oldest", response_model=PaginatedResponse[EmailDocument])
async def get_oldest_emails(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get oldest emails with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_oldest_emails(offset)
    total = await service.count_all_emails()

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching oldest emails: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch oldest emails")


@router.get("/successful", response_model=PaginatedResponse[EmailDocument])
async def get_successful_emails(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get successful emails with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_successful_emails(offset)
    total = await service.count_emails_by_status("success")

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching successful emails: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch successful emails")


@router.get("/failed", response_model=PaginatedResponse[EmailDocument])
async def get_failed_emails(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get failed emails with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_failed_emails(offset)
    total = await service.count_emails_by_status("failed")

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching failed emails: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch failed emails")


@router.get("/pending", response_model=PaginatedResponse[EmailDocument])
async def get_pending_emails(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get pending emails with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_pending_emails(offset)
    total = await service.count_emails_by_status("pending")

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching pending emails: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch pending emails")


@router.get("/by-category", response_model=PaginatedResponse[EmailDocument])
async def get_emails_by_category(
    category: EmailCategory = Query(...,
                                    description="Email category to filter by"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get emails by category with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_emails_by_category(category.value, offset)
    total = await service.count_emails_by_category(category.value)

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching emails by category: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch emails by category")


@router.get("/by-direction", response_model=PaginatedResponse[EmailDocument])
async def get_emails_by_direction(
    direction: str = Query(...,
                           description="Email direction (inbound/outbound)"),
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get emails by direction with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_emails_by_direction(direction, offset)
    total = await service.count_emails_by_direction(direction)

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching emails by direction: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch emails by direction")


@router.get("/with-attachments", response_model=PaginatedResponse[EmailDocument])
async def get_emails_with_attachments(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get emails with attachments with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_emails_with_attachments(offset)
    total = await service.count_emails_with_attachments()

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching emails with attachments: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch emails with attachments")


@router.get("/processed", response_model=PaginatedResponse[EmailDocument])
async def get_processed_emails(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    service: MongoService = Depends(get_mongo_service)
):
  """Get processed emails with pagination."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    emails = await service.get_processed_emails(offset)
    total = await service.count_processed_emails()

    return PaginatedResponse(
        items=emails,
        page=page,
        limit=PAGINATION_LIMIT,
        total=total,
        has_more=offset + PAGINATION_LIMIT < total
    )
  except Exception as e:
    logfire.error(f"Error fetching processed emails: {str(e)}")
    raise HTTPException(
        status_code=500, detail="Failed to fetch processed emails")


@router.get("/{email_id}", response_model=GenericResponse[EmailDocument])
async def get_email_by_id(
    email_id: str,
    service: MongoService = Depends(get_mongo_service)
):
  """Get a single email by ID."""
  try:
    email = await service.get_email_by_id(email_id)
    if not email:
      raise HTTPException(status_code=404, detail="Email not found")

    return GenericResponse(
        success=True,
        data=email
    )
  except HTTPException:
    raise
  except Exception as e:
    logfire.error(f"Error fetching email by ID: {str(e)}")
    raise HTTPException(status_code=500, detail="Failed to fetch email")
