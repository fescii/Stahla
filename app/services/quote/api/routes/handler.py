# app/services/quote/api/routes/handler.py

"""
API route handlers for quote service.
"""

import logging
from typing import Any, Dict, Optional
import time

import logfire
from fastapi import HTTPException, BackgroundTasks

from app.models.quote import QuoteRequest, QuoteResponse
from app.services.quote.manager import QuoteService
from app.services.quote.background.tasks.processor import BackgroundTaskHelper
from app.services.quote.logging.error.reporter import ErrorReporter
from app.services.quote.logging.metrics.counter import MetricsCounter

logger = logging.getLogger(__name__)


class QuoteRouteHandler:
  """Handles quote API route processing."""

  def __init__(
      self,
      quote_service: QuoteService,
      error_reporter: ErrorReporter,
      metrics_counter: MetricsCounter
  ):
    self.quote_service = quote_service
    self.error_reporter = error_reporter
    self.metrics_counter = metrics_counter

  async def handle_quote_request(
      self,
      request: QuoteRequest,
      background_tasks: BackgroundTasks
  ) -> QuoteResponse:
    """
    Handle a quote request with full error handling and metrics.

    Args:
        request: The quote request
        background_tasks: FastAPI background tasks

    Returns:
        QuoteResponse with quote details

    Raises:
        HTTPException: If quote generation fails
    """
    start_time = time.time()
    request_data = request.model_dump() if hasattr(
        request, 'model_dump') else request.dict()

    try:
      # Record request metric
      await self.metrics_counter.increment_quote_request()

      logfire.info("Processing quote request", request_data=request_data)

      # Generate the quote
      quote_response = await self.quote_service.build_quote(
          quote_request=request,
          background_tasks=background_tasks
      )

      # Record success metrics
      processing_time = (time.time() - start_time) * 1000  # Convert to ms
      await self.metrics_counter.increment_quote_success()
      await self.metrics_counter.record_processing_time("quote_generation", processing_time)

      logfire.info(
          "Quote request processed successfully",
          processing_time_ms=processing_time,
          quote_total=getattr(quote_response, 'total_cost', None)
      )

      return quote_response

    except ValueError as e:
      # Handle validation errors
      await self._handle_quote_error(
          error=e,
          error_type="ValidationError",
          request_data=request_data,
          background_tasks=background_tasks,
          status_code=400
      )

    except Exception as e:
      # Handle unexpected errors
      await self._handle_quote_error(
          error=e,
          error_type="UnexpectedError",
          request_data=request_data,
          background_tasks=background_tasks,
          status_code=500
      )

  async def handle_config_request(self) -> Dict[str, Any]:
    """
    Handle configuration request.

    Returns:
        Configuration data for quote generation
    """
    try:
      logfire.info("Processing config request")

      config = await self.quote_service.get_config_for_quoting()

      logfire.info("Config request processed successfully")
      return config

    except Exception as e:
      await self.error_reporter.report_error(
          service_name="QuoteAPI",
          error_type="ConfigError",
          message=f"Failed to get config: {str(e)}",
          immediate=True
      )

      raise HTTPException(
          status_code=500,
          detail="Failed to retrieve configuration"
      )

  async def handle_distance_request(
      self,
      address: str,
      background_tasks: BackgroundTasks
  ) -> Dict[str, Any]:
    """
    Handle distance calculation request.

    Args:
        address: The address to calculate distance for
        background_tasks: FastAPI background tasks

    Returns:
        Distance calculation results
    """
    try:
      logfire.info("Processing distance request", address=address)

      # Use the quote service's distance calculation
      distance_result = await self.quote_service._estimate_distance_when_location_service_fails(
          delivery_location_str=address
      )

      if distance_result:
        # Convert km to miles for consistency
        distance_km = distance_result.distance_miles / 0.621371
        result = {
            "address": address,
            "distance_km": distance_km,
            "distance_miles": distance_result.distance_miles,
            "nearest_hub": distance_result.nearest_branch.name,
            "success": True
        }
      else:
        result = {
            "address": address,
            "distance_km": None,
            "distance_miles": None,
            "nearest_hub": None,
            "success": False,
            "error": "Could not calculate distance"
        }

      logfire.info("Distance request processed", result=result)
      return result

    except Exception as e:
      # Log error in background
      BackgroundTaskHelper.add_error_logging_task(
          background_tasks,
          self.quote_service.mongo_service,
          "QuoteAPI",
          "DistanceError",
          f"Distance calculation failed for {address}: {str(e)}"
      )

      raise HTTPException(
          status_code=500,
          detail="Failed to calculate distance"
      )

  async def _handle_quote_error(
      self,
      error: Exception,
      error_type: str,
      request_data: Dict[str, Any],
      background_tasks: BackgroundTasks,
      status_code: int
  ):
    """Handle quote generation errors with proper logging and metrics."""

    # Record error metrics
    await self.metrics_counter.increment_quote_error(error_type)

    # Log error in background
    BackgroundTaskHelper.add_error_logging_task(
        background_tasks,
        self.quote_service.mongo_service,
        "QuoteService",
        error_type,
        f"Quote generation failed: {str(error)}",
        {"request_data": request_data}
    )

    # Log to application logs immediately
    logfire.error(
        f"Quote generation failed: {error}",
        error_type=error_type,
        request_data=request_data
    )

    # Determine user-friendly error message
    if error_type == "ValidationError":
      detail = f"Invalid request data: {str(error)}"
    else:
      detail = "An error occurred while generating the quote. Please try again."

    raise HTTPException(
        status_code=status_code,
        detail=detail
    )
