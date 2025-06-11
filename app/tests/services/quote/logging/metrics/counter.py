# app/tests/services/quote/logging/metrics/counter.py
"""Tests for metrics counter."""

from unittest.mock import Mock, AsyncMock

from app.services.quote.logging.metrics.counter import MetricsCounter


class TestMetricsCounter:
  """Test cases for MetricsCounter."""

  def setup_method(self):
    """Set up test fixtures."""
    self.mock_redis = AsyncMock()
    self.counter = MetricsCounter(self.mock_redis)

  async def test_increment_cache_hit(self):
    """Test incrementing cache hit counter."""
    # Act
    await self.counter.increment_cache_hit("pricing")

    # Assert Redis increment was called
    self.mock_redis.incr.assert_called_once()

  async def test_increment_cache_miss(self):
    """Test incrementing cache miss counter."""
    # Act
    await self.counter.increment_cache_miss("location")

    # Assert Redis increment was called
    self.mock_redis.incr.assert_called_once()

  async def test_increment_quote_request(self):
    """Test incrementing quote request counter."""
    # Act
    await self.counter.increment_quote_request("commercial")

    # Assert Redis increment was called
    self.mock_redis.incr.assert_called_once()

  async def test_increment_sync_operation(self):
    """Test incrementing sync operation counter."""
    # Act
    await self.counter.increment_sync_operation("sheets")

    # Assert Redis increment was called
    self.mock_redis.incr.assert_called_once()

  async def test_increment_quote_success(self):
    """Test incrementing quote success counter."""
    # Act
    await self.counter.increment_quote_success("commercial")

    # Assert Redis increment was called
    self.mock_redis.increment.assert_called_once()

  async def test_increment_quote_error(self):
    """Test incrementing quote error counter."""
    # Act
    await self.counter.increment_quote_error("validation_failed")

    # Assert Redis increment was called
    self.mock_redis.increment.assert_called_once()

  async def test_record_processing_time(self):
    """Test recording processing time."""
    # Arrange
    mock_client = AsyncMock()
    self.mock_redis.get_client.return_value = mock_client

    # Act
    await self.counter.record_processing_time("quote_calculation", 150.5)

    # Assert
    mock_client.lpush.assert_called_once()
    mock_client.ltrim.assert_called_once()

  async def test_get_metrics_summary(self):
    """Test getting metrics summary."""
    # Arrange
    self.mock_redis.scan_keys.return_value = [
        "metrics:cache_hits:pricing",
        "metrics:quote_requests:standard"
    ]
    self.mock_redis.get.side_effect = lambda key: {
        "metrics:cache_hits:pricing": "100",
        "metrics:quote_requests:standard": "500"
    }.get(key, "0")

    # Act
    summary = await self.counter.get_metrics_summary()

    # Assert
    assert summary["metrics:cache_hits:pricing"] == 100
    assert summary["metrics:quote_requests:standard"] == 500

  async def test_error_handling_in_increment(self):
    """Test error handling during increment operations."""
    # Arrange
    self.mock_redis.increment.side_effect = Exception(
        "Redis connection failed")

    # Act & Assert - should not raise exception
    await self.counter.increment_cache_hit("pricing")

    # Verify attempt was made
    self.mock_redis.increment.assert_called_once()
