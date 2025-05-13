# Stahla AI SDR API Documentation

This document provides a guide to the Stahla AI SDR API and the external APIs it interacts with. It details internal endpoints, authentication, request/response formats, and summarizes external API usage.

## Internal API (FastAPI Application)

**Base Path:** `/api/v1`

**Authentication:** Specific endpoints require authentication as noted.
_ **Pricing Webhooks:** Require an API key passed via the `Authorization: Bearer <API_KEY>` header, matching the `PRICING_WEBHOOK_API_KEY` setting.
_ **Dashboard API:** Requires authentication (placeholder implementation currently allows access).

---

### Health Check (`/api/v1/health`)

- **`GET /`**
  - **Description:** Checks the health and status of the API application, including basic system metrics.
  - **Auth:** Not Required
  - **Request Body:** None
  - **Response Body:** `HealthCheckResponse` model (defined in `app.models.common`) containing `status`, `uptime`, `cpu_usage`, `memory_usage`.
    ```json
    {
      "status": "ok",
      "uptime": "1 day, 2:30:45",
      "cpu_usage": 15.5,
      "memory_usage": {
        "total": 8192.0,
        "available": 4096.0,
        "percent": 50.0,
        "used": 4096.0,
        "free": 4096.0
      }
    }
    ```

---

### Classification (`/api/v1/classify`)

- **`POST /`**
  - **Description:** Takes input data (from forms, emails, calls) and classifies the lead type (Services, Logistics, Leads, Disqualify) using the configured method (rules or AI). Called internally after processing webhooks.
  - **Auth:** Not Required (Assumed internal call or protected by ingress)
  - **Request Body:** `ClassificationInput` model (defined in `app.models.classification`). Contains source, raw data, extracted data fields (contact info, event details, etc.).
  - **Response Body:** `ClassificationResult` model (defined in `app.models.classification`). Contains the `ClassificationOutput` (lead_type, reasoning, confidence, metadata) and potentially error information.

---

### HubSpot Interaction (`/api/v1/hubspot`)

- **(No direct API endpoints exposed for general HubSpot interaction)**
  - **Note:** HubSpot interactions (create/update contact, company, lead, associate) are performed internally by the `HubSpotManager` service (`app/services/hubspot.py`) triggered by other processes (e.g., after classification via webhook helpers).

---

### Documentation (`/api/v1/docs/`)

- **`GET /{doc_path:path}`**
  - **Description:** Serves project documentation files (from the `/docs` directory) rendered as HTML pages. Allows accessing files like `features.md` via `/api/v1/docs/features` or `/api/v1/docs/features.md`.
  - **Auth:** Not Required
  - **Request Body:** None
  - **Response:** HTML content of the rendered Markdown file or 404 if not found.

---

### Webhooks (`/api/v1/webhook`)

- **`POST /form`**

  - **Description:** Receives web form submission data. Checks for completeness. If complete, triggers lead classification and HubSpot updates (via background tasks). If incomplete, triggers a Bland.ai follow-up call (via background task).
  - **Auth:** Not Required (Assumed protected by obscurity or network rules)
  - **Request Body:** `FormPayload` model (defined in `app.models.webhook`). Contains standard form fields (firstname, lastname, email, phone, company, product_interest, etc.).
  - **Response Body:**
    - On Incomplete: `{"status": "incomplete", "message": "Form incomplete, initiating follow-up call."}` (Status 200 OK)
    - On Complete: `{"status": "success", "message": "Form processed and classification initiated.", "classification_result": {...}, "hubspot_update_status": "initiated" | "skipped"}` (Status 200 OK)

- **`POST /hubspot`**

  - **Description:** Endpoint intended to receive webhook events _from_ HubSpot (e.g., contact updates). Placeholder implementation.
  - **Auth:** Not Required (Requires validation of HubSpot signature in a real implementation)
  - **Request Body:** Varies depending on the HubSpot webhook event type.
  - **Response Body:** `{"message": "HubSpot webhook received"}` (Placeholder)

- **`POST /voice`**

  - **Description:** Receives call completion data (transcript, summary, variables, metadata) from Bland.ai. Processes the transcript, triggers lead classification, and HubSpot updates (via background tasks).
  - **Auth:** Not Required (Assumed protected by obscurity or network rules)
  - **Request Body:** `BlandWebhookPayload` model (defined in `app.models.bland`).
  - **Response Body:** `{"status": "success", "message": "Webhook processed, classification initiated."}` or error details.

- **`POST /pricing/location_lookup`**

  - **Description:** Accepts a delivery location and triggers an asynchronous background task to calculate the distance to the nearest branch using Google Maps and cache the result in Redis. Returns immediately. Designed to be called early in a quoting process.
  - **Auth:** Required (`Authorization: Bearer <PRICING_WEBHOOK_API_KEY>`)
  - **Request Body:** `LocationLookupRequest` model (defined in `app.api.v1.endpoints.webhooks.pricing`).
    ```json
    {
      "delivery_location": "string (required, full address)"
    }
    ```
  - **Response Body:** `{"message": "Location lookup accepted for background processing."}` (Status 202 Accepted)

