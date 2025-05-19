<!-- filepath: /docs/services.md -->

# Application Services and Utilities

This document outlines the various services and utility modules used within the Stahla AI SDR application. These components handle core business logic, interactions with external APIs, and data processing.

## Services (`app/services/`)

This section details the main service classes responsible for specific domains of functionality.

### 1. Bland AI Service (`app/services/bland.py`)

- **Class:** `BlandAIManager`
- **Purpose:** Manages all interactions with the Bland.ai API. This includes initiating voice calls, managing call pathways, and synchronizing tool definitions (like location and quote tools) with Bland.ai.
- **Key Responsibilities:**
  - Loading call pathway definitions from local JSON files (`app/assets/call.json`).
  - Loading tool definitions for location and quoting from local JSON files (`app/assets/location.json`, `app/assets/quote.json`).
  - Synchronizing pathways and tools with Bland.ai by updating existing configurations or creating new ones if necessary. This involves using `BLAND_PATHWAY_ID`, `BLAND_LOCATION_TOOL_ID`, and `BLAND_QUOTE_TOOL_ID` from settings.
  - Initiating outbound calls via the Bland.ai API (`POST /v1/calls`).
  - Making HTTP requests to the Bland.ai API using an `httpx.AsyncClient`.
  - Logging call events, API interactions, and errors, potentially to a MongoDB instance if configured.
  - Checking the connection status to the Bland.ai API.
- **Initialization:**
  - Requires a Bland.ai API key, base URL, and optionally a pathway ID, MongoService instance, and BackgroundTasks instance.
- **Core Methods:**
  - `_load_pathway_definition()`: Loads the call pathway from `app/assets/call.json`.
  - `_load_location_tool_definition()`: Loads the location tool definition from `app/assets/location.json`.
  - `_load_quote_tool_definition()`: Loads the quote tool definition from `app/assets/quote.json`.
  - `_sync_pathway()`: Updates the specified Bland.ai pathway with the loaded definition.
  - `_sync_location_tool()`: Updates the specified Bland.ai location tool.
  - `_sync_quote_tool()`: Updates the specified Bland.ai quote tool.
  - `_sync_bland()`: Performs all synchronization tasks for pathway and tools.
  - `initiate_callback(request: BlandCallbackRequest, contact_id: str, background_tasks: BackgroundTasks)`: Initiates a call. (Method signature inferred from typical usage, actual parameters might vary based on endpoint definitions).
  - `process_webhook_data(payload: BlandWebhookPayload)`: Processes incoming webhook data from Bland.ai after a call. (Method signature inferred).
  - `_make_request()`: A helper to execute HTTP requests to the Bland.ai API, handling responses and errors.
  - `check_connection()`: Verifies connectivity with the Bland.ai API.
  - `close()`: Closes the underlying `httpx.AsyncClient`.

### 2. Email Service (`app/services/email.py`)

- **Class:** `EmailManager`
- **Purpose:** Handles the processing of incoming emails, including parsing content, extracting relevant data, checking for completeness, and managing automated replies. It also facilitates sending handoff notifications to sales teams.
- **Key Responsibilities:**
  - Parsing email subject and body (text and HTML) to extract structured data (e.g., contact info, product interest, event details).
  - Utilizing regex patterns for initial data extraction.
  - Optionally using an LLM (e.g., Marvin via `MARVIN_API_KEY`) for more advanced data extraction from email content if configured (`LLM_PROVIDER`).
  - Checking the completeness of extracted data against predefined required and desired fields.
  - Sending automated email replies to request missing information if the initial data is incomplete and email sending is enabled (`EMAIL_SENDING_ENABLED`).
  - Sending handoff notification emails to internal teams (e.g., sales) after a lead has been classified and processed in HubSpot. The recipient team is determined by the lead classification type.
- **Initialization:**
  - Initializes an `httpx.AsyncClient` for potential external email sending or API interactions.
