import time
import logfire
from fastapi import APIRouter, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Any

# Model imports
from app.models.location import (
    BranchLocation,
    LocationLookupRequest as LocationServiceRequest,
    DistanceResult,
)  # Changed Branch to BranchLocation
from app.models.quote import QuoteRequest, QuoteResponse

# Service and dependency imports
from app.services.location import LocationService
from app.services.quote import (
    QuoteService,
    get_quote_service,
)  # Import get_quote_service directly
from app.core.dependencies import get_location_service_dep
from app.models.common import GenericResponse  # Added import

router = APIRouter()

# --- Response Models for Test Endpoints ---


class LocationServiceTestData(BaseModel):
  branch: Optional[BranchLocation] = None  # Changed Branch to BranchLocation
  distance_km: Optional[float] = None
  error_message: Optional[str] = Field(
      default=None, description="Error message if processing failed"
  )


class LocationServiceTestResponse(BaseModel):
  data: Optional[LocationServiceTestData] = None
  processing_time_ms: float = Field(
      ...,
      description="Time taken for the service to process the request in milliseconds",
  )


class QuoteServiceTestResponse(BaseModel):
  # QuoteResponse is the data from the service
  data: Optional[QuoteResponse] = None
  processing_time_ms: float = Field(
      ...,
      description="Time taken for the service to process the request in milliseconds",
  )
  error_message: Optional[str] = Field(
      default=None, description="Error message if processing failed"
  )


# --- Test Endpoints ---


@router.post(
    "/location", response_model=GenericResponse[LocationServiceTestResponse]
)  # Updated response_model
async def test_location_service(
    request_payload: LocationServiceRequest,
    background_tasks: BackgroundTasks,
    location_service: LocationService = Depends(get_location_service_dep),
):
  """
  Tests the location service by calling `get_distance_to_nearest_branch`
  and returns the service's response along with processing time.
  """
  logfire.info(
      f"Test endpoint: Received location service test request for: {request_payload.delivery_location}"
  )
  start_time = time.perf_counter()
  # Changed Branch to BranchLocation
  branch_info: Optional[BranchLocation] = None
  distance: Optional[float] = None
  error_msg: Optional[str] = None

  try:
    # Use the correct method that returns DistanceResult
    distance_result = await location_service.get_distance_to_nearest_branch(
        request_payload.delivery_location, background_tasks
    )
    if distance_result:
      branch_info = distance_result.nearest_branch
      distance = distance_result.distance_miles
    else:
      # This case could be that no branch is found or an issue occurred internally that didn't raise an exception
      logfire.info(
          f"Test location service: No branch found or data unavailable for {request_payload.delivery_location}"
      )
      # Depending on desired behavior, this could be an error or just null data
      # For now, let's return null data without an error_message unless an explicit error is caught.
  except Exception as e:
    logfire.error(
        f"Test location service: Error processing {request_payload.delivery_location}: {e}",
        exc_info=True,
    )
    error_msg = str(e)

  end_time = time.perf_counter()
  processing_time_ms = (end_time - start_time) * 1000

  response_data = LocationServiceTestData(
      branch=branch_info, distance_km=distance, error_message=error_msg
  )

  test_response = LocationServiceTestResponse(
      data=(
          response_data if not error_msg else None
      ),  # Only include data if no error, or adjust as needed
      processing_time_ms=processing_time_ms,
  )
  if error_msg:
    return GenericResponse.error(
        message="Location service test failed", details=error_msg, status_code=500
    )  # Return GenericResponse.error
  return GenericResponse(data=test_response)  # Wrapped in GenericResponse


@router.post(
    "/quote", response_model=GenericResponse[QuoteServiceTestResponse]
)  # Updated response_model
async def test_quote_service(
    request_payload: QuoteRequest,
    quote_service: QuoteService = Depends(
        get_quote_service
    ),  # Use get_quote_service directly
):
  """
  Tests the quote service by calling `build_quote`
  and returns the service's response along with processing time.
  """
  logfire.info(
      f"Test endpoint: Received quote service test request for ID: {request_payload.request_id}"
  )
  start_time = time.perf_counter()
  quote_data: Optional[QuoteResponse] = None
  error_msg: Optional[str] = None
  is_value_error = False

  try:
    quote_data = await quote_service.build_quote(request_payload)
  except ValueError as ve:  # Specific error handling as seen in webhook
    logfire.warn(
        f"Test quote service: Value error for request {request_payload.request_id}: {ve}"
    )
    error_msg = str(ve)
    is_value_error = True
  except Exception as e:
    logfire.error(
        f"Test quote service: Error processing quote request {request_payload.request_id}: {e}",
        exc_info=True,
    )
    error_msg = str(e)
    # Consider raising HTTPException for unexpected errors if preferred
    # raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

  end_time = time.perf_counter()
  processing_time_ms = (end_time - start_time) * 1000

  test_response = QuoteServiceTestResponse(
      data=quote_data if not error_msg else None,
      processing_time_ms=processing_time_ms,
      error_message=error_msg,
  )
  if error_msg:
    return GenericResponse.error(
        message="Quote service test failed",
        details=error_msg,
        status_code=400 if is_value_error else 500,
    )  # Return GenericResponse.error, adjust status for ValueError
  return GenericResponse(data=test_response)  # Wrapped in GenericResponse
