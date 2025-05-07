\
# filepath: app/services/mongo/mongo.py
import logfire
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from app.core.config import settings
from typing import Optional, Dict, Any, List
from datetime import datetime

# Define collection names
REPORTS_COLLECTION = "reports"

class MongoService:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None

    async def connect_to_mongo(self):
        logfire.info("Connecting to MongoDB...")
        if not settings.MONGO_CONNECTION_URL:
            logfire.error("MONGO_CONNECTION_URL not set in environment/settings.")
            raise ValueError("MongoDB connection URL is not configured.")
            
        self.client = AsyncIOMotorClient(settings.MONGO_CONNECTION_URL)
        try:
            # The ismaster command is cheap and does not require auth.
            await self.client.admin.command('ismaster')
            self.db = self.client[settings.MONGO_DB_NAME]
            logfire.info(f"Successfully connected to MongoDB. Database: '{settings.MONGO_DB_NAME}'")
            # TODO: Consider creating indexes here if needed
            # await self.create_indexes()
        except ConnectionFailure as e:
            logfire.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
            raise
        except OperationFailure as e:
            logfire.error(f"MongoDB authentication failed or operation failure during connection check: {e}")
            # This might happen if the app user/pass is wrong or DB doesn't exist and user can't create
            self.client = None
            self.db = None
            raise

    async def close_mongo_connection(self):
        logfire.info("Closing MongoDB connection...")
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            logfire.info("MongoDB connection closed.")

    async def get_db(self) -> AsyncIOMotorDatabase:
        if not self.db:
            logfire.error("MongoDB database is not initialized. Call connect_to_mongo first.")
            # Depending on strategy, could try to reconnect here, but safer to raise
            raise RuntimeError("Database connection is not available.")
        return self.db

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

# Singleton instance
mongo_service = MongoService()

# Dependency injector
async def get_mongo_service() -> MongoService:
    # This assumes connect_to_mongo is called during lifespan startup
    if not mongo_service.db:
        # Attempt to reconnect or handle error appropriately
        # For simplicity, we raise an error here, assuming lifespan handles connection.
        logfire.critical("MongoDB connection requested but not available.")
        raise RuntimeError("MongoDB connection is not available.")
    return mongo_service