- **`POST /pricing/quote`**
  - **Description:** Calculates a comprehensive price quote with detailed information about the rental, product, location, and budget breakdown. Relies on cached pricing data (from Google Sheets) and cached location data (from `/location_lookup` or calculated on demand). Logs request/response data via background task.
  - **Auth:** Required (`Authorization: Bearer <PRICING_WEBHOOK_API_KEY>`)
  - **Request Body:** `QuoteRequest` model (defined in `app.models.quote`). Contains `request_id`, `delivery_location`, `trailer_type`, `rental_start_date`, `rental_days`, `usage_type`, `extras`.
  - **Response Body:** Enhanced `QuoteResponse` model with comprehensive details:

    - `request_id` and `quote_id`: Identifiers for the request and generated quote
    - `quote`: Object containing:
      - `line_items`: Detailed list of charges with descriptions and prices
      - `subtotal`: Total cost before taxes/fees
      - `delivery_tier_applied` and `delivery_details`: Summary and detailed breakdown of delivery costs
      - `product_details`: Complete specifications of the quoted product (features, dimensions, capacity)
      - `rental_details`: Comprehensive rental information (dates, duration, pricing tier)
      - `budget_details`: Detailed financial breakdown (taxes, fees, equivalent rates, cost categories)
      - `notes`: Additional information about the quote
    - `location_details`: Complete location information (branch details, distance, service area)
    - `metadata`: Quote generation process details (timestamps, data sources, calculation methods)

    (Status 200 OK on success, 400/500 on error).

---

### Dashboard (`/api/v1/dashboard`)

- **`GET /overview`**

  - **Description:** Provides a summary of system status including cache stats, sync status, basic request/error counts (from Redis counters), recent errors (aggregated), and recent requests (from Redis lists). Data is read from Redis, populated by background tasks.
  - **Auth:** Required (Placeholder implementation)
  - **Request Body:** None
  - **Response Body:** `DashboardOverview` model (defined in `app.models.dash.dashboard`).

- **`GET /requests/recent`**

  - **Description:** Retrieves the last N (default 20, max 100) processed requests and their responses logged to the Redis list `dash:recent_requests`.
  - **Auth:** Required (Placeholder implementation)
  - **Query Parameters:** `limit` (integer, optional)
  - **Request Body:** None
  - **Response Body:** `List[RequestLogEntry]` (defined in `app.models.dash.dashboard`).

- **`POST /sync/trigger`**

  - **Description:** Manually triggers an immediate synchronization of pricing, config, and branches from Google Sheets to Redis by calling the `sync_full_catalog_to_redis` method of the running `SheetSyncService` instance.
  - **Auth:** Required (Placeholder implementation, likely admin-only).
  - **Request Body:** None
  - **Response Body:** `{"message": "Manual sync triggered successfully."}` (Status 200 OK) or 500 error.

- **`GET /cache/search`**

  - **Description:** Searches Redis cache keys matching a glob pattern using the `SCAN` command. Returns a limited list (max 100) of keys with value previews and TTLs.
  - **Auth:** Required (Placeholder implementation).
  - **Query Parameters:** `pattern` (string, required)
  - **Request Body:** None
  - **Response Body:** `List[CacheSearchResult]` (defined in `app.models.dash.dashboard`).

- **`GET /cache/item`**

  - **Description:** Retrieves the value and TTL of a specific Redis cache key.
  - **Auth:** Required (Placeholder implementation).
  - **Query Parameters:** `key` (string, required)
  - **Request Body:** None
  - **Response Body:** `CacheItem` (defined in `app.models.dash.dashboard`) or 404 error.

- **`POST /cache/clear/item`**

  - **Description:** Manually clears a specific cache key from Redis.
  - **Auth:** Required (Placeholder implementation, likely admin-only).
  - **Request Body:** `ClearCacheRequest` model (defined in `app.models.dash.dashboard`).
    ```json
    {
      "key": "string (required)"
    }
    ```
  - **Response:** Status 204 No Content.

- **`POST /cache/clear/pricing`**

  - **Description:** Clears the entire pricing catalog cache (`pricing:catalog` key) from Redis. Requires confirmation flag.
  - **Auth:** Required (Placeholder implementation, likely admin-only).
  - **Request Body:** `ClearPricingCacheRequest` model (defined in `app.models.dash.dashboard`).
    ```json
    {
      "confirm": true
    }
    ```
  - **Response:** Status 204 No Content.

- **`POST /cache/clear/maps`**
  - **Description:** Clears Google Maps distance cache keys (`maps:distance:*`) matching a location pattern using `SCAN` and `DEL`.
  - **Auth:** Required (Placeholder implementation, likely admin-only).
  - **Request Body:**
    ```json
    {
      "location_pattern": "string (required, pattern to match location part of key, e.g., '*123mainst*')"
    }
    ```
  - **Response Body:** `{"message": "Cleared X maps cache keys matching pattern '...'.'"}` (Status 200 OK).