- **Core Methods:**
  - `_extract_data_with_llm(payload: EmailWebhookPayload)`: Uses an LLM to extract structured data from email content.
  - `_parse_email_content(payload: EmailWebhookPayload)`: Parses email content using regex and basic logic.
  - `_check_email_data_completeness(extracted_data: Dict[str, Any])`: Checks if extracted data meets minimum requirements.
  - `_send_auto_reply(original_payload: EmailWebhookPayload, missing_fields: List[str], extracted_data: Dict[str, Any])`: Sends an email requesting missing information.
  - `send_handoff_notification(classification_result: ClassificationResult, contact_result: Optional[HubSpotContactResult], lead_result: Optional[HubSpotApiResult])`: Sends a notification email to the appropriate team.
  - `process_incoming_email(payload: EmailWebhookPayload)`: Main entry point to process an email. It orchestrates parsing, LLM enhancement (if applicable), completeness checks, and auto-replies.
  - `close_client()` / `close()`: Closes the `httpx.AsyncClient`.

### 3. HubSpot Service (`app/services/hubspot.py`)

- **Class:** `HubSpotManager`
- **Purpose:** Manages all interactions with the HubSpot CRM API. This includes creating, reading, updating, and deleting (archiving) HubSpot objects like Contacts, Companies, Deals, and Tickets. It also handles associations between these objects and manages pipeline/stage lookups.
- **Key Responsibilities:**
  - CRUD operations for Contacts, Companies, Deals, and Tickets.
  - Searching HubSpot objects using various criteria.
  - Managing associations between different HubSpot objects (e.g., associating a Contact with a Company, a Deal with a Contact).
  - Fetching HubSpot owners, pipelines, and pipeline stages, with caching mechanisms (`TTLCache`) to improve performance and reduce API calls.
  - Converting date strings to HubSpot-compatible millisecond timestamps (normalized to midnight UTC).
  - Handling HubSpot API errors gracefully and logging them.
- **Initialization:**
  - Requires a HubSpot Access Token (`HUBSPOT_ACCESS_TOKEN` from settings).
  - Initializes the official HubSpot Python SDK client.
  - Configures caches for pipelines, stages, and owners with TTLs defined in settings.
  - Loads various association type IDs from settings (e.g., `HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_CONTACT`).
- **Core Methods (Object-Specific):**
  - **Contacts:** `create_contact`, `get_contact`, `update_contact`, `delete_contact` (archives), `create_or_update_contact` (searches by email then creates/updates).
  - **Companies:** `create_company`, `get_company`, `update_company`, `delete_company` (archives), `create_or_update_company` (searches by domain then creates/updates).
  - **Deals:** `create_deal`, `get_deal`, `update_deal`, `delete_deal` (archives).
  - **Tickets:** `create_ticket`, `get_ticket`, `update_ticket`, `delete_ticket` (archives).
  - **Generic Search:** `search_objects(object_type: str, search_request: HubSpotSearchRequest)` for contacts, companies, deals, tickets.
- **Core Methods (Associations):**
  - `associate_objects(from_object_type: str, from_object_id: str, to_object_type: str, to_object_id: str, association_type: Union[str, int])`: Creates an association.
  - `batch_associate_objects(...)`: Creates multiple associations in a batch.
  - Specific association helpers like `associate_contact_to_company`, `associate_deal_to_contact`, etc.
- **Core Methods (Pipelines, Stages, Owners):**
  - `get_pipelines(object_type: Literal["deal", "ticket"])`: Fetches all pipelines for deals or tickets, uses caching.
  - `get_pipeline_id(object_type: Literal["deal", "ticket"], pipeline_name: str)`: Gets a specific pipeline ID by name.
  - `get_pipeline_stages(object_type: Literal["deal", "ticket"], pipeline_id: str)`: Fetches stages for a pipeline, uses caching.
  - `get_stage_id(object_type: Literal["deal", "ticket"], pipeline_name: str, stage_name: str)`: Gets a specific stage ID by name within a pipeline.
  - `get_owners(email: Optional[str] = None, owner_id: Optional[str] = None)`: Fetches HubSpot owners, uses caching.
  - `get_owner_id_by_email(email: str)`: Gets a specific owner's ID by their email.
- **Helper Methods:**
  - `_convert_date_to_timestamp_ms(date_str: Optional[str])`: Converts "YYYY-MM-DD" to a HubSpot timestamp.
  - `_handle_api_error(e: Exception, context: str, object_id: Optional[str] = None)`: Centralized error handler.
- **Connection Check:**
  - `check_connection()`: Verifies connectivity with the HubSpot API by attempting a simple read operation (e.g., fetching owners).

### 4. n8n Integration Service (`app/services/n8n.py`)

