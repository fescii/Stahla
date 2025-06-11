# app/tests/services/hubspot/methods.py

"""Test HubSpot service method accessibility."""

import sys
import traceback
from pathlib import Path

# Add the project root to the path
project_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_path))


def test_method_accessibility():
  """Test that all methods are accessible through the manager."""
  print("Testing method accessibility...")

  try:
    from app.services.hubspot import HubSpotManager
    manager = HubSpotManager(access_token="test_key")

    # Test contact methods
    contact_methods = [
        'create', 'get_by_email', 'get_by_id', 'update_contact',
        'delete_contact', 'create_or_update_contact', 'search'
    ]
    for method in contact_methods:
      assert hasattr(
          manager.contact, method), f"Contact method {method} not found"
    print("✓ All contact methods accessible")

    # Test company methods
    company_methods = ['create', 'get_by_domain', 'update', 'delete', 'search']
    for method in company_methods:
      assert hasattr(
          manager.company, method), f"Company method {method} not found"
    print("✓ All company methods accessible")

    # Test lead methods
    lead_methods = [
        'create', 'get_by_id', 'update_properties',
        'associate_to_contact', 'search', 'create_or_update_contact_and_lead'
    ]
    for method in lead_methods:
      assert hasattr(manager.lead, method), f"Lead method {method} not found"
    print("✓ All lead methods accessible")

    # Test owner methods
    owner_methods = ['get_owners', 'get_owner_by_email', 'search_by_criteria']
    for method in owner_methods:
      assert hasattr(manager.owner, method), f"Owner method {method} not found"
    print("✓ All owner methods accessible")

    # Test pipeline methods
    pipeline_methods = [
        'get_pipelines', 'get_pipeline_stages', 'get_pipeline_by_id', 'get_default_pipeline'
    ]
    for method in pipeline_methods:
      assert hasattr(manager.pipeline,
                     method), f"Pipeline method {method} not found"
    print("✓ All pipeline methods accessible")

    # Test association methods
    association_methods = ['associate_objects', 'batch_associate_objects']
    for method in association_methods:
      assert hasattr(manager.association,
                     method), f"Association method {method} not found"
    print("✓ All association methods accessible")

    # Test property methods
    property_methods = [
        'create_property', 'get_property', 'get_all_properties',
        'batch_create_properties', 'create_property_full'
    ]
    for method in property_methods:
      assert hasattr(manager.property,
                     method), f"Property method {method} not found"
    print("✓ All property methods accessible")

    return True
  except Exception as e:
    print(f"✗ Method accessibility error: {e}")
    traceback.print_exc()
    return False


if __name__ == "__main__":
  success = test_method_accessibility()
  sys.exit(0 if success else 1)
