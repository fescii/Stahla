# app/tests/services/hubspot/runner.py

"""Test runner for all HubSpot service tests."""

from app.tests.services.hubspot.utils.helpers import test_utility_functions
from app.tests.services.hubspot.methods import test_method_accessibility
from app.tests.services.hubspot.manager import test_manager_instantiation
from app.tests.services.hubspot.imports import test_imports
import sys
from pathlib import Path

# Add the project root to the path
project_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_path))

# Import test functions using absolute imports


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
    print()  # Add spacing between tests

  print(f"=== Test Results ===")
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
