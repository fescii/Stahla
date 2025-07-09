# filepath: app/services/mongo/emails/operations.py
import logfire
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from app.models.mongo.emails import EmailDocument, EmailCategory, EmailStatus
from app.services.mongo.collections.names import EMAILS_COLLECTION


class EmailsOperations:
  """Handles MongoDB operations for emails collection."""

  def __init__(self, db):
    self.db = db

  async def create_email(self, email_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates a new email document in the emails collection.

    Args:
        email_data: Dictionary containing email data

    Returns:
        Email ID if successful, None otherwise
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      # Create EmailDocument to validate data
      email_doc = EmailDocument(**email_data)

      # Prepare document for insertion
      doc_dict = email_doc.model_dump()
      doc_dict["_id"] = doc_dict.pop("id")  # Use id as _id
      doc_dict["created_at"] = datetime.now(timezone.utc)
      doc_dict["updated_at"] = datetime.now(timezone.utc)

      # Insert the document
      result = await collection.insert_one(doc_dict)

      if result.inserted_id:
        logfire.info(f"Email created successfully",
                     email_id=str(result.inserted_id))
        return str(result.inserted_id)
      else:
        logfire.error("Failed to create email: no ID returned")
        return None

    except Exception as e:
      logfire.error(f"Error creating email: {e}", exc_info=True)
      return None

  async def update_email(self, email_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Updates an existing email document.

    Args:
        email_id: Email ID to update
        update_data: Dictionary containing fields to update

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      # Add updated_at timestamp
      update_data["updated_at"] = datetime.now(timezone.utc)

      # Perform the update
      result = await collection.update_one(
          {"_id": email_id},
          {"$set": update_data}
      )

      if result.matched_count > 0:
        logfire.info(f"Email updated successfully", email_id=email_id)
        return True
      else:
        logfire.warn(f"No email found with ID: {email_id}")
        return False

    except Exception as e:
      logfire.error(f"Error updating email {email_id}: {e}", exc_info=True)
      return False

  async def get_email(self, email_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves an email by ID.

    Args:
        email_id: Email ID to retrieve

    Returns:
        Email document if found, None otherwise
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      doc = await collection.find_one({"_id": email_id})

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved email", email_id=email_id)
        return doc
      else:
        logfire.info(f"Email not found", email_id=email_id)
        return None

    except Exception as e:
      logfire.error(f"Error retrieving email {email_id}: {e}", exc_info=True)
      return None

  async def get_email_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves an email by message ID.

    Args:
        message_id: Email message ID

    Returns:
        Email document if found, None otherwise
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      doc = await collection.find_one({"message_id": message_id})

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved email by message ID",
                      message_id=message_id, email_id=doc["id"])
        return doc
      else:
        logfire.info(f"No email found with message ID", message_id=message_id)
        return None

    except Exception as e:
      logfire.error(
          f"Error retrieving email by message ID {message_id}: {e}", exc_info=True)
      return None

  async def get_emails_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves emails for a specific contact.

    Args:
        contact_id: HubSpot contact ID
        limit: Maximum number of emails to return

    Returns:
        List of email documents
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      cursor = collection.find(
          {"contact_id": contact_id}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} emails for contact", contact_id=contact_id)
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving emails for contact {contact_id}: {e}", exc_info=True)
      return []

  async def get_emails_by_category(self, category: str, offset: int = 0) -> List[EmailDocument]:
    """Gets emails by category with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({"category": category})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting emails by category: {str(e)}")
      return []

  async def get_emails_by_status(self, status: EmailStatus, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves emails by status.

    Args:
        status: Email status to filter by
        limit: Maximum number of emails to return

    Returns:
        List of email documents
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      cursor = collection.find(
          {"status": status.value}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(f"Retrieved {len(docs)} emails with status {status.value}")
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving emails by status {status.value}: {e}", exc_info=True)
      return []

  async def get_emails_by_thread(self, thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves emails in a specific thread.

    Args:
        thread_id: Email thread ID
        limit: Maximum number of emails to return

    Returns:
        List of email documents
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      cursor = collection.find(
          {"thread_id": thread_id}
      ).sort("created_at", 1).limit(limit)  # Ascending order for thread

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} emails in thread", thread_id=thread_id)
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving emails by thread {thread_id}: {e}", exc_info=True)
      return []

  async def get_emails_paginated(
      self,
      page: int = 1,
      page_size: int = 10,
      category_filter: Optional[str] = None,
      status_filter: Optional[str] = None,
      direction_filter: Optional[str] = None,
      sort_field: str = "created_at",
      sort_order: int = -1
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves paginated emails with optional filtering and sorting.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        category_filter: Optional category filter
        status_filter: Optional status filter
        direction_filter: Optional direction filter (inbound/outbound)
        sort_field: Field to sort by
        sort_order: Sort order (1 for ascending, -1 for descending)

    Returns:
        Tuple of (email documents, total count)
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      # Build query
      query = {}
      if category_filter:
        query["category"] = category_filter
      if status_filter:
        query["status"] = status_filter
      if direction_filter:
        query["direction"] = direction_filter

      # Calculate skip
      skip = (page - 1) * page_size

      # Get documents
      cursor = collection.find(query).sort(
          sort_field, sort_order).skip(skip).limit(page_size)
      docs = await cursor.to_list(length=page_size)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      # Get total count
      total_count = await collection.count_documents(query)

      logfire.debug(
          f"Retrieved {len(docs)} emails (page {page}, total {total_count})")
      return docs, total_count

    except Exception as e:
      logfire.error(f"Error retrieving paginated emails: {e}", exc_info=True)
      return [], 0

  async def update_email_status(self, email_id: str, status: EmailStatus, error_message: Optional[str] = None) -> bool:
    """
    Updates an email's status.

    Args:
        email_id: Email ID to update
        status: New status
        error_message: Error message if status indicates failure

    Returns:
        True if successful, False otherwise
    """
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == EmailStatus.DELIVERED:
      update_data["delivery_timestamp"] = datetime.now(timezone.utc)
    elif status == EmailStatus.SUCCESS and not update_data.get("processed_at"):
      update_data["processed_at"] = datetime.now(timezone.utc)

    return await self.update_email(email_id, update_data)

  async def update_email_delivery_tracking(self, email_id: str, delivery_data: Dict[str, Any]) -> bool:
    """
    Updates email delivery tracking information.

    Args:
        email_id: Email ID to update
        delivery_data: Dictionary containing delivery tracking data

    Returns:
        True if successful, False otherwise
    """
    update_data = {
        "updated_at": datetime.now(timezone.utc)
    }

    # Add delivery tracking fields
    if "delivery_status" in delivery_data:
      update_data["delivery_status"] = delivery_data["delivery_status"]
    if "delivery_timestamp" in delivery_data:
      update_data["delivery_timestamp"] = delivery_data["delivery_timestamp"]
    if "open_count" in delivery_data:
      update_data["open_count"] = delivery_data["open_count"]
    if "click_count" in delivery_data:
      update_data["click_count"] = delivery_data["click_count"]

    return await self.update_email(email_id, update_data)

  async def get_email_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about emails.

    Returns:
        Dictionary with email statistics
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      total_emails = await collection.count_documents({})

      # Count by category
      stats = {"total_emails": total_emails}

      for category in EmailCategory:
        count = await collection.count_documents({"category": category.value})
        stats[f"{category.value}_emails"] = count

      # Count by status
      for status in EmailStatus:
        count = await collection.count_documents({"status": status.value})
        stats[f"{status.value}_emails"] = count

      # Count by direction
      inbound_count = await collection.count_documents({"direction": "inbound"})
      outbound_count = await collection.count_documents({"direction": "outbound"})
      stats["inbound_emails"] = inbound_count
      stats["outbound_emails"] = outbound_count

      # Count with attachments
      with_attachments = await collection.count_documents({"has_attachments": True})
      stats["emails_with_attachments"] = with_attachments

      logfire.debug(f"Retrieved email statistics", stats=stats)
      return stats

    except Exception as e:
      logfire.error(f"Error retrieving email statistics: {e}", exc_info=True)
      return {"total_emails": 0}

  async def delete_email(self, email_id: str) -> bool:
    """
    Deletes an email by ID.

    Args:
        email_id: Email ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[EMAILS_COLLECTION]

      result = await collection.delete_one({"_id": email_id})

      if result.deleted_count > 0:
        logfire.info(f"Email deleted successfully", email_id=email_id)
        return True
      else:
        logfire.warn(f"No email found to delete", email_id=email_id)
        return False

    except Exception as e:
      logfire.error(f"Error deleting email {email_id}: {e}", exc_info=True)
      return False

  async def compose_email_for_n8n(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Composes an email document for n8n sending.

    Args:
        email_data: Email composition data

    Returns:
        Composed email document ready for n8n
    """
    try:
      # Prepare email document data
      email_doc_data = {
          "id": email_data.get("id"),
          "category": EmailCategory.SENT.value,
          "status": EmailStatus.PROCESSING.value,
          "direction": "outbound",
          "from_email": email_data.get("from_email"),
          "from_name": email_data.get("from_name"),
          "to_emails": email_data.get("to_emails", []),
          "cc_emails": email_data.get("cc_emails", []),
          "bcc_emails": email_data.get("bcc_emails", []),
          "subject": email_data.get("subject"),
          "body_text": email_data.get("body_text"),
          "body_html": email_data.get("body_html"),
          "has_attachments": len(email_data.get("attachments", [])) > 0,
          "attachment_count": len(email_data.get("attachments", [])),
          "attachments": email_data.get("attachments", []),
          "n8n_workflow_id": email_data.get("n8n_workflow_id"),
          "contact_id": email_data.get("contact_id"),
          "lead_id": email_data.get("lead_id"),
          "email_sent_at": datetime.now(timezone.utc)
      }

      # Store in database
      await self.create_email(email_doc_data)

      logfire.info(f"Email composed for n8n", email_id=email_doc_data["id"])
      return email_doc_data

    except Exception as e:
      logfire.error(f"Error composing email for n8n: {e}", exc_info=True)
      return {}

  # === Pagination Methods ===
  async def get_recent_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Gets recent emails with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting recent emails: {str(e)}")
      return []

  async def get_oldest_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Gets oldest emails with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({})
      cursor = cursor.sort("created_at", 1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting oldest emails: {str(e)}")
      return []

  async def get_successful_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Gets successful emails with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({"status": "success"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting successful emails: {str(e)}")
      return []

  async def get_failed_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Gets failed emails with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({"status": "failed"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting failed emails: {str(e)}")
      return []

  async def get_pending_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Gets pending emails with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({"status": "pending"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting pending emails: {str(e)}")
      return []

  async def get_emails_by_direction(self, direction: str, offset: int = 0) -> List[EmailDocument]:
    """Gets emails by direction with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({"direction": direction})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting emails by direction: {str(e)}")
      return []

  async def get_emails_with_attachments(self, offset: int = 0) -> List[EmailDocument]:
    """Gets emails with attachments with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find({"has_attachments": True})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting emails with attachments: {str(e)}")
      return []

  async def get_processed_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Gets processed emails with pagination."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      cursor = collection.find(
          {"processing_result": {"$exists": True, "$ne": None}})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      emails = []
      async for result in cursor:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        emails.append(EmailDocument(**result))

      return emails
    except Exception as e:
      logfire.error(f"Error getting processed emails: {str(e)}")
      return []

  async def get_email_by_id(self, email_id: str) -> Optional[EmailDocument]:
    """Gets a single email by ID."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      result = await collection.find_one({"id": email_id})

      if result:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        return EmailDocument(**result)
      return None
    except Exception as e:
      logfire.error(f"Error getting email by ID: {str(e)}")
      return None

  # === Count Methods ===
  async def count_all_emails(self) -> int:
    """Counts all emails."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      return await collection.count_documents({})
    except Exception as e:
      logfire.error(f"Error counting all emails: {str(e)}")
      return 0

  async def count_emails_by_status(self, status: str) -> int:
    """Counts emails by status."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      return await collection.count_documents({"status": status})
    except Exception as e:
      logfire.error(f"Error counting emails by status: {str(e)}")
      return 0

  async def count_emails_by_category(self, category: str) -> int:
    """Counts emails by category."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      return await collection.count_documents({"category": category})
    except Exception as e:
      logfire.error(f"Error counting emails by category: {str(e)}")
      return 0

  async def count_emails_by_direction(self, direction: str) -> int:
    """Counts emails by direction."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      return await collection.count_documents({"direction": direction})
    except Exception as e:
      logfire.error(f"Error counting emails by direction: {str(e)}")
      return 0

  async def count_emails_with_attachments(self) -> int:
    """Counts emails with attachments."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      return await collection.count_documents({"has_attachments": True})
    except Exception as e:
      logfire.error(f"Error counting emails with attachments: {str(e)}")
      return 0

  async def count_processed_emails(self) -> int:
    """Counts processed emails."""
    try:
      collection = self.db[EMAILS_COLLECTION]
      return await collection.count_documents({"processing_result": {"$exists": True, "$ne": None}})
    except Exception as e:
      logfire.error(f"Error counting processed emails: {str(e)}")
      return 0
