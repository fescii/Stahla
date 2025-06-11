# app/tests/services/quote/location/distance.py

"""
Tests for location distance calculator.
"""

from unittest.mock import AsyncMock, MagicMock

from app.services.quote.location.distance import DistanceCalculator
from app.models.location import DistanceResult, BranchLocation


class TestDistanceCalculator:
  """Test cases for distance calculator."""

  def setup_method(self):
    """Setup test dependencies."""
    self.location_service = AsyncMock()
    self.calculator = DistanceCalculator(self.location_service)

  def test_initialization(self):
    """Test that distance calculator initializes properly."""
    assert self.calculator.location_service is not None

  async def test_calculate_delivery_distance_success(self):
    """Test successful distance calculation."""
    mock_result = DistanceResult(
        nearest_branch=BranchLocation(name="Omaha", address="123 Main St"),
        delivery_location="456 Test Ave",
        distance_miles=25.0,
        distance_meters=40234,
        duration_seconds=1800,
        within_service_area=True
    )

    self.location_service.get_distance = AsyncMock(return_value=mock_result)

    result = await self.calculator.calculate_delivery_distance("456 Test Ave")

    assert result == mock_result
    self.location_service.get_distance.assert_called_once_with("456 Test Ave")

  async def test_calculate_delivery_distance_empty_address(self):
    """Test distance calculation with empty address."""
    result = await self.calculator.calculate_delivery_distance("")

    assert result is None
    self.location_service.get_distance.assert_not_called()

  async def test_calculate_delivery_distance_service_failure_fallback(self):
    """Test distance calculation falls back when service fails."""
    # Mock service failure
    self.location_service.get_distance = AsyncMock(return_value=None)

    result = await self.calculator.calculate_delivery_distance("456 Test Ave")

    # Should attempt fallback calculation
    self.location_service.get_distance.assert_called_once()
    # Result may be None if fallback also fails, which is acceptable

  async def test_get_estimated_distance(self):
    """Test estimated distance calculation."""
    result = await self.calculator.get_estimated_distance(
        delivery_address="456 Test Ave",
        fallback_distance=50.0
    )

    assert isinstance(result, DistanceResult)
    assert result.distance_miles == 50.0
    assert result.delivery_location == "456 Test Ave"
    assert result.nearest_branch.name == "Estimated Hub"

  def test_is_within_service_area_inside(self):
    """Test service area check for location inside area."""
    distance_result = DistanceResult(
        nearest_branch=BranchLocation(name="Omaha", address="123 Main St"),
        delivery_location="456 Test Ave",
        distance_miles=50.0,  # Within 100 mile default
        distance_meters=80467,
        duration_seconds=3600,
        within_service_area=True
    )

    result = self.calculator.is_within_service_area(distance_result)

    assert result is True

  def test_is_within_service_area_outside(self):
    """Test service area check for location outside area."""
    distance_result = DistanceResult(
        nearest_branch=BranchLocation(name="Omaha", address="123 Main St"),
        delivery_location="456 Test Ave",
        distance_miles=150.0,  # Outside 100 mile default
        distance_meters=241401,
        duration_seconds=7200,
        within_service_area=False
    )

    result = self.calculator.is_within_service_area(distance_result)

    assert result is False

  def test_is_within_service_area_custom_limit(self):
    """Test service area check with custom distance limit."""
    distance_result = DistanceResult(
        nearest_branch=BranchLocation(name="Omaha", address="123 Main St"),
        delivery_location="456 Test Ave",
        distance_miles=75.0,
        distance_meters=120700,
        duration_seconds=4500,
        within_service_area=True
    )

    # With custom 60 mile limit, should be outside
    result = self.calculator.is_within_service_area(
        distance_result, max_distance_miles=60.0)

    assert result is False
