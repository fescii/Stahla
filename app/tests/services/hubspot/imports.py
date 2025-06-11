# app/tests/services/hubspot/imports.py

"""Test imports for HubSpot service structure."""

import sys
import traceback
from pathlib import Path

# Add the project root to the path
project_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_path))


def test_imports():
  """Test that all imports work correctly."""
  print("Testing imports...")

  try:
    # Test main manager import
    from app.services.hubspot import HubSpotManager
    print("✓ HubSpotManager import successful")

    # Test individual operation imports
    from app.services.hubspot.contact.operations import ContactOperations
    from app.services.hubspot.company.operations import CompanyOperations
    from app.services.hubspot.lead.operations import LeadOperations
    from app.services.hubspot.owner.operations import OwnerOperations
    from app.services.hubspot.pipeline.operations import PipelineOperations
    from app.services.hubspot.association.operations import AssociationOperations
    from app.services.hubspot.property.operations import PropertyOperations
    from app.services.hubspot.utils.helpers import format_contact_for_hubspot, convert_date_to_timestamp_ms

    print("✓ All operation class imports successful")

    return True
  except Exception as e:
    print(f"✗ Import error: {e}")
    traceback.print_exc()
    return False


if __name__ == "__main__":
  success = test_imports()
  sys.exit(0 if success else 1)
