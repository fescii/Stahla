# filepath: app/services/mongo/service.py
import logfire
from app.services.mongo.connection import MongoConnection, IndexManager
from app.services.mongo.stats import StatsOperations
from app.services.mongo.reports import ReportsOperations
from app.services.mongo.bland import BlandOperations, BlandUpdates
from app.services.mongo.errors import ErrorOperations
from app.services.mongo.sheets import SheetsOperations
from typing import Optional, Dict, Any, List, Union, Tuple
from datetime import datetime, timezone
from app.models.blandlog import BlandCallStatus


class MongoService:
  """Main MongoDB service class that composes all operations."""

  def __init__(self):
    self.connection = MongoConnection()
    # Operations will be initialized after connection is established
    self.stats_ops: Optional[StatsOperations] = None
    self.reports_ops: Optional[ReportsOperations] = None
    self.bland_ops: Optional[BlandOperations] = None
    self.bland_updates: Optional[BlandUpdates] = None
    self.error_ops: Optional[ErrorOperations] = None
    self.sheets_ops: Optional[SheetsOperations] = None
    self.index_manager: Optional[IndexManager] = None

  async def connect_and_initialize(self):
    """Connects to MongoDB and initializes all operation classes."""
    await self.connection.connect_and_initialize()

    # Initialize all operation classes with the database instance
    db = await self.connection.get_db()
    self.stats_ops = StatsOperations(db)
    self.reports_ops = ReportsOperations(db)
    self.bland_ops = BlandOperations(db)
    self.bland_updates = BlandUpdates(db)
    self.error_ops = ErrorOperations(db)
    self.sheets_ops = SheetsOperations(db)
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

  # === Bland Operations ===
  async def get_bland_calls(
      self,
      page: int,
      page_size: int,
      status_filter: Optional[str],
      sort_field: str,
      sort_order: int,
  ) -> Tuple[List[Dict[str, Any]], int]:
    """Retrieves a paginated list of Bland call logs."""
    if self.bland_ops:
      return await self.bland_ops.get_bland_calls(page, page_size, status_filter, sort_field, sort_order)
    return [], 0

  async def get_bland_call_log(self, contact_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single Bland call log by contact_id."""
    if self.bland_ops:
      return await self.bland_ops.get_bland_call_log(contact_id)
    return None

  async def get_bland_call_stats(self) -> Dict[str, int]:
    """Retrieves statistics about Bland call logs."""
    if self.bland_ops:
      return await self.bland_ops.get_bland_call_stats()
    return {}

  # === Bland Update Operations ===
  async def update_bland_call_log_internal(
      self,
      contact_id: str,
      update_data: Dict[str, Any]
  ) -> bool:
    """Updates a Bland call log document in MongoDB."""
    if self.bland_updates:
      return await self.bland_updates.update_bland_call_log_internal(contact_id, update_data)
    return False

  async def update_bland_call_log_completion(
      self,
      contact_id: str,
      call_id_bland: str,
      status: BlandCallStatus,
      transcript_payload: List[Dict[str, Any]],
      summary_text: Optional[str] = None,
      classification_payload: Optional[Dict[str, Any]] = None,
      full_webhook_payload: Optional[Dict[str, Any]] = None,
      call_completed_timestamp: Optional[datetime] = None,
      bland_processing_result_payload: Optional[Dict[str, Any]] = None,
      processing_status_message: Optional[str] = None
  ) -> bool:
    """Updates a Bland call log with completion data."""
    if self.bland_updates:
      return await self.bland_updates.update_bland_call_log_completion(
          contact_id, call_id_bland, status, transcript_payload,
          summary_text, classification_payload, full_webhook_payload,
          call_completed_timestamp, bland_processing_result_payload,
          processing_status_message
      )
    return False

  async def log_bland_call_attempt(
      self,
      contact_id: str,
      phone_number: str,
      task: Optional[str] = None,
      pathway_id_used: Optional[str] = None,
      initial_status: BlandCallStatus = BlandCallStatus.PENDING,
      call_id_bland: Optional[str] = None,
      retry_of_call_id: Optional[str] = None,
      retry_reason: Optional[str] = None,
      voice_id: Optional[str] = None,
      webhook_url: Optional[str] = None,
      max_duration: Optional[int] = 12,
      request_data_variables: Optional[Dict[str, Any]] = None,
      transfer_phone_number: Optional[str] = None
  ) -> bool:
    """Logs an initial Bland.ai call attempt to MongoDB."""
    if self.bland_updates:
      return await self.bland_updates.log_bland_call_attempt(
          contact_id, phone_number, task, pathway_id_used, initial_status,
          call_id_bland, retry_of_call_id, retry_reason, voice_id,
          webhook_url, max_duration, request_data_variables, transfer_phone_number
      )
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
