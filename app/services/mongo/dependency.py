# filepath: app/services/mongo/dependency.py
import logfire
from typing import Optional
from fastapi import HTTPException
from .service import MongoService

# Global instance
mongo_service_instance: Optional[MongoService] = None


async def startup_mongo_service():
  """Startup function for MongoDB service."""
  global mongo_service_instance
  logfire.info("Attempting to start up MongoDB service...")
  if mongo_service_instance is None:
    mongo_service_instance = MongoService()
    try:
      await mongo_service_instance.connect_and_initialize()
      logfire.info("MongoDB service started and initialized successfully.")
    except Exception as e:
      logfire.error(f"MongoDB service startup failed: {e}", exc_info=True)
      mongo_service_instance = None
  else:
    logfire.info("MongoDB service already started.")


async def shutdown_mongo_service():
  """Shutdown function for MongoDB service."""
  global mongo_service_instance
  if mongo_service_instance:
    logfire.info("Attempting to shut down MongoDB service...")
    await mongo_service_instance.close_mongo_connection()
    mongo_service_instance = None


async def get_mongo_service() -> MongoService:
  """
  FastAPI dependency injector for MongoService.
  Returns the initialized mongo_service_instance.
  Raises HTTPException if the service is not available.
  """
  global mongo_service_instance
  if mongo_service_instance is None:
    logfire.error(
        "get_mongo_service: mongo_service_instance is None. MongoDB might not have started correctly."
    )
    logfire.info(
        "get_mongo_service: Attempting to initialize mongo_service_instance as it was None."
    )
    await startup_mongo_service()
    if mongo_service_instance is None:
      raise HTTPException(
          status_code=503,
          detail="MongoDB service is not available. Initialization may have failed.",
      )
  return mongo_service_instance
