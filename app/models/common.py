# filepath: /home/a03/PycharmProjects/Stahla/app/models/common.py
# app/models/common.py

from pydantic import BaseModel
from typing import Dict, Any, Optional, TypeVar, Generic


class HealthCheckResponse(BaseModel):
  """Model for health check response."""
  status: str  # 'ok' or 'error'
  # Detailed information about system resources and dependencies
  details: Dict[str, Any]


# Define a generic response model
T = TypeVar('T')

# Correct inheritance order: BaseModel first, then Generic[T]


class GenericResponse(BaseModel, Generic[T]):
  success: bool = True
  data: Optional[T] = None
  error_message: Optional[str] = None
  error_details: Optional[Any] = None
  status_code: Optional[int] = None  # Added status_code

  @classmethod
  # Added status_code
  def error(cls, message: str, details: Optional[Any] = None, status_code: int = 500):
    return cls(success=False, data=None, error_message=message, error_details=details, status_code=status_code)

# Define MessageResponse model


class MessageResponse(BaseModel):
  message: str


# Define PaginatedResponse model
class PaginatedResponse(BaseModel, Generic[T]):
  items: list[T]
  page: int
  limit: int
  total: int
  has_more: bool

# You can add other common models here if needed
