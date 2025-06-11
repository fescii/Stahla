# app/services/quote/sync/parsers/states.py

"""
States data parser for Google Sheets sync.
"""

import logging
from typing import Any, Dict, List

import logfire

logger = logging.getLogger(__name__)


class StatesParser:
  """Handles parsing of states data from Google Sheets."""

  def parse_states(self, states_data: List[List[Any]]) -> List[Dict[str, Any]]:
    """
    Parse states data from sheet format to structured format.

    Args:
        states_data: Raw data from Google Sheets

    Returns:
        List of parsed state dictionaries
    """
    states = []
    if not states_data or len(states_data) < 2:
      logfire.warning(
          "No valid states data found in sheet. Expected at least 2 rows (header + data)."
      )
      return states

    # Skip header row (first row)
    data_rows = states_data[1:]

    for i, row in enumerate(data_rows):
      if len(row) >= 2 and row[0] and row[1]:  # State and Code columns required
        try:
          state_name = str(row[0]).strip()
          state_code = str(row[1]).strip()

          if state_name and state_code:
            states.append({
                "state": state_name,
                "code": state_code,
            })
          else:
            logfire.warning(
                f"Skipping state row {i+2} (original sheet row) due to empty state name or code: {row}"
            )
        except Exception as e:
          logfire.error(
              f"Skipping state row {i+2} (original sheet row) due to parsing/validation error: {row}. Error: {e}"
          )
      else:
        logfire.warning(
            f"Skipping state row {i+2} (original sheet row) due to insufficient columns or empty data: {row}"
        )

    logfire.info(f"Successfully parsed {len(states)} states from sheet data")
    return states
