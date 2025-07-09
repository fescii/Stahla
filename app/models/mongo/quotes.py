# filepath: app/models/mongo/quotes.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class QuoteStatus(str, Enum):
  """Status of quote generation."""
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"
  EXPIRED = "expired"


class QuoteDocument(BaseModel):
  """MongoDB document model for quotes collection."""

  id: str = Field(...,
                  description="Unique quote identifier, used as _id in MongoDB")
  request_id: Optional[str] = Field(
      None, description="Original request ID from quote generation")
  contact_id: Optional[str] = Field(
      None, description="HubSpot contact ID if available")
  lead_id: Optional[str] = Field(
      None, description="HubSpot lead ID if available")

  # Quote details
  quote_data: Optional[Dict[str, Any]] = Field(
      None, description="Complete quote response data")
  total_amount: Optional[float] = Field(
      None, description="Total quote amount for querying purposes")
  subtotal: Optional[float] = Field(
      None, description="Subtotal before taxes and final adjustments")
  delivery_cost: Optional[float] = Field(
      None, description="Delivery cost component")
  rental_cost: Optional[float] = Field(
      None, description="Rental cost component")

  # Request details
  request_data: Optional[Dict[str, Any]] = Field(
      None, description="Original quote request data")
  delivery_location: Optional[str] = Field(
      None, description="Delivery address for the quote")
  rental_duration_days: Optional[int] = Field(
      None, description="Rental duration in days")
  product_type: Optional[str] = Field(
      None, description="Primary product type quoted")
  stall_count: Optional[int] = Field(
      None, description="Number of stalls/units quoted")

  # Status and metadata
  status: QuoteStatus = Field(
      QuoteStatus.PENDING, description="Current status of the quote")
  error_message: Optional[str] = Field(
      None, description="Error message if quote generation failed")
  processing_time_ms: Optional[int] = Field(
      None, description="Processing time in milliseconds")

  # Validation and expiry
  valid_until: Optional[datetime] = Field(
      None, description="Quote expiration date")
  is_expired: bool = Field(False, description="Whether the quote has expired")

  # Background task tracking
  background_task_id: Optional[str] = Field(
      None, description="ID of background task that generated this quote")

  # Timestamps
  created_at: datetime = Field(
      default_factory=datetime.utcnow, description="Creation timestamp")
  updated_at: datetime = Field(
      default_factory=datetime.utcnow, description="Last update timestamp")

  class Config:
    json_schema_extra = {
        "example": {
            "id": "QT-uuid-123",
            "request_id": "req_abc123",
            "contact_id": "hubspot_contact_123",
            "quote_data": {
                "line_items": [],
                "subtotal": 2500.00,
                "total": 2750.00
            },
            "total_amount": 2750.00,
            "subtotal": 2500.00,
            "delivery_cost": 200.00,
            "rental_cost": 2300.00,
            "request_data": {
                "delivery_location": "123 Main St, City, ST 12345",
                "rental_days": 7,
                "product_type": "restroom_trailer"
            },
            "delivery_location": "123 Main St, City, ST 12345",
            "rental_duration_days": 7,
            "product_type": "restroom_trailer",
            "stall_count": 3,
            "status": "completed",
            "processing_time_ms": 450,
            "valid_until": "2025-07-23T14:32:10.123456",
            "is_expired": False
        }
    }
