# app/api/v1/endpoints/mongo/quotes.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
import logfire
from app.services.mongo import MongoService, get_mongo_service
from app.models.mongo.quotes import QuoteDocument, QuoteStatus
from app.models.common import GenericResponse, PaginatedResponse
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/quotes", tags=["quotes"])

# Hardcoded pagination limit
PAGINATION_LIMIT = 10


@router.get("/recent", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_recent_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get recent quotes ordered by creation date (newest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_recent_quotes(limit=PAGINATION_LIMIT, offset=offset)
    total_count = await mongo_service.count_quotes()

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching recent quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/oldest", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_oldest_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get oldest quotes ordered by creation date (oldest first)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_oldest_quotes(limit=PAGINATION_LIMIT, offset=offset)
    total_count = await mongo_service.count_quotes()

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching oldest quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/highest", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_highest_value_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get quotes ordered by total amount (highest to lowest)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_value(limit=PAGINATION_LIMIT, offset=offset, ascending=False)
    total_count = await mongo_service.count_quotes()

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching highest value quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/lowest", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_lowest_value_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get quotes ordered by total amount (lowest to highest)."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_value(limit=PAGINATION_LIMIT, offset=offset, ascending=True)
    total_count = await mongo_service.count_quotes()

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching lowest value quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/successful", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_successful_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get successfully completed quotes."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_status(
        status=QuoteStatus.COMPLETED,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_quotes_by_status(QuoteStatus.COMPLETED)

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching successful quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/failed", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_failed_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get failed quotes."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_status(
        status=QuoteStatus.FAILED,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_quotes_by_status(QuoteStatus.FAILED)

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching failed quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/expired", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_expired_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get expired quotes."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_status(
        status=QuoteStatus.EXPIRED,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_quotes_by_status(QuoteStatus.EXPIRED)

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching expired quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/pending", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_pending_quotes(
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get pending quotes."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_status(
        status=QuoteStatus.PENDING,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_quotes_by_status(QuoteStatus.PENDING)

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching pending quotes: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/by-product/{product_type}", response_model=GenericResponse[PaginatedResponse[QuoteDocument]])
async def get_quotes_by_product(
    product_type: str,
    page: int = Query(1, ge=1, description="Page number starting from 1"),
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get quotes by product type."""
  try:
    offset = (page - 1) * PAGINATION_LIMIT
    quotes = await mongo_service.get_quotes_by_product_type(
        product_type=product_type,
        limit=PAGINATION_LIMIT,
        offset=offset
    )
    total_count = await mongo_service.count_quotes_by_product_type(product_type)

    return GenericResponse(
        data=PaginatedResponse(
            items=quotes,
            page=page,
            limit=PAGINATION_LIMIT,
            total=total_count,
            has_more=(offset + PAGINATION_LIMIT) < total_count
        )
    )
  except Exception as e:
    logfire.error(f"Error fetching quotes by product type: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quotes",
        details={"error": str(e)},
        status_code=500
    )


@router.get("/{quote_id}", response_model=GenericResponse[QuoteDocument])
async def get_quote_by_id(
    quote_id: str,
    mongo_service: MongoService = Depends(get_mongo_service),
    current_user: User = Depends(get_current_user)
):
  """Get a single quote by ID."""
  try:
    quote = await mongo_service.get_quote_by_id(quote_id)
    if not quote:
      return GenericResponse.error(
          message="Quote not found",
          status_code=404
      )

    return GenericResponse(data=quote)
  except Exception as e:
    logfire.error(f"Error fetching quote by ID: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to fetch quote",
        details={"error": str(e)},
        status_code=500
    )
