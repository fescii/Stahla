"""
Core dependency injection module for Bland AI services.
"""

from app.services.bland import bland_manager, BlandAIManager


def get_bland_manager_dep() -> BlandAIManager:
  """
  Get the BlandAI manager singleton instance.
  """
  return bland_manager
