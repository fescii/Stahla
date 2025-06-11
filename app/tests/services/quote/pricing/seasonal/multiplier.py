# app/tests/services/quote/pricing/seasonal/multiplier.py
"""Tests for seasonal pricing multiplier."""

from decimal import Decimal
from datetime import date, datetime
from unittest.mock import Mock, patch

from app.services.quote.pricing.seasonal.multiplier import SeasonalMultiplier


class TestSeasonalMultiplier:
  """Test cases for SeasonalMultiplier."""

  def setup_method(self):
    """Set up test fixtures."""
    self.mock_manager = Mock()
    self.multiplier = SeasonalMultiplier(self.mock_manager)

  def test_determine_seasonal_multiplier_peak_season(self):
    """Test determining multiplier during peak season."""
    # Arrange
    rental_start_date = date(2024, 7, 15)  # Mid-July
    seasonal_config = {
        "standard": 1.0,
        "tiers": [
            {
                "name": "Summer Peak",
                "start_date": "2024-06-01",
                "end_date": "2024-08-31",
                "rate": 1.25
            }
        ]
    }

    # Act
    rate, description = self.multiplier.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # Assert
    assert rate == 1.25
    assert "Summer Peak" in description

  def test_determine_seasonal_multiplier_standard_season(self):
    """Test determining multiplier during standard season."""
    # Arrange
    rental_start_date = date(2024, 1, 15)  # Mid-January
    seasonal_config = {
        "standard": 1.0,
        "tiers": [
            {
                "name": "Summer Peak",
                "start_date": "2024-06-01",
                "end_date": "2024-08-31",
                "rate": 1.25
            }
        ]
    }

    # Act
    rate, description = self.multiplier.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # Assert
    assert rate == 1.0
    assert "Standard Season Rate" in description

  def test_determine_seasonal_multiplier_multiple_tiers(self):
    """Test determining multiplier with multiple seasonal tiers."""
    # Arrange
    rental_start_date = date(2024, 12, 15)  # Mid-December
    seasonal_config = {
        "standard": 1.0,
        "tiers": [
            {
                "name": "Summer Peak",
                "start_date": "2024-06-01",
                "end_date": "2024-08-31",
                "rate": 1.25
            },
            {
                "name": "Holiday Season",
                "start_date": "2024-12-01",
                "end_date": "2024-12-31",
                "rate": 1.15
            }
        ]
    }

    # Act
    rate, description = self.multiplier.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # Assert
    assert rate == 1.15
    assert "Holiday Season" in description

  def test_determine_seasonal_multiplier_invalid_tier(self):
    """Test handling invalid tier configuration."""
    # Arrange
    rental_start_date = date(2024, 7, 15)
    seasonal_config = {
        "standard": 1.0,
        "tiers": [
            {
                "name": "Invalid Tier",
                "start_date": "invalid-date",
                "end_date": "2024-08-31",
                "rate": 1.25
            }
        ]
    }

    # Act
    rate, description = self.multiplier.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # Assert - should fall back to standard rate
    assert rate == 1.0
    assert "Standard Season Rate" in description

  def test_determine_seasonal_multiplier_no_tiers(self):
    """Test determining multiplier with no tiers configured."""
    # Arrange
    rental_start_date = date(2024, 7, 15)
    seasonal_config = {
        "standard": 0.95,
        "tiers": []
    }

    # Act
    rate, description = self.multiplier.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # Assert
    assert rate == 0.95
    assert "Standard Season Rate" in description

  def test_determine_seasonal_multiplier_missing_rate(self):
    """Test tier without rate specification."""
    # Arrange
    rental_start_date = date(2024, 7, 15)
    seasonal_config = {
        "standard": 1.0,
        "tiers": [
            {
                "name": "No Rate Tier",
                "start_date": "2024-07-01",
                "end_date": "2024-07-31"
                # Missing rate field
            }
        ]
    }

    # Act
    rate, description = self.multiplier.determine_seasonal_multiplier(
        rental_start_date, seasonal_config
    )

    # Assert - should use standard rate as default
    assert rate == 1.0
    assert "No Rate Tier" in description
