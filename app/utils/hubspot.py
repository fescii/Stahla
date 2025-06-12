from datetime import datetime, timezone
from typing import Optional


def to_hubspot_midnight_unix(date_str: Optional[str]) -> Optional[int]:
  """
  Convert a date string to a HubSpot-compatible Unix timestamp.
  This function assumes the date string is in 'YYYY-MM-DD' format.
  """
  if not date_str:
    return None
  try:
    # Parse the date string and convert to midnight Unix timestamp
    # Try multiple common date formats
    dt = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
      try:
        dt = datetime.strptime(date_str, fmt)
        break
      except ValueError:
        continue
    if not dt:
      return None
    return int(dt.replace(hour=0, minute=0, second=0).timestamp())
  except ValueError:
    return None
