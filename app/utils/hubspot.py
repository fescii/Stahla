from datetime import datetime, timezone
from typing import Optional


def to_hubspot_date_string_from_input(date_str: Optional[str]) -> Optional[str]:
  """
  Convert a date string to HubSpot-compatible YYYY-MM-DD format.

  HubSpot date properties expect date strings in YYYY-MM-DD format, not timestamps.

  Args:
      date_str: Date string in various formats (YYYY-MM-DD, MM/DD/YYYY, etc.)

  Returns:
      Date string in YYYY-MM-DD format, or None if invalid

  Example:
      to_hubspot_date_string_from_input("05/25/2025") -> "2025-05-25"
      to_hubspot_date_string_from_input("2025-05-25") -> "2025-05-25"
  """
  if not date_str:
    return None
  try:
    # Parse the date string
    dt = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
      try:
        dt = datetime.strptime(date_str, fmt)
        break
      except ValueError:
        continue
    if not dt:
      return None

    # Return in YYYY-MM-DD format
    return dt.strftime("%Y-%m-%d")
  except (ValueError, OSError):
    return None


def to_hubspot_midnight_unix(date_str: Optional[str]) -> Optional[str]:
  """
  Convert a date string to a HubSpot-compatible Unix timestamp in milliseconds as string.
  This function converts the date to midnight UTC and returns milliseconds since epoch.

  HubSpot requires UNIX timestamps in milliseconds for date properties.
  Date properties should be set to midnight UTC for the desired date.

  Args:
      date_str: Date string in various formats (YYYY-MM-DD, MM/DD/YYYY, etc.)

  Returns:
      String representation of UNIX timestamp in milliseconds, or None if invalid

  Example:
      to_hubspot_midnight_unix("2025-05-01") -> "1430438400000" (May 1, 2015 00:00:00 UTC)
  """
  if not date_str:
    return None
  try:
    # Parse the date string and convert to midnight UTC timestamp
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

    # Set to midnight UTC and convert to milliseconds
    midnight_utc = dt.replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    timestamp_ms = int(midnight_utc.timestamp() * 1000)
    return str(timestamp_ms)
  except (ValueError, OSError):
    return None


def to_hubspot_datetime_unix(datetime_str: Optional[str]) -> Optional[str]:
  """
  Convert a datetime string to a HubSpot-compatible Unix timestamp in milliseconds.

  HubSpot datetime properties can store both date and time values and should be
  formatted as UNIX timestamp in milliseconds.

  Args:
      datetime_str: Datetime string in ISO 8601 format (YYYY-MM-DDThh:mm:ss) or similar

  Returns:
      String representation of UNIX timestamp in milliseconds, or None if invalid

  Example:
      to_hubspot_datetime_unix("2025-07-10T10:30:00") -> timestamp in milliseconds
  """
  if not datetime_str:
    return None
  try:
    # Try multiple datetime formats
    dt = None
    formats = [
        "%Y-%m-%dT%H:%M:%S",      # ISO 8601 basic
        "%Y-%m-%dT%H:%M:%S.%f",   # ISO 8601 with microseconds
        "%Y-%m-%dT%H:%M:%SZ",     # ISO 8601 with Z suffix
        "%Y-%m-%d %H:%M:%S",      # Space separated
        "%m/%d/%Y %H:%M:%S",      # US format with time
        "%d-%m-%Y %H:%M:%S",      # EU format with time
    ]

    for fmt in formats:
      try:
        dt = datetime.strptime(datetime_str, fmt)
        break
      except ValueError:
        continue

    if not dt:
      return None

    # Ensure UTC timezone
    if dt.tzinfo is None:
      dt = dt.replace(tzinfo=timezone.utc)

    # Convert to milliseconds
    timestamp_ms = int(dt.timestamp() * 1000)
    return str(timestamp_ms)
  except (ValueError, OSError):
    return None


def from_hubspot_unix_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
  """
  Convert a HubSpot Unix timestamp in milliseconds back to a datetime object.

  Args:
      timestamp_str: String representation of UNIX timestamp in milliseconds

  Returns:
      datetime object in UTC, or None if invalid

  Example:
      from_hubspot_unix_timestamp("1430438400000") -> datetime(2015, 5, 1, 0, 0, tzinfo=timezone.utc)
  """
  if not timestamp_str:
    return None
  try:
    timestamp_ms = int(timestamp_str)
    timestamp_seconds = timestamp_ms / 1000
    return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
  except (ValueError, OSError):
    return None


def to_hubspot_date_string(date_obj: Optional[datetime]) -> Optional[str]:
  """
  Convert a datetime object to HubSpot-compatible date string (YYYY-MM-DD format).

  Args:
      date_obj: datetime object

  Returns:
      Date string in YYYY-MM-DD format, or None if invalid

  Example:
      to_hubspot_date_string(datetime(2025, 7, 10)) -> "2025-07-10"
  """
  if not date_obj:
    return None
  try:
    return date_obj.strftime("%Y-%m-%d")
  except (ValueError, AttributeError):
    return None


def to_hubspot_datetime_string(datetime_obj: Optional[datetime]) -> Optional[str]:
  """
  Convert a datetime object to HubSpot-compatible ISO 8601 datetime string.

  Args:
      datetime_obj: datetime object

  Returns:
      ISO 8601 datetime string, or None if invalid

  Example:
      to_hubspot_datetime_string(datetime(2025, 7, 10, 10, 30, 0, tzinfo=timezone.utc)) 
      -> "2025-07-10T10:30:00Z"
  """
  if not datetime_obj:
    return None
  try:
    # Ensure UTC timezone
    if datetime_obj.tzinfo is None:
      datetime_obj = datetime_obj.replace(tzinfo=timezone.utc)
    return datetime_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
  except (ValueError, AttributeError):
    return None
