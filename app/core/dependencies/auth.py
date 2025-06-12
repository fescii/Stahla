"""
Core dependency injection module for authentication services.
"""

from fastapi import Depends
from app.services.mongo.dependency import MongoService, get_mongo_service
from app.services.auth.auth import AuthService, get_auth_service


def get_auth_service_dep(
    mongo_service: MongoService = Depends(get_mongo_service)
) -> AuthService:
  """
  Get AuthService instance.
  """
  return AuthService(mongo_service)
