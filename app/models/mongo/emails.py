# filepath: app/models/mongo/emails.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class EmailCategory(str, Enum):
  """Category of email operation."""
  SENT = "sent"
  RECEIVED = "received"
  FAILED = "failed"
  QUEUED = "queued"
  PROCESSING = "processing"


class EmailStatus(str, Enum):
  """Status of email processing."""
  PENDING = "pending"
  PROCESSING = "processing"
  SUCCESS = "success"
  FAILED = "failed"
  DELIVERED = "delivered"
  BOUNCED = "bounced"
  REJECTED = "rejected"
  DEFERRED = "deferred"


class EmailDocument(BaseModel):
  """MongoDB document model for email operations."""

  id: str = Field(...,
                  description="Unique email identifier, used as _id in MongoDB")
  contact_id: Optional[str] = Field(
      None, description="HubSpot contact ID if available")
  lead_id: Optional[str] = Field(
      None, description="HubSpot lead ID if available")

  # Email identification
  message_id: Optional[str] = Field(None, description="Email message ID")
  external_id: Optional[str] = Field(
      None, description="External system ID (n8n workflow ID, etc.)")
  thread_id: Optional[str] = Field(
      None, description="Email thread ID for conversations")

  # Email details
  category: EmailCategory = Field(...,
                                  description="Email category: sent, received, failed, etc.")
  status: EmailStatus = Field(
      EmailStatus.PENDING, description="Current email status")
  direction: str = Field(..., description="Email direction: inbound, outbound")

  # Sender and recipient information
  from_email: Optional[EmailStr] = Field(
      None, description="Sender email address")
  from_name: Optional[str] = Field(None, description="Sender name")
  to_emails: Optional[List[EmailStr]] = Field(
      default_factory=list, description="Recipient email addresses")
  cc_emails: Optional[List[EmailStr]] = Field(
      default_factory=list, description="CC email addresses")
  bcc_emails: Optional[List[EmailStr]] = Field(
      default_factory=list, description="BCC email addresses")
  reply_to: Optional[EmailStr] = Field(
      None, description="Reply-to email address")

  # Email content
  subject: Optional[str] = Field(None, description="Email subject line")
  body_text: Optional[str] = Field(None, description="Plain text body")
  body_html: Optional[str] = Field(None, description="HTML body")

  # Attachments
  has_attachments: bool = Field(
      False, description="Whether email has attachments")
  attachment_count: int = Field(0, description="Number of attachments")
  attachments: Optional[List[Dict[str, Any]]] = Field(
      default_factory=list, description="Attachment details")

  # Email headers and metadata
  headers: Optional[Dict[str, str]] = Field(
      default_factory=dict, description="Email headers")
  email_metadata: Optional[Dict[str, Any]] = Field(
      default_factory=dict, description="Additional email metadata")

  # N8N integration
  n8n_workflow_id: Optional[str] = Field(None, description="N8N workflow ID")
  n8n_execution_id: Optional[str] = Field(None, description="N8N execution ID")
  n8n_node_id: Optional[str] = Field(None, description="N8N node ID")
  n8n_webhook_url: Optional[str] = Field(
      None, description="N8N webhook URL used")

  # Processing details
  processing_result: Optional[Dict[str, Any]] = Field(
      None, description="Processing results")
  classification_triggered: bool = Field(
      False, description="Whether classification was triggered")
  auto_reply_sent: bool = Field(
      False, description="Whether auto-reply was sent")

  # Delivery tracking (for sent emails)
  delivery_status: Optional[str] = Field(
      None, description="Delivery status for sent emails")
  delivery_timestamp: Optional[datetime] = Field(
      None, description="When email was delivered")
  open_count: int = Field(0, description="Number of times email was opened")
  click_count: int = Field(0, description="Number of clicks in email")

  # Error handling
  error_message: Optional[str] = Field(
      None, description="Error message if email processing failed")
  error_type: Optional[str] = Field(
      None, description="Type of error encountered")
  retry_count: int = Field(0, description="Number of retry attempts")

  # Background task tracking
  background_task_id: Optional[str] = Field(
      None, description="ID of background task that processed this email")

  # Timestamps
  email_sent_at: Optional[datetime] = Field(
      None, description="When email was sent")
  email_received_at: Optional[datetime] = Field(
      None, description="When email was received")
  processed_at: Optional[datetime] = Field(
      None, description="When email was processed")
  created_at: datetime = Field(
      default_factory=datetime.utcnow, description="Creation timestamp")
  updated_at: datetime = Field(
      default_factory=datetime.utcnow, description="Last update timestamp")

  class Config:
    json_schema_extra = {
        "example": {
            "id": "email_uuid_123",
            "contact_id": "hubspot_contact_123",
            "message_id": "msg_456789",
            "external_id": "n8n_execution_123",
            "category": "sent",
            "status": "delivered",
            "direction": "outbound",
            "from_email": "support@stahla.com",
            "from_name": "Stahla Support",
            "to_emails": ["customer@example.com"],
            "cc_emails": [],
            "subject": "Your Quote Request - Stahla",
            "body_text": "Thank you for your quote request...",
            "body_html": "<html><body>Thank you for your quote request...</body></html>",
            "has_attachments": True,
            "attachment_count": 1,
            "attachments": [
                {
                    "filename": "quote.pdf",
                    "content_type": "application/pdf",
                    "size": 25600
                }
            ],
            "n8n_workflow_id": "workflow_789",
            "n8n_execution_id": "exec_123",
            "delivery_status": "delivered",
            "delivery_timestamp": "2025-07-09T10:05:00.000Z",
            "open_count": 1,
            "click_count": 0,
            "email_sent_at": "2025-07-09T10:00:00.000Z",
            "processed_at": "2025-07-09T10:00:30.000Z"
        }
    }
