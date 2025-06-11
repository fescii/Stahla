# app/tests/services/quote/pricing/delivery/calculator.py

"""
Tests for delivery pricing calculator.
"""

from unittest.mock import MagicMock

from app.services.quote.pricing.delivery.calculator import DeliveryCalculator
from app.models.location import DistanceResult, BranchLocation


class TestDeliveryCalculator:
  """Test cases for delivery pricing calculator."""

  def setup_method(self):
    """Setup test dependencies."""
    self.manager = MagicMock()
    self.calculator = DeliveryCalculator(self.manager)

  def test_initialization(self):
    """Test that delivery calculator initializes properly."""
    assert self.calculator.manager is not None

  async def test_calculate_delivery_cost_basic(self):
    """Test basic delivery cost calculation."""
    distance_result = DistanceResult(
        nearest_branch=BranchLocation(name="Omaha", address="123 Main St"),
        delivery_location="456 Test Ave",
        distance_miles=25.0,
        distance_meters=40234,
        duration_seconds=1800,
        within_service_area=True
    )

    catalog = {
        "delivery": {
            "base_fee": 50.0,
            "per_mile_rate": 2.5,
            "tiers": []
        }
    }

    result = await self.calculator.calculate_delivery_cost(
        distance_result=distance_result,
        catalog=catalog,
        rate_multiplier=1.0,
        season_desc="standard",
        is_distance_estimated=False
    )

    assert isinstance(result, dict)
    assert "cost" in result or "total_cost" in result

  async def test_calculate_delivery_cost_with_multiplier(self):
    """Test delivery cost calculation with rate multiplier."""
    distance_result = DistanceResult(
        nearest_branch=BranchLocation(name="Omaha", address="123 Main St"),
        delivery_location="456 Test Ave",
        distance_miles=25.0,
        distance_meters=40234,
        duration_seconds=1800,
        within_service_area=True
    )

    catalog = {
        "delivery": {
            "base_fee": 50.0,
            "per_mile_rate": 2.5,
            "tiers": []
        }
    }

    result = await self.calculator.calculate_delivery_cost(
        distance_result=distance_result,
        catalog=catalog,
        rate_multiplier=1.5,  # 50% increase
        season_desc="peak",
        is_distance_estimated=False
    )

    assert isinstance(result, dict)
    assert "cost" in result or "total_cost" in result

  def test_get_delivery_cost_for_distance_basic(self):
    """Test the legacy delivery cost method."""
    delivery_config = {
        "base_fee": 50.0,
        "per_mile_rate": 2.5
    }

    result = self.calculator.get_delivery_cost_for_distance(
        distance_miles=20.0,
        delivery_config=delivery_config,
        branch_name="omaha"
    )

    expected_cost = 50.0 + (20.0 * 2.5)  # base_fee + (distance * rate)
    assert result == expected_cost

  def test_get_delivery_cost_for_distance_zero_distance(self):
    """Test delivery cost calculation with zero distance."""
    delivery_config = {
        "base_fee": 50.0,
        "per_mile_rate": 2.5
    }

    result = self.calculator.get_delivery_cost_for_distance(
        distance_miles=0.0,
        delivery_config=delivery_config,
        branch_name="omaha"
    )

    expected_cost = 50.0  # Only base fee
    assert result == expected_cost
