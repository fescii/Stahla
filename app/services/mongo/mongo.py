# filepath: app/services/mongo/mongo.py
import logfire
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from pymongo.server_api import ServerApi # Import ServerApi
from bson.codec_options import CodecOptions, UuidRepresentation # Import UuidRepresentation
from app.core.config import settings
from typing import Optional, Dict, Any, List
from datetime import datetime
from pymongo import ASCENDING, DESCENDING # Import for indexes

# Define collection names
REPORTS_COLLECTION = "reports"
USERS_COLLECTION = "users" # Define users collection name here

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
        # Correct the check to use 'is None'
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
            
            # Add other index creations here

        except Exception as e:
            logfire.error(f"Error creating MongoDB indexes: {e}", exc_info=True)

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

    async def get_recent_reports(self, report_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves recent reports, optionally filtered by type."""
        db = await self.get_db()
        collection = db[REPORTS_COLLECTION]
        query = {}
        if report_type:
            query["report_type"] = report_type
        
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
