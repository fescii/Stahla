# app/tests/services/quote/runner.py
"""Test runner and validator for the modular quote service."""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any


class TestStructureValidator:
  """Validates the test structure follows modular conventions."""

  def __init__(self, base_path: str):
    self.base_path = Path(base_path)

  def validate_structure(self) -> Dict[str, Any]:
    """Validate the complete test structure."""
    results = {
        "valid": True,
        "errors": [],
        "warnings": [],
        "stats": {}
    }

    # Check for required test directories
    required_dirs = [
        "background/tasks",
        "location",
        "logging/error",
        "logging/metrics",
        "pricing/delivery",
        "pricing/extras",
        "pricing/seasonal",
        "pricing/trailer",
        "quote/builder",
        "sync"
    ]

    for dir_path in required_dirs:
      full_path = self.base_path / dir_path
      if not full_path.exists():
        results["errors"].append(f"Missing required directory: {dir_path}")
        results["valid"] = False

    # Check naming conventions
    self._validate_naming_conventions(results)

    # Count test files
    self._collect_stats(results)

    return results

  def _validate_naming_conventions(self, results: Dict[str, Any]):
    """Validate that all files follow lowercase naming conventions."""
    for file_path in self.base_path.rglob("*.py"):
      relative_path = file_path.relative_to(self.base_path)

      # Check each part of the path
      for part in relative_path.parts:
        if part == "__init__.py":
          continue

        if part.endswith(".py"):
          name = part[:-3]  # Remove .py extension
        else:
          name = part

        # Check for invalid characters
        if any(char in name for char in ["-", "_", "."]) and name != "__init__":
          if "-" in name or "." in name:
            results["errors"].append(
                f"Invalid naming: {relative_path} contains hyphens or dots"
            )
            results["valid"] = False
          elif "_" in name:
            results["warnings"].append(
                f"Warning: {relative_path} contains underscores (prefer camelCase)"
            )

        # Check for uppercase
        if not name.islower() and name != "__init__":
          results["errors"].append(
              f"Invalid naming: {relative_path} not lowercase"
          )
          results["valid"] = False

  def _collect_stats(self, results: Dict[str, Any]):
    """Collect statistics about the test structure."""
    stats = {
        "total_files": 0,
        "test_files": 0,
        "init_files": 0,
        "directories": 0,
        "max_depth": 0
    }

    for file_path in self.base_path.rglob("*"):
      if file_path.is_file():
        stats["total_files"] += 1
        if file_path.name == "__init__.py":
          stats["init_files"] += 1
        elif file_path.suffix == ".py":
          stats["test_files"] += 1

        # Calculate depth
        depth = len(file_path.relative_to(self.base_path).parts)
        stats["max_depth"] = max(stats["max_depth"], depth)

      elif file_path.is_dir():
        stats["directories"] += 1

    results["stats"] = stats


def main():
  """Main test validation function."""
  # Get the test directory path
  test_dir = Path(__file__).parent

  print("🧪 Validating Quote Service Test Structure")
  print("=" * 50)

  # Validate structure
  validator = TestStructureValidator(str(test_dir))
  results = validator.validate_structure()

  # Display results
  if results["valid"]:
    print("✅ Test structure validation PASSED")
  else:
    print("❌ Test structure validation FAILED")

  print(f"\n📊 Statistics:")
  stats = results["stats"]
  print(f"  - Total files: {stats['total_files']}")
  print(f"  - Test files: {stats['test_files']}")
  print(f"  - Init files: {stats['init_files']}")
  print(f"  - Directories: {stats['directories']}")
  print(f"  - Max depth: {stats['max_depth']}")

  if results["errors"]:
    print(f"\n❌ Errors ({len(results['errors'])}):")
    for error in results["errors"]:
      print(f"  - {error}")

  if results["warnings"]:
    print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
    for warning in results["warnings"]:
      print(f"  - {warning}")

  if not results["errors"] and not results["warnings"]:
    print("\n🎉 No issues found! Test structure is properly modularized.")

  # List all test modules
  print(f"\n📂 Test Modules:")
  test_files = list(test_dir.rglob("*.py"))
  test_files = [f for f in test_files if f.name !=
                "__init__.py" and f.name != "runner.py"]

  for test_file in sorted(test_files):
    relative_path = test_file.relative_to(test_dir)
    print(f"  - {relative_path}")

  return 0 if results["valid"] else 1


if __name__ == "__main__":
  sys.exit(main())
