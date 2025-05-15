# filepath: app/services/mongo/mongo.py
import logfire
import logging
import copy
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.codec_options import CodecOptions, UuidRepresentation
from app.core.config import settings
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timezone
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
      logfire.critical(f"MongoDB service startup failed: {e}", exc_info=True)
      mongo_service_instance = None  # Set back to None on failure
  else:
    logfire.info("MongoDB service already started.")


async def shutdown_mongo_service():
  global mongo_service_instance
  if mongo_service_instance:
    logfire.info("Attempting to shut down MongoDB service...")
    await mongo_service_instance.close_mongo_connection()
    mongo_service_instance = None
    logfire.info("MongoDB service shut down successfully.")
  else:
    logfire.info("MongoDB service not running or already shut down.")


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

  # --- Generic Error Logging Method ---
  async def log_error_to_db(
      self,
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None,
      contact_id: Optional[str] = None,  # Optional HubSpot Contact ID
  ) -> Optional[str]:
    """
    Logs a generic error to the ERROR_LOGS_COLLECTION.
    Returns the ID of the inserted error log document or None if logging failed.
    """
    if self.db is None:
      logfire.error(
          "log_error_to_db: MongoDB database is not initialized. Cannot log error."
      )
      # Potentially raise an exception or handle as per application's error strategy
      return None

    collection = self.db[ERROR_LOGS_COLLECTION]
    error_doc = {
        "timestamp": datetime.now(timezone.utc),
        "service_name": service_name,
        "error_type": error_type,
        "message": message,
        "details": details if details is not None else {},
        "contact_id": contact_id,  # Will be None if not provided
        "resolved": False,  # Default to unresolved
        "resolved_at": None,
    }
    try:
      result = await collection.insert_one(error_doc)
      logfire.info(
          f"Logged error for service '{service_name}' to MongoDB with id: {result.inserted_id}",
          error_id=str(result.inserted_id),
          service_name=service_name,
      )
      return str(result.inserted_id)
    except Exception as e:
      # Log to logfire as a fallback, but avoid recursive DB logging if this itself fails
      logfire.error(
          f"Failed to log error to MongoDB for service '{service_name}': {e}",
          exc_info=True,
          original_error_message=message,
      )
      return None

  # --- Bland Call Log Specific Methods ---

  async def log_bland_call_attempt(
      self,
      contact_id: str,
      phone_number: str,
      task: Optional[str],  # Task description if pathway_id_used is None
      initial_status: BlandCallStatus = BlandCallStatus.PENDING,
      call_id_bland: Optional[
          str
      ] = None,  # Bland's call_id for *this* attempt, if known early
      retry_of_call_id: Optional[
          str
      ] = None,  # Bland's call_id of the *previous* attempt being retried
      retry_reason: Optional[str] = None,
      # New fields for storing call inputs
      voice_id: Optional[int] = None,
      transfer_phone_number: Optional[str] = None,
      webhook_url: Optional[str] = None,
      request_data_variables: Optional[Dict[str, Any]] = None,
      max_duration: Optional[int] = None,
      pathway_id_used: Optional[str] = None,
  ) -> Optional[str]:
    """
    Logs an attempt of a Bland.ai call or updates for a retry.
    HubSpot Contact ID (contact_id) is used as MongoDB '_id'.
    """
    db = await self.get_db()
    collection = db[BLAND_CALL_LOGS_COLLECTION]

    current_time = datetime.utcnow()

    doc_fields = {
        "phone_number": phone_number,
        "task": task,
        "pathway_id_used": pathway_id_used,
        "status": initial_status.value,  # Will be PENDING for new, or updated if retry
        "updated_at": current_time,
        "voice_id": voice_id,
        "transfer_phone_number": transfer_phone_number,
        "webhook_url": webhook_url,
        "request_data_variables": request_data_variables,
        "max_duration": max_duration,
        # These are specific to this attempt, might be None initially
        "call_id_bland": call_id_bland,
        "retry_of_call_id": retry_of_call_id,
        "retry_reason": retry_reason,
    }
    # Remove None values from doc_fields to avoid inserting them if not provided
    doc_fields = {k: v for k, v in doc_fields.items() if v is not None}

    try:
      # Attempt to insert a new document
      doc_to_insert = {
          "_id": contact_id,
          "created_at": current_time,
          "retry_count": 0,  # Initial attempt
          **doc_fields,
      }
      # Ensure status is PENDING for a truly new insert.
      doc_to_insert["status"] = BlandCallStatus.PENDING.value

      result = await collection.insert_one(doc_to_insert)
      logfire.info(
          f"Logged new Bland call attempt for contact_id: {contact_id}, mongo_id: {result.inserted_id}",
          contact_id=contact_id,
      )
      return str(result.inserted_id)
    except OperationFailure as e:
      if (
          e.code == 11000
      ):  # Duplicate key error for _id, means it's a retry or concurrent attempt
        logfire.warning(
            f"Bland call log for contact_id: {contact_id} already exists. Updating for retry.",
            contact_id=contact_id,
        )

        update_set_fields = {
            "status": BlandCallStatus.RETRYING.value,
            "updated_at": current_time,
            "last_retry_attempt_at": current_time,
            # Update all params for this new attempt
            "phone_number": phone_number,
            "task": task,
            "pathway_id_used": pathway_id_used,
            "voice_id": voice_id,
            "transfer_phone_number": transfer_phone_number,
            "webhook_url": webhook_url,
            "request_data_variables": request_data_variables,
            "max_duration": max_duration,
            "retry_reason": retry_reason,
            # This is the Bland call_id of the *previous* attempt
            "retry_of_call_id": retry_of_call_id,
            # This is the Bland call_id for *this current* retry attempt, if known now (usually None)
            "call_id_bland": call_id_bland,
        }
        # Clean None values from $set to avoid overwriting with None if not provided for the retry
        update_set_fields = {
            k: v for k, v in update_set_fields.items() if v is not None
        }

        update_data_for_retry = {
            "$set": update_set_fields,
            "$inc": {"retry_count": 1},
        }

        # If call_id_bland is explicitly None for this retry attempt (e.g. previous one failed before getting it, and this one hasn

  async def update_bland_call_log_completion(
      self,
      contact_id: str,
      call_id_bland: str,
      status: BlandCallStatus,
      transcript_payload: Optional[List[Dict[str, Any]]],
      summary_text: Optional[str],
      classification_payload: Optional[Dict[str, Any]],
      full_webhook_payload: Dict[str, Any],
      call_completed_timestamp: datetime,
      bland_processing_result_payload: Dict[str, Any],
      processing_status_message: Optional[str]
  ) -> bool:
    """
    Updates a Bland call log upon completion and processing of the webhook.
    Uses contact_id (as _id) and call_id_bland to identify the correct log entry.
    """
    db = await self.get_db()
    collection = db[BLAND_CALL_LOGS_COLLECTION]
    current_time = datetime.utcnow()

    query = {
        "_id": contact_id,
        "call_id_bland": call_id_bland  # Ensure we update the specific call attempt
    }

    update_fields = {
        "status": status.value,
        "updated_at": current_time,
        "completed_at_bland": call_completed_timestamp,  # Timestamp from Bland payload
        "transcript_payload": transcript_payload,
        "summary_text": summary_text,
        "classification_payload": classification_payload,
        "full_webhook_payload": full_webhook_payload,
        "bland_processing_result": bland_processing_result_payload,
        "processing_status_message": processing_status_message,
        "error_message": None  # Clear any previous error message for this attempt if now completed
    }
    # Remove None values to avoid overwriting existing fields with None if not provided
    update_fields = {k: v for k, v in update_fields.items() if v is not None}

    update_doc = {"$set": update_fields}

    try:
      result = await collection.update_one(query, update_doc)
      if result.matched_count > 0:
        logfire.info(
            f"Successfully updated Bland call log completion for contact_id: {contact_id}, call_id_bland: {call_id_bland}",
            contact_id=contact_id, call_id_bland=call_id_bland, modified_count=result.modified_count
        )
        return True
      else:
        logfire.warning(
            f"No Bland call log found to update for completion with contact_id: {contact_id} and call_id_bland: {call_id_bland}",
            contact_id=contact_id, call_id_bland=call_id_bland
        )
        # Attempt to find by contact_id only if specific call_id_bland wasn't found,
        # this might indicate a mismatch or a log that wasn't updated with call_id_bland yet.
        # Check if call_id_bland was never set
        fallback_query = {"_id": contact_id, "call_id_bland": None}
        fallback_result = await collection.update_one(fallback_query, update_doc)
        if fallback_result.matched_count > 0:
          logfire.info(
              f"Successfully updated Bland call log completion via fallback for contact_id: {contact_id} (original call_id_bland: {call_id_bland})",
              contact_id=contact_id, call_id_bland=call_id_bland, modified_count=fallback_result.modified_count
          )
          return True
        else:
          logfire.error(
              f"Fallback update also failed for Bland call log completion. contact_id: {contact_id}",
              contact_id=contact_id, call_id_bland=call_id_bland
          )
          return False
    except Exception as e:
      logfire.error(
          f"Error updating Bland call log completion for contact_id: {contact_id}, call_id_bland: {call_id_bland}: {e}",
          exc_info=True, contact_id=contact_id, call_id_bland=call_id_bland, error_details=str(e)
      )
      return False

# --- Dependency Injector Function ---


async def get_mongo_service() -> MongoService:
  """
  FastAPI dependency injector for MongoService.
  Returns the initialized mongo_service_instance.
  Raises HTTPException if the service is not available.
  """
  if mongo_service_instance is None:
    logfire.error(
        "get_mongo_service: mongo_service_instance is None. MongoDB might not have started correctly."
    )
    raise HTTPException(
        status_code=503,
        detail="MongoDB service is not available. Initialization may have failed.",
    )
  return mongo_service_instance

  # --- Sheet Sync Specific Methods ---
