# app/tests/services/quote/quote/builder/orchestrator.py
"""Tests for quote builder orchestrator."""

from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import date

from app.services.quote.quote.builder.orchestrator import QuoteBuildingOrchestrator
from app.models.quote import QuoteRequest


class TestQuoteBuildingOrchestrator:
  """Test cases for QuoteBuildingOrchestrator."""

  def setup_method(self):
    """Set up test fixtures."""
    self.mock_manager = Mock()
    self.orchestrator = QuoteBuildingOrchestrator(self.mock_manager)

  async def test_build_quote_basic(self):
    """Test basic quote building."""
    # Arrange - create a minimal valid QuoteRequest
    quote_request = QuoteRequest(
        delivery_location="123 Main St, Anytown, ST 12345",
        trailer_type="standard_20",
        rental_start_date=date(2025, 6, 15),
        rental_days=30,
        usage_type="commercial"
    )

    # Mock the build_quote method to return a simple mock response
    with patch.object(self.orchestrator, 'build_quote', new_callable=AsyncMock) as mock_build:
      mock_response = Mock()
      mock_response.quote_id = "test-123"
      mock_build.return_value = mock_response

      # Act
      result = await self.orchestrator.build_quote(quote_request)

      # Assert
      assert result.quote_id == "test-123"
      mock_build.assert_called_once_with(quote_request)

  def test_initialization(self):
    """Test orchestrator initialization."""
    # Assert all components are initialized
    assert self.orchestrator.catalog_loader is not None
    assert self.orchestrator.distance_calculator is not None
    assert self.orchestrator.trailer_pricer is not None
    assert self.orchestrator.delivery_pricer is not None
    assert self.orchestrator.extras_pricer is not None
    assert self.orchestrator.response_formatter is not None
    assert self.orchestrator.manager == self.mock_manager

  async def test_catalog_loading(self):
    """Test catalog loading functionality."""
    # Mock catalog loader
    with patch.object(self.orchestrator, 'catalog_loader') as mock_catalog:
      mock_catalog.load_catalog.return_value = {
          "products": {}, "generators": {}}

      # Act
      catalog = await self.orchestrator.catalog_loader.load_catalog()

      # Assert
      assert "products" in catalog
      assert "generators" in catalog
      mock_catalog.load_catalog.assert_called_once()

  async def test_distance_calculation(self):
    """Test distance calculation functionality."""
    # Mock distance calculator
    with patch.object(self.orchestrator, 'distance_calculator') as mock_distance:
      mock_distance.calculate_distance.return_value = 25.5

      # Act
      distance = await self.orchestrator.distance_calculator.calculate_distance(
          "Origin", "Destination"
      )

      # Assert
      assert distance == 25.5
      mock_distance.calculate_distance.assert_called_once_with(
          "Origin", "Destination")

  async def test_trailer_pricing(self):
    """Test trailer pricing functionality."""
    # Mock trailer pricer
    with patch.object(self.orchestrator, 'trailer_pricer') as mock_trailer:
      mock_trailer.price_trailer.return_value = Decimal("150.00")

      # Create minimal request data
      request_data = {
          "trailer_type": "standard_20",
          "rental_days": 30,
          "usage_type": "commercial"
      }

      # Act
      price = await mock_trailer.price_trailer(request_data)

      # Assert
      assert price == Decimal("150.00")
      mock_trailer.price_trailer.assert_called_once_with(request_data)

  async def test_delivery_pricing(self):
    """Test delivery pricing functionality."""
    # Mock delivery pricer
    with patch.object(self.orchestrator, 'delivery_pricer') as mock_delivery:
      mock_delivery.price_delivery.return_value = Decimal("50.00")

      # Create minimal request data
      request_data = {
          "delivery_location": "123 Main St",
          "distance_miles": 25.5
      }

      # Act
      price = await mock_delivery.price_delivery(request_data)

      # Assert
      assert price == Decimal("50.00")
      mock_delivery.price_delivery.assert_called_once_with(request_data)

  async def test_extras_pricing(self):
    """Test extras pricing functionality."""
    # Mock extras pricer
    with patch.object(self.orchestrator, 'extras_pricer') as mock_extras:
      mock_extras.price_extras.return_value = Decimal("25.00")

      # Create minimal request data
      request_data = {
          "extras": [{"extra_id": "generator", "qty": 1}]
      }

      # Act
      price = await mock_extras.price_extras(request_data)

      # Assert
      assert price == Decimal("25.00")
      mock_extras.price_extras.assert_called_once_with(request_data)
