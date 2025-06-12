# filepath: app/services/mongo/reports/operations.py
import logfire
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone
from app.services.mongo.collections.names import REPORTS_COLLECTION


class ReportsOperations:
  """Handles MongoDB operations for reports."""

  def __init__(self, db):
    self.db = db

  async def log_report(
      self,
      report_type: str,
      data: Dict[str, Any],
      success: bool,
      error_message: Optional[str] = None,
  ):
    """Logs a report document to the reports collection."""
    collection = self.db[REPORTS_COLLECTION]
    report_doc = {
        "timestamp": datetime.now(timezone.utc),
        "report_type": report_type,
        "success": success,
        "data": data,
        "error_message": error_message,
    }
    try:
      result = await collection.insert_one(report_doc)
      logfire.debug(
          f"Logged report '{report_type}' to MongoDB with id: {result.inserted_id}"
      )
      return result.inserted_id
    except Exception as e:
      logfire.error(
          f"Failed to log report '{report_type}' to MongoDB: {e}", exc_info=True
      )
      return None

  async def get_recent_reports(
      self, report_type: Optional[Union[str, List[str]]] = None, limit: int = 100
  ) -> List[Dict[str, Any]]:
    """Retrieves recent reports, optionally filtered by a single type or a list of types."""
    collection = self.db[REPORTS_COLLECTION]
    query = {}
    if report_type:
      if isinstance(report_type, str):
        query["report_type"] = report_type
      elif isinstance(report_type, list):
        query["report_type"] = {"$in": report_type}

    try:
      cursor = collection.find(query).sort("timestamp", -1).limit(limit)
      reports = await cursor.to_list(length=limit)
      # Convert ObjectId to string for JSON serialization if needed later
      for report in reports:
        report["_id"] = str(report["_id"])
      return reports
    except Exception as e:
      logfire.error(
          f"Failed to retrieve reports from MongoDB: {e}", exc_info=True
      )
      return []

  async def get_report_summary(self) -> Dict[str, Any]:
    """Provides a summary of report counts by type and success/failure."""
    collection = self.db[REPORTS_COLLECTION]
    summary = {
        "total_reports": 0,
        "success_count": 0,
        "failure_count": 0,
        "by_type": {},
    }
    try:
      pipeline = [
          {
              "$group": {
                  "_id": {"type": "$report_type", "success": "$success"},
                  "count": {"$sum": 1},
              }
          },
          {
              "$group": {
                  "_id": "$_id.type",
                  "counts": {
                      "$push": {
                          "k": {"$cond": ["$_id.success", "success", "failure"]},
                          "v": "$count",
                      }
                  },
                  "total": {"$sum": "$count"},
              }
          },
          {
              "$project": {
                  "_id": 0,
                  "type": "$_id",
                  "total": "$total",
                  "status_counts": {"$arrayToObject": "$counts"},
              }
          },
      ]
      results = await collection.aggregate(pipeline).to_list(length=None)

      total_reports = 0
      total_success = 0
      total_failure = 0
      by_type_summary = {}

      for item in results:
        report_type = item.get("type")
        type_total = item.get("total", 0)
        type_success = item.get("status_counts", {}).get("success", 0)
        type_failure = item.get("status_counts", {}).get("failure", 0)

        total_reports += type_total
        total_success += type_success
        total_failure += type_failure

        by_type_summary[report_type] = {
            "total": type_total,
            "success": type_success,
            "failure": type_failure,
        }

      summary["total_reports"] = total_reports
      summary["success_count"] = total_success
      summary["failure_count"] = total_failure
      summary["by_type"] = by_type_summary

      return summary

    except Exception as e:
      logfire.error(
          f"Failed to aggregate report summary from MongoDB: {e}", exc_info=True
      )
      return summary
