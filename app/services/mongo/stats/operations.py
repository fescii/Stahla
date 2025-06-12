# filepath: app/services/mongo/stats/operations.py
import logfire
from typing import Dict
from app.services.mongo.collections.names import STATS_COLLECTION


class StatsOperations:
  """Handles MongoDB operations for dashboard statistics."""

  def __init__(self, db):
    self.db = db

  async def increment_request_stat(self, stat_name: str, success: bool):
    """Increments a counter for a given statistic (e.g., quote_requests) in MongoDB."""
    logfire.info(
        f"increment_request_stat: Attempting for '{stat_name}', success: {success}. DB state: {'DB available' if self.db is not None else 'DB NOT AVAILABLE'}"
    )

    if self.db is None:
      logfire.error(
          f"increment_request_stat: MongoDB database is not initialized. Cannot increment stat for {stat_name}."
      )
      return

    # Log database and collection names
    db_name = self.db.name
    collection_name_actual = STATS_COLLECTION
    logfire.info(
        f"increment_request_stat: Operating on DB: '{db_name}', Collection: '{collection_name_actual}'"
    )

    collection = self.db[collection_name_actual]
    query = {"_id": stat_name}
    update = {
        "$inc": {
            "total": 1,
            "successful": 1 if success else 0,
            "failed": 1 if not success else 0,
        }
    }
    try:
      result = await collection.update_one(query, update, upsert=True)
      logfire.info(
          f"increment_request_stat: Upsert for '{stat_name}' (success: {success}). Matched: {result.matched_count}, Modified: {result.modified_count}, UpsertedId: {result.upserted_id}"
      )

      # DEBUG: Attempt to read the document immediately after upsert
      doc_after_upsert = await collection.find_one({"_id": stat_name})
      if doc_after_upsert:
        logfire.info(
            f"increment_request_stat: DEBUG READ AFTER UPSERT for '{stat_name}' FOUND: {doc_after_upsert}"
        )
      else:
        logfire.warning(
            f"increment_request_stat: DEBUG READ AFTER UPSERT for '{stat_name}' NOT FOUND."
        )

    except Exception as e:
      logfire.error(
          f"increment_request_stat: Failed for '{stat_name}' in MongoDB: {e}",
          exc_info=True,
          stat_name=stat_name,
          success=success,
      )

  async def get_dashboard_stats(self) -> Dict[str, Dict[str, int]]:
    """Retrieves dashboard statistics like quote requests and location lookups from MongoDB."""
    logfire.info(
        f"get_dashboard_stats: Attempting. DB state: {'DB available' if self.db is not None else 'DB NOT AVAILABLE'}"
    )
    if self.db is None:
      logfire.error(
          "get_dashboard_stats: MongoDB database is not initialized. Cannot fetch stats."
      )
      return {}

    # Log database and collection names
    db_name = self.db.name
    collection_name_actual = STATS_COLLECTION
    logfire.info(
        f"get_dashboard_stats: Operating on DB: '{db_name}', Collection: '{collection_name_actual}'"
    )

    collection = self.db[collection_name_actual]
    stats_to_fetch = ["quote_requests", "location_lookups"]
    dashboard_data: Dict[str, Dict[str, int]] = {}

    try:
      for stat_name in stats_to_fetch:
        doc = await collection.find_one({"_id": stat_name})
        if doc:
          dashboard_data[stat_name] = {
              "total": doc.get("total", 0),
              "successful": doc.get("successful", 0),
              "failed": doc.get("failed", 0),
          }
          # Log found stats
          logfire.info(
              f"Found stat '{stat_name}': Total={doc.get('total', 0)}, Success={doc.get('successful', 0)}, Failed={doc.get('failed', 0)}"
          )
        else:
          logfire.warning(
              f"No document found for stat_name: '{stat_name}' in {STATS_COLLECTION}. Returning zeros."
          )
          dashboard_data[stat_name] = {
              "total": 0, "successful": 0, "failed": 0}

      logfire.info(f"Successfully retrieved dashboard stats: {dashboard_data}")
      return dashboard_data
    except Exception as e:
      logfire.error(
          f"Failed to retrieve dashboard stats from MongoDB: {e}", exc_info=True
      )
      # Return default structure on error
      for stat_name in stats_to_fetch:
        if stat_name not in dashboard_data:
          dashboard_data[stat_name] = {
              "total": 0, "successful": 0, "failed": 0}
      return dashboard_data