- **Purpose:** Facilitates sending data to an n8n (workflow automation tool) webhook. This is typically used for handoff automation after a lead has been classified and processed.
- **Key Functions:**
  - `send_to_n8n_webhook(payload: Dict[str, Any], webhook_url: Optional[str], api_key: Optional[str])`:
    - Sends the provided `payload` dictionary as JSON to the specified `webhook_url`.
    - Uses the `N8N_WEBHOOK_URL` from settings by default.
    - If an `api_key` (default from `N8N_API_KEY` in settings) is provided, it includes it in a custom header named `Stahla`.
    - Logs the interaction and handles HTTP errors.
    - Uses a shared `httpx.AsyncClient`.
  - `trigger_n8n_handoff_automation(classification_result: ClassificationResult, input_data: ClassificationInput, contact_result: Optional[HubSpotApiResult], lead_result: Optional[HubSpotApiResult])`:
    - Prepares a structured payload containing details about the lead, event, classification, call, routing, and HubSpot entities.
    - Pulls data primarily from `input_data` (which reflects call variables from Bland.ai, form submissions, etc.) and `classification_result`.
    - Includes HubSpot contact and lead IDs and URLs if available.
    - Determines the target team email list based on classification metadata.
    - Skips handoff if the lead is classified as "Disqualify".
    - Calls `send_to_n8n_webhook` to send the composed payload.
- **Client Management:**
  - `close_n8n_client()`: Closes the shared `httpx.AsyncClient`.
- **Configuration:**
  - Relies on `N8N_WEBHOOK_URL` and `N8N_API_KEY` from `app.core.config.settings`.

### 5. Authentication Service (`app/services/auth/auth.py`)

- **Purpose:** Manages authentication and authorization, primarily focusing on API key validation and potentially user management if integrated with a user database.
- **Key Responsibilities & Features:**
  - Validates API keys (e.g., passed in headers like `X-API-Key`).
  - Checks if an API key is active and possesses the required permissions for a requested operation.
  - Likely defines Pydantic models for `APIKey` (with fields like key, user_id, permissions, active status) and potentially `User`.
  - May include functions to create API keys, retrieve key details (possibly from `MongoService`), and verify keys against required permissions.
  - Could use FastAPI's `Security` utilities for dependency injection to protect endpoints (e.g., a `get_current_active_user` dependency).
  - May use libraries like `passlib` for password hashing if user credential management is involved.
- **Dependencies:** Likely `MongoService` (for storing API keys/users), FastAPI, `passlib`.

### 6. Classification Services (`app/services/classify/`)

This sub-module handles lead/interaction classification, determining the nature, urgency, and appropriate next steps based on input data.

#### 6.1. Main Classification Orchestrator (`app/services/classify/classification.py`)

- **Class:** `ClassificationService`
- **Purpose:** Orchestrates the process of classifying leads or interactions. It combines rule-based logic with potential LLM-driven analysis.
- **Key Responsibilities:**
  - Accepts `ClassificationInput` (data from calls, emails, forms).
  - Applies predefined rules from `app/services/classify/rules.py`.
  - If necessary, invokes an LLM (e.g., via `MarvinService` from `app/services/classify/marvin.py`) for more complex classification.
  - Produces a `ClassificationResult` detailing the classification type, metadata, urgency, and actions.
- **Core Methods:**
  - `classify_input(input_data: ClassificationInput)`: Main classification method.
  - `_apply_rules(input_data: ClassificationInput)`: Internal method for rule application.
  - `_invoke_llm_classification(input_data: ClassificationInput)`: Internal method for LLM interaction.
- **Dependencies:** `MarvinService`, rule definitions in `rules.py`, `ClassificationInput` and `ClassificationResult` models.

#### 6.2. Marvin AI Integration (`app/services/classify/marvin.py`)

- **Class:** `MarvinService`
- **Purpose:** Acts as an interface to the Marvin AI library/SDK, enabling the use of LLMs for tasks like classification, data extraction, and text generation.
- **Key Responsibilities:**
  - Initializes and configures the Marvin client (API keys, model selection).
  - Provides wrapper methods for Marvin's functionalities (e.g., `classify_text_with_marvin`, `extract_data_with_marvin_from_text_using_model`).
  - Manages API communication with the Marvin service, including error handling and retries.
