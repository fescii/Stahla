"""
Core dependency injection module for MongoDB services.
"""

from fastapi import Depends
from app.services.mongo.dependency import MongoService, get_mongo_service


async def get_mongo_service_dep() -> MongoService:
  """
  Get MongoService instance.
  """
  return await get_mongo_service()
