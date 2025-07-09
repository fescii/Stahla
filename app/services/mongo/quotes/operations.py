# filepath: app/services/mongo/quotes/operations.py
import logfire
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from app.models.mongo.quotes import QuoteDocument, QuoteStatus
from app.services.mongo.collections.names import QUOTES_COLLECTION


class QuotesOperations:
  """Handles MongoDB operations for quotes collection."""

  def __init__(self, db):
    self.db = db

  async def create_quote(self, quote_data: Dict[str, Any]) -> Optional[str]:
    """
    Creates a new quote document in the quotes collection.

    Args:
        quote_data: Dictionary containing quote data

    Returns:
        Quote ID if successful, None otherwise
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      # Create QuoteDocument to validate data
      quote_doc = QuoteDocument(**quote_data)

      # Prepare document for insertion
      doc_dict = quote_doc.model_dump()
      doc_dict["_id"] = doc_dict.pop("id")  # Use id as _id
      doc_dict["created_at"] = datetime.now(timezone.utc)
      doc_dict["updated_at"] = datetime.now(timezone.utc)

      # Insert the document
      result = await collection.insert_one(doc_dict)

      if result.inserted_id:
        logfire.info(f"Quote created successfully",
                     quote_id=str(result.inserted_id))
        return str(result.inserted_id)
      else:
        logfire.error("Failed to create quote: no ID returned")
        return None

    except Exception as e:
      logfire.error(f"Error creating quote: {e}", exc_info=True)
      return None

  async def update_quote(self, quote_id: str, update_data: Dict[str, Any]) -> bool:
    """
    Updates an existing quote document.

    Args:
        quote_id: Quote ID to update
        update_data: Dictionary containing fields to update

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      # Add updated_at timestamp
      update_data["updated_at"] = datetime.now(timezone.utc)

      # Perform the update
      result = await collection.update_one(
          {"_id": quote_id},
          {"$set": update_data}
      )

      if result.matched_count > 0:
        logfire.info(f"Quote updated successfully", quote_id=quote_id)
        return True
      else:
        logfire.warn(f"No quote found with ID: {quote_id}")
        return False

    except Exception as e:
      logfire.error(f"Error updating quote {quote_id}: {e}", exc_info=True)
      return False

  async def get_quote(self, quote_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a quote by ID.

    Args:
        quote_id: Quote ID to retrieve

    Returns:
        Quote document if found, None otherwise
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      doc = await collection.find_one({"_id": quote_id})

      if doc:
        # Convert _id back to id
        doc["id"] = str(doc.pop("_id"))
        logfire.debug(f"Retrieved quote", quote_id=quote_id)
        return doc
      else:
        logfire.info(f"Quote not found", quote_id=quote_id)
        return None

    except Exception as e:
      logfire.error(f"Error retrieving quote {quote_id}: {e}", exc_info=True)
      return None

  async def get_quotes_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves quotes for a specific contact.

    Args:
        contact_id: HubSpot contact ID
        limit: Maximum number of quotes to return

    Returns:
        List of quote documents
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      cursor = collection.find(
          {"contact_id": contact_id}
      ).sort("created_at", -1).limit(limit)

      docs = await cursor.to_list(length=limit)

      # Convert _id to id for all documents
      for doc in docs:
        doc["id"] = str(doc.pop("_id"))

      logfire.debug(
          f"Retrieved {len(docs)} quotes for contact", contact_id=contact_id)
      return docs

    except Exception as e:
      logfire.error(
          f"Error retrieving quotes for contact {contact_id}: {e}", exc_info=True)
      return []

  async def get_quotes_by_status(self, status: QuoteStatus, limit: int = 10, offset: int = 0) -> List[QuoteDocument]:
    """
    Retrieves quotes by status with pagination.

    Args:
        status: Quote status to filter by
        limit: Maximum number of quotes to return
        offset: Number of quotes to skip

    Returns:
        List of QuoteDocument objects
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      cursor = collection.find(
          {"status": status.value}
      ).sort("created_at", -1).skip(offset).limit(limit)

      results = await cursor.to_list(length=limit)

      quotes = []
      for result in results:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        quotes.append(QuoteDocument(**result))

      logfire.debug(
          f"Retrieved {len(quotes)} quotes with status {status.value}")
      return quotes

    except Exception as e:
      logfire.error(
          f"Error retrieving quotes by status {status.value}: {e}", exc_info=True)
      return []

  async def update_quote_status(self, quote_id: str, status: QuoteStatus, error_message: Optional[str] = None) -> bool:
    """
    Updates a quote's status.

    Args:
        quote_id: Quote ID to update
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

    return await self.update_quote(quote_id, update_data)

  async def get_quote_stats(self) -> Dict[str, int]:
    """
    Retrieves statistics about quotes.

    Returns:
        Dictionary with quote statistics
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      total_quotes = await collection.count_documents({})

      # Count by status
      stats = {"total_quotes": total_quotes}

      for status in QuoteStatus:
        count = await collection.count_documents({"status": status.value})
        stats[f"{status.value}_quotes"] = count

      logfire.debug(f"Retrieved quote statistics", stats=stats)
      return stats

    except Exception as e:
      logfire.error(f"Error retrieving quote statistics: {e}", exc_info=True)
      return {"total_quotes": 0}

  async def delete_quote(self, quote_id: str) -> bool:
    """
    Deletes a quote by ID.

    Args:
        quote_id: Quote ID to delete

    Returns:
        True if successful, False otherwise
    """
    try:
      collection = self.db[QUOTES_COLLECTION]

      result = await collection.delete_one({"_id": quote_id})

      if result.deleted_count > 0:
        logfire.info(f"Quote deleted successfully", quote_id=quote_id)
        return True
      else:
        logfire.warn(f"No quote found to delete", quote_id=quote_id)
        return False

    except Exception as e:
      logfire.error(f"Error deleting quote {quote_id}: {e}", exc_info=True)
      return False

  async def get_quote_by_id(self, quote_id: str) -> Optional[QuoteDocument]:
    """
    Retrieves a quote by its ID.

    Args:
        quote_id: The quote ID to search for

    Returns:
        QuoteDocument if found, None otherwise
    """
    try:
      collection = self.db[QUOTES_COLLECTION]
      result = await collection.find_one({"id": quote_id})

      if result:
        # Remove MongoDB's _id field
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        return QuoteDocument(**result)
      return None
    except Exception as e:
      logfire.error(f"Error retrieving quote by ID: {e}", exc_info=True)
      return None

  # Pagination query methods
  async def get_recent_quotes(self, limit: int = 10, offset: int = 0) -> List[QuoteDocument]:
    """Get recent quotes ordered by creation date (newest first)."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      cursor = collection.find().sort("created_at", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      quotes = []
      for result in results:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        quotes.append(QuoteDocument(**result))
      return quotes
    except Exception as e:
      logfire.error(f"Error fetching recent quotes: {e}", exc_info=True)
      return []

  async def get_oldest_quotes(self, limit: int = 10, offset: int = 0) -> List[QuoteDocument]:
    """Get oldest quotes ordered by creation date (oldest first)."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      cursor = collection.find().sort("created_at", 1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      quotes = []
      for result in results:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        quotes.append(QuoteDocument(**result))
      return quotes
    except Exception as e:
      logfire.error(f"Error fetching oldest quotes: {e}", exc_info=True)
      return []

  async def get_quotes_by_value(self, limit: int = 10, offset: int = 0, ascending: bool = True) -> List[QuoteDocument]:
    """Get quotes ordered by total amount."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      sort_direction = 1 if ascending else -1
      cursor = collection.find().sort(
          "total_amount", sort_direction).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      quotes = []
      for result in results:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        quotes.append(QuoteDocument(**result))
      return quotes
    except Exception as e:
      logfire.error(f"Error fetching quotes by value: {e}", exc_info=True)
      return []

  async def get_quotes_by_product_type(self, product_type: str, limit: int = 10, offset: int = 0) -> List[QuoteDocument]:
    """Get quotes filtered by product type."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      cursor = collection.find({"product_type": product_type}).sort(
          "created_at", -1).skip(offset).limit(limit)
      results = await cursor.to_list(length=limit)

      quotes = []
      for result in results:
        if "_id" in result:
          result["id"] = str(result.pop("_id"))
        quotes.append(QuoteDocument(**result))
      return quotes
    except Exception as e:
      logfire.error(
          f"Error fetching quotes by product type: {e}", exc_info=True)
      return []

  # Count methods for pagination
  async def count_quotes(self) -> int:
    """Count total quotes."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      return await collection.count_documents({})
    except Exception as e:
      logfire.error(f"Error counting quotes: {e}", exc_info=True)
      return 0

  async def count_quotes_by_status(self, status: QuoteStatus) -> int:
    """Count quotes by status."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      return await collection.count_documents({"status": status.value})
    except Exception as e:
      logfire.error(f"Error counting quotes by status: {e}", exc_info=True)
      return 0

  async def count_quotes_by_product_type(self, product_type: str) -> int:
    """Count quotes by product type."""
    try:
      collection = self.db[QUOTES_COLLECTION]
      return await collection.count_documents({"product_type": product_type})
    except Exception as e:
      logfire.error(
          f"Error counting quotes by product type: {e}", exc_info=True)
      return 0
