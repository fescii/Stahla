# filepath: app/services/dash/errors/manager.py
import logging
from typing import List, Optional
from app.services.mongo import MongoService
from app.models.dash.dashboard import ErrorLogEntry

logger = logging.getLogger(__name__)


class ErrorManager:
  """Handles error log operations for dashboard."""

  def __init__(self, mongo_service: MongoService):
    self.mongo = mongo_service

  async def get_error_logs(
      self, report_type: Optional[str] = None, limit: int = 50
  ) -> List[ErrorLogEntry]:
    """Retrieves recent error logs from MongoDB, optionally filtered by type."""
    logger.info(
        f"Fetching error logs from MongoDB. Type: {report_type}, Limit: {limit}"
    )
    try:
      raw_reports = await self.mongo.get_recent_reports(
          report_type=report_type, limit=limit
      )

      # Log the raw data received from MongoDB before filtering
      logger.debug(
          f"Raw reports received from MongoDB for get_error_logs: {raw_reports}"
      )

      # Filter for errors (success=False) and parse into ErrorLogEntry model
      error_logs = []
      for report in raw_reports:
        # Check if 'success' field exists and is explicitly False
        if "success" in report and report["success"] is False:
          try:
            # Transform MongoDB report to ErrorLogEntry format
            error_entry_data = {
                "timestamp": report.get("timestamp"),
                "error_type": report.get("report_type", "Unknown"),
                "message": report.get("error_message", "No message provided"),
                "details": {
                    "_id": str(report.get("_id")),
                    "data": report.get("data", {}),
                    "success": report.get("success")
                }
            }
            error_logs.append(ErrorLogEntry(**error_entry_data))
          except Exception as parse_error:
            logger.warning(
                f"Failed to parse MongoDB report into ErrorLogEntry: {report}. Error: {parse_error}"
            )

      logger.info(f"Retrieved {len(error_logs)} error logs after filtering.")
      return error_logs
    except Exception as e:
      logger.error(
          f"Failed to retrieve error logs from MongoDB: {e}", exc_info=True
      )
      return []
