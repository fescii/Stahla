# app/tests/services/hubspot/utils/helpers.py

"""Test HubSpot utility functions."""

import sys
import traceback
from pathlib import Path

# Add the project root to the path
project_path = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_path))


def test_utility_functions():
  """Test that utility functions work correctly."""
  print("Testing utility functions...")

  try:
    from app.services.hubspot.utils.helpers import (
        format_contact_for_hubspot,
        convert_date_to_timestamp_ms,
        _convert_date_to_timestamp_ms
    )

    # Test format_contact_for_hubspot
    test_data = {"email": "test@example.com",
                 "first_name": "Test", "last_name": "User"}
    formatted = format_contact_for_hubspot(test_data)
    assert isinstance(
        formatted, dict), "format_contact_for_hubspot should return dict"
    assert "properties" in formatted, "Formatted contact should have properties"
    print("✓ format_contact_for_hubspot works")

    # Test date conversion
    from datetime import datetime, timezone
    test_date = datetime.now()
    timestamp = convert_date_to_timestamp_ms(test_date)
    assert isinstance(
        timestamp, int), "convert_date_to_timestamp_ms should return int"
    print("✓ convert_date_to_timestamp_ms works")

    return True
  except Exception as e:
    print(f"✗ Utility function error: {e}")
    traceback.print_exc()
    return False


if __name__ == "__main__":
  success = test_utility_functions()
  sys.exit(0 if success else 1)
