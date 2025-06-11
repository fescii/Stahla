# app/services/quote/sync/parsers/branches.py

"""
Branch data parser for Google Sheets sync.
"""

import logging
from typing import Any, Dict, List

import logfire
from app.models.location import BranchLocation
from app.core.config import settings

logger = logging.getLogger(__name__)


class BranchParser:
  """Handles parsing of branch data from Google Sheets."""

  def parse_branches(self, branches_data: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    Parse branch data from sheet format to structured format.

    Args:
        branches_data: Raw data from Google Sheets

    Returns:
        List of parsed branch dictionaries
    """
    branches = []
    if not branches_data or len(branches_data) < 2:
      logfire.warning(
          f"No data or insufficient rows (expected header + data) provided to parse_branches for range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'. Branch list will be empty."
      )
      return branches

    data_rows = branches_data[1:]  # Skip header row

    for i, row in enumerate(data_rows):
      if len(row) >= 2 and row[0] and row[1]:
        try:
          branch_name = str(row[0]).strip()
          branch_address = str(row[1]).strip()
          branch = BranchLocation(name=branch_name, address=branch_address)
          branches.append(branch.model_dump())
        except Exception as e:
          logfire.warning(
              f"Skipping branch row {i+2} (original sheet row) due to parsing/validation error: {row}. Error: {e}"
          )
      else:
        logfire.warning(
            f"Skipping incomplete branch row {i+2} (original sheet row): {row}. Expected at least 2 columns."
        )

    logfire.info(
        f"BranchParser: Parsed {len(branches)} branches from sheet range '{settings.GOOGLE_SHEET_BRANCHES_RANGE}'."
    )
    return branches
