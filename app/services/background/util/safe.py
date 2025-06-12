"""
Safe background task utilities that avoid circular imports.
These utilities can be imported from anywhere in the application.
"""

from typing import Any, Optional, Callable
from fastapi import BackgroundTasks


def get_background_tasks(service_instance: Any) -> Optional[BackgroundTasks]:
  """
  Safe method to get background tasks from a service instance.
  Returns None if no background tasks are available.

  Args:
      service_instance: Any service instance that might have background_tasks attribute

  Returns:
      BackgroundTasks object if available, None otherwise
  """
  if hasattr(service_instance, 'background_tasks'):
    return getattr(service_instance, 'background_tasks')

  # Also check redis_service if available
  if hasattr(service_instance, 'redis_service') and service_instance.redis_service is not None:
    if hasattr(service_instance.redis_service, 'background_tasks'):
      return getattr(service_instance.redis_service, 'background_tasks')

  return None


def add_task_safely(service_instance: Any, task_func: Callable, *args: Any, **kwargs: Any) -> bool:
  """
  Safely add a background task if background tasks are available.

  Args:
      service_instance: Any service instance that might have background_tasks
      task_func: The function to run as a background task
      *args: Arguments to pass to the task function
      **kwargs: Keyword arguments to pass to the task function

  Returns:
      True if task was added, False if no background tasks were available
  """
  bg_tasks = get_background_tasks(service_instance)
  if bg_tasks:
    bg_tasks.add_task(task_func, *args, **kwargs)
    return True
  return False
