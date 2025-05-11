# filepath: app/services/mongo/mongo.py
import logfire
import logging
import copy # Added import
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.server_api import ServerApi # Import ServerApi
from bson.codec_options import CodecOptions, UuidRepresentation # Import UuidRepresentation
from app.core.config import settings
from typing import Optional, Dict, Any, List, Union, Tuple # Import Union
from datetime import datetime, timezone # Added import
from pymongo import ASCENDING, DESCENDING # Import for indexes
from pymongo import UpdateOne # Ensure UpdateOne is imported
from fastapi import HTTPException
from app.models.bland_call_log import BlandCallLog, BlandCallStatus, PaginatedBlandCallResponse, BlandCallStats
from app.models.error_log import ErrorLog, PaginatedErrorLogResponse # Added ErrorLog models

# --- Constants for Collection Names ---
REPORTS_COLLECTION = "reports"
USERS_COLLECTION = "users" # Define users collection name here
SHEET_PRODUCTS_COLLECTION = "sheet_products"
SHEET_GENERATORS_COLLECTION = "sheet_generators"
SHEET_BRANCHES_COLLECTION = "sheet_branches"
SHEET_CONFIG_COLLECTION = "sheet_config"
BLAND_CALL_LOGS_COLLECTION = "bland_call_logs"
ERROR_LOGS_COLLECTION = "error_logs" # New collection for general errors

