# app/tests/services/quote/logging/error/reporter.py
"""Tests for error reporter."""

import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.quote.logging.error.reporter import ErrorReporter


class TestErrorReporter:
  """Test cases for ErrorReporter."""

  def setup_method(self):
    """Set up test fixtures."""
    self.mock_mongo = AsyncMock()
    self.mock_redis = AsyncMock()
    self.reporter = ErrorReporter(self.mock_mongo, self.mock_redis)

  async def test_report_error_immediate(self):
    """Test immediate error reporting."""
    # Act
    await self.reporter.report_error(
        service_name="QuoteService",
        error_type="ValueError",
        message="Test error",
        details={"operation": "calculate"},
        immediate=True
    )

    # Assert - should not queue for immediate errors
    assert self.reporter._error_queue.qsize() == 0

  async def test_report_error_queued(self):
    """Test queued error reporting."""
    # Act
    await self.reporter.report_error(
        service_name="QuoteService",
        error_type="ConnectionError",
        message="Database connection failed",
        details={"host": "localhost"},
        immediate=False
    )

    # Assert - should be queued
    assert self.reporter._error_queue.qsize() == 1

  async def test_report_quote_error(self):
    """Test quote-specific error reporting."""
    # Arrange
    error = ValueError("Invalid quote data")
    context = "quote_calculation"
    request_data = {"zip_code": "12345", "duration": 30}

    # Act
    await self.reporter.report_quote_error(
        context=context,
        error=error,
        request_data=request_data,
        immediate=True
    )

    # Assert - should not queue for immediate errors
    assert self.reporter._error_queue.qsize() == 0

  async def test_background_processing_lifecycle(self):
    """Test starting and stopping background processing."""
    # Act - start processing
    await self.reporter.start_background_processing()
    assert self.reporter._processing_task is not None
    assert not self.reporter._processing_task.done()

    # Act - stop processing
    await self.reporter.stop_background_processing()
    assert self.reporter._processing_task is None

  def test_determine_severity(self):
    """Test error severity determination."""
    # Test critical errors
    assert self.reporter._determine_severity("DatabaseError") == "critical"
    assert self.reporter._determine_severity("ConnectionError") == "critical"

    # Test high errors
    assert self.reporter._determine_severity("ValidationError") == "high"
    assert self.reporter._determine_severity("AuthenticationError") == "high"

    # Test medium errors
    assert self.reporter._determine_severity("ValueError") == "medium"
    assert self.reporter._determine_severity("KeyError") == "medium"

    # Test low errors
    assert self.reporter._determine_severity("Warning") == "low"
    assert self.reporter._determine_severity("Info") == "low"

    # Test unknown error types
    assert self.reporter._determine_severity("UnknownError") == "medium"

  async def test_batch_processing(self):
    """Test batch error processing."""
    # Arrange - add multiple errors to queue
    for i in range(3):
      await self.reporter.report_error(
          service_name="TestService",
          error_type="TestError",
          message=f"Error {i}",
          immediate=False
      )

    # Assert queue has items
    assert self.reporter._error_queue.qsize() == 3
