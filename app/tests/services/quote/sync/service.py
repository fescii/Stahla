# app/tests/services/quote/sync/service.py
"""Tests for sheet sync service."""

from unittest.mock import Mock, AsyncMock, patch
import asyncio

from app.services.quote.sync.service import SheetSyncService


class TestSheetSyncService:
  """Test cases for SheetSyncService."""

  def setup_method(self):
    """Set up test fixtures."""
    self.service = SheetSyncService()

  async def test_initialize(self):
    """Test service initialization."""
    # Arrange
    with patch('app.services.quote.sync.service.get_redis_service') as mock_redis, \
            patch('app.services.quote.sync.service.get_mongo_service') as mock_mongo:

      mock_redis_instance = AsyncMock()
      mock_mongo_instance = AsyncMock()
      mock_redis.return_value = mock_redis_instance
      mock_mongo.return_value = mock_mongo_instance

      # Mock sheets service initialization
      self.service.sheets_service.initialize_service = AsyncMock()

      # Act
      await self.service.initialize()

      # Assert
      assert self.service.redis_service == mock_redis_instance
      assert self.service.mongo_service == mock_mongo_instance
      assert self.service.redis_storage is not None
      assert self.service.mongo_storage is not None
      self.service.sheets_service.initialize_service.assert_called_once()

  async def test_start_background_sync(self):
    """Test starting background sync."""
    # Arrange
    self.service._run_sync_loop = AsyncMock()

    # Act
    await self.service.start_background_sync()

    # Assert
    assert self.service._sync_task is not None
    assert not self.service._stop_sync.is_set()

  async def test_stop_background_sync(self):
    """Test stopping background sync."""
    # Arrange - start sync first
    self.service._sync_task = AsyncMock()
    self.service._sync_task.done.return_value = False

    # Act
    await self.service.stop_background_sync()

    # Assert
    assert self.service._stop_sync.is_set()
    self.service._sync_task.cancel.assert_called_once()

  async def test_sync_full_catalog(self):
    """Test full catalog synchronization."""
    # Arrange
    self.service.redis_storage = AsyncMock()
    self.service.mongo_storage = AsyncMock()
    self.service.sheets_service = AsyncMock()

    # Mock sheet data
    mock_branches_data = [["Branch1", "Address1"], ["Branch2", "Address2"]]
    mock_states_data = [["CA"], ["TX"]]
    mock_products_data = [["Product1", "100"], ["Product2", "200"]]

    self.service.sheets_service.get_sheet_data.side_effect = [
        mock_branches_data,
        mock_states_data,
        mock_products_data,
        []  # generators
    ]

    # Act
    result = await self.service.sync_full_catalog()

    # Assert
    assert "success" in result
    assert self.service.sheets_service.get_sheet_data.call_count == 4

  async def test_get_branches_list(self):
    """Test getting branches list."""
    # Arrange
    self.service.redis_storage = AsyncMock()
    expected_branches = [
        {"name": "Branch1", "address": "Address1"},
        {"name": "Branch2", "address": "Address2"}
    ]
    self.service.redis_storage.get_branches_list.return_value = expected_branches

    # Act
    result = await self.service.get_branches_list()

    # Assert
    assert result == expected_branches
    self.service.redis_storage.get_branches_list.assert_called_once()

  async def test_get_states_list(self):
    """Test getting states list."""
    # Arrange
    self.service.redis_storage = AsyncMock()
    expected_states = ["CA", "TX", "NY"]
    self.service.redis_storage.get_states_list.return_value = expected_states

    # Act
    result = await self.service.get_states_list()

    # Assert
    assert result == expected_states
    self.service.redis_storage.get_states_list.assert_called_once()

  async def test_get_pricing_catalog(self):
    """Test getting pricing catalog."""
    # Arrange
    self.service.redis_storage = AsyncMock()
    expected_catalog = {
        "products": {"standard_20": {"daily_rate": "50.00"}},
        "generators": {"gen_5000": {"daily_rate": "15.00"}}
    }
    self.service.redis_storage.get_pricing_catalog.return_value = expected_catalog

    # Act
    result = await self.service.get_pricing_catalog()

    # Assert
    assert result == expected_catalog
    self.service.redis_storage.get_pricing_catalog.assert_called_once()

  async def test_refresh_catalog(self):
    """Test catalog refresh."""
    # Arrange
    self.service.sync_full_catalog = AsyncMock(return_value={"success": True})

    # Act
    result = await self.service.refresh_catalog()

    # Assert
    assert result["success"] is True
    self.service.sync_full_catalog.assert_called_once()

  async def test_initialization_error_handling(self):
    """Test error handling during initialization."""
    # Arrange
    with patch('app.services.quote.sync.service.get_redis_service') as mock_redis:
      mock_redis.side_effect = Exception("Redis connection failed")

      # Act & Assert
      try:
        await self.service.initialize()
        assert False, "Expected exception"
      except Exception as e:
        assert "Redis connection failed" in str(e)

  async def test_sync_with_empty_sheets(self):
    """Test synchronization with empty sheet data."""
    # Arrange
    self.service.redis_storage = AsyncMock()
    self.service.mongo_storage = AsyncMock()
    self.service.sheets_service = AsyncMock()

    # Mock empty sheet data
    self.service.sheets_service.get_sheet_data.return_value = []

    # Act
    result = await self.service.sync_full_catalog()

    # Assert
    assert "success" in result
