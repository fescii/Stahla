# app/tests/services/quote/manager.py

"""
Tests for the main quote service manager.
"""

from unittest.mock import AsyncMock, MagicMock
from datetime import date

from app.services.quote.manager import QuoteService
from app.models.quote import QuoteRequest


class TestQuoteServiceManager:
  """Test cases for quote service manager."""

  def setup_method(self):
    """Setup test dependencies."""
    self.redis_service = AsyncMock()
    self.location_service = AsyncMock()
    self.mongo_service = AsyncMock()

    self.quote_service = QuoteService(
        redis_service=self.redis_service,
        location_service=self.location_service,
        mongo_service=self.mongo_service,
    )

  def test_initialization(self):
    """Test that quote service initializes properly."""
    assert self.quote_service.redis_service is not None
    assert self.quote_service.location_service is not None
    assert self.quote_service.mongo_service is not None
    assert self.quote_service.catalog is not None
    assert self.quote_service.delivery is not None
    assert self.quote_service.extras is not None
    assert self.quote_service.seasonal is not None
    assert self.quote_service.trailer is not None
    assert self.quote_service.quote_builder is not None

  async def test_build_quote_delegation(self):
    """Test that build quote delegates to orchestrator."""
    request = QuoteRequest(
        delivery_location="123 Main St, Omaha, NE",
        trailer_type="3_stall_ada",
        rental_start_date=date(2024, 6, 15),
        rental_days=7,
        usage_type="event",
        extras=[]
    )

    # Mock the orchestrator
    mock_response = MagicMock()
    self.quote_service.quote_builder.build_quote = AsyncMock(
        return_value=mock_response)

    result = await self.quote_service.build_quote(request)

    self.quote_service.quote_builder.build_quote.assert_called_once_with(
        request, None)
    assert result == mock_response

  async def test_get_config_delegation(self):
    """Test that get config delegates to catalog."""
    mock_config = {"products": [], "generators": []}
    self.quote_service.catalog.get_config_for_quoting = AsyncMock(
        return_value=mock_config)

    result = await self.quote_service.get_config_for_quoting()

    self.quote_service.catalog.get_config_for_quoting.assert_called_once()
    assert result == mock_config

  def test_delivery_cost_delegation(self):
    """Test that delivery cost calculation delegates properly."""
    mock_cost = 25.0
    self.quote_service.delivery.get_delivery_cost_for_distance = MagicMock(
        return_value=mock_cost)

    result = self.quote_service.get_delivery_cost_for_distance(
        distance_miles=50.0,
        delivery_config={"base_rate": 1.0},
        branch_name="omaha"
    )

    self.quote_service.delivery.get_delivery_cost_for_distance.assert_called_once_with(
        50.0, {"base_rate": 1.0}, "omaha"
    )
    assert result == mock_cost
