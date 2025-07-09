# filepath: app/services/mongo/classify/operations.py
import logfire
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from app.models.mongo.classify import ClassifyDocument, ClassifyStatus
from app.services.mongo.collections.names import CLASSIFY_COLLECTION


class ClassifyOperations:
  """Handles MongoDB operations for classify collection."""

  def __init__(self, db):
    self.db = db

  async def create_classify(self, classify_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates a new classify document in the classify collection.

    Args:
        classify_data: Dictionary containing classification data

    Returns:
        Classify ID if successful, None otherwise
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      # Create ClassifyDocument to validate data
      classify_doc = ClassifyDocument(**classify_data)

      # Prepare document for insertion
      doc_dict = classify_doc.model_dump()
      doc_dict["_id"] = doc_dict.pop("id")  # Use id as _id
      doc_dict["created_at"] = datetime.now(timezone.utc)
      doc_dict["updated_at"] = datetime.now(timezone.utc)

      # Insert the document
      result = await collection.insert_one(doc_dict)

      if result.inserted_id:
        logfire.info(f"Classification created successfully",
                     classify_id=str(result.inserted_id))
        return str(result.inserted_id)
      else:
        logfire.error("Failed to create classification: no ID returned")
        return None

    except Exception as e:
      logfire.error(f"Error creating classification: {e}", exc_info=True)
      return None

  async def update_classify(self, classify_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Updates an existing classify document.

    Args:
        classify_id: Classify ID to update
        update_data: Dictionary containing fields to update

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      # Add updated_at timestamp
      update_data["updated_at"] = datetime.now(timezone.utc)

      # Perform the update
      result = await collection.update_one(
          {"_id": classify_id},
          {"$set": update_data}
      )

      if result.matched_count > 0:
        logfire.info(f"Classification updated successfully",
                     classify_id=classify_id)
        return True
      else:
        logfire.warn(f"No classification found with ID: {classify_id}")
        return False

    except Exception as e:
      logfire.error(
          f"Error updating classification {classify_id}: {e}", exc_info=True)
      return False

  async def get_classify(self, classify_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a classification by ID.

    Args:
        classify_id: Classify ID to retrieve

    Returns:
        Classification document if found, None otherwise
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      doc = await collection.find_one({"_id": classify_id})

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved classification", classify_id=classify_id)
        return doc
      else:
        logfire.info(f"Classification not found", classify_id=classify_id)
        return None

    except Exception as e:
      logfire.error(
          f"Error retrieving classification {classify_id}: {e}", exc_info=True)
      return None

  async def get_classify_by_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves the most recent classification for a contact.

    Args:
        contact_id: HubSpot contact ID

    Returns:
        Classification document if found, None otherwise
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      doc = await collection.find_one(
          {"contact_id": contact_id},
          sort=[("created_at", -1)]
      )

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved classification for contact",
                      contact_id=contact_id, classify_id=doc["id"])
        return doc
      else:
        logfire.info(f"No classification found for contact",
                     contact_id=contact_id)
        return None

    except Exception as e:
      logfire.error(
          f"Error retrieving classification for contact {contact_id}: {e}", exc_info=True)
      return None

  async def get_classifications_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves classifications for a specific contact.

    Args:
        contact_id: HubSpot contact ID
        limit: Maximum number of classifications to return

    Returns:
        List of classification documents
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      cursor = collection.find(
          {"contact_id": contact_id}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} classifications for contact", contact_id=contact_id)
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving classifications for contact {contact_id}: {e}", exc_info=True)
      return []

  async def get_classifications_by_status(self, status: ClassifyStatus, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]:
    """
    Retrieves classifications by status with pagination.

    Args:
        status: Classification status to filter by
        limit: Maximum number of classifications to return
        offset: Number of classifications to skip

    Returns:
        List of ClassifyDocument objects
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      cursor = collection.find(
          {"status": status.value}
      ).sort("created_at", -1).skip(offset).limit(limit)

      results = await cursor.to_list(length=limit)

      classifications = []
      for result in results:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))

      logfire.debug(
          f"Retrieved {len(classifications)} classifications with status {status.value}")
      return classifications
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving classifications by status {status.value}: {e}", exc_info=True)
      return []

  async def get_classifications_by_lead_type(self, lead_type: str, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]:
    """
    Retrieves classifications by lead type with pagination.

    Args:
        lead_type: Lead type to filter by (Services, Logistics, Leads, Disqualify)
        limit: Maximum number of classifications to return
        offset: Number of classifications to skip

    Returns:
        List of ClassifyDocument objects
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      cursor = collection.find(
          {"lead_type": lead_type}
      ).sort("created_at", -1).skip(offset).limit(limit)

      results = await cursor.to_list(length=limit)

      classifications = []
      for result in results:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))

      logfire.debug(
          f"Retrieved {len(classifications)} classifications with lead type {lead_type}")
      return classifications
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving classifications by lead type {lead_type}: {e}", exc_info=True)
      return []

  async def get_classifications_requiring_review(self, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves classifications that require human review.

    Args:
        limit: Maximum number of classifications to return

    Returns:
        List of classification documents
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      cursor = collection.find(
          {"requires_human_review": True}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(f"Retrieved {len(docs)} classifications requiring review")
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving classifications requiring review: {e}", exc_info=True)
      return []

  async def get_classifications_paginated(
      self,
      page: int = 1,
      page_size: int = 10,
      status_filter: Optional[str] = None,
      lead_type_filter: Optional[str] = None,
      sort_field: str = "created_at",
      sort_order: int = -1
  ) -> Tuple[List[Dict[str, Any]], int]:
    """
    Retrieves paginated classifications with optional filtering and sorting.

    Args:
        page: Page number (1-based)
        page_size: Number of items per page
        status_filter: Optional status filter
        lead_type_filter: Optional lead type filter
        sort_field: Field to sort by
        sort_order: Sort order (1 for ascending, -1 for descending)

    Returns:
        Tuple of (classification documents, total count)
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      # Build query
      query = {}
      if status_filter:
        query["status"] = status_filter
      if lead_type_filter:
        query["lead_type"] = lead_type_filter

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
          f"Retrieved {len(docs)} classifications (page {page}, total {total_count})")
      return docs, total_count

    except Exception as e:
      logfire.error(
          f"Error retrieving paginated classifications: {e}", exc_info=True)
      return [], 0

  async def update_classify_status(self, classify_id: str, status: ClassifyStatus, error_message: Optional[str] = None) -> bool:
    """
    Updates a classification's status.

    Args:
        classify_id: Classify ID to update
        status: New status
        error_message: Error message if status is FAILED

    Returns:
        True if successful, False otherwise
    """
    update_data = {
        "status": status.value,
        "updated_at": datetime.now(timezone.utc)
    }

    if error_message:
      update_data["error_message"] = error_message

    if status == ClassifyStatus.COMPLETED:
      update_data["classified_at"] = datetime.now(timezone.utc)

    return await self.update_classify(classify_id, update_data)

  async def get_classify_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about classifications.

    Returns:
        Dictionary with classification statistics
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      total_classifications = await collection.count_documents({})

      # Count by status
      stats = {"total_classifications": total_classifications}

      for status in ClassifyStatus:
        count = await collection.count_documents({"status": status.value})
        stats[f"{status.value}_classifications"] = count

      # Count by lead type
      for lead_type in ["Services", "Logistics", "Leads", "Disqualify"]:
        count = await collection.count_documents({"lead_type": lead_type})
        stats[f"{lead_type.lower()}_leads"] = count

      # Count requiring review
      review_count = await collection.count_documents({"requires_human_review": True})
      stats["requiring_review"] = review_count

      logfire.debug(f"Retrieved classification statistics", stats=stats)
      return stats

    except Exception as e:
      logfire.error(
          f"Error retrieving classification statistics: {e}", exc_info=True)
      return {"total_classifications": 0}

  async def delete_classify(self, classify_id: str) -> bool:
    """
    Deletes a classification by ID.

    Args:
        classify_id: Classify ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[CLASSIFY_COLLECTION]

      result = await collection.delete_one({"_id": classify_id})

      if result.deleted_count > 0:
        logfire.info(f"Classification deleted successfully",
                     classify_id=classify_id)
        return True
      else:
        logfire.warn(f"No classification found to delete",
                     classify_id=classify_id)
        return False

    except Exception as e:
      logfire.error(
          f"Error deleting classification {classify_id}: {e}", exc_info=True)
      return False

  # Pagination query methods
  async def get_recent_classifications(self, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]:
    """Get recent classifications ordered by creation date (newest first)."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find().sort("created_at", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      classifications = []
      for result in results:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))
      return classifications
    except Exception as e:
      logfire.error(
          f"Error fetching recent classifications: {e}", exc_info=True)
      return []

  async def get_oldest_classifications(self, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]:
    """Get oldest classifications ordered by creation date (oldest first)."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find().sort("created_at", 1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      classifications = []
      for result in results:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))
      return classifications
    except Exception as e:
      logfire.error(
          f"Error fetching oldest classifications: {e}", exc_info=True)
      return []

  async def get_classifications_by_confidence(self, min_confidence: float, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]:
    """Get classifications filtered by minimum confidence level."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find({"confidence": {"$gte": min_confidence}}).sort(
          "confidence", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      classifications = []
      for result in results:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))
      return classifications
    except Exception as e:
      logfire.error(
          f"Error fetching classifications by confidence: {e}", exc_info=True)
      return []

  async def get_classifications_by_source(self, source: str, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]:
    """Get classifications filtered by source."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find({"source": source}).sort(
          "created_at", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      classifications = []
      for result in results:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))
      return classifications
    except Exception as e:
      logfire.error(
          f"Error fetching classifications by source: {e}", exc_info=True)
      return []

  async def get_classification_by_id(self, classify_id: str) -> Optional[ClassifyDocument]:
    """Get a single classification by ID."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      result = await collection.find_one({"id": classify_id})

      if result:
        result.pop("_id", None)
        return ClassifyDocument(**result)
      return None
    except Exception as e:
      logfire.error(
          f"Error retrieving classification by ID: {e}", exc_info=True)
      return None

  # Count methods for pagination
  async def count_classifications(self) -> int:
    """Count total classifications."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      return await collection.count_documents({})
    except Exception as e:
      logfire.error(f"Error counting classifications: {e}", exc_info=True)
      return 0

  async def count_classifications_by_status(self, status: ClassifyStatus) -> int:
    """Count classifications by status."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      return await collection.count_documents({"status": status.value})
    except Exception as e:
      logfire.error(
          f"Error counting classifications by status: {e}", exc_info=True)
      return 0

  async def count_classifications_by_lead_type(self, lead_type: str) -> int:
    """Count classifications by lead type."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      return await collection.count_documents({"lead_type": lead_type})
    except Exception as e:
      logfire.error(
          f"Error counting classifications by lead type: {e}", exc_info=True)
      return 0

  async def count_classifications_by_confidence(self, min_confidence: float) -> int:
    """Count classifications by minimum confidence level."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      return await collection.count_documents({"confidence": {"$gte": min_confidence}})
    except Exception as e:
      logfire.error(
          f"Error counting classifications by confidence: {e}", exc_info=True)
      return 0

  async def count_classifications_by_source(self, source: str) -> int:
    """Count classifications by source."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      return await collection.count_documents({"source": source})
    except Exception as e:
      logfire.error(
          f"Error counting classifications by source: {e}", exc_info=True)
      return 0

  # === Additional Pagination Methods ===
  async def get_successful_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Gets successful classifications with pagination."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find({"status": "success"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      classifications = []
      async for result in cursor:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))

      return classifications
    except Exception as e:
      logfire.error(f"Error getting successful classifications: {str(e)}")
      return []

  async def get_failed_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Gets failed classifications with pagination."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find({"status": "failed"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      classifications = []
      async for result in cursor:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))

      return classifications
    except Exception as e:
      logfire.error(f"Error getting failed classifications: {str(e)}")
      return []

  async def get_disqualified_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Gets disqualified classifications with pagination."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      cursor = collection.find({"classification_result": "Disqualify"})
      cursor = cursor.sort("created_at", -1)
      cursor = cursor.skip(offset).limit(10)

      classifications = []
      async for result in cursor:
        result.pop("_id", None)
        classifications.append(ClassifyDocument(**result))

      return classifications
    except Exception as e:
      logfire.error(f"Error getting disqualified classifications: {str(e)}")
      return []

  async def count_all_classifications(self) -> int:
    """Counts all classifications."""
    try:
      collection = self.db[CLASSIFY_COLLECTION]
      return await collection.count_documents({})
    except Exception as e:
      logfire.error(f"Error counting all classifications: {str(e)}")
      return 0
