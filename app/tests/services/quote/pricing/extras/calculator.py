# app/tests/services/quote/pricing/extras/calculator.py
"""Tests for extras pricing calculator."""

from decimal import Decimal
from unittest.mock import Mock, AsyncMock

from app.services.quote.pricing.extras.calculator import ExtrasCalculator
from app.models.quote import ExtraInput, LineItem


class TestExtrasCalculator:
  """Test cases for ExtrasCalculator."""

  def setup_method(self):
    """Set up test fixtures."""
    self.mock_manager = Mock()
    self.calculator = ExtrasCalculator(self.mock_manager)

  async def test_calculate_extras_cost_empty(self):
    """Test calculation with no extras."""
    # Arrange
    extras_input = []
    trailer_id = "standard_20"
    rental_days = 30
    catalog = {"generators": {}, "products": {}}

    # Act
    result = await self.calculator.calculate_extras_cost(
        extras_input, trailer_id, rental_days, catalog
    )

    # Assert
    assert result == []

  async def test_calculate_extras_cost_generator(self):
    """Test calculation with generator extra."""
    # Arrange
    extras_input = [ExtraInput(extra_id="gen_5000", qty=1)]
    trailer_id = "standard_20"
    rental_days = 30
    catalog = {
        "generators": {
            "gen_5000": {
                "name": "5000W Generator",
                "daily_rate": "15.00"
            }
        },
        "products": {}
    }

    # Mock the generator cost calculation
    self.calculator._calculate_generator_cost = AsyncMock(
        return_value=(450.0, 15.0, "1x 5000W Generator")
    )

    # Act
    result = await self.calculator.calculate_extras_cost(
        extras_input, trailer_id, rental_days, catalog
    )

    # Assert
    assert len(result) == 1
    assert result[0].total == 450.0
    assert result[0].unit_price == 15.0

  async def test_calculate_extras_cost_service(self):
    """Test calculation with service extra."""
    # Arrange
    extras_input = [ExtraInput(extra_id="maintenance_plan", qty=1)]
    trailer_id = "standard_20"
    rental_days = 30
    catalog = {
        "generators": {},
        "products": {
            "standard_20": {
                "extras": {
                    "maintenance_plan": {
                        "name": "Monthly Maintenance",
                        "cost": 50.0
                    }
                }
            }
        }
    }

    # Act
    result = await self.calculator.calculate_extras_cost(
        extras_input, trailer_id, rental_days, catalog
    )

    # Assert
    assert len(result) == 1
    line_item = result[0]
    assert line_item.description.startswith("1x maintenance_plan")
    assert line_item.total == 50.0

  async def test_calculate_extras_cost_multiple(self):
    """Test calculation with multiple extras."""
    # Arrange
    extras_input = [
        ExtraInput(extra_id="gen_5000", qty=1),
        ExtraInput(extra_id="locks", qty=3)
    ]
    trailer_id = "standard_20"
    rental_days = 30
    catalog = {
        "generators": {
            "gen_5000": {"name": "5000W Generator", "daily_rate": "15.00"}
        },
        "products": {
            "standard_20": {
                "extras": {
                    "locks": {"name": "Security Lock", "cost": 10.0}
                }
            }
        }
    }

    # Mock generator calculation
    self.calculator._calculate_generator_cost = AsyncMock(
        return_value=(450.0, 15.0, "1x 5000W Generator")
    )

    # Act
    result = await self.calculator.calculate_extras_cost(
        extras_input, trailer_id, rental_days, catalog
    )

    # Assert
    assert len(result) == 2

    # Generator extra - find by description pattern
    gen_item = next(item for item in result if "gen_5000" in item.description)
    assert gen_item.total == 450.0

    # Service extra - find by description pattern
    lock_item = next(item for item in result if "locks" in item.description)
    assert lock_item.total == 30.0  # 10.0 * 3 qty
