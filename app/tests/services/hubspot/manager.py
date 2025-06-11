# app/tests/services/hubspot/manager.py

"""Test HubSpot manager instantiation and basic functionality."""

import sys
import traceback
from pathlib import Path

# Add the project root to the path
project_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_path))


def test_manager_instantiation():
  """Test that HubSpotManager can be instantiated."""
  print("Testing manager instantiation...")

  try:
    from app.services.hubspot import HubSpotManager

    # Test instantiation
    manager = HubSpotManager(access_token="test_key")
    print("✓ HubSpotManager instantiation successful")

    # Test that all operation classes are accessible
    assert hasattr(manager, 'contact'), "ContactOperations not accessible"
    assert hasattr(manager, 'company'), "CompanyOperations not accessible"
    assert hasattr(manager, 'lead'), "LeadOperations not accessible"
    assert hasattr(manager, 'owner'), "OwnerOperations not accessible"
    assert hasattr(manager, 'pipeline'), "PipelineOperations not accessible"
    assert hasattr(
        manager, 'association'), "AssociationOperations not accessible"
    assert hasattr(manager, 'property'), "PropertyOperations not accessible"

    print("✓ All operation classes accessible through manager")

    return True
  except Exception as e:
    print(f"✗ Manager instantiation error: {e}")
    traceback.print_exc()
    return False


if __name__ == "__main__":
  success = test_manager_instantiation()
  sys.exit(0 if success else 1)