- **Core Methods:**
  - `__init__(api_key: str, model_name: Optional[str])`: Constructor.
  - `classify_with_marvin(text_to_classify: str, categories: List[str], instructions: Optional[str])`: Classifies text.
  - `extract_data_with_marvin(text_to_extract_from: str, data_model: Type[BaseModel], instructions: Optional[str])`: Extracts structured data.
- **Dependencies:** Marvin AI library, Pydantic. Requires `MARVIN_API_KEY`.

#### 6.3. Rule Definitions (`app/services/classify/rules.py`)

- **Purpose:** Contains the specific rule-based logic used by the `ClassificationService`. This module defines functions or data structures representing individual classification rules and their conditions.
- **Key Features:**
  - A collection of functions, each implementing a specific rule by evaluating conditions on `ClassificationInput` data (e.g., checking for keywords, specific field values, patterns).
  - Rules can return partial or full `ClassificationResult` components.
  - Likely includes a mechanism (e.g., a list or pipeline) to apply these rules in a defined order or priority.
- **Dependencies:** `ClassificationInput`, `ClassificationResult` models.

### 7. Dashboard Services (`app/services/dash/`)

This sub-module provides backend logic for the application's dashboard, including data aggregation, background task management, and monitoring.

#### 7.1. Dashboard Logic (`app/services/dash/dashboard.py`)

- **Class:** `DashboardService`
- **Purpose:** Provides the core business logic for the application's dashboard. It aggregates and processes data from various sources to present key metrics, activities, and system status.
- **Key Responsibilities:**
  - Fetching data for dashboard widgets (e.g., call stats, lead conversion, error logs, HubSpot sync status).
  - Interacting with `MongoService` (application data), `HubSpotManager` (CRM data), `RedisService` (cache), `BlandAIManager` (call system status).
  - May use `app/services/dash/background.py` for pre-computed data or to trigger computations.
- **Core Methods (Examples):**
  - `get_overview_metrics()`: High-level statistics.
  - `get_recent_activity_feed()`: List of recent events.
  - `get_call_volume_trends()`: Data for charts.
  - `get_hubspot_sync_status()`: HubSpot synchronization status.
- **Dependencies:** `MongoService`, `HubSpotManager`, `RedisService`, `BlandAIManager`, `ClassificationService`, dashboard-specific data models.

#### 7.2. Background Task Management (`app/services/dash/background.py`)

