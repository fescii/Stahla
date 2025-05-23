# filepath: app/services/mongo/mongo.py
import logfire
import logging
import copy
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation
from app.core.config import settings
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timezone
import uuid
from pymongo import ASCENDING, DESCENDING
from pymongo import UpdateOne
from app.models.blandlog import BlandCallStatus
from app.models.error import ErrorLog
from fastapi import HTTPException  # Added import

# --- Constants for Collection Names ---
REPORTS_COLLECTION = "reports"
USERS_COLLECTION = "users"  # Define users collection name here
SHEET_PRODUCTS_COLLECTION = "sheet_products"
SHEET_GENERATORS_COLLECTION = "sheet_generators"
SHEET_BRANCHES_COLLECTION = "sheet_branches"
SHEET_CONFIG_COLLECTION = "sheet_config"
BLAND_CALL_LOGS_COLLECTION = "bland_call_logs"
ERROR_LOGS_COLLECTION = "error_logs"  # New collection for general errors
STATS_COLLECTION = "dashboard_stats"  # Collection for dashboard counters

mongo_service_instance: Optional["MongoService"] = None


async def startup_mongo_service():
  global mongo_service_instance
  logfire.info("Attempting to start up MongoDB service...")
  if mongo_service_instance is None:
    mongo_service_instance = MongoService()
    try:
      await mongo_service_instance.connect_and_initialize()
      logfire.info("MongoDB service started and initialized successfully.")
    except Exception as e:
      logfire.error(f"MongoDB service startup failed: {e}", exc_info=True)
      mongo_service_instance = None  # Set back to None on failure
  else:
    logfire.info("MongoDB service already started.")


async def shutdown_mongo_service():
  global mongo_service_instance
  if mongo_service_instance:
    logfire.info("Attempting to shut down MongoDB service...")
    await mongo_service_instance.close_mongo_connection()
    mongo_service_instance = None


async def get_mongo_service() -> "MongoService":  # Changed to async
  """
  FastAPI dependency injector for MongoService.
  Returns the initialized mongo_service_instance.
  Raises HTTPException if the service is not available.
  """
  global mongo_service_instance  # Ensure we are using the global instance
  if mongo_service_instance is None:
    logfire.error(
        "get_mongo_service: mongo_service_instance is None. MongoDB might not have started correctly."
    )
    # Attempt to initialize it if it's None, as a fallback, though startup should handle this.
    # This might be problematic if called before lifespan startup is complete.
    # Consider if this fallback is desired or if it should strictly rely on startup.
    logfire.info(
        "get_mongo_service: Attempting to initialize mongo_service_instance as it was None.")
    await startup_mongo_service()  # Try to start it if not already started
    if mongo_service_instance is None:  # Check again after attempting startup
      raise HTTPException(
          status_code=503,
          detail="MongoDB service is not available. Initialization may have failed.",
      )
  return mongo_service_instance


