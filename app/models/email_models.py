# app/models/email_models.py

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any

class EmailAttachment(BaseModel):
    """Represents an email attachment."""
    filename: Optional[str] = None
    content_type: Optional[str] = Field(None, alias="contentType")
    size: Optional[int] = None
    # Content might be base64 encoded string or a URL depending on the source
    content: Optional[str] = None # Or bytes, or HttpUrl

class EmailWebhookPayload(BaseModel):
    """
    Structure of the webhook payload received for an incoming email.
    This structure is hypothetical and depends heavily on the service
    that forwards the email content (e.g., SendGrid Inbound Parse,
    Mailgun Routes, AWS SES+Lambda, custom SMTP listener).
    Adjust fields based on the actual service used.
    """
    message_id: Optional[str] = Field(None, alias="messageId", description="Unique ID of the email message.")
    from_email: Optional[EmailStr] = Field(None, alias="from")
    to_emails: Optional[List[EmailStr]] = Field(None, alias="to")
    cc_emails: Optional[List[EmailStr]] = Field(None, alias="cc")
    subject: Optional[str] = None
    body_text: Optional[str] = Field(None, alias="bodyText", description="Plain text body of the email.")
    body_html: Optional[str] = Field(None, alias="bodyHtml", description="HTML body of the email.")
    headers: Optional[Dict[str, str]] = Field(None, description="Email headers.")
    attachments: Optional[List[EmailAttachment]] = Field(default_factory=list)
    received_at: Optional[str] = Field(None, alias="receivedAt", description="Timestamp when the email was received.")
    # Add any other relevant fields provided by the email webhook service

    class Config:
        extra = 'allow' # Allow extra fields

class EmailProcessingResult(BaseModel):
    """Result structure for email processing operations."""
    status: str # e.g., "success", "error", "auto_reply_sent"
    message: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    classification_pending: bool = False
    details: Optional[Any] = None # For detailed results or errors
    message_id: Optional[str] = None # Include message ID where relevant

"""
**Instructions:**
1.  Create a file named `email_models.py` inside the `app/models/` directory.
2.  Paste this code into it.
3.  **Crucially:** You **must** adapt the `EmailWebhookPayload` model to match the actual data structure provided by the service that sends email webhooks to your application. 
  The fields here are common examples but will vary based on the service used (e.g., SendGrid, Mailgun, AWS SES).
4.  Ensure you have the necessary dependencies installed for Pydantic and FastAPI.
5.  Use this model in your email processing service to validate incoming webhook data.
6.  Implement the logic to parse the email, check for missing fields, and trigger auto-replies as needed.
7.  Integrate this model with your classification engine as necessary.
8.  Test the webhook endpoint with sample payloads to ensure it works as expected.
9.  Update your API documentation to reflect the new email processing capabilities.
10.  Consider adding unit tests for the email processing logic to ensure robustness and reliability.
"""