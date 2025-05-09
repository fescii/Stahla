# filepath: /home/femar/AO3/Stahla/app/api/v1/endpoints/webhooks/pricing.py
import logging
from typing import Annotated
import time # For latency calculation

from fastapi import APIRouter, Depends, HTTPException, Security, status, BackgroundTasks
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel # Import BaseModel for LocationLookupRequest

from app.core.config import settings
# Import models using the correct path
from app.models.location import LocationLookupRequest
from app.models.quote import QuoteRequest, QuoteResponse
from app.models.common import GenericResponse, MessageResponse
# Import service classes and their injectors
from app.services.location.location import LocationService 
from app.services.quote.quote import QuoteService, get_quote_service 
from app.services.redis.redis import RedisService, get_redis_service 
# Import dependency injectors from core
from app.core.dependencies import get_location_service_dep 
from app.core.security import get_api_key # Keep API key dependency
# Import background task helpers
from app.services.dash.background import (
    log_request_response_bg,
    increment_request_counter_bg,
    log_error_bg,
    TOTAL_QUOTE_REQUESTS_KEY,
    SUCCESS_QUOTE_REQUESTS_KEY,
    ERROR_QUOTE_REQUESTS_KEY,
    TOTAL_LOCATION_LOOKUPS_KEY
)

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Security --- 
API_KEY_NAME = "Authorization"
# Use auto_error=False initially to provide custom error message
api_key_header_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header_scheme)):
    """Dependency to validate the API key from the Authorization header (Bearer <key>)."""
    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    parts = api_key_header.split() 
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authorization header format. Expected 'Bearer <API_KEY>'"
        )
    
    token = parts[1]
    if token == settings.PRICING_WEBHOOK_API_KEY:
        return token
    else:
        logger.warning(f"Invalid Pricing Webhook API Key received: {token[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

# --- Models for Location Lookup --- 
class LocationLookupRequest(BaseModel):
    delivery_location: str

# --- Endpoints --- 

@router.post(
    "/location_lookup",
    response_model=GenericResponse[MessageResponse], # Updated response_model
    summary="Trigger Background Location Distance Calculation",
    description="Accepts a delivery location and triggers an asynchronous task to calculate and cache the distance to the nearest branch. Returns immediately.",
    # Removed tags here, they should be applied when including the router in api.py
)
async def webhook_location_lookup(
    payload: LocationLookupRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationService = Depends(get_location_service_dep), # Use core dependency
    redis_service: RedisService = Depends(get_redis_service), # Use direct injector
    api_key: str = Depends(get_api_key) # Enforce API Key Auth
):
    """
    Webhook endpoint to initiate background caching of location distance.
    - Validates API Key.
    - Receives `delivery_location`.
    - Adds a background task to call `location_service.prefetch_distance`.
    - Returns `202 Accepted` immediately.
    """
    logger.info(f"Received location_lookup webhook for: {payload.delivery_location}")
    
    # Add background tasks
    background_tasks.add_task(location_service.prefetch_distance, payload.delivery_location)
    background_tasks.add_task(increment_request_counter_bg, redis_service, TOTAL_LOCATION_LOOKUPS_KEY)
    # Optionally log the request itself (without response yet)
    # background_tasks.add_task(log_request_response_bg, redis_service, ...) 
    
    logger.info(f"Background tasks added for prefetching distance and incrementing counter for: {payload.delivery_location}")
    # Return 202 immediately, indicating the request is accepted for processing
    return GenericResponse(data=MessageResponse(message="Location lookup accepted for background processing."))


@router.post(
    "/quote",
    response_model=GenericResponse[QuoteResponse], # Updated response_model
    summary="Generate Real-time Price Quote",
    description="Calculates a price quote based on provided details, utilizing cached pricing and location data. Requires prior location lookup for optimal performance.",
    # Removed tags here
)
async def webhook_quote(
    payload: QuoteRequest,
    background_tasks: BackgroundTasks, # Keep for error logging
    quote_service: QuoteService = Depends(get_quote_service), # Use injector from quote.py
    redis_service: RedisService = Depends(get_redis_service), # Use direct injector for error logging
    api_key: str = Depends(get_api_key)
) -> GenericResponse[QuoteResponse]: # Updated return type hint
    """
    Webhook endpoint to generate a price quote. Middleware handles request/response logging.
    """
    request_id = payload.request_id

    try:
        logger.info(f"Received quote webhook for request_id: {request_id}")
        quote_response = await quote_service.build_quote(payload)
        return GenericResponse(data=quote_response) # Return GenericResponse on success
    except ValueError as ve:
        logger.warning(f"Value error building quote for request {request_id}: {ve}")
        background_tasks.add_task(log_error_bg, redis_service, "ValueError", str(ve), {"request_id": request_id})
        return GenericResponse.error(message=str(ve), details={"request_id": request_id}) # Return GenericResponse on error
    except Exception as e:
        logger.exception(f"Unexpected error building quote for request {request_id}", exc_info=e)
        background_tasks.add_task(log_error_bg, redis_service, type(e).__name__, str(e), {"request_id": request_id})
        return GenericResponse.error(message="An internal error occurred while generating the quote.", details={"error_type": type(e).__name__, "request_id": request_id}) # Return GenericResponse on error
