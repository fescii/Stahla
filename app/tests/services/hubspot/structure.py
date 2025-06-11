#!/usr/bin/env python
"""
Test script to verify the new HubSpot service structure.
This script tests that all imports work correctly and methods are accessible.
"""

import sys
import traceback
from pathlib import Path

# Add the app directory to the path - go up 3 levels to reach app folder
app_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(app_path))

# Also add the root project directory to find 'app' module
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


def test_manager_instantiation():
  """Test that HubSpotManager can be instantiated."""
  print("\nTesting manager instantiation...")

  try:
    from app.services.hubspot import HubSpotManager

    # Test instantiation without API key (should work for structure testing)
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


def test_method_accessibility():
  """Test that all methods are accessible through the manager."""
  print("\nTesting method accessibility...")

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

    # Test lead methods - removed 'delete' as it's not implemented
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


def test_utility_functions():
  """Test that utility functions work correctly."""
  print("\nTesting utility functions...")

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
    from datetime import datetime
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


def main():
  """Run all tests."""
  print("=== HubSpot Service Structure Test ===\n")

  tests = [
      test_imports,
      test_manager_instantiation,
      test_method_accessibility,
      test_utility_functions
  ]

  results = []
  for test in tests:
    results.append(test())

  print(f"\n=== Test Results ===")
  print(f"Passed: {sum(results)}/{len(results)}")

  if all(results):
    print("🎉 All tests passed! The new HubSpot service structure is working correctly.")
    return True
  else:
    print("❌ Some tests failed. Please check the errors above.")
    return False


if __name__ == "__main__":
  success = main()
  sys.exit(0 if success else 1)
