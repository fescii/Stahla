# app/services/quote/sync/sheets/service.py

"""
Google Sheets service for data fetching.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import asyncio

import logfire
from googleapiclient.errors import HttpError

from app.services.quote.auth.google.credentials import create_sheets_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class SheetsService:
  """Handles Google Sheets API interactions."""

  def __init__(self):
    self.service = None
    self.google_app_creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS

  async def initialize_service(self):
    """Initialize the Google Sheets service."""
    try:
      if not self.google_app_creds_path:
        raise ValueError("Google application credentials path not configured")
      self.service = create_sheets_service(self.google_app_creds_path)
      logfire.info("SheetsService initialized successfully")
    except Exception as e:
      logfire.error(f"Failed to initialize SheetsService: {e}")
      raise

  async def fetch_sheet_data(
      self,
      spreadsheet_id: str,
      range_name: str
  ) -> Optional[List[List[Any]]]:
    """
    Fetch data from a Google Sheet range.

    Args:
        spreadsheet_id: The Google Sheet ID
        range_name: The range to fetch (e.g., 'Sheet1!A1:Z100')

    Returns:
        List of rows, or None if error
    """
    if self.service is None:
      await self.initialize_service()

    if self.service is None:
      logfire.error("Sheets service not initialized")
      return None

    try:
      logfire.info(
          f"Fetching sheet data: {spreadsheet_id}, range: {range_name}")

      # Run the synchronous API call in a thread pool
      # Type checker knows service is not None after the check above
      service = self.service  # Local variable for type safety
      result = await asyncio.get_event_loop().run_in_executor(
          None,
          lambda: service.spreadsheets().values().get(
              spreadsheetId=spreadsheet_id,
              range=range_name
          ).execute()
      )

      values = result.get("values", [])
      logfire.info(f"Successfully fetched {len(values)} rows from sheet")
      return values

    except HttpError as error:
      error_details = error.error_details if hasattr(
          error, 'error_details') else []
      logfire.error(
          f"HTTP error fetching sheet data: {error}",
          spreadsheet_id=spreadsheet_id,
          range_name=range_name,
          error_details=error_details
      )
      return None

    except Exception as e:
      logfire.error(
          f"Unexpected error fetching sheet data: {e}",
          spreadsheet_id=spreadsheet_id,
          range_name=range_name
      )
      return None

  async def fetch_multiple_ranges(
      self,
      spreadsheet_id: str,
      ranges: List[str]
  ) -> Dict[str, Optional[List[List[Any]]]]:
    """
    Fetch data from multiple ranges in parallel.

    Args:
        spreadsheet_id: The Google Sheet ID
        ranges: List of range names to fetch

    Returns:
        Dictionary mapping range names to their data
    """
    tasks = []
    for range_name in ranges:
      task = self.fetch_sheet_data(spreadsheet_id, range_name)
      tasks.append((range_name, task))

    results = {}
    for range_name, task in tasks:
      results[range_name] = await task

    return results
