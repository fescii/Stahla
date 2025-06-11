# app/tests/services/quote/background/tasks/processor.py
"""Tests for background task processor."""

from unittest.mock import Mock, patch
from fastapi import BackgroundTasks


class TestTaskProcessor:
  """Test cases for TaskProcessor."""

  def setup_method(self):
    """Set up test fixtures."""
    self.mock_background_tasks = Mock(spec=BackgroundTasks)

  def test_background_tasks_integration(self):
    """Test BackgroundTasks integration."""
    # Arrange
    background_tasks = BackgroundTasks()
    executed = []

    def test_task(value):
      executed.append(value)

    # Act
    background_tasks.add_task(test_task, "test_value")

    # Assert - task should be queued
    assert len(background_tasks.tasks) == 1
    task_info = background_tasks.tasks[0]
    assert task_info.func == test_task
    assert task_info.args == ("test_value",)

  def test_add_task_with_args(self):
    """Test adding task with arguments."""
    # Arrange
    background_tasks = BackgroundTasks()

    def dummy_func(arg1, arg2="default"):
      return f"{arg1}-{arg2}"

    # Act
    background_tasks.add_task(dummy_func, "test", arg2="custom")

    # Assert
    assert len(background_tasks.tasks) == 1
    task_info = background_tasks.tasks[0]
    assert task_info.func == dummy_func
    assert task_info.args == ("test",)
    assert task_info.kwargs == {"arg2": "custom"}

  def test_add_multiple_tasks(self):
    """Test adding multiple tasks."""
    # Arrange
    background_tasks = BackgroundTasks()

    def task1():
      pass

    def task2(arg):
      pass

    # Act
    background_tasks.add_task(task1)
    background_tasks.add_task(task2, "arg_value")

    # Assert
    assert len(background_tasks.tasks) == 2
    assert background_tasks.tasks[0].func == task1
    assert background_tasks.tasks[1].func == task2
    assert background_tasks.tasks[1].args == ("arg_value",)

  async def test_async_task_handling(self):
    """Test handling asynchronous tasks."""
    # Arrange
    background_tasks = BackgroundTasks()

    async def async_task(value):
      return f"processed_{value}"

    # Act
    background_tasks.add_task(async_task, "test")

    # Assert
    assert len(background_tasks.tasks) == 1
    task_info = background_tasks.tasks[0]
    assert task_info.func == async_task
    assert task_info.args == ("test",)
