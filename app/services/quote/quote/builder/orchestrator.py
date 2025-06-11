# app/services/quote/quote/builder/orchestrator.py

"""
Main quote building orchestrator that coordinates all quote calculation steps.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta

from app.models.quote import QuoteRequest, QuoteResponse, QuoteBody
from app.services.quote.quote.builder.catalog.loader import CatalogLoader
from app.services.quote.quote.builder.distance.calculator import DistanceCalculator
from app.services.quote.quote.builder.trailer.pricer import TrailerPricer
from app.services.quote.quote.builder.delivery.pricer import DeliveryPricer
from app.services.quote.quote.builder.extras.pricer import ExtrasPricer
from app.services.quote.quote.builder.response.formatter import ResponseFormatter

logger = logging.getLogger(__name__)


class QuoteBuildingOrchestrator:
  """Orchestrates the complete quote building process."""

  def __init__(self, manager):
    self.manager = manager

    # Initialize building components
    self.catalog_loader = CatalogLoader(manager)
    self.distance_calculator = DistanceCalculator(manager)
    self.trailer_pricer = TrailerPricer(manager)
    self.delivery_pricer = DeliveryPricer(manager)
    self.extras_pricer = ExtrasPricer(manager)
    self.response_formatter = ResponseFormatter(manager)

  async def build_quote(
      self,
      request: QuoteRequest,
      background_tasks: Optional[Any] = None,
  ) -> QuoteResponse:
    """
    Builds a complete quote response based on the request.

    Args:
        request: The quote request
        background_tasks: FastAPI background tasks for async operations

    Returns:
        Complete quote response
    """
    logger.info(f"Building quote for request_id: {request.request_id}")

    # Step 1: Load pricing catalog
    catalog = await self.catalog_loader.load_catalog()

    # Step 2: Calculate delivery distance
    distance_result = await self.distance_calculator.calculate_distance(
        request.delivery_location, background_tasks
    )

    # Step 3: Calculate trailer cost
    trailer_cost_result = await self.trailer_pricer.calculate_trailer_price(
        request, catalog
    )

    # Step 4: Calculate delivery cost
    delivery_result = await self.delivery_pricer.calculate_delivery_cost(
        request, catalog, distance_result
    )

    # Step 5: Calculate extras cost
    extras_result = await self.extras_pricer.calculate_extras_cost(
        request, catalog
    )

    # Step 6: Format response
    response = self.response_formatter.format_quote_response(
        request,
        catalog,
        distance_result,
        trailer_cost_result,
        delivery_result,
        extras_result
    )

    logger.info(
        f"Quote built successfully for request_id: {request.request_id}, quote_id: {response.quote_id}"
    )

    return response
