# filepath: app/services/mongo/connection/indexes.py
import logfire
from pymongo import ASCENDING, DESCENDING
from app.services.mongo.collections.names import *


class IndexManager:
  """Manages MongoDB index creation."""

  def __init__(self, db):
    self.db = db

  async def create_indexes(self):
    """Creates necessary indexes in MongoDB collections if they don't exist."""
    logfire.info("Attempting to create MongoDB indexes...")
    if self.db is None:
      logfire.error(
          "Cannot create indexes, MongoDB database is not initialized."
      )
      return

    try:
      await self._create_users_indexes()
      await self._create_reports_indexes()
      await self._create_sheet_indexes()
      await self._create_bland_indexes()
      await self._create_error_indexes()
      await self._create_service_status_indexes()
      await self._create_stats_indexes()
      # New collections
      await self._create_quotes_indexes()
      await self._create_calls_indexes()
      await self._create_classify_indexes()
      await self._create_location_indexes()
      await self._create_emails_indexes()
    except Exception as e:
      logfire.error(f"Error creating MongoDB indexes: {e}", exc_info=True)

  async def _create_users_indexes(self):
    """Creates indexes for users collection."""
    users_collection = self.db[USERS_COLLECTION]
    await users_collection.create_index(
        [("email", ASCENDING)], unique=True, name="email_unique_idx"
    )
    logfire.info(
        f"Index 'email_unique_idx' ensured for collection '{USERS_COLLECTION}'."
    )

  async def _create_reports_indexes(self):
    """Creates indexes for reports collection."""
    reports_collection = self.db[REPORTS_COLLECTION]
    await reports_collection.create_index(
        [("timestamp", DESCENDING)], name="timestamp_desc_idx"
    )
    logfire.info(
        f"Index 'timestamp_desc_idx' ensured for collection '{REPORTS_COLLECTION}'."
    )

  async def _create_sheet_indexes(self):
    """Creates indexes for sheet sync collections."""
    # Products
    sheet_products_coll = self.db[SHEET_PRODUCTS_COLLECTION]
    await sheet_products_coll.create_index(
        [("id", ASCENDING)], unique=True, name="sheet_product_id_unique_idx"
    )
    logfire.info(
        f"Index 'sheet_product_id_unique_idx' ensured for collection '{SHEET_PRODUCTS_COLLECTION}'."
    )

    # Generators
    sheet_generators_coll = self.db[SHEET_GENERATORS_COLLECTION]
    await sheet_generators_coll.create_index(
        [("id", ASCENDING)], unique=True, name="sheet_generator_id_unique_idx"
    )
    logfire.info(
        f"Index 'sheet_generator_id_unique_idx' ensured for collection '{SHEET_GENERATORS_COLLECTION}'."
    )

    # Branches
    sheet_branches_coll = self.db[SHEET_BRANCHES_COLLECTION]
    await sheet_branches_coll.create_index(
        [("address", ASCENDING)],
        unique=True,
        name="sheet_branch_address_unique_idx",
    )
    logfire.info(
        f"Index 'sheet_branch_address_unique_idx' ensured for collection '{SHEET_BRANCHES_COLLECTION}'."
    )

    # Config
    sheet_config_coll = self.db[SHEET_CONFIG_COLLECTION]
    await sheet_config_coll.create_index(
        [("config_type", ASCENDING)],
        unique=True,
        name="sheet_config_type_unique_idx",
        sparse=True,
    )
    logfire.info(
        f"Index 'sheet_config_type_unique_idx' (sparse) ensured for collection '{SHEET_CONFIG_COLLECTION}'."
    )

    # States
    sheet_states_coll = self.db[SHEET_STATES_COLLECTION]
    await sheet_states_coll.create_index(
        [("code", ASCENDING)], unique=True, name="sheet_state_code_unique_idx"
    )
    logfire.info(
        f"Index 'sheet_state_code_unique_idx' ensured for collection '{SHEET_STATES_COLLECTION}'."
    )

  async def _create_bland_indexes(self):
    """Creates indexes for Bland Call Logs."""
    bland_logs_coll = self.db[BLAND_CALL_LOGS_COLLECTION]

    await bland_logs_coll.create_index(
        [("status", ASCENDING)], name="bland_call_log_status_idx"
    )
    await bland_logs_coll.create_index(
        [("created_at", DESCENDING)], name="bland_call_log_created_at_idx"
    )
    await bland_logs_coll.create_index(
        [("phone_number", ASCENDING)],
        name="bland_call_log_phone_idx",
        sparse=True,
    )
    await bland_logs_coll.create_index(
        [("call_id_bland", ASCENDING)],
        name="bland_call_log_bland_call_id_idx",
        sparse=True,
    )
    logfire.info(
        f"Indexes ensured for collection '{BLAND_CALL_LOGS_COLLECTION}'."
    )

  async def _create_error_indexes(self):
    """Creates indexes for Error Logs."""
    error_logs_coll = self.db[ERROR_LOGS_COLLECTION]
    await error_logs_coll.create_index(
        [("timestamp", DESCENDING)], name="error_log_timestamp_idx"
    )
    await error_logs_coll.create_index(
        [("service_name", ASCENDING)], name="error_log_service_name_idx"
    )
    await error_logs_coll.create_index(
        [("error_type", ASCENDING)], name="error_log_error_type_idx"
    )
    logfire.info(
        f"Indexes ensured for collection '{ERROR_LOGS_COLLECTION}'."
    )

  async def _create_service_status_indexes(self):
    """Creates indexes for Service Status."""
    service_status_coll = self.db[SERVICE_STATUS_COLLECTION]
    await service_status_coll.create_index(
        [("timestamp", DESCENDING)], name="service_status_timestamp_idx"
    )
    await service_status_coll.create_index(
        [("service_name", ASCENDING), ("timestamp", DESCENDING)],
        name="service_status_name_timestamp_idx",
    )
    logfire.info(
        f"Indexes ensured for collection '{SERVICE_STATUS_COLLECTION}'."
    )

  async def _create_stats_indexes(self):
    """Creates indexes for stats collection."""
    stats_collection = self.db[STATS_COLLECTION]
    await stats_collection.create_index([("_id", ASCENDING)], name="stats_id_idx")
    logfire.info(
        f"Index 'stats_id_idx' ensured for collection '{STATS_COLLECTION}'."
    )

  async def _create_quotes_indexes(self):
    """Creates indexes for quotes collection."""
    quotes_collection = self.db[QUOTES_COLLECTION]

    await quotes_collection.create_index(
        [("contact_id", ASCENDING)], name="quotes_contact_id_idx", sparse=True
    )
    await quotes_collection.create_index(
        [("status", ASCENDING)], name="quotes_status_idx"
    )
    await quotes_collection.create_index(
        [("created_at", DESCENDING)], name="quotes_created_at_idx"
    )
    await quotes_collection.create_index(
        [("total_amount", ASCENDING)], name="quotes_total_amount_idx", sparse=True
    )
    await quotes_collection.create_index(
        [("valid_until", ASCENDING)], name="quotes_valid_until_idx", sparse=True
    )

    logfire.info(f"Indexes ensured for collection '{QUOTES_COLLECTION}'.")

  async def _create_calls_indexes(self):
    """Creates indexes for calls collection."""
    calls_collection = self.db[CALLS_COLLECTION]

    await calls_collection.create_index(
        [("contact_id", ASCENDING)], name="calls_contact_id_idx", sparse=True
    )
    await calls_collection.create_index(
        [("status", ASCENDING)], name="calls_status_idx"
    )
    await calls_collection.create_index(
        [("created_at", DESCENDING)], name="calls_created_at_idx"
    )
    await calls_collection.create_index(
        [("phone_number", ASCENDING)], name="calls_phone_number_idx"
    )
    await calls_collection.create_index(
        [("call_id_bland", ASCENDING)], name="calls_bland_id_idx", sparse=True
    )

    logfire.info(f"Indexes ensured for collection '{CALLS_COLLECTION}'.")

  async def _create_classify_indexes(self):
    """Creates indexes for classify collection."""
    classify_collection = self.db[CLASSIFY_COLLECTION]

    await classify_collection.create_index(
        [("contact_id", ASCENDING)], name="classify_contact_id_idx", sparse=True
    )
    await classify_collection.create_index(
        [("status", ASCENDING)], name="classify_status_idx"
    )
    await classify_collection.create_index(
        [("lead_type", ASCENDING)], name="classify_lead_type_idx", sparse=True
    )
    await classify_collection.create_index(
        [("requires_human_review", ASCENDING)], name="classify_requires_review_idx"
    )
    await classify_collection.create_index(
        [("created_at", DESCENDING)], name="classify_created_at_idx"
    )
    await classify_collection.create_index(
        [("source", ASCENDING)], name="classify_source_idx"
    )

    logfire.info(f"Indexes ensured for collection '{CLASSIFY_COLLECTION}'.")

  async def _create_location_indexes(self):
    """Creates indexes for location collection."""
    location_collection = self.db[LOCATION_COLLECTION]

    await location_collection.create_index(
        [("contact_id", ASCENDING)], name="location_contact_id_idx", sparse=True
    )
    await location_collection.create_index(
        [("status", ASCENDING)], name="location_status_idx"
    )
    await location_collection.create_index(
        [("delivery_location", ASCENDING)], name="location_delivery_location_idx"
    )
    await location_collection.create_index(
        [("within_service_area", ASCENDING)], name="location_within_service_area_idx", sparse=True
    )
    await location_collection.create_index(
        [("created_at", DESCENDING)], name="location_created_at_idx"
    )

    logfire.info(f"Indexes ensured for collection '{LOCATION_COLLECTION}'.")

  async def _create_emails_indexes(self):
    """Creates indexes for emails collection."""
    emails_collection = self.db[EMAILS_COLLECTION]

    await emails_collection.create_index(
        [("contact_id", ASCENDING)], name="emails_contact_id_idx", sparse=True
    )
    await emails_collection.create_index(
        [("category", ASCENDING)], name="emails_category_idx"
    )
    await emails_collection.create_index(
        [("status", ASCENDING)], name="emails_status_idx"
    )
    await emails_collection.create_index(
        [("direction", ASCENDING)], name="emails_direction_idx"
    )
    await emails_collection.create_index(
        [("message_id", ASCENDING)], name="emails_message_id_idx", sparse=True
    )
    await emails_collection.create_index(
        [("thread_id", ASCENDING)], name="emails_thread_id_idx", sparse=True
    )
    await emails_collection.create_index(
        [("created_at", DESCENDING)], name="emails_created_at_idx"
    )
    await emails_collection.create_index(
        [("from_email", ASCENDING)], name="emails_from_email_idx", sparse=True
    )

    logfire.info(f"Indexes ensured for collection '{EMAILS_COLLECTION}'.")
