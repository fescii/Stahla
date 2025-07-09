# filepath: app/services/mongo/service.py
import logfire
from app.services.mongo.connection import MongoConnection, IndexManager
from app.services.mongo.stats import StatsOperations
from app.services.mongo.reports import ReportsOperations
from app.services.mongo.errors import ErrorOperations
from app.services.mongo.sheets import SheetsOperations
from app.services.mongo.quotes import QuotesOperations
from app.services.mongo.calls import CallsOperations
from app.services.mongo.classify import ClassifyOperations
from app.services.mongo.location import LocationOperations
from app.services.mongo.emails import EmailsOperations
from app.models.mongo.classify import ClassifyDocument, ClassifyStatus
from app.models.mongo.location import LocationDocument
from app.models.mongo.emails import EmailDocument
from app.models.mongo.calls import CallDocument, CallStatus
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timezone


class MongoService:
  """Main MongoDB service class that composes all operations."""

  def __init__(self):
    self.connection = MongoConnection()
    # Operations will be initialized after connection is established
    self.stats_ops: Optional[StatsOperations] = None
    self.reports_ops: Optional[ReportsOperations] = None
    self.error_ops: Optional[ErrorOperations] = None
    self.sheets_ops: Optional[SheetsOperations] = None
    self.quotes_ops: Optional[QuotesOperations] = None
    self.calls_ops: Optional[CallsOperations] = None
    self.classify_ops: Optional[ClassifyOperations] = None
    self.location_ops: Optional[LocationOperations] = None
    self.emails_ops: Optional[EmailsOperations] = None
    self.index_manager: Optional[IndexManager] = None

  async def connect_and_initialize(self):
    """Connects to MongoDB and initializes all operation classes."""
    await self.connection.connect_and_initialize()

    # Initialize all operation classes with the database instance
    db = await self.connection.get_db()
    self.stats_ops = StatsOperations(db)
    self.reports_ops = ReportsOperations(db)
    self.error_ops = ErrorOperations(db)
    self.sheets_ops = SheetsOperations(db)
    self.quotes_ops = QuotesOperations(db)
    self.calls_ops = CallsOperations(db)
    self.classify_ops = ClassifyOperations(db)
    self.location_ops = LocationOperations(db)
    self.emails_ops = EmailsOperations(db)
    self.index_manager = IndexManager(db)

    # Create indexes
    await self.index_manager.create_indexes()

  async def close_mongo_connection(self):
    """Closes MongoDB connection."""
    await self.connection.close_connection()

  async def get_db(self):
    """Returns the database instance."""
    return await self.connection.get_db()

  async def check_connection(self) -> str:
    """Checks the MongoDB connection."""
    return await self.connection.check_connection()

  # === Stats Operations ===
  async def increment_request_stat(self, stat_name: str, success: bool):
    """Increments a counter for a given statistic."""
    if self.stats_ops:
      await self.stats_ops.increment_request_stat(stat_name, success)

  async def get_dashboard_stats(self) -> Dict[str, Dict[str, int]]:
    """Retrieves dashboard statistics."""
    if self.stats_ops:
      return await self.stats_ops.get_dashboard_stats()
    return {}

  # === Reports Operations ===
  async def log_report(
      self,
      report_type: str,
      data: Dict[str, Any],
      success: bool,
      error_message: Optional[str] = None,
  ):
    """Logs a report document to the reports collection."""
    if self.reports_ops:
      return await self.reports_ops.log_report(report_type, data, success, error_message)

  async def get_recent_reports(
      self, report_type: Optional[Union[str, List[str]]] = None, limit: int = 100
  ) -> List[Dict[str, Any]]:
    """Retrieves recent reports."""
    if self.reports_ops:
      return await self.reports_ops.get_recent_reports(report_type, limit)
    return []

  async def get_report_summary(self) -> Dict[str, Any]:
    """Provides a summary of report counts by type and success/failure."""
    if self.reports_ops:
      return await self.reports_ops.get_report_summary()
    return {}

  # === Calls Operations (Migrated from Bland) ===
  async def get_bland_calls(
      self,
      page: int,
      page_size: int,
      status_filter: Optional[str],
      sort_field: str,
      sort_order: int,
  ) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves a paginated list of call logs (migrated from Bland)."""
    if self.calls_ops:
      # Convert to calls operations - get recent calls for now
      limit = page_size
      offset = (page - 1) * page_size
      calls = await self.calls_ops.get_recent_calls(limit, offset)

      # Convert CallDocument objects to dicts for backward compatibility
      calls_dict = [call.model_dump() for call in calls]

      # For total count, we'll approximate
      stats = await self.calls_ops.get_call_stats()
      total_count = stats.get('total_calls', len(calls_dict))

      return calls_dict, total_count
    return [], 0

  async def get_bland_call_log(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single call log by contact_id (migrated from Bland)."""
    if self.calls_ops:
      call = await self.calls_ops.get_call_by_contact(contact_id)
      return call  # Already a dict
    return None

  async def get_bland_call_stats(self) -> Dict[str, int]:
    """Retrieves statistics about call logs (migrated from Bland)."""
    if self.calls_ops:
      stats = await self.calls_ops.get_call_stats()
      # Map to old format for backward compatibility
      return {
          "total_calls": stats.get("total_calls", 0),
          "pending_calls": stats.get("pending_calls", 0),
          "completed_calls": stats.get("completed_calls", 0),
          "failed_calls": stats.get("failed_calls", 0),
          "retrying_calls": stats.get("retrying_calls", 0)
      }
    return {}

  # === Call Update Operations (Migrated from Bland) ===
  async def update_bland_call_log_internal(
      self,
      contact_id: str,
      update_data: Dict[str, Any]
  ) -> bool:
    """Updates a call log document in MongoDB (migrated from Bland)."""
    if self.calls_ops:
      # Find the call by contact_id first
      call = await self.calls_ops.get_call_by_contact(contact_id)
      if call and call.get("id"):
        return await self.calls_ops.update_call(call["id"], update_data)
    return False

  async def update_bland_call_log_completion(
      self,
      contact_id: str,
      call_id_bland: str,
      status: CallStatus,
      transcript_payload: List[Dict[str, Any]],
      summary_text: Optional[str] = None,
      classification_payload: Optional[Dict[str, Any]] = None,
      full_webhook_payload: Optional[Dict[str, Any]] = None,
      call_completed_timestamp: Optional[datetime] = None,
      bland_processing_result_payload: Optional[Dict[str, Any]] = None,
      processing_status_message: Optional[str] = None
  ) -> bool:
    """Updates a call log with completion data (migrated from Bland)."""
    if self.calls_ops:
      call = await self.calls_ops.get_call_by_contact(contact_id)
      if call and call.get("id"):
        update_data = {
            "status": status,
            "call_id_bland": call_id_bland,
            "transcript_payload": transcript_payload,
            "summary": summary_text,
            "classification_payload": classification_payload,
            "full_webhook_payload": full_webhook_payload,
            "call_completed_at": call_completed_timestamp or datetime.now(timezone.utc),
            "processing_result_payload": bland_processing_result_payload,
            "processing_status_message": processing_status_message,
            "updated_at": datetime.now(timezone.utc)
        }
        return await self.calls_ops.update_call(call["id"], update_data)
    return False

  async def log_bland_call_attempt(
      self,
      contact_id: str,
      phone_number: str,
      task: Optional[str] = None,
      pathway_id_used: Optional[str] = None,
      initial_status: CallStatus = CallStatus.PENDING,
      call_id_bland: Optional[str] = None,
      retry_of_call_id: Optional[str] = None,
      retry_reason: Optional[str] = None,
      voice_id: Optional[str] = None,
      webhook_url: Optional[str] = None,
      max_duration: Optional[int] = 12,
      request_data_variables: Optional[Dict[str, Any]] = None,
      transfer_phone_number: Optional[str] = None
  ) -> bool:
    """Logs an initial call attempt to MongoDB (migrated from Bland)."""
    if self.calls_ops:
      call_data = {
          "id": f"call_{contact_id}_{datetime.now().timestamp()}",
          "contact_id": contact_id,
          "phone_number": phone_number,
          "task": task,
          "pathway_id_used": pathway_id_used,
          "status": initial_status,
          "call_id_bland": call_id_bland,
          "retry_of_call_id": retry_of_call_id,
          "retry_reason": retry_reason,
          "voice_id": voice_id,
          "webhook_url": webhook_url,
          "max_duration": max_duration,
          "request_data_variables": request_data_variables,
          "transfer_phone_number": transfer_phone_number,
          "call_initiated_at": datetime.now(timezone.utc)
      }
      result = await self.calls_ops.create_call(call_data)
      return bool(result)
    return False

  # === Error Operations ===
  async def log_error_to_db(
      self,
      service_name: str,
      error_type: str,
      message: str,
      details: Optional[Dict[str, Any]] = None,
      stack_trace: Optional[str] = None,
      request_context: Optional[Dict[str, Any]] = None
  ) -> Optional[str]:
    """Logs an error to the error_logs collection in MongoDB."""
    if self.error_ops:
      return await self.error_ops.log_error_to_db(
          service_name, error_type, message, details, stack_trace, request_context
      )
    return None

  async def get_error_logs(
      self,
      page: int = 1,
      page_size: int = 10,
      service_name_filter: Optional[str] = None,
      error_type_filter: Optional[str] = None,
      sort_field: str = "timestamp",
      sort_order: int = -1  # DESCENDING
  ) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves error logs from MongoDB with pagination and filtering."""
    if self.error_ops:
      return await self.error_ops.get_error_logs(
          page, page_size, service_name_filter, error_type_filter, sort_field, sort_order
      )
    return [], 0

  # === Sheets Operations ===
  async def replace_sheet_collection_data(
      self, collection_name: str, data: List[Dict[str, Any]], id_field: str
  ):
    """Replaces all data in the specified collection with the new data from the sheet."""
    if self.sheets_ops:
      await self.sheets_ops.replace_sheet_collection_data(collection_name, data, id_field)

  async def upsert_sheet_config_document(
      self,
      document_id: str,
      config_data: Dict[str, Any],
      config_type: Optional[str] = None,
  ) -> Dict[str, Any]:
    """Upserts a single configuration document in the SHEET_CONFIG_COLLECTION."""
    if self.sheets_ops:
      return await self.sheets_ops.upsert_sheet_config_document(document_id, config_data, config_type)
    return {"success": False, "error": "Sheets operations not initialized"}

  # === Quotes Operations ===
  async def create_quote(self, quote_data: Dict[str, Any]) -> Optional[str]:
    """Creates a new quote document."""
    if self.quotes_ops:
      return await self.quotes_ops.create_quote(quote_data)
    return None

  async def update_quote(self, quote_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates an existing quote document."""
    if self.quotes_ops:
      return await self.quotes_ops.update_quote(quote_id, update_data)
    return False

  async def get_quote(self, quote_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a quote by ID."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quote(quote_id)
    return None

  async def get_quotes_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves quotes for a specific contact."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quotes_by_contact(contact_id, limit)
    return []

  async def get_quote_stats(self) -> Dict[str, int]:
    """Retrieves statistics about quotes."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quote_stats()
    return {"total_quotes": 0}

  # === Quote Pagination Methods ===
  async def get_recent_quotes(self, limit: int = 10, offset: int = 0):
    """Get recent quotes ordered by creation date (newest first)."""
    if self.quotes_ops:
      return await self.quotes_ops.get_recent_quotes(limit, offset)
    return []

  async def get_oldest_quotes(self, limit: int = 10, offset: int = 0):
    """Get oldest quotes ordered by creation date (oldest first)."""
    if self.quotes_ops:
      return await self.quotes_ops.get_oldest_quotes(limit, offset)
    return []

  async def get_quotes_by_value(self, limit: int = 10, offset: int = 0, ascending: bool = True):
    """Get quotes ordered by total amount."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quotes_by_value(limit, offset, ascending)
    return []

  async def get_quotes_by_status(self, status, limit: int = 10, offset: int = 0):
    """Get quotes filtered by status."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quotes_by_status(status, limit, offset)
    return []

  async def get_quotes_by_product_type(self, product_type: str, limit: int = 10, offset: int = 0):
    """Get quotes filtered by product type."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quotes_by_product_type(product_type, limit, offset)
    return []

  async def get_quote_by_id(self, quote_id: str):
    """Get a single quote by ID."""
    if self.quotes_ops:
      return await self.quotes_ops.get_quote_by_id(quote_id)
    return None

  async def count_quotes(self) -> int:
    """Count total quotes."""
    if self.quotes_ops:
      return await self.quotes_ops.count_quotes()
    return 0

  async def count_quotes_by_status(self, status) -> int:
    """Count quotes by status."""
    if self.quotes_ops:
      return await self.quotes_ops.count_quotes_by_status(status)
    return 0

  async def count_quotes_by_product_type(self, product_type: str) -> int:
    """Count quotes by product type."""
    if self.quotes_ops:
      return await self.quotes_ops.count_quotes_by_product_type(product_type)
    return 0

  # === Calls Operations ===
  async def create_call(self, call_data: Dict[str, Any]) -> Optional[str]:
    """Creates a new call document."""
    if self.calls_ops:
      return await self.calls_ops.create_call(call_data)
    return None

  async def update_call(self, call_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates an existing call document."""
    if self.calls_ops:
      return await self.calls_ops.update_call(call_id, update_data)
    return False

  async def get_call(self, call_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a call by ID."""
    if self.calls_ops:
      return await self.calls_ops.get_call(call_id)
    return None

  async def get_call_by_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent call for a contact."""
    if self.calls_ops:
      return await self.calls_ops.get_call_by_contact(contact_id)
    return None

  async def get_calls_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves calls for a specific contact."""
    if self.calls_ops:
      return await self.calls_ops.get_calls_by_contact(contact_id, limit)
    return []

  async def get_call_stats(self) -> Dict[str, int]:
    """Retrieves statistics about calls."""
    if self.calls_ops:
      return await self.calls_ops.get_call_stats()
    return {"total_calls": 0}

  # === Calls Pagination Methods ===
  async def get_recent_calls(self, limit: int = 10, offset: int = 0):
    """Get recent calls ordered by creation date (newest first)."""
    if self.calls_ops:
      return await self.calls_ops.get_recent_calls(limit, offset)
    return []

  async def get_oldest_calls(self, limit: int = 10, offset: int = 0):
    """Get oldest calls ordered by creation date (oldest first)."""
    if self.calls_ops:
      return await self.calls_ops.get_oldest_calls(limit, offset)
    return []

  async def get_calls_by_status(self, status, limit: int = 10, offset: int = 0):
    """Get calls filtered by status."""
    if self.calls_ops:
      return await self.calls_ops.get_calls_by_status(status, limit, offset)
    return []

  async def get_calls_by_duration(self, limit: int = 10, offset: int = 0, ascending: bool = True):
    """Get calls ordered by duration."""
    if self.calls_ops:
      return await self.calls_ops.get_calls_by_duration(limit, offset, ascending)
    return []

  async def get_calls_by_source(self, source: str, limit: int = 10, offset: int = 0):
    """Get calls filtered by source."""
    if self.calls_ops:
      return await self.calls_ops.get_calls_by_source(source, limit, offset)
    return []

  async def get_call_by_id(self, call_id: str):
    """Get a single call by ID."""
    if self.calls_ops:
      return await self.calls_ops.get_call_by_id(call_id)
    return None

  async def count_calls(self) -> int:
    """Count total calls."""
    if self.calls_ops:
      return await self.calls_ops.count_calls()
    return 0

  async def count_calls_by_status(self, status) -> int:
    """Count calls by status."""
    if self.calls_ops:
      return await self.calls_ops.count_calls_by_status(status)
    return 0

  async def count_calls_by_source(self, source: str) -> int:
    """Count calls by source."""
    if self.calls_ops:
      return await self.calls_ops.count_calls_by_source(source)
    return 0

  # === Classify Operations ===
  async def create_classify(self, classify_data: Dict[str, Any]) -> Optional[str]:
    """Creates a new classification document."""
    if self.classify_ops:
      return await self.classify_ops.create_classify(classify_data)
    return None

  async def update_classify(self, classify_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates an existing classification document."""
    if self.classify_ops:
      return await self.classify_ops.update_classify(classify_id, update_data)
    return False

  async def get_classify(self, classify_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a classification by ID."""
    if self.classify_ops:
      return await self.classify_ops.get_classify(classify_id)
    return None

  async def get_classify_by_contact(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the most recent classification for a contact."""
    if self.classify_ops:
      return await self.classify_ops.get_classify_by_contact(contact_id)
    return None

  async def get_classifications_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves classifications for a specific contact."""
    if self.classify_ops:
      return await self.classify_ops.get_classifications_by_contact(contact_id, limit)
    return []

  async def get_classifications_requiring_review(self, limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves classifications that require human review."""
    if self.classify_ops:
      return await self.classify_ops.get_classifications_requiring_review(limit)
    return []

  async def get_classify_stats(self) -> Dict[str, int]:
    """Retrieves statistics about classifications."""
    if self.classify_ops:
      return await self.classify_ops.get_classify_stats()
    return {"total_classifications": 0}

  # === Classify Pagination Operations ===
  async def get_recent_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves recent classifications with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_recent_classifications(offset)
    return []

  async def get_oldest_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves oldest classifications with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_oldest_classifications(offset)
    return []

  async def get_successful_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves successful classifications with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_successful_classifications(offset)
    return []

  async def get_failed_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves failed classifications with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_failed_classifications(offset)
    return []

  async def get_disqualified_classifications(self, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves disqualified classifications with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_disqualified_classifications(offset)
    return []

  async def get_classifications_by_lead_type(self, lead_type: str, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves classifications by lead type with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_classifications_by_lead_type(lead_type, offset)
    return []

  async def get_classifications_by_confidence(self, min_confidence: float, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves classifications by confidence level with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_classifications_by_confidence(min_confidence, offset)
    return []

  async def get_classifications_by_source(self, source: str, offset: int = 0) -> List[ClassifyDocument]:
    """Retrieves classifications by source with pagination."""
    if self.classify_ops:
      return await self.classify_ops.get_classifications_by_source(source, offset)
    return []

  async def get_classification_by_id(self, classification_id: str) -> Optional[ClassifyDocument]:
    """Retrieves a single classification by ID."""
    if self.classify_ops:
      return await self.classify_ops.get_classification_by_id(classification_id)
    return None

  async def count_all_classifications(self) -> int:
    """Counts all classifications."""
    if self.classify_ops:
      return await self.classify_ops.count_all_classifications()
    return 0

  async def count_classifications_by_status(self, status: str) -> int:
    """Counts classifications by status."""
    if self.classify_ops:
      # Convert string to ClassifyStatus enum
      try:
        status_enum = ClassifyStatus(status)
        return await self.classify_ops.count_classifications_by_status(status_enum)
      except ValueError:
        return 0
    return 0

  async def count_classifications_by_lead_type(self, lead_type: str) -> int:
    """Counts classifications by lead type."""
    if self.classify_ops:
      return await self.classify_ops.count_classifications_by_lead_type(lead_type)
    return 0

  async def count_classifications_by_confidence(self, min_confidence: float) -> int:
    """Counts classifications by confidence level."""
    if self.classify_ops:
      return await self.classify_ops.count_classifications_by_confidence(min_confidence)
    return 0

  async def count_classifications_by_source(self, source: str) -> int:
    """Counts classifications by source."""
    if self.classify_ops:
      return await self.classify_ops.count_classifications_by_source(source)
    return 0

  # === Location Operations ===
  async def create_location(self, location_data: Dict[str, Any]) -> Optional[str]:
    """Creates a new location document."""
    if self.location_ops:
      return await self.location_ops.create_location(location_data)
    return None

  async def update_location(self, location_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates an existing location document."""
    if self.location_ops:
      return await self.location_ops.update_location(location_id, update_data)
    return False

  async def get_location(self, location_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a location by ID."""
    if self.location_ops:
      return await self.location_ops.get_location(location_id)
    return None

  async def get_location_by_address(self, delivery_location: str) -> Optional[Dict[str, Any]]:
    """Retrieves a location by delivery address."""
    if self.location_ops:
      return await self.location_ops.get_location_by_address(delivery_location)
    return None

  async def get_locations_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves locations for a specific contact."""
    if self.location_ops:
      return await self.location_ops.get_locations_by_contact(contact_id, limit)
    return []

  async def get_location_stats(self) -> Dict[str, int]:
    """Retrieves statistics about locations."""
    if self.location_ops:
      return await self.location_ops.get_location_stats()
    return {"total_locations": 0}

  # === Location Pagination Operations ===
  async def get_recent_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Retrieves recent locations with pagination."""
    if self.location_ops:
      return await self.location_ops.get_recent_locations(offset)
    return []

  async def get_oldest_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Retrieves oldest locations with pagination."""
    if self.location_ops:
      return await self.location_ops.get_oldest_locations(offset)
    return []

  async def get_successful_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Retrieves successful locations with pagination."""
    if self.location_ops:
      return await self.location_ops.get_successful_locations(offset)
    return []

  async def get_failed_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Retrieves failed locations with pagination."""
    if self.location_ops:
      return await self.location_ops.get_failed_locations(offset)
    return []

  async def get_pending_locations(self, offset: int = 0) -> List[LocationDocument]:
    """Retrieves pending locations with pagination."""
    if self.location_ops:
      return await self.location_ops.get_pending_locations(offset)
    return []

  async def get_locations_by_distance(self, ascending: bool = True, offset: int = 0) -> List[LocationDocument]:
    """Retrieves locations sorted by distance with pagination."""
    if self.location_ops:
      return await self.location_ops.get_locations_by_distance(ascending, offset)
    return []

  async def get_locations_by_branch(self, branch: str, offset: int = 0) -> List[LocationDocument]:
    """Retrieves locations by branch with pagination."""
    if self.location_ops:
      return await self.location_ops.get_locations_by_branch(branch, offset)
    return []

  async def get_locations_with_fallback(self, offset: int = 0) -> List[LocationDocument]:
    """Retrieves locations that used fallback method with pagination."""
    if self.location_ops:
      return await self.location_ops.get_locations_with_fallback(offset)
    return []

  async def get_location_by_id(self, location_id: str) -> Optional[LocationDocument]:
    """Retrieves a single location by ID."""
    if self.location_ops:
      return await self.location_ops.get_location_by_id(location_id)
    return None

  async def count_all_locations(self) -> int:
    """Counts all locations."""
    if self.location_ops:
      return await self.location_ops.count_all_locations()
    return 0

  async def count_locations_by_status(self, status: str) -> int:
    """Counts locations by status."""
    if self.location_ops:
      return await self.location_ops.count_locations_by_status(status)
    return 0

  async def count_locations_by_branch(self, branch: str) -> int:
    """Counts locations by branch."""
    if self.location_ops:
      return await self.location_ops.count_locations_by_branch(branch)
    return 0

  async def count_locations_with_fallback(self) -> int:
    """Counts locations that used fallback method."""
    if self.location_ops:
      return await self.location_ops.count_locations_with_fallback()
    return 0

  # === Emails Operations ===
  async def create_email(self, email_data: Dict[str, Any]) -> Optional[str]:
    """Creates a new email document."""
    if self.emails_ops:
      return await self.emails_ops.create_email(email_data)
    return None

  async def update_email(self, email_id: str, update_data: Dict[str, Any]) -> bool:
    """Updates an existing email document."""
    if self.emails_ops:
      return await self.emails_ops.update_email(email_id, update_data)
    return False

  async def get_email(self, email_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an email by ID."""
    if self.emails_ops:
      return await self.emails_ops.get_email(email_id)
    return None

  async def get_email_by_message_id(self, message_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an email by message ID."""
    if self.emails_ops:
      return await self.emails_ops.get_email_by_message_id(message_id)
    return None

  async def get_emails_by_contact(self, contact_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves emails for a specific contact."""
    if self.emails_ops:
      return await self.emails_ops.get_emails_by_contact(contact_id, limit)
    return []

  async def get_emails_by_thread(self, thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves emails in a specific thread."""
    if self.emails_ops:
      return await self.emails_ops.get_emails_by_thread(thread_id, limit)
    return []

  async def get_email_stats(self) -> Dict[str, int]:
    """Retrieves statistics about emails."""
    if self.emails_ops:
      return await self.emails_ops.get_email_stats()
    return {"total_emails": 0}

  async def compose_email_for_n8n(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
    """Composes an email document for n8n sending."""
    if self.emails_ops:
      return await self.emails_ops.compose_email_for_n8n(email_data)
    return {}

  # === Emails Pagination Operations ===
  async def get_recent_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves recent emails with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_recent_emails(offset)
    return []

  async def get_oldest_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves oldest emails with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_oldest_emails(offset)
    return []

  async def get_successful_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves successful emails with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_successful_emails(offset)
    return []

  async def get_failed_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves failed emails with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_failed_emails(offset)
    return []

  async def get_pending_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves pending emails with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_pending_emails(offset)
    return []

  async def get_emails_by_category(self, category: str, offset: int = 0) -> List[EmailDocument]:
    """Retrieves emails by category with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_emails_by_category(category, offset)
    return []

  async def get_emails_by_direction(self, direction: str, offset: int = 0) -> List[EmailDocument]:
    """Retrieves emails by direction with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_emails_by_direction(direction, offset)
    return []

  async def get_emails_with_attachments(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves emails with attachments with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_emails_with_attachments(offset)
    return []

  async def get_processed_emails(self, offset: int = 0) -> List[EmailDocument]:
    """Retrieves processed emails with pagination."""
    if self.emails_ops:
      return await self.emails_ops.get_processed_emails(offset)
    return []

  async def get_email_by_id(self, email_id: str) -> Optional[EmailDocument]:
    """Retrieves a single email by ID."""
    if self.emails_ops:
      return await self.emails_ops.get_email_by_id(email_id)
    return None

  async def count_all_emails(self) -> int:
    """Counts all emails."""
    if self.emails_ops:
      return await self.emails_ops.count_all_emails()
    return 0

  async def count_emails_by_status(self, status: str) -> int:
    """Counts emails by status."""
    if self.emails_ops:
      return await self.emails_ops.count_emails_by_status(status)
    return 0

  async def count_emails_by_category(self, category: str) -> int:
    """Counts emails by category."""
    if self.emails_ops:
      return await self.emails_ops.count_emails_by_category(category)
    return 0

  async def count_emails_by_direction(self, direction: str) -> int:
    """Counts emails by direction."""
    if self.emails_ops:
      return await self.emails_ops.count_emails_by_direction(direction)
    return 0

  async def count_emails_with_attachments(self) -> int:
    """Counts emails with attachments."""
    if self.emails_ops:
      return await self.emails_ops.count_emails_with_attachments()
    return 0

  async def count_processed_emails(self) -> int:
    """Counts processed emails."""
    if self.emails_ops:
      return await self.emails_ops.count_processed_emails()
    return 0
