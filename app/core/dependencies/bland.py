"""
Core dependency injection module for Bland AI services.
"""

from app.services.bland import get_bland_manager, BlandAIManager


def get_bland_manager_dep() -> BlandAIManager:
  """
  Get the BlandAI manager singleton instance.
  """
  return get_bland_manager()
