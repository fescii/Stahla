# filepath: app/models/mongo/classify.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class ClassifyStatus(str, Enum):
  """Status of classification processing."""
  PENDING = "pending"
  PROCESSING = "processing"
  COMPLETED = "completed"
  FAILED = "failed"
  REQUIRES_REVIEW = "requires_review"
  DISQUALIFIED = "disqualified"
  SERVICES = "services"
  LOGISTICS = "logistics"
  LEADS = "leads"


class ClassifyDocument(BaseModel):
  """MongoDB document model for classification results."""

  id: str = Field(..., description="Unique classification identifier, used as _id in MongoDB")
  contact_id: Optional[str] = Field(None, description="HubSpot contact ID")
  lead_id: Optional[str] = Field(
      None, description="HubSpot lead ID if available")

  # Source information
  source: str = Field(...,
                      description="Classification source: webform, voice, email")
  raw_data: Optional[Dict[str, Any]] = Field(
      None, description="Raw input data for classification")
  extracted_data: Optional[Dict[str, Any]] = Field(
      None, description="Extracted/processed data")

  # Classification input
  classification_input: Optional[Dict[str, Any]] = Field(
      None, description="Complete classification input data")

  # Classification results
  lead_type: Optional[str] = Field(
      None, description="Classified lead type: Services, Logistics, Leads, Disqualify")
  classification_result: Optional[str] = Field(
      None, description="Final classification result")
  confidence: Optional[float] = Field(
      None, description="Classification confidence score (0.0-1.0)")
  reasoning: Optional[str] = Field(
      None, description="Reasoning for the classification")
  routing_suggestion: Optional[str] = Field(
      None, description="Suggested routing/team")

  # Status and processing
  status: ClassifyStatus = Field(
      ClassifyStatus.PENDING, description="Current classification status")
  processing_method: Optional[str] = Field(
      None, description="Method used: rules, marvin, hybrid")
  requires_human_review: bool = Field(
      False, description="Whether human review is required")

  # Extracted details
  intended_use: Optional[str] = Field(
      None, description="Intended use: Small Event, Large Event, Construction, etc.")
  product_interest: Optional[List[str]] = Field(
      default_factory=list, description="List of products of interest")
  is_local: Optional[bool] = Field(
      None, description="Whether location is local (within service area)")
  is_in_service_area: Optional[bool] = Field(
      None, description="Whether in defined service area")

  # Event/project details
  event_type: Optional[str] = Field(
      None, description="Type of event or project")
  location: Optional[str] = Field(None, description="Event/project location")
  duration_days: Optional[int] = Field(None, description="Duration in days")
  stall_count: Optional[int] = Field(
      None, description="Number of stalls/units needed")
  guest_count: Optional[int] = Field(
      None, description="Expected attendance/guests")

  # Contact information
  contact_name: Optional[str] = Field(None, description="Contact person name")
  contact_email: Optional[str] = Field(None, description="Contact email")
  contact_phone: Optional[str] = Field(None, description="Contact phone")
  company_name: Optional[str] = Field(None, description="Company name")

  # Additional metadata
  metadata: Optional[Dict[str, Any]] = Field(
      default_factory=dict, description="Additional classification metadata")

  # Error handling
  error_message: Optional[str] = Field(
      None, description="Error message if classification failed")

  # Background task tracking
  background_task_id: Optional[str] = Field(
      None, description="ID of background task that processed this classification")

  # Follow-up actions
  hubspot_updated: bool = Field(
      False, description="Whether HubSpot was updated with results")
  n8n_triggered: bool = Field(
      False, description="Whether n8n automation was triggered")

  # Timestamps
  classified_at: Optional[datetime] = Field(
      None, description="When classification was completed")
  created_at: datetime = Field(
      default_factory=datetime.utcnow, description="Creation timestamp")
  updated_at: datetime = Field(
      default_factory=datetime.utcnow, description="Last update timestamp")

  class Config:
    json_schema_extra = {
        "example": {
            "id": "classify_uuid_123",
            "contact_id": "hubspot_contact_123",
            "source": "voice",
            "raw_data": {
                "transcript": "Customer needs restroom trailer for wedding..."
            },
            "lead_type": "Services",
            "classification_result": "Services",
            "confidence": 0.95,
            "reasoning": "Small event, trailer rental, local delivery",
            "routing_suggestion": "Stahla Services Sales Team",
            "status": "completed",
            "processing_method": "marvin",
            "requires_human_review": False,
            "intended_use": "Small Event",
            "product_interest": ["Restroom Trailer"],
            "is_local": True,
            "is_in_service_area": True,
            "event_type": "Wedding",
            "location": "Kansas City, KS",
            "duration_days": 3,
            "stall_count": 2,
            "guest_count": 150,
            "contact_name": "Jane Smith",
            "contact_email": "jane@example.com",
            "contact_phone": "555-1234",
            "hubspot_updated": True,
            "n8n_triggered": True,
            "classified_at": "2025-07-09T10:05:00.000Z"
        }
    }
