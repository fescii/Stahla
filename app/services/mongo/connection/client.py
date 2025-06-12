# filepath: app/services/mongo/connection/client.py
import logfire
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, OperationFailure
from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation
from app.core.config import settings
from typing import Optional


class MongoConnection:
  """Handles MongoDB connection and database access."""

  def __init__(self):
    self.client: Optional[AsyncIOMotorClient] = None
    self.db: Optional[AsyncIOMotorDatabase] = None
    logfire.info(
        "MongoConnection instance created. Connection will be established.")

  async def connect_and_initialize(self):
    """Connects to MongoDB and performs initial setup."""
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
          serverSelectionTimeoutMS=3000,
          connectTimeoutMS=2000,
          socketTimeoutMS=2000,
          uuidRepresentation="standard",
      )

      # Test connection
      await self.client.admin.command("ismaster")

      # Get database with codec options
      self.db = self.client.get_database(
          settings.MONGO_DB_NAME, codec_options=codec_options
      )

      logfire.info(
          f"Successfully connected to MongoDB. Database: '{settings.MONGO_DB_NAME}'"
      )
    except (ConnectionFailure, OperationFailure) as e:
      logfire.error(
          f"Failed to connect to MongoDB or authentication failed: {e}"
      )
      self.client = None
      self.db = None
      raise
    except Exception as e:
      logfire.error(
          f"An unexpected error occurred during MongoDB connection: {e}",
          exc_info=True,
      )
      self.client = None
      self.db = None
      raise

  async def close_connection(self):
    """Closes MongoDB connection."""
    logfire.info("Closing MongoDB connection...")
    if self.client:
      self.client.close()
      self.client = None
      self.db = None
      logfire.info("MongoDB connection closed.")

  async def get_db(self) -> AsyncIOMotorDatabase:
    """Returns the database instance."""
    if self.db is None:
      logfire.error("MongoDB database is not initialized.")
      raise RuntimeError("Database connection is not available.")
    return self.db

  async def check_connection(self) -> str:
    """Checks the MongoDB connection by pinging the database."""
    logfire.debug("Attempting MongoDB connection check...")
    if self.db is None:
      logfire.warn(
          "MongoDB connection check: Database instance (self.db) is None."
      )
      return "error: MongoDB database not initialized internally."
    try:
      await self.db.command("ping")
      logfire.info("MongoDB connection check successful (ping).")
      return "ok"
    except (ConnectionFailure, OperationFailure) as e:
      logfire.error(
          f"MongoDB connection check failed (ping operation failed): {str(e)}",
          exc_info=True,
      )
      return f"error: Ping failed - {str(e)}"
    except Exception as e:
      logfire.error(
          f"MongoDB connection check failed with an unexpected exception: {str(e)}",
          exc_info=True,
      )
      return f"error: Unexpected exception - {str(e)}"