class MongoService:
    # client and db are now instance attributes, initialized in __init__
    client: Optional[AsyncIOMotorClient]
    db: Optional[AsyncIOMotorDatabase]

    def __init__(self):
        # Initialize attributes to None before async connection
        self.client = None
        self.db = None
        logfire.info("MongoService instance created. Connection will be established.")

    async def connect_and_initialize(self):
        """Connects to MongoDB and performs initial setup like index creation."""
        logfire.info("Connecting to MongoDB...")
        if not settings.MONGO_CONNECTION_URL:
            logfire.error("MONGO_CONNECTION_URL not set in environment/settings.")
            raise ValueError("MongoDB connection URL is not configured.")

        try:
            # Configure UUID representation
            codec_options = CodecOptions(uuid_representation=UuidRepresentation.STANDARD)
            
            self.client = AsyncIOMotorClient(
                settings.MONGO_CONNECTION_URL, 
                serverSelectionTimeoutMS=5000, # Add timeout
                uuidRepresentation='standard' # Explicitly set standard UUID representation
                # server_api=ServerApi('1') # Optional: Specify Stable API version
            )
            # The ismaster command is cheap and does not require auth.
            await self.client.admin.command('ismaster')
            # Get database with codec options
            self.db = self.client.get_database(
                settings.MONGO_DB_NAME, 
                codec_options=codec_options
            )
            # self.db = self.client[settings.MONGO_DB_NAME] # Old way
            logfire.info(f"Successfully connected to MongoDB. Database: '{settings.MONGO_DB_NAME}'")
            # Create indexes after successful connection
            await self.create_indexes()
        except (ConnectionFailure, OperationFailure) as e:
            logfire.error(f"Failed to connect to MongoDB or authentication failed: {e}")
            self.client = None
            self.db = None
            raise # Re-raise the exception to signal connection failure
        except Exception as e:
            logfire.error(f"An unexpected error occurred during MongoDB connection: {e}", exc_info=True)
            self.client = None
            self.db = None
            raise # Re-raise

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
             logfire.error("Cannot create indexes, MongoDB database is not initialized.")
             return
        try:
            # Index for users collection (example: unique email)
            users_collection = self.db[USERS_COLLECTION]
            await users_collection.create_index([("email", ASCENDING)], unique=True, name="email_unique_idx")
            logfire.info(f"Index 'email_unique_idx' ensured for collection '{USERS_COLLECTION}'.")

            # Index for reports collection (example: timestamp descending)
            reports_collection = self.db[REPORTS_COLLECTION]
            await reports_collection.create_index([("timestamp", DESCENDING)], name="timestamp_desc_idx")
            logfire.info(f"Index 'timestamp_desc_idx' ensured for collection '{REPORTS_COLLECTION}'.")

            # Indexes for sheet sync collections
            sheet_products_coll = self.db[SHEET_PRODUCTS_COLLECTION]
            await sheet_products_coll.create_index([("id", ASCENDING)], unique=True, name="sheet_product_id_unique_idx")
            logfire.info(f"Index 'sheet_product_id_unique_idx' ensured for collection '{SHEET_PRODUCTS_COLLECTION}'.")

            sheet_generators_coll = self.db[SHEET_GENERATORS_COLLECTION]
            await sheet_generators_coll.create_index([("id", ASCENDING)], unique=True, name="sheet_generator_id_unique_idx")
            logfire.info(f"Index 'sheet_generator_id_unique_idx' ensured for collection '{SHEET_GENERATORS_COLLECTION}'.")

            sheet_branches_coll = self.db[SHEET_BRANCHES_COLLECTION]
            await sheet_branches_coll.create_index([("address", ASCENDING)], unique=True, name="sheet_branch_address_unique_idx")
            logfire.info(f"Index 'sheet_branch_address_unique_idx' ensured for collection '{SHEET_BRANCHES_COLLECTION}'.")

            sheet_config_coll = self.db[SHEET_CONFIG_COLLECTION]
            # _id is automatically indexed. If using a specific field like 'config_type' for multiple configs:
            await sheet_config_coll.create_index([("config_type", ASCENDING)], unique=True, name="sheet_config_type_unique_idx", sparse=True)
            logfire.info(f"Index 'sheet_config_type_unique_idx' (sparse) ensured for collection '{SHEET_CONFIG_COLLECTION}'.")

            # Indexes for Bland Call Logs
            bland_logs_coll = self.db[BLAND_CALL_LOGS_COLLECTION]
            # HubSpot Contact ID will be stored as _id, which is automatically indexed and unique.
            # We ensure 'id' field (which will be the HubSpot Contact ID) is used for _id upon insertion.
            await bland_logs_coll.create_index([("status", ASCENDING)], name="bland_call_log_status_idx")
            await bland_logs_coll.create_index([("created_at", DESCENDING)], name="bland_call_log_created_at_idx")
            await bland_logs_coll.create_index([("phone_number", ASCENDING)], name="bland_call_log_phone_idx", sparse=True) # If searching by phone
            await bland_logs_coll.create_index([("call_id_bland", ASCENDING)], name="bland_call_log_bland_call_id_idx", sparse=True) # If searching by Bland's call_id
            logfire.info(f"Indexes ensured for collection '{BLAND_CALL_LOGS_COLLECTION}'.")

            # Indexes for Error Logs
            error_logs_coll = self.db[ERROR_LOGS_COLLECTION]
            await error_logs_coll.create_index([("timestamp", DESCENDING)], name="error_log_timestamp_idx")
            await error_logs_coll.create_index([("service_name", ASCENDING)], name="error_log_service_name_idx")
            await error_logs_coll.create_index([("error_type", ASCENDING)], name="error_log_error_type_idx")
            logfire.info(f"Indexes ensured for collection '{ERROR_LOGS_COLLECTION}'.")

        except Exception as e:
            logfire.error(f"Error creating MongoDB indexes: {e}", exc_info=True)

    # --- Sheet Sync Specific Methods ---

    async def replace_sheet_collection_data(self, collection_name: str, data: List[Dict[str, Any]], id_field: str):
        """
        Replaces all data in the specified collection with the new data from the sheet.
        Uses the value of `id_field` from each item in `data` as the `_id` in MongoDB.
        The entire item (including all its original fields) is stored in the document.
        Documents existing in MongoDB but not in the new `data` (based on `id_field`) are removed.
        """
        collection = self.db[collection_name]
        logfire_extra_data = {"collection_name": collection_name, "id_field": id_field, "item_count": len(data)}

        if not data:
            logfire.info(f"SheetSync: Empty data provided for {collection_name}. Deleting all existing documents.", **logfire_extra_data)
            try:
                delete_result = await collection.delete_many({})
                logfire.info(f"SheetSync: Deleted {delete_result.deleted_count} documents from {collection_name} due to empty sheet data.", **logfire_extra_data)
            except Exception as e:
                logfire.error(f"SheetSync: Error deleting documents from {collection_name} for empty data: {e}", exc_info=True, **logfire_extra_data)
            return

        operations = []
        current_ids_in_sheet_data = set()

        for item in data:
            item_id_value = item.get(id_field)

            if item_id_value is None:
                logfire.warning(f"SheetSync: Item in {collection_name} is missing id_field '{id_field}'. Skipping item: {item}", **logfire_extra_data)
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
                    {"_id": item_id_value},  # Filter by _id (which is the sheet's id_field value)
                    {"$set": document_to_set}, # Set all fields from the item
                    upsert=True
                )
            )
        
        if operations:
            logfire.info(f"SheetSync: Performing {len(operations)} bulk upsert operations on {collection_name} using '{id_field}' as _id source.", **logfire_extra_data)
            if operations: # Log sample for debugging
                 # Correctly access filter (q) and update (u) from the UpdateOne's document
                 sample_op_doc = operations[0]._doc
                 logfire.debug(f"SheetSync: Sample operation for {collection_name}: Filter={{'_id': {sample_op_doc.get('q', {}).get('_id')}}}, Update={{'$set': {sample_op_doc.get('u', {}).get('$set')}}}", **logfire_extra_data)
            try:
                result = await collection.bulk_write(operations, ordered=False)
                logfire.info(f"SheetSync: Bulk write to {collection_name} completed. Upserted: {result.upserted_count}, Modified: {result.modified_count}, Matched: {result.matched_count}.", **logfire_extra_data)
            except Exception as e:
                logfire.error(f"SheetSync: Error during bulk write for {collection_name}: {e}", exc_info=True, **logfire_extra_data)
                # Depending on requirements, you might want to raise e or handle it further
        else:
            logfire.info(f"SheetSync: No valid operations to perform for {collection_name} (e.g., all items lacked id_field or data was empty after filtering).", **logfire_extra_data)

        # After upserting, delete any documents that were not in the new data list.
        # This ensures the collection is an exact mirror of the 'data' list from the sheet.
        if current_ids_in_sheet_data: # Only delete if there was some valid new data
            delete_filter = {"_id": {"$nin": list(current_ids_in_sheet_data)}}
            try:
                delete_result = await collection.delete_many(delete_filter)
                if delete_result.deleted_count > 0:
                    logfire.info(f"SheetSync: Deleted {delete_result.deleted_count} documents from {collection_name} that are no longer in the sheet data.", **logfire_extra_data)
            except Exception as e:
                logfire.error(f"SheetSync: Error deleting old documents from {collection_name}: {e}", exc_info=True, **logfire_extra_data)
        elif not operations and data: # New data was present, but no operations were made (e.g. all items lacked id_field)
             logfire.warning(f"SheetSync: No documents were upserted for {collection_name}, and therefore no old documents were deleted. The collection might be stale if it previously had data.", **logfire_extra_data)

    async def upsert_sheet_config_document(self, document_id: str, config_data: Dict[str, Any], config_type: Optional[str] = None) -> Dict[str, Any]:
        """Upserts a single configuration document in the SHEET_CONFIG_COLLECTION."""
        db = await self.get_db()
        collection = db[SHEET_CONFIG_COLLECTION]
        
        # The document to be upserted. We'll use the provided document_id as MongoDB's _id.
        payload_to_set = {**config_data, "last_updated_mongo": datetime.utcnow()}
        if config_type:
            payload_to_set["config_type"] = config_type
            
        query = {"_id": document_id} # Query by the custom _id
        update_doc = {"$set": payload_to_set}
        
        try:
            update_result = await collection.update_one(query, update_doc, upsert=True)
            upserted_id_str = None
            if update_result.upserted_id is not None:
                upserted_id_str = str(update_result.upserted_id)
            elif update_result.matched_count > 0 : # If matched, the ID was the document_id
                upserted_id_str = document_id

            logfire.info(f"Upserted document with _id '{document_id}' in MongoDB collection '{SHEET_CONFIG_COLLECTION}'. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}, UpsertedId: {upserted_id_str}")
            return {
                "matched_count": update_result.matched_count,
                "modified_count": update_result.modified_count,
                "upserted_id": upserted_id_str,
                "success": True
            }
        except Exception as e:
            logfire.error(f"Failed to upsert document with _id '{document_id}' in MongoDB collection '{SHEET_CONFIG_COLLECTION}': {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # --- Dashboard Specific Methods ---

    async def log_report(self, report_type: str, data: Dict[str, Any], success: bool, error_message: Optional[str] = None):
        """Logs a report document to the reports collection."""
        db = await self.get_db()
        collection = db[REPORTS_COLLECTION]
        report_doc = {
            "timestamp": datetime.utcnow(),
            "report_type": report_type,
            "success": success,
            "data": data,
            "error_message": error_message
        }
        try:
            result = await collection.insert_one(report_doc)
            logfire.debug(f"Logged report '{report_type}' to MongoDB with id: {result.inserted_id}")
            return result.inserted_id
        except Exception as e:
            logfire.error(f"Failed to log report '{report_type}' to MongoDB: {e}", exc_info=True)
            return None

    async def get_recent_reports(self, report_type: Optional[Union[str, List[str]]] = None, limit: int = 100) -> List[Dict[str, Any]]:
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
            logfire.error(f"Failed to retrieve reports from MongoDB: {e}", exc_info=True)
            return []

    async def get_report_summary(self) -> Dict[str, Any]:
        """Provides a summary of report counts by type and success/failure."""
        db = await self.get_db()
        collection = db[REPORTS_COLLECTION]
        summary = {
            "total_reports": 0,
            "success_count": 0,
            "failure_count": 0,
            "by_type": {}
        }
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": {"type": "$report_type", "success": "$success"},
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$group": {
                        "_id": "$_id.type",
                        "counts": {
                            "$push": {"k": {"$cond": ["$_id.success", "success", "failure"]}, "v": "$count"}
                        },
                        "total": {"$sum": "$count"}
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "type": "$_id",
                        "total": "$total",
                        "status_counts": {"$arrayToObject": "$counts"}
                    }
                }
            ]
            results = await collection.aggregate(pipeline).to_list(length=None)
            
            total_reports = 0
            total_success = 0
            total_failure = 0
            by_type_summary = {}

            for item in results:
                report_type = item.get('type')
                type_total = item.get('total', 0)
                type_success = item.get('status_counts', {}).get('success', 0)
                type_failure = item.get('status_counts', {}).get('failure', 0)
                
                total_reports += type_total
                total_success += type_success
                total_failure += type_failure
                
                by_type_summary[report_type] = {
                    "total": type_total,
                    "success": type_success,
                    "failure": type_failure
                }

            summary["total_reports"] = total_reports
            summary["success_count"] = total_success
            summary["failure_count"] = total_failure
            summary["by_type"] = by_type_summary
            
            return summary

        except Exception as e:
            logfire.error(f"Failed to aggregate report summary from MongoDB: {e}", exc_info=True)
            return summary # Return default summary on error

    # --- Bland Call Log Specific Methods ---

    async def log_bland_call_attempt(
        self,
        contact_id: str,
        phone_number: str,
        task: Optional[str], # Task description if pathway_id_used is None
        initial_status: BlandCallStatus = BlandCallStatus.PENDING,
        call_id_bland: Optional[str] = None, # Bland's call_id for *this* attempt, if known early
        retry_of_call_id: Optional[str] = None, # Bland's call_id of the *previous* attempt being retried
        retry_reason: Optional[str] = None,
        # New fields for storing call inputs
        voice_id: Optional[int] = None,
        transfer_phone_number: Optional[str] = None,
        webhook_url: Optional[str] = None,
        request_data_variables: Optional[Dict[str, Any]] = None,
        max_duration: Optional[int] = None,
        pathway_id_used: Optional[str] = None
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
            "status": initial_status.value, # Will be PENDING for new, or updated if retry
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
                "retry_count": 0, # Initial attempt
                **doc_fields
            }
            # Ensure status is PENDING for a truly new insert.
            doc_to_insert["status"] = BlandCallStatus.PENDING.value

            result = await collection.insert_one(doc_to_insert)
            logfire.info(f"Logged new Bland call attempt for contact_id: {contact_id}, mongo_id: {result.inserted_id}", contact_id=contact_id)
            return str(result.inserted_id)
        except OperationFailure as e:
            if e.code == 11000: # Duplicate key error for _id, means it's a retry or concurrent attempt
                logfire.warning(f"Bland call log for contact_id: {contact_id} already exists. Updating for retry.", contact_id=contact_id)
                
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
                    "retry_of_call_id": retry_of_call_id, # This is the Bland call_id of the *previous* attempt
                    "call_id_bland": call_id_bland # This is the Bland call_id for *this current* retry attempt, if known now (usually None)
                }
                # Clean None values from $set to avoid overwriting with None if not provided for the retry
                update_set_fields = {k: v for k, v in update_set_fields.items() if v is not None}

                update_data_for_retry = {
                    "$set": update_set_fields,
                    "$inc": {"retry_count": 1}
                }
                
                # If call_id_bland is explicitly None for this retry attempt (e.g. previous one failed before getting it, and this one hasn't got one yet)
                # ensure it's unset rather than keeping an old one.
                if call_id_bland is None and "call_id_bland" not in update_set_fields:
                     if "$unset" not in update_data_for_retry: update_data_for_retry["$unset"] = {}
                     update_data_for_retry["$unset"]["call_id_bland"] = ""


                updated = await self.update_bland_call_log_internal(contact_id, update_data_for_retry)
                return contact_id if updated else None
            
            logfire.error(f"MongoDB operation failure logging Bland call attempt for contact_id {contact_id}: {e}", contact_id=contact_id, exc_info=True)
            return None
        except Exception as e:
            logfire.error(f"Failed to log Bland call attempt for contact_id {contact_id}: {e}", contact_id=contact_id, exc_info=True)
            return None

    async def update_bland_call_log_internal(self, call_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Internal method to update a BlandCallLog document by call_id.
        Uses $set operator for updates. Ensures 'updated_at' is always updated.
        """
        logger.debug(f"Attempting to update bland_call_log for call_id: {call_id} with data: {update_data}")
        if not self.db or self.bland_call_logs_collection is None:
            logger.error("Database or bland_call_logs_collection not initialized.")
            return False

        # Ensure 'updated_at' is always part of the update
        update_data_copy = copy.deepcopy(update_data)
        update_data_copy["updated_at"] = datetime.now(timezone.utc)

        try:
            result = await self.bland_call_logs_collection.update_one(
                {"call_id": call_id},
                {"$set": update_data_copy}
            )

            if result.matched_count == 0:
                logger.warning(f"No document found with call_id: {call_id} to update.")
                return False
            if result.modified_count == 0 and result.matched_count > 0:
                logger.info(f"Document with call_id: {call_id} found but no fields were modified by the update data: {update_data_copy}")
                # Still return True as the operation to find and "update" (even if to same values) was successful
                return True
            
            logger.info(f"Successfully updated bland_call_log for call_id: {call_id}. Matched: {result.matched_count}, Modified: {result.modified_count}")
            return True
        except OperationFailure as e:
            logger.error(f"MongoDB OperationFailure while updating bland_call_log for call_id {call_id}: {e.details}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"An unexpected error occurred while updating bland_call_log for call_id {call_id}: {e}", exc_info=True)
            return False

    async def update_bland_call_completion(
        self,
        contact_id: str,
        status: BlandCallStatus,
        summary: Optional[str] = None,
        transcript: Optional[str] = None,
        full_response_bland: Optional[Dict[str, Any]] = None, # This is the correct variable name
        error_message: Optional[str] = None,
        call_id_bland: Optional[str] = None 
    ) -> bool:
        """Updates a Bland call log upon completion or failure, using HubSpot Contact ID."""
        update_payload = {
            "status": status.value,
            "updated_at": datetime.utcnow(),
        }

        if call_id_bland: # If a specific bland_call_id is passed (e.g. from initial attempt if not set before)
            update_payload["call_id_bland"] = call_id_bland
        
        if full_response_bland:
            update_payload["call_id_bland"] = full_response_bland.get("call_id", call_id_bland) # Prioritize from full_response_bland
            update_payload["summary"] = full_response_bland.get("summary")
            update_payload["transcript"] = full_response_bland.get("transcript") or full_response_bland.get("concatenated_transcript")
            update_payload["full_response_bland"] = full_response_bland
        
        # Use provided summary/transcript if full_response_bland doesn't contain them or is not provided
        if summary is not None and "summary" not in update_payload:
            update_payload["summary"] = summary
        if transcript is not None and "transcript" not in update_payload:
            update_payload["transcript"] = transcript

        if error_message:
            update_payload["error_message"] = error_message
        
        # Remove None values to avoid overwriting existing fields with None, unless explicitly set to None (e.g. clearing an error)
        # For this function, we generally want to set fields if they are provided.
        # If a field in full_response_bland is None, it will be set to None in DB. This is usually desired.
        # The initial construction of update_payload handles this.

        return await self.update_bland_call_log_internal(contact_id, {"$set": update_payload})


    async def get_bland_call_log(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a Bland.ai call log by its HubSpot Contact ID (_id)."""
        db = await self.get_db()
        collection = db[BLAND_CALL_LOGS_COLLECTION]
        try:
            log_doc = await collection.find_one({"_id": contact_id})
            return log_doc # _id is already the contact_id (string)
        except Exception as e:
            logfire.error(f"Failed to retrieve Bland call log for contact_id {contact_id}: {e}", contact_id=contact_id, exc_info=True)
            return None

    async def get_bland_calls(
        self, 
        page: int = 1, 
        page_size: int = 10, 
        status_filter: Optional[str] = None, # Renamed from status to status_filter
        sort_field: str = "created_at", 
        sort_order: int = DESCENDING
    ) -> Tuple[List[Dict[str, Any]], int]: # Corrected return type annotation
        """Retrieves a paginated list of Bland.ai call logs."""
        db = await self.get_db()
        collection = db[BLAND_CALL_LOGS_COLLECTION]
        query = {}
        if status_filter:
            query["status"] = status_filter
        
        try:
            total_items = await collection.count_documents(query)
            skip = (page - 1) * page_size
            cursor = collection.find(query).sort(sort_field, sort_order).skip(skip).limit(page_size)
            items = await cursor.to_list(length=page_size)
            # _id is already a string (HubSpot Contact ID), so no conversion needed for _id.
            return items, total_items
        except Exception as e:
            logfire.error(f"Failed to retrieve Bland calls: {e}", query=query, exc_info=True)
            return [], 0

    async def get_bland_call_stats(self) -> Dict[str, Any]:
        """Counts Bland.ai calls, categorized by status, and includes a total."""
        db = await self.get_db()
        collection = db[BLAND_CALL_LOGS_COLLECTION]
        
        all_statuses = [status.value for status in BlandCallStatus]
        
        pipeline = [
            {
                "$group": {
                    "_id": "$status",
                    "count": {"$sum": 1}
                }
            }
        ]
        
        # Initialize stats with all statuses from the enum, ensuring all are present
        stats = {status_val: 0 for status_val in all_statuses}
        total_calls = 0
        
        try:
            cursor = collection.aggregate(pipeline)
            async for doc in cursor:
                status_val = doc["_id"]
                count = doc["count"]
                if status_val in stats: # Should always be true if status in DB is valid
                    stats[status_val] = count
                total_calls += count
            
            stats["total_calls"] = total_calls
            return stats
        except Exception as e:
            logfire.error(f"Failed to retrieve Bland call stats: {e}", exc_info=True)
            # Return stats with 0 counts in case of error, including total
            # Ensure all enum statuses are present with 0 count
            error_stats = {status_val: 0 for status_val in all_statuses}
            error_stats["total_calls"] = 0
            return error_stats

    # --- General Error Log Specific Methods ---

    async def log_error_to_db(
        self,
        service_name: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Logs a general error to the error_logs collection."""
        db = await self.get_db()
        collection = db[ERROR_LOGS_COLLECTION]
        
        error_log_entry = ErrorLog(
            service_name=service_name,
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace,
            request_context=request_context,
            additional_data=additional_data
        )
        
        try:
            error_doc = error_log_entry.model_dump(by_alias=True)
            
            result = await collection.insert_one(error_doc)
            logfire.info(f"Logged general error from service '{service_name}' to MongoDB with id: {result.inserted_id}", error_id=str(result.inserted_id))
            return str(result.inserted_id)
        except Exception as e:
            logfire.error(f"Failed to log general error from service '{service_name}' to MongoDB: {e}", exc_info=True)
            return None

    async def get_error_logs(
        self,
        page: int = 1,
        page_size: int = 10,
        service_name_filter: Optional[str] = None,
        error_type_filter: Optional[str] = None,
        sort_field: str = "timestamp",
        sort_order: int = DESCENDING # PyMongo constant
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Retrieves a paginated list of error logs, with optional filtering and sorting."""
        db = await self.get_db()
        collection = db[ERROR_LOGS_COLLECTION]
        query = {}
        if service_name_filter:
            query["service_name"] = service_name_filter
        if error_type_filter:
            query["error_type"] = error_type_filter

        skip = (page - 1) * page_size
        
        try:
            cursor = collection.find(query).sort(sort_field, sort_order).skip(skip).limit(page_size)
            items = await cursor.to_list(length=page_size)
            total_items = await collection.count_documents(query)
            return items, total_items
        except Exception as e:
            logfire.error(f"Failed to retrieve error logs from MongoDB: {e}", exc_info=True)
            return [], 0

# --- Lifespan Integration Functions ---

mongo_service_instance: Optional[MongoService] = None

async def startup_mongo_service() -> Optional[MongoService]:
    """Creates MongoService instance, connects, initializes indexes."""
    global mongo_service_instance
    if mongo_service_instance is not None:
        logfire.info("MongoService already initialized.")
        return mongo_service_instance

    logfire.info("Starting MongoDB service initialization...")
    instance = MongoService()
    try:
        await instance.connect_and_initialize() # Connects and creates indexes
        mongo_service_instance = instance # Store instance only on success
        logfire.info("MongoDB service initialization successful.")
        return mongo_service_instance
    except Exception as e:
        logfire.error(f"Failed during MongoDB startup sequence: {e}", exc_info=True)
        mongo_service_instance = None # Ensure it's None on failure
        return None # Indicate failure

async def shutdown_mongo_service():
    """Closes the MongoDB connection if the service was initialized."""
    global mongo_service_instance
    if mongo_service_instance:
        logfire.info("Shutting down MongoDB service...")
        await mongo_service_instance.close_mongo_connection()
        mongo_service_instance = None
    else:
        logfire.info("MongoDB service was not initialized, skipping shutdown.")

# Dependency injector using the singleton instance
async def get_mongo_service() -> MongoService:
    """Dependency injector to get the initialized MongoService instance."""
    if mongo_service_instance is None or mongo_service_instance.db is None:
        logfire.error("MongoDB service requested but not available or not connected.")
        raise RuntimeError("MongoDB service is not available.")
    return mongo_service_instance