class MongoService:
  # client and db are now instance attributes, initialized in __init__
  client: Optional[AsyncIOMotorClient]
  db: Optional[AsyncIOMotorDatabase]

  def __init__(self):
    # Initialize attributes to None before async connection
    self.client = None
    self.db = None
    logfire.info(
        "MongoService instance created. Connection will be established.")

  async def connect_and_initialize(self):
    """Connects to MongoDB and performs initial setup like index creation."""
    logfire.info("Connecting to MongoDB...")
    if not settings.MONGO_CONNECTION_URL:
      logfire.error("MONGO_CONNECTION_URL not set in environment/settings.")
      raise ValueError("MongoDB connection URL is not configured.")

    try:
      # Configure UUID representation
      codec_options = CodecOptions(
          uuid_representation=UuidRepresentation.STANDARD
      )

      self.client = AsyncIOMotorClient(
          settings.MONGO_CONNECTION_URL,
          serverSelectionTimeoutMS=3000,  # Reduced from 5000ms
          connectTimeoutMS=2000,  # Added: 2 seconds
          socketTimeoutMS=2000,  # Added: 2 seconds for operations
          uuidRepresentation="standard",  # Explicitly set standard UUID representation
          # server_api=ServerApi('1') # Optional: Specify Stable API version
      )
      # The ismaster command is cheap and does not require auth.
      await self.client.admin.command("ismaster")
      # Get database with codec options
      self.db = self.client.get_database(
          settings.MONGO_DB_NAME, codec_options=codec_options
      )
      # self.db = self.client[settings.MONGO_DB_NAME] # Old way
      logfire.info(
          f"Successfully connected to MongoDB. Database: '{settings.MONGO_DB_NAME}'"
      )
      # Create indexes after successful connection
      await self.create_indexes()
    except (ConnectionFailure, OperationFailure) as e:
      logfire.error(
          f"Failed to connect to MongoDB or authentication failed: {e}")
      self.client = None
      self.db = None
      raise  # Re-raise the exception to signal connection failure
    except Exception as e:
      logfire.error(
          f"An unexpected error occurred during MongoDB connection: {e}",
          exc_info=True,
      )
      self.client = None
      self.db = None
      raise  # Re-raise

  async def close_mongo_connection(self):
    logfire.info("Closing MongoDB connection...")
    if self.client:
      self.client.close()
      self.client = None
      self.db = None
      logfire.info("MongoDB connection closed.")

  async def get_db(self) -> AsyncIOMotorDatabase:
    # Correct the check to use 'is None'
    if self.db is None:
      logfire.error("MongoDB database is not initialized.")
      raise RuntimeError("Database connection is not available.")
    return self.db

  async def create_indexes(self):
    """Creates necessary indexes in MongoDB collections if they don't exist."""
    logfire.info("Attempting to create MongoDB indexes...")
    if self.db is None:
      logfire.error(
          "Cannot create indexes, MongoDB database is not initialized.")
      return
    try:
      # Index for users collection (example: unique email)
      users_collection = self.db[USERS_COLLECTION]
      await users_collection.create_index(
          [("email", ASCENDING)], unique=True, name="email_unique_idx"
      )
      logfire.info(
          f"Index 'email_unique_idx' ensured for collection '{USERS_COLLECTION}'."
      )

      # Index for reports collection (example: timestamp descending)
      reports_collection = self.db[REPORTS_COLLECTION]
      await reports_collection.create_index(
          [("timestamp", DESCENDING)], name="timestamp_desc_idx"
      )
      logfire.info(
          f"Index 'timestamp_desc_idx' ensured for collection '{REPORTS_COLLECTION}'."
      )

      # Indexes for sheet sync collections
      sheet_products_coll = self.db[SHEET_PRODUCTS_COLLECTION]
      await sheet_products_coll.create_index(
          [("id", ASCENDING)], unique=True, name="sheet_product_id_unique_idx"
      )
      logfire.info(
          f"Index 'sheet_product_id_unique_idx' ensured for collection '{SHEET_PRODUCTS_COLLECTION}'."
      )

      sheet_generators_coll = self.db[SHEET_GENERATORS_COLLECTION]
      await sheet_generators_coll.create_index(
          [("id", ASCENDING)], unique=True, name="sheet_generator_id_unique_idx"
      )
      logfire.info(
          f"Index 'sheet_generator_id_unique_idx' ensured for collection '{SHEET_GENERATORS_COLLECTION}'."
      )

      sheet_branches_coll = self.db[SHEET_BRANCHES_COLLECTION]
      await sheet_branches_coll.create_index(
          [("address", ASCENDING)],
          unique=True,
          name="sheet_branch_address_unique_idx",
      )
      logfire.info(
          f"Index 'sheet_branch_address_unique_idx' ensured for collection '{SHEET_BRANCHES_COLLECTION}'."
      )

      sheet_config_coll = self.db[SHEET_CONFIG_COLLECTION]
      # _id is automatically indexed. If using a specific field like 'config_type' for multiple configs:
      await sheet_config_coll.create_index(
          [("config_type", ASCENDING)],
          unique=True,
          name="sheet_config_type_unique_idx",
          sparse=True,
      )
      logfire.info(
          f"Index 'sheet_config_type_unique_idx' (sparse) ensured for collection '{SHEET_CONFIG_COLLECTION}'."
      )

      # Indexes for Bland Call Logs
      bland_logs_coll = self.db[BLAND_CALL_LOGS_COLLECTION]
      # HubSpot Contact ID will be stored as _id, which is automatically indexed and unique.
      # We ensure 'id' field (which will be the HubSpot Contact ID) is used for _id upon insertion.
      await bland_logs_coll.create_index(
          [("status", ASCENDING)], name="bland_call_log_status_idx"
      )
      await bland_logs_coll.create_index(
          [("created_at", DESCENDING)], name="bland_call_log_created_at_idx"
      )
      await bland_logs_coll.create_index(
          [("phone_number", ASCENDING)],
          name="bland_call_log_phone_idx",
          sparse=True,
      )  # If searching by phone
      await bland_logs_coll.create_index(
          [("call_id_bland", ASCENDING)],
          name="bland_call_log_bland_call_id_idx",
          sparse=True,
      )  # If searching by Bland's call_id
      logfire.info(
          f"Indexes ensured for collection '{BLAND_CALL_LOGS_COLLECTION}'."
      )

      # Indexes for Error Logs
      error_logs_coll = self.db[ERROR_LOGS_COLLECTION]
      await error_logs_coll.create_index(
          [("timestamp", DESCENDING)], name="error_log_timestamp_idx"
      )
      await error_logs_coll.create_index(
          [("service_name", ASCENDING)], name="error_log_service_name_idx"
      )
      await error_logs_coll.create_index(
          [("error_type", ASCENDING)], name="error_log_error_type_idx"
      )
      logfire.info(
          f"Indexes ensured for collection '{ERROR_LOGS_COLLECTION}'.")

      # Indexes for Service Status
      SERVICE_STATUS_COLLECTION = (
          "service_status"  # Match the constant from background_check.py
      )
      service_status_coll = self.db[SERVICE_STATUS_COLLECTION]
      await service_status_coll.create_index(
          [("timestamp", DESCENDING)], name="service_status_timestamp_idx"
      )
      await service_status_coll.create_index(
          [("service_name", ASCENDING), ("timestamp", DESCENDING)],
          name="service_status_name_timestamp_idx",
      )
      logfire.info(
          f"Indexes ensured for collection '{SERVICE_STATUS_COLLECTION}'."
      )

      # Index for stats collection
      stats_collection = self.db[STATS_COLLECTION]
      # Removed unique=True
      await stats_collection.create_index([("_id", ASCENDING)], name="stats_id_idx")
      logfire.info(
          f"Index 'stats_id_idx' ensured for collection '{STATS_COLLECTION}'.")

    except Exception as e:
      logfire.error(f"Error creating MongoDB indexes: {e}", exc_info=True)

  async def check_connection(self) -> str:
    """Checks the MongoDB connection by pinging the database."""
    logfire.debug("Attempting MongoDB connection check...")
    if self.db is None:  # self.db is set in connect_and_initialize
      logfire.warn(
          "MongoDB connection check: Database instance (self.db) is None."
      )
      return "error: MongoDB database not initialized internally."
    try:
      await self.db.command("ping")  # Standard way to check MongoDB connection
      logfire.info("MongoDB connection check successful (ping).")
      return "ok"
    except (ConnectionFailure, OperationFailure) as e:
      logfire.error(
          f"MongoDB connection check failed (ping operation failed): {str(e)}",
          exc_info=True,
      )
      return f"error: Ping failed - {str(e)}"
    except Exception as e:  # Catch any other unexpected errors
      logfire.error(
          f"MongoDB connection check failed with an unexpected exception: {str(e)}",
          exc_info=True,
      )
      return f"error: Unexpected exception - {str(e)}"

  async def replace_sheet_collection_data(
      self, collection_name: str, data: List[Dict[str, Any]], id_field: str
  ):
    """
    Replaces all data in the specified collection with the new data from the sheet.
    Uses the value of `id_field` from each item in `data` as the `_id` in MongoDB.
    The entire item (including all its original fields) is stored in the document.
    Documents existing in MongoDB but not in the new `data` (based on `id_field`) are removed.
    """
    if self.db is None:
      logfire.error(
          "replace_sheet_collection_data: MongoDB database is not initialized.")
      raise RuntimeError("Database connection is not available.")
    collection = self.db[collection_name]
    logfire_extra_data = {
        "collection_name": collection_name,
        "id_field": id_field,
        "item_count": len(data),
    }

    if not data:
      logfire.info(
          f"SheetSync: Empty data provided for {collection_name}. Deleting all existing documents.",
          **logfire_extra_data,
      )
      try:
        delete_result = await collection.delete_many({})
        logfire.info(
            f"SheetSync: Deleted {delete_result.deleted_count} documents from {collection_name} due to empty sheet data.",
            **logfire_extra_data,
        )
      except Exception as e:
        logfire.error(
            f"SheetSync: Error deleting documents from {collection_name} for empty data: {e}",
            exc_info=True,
            **logfire_extra_data,
        )
      return

    operations = []
    current_ids_in_sheet_data = set()

    for item in data:
      item_id_value = item.get(id_field)

      if item_id_value is None:
        logfire.warning(
            f"SheetSync: Item in {collection_name} is missing id_field '{id_field}'. Skipping item: {item}",
            **logfire_extra_data,
        )
        continue

      current_ids_in_sheet_data.add(item_id_value)

      # The document to be $set will be the original item itself.
      # This ensures all fields from the sheet (e.g., "id", "name", "price", "category")
      # are present in the MongoDB document.
      # MongoDB's _id will be item_id_value.
      # Example: if item = {"id": "P1", "name": "ProdA", "price": 100},
      # MongoDB doc will be: {"_id": "P1", "id": "P1", "name": "ProdA", "price": 100}
      document_to_set = item

      operations.append(
          UpdateOne(
              {
                  "_id": item_id_value
              },  # Filter by _id (which is the sheet's id_field value)
              {"$set": document_to_set},  # Set all fields from the item
              upsert=True,
          )
      )

    if operations:
      logfire.info(
          f"SheetSync: Performing {len(operations)} bulk upsert operations on {collection_name} using '{id_field}' as _id source.",
          **logfire_extra_data,
      )
      if operations:  # Log sample for debugging
        # Correctly access filter (q) and update (u) from the UpdateOne's document
        sample_op_doc = operations[0]._doc
        logfire.debug(
            f"SheetSync: Sample operation for {collection_name}: Filter={{'_id': {sample_op_doc.get('q', {}).get('_id')}}}, Update={{'$set': {sample_op_doc.get('u', {}).get('$set')}}}",
            **logfire_extra_data,
        )
      try:
        result = await collection.bulk_write(operations, ordered=False)
        logfire.info(
            f"SheetSync: Bulk write to {collection_name} completed. Upserted: {result.upserted_count}, Modified: {result.modified_count}, Matched: {result.matched_count}.",
            **logfire_extra_data,
        )
      except Exception as e:
        logfire.error(
            f"SheetSync: Error during bulk write for {collection_name}: {e}",
            exc_info=True,
            **logfire_extra_data,
        )
        # Depending on requirements, you might want to raise e or handle it further
    else:
      logfire.info(
          f"SheetSync: No valid operations to perform for {collection_name} (e.g., all items lacked id_field or data was empty after filtering).",
          **logfire_extra_data,
      )

    # After upserting, delete any documents that were not in the new data list.
    # This ensures the collection is an exact mirror of the 'data' list from the sheet.
    if current_ids_in_sheet_data:  # Only delete if there was some valid new data
      delete_filter = {"_id": {"$nin": list(current_ids_in_sheet_data)}}
      try:
        delete_result = await collection.delete_many(delete_filter)
        if delete_result.deleted_count > 0:
          logfire.info(
              f"SheetSync: Deleted {delete_result.deleted_count} documents from {collection_name} that are no longer in the sheet data.",
              **logfire_extra_data,
          )
      except Exception as e:
        logfire.error(
            f"SheetSync: Error deleting old documents from {collection_name}: {e}",
            exc_info=True,
            **logfire_extra_data,
        )
    elif (
        not operations and data
        # New data was present, but no operations were made (e.g. all items lacked id_field)
    ):
      logfire.warning(
          f"SheetSync: No documents were upserted for {collection_name}, and therefore no old documents were deleted. The collection might be stale if it previously had data.",
          **logfire_extra_data,
      )

  async def upsert_sheet_config_document(
      self,
      document_id: str,
      config_data: Dict[str, Any],
      config_type: Optional[str] = None,
  ) -> Dict[str, Any]:
    """Upserts a single configuration document in the SHEET_CONFIG_COLLECTION."""
    db = await self.get_db()
    collection = db[SHEET_CONFIG_COLLECTION]

    # The document to be upserted. We'll use the provided document_id as MongoDB's _id.
    payload_to_set = {**config_data, "last_updated_mongo": datetime.utcnow()}
    if config_type:
      payload_to_set["config_type"] = config_type

    query = {"_id": document_id}  # Query by the custom _id
    update_doc = {"$set": payload_to_set}

    try:
      update_result = await collection.update_one(query, update_doc, upsert=True)
      upserted_id_str = None
      if update_result.upserted_id is not None:
        upserted_id_str = str(update_result.upserted_id)
      elif (
          update_result.matched_count > 0
      ):  # If matched, the ID was the document_id
        upserted_id_str = document_id

      logfire.info(
          f"Upserted document with _id '{document_id}' in MongoDB collection '{SHEET_CONFIG_COLLECTION}'. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}, UpsertedId: {upserted_id_str}"
      )
      return {
          "matched_count": update_result.matched_count,
          "modified_count": update_result.modified_count,
          "upserted_id": upserted_id_str,
          "success": True,
      }
    except Exception as e:
      logfire.error(
          f"Failed to upsert document with _id '{document_id}' in MongoDB collection '{SHEET_CONFIG_COLLECTION}': {e}",
          exc_info=True,
      )
      return {"success": False, "error": str(e)}

  # --- Dashboard Specific Methods ---

  async def log_report(
      self,
      report_type: str,
      data: Dict[str, Any],
      success: bool,
      error_message: Optional[str] = None,
  ):
    """Logs a report document to the reports collection."""
    db = await self.get_db()
    collection = db[REPORTS_COLLECTION]
    report_doc = {
        "timestamp": datetime.utcnow(),
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

  async def increment_request_stat(self, stat_name: str, success: bool):
    """Increments a counter for a given statistic (e.g., quote_requests) in MongoDB."""
    logfire.info(
        f"increment_request_stat: Attempting for '{stat_name}', success: {success}. DB state: {'DB available' if self.db is not None else 'DB NOT AVAILABLE'}")

    if self.db is None:
      logfire.error(
          f"increment_request_stat: MongoDB database is not initialized. Cannot increment stat for {stat_name}."
      )
      return

    # Log database and collection names
    db_name = self.db.name
    collection_name_actual = STATS_COLLECTION
    logfire.info(
        f"increment_request_stat: Operating on DB: '{db_name}', Collection: '{collection_name_actual}'")

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
            f"increment_request_stat: DEBUG READ AFTER UPSERT for '{stat_name}' FOUND: {doc_after_upsert}")
      else:
        logfire.warning(
            f"increment_request_stat: DEBUG READ AFTER UPSERT for '{stat_name}' NOT FOUND.")

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
        f"get_dashboard_stats: Attempting. DB state: {'DB available' if self.db is not None else 'DB NOT AVAILABLE'}")
    if self.db is None:
      logfire.error(
          "get_dashboard_stats: MongoDB database is not initialized. Cannot fetch stats."
      )
      return {}

    # Log database and collection names
    db_name = self.db.name
    collection_name_actual = STATS_COLLECTION
    logfire.info(
        f"get_dashboard_stats: Operating on DB: '{db_name}', Collection: '{collection_name_actual}'")

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
              f"Found stat '{stat_name}': Total={doc.get('total', 0)}, Success={doc.get('successful', 0)}, Failed={doc.get('failed', 0)}")
        else:
          logfire.warning(  # Changed to warning for better visibility
              f"No document found for stat_name: '{stat_name}' in {STATS_COLLECTION}. Returning zeros."
          )
          dashboard_data[stat_name] = {
              "total": 0, "successful": 0, "failed": 0}
      # Changed to info
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

  async def get_recent_reports(
      self, report_type: Optional[Union[str, List[str]]] = None, limit: int = 100
  ) -> List[Dict[str, Any]]:
    """Retrieves recent reports, optionally filtered by a single type or a list of types."""
    db = await self.get_db()
    collection = db[REPORTS_COLLECTION]
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
    db = await self.get_db()
    collection = db[REPORTS_COLLECTION]
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
      return summary  # Return default summary on error

  # ... (existing code in MongoService class) ...

  async def get_bland_calls(
      self,
      page: int,
      page_size: int,
      status_filter: Optional[str],
      sort_field: str,
      sort_order: int,
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves a paginated list of Bland call logs, optionally filtered by status
    and sorted by a specified field and order.
    """
    db = await self.get_db()
    collection = db[BLAND_CALL_LOGS_COLLECTION]
    query = {}
    if status_filter:
      query["status"] = status_filter

    # Calculate skip for pagination
    skip = (page - 1) * page_size

    try:
      cursor = (
          collection.find(query)
          .sort(sort_field, sort_order)
          .skip(skip)
          .limit(page_size)
      )
      items = await cursor.to_list(length=page_size)

      # Convert ObjectId to string for JSON serialization if needed
      # and ensure all necessary fields are present or defaulted.
      processed_items = []
      for item_from_db in items:
        # Create a new dictionary to avoid modifying the original item_from_db if it's used elsewhere
        item_for_model = dict(item_from_db)
        # Map _id to id and convert to string
        item_for_model["id"] = str(item_for_model.pop("_id"))

        # Ensure other fields expected by BlandCallLog model are present
        item_for_model.setdefault("call_id_bland", None)
        item_for_model.setdefault("retry_of_call_id", None)
        item_for_model.setdefault("retry_reason", None)
        item_for_model.setdefault("pathway_id_used", None)
        item_for_model.setdefault("voice_id", None)
        item_for_model.setdefault("transfer_phone_number", None)
        item_for_model.setdefault("webhook_url", None)
        item_for_model.setdefault(
            "request_data_variables", {})  # Default to empty dict
        item_for_model.setdefault("max_duration", None)
        item_for_model.setdefault("analysis", None)
        item_for_model.setdefault("summary", None)
        item_for_model.setdefault("transcript", None)
        item_for_model.setdefault("recordings", [])  # Default to empty list
        item_for_model.setdefault("error_message", None)
        item_for_model.setdefault("duration", 0.0)  # Default to 0.0
        item_for_model.setdefault("cost", 0.0)  # Default to 0.0
        item_for_model.setdefault("answered_by", None)
        item_for_model.setdefault("ended_reason", None)
        item_for_model.setdefault("external_id", None)
        item_for_model.setdefault("from_number", None)
        item_for_model.setdefault(
            "to_number", item_for_model.get("phone_number"))
        item_for_model.setdefault("batch_id", None)
        # Ensure all fields from BlandCallStatus are potentially present or defaulted if not already
        for status_member in BlandCallStatus:
          # Example, adjust if model uses different naming
          item_for_model.setdefault(status_member.name.lower(), None)

        processed_items.append(item_for_model)

      total_items = await collection.count_documents(query)
      logfire.debug(
          f"Retrieved {len(processed_items)} bland call logs from DB. Total matching query: {total_items}. Page: {page}, PageSize: {page_size}"
      )
      return processed_items, total_items
    except Exception as e:
      logfire.error(
          f"Failed to retrieve bland call logs from MongoDB: {e}", exc_info=True
      )
      return [], 0

  # -- Get a single bland call using contact_id
  async def get_bland_call_log(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single Bland call log by contact_id.

    Args:
        contact_id: The HubSpot Contact ID used as _id in MongoDB

    Returns:
        A dictionary with the call log data or None if not found
    """
    if self.db is None:
      logfire.error("get_bland_call_log: MongoDB database is not initialized.")
      return None

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]

    try:
      item = await collection.find_one({"_id": contact_id})
      if item:
        # Create a new dictionary to avoid modifying the original item if it's used elsewhere
        item_dict = dict(item)
        # Map _id to id and convert to string
        item_dict["id"] = str(item_dict.pop("_id"))

        # Ensure other fields expected by BlandCallLog model are present
        item_dict.setdefault("call_id_bland", None)
        item_dict.setdefault("retry_of_call_id", None)
        item_dict.setdefault("retry_reason", None)
        item_dict.setdefault("pathway_id_used", None)
        item_dict.setdefault("voice_id", None)
        item_dict.setdefault("transfer_phone_number", None)
        item_dict.setdefault("webhook_url", None)
        item_dict.setdefault("request_data_variables", {})
        item_dict.setdefault("max_duration", None)
        item_dict.setdefault("analysis", None)
        item_dict.setdefault("summary", None)
        item_dict.setdefault("transcript", None)
        item_dict.setdefault("recordings", [])
        item_dict.setdefault("error_message", None)
        item_dict.setdefault("duration", 0.0)
        item_dict.setdefault("cost", 0.0)
        item_dict.setdefault("answered_by", None)
        item_dict.setdefault("ended_reason", None)
        item_dict.setdefault("external_id", None)
        item_dict.setdefault("from_number", None)
        item_dict.setdefault("to_number", item_dict.get("phone_number"))
        item_dict.setdefault("batch_id", None)

        # Ensure all fields from BlandCallStatus are potentially present or defaulted
        for status_member in BlandCallStatus:
          item_dict.setdefault(status_member.name.lower(), None)

        logfire.debug(f"Retrieved bland call log for contact_id: {contact_id}")
        return item_dict

      logfire.info(f"No bland call log found for contact_id: {contact_id}")
      return None

    except Exception as e:
      logfire.error(
          f"Failed to retrieve bland call log from MongoDB for contact_id {contact_id}: {e}",
          exc_info=True
      )
      return None

  async def get_bland_call_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about Bland call logs, including counts by status.
    Returns a dictionary with total_calls and counts for each status in BlandCallStatus.

    Returns:
        Dictionary with keys: total_calls, pending_calls, completed_calls, failed_calls, retrying_calls
    """
    if self.db is None:
      logfire.error(
          "get_bland_call_stats: MongoDB database is not initialized.")
      return {
          "total_calls": 0,
          "pending_calls": 0,
          "completed_calls": 0,
          "failed_calls": 0,
          "retrying_calls": 0
      }

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]

    try:
      # Get total count of calls
      total_calls = await collection.count_documents({})

      # Get count for each status
      pending_calls = await collection.count_documents(
          {"status": BlandCallStatus.PENDING.value})
      completed_calls = await collection.count_documents(
          {"status": BlandCallStatus.COMPLETED.value})
      failed_calls = await collection.count_documents(
          {"status": BlandCallStatus.FAILED.value})
      retrying_calls = await collection.count_documents(
          {"status": BlandCallStatus.RETRYING.value})

      stats = {
          "total_calls": total_calls,
          "pending_calls": pending_calls,
          "completed_calls": completed_calls,
          "failed_calls": failed_calls,
          "retrying_calls": retrying_calls
      }

      logfire.info(f"Retrieved Bland call statistics: {stats}")
      return stats
    except Exception as e:
      logfire.error(
          f"Failed to retrieve Bland call statistics from MongoDB: {e}", exc_info=True)
      # Return zeroes for all counts in case of error
      return {
          "total_calls": 0,
          "pending_calls": 0,
          "completed_calls": 0,
          "failed_calls": 0,
          "retrying_calls": 0
      }

  async def update_bland_call_log_internal(
      self,
      contact_id: str,
      update_data: Dict[str, Any]
  ) -> bool:
    """
    Updates a Bland call log document in MongoDB based on the contact_id.
    Used internally by BlandAIManager to update call status, errors, and other details.

    Args:
        contact_id: The HubSpot Contact ID used as _id in MongoDB
        update_data: MongoDB update operation document (e.g., {"$set": {...}, "$inc": {...}})

    Returns:
        True if the update was successful (or document was found), False otherwise
    """
    if self.db is None:
      logfire.error(
          "update_bland_call_log_internal: MongoDB database is not initialized.")
      return False

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]

    try:
      # Use _id for querying since that's how we store contact_id in MongoDB
      result = await collection.update_one({"_id": contact_id}, update_data)

      if result.matched_count > 0:
        logfire.info(
            f"Updated Bland call log for contact_id: {contact_id}. "
            f"Modified: {result.modified_count}"
        )
        return True
      else:
        logfire.warning(
            f"No Bland call log found to update for contact_id: {contact_id}"
        )
        return False
    except Exception as e:
      logfire.error(
          f"Failed to update Bland call log for contact_id {contact_id}: {e}",
          exc_info=True
      )
      return False

  async def update_bland_call_log_completion(
      self,
      contact_id: str,
      call_id_bland: str,
      status: BlandCallStatus,
      transcript_payload: List[Dict[str, Any]],
      summary_text: Optional[str] = None,
      classification_payload: Optional[Dict[str, Any]] = None,
      full_webhook_payload: Optional[Dict[str, Any]] = None,
      call_completed_timestamp: Optional[datetime] = None,
      bland_processing_result_payload: Optional[Dict[str, Any]] = None,
      processing_status_message: Optional[str] = None
  ) -> bool:
    """
    Updates a Bland call log with completion data received from webhook.

    Args:
        contact_id: The HubSpot Contact ID used as _id in MongoDB
        call_id_bland: The Bland.ai call ID for verification
        status: The new status (typically COMPLETED)
        transcript_payload: The transcript data from Bland.ai
        summary_text: Optional summary text extracted from the transcript
        classification_payload: Optional classification data for the call
        full_webhook_payload: Optional full webhook payload for reference
        call_completed_timestamp: When the call was completed
        bland_processing_result_payload: Results from processing the transcript
        processing_status_message: Status message from transcript processing

    Returns:
        True if the update was successful, False otherwise
    """
    if self.db is None:
      logfire.error(
          "update_bland_call_log_completion: MongoDB database is not initialized.")
      return False

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]
    current_time = datetime.utcnow()
    completed_time = call_completed_timestamp or current_time

    # Build update document
    update_data = {
        "$set": {
            "status": status.value,
            "updated_at": current_time,
            "completed_at": completed_time,
            "transcript": transcript_payload,  # Store the full transcript payload
            "summary": summary_text,
            "analysis": {
                "classification": classification_payload,
                "processing_result": bland_processing_result_payload,
                "processing_status": processing_status_message
            },
            "full_webhook_payload": full_webhook_payload
        }
    }

    try:
      # Use both _id (contact_id) and call_id_bland for verification to ensure
      # we're updating the correct document
      query = {
          "_id": contact_id,
          "call_id_bland": call_id_bland
      }

      result = await collection.update_one(query, update_data)

      if result.matched_count > 0:
        logfire.info(
            f"Updated Bland call log completion for contact_id: {contact_id}, "
            f"call_id_bland: {call_id_bland}. Modified: {result.modified_count}"
        )
        return True
      else:
        # If no match with both fields, try with just contact_id (fallback)
        fallback_result = await collection.update_one(
            {"_id": contact_id}, update_data
        )

        if fallback_result.matched_count > 0:
          logfire.warning(
              f"Updated Bland call log with fallback query (contact_id only) for "
              f"contact_id: {contact_id}. The stored call_id_bland may not match "
              f"the provided call_id_bland: {call_id_bland}"
          )
          return True
        else:
          logfire.error(
              f"No Bland call log found to update for contact_id: {contact_id}, "
              f"call_id_bland: {call_id_bland}"
          )
          return False
    except Exception as e:
      logfire.error(
          f"Failed to update Bland call log completion for contact_id {contact_id}, "
          f"call_id_bland {call_id_bland}: {e}",
          exc_info=True
      )
      return False

  async def log_bland_call_attempt(
      self,
      contact_id: str,
      phone_number: str,
      task: Optional[str] = None,
      pathway_id_used: Optional[str] = None,
      initial_status: BlandCallStatus = BlandCallStatus.PENDING,
      call_id_bland: Optional[str] = None,
      retry_of_call_id: Optional[str] = None,
      retry_reason: Optional[str] = None,
      voice_id: Optional[str] = None,
      webhook_url: Optional[str] = None,
      max_duration: Optional[int] = 12,
      request_data_variables: Optional[Dict[str, Any]] = None,
      transfer_phone_number: Optional[str] = None
  ) -> bool:
    """
    Logs an initial Bland.ai call attempt to MongoDB.
    Creates a new document or updates an existing one if the contact_id already exists.

    Args:
        contact_id: The HubSpot Contact ID to use as _id in MongoDB
        phone_number: The phone number being called
        task: The task description if pathway_id is not used
        pathway_id_used: The Bland.ai pathway ID used for the call, if any
        initial_status: The initial status of the call (default: PENDING)
        call_id_bland: The Bland.ai call ID if already received
        retry_of_call_id: The original call ID if this is a retry
        retry_reason: Reason for retry if applicable
        voice_id: The voice ID used for the call
        webhook_url: The webhook URL configured for Bland.ai
        max_duration: Maximum duration of the call in minutes
        request_data_variables: Variables passed to Bland.ai in request_data
        transfer_phone_number: Transfer phone number for the call

    Returns:
        True if the log was created successfully, False otherwise
    """
    if self.db is None:
      logfire.error(
          "log_bland_call_attempt: MongoDB database is not initialized.")
      return False

    collection = self.db[BLAND_CALL_LOGS_COLLECTION]
    current_time = datetime.utcnow()

    # Prepare document for insertion or update
    document = {
        "phone_number": phone_number,
        "status": initial_status.value,
        "created_at": current_time,
        "updated_at": current_time,
        "task": task,
        "pathway_id_used": pathway_id_used,
        "call_id_bland": call_id_bland,
        "webhook_url": webhook_url,
        "voice_id": voice_id,
        "max_duration": max_duration,
        "transfer_phone_number": transfer_phone_number,
        "request_data_variables": request_data_variables or {}
    }

    # Add retry information if this is a retry
    if retry_of_call_id:
      document["retry_of_call_id"] = retry_of_call_id
      document["retry_reason"] = retry_reason
      # Increment retry_count field if this is a retry
      update_operation = {
          "$set": document,
          "$inc": {"retry_count": 1},
          "$setOnInsert": {"_id": contact_id}
      }
    else:
      # For new calls (not retries), set retry_count to 0
      document["retry_count"] = 0
      document["retry_of_call_id"] = None
      document["retry_reason"] = None
      update_operation = {
          "$set": document,
          "$setOnInsert": {"_id": contact_id, "created_at": current_time}
      }

    try:
      # Use upsert to create a new document or update an existing one
      result = await collection.update_one(
          {"_id": contact_id},
          update_operation,
          upsert=True
      )

      if result.upserted_id:
        logfire.info(
            f"Created new Bland call log for contact_id: {contact_id}, "
            f"phone_number: {phone_number}, initial_status: {initial_status.value}"
        )
      else:
        logfire.info(
            f"Updated existing Bland call log for contact_id: {contact_id}, "
            f"phone_number: {phone_number}, status set to: {initial_status.value}"
        )

      return True
    except Exception as e:
      logfire.error(
          f"Failed to log Bland call attempt for contact_id {contact_id}: {e}",
          exc_info=True
      )
      return False

  async def log_error_to_db(
      self,
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None,
      stack_trace: Optional[str] = None,
      request_context: Optional[Dict[str, Any]] = None
  ) -> Optional[str]:
    """
    Logs an error to the error_logs collection in MongoDB.

    Args:
        service_name: Name of the service where the error occurred
        error_type: Type of error (e.g., ValueError, HTTPException, CacheMiss)
        message: The error message
        details: Specific details about the error for debugging
        stack_trace: Optional stack trace if available
        request_context: Optional contextual information about the request

    Returns:
        String ID of the created error log document, or None if operation failed
    """
    if self.db is None:
      logfire.error("log_error_to_db: MongoDB database is not initialized.")
      return None

    collection = self.db[ERROR_LOGS_COLLECTION]
    current_time = datetime.utcnow()

    # Create error document based on ErrorLog model structure
    error_doc = {
        "_id": uuid.uuid4(),  # Generate a unique ID
        "timestamp": current_time,
        "service_name": service_name,
        "error_type": error_type,
        "error_message": message,
        "stack_trace": stack_trace,
        "request_context": request_context,
        "additional_data": details  # Use details parameter for additional_data field
    }

    try:
      result = await collection.insert_one(error_doc)
      error_id = str(result.inserted_id)
      logfire.info(
          f"Logged error to MongoDB: type={error_type}, service={service_name}, id={error_id}"
      )
      return error_id
    except Exception as e:
      logfire.error(
          f"Failed to log error to MongoDB: {e}. Original error: {message}",
          exc_info=True
      )
      return None
