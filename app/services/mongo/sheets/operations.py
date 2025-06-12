# filepath: app/services/mongo/sheets/operations.py
import logfire
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pymongo import UpdateOne
from app.services.mongo.collections.names import SHEET_CONFIG_COLLECTION


class SheetsOperations:
  """Handles MongoDB operations for Google Sheets synchronization."""

  def __init__(self, db):
    self.db = db

  async def replace_sheet_collection_data(
      self, collection_name: str, data: List[Dict[str, Any]], id_field: str
  ):
    """
    Replaces all data in the specified collection with the new data from the sheet.
    Uses the value of `id_field` from each item in `data` as the `_id` in MongoDB.
    The entire item (including all its original fields) is stored in the document.
    Documents existing in MongoDB but not in the new `data` (based on `id_field`) are removed.
    """
    if self.db is None:
      logfire.error(
          "replace_sheet_collection_data: MongoDB database is not initialized.")
      raise RuntimeError("Database connection is not available.")
    collection = self.db[collection_name]
    logfire_extra_data = {
        "collection_name": collection_name,
        "id_field": id_field,
        "item_count": len(data),
    }

    if not data:
      logfire.info(
          f"SheetSync: Empty data provided for {collection_name}. Deleting all existing documents.",
          **logfire_extra_data,
      )
      try:
        delete_result = await collection.delete_many({})
        logfire.info(
            f"SheetSync: Deleted {delete_result.deleted_count} documents from {collection_name} due to empty sheet data.",
            **logfire_extra_data,
        )
      except Exception as e:
        logfire.error(
            f"SheetSync: Error deleting documents from {collection_name} for empty data: {e}",
            exc_info=True,
            **logfire_extra_data,
        )
      return

    operations = []
    current_ids_in_sheet_data = set()

    for item in data:
      item_id_value = item.get(id_field)

      if item_id_value is None:
        logfire.warning(
            f"SheetSync: Item in {collection_name} is missing id_field '{id_field}'. Skipping item: {item}",
            **logfire_extra_data,
        )
        continue

      current_ids_in_sheet_data.add(item_id_value)

      # The document to be $set will be the original item itself.
      # This ensures all fields from the sheet (e.g., "id", "name", "price", "category")
      # are present in the MongoDB document.
      # MongoDB's _id will be item_id_value.
      # Example: if item = {"id": "P1", "name": "ProdA", "price": 100},
      # MongoDB doc will be: {"_id": "P1", "id": "P1", "name": "ProdA", "price": 100}
      document_to_set = item

      operations.append(
          UpdateOne(
              {
                  "_id": item_id_value
              },  # Filter by _id (which is the sheet's id_field value)
              {"$set": document_to_set},  # Set all fields from the item
              upsert=True,
          )
      )

    if operations:
      logfire.info(
          f"SheetSync: Performing {len(operations)} bulk upsert operations on {collection_name} using '{id_field}' as _id source.",
          **logfire_extra_data,
      )
      if operations:  # Log sample for debugging
        # Correctly access filter (q) and update (u) from the UpdateOne's document
        sample_op_doc = operations[0]._doc
        logfire.debug(
            f"SheetSync: Sample operation for {collection_name}: Filter={{'_id': {sample_op_doc.get('q', {}).get('_id')}}}, Update={{'$set': {sample_op_doc.get('u', {}).get('$set')}}}",
            **logfire_extra_data,
        )
      try:
        result = await collection.bulk_write(operations, ordered=False)
        logfire.info(
            f"SheetSync: Bulk write to {collection_name} completed. Upserted: {result.upserted_count}, Modified: {result.modified_count}, Matched: {result.matched_count}.",
            **logfire_extra_data,
        )
      except Exception as e:
        logfire.error(
            f"SheetSync: Error during bulk write for {collection_name}: {e}",
            exc_info=True,
            **logfire_extra_data,
        )
        # Depending on requirements, you might want to raise e or handle it further
    else:
      logfire.info(
          f"SheetSync: No valid operations to perform for {collection_name} (e.g., all items lacked id_field or data was empty after filtering).",
          **logfire_extra_data,
      )

    # After upserting, delete any documents that were not in the new data list.
    # This ensures the collection is an exact mirror of the 'data' list from the sheet.
    if current_ids_in_sheet_data:  # Only delete if there was some valid new data
      delete_filter = {"_id": {"$nin": list(current_ids_in_sheet_data)}}
      try:
        delete_result = await collection.delete_many(delete_filter)
        if delete_result.deleted_count > 0:
          logfire.info(
              f"SheetSync: Deleted {delete_result.deleted_count} documents from {collection_name} that are no longer in the sheet data.",
              **logfire_extra_data,
          )
      except Exception as e:
        logfire.error(
            f"SheetSync: Error deleting old documents from {collection_name}: {e}",
            exc_info=True,
            **logfire_extra_data,
        )
    elif (
        not operations and data
        # New data was present, but no operations were made (e.g. all items lacked id_field)
    ):
      logfire.warning(
          f"SheetSync: No documents were upserted for {collection_name}, and therefore no old documents were deleted. The collection might be stale if it previously had data.",
          **logfire_extra_data,
      )

  async def upsert_sheet_config_document(
      self,
      document_id: str,
      config_data: Dict[str, Any],
      config_type: Optional[str] = None,
  ) -> Dict[str, Any]:
    """Upserts a single configuration document in the SHEET_CONFIG_COLLECTION."""
    collection = self.db[SHEET_CONFIG_COLLECTION]

    # The document to be upserted. We'll use the provided document_id as MongoDB's _id.
    payload_to_set = {**config_data,
                      "last_updated_mongo": datetime.now(timezone.utc)}
    if config_type:
      payload_to_set["config_type"] = config_type

    query = {"_id": document_id}  # Query by the custom _id
    update_doc = {"$set": payload_to_set}

    try:
      update_result = await collection.update_one(query, update_doc, upsert=True)
      upserted_id_str = None
      if update_result.upserted_id is not None:
        upserted_id_str = str(update_result.upserted_id)
      elif (
          update_result.matched_count > 0
      ):  # If matched, the ID was the document_id
        upserted_id_str = document_id

      logfire.info(
          f"Upserted document with _id '{document_id}' in MongoDB collection '{SHEET_CONFIG_COLLECTION}'. Matched: {update_result.matched_count}, Modified: {update_result.modified_count}, UpsertedId: {upserted_id_str}"
      )
      return {
          "matched_count": update_result.matched_count,
          "modified_count": update_result.modified_count,
          "upserted_id": upserted_id_str,
          "success": True,
      }
    except Exception as e:
      logfire.error(
          f"Failed to upsert document with _id '{document_id}' in MongoDB collection '{SHEET_CONFIG_COLLECTION}': {e}",
          exc_info=True,
      )
      return {"success": False, "error": str(e)}