- **Purpose:** Manages background tasks related to dashboard data aggregation, report generation, or other long-running processes initiated via the dashboard or system.
- **Key Features:**
  - May define a `DashboardBackgroundProcessor` class or similar.
  - Functions to enqueue tasks (e.g., using FastAPI's `BackgroundTasks` or a dedicated queue like Celery/RQ).
  - Actual task execution logic, such as:
    - `update_dashboard_summary_data()`: Periodically computes and caches summary statistics.
    - `trigger_long_running_report_generation(params)`: Initiates background report generation.
- **Dependencies:** FastAPI's `BackgroundTasks`, `MongoService`, `HubSpotManager`, `RedisService`.

#### 7.3. Background Task Monitoring (`app/services/dash/background_check.py`)

- **Purpose:** Implements health checks and status monitoring for background tasks or services managed by `app/services/dash/background.py`.
- **Key Functions:**
  - `check_background_task_status(task_id: str)`: Status of a specific task.
  - `get_background_services_health()`: Aggregated health of background processes.
  - `get_last_successful_run_time(task_name: str)`: Timestamp of last successful run for recurring tasks.
- **Dependencies:** `RedisService` (for task status/heartbeats), `MongoService` (for task logs/metadata).

### 8. Location Service (`app/services/location/location.py`)

- **Class:** `LocationService`
- **Purpose:** Centralizes location-based functionalities, likely superseding or consolidating logic from `app/utils/location.py` and `app/utils/enhanced.py`. It serves as the primary interface for geocoding, distance calculation, and locality determination.
- **Key Responsibilities:**
  - Provides a consistent API for geocoding addresses/descriptions.
  - Calculates distances between geographic points.
  - Determines if a location is "local" based on service hubs and drive times.
  - Manages geocoding provider interactions (e.g., Nominatim) and result caching.
- **Core Methods (Examples):**
  - `geocode(address_details) -> Optional[Coordinates]`
  - `calculate_distance(point1: Coordinates, point2: Coordinates) -> float`
  - `estimate_drive_time(distance_km: float) -> float`
  - `is_local(coordinates: Coordinates) -> bool`
  - `determine_locality(address_details) -> LocalityResult`
- **Dependencies:** `geopy` library, caching mechanism (e.g., in-memory, Redis), location-related Pydantic models.

### 9. MongoDB Service (`app/services/mongo/mongo.py`)

- **Class:** `MongoService`
- **Purpose:** A dedicated interface for all MongoDB interactions, abstracting direct driver calls and providing methods tailored to the application's data models and query needs.
- **Key Responsibilities:**
  - Managing MongoDB connections.
  - Providing CRUD operations for various collections (e.g., `calls`, `logs`, `users`, `api_keys`).
  - Implementing specific query methods (e.g., `find_call_by_id`, `save_classification_result`).
  - Handling data transformation between Pydantic models and MongoDB documents.
- **Core Methods (Examples):**
  - `__init__(connection_string: str, database_name: str)`
  - `get_collection(collection_name: str)`
  - `insert_document(collection_name: str, document: dict)`
  - `find_document_by_id(collection_name: str, document_id: str)`
- **Dependencies:** `motor` (async MongoDB driver), Pydantic models. Requires MongoDB connection settings.

### 10. Quoting Services (`app/services/quote/`)

This sub-module handles product/service quoting, including generation, management, and synchronization.

#### 10.1. Quote Management (`app/services/quote/quote.py`)

- **Class:** `QuoteService`
- **Purpose:** Manages the generation, retrieval, and overall lifecycle of product/service quotes.
- **Key Responsibilities:**
  - Fetching product/service details and pricing (from DB via `MongoService` or config files like those in `sheets/`).
  - Applying business logic for calculations (discounts, taxes).
  - Generating quote documents/data (`QuoteModel`).
  - Storing and retrieving quotes.
  - Potentially integrating with `HubSpotManager` to link quotes with CRM records.
- **Core Methods (Examples):**
  - `create_quote(quote_request: QuoteRequestModel) -> QuoteModel`
  - `get_quote_by_id(quote_id: str) -> Optional[QuoteModel]`
  - `update_quote_status(quote_id: str, status: str)`
- **Dependencies:** `MongoService`, potentially `HubSpotManager`, quote-related Pydantic models.

#### 10.2. Quote Authentication/Authorization (`app/services/quote/auth.py`)

- **Purpose:** Handles authentication or authorization specific to the quoting functionality. This might be for securing quote-related API endpoints or for internal service-to-service authorization for quote operations.
- **Key Features (Hypothetical):**
  - Could define a `QuoteServiceAuthenticator` or specific FastAPI dependencies.
  - Functions like `verify_quote_access_token(token: str)`.
  - If using the main API key system, it might contain helpers to check for quote-specific permissions (e.g., a `require_quote_permission` dependency).
- **Dependencies:** FastAPI's `Security`, possibly `MongoService`.

#### 10.3. Quote Synchronization (`app/services/quote/sync.py`)

- **Purpose:** Manages synchronization tasks related to quotes. This could involve syncing quote data with external systems (like HubSpot) or ensuring consistency of product/pricing information used by the `QuoteService`.
- **Key Functions/Classes (Examples):**
  - `QuoteSyncManager` or similar.
  - `sync_quotes_to_hubspot()`: Pushes new/updated quotes to HubSpot.
  - `sync_product_catalog_from_source()`: Updates local product/pricing data from an external source (e.g., CSVs in `sheets/`).
- **Dependencies:** `QuoteService`, `HubSpotManager`, `MongoService`.
- **Triggers:** Can be periodic background tasks or event-driven.

### 11. Redis Service (`app/services/redis/redis.py`)

- **Class:** `RedisService`
- **Purpose:** Provides a centralized interface for interacting with a Redis cache, abstracting direct client calls.
- **Key Responsibilities:**
  - Managing Redis connections.
  - Providing methods for basic Redis operations (`get`, `set`, `delete`, `expire`).
  - Handling serialization/deserialization of cached objects.
- **Core Methods (Examples):**
  - `__init__(redis_url: str)`
  - `async get_value(key: str) -> Optional[Any]`
  - `async set_value(key: str, value: Any, expire_seconds: Optional[int] = None)`
  - `async delete_key(key: str)`
  - `async check_connection()`
- **Dependencies:** `aioredis` (async Redis client). Requires Redis connection URL.