---

## External API Interactions

The application interacts with several external APIs via its service layer.

### 1. Bland.ai

- **Service:** `app/services/bland.py` (`BlandAIManager`)
- **Authentication:** API Key (`BLAND_API_KEY`) passed in `Authorization` header.
- **Endpoints Called:**
  - **`POST /v1/calls`**: Used by `initiate_callback` to start outbound calls (e.g., for incomplete forms). Sends phone number, pathway ID (or task), webhook URL, and metadata. Expects a `call_id` in response.
  - **`POST /v1/pathway/{pathway_id}`**: Used by `_sync_pathway` during startup (`sync_bland_pathway_on_startup`) to attempt to update the conversation pathway defined by `BLAND_PATHWAY_ID` using the definition from `app/assets/call.json`. Sends pathway name, description, nodes, and edges.
- **Webhook Received:** The application receives call completion data from Bland.ai at `/api/v1/webhook/voice`.

### 2. HubSpot

- **Service:** `app/services/hubspot.py` (`HubSpotManager`)
- **Authentication:** API Key (`HUBSPOT_API_KEY`) passed as Bearer token in `Authorization` header.
- **Endpoints Called (Examples):**
  - **`POST /crm/v3/objects/contacts/search`**: Used by `search_contact_by_email` to find existing contacts.
  - **`POST /crm/v3/objects/contacts`**: Used by `create_or_update_contact` to create new contacts. Sends contact properties.
  - **`PATCH /crm/v3/objects/contacts/{contact_id}`**: Used by `create_or_update_contact` and `update_contact_properties` to update existing contacts. Sends contact properties.
  - **`POST /crm/v3/objects/companies/search`**: Used by `search_company_by_domain`.
  - **`POST /crm/v3/objects/companies`**: Used by `create_or_update_company`.
  - **`PUT /crm/v3/objects/contacts/{contact_id}/associations/company/{company_id}/{association_type_id}`**: Used by `associate_contact_to_company`.
  - **`POST /crm/v3/objects/leads`**: Used by `create_lead`. Sends lead properties and associations.
  - **`PATCH /crm/v3/objects/leads/{lead_id}`**: Used by `update_lead_properties`.
  - **`GET /crm/v3/objects/contacts/{contact_id}`**: Used by `get_contact_by_id`.
  - **`GET /crm/v3/objects/leads/{lead_id}`**: Used by `get_lead_by_id`.
  - **`GET /crm/v3/pipelines/deals`**: Used by `get_pipeline_id`.
  - **`GET /crm/v3/pipelines/deals/{pipeline_id}/stages`**: Used by `get_stage_id`.
  - **`GET /crm/v3/owners/`**: Used by `get_owners`.
- **Webhook Received:** The application has an endpoint `/api/v1/webhook/hubspot` intended for receiving HubSpot webhooks (implementation is basic).

### 3. Google Maps Distance Matrix API

- **Service:** `app/services/location/location.py` (`LocationService`)
- **Authentication:** API Key (`GOOGLE_MAPS_API_KEY`) used by the `googlemaps` client library.
- **Endpoints Called:** Implicitly calls the Distance Matrix API endpoint via `self.gmaps.distance_matrix`. Sends origin/destination addresses. Expects distance and duration values in response.
- **Usage:** Called by `_get_distance_from_google` when calculating the distance between a branch and a delivery location if the result is not found in the Redis cache. Background tasks increment counters (`dash:stats:gmaps_calls_total`, `dash:stats:gmaps_errors_total`) on call/error.

### 4. Google Sheets API

- **Service:** `app/services/quote/sync.py` (`SheetSyncService`)
- **Authentication:** Google Service Account credentials (via file path `GOOGLE_APPLICATION_CREDENTIALS` or Application Default Credentials). Requires `https://www.googleapis.com/auth/spreadsheets.readonly` scope.
- **Endpoints Called:** Uses the `google-api-python-client` library. Primarily calls:
  - **`spreadsheets.values.get`**: Used by `_fetch_sheet_data` to read data from specified ranges (products, generators, branches, config) within the Google Sheet identified by `GOOGLE_SHEET_ID`.
- **Usage:** Called periodically by the background sync task (`_run_sync_loop`) and on application startup to refresh the pricing catalog, branch list, and configuration stored in Redis. Errors during sync are logged via background tasks.

### 5. n8n (Optional Workflow Automation)

- **Service:** `app/services/n8n.py`
- **Authentication:** Optional API Key (`N8N_API_KEY`) sent in a custom `Stahla` header.
- **Endpoints Called:**
  - **`POST {N8N_WEBHOOK_URL}`**: Used by `send_to_n8n_webhook` (called by `trigger_n8n_handoff_automation`) to send classification results and lead details to an n8n workflow for further automation (e.g., complex notifications, CRM updates beyond basic creation).
- **Usage:** Triggered after successful lead classification if `N8N_ENABLED` is true in settings.
