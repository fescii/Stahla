<!-- filepath: /docs/webhooks.md -->

# Stahla AI SDR Webhooks

This document details the webhooks used within the Stahla AI SDR application. Webhooks are crucial for receiving real-time data from external services (like web forms, HubSpot, Bland.ai) and for internal asynchronous processing.

## Common Webhook Router

All webhook endpoints are grouped under the `/api/v1/webhook` base path. This is defined in `app/api/v1/api.py`.

```python
# app/api/v1/api.py
# ...
# Create a sub-router for all webhooks for better organization
webhook_router = APIRouter()
# Path defined in form.router (e.g., /form)
webhook_router.include_router(webhooks_form.router)
# Path defined in hubspot.router
webhook_router.include_router(webhooks_hubspot.router)
# Path defined in voice.router
webhook_router.include_router(webhooks_voice.router)
# Paths /location_lookup and /quote are relative to this
webhook_router.include_router(webhooks_pricing.router)

# Include the webhook_router under /webhook prefix
api_router_v1.include_router(
    webhook_router, prefix="/webhook", tags=["Webhooks"])
# ...
```

## Specific Webhook Endpoints

### 1. Form Webhook

- **Endpoint:** `POST /api/v1/webhook/form`
- **File:** `app/api/v1/endpoints/webhooks/form.py`
- **Purpose:** Receives form submissions from web forms.
- **Request Model:** `app.models.webhook.FormPayload`

  ```python
  # app/models/webhook.py
  class FormPayload(BaseModel):
      # Basic contact info
      firstname: Optional[str] = None
      lastname: Optional[str] = None
      email: Optional[EmailStr] = None
      phone: Optional[str] = None
      company: Optional[str] = None

      # Lead details
      product_interest: Optional[str] = Field(None, description="Product(s) the prospect is interested in")
      lead_type_guess: Optional[str] = Field(None, description="Initial guess about lead type")
      event_type: Optional[str] = Field(None, description="Type of event or project")

      # Location information
      event_location_description: Optional[str] = Field(None, description="Address or general location")
      event_state: Optional[str] = Field(None, description="Two-letter state code")
      event_city: Optional[str] = Field(None, description="City of the event")
      event_postal_code: Optional[str] = Field(None, description="Postal/ZIP code")

      # Event details
      duration_days: Optional[int] = Field(None, description="Rental duration in days")
      start_date: Optional[str] = Field(None, description="Start/delivery date")
      end_date: Optional[str] = Field(None, description="End/pickup date")
      guest_count: Optional[int] = Field(None, description="Estimated number of attendees")
      required_stalls: Optional[int] = Field(None, description="Number of stalls needed")
      ada_required: Optional[bool] = Field(None, description="ADA-compliant facilities required")
      budget_mentioned: Optional[str] = Field(None, description="Budget information provided")
      comments: Optional[str] = Field(None, description="Additional comments")

      # Site requirements
      power_available: Optional[bool] = Field(None, description="Power available on site?")
      water_available: Optional[bool] = Field(None, description="Water available on site?")
      other_facilities_available: Optional[bool] = Field(None, description="Other restroom facilities available?")
      other_products_needed: Optional[List[str]] = Field(default_factory=list, description="Other products requested")

      # Metadata
      form_id: Optional[str] = Field(None, description="Identifier for the form submitted")
      submission_timestamp: Optional[str] = Field(None, description="Timestamp of form submission")

      class Config:
          extra = 'allow' # Allows any other fields submitted by the form
  ```

- **Processing Workflow:**
  1.  Receives `FormPayload`.
  2.  Checks if the form data is complete using `_is_form_complete` helper.
  3.  **If incomplete:**
      - Triggers a follow-up call via Bland.ai using `_trigger_bland_call` helper in the background.
      - Returns an "incomplete" status.
  4.  **If complete:**
      - Converts `FormPayload` to `ClassificationInput` using `prepare_classification_input`.
      - Triggers lead classification using `classification_manager.classify_lead_data`.
      - If classification is successful, triggers a HubSpot contact/deal update using `_handle_hubspot_update` helper in the background.
      - Returns a "success" status with classification results.
- **Response Model:** `GenericResponse[FormWebhookResponseData]`
  ```python
  # app/api/v1/endpoints/webhooks/form.py
  class FormWebhookResponseData(BaseModel):
      status: str
      message: str
      classification_result: Optional[Any] = None
      hubspot_update_status: Optional[str] = None
  ```

### 2. HubSpot Webhook

- **Endpoint:** `POST /api/v1/webhook/hubspot`
- **File:** `app/api/v1/endpoints/webhooks/hubspot.py`
- **Purpose:** Handles direct contact data payloads from HubSpot, typically triggered by HubSpot Workflows (e.g., when a contact property changes or a new contact is created meeting certain criteria). This allows Stahla to react to changes in HubSpot CRM in real-time.
- **Request Model:** `app.models.webhook.HubSpotContactDataPayload`

  ```python
  # app/models/webhook.py
  class HubSpotContactDataPayload(BaseModel):
      vid: int # HubSpot Contact ID (VID)
      canonical_vid: int = Field(..., alias='canonical-vid')
      merged_vids: List[int] = Field(..., alias='merged-vids')
      portal_id: int = Field(..., alias='portal-id')
      is_contact: bool = Field(..., alias='is-contact')
      properties: Dict[str, Optional[HubSpotPropertyDetail]] # Dictionary of contact properties
      form_submissions: List[Any] = Field(..., alias='form-submissions') # List of form submissions by the contact
      list_memberships: List[Any] = Field(..., alias='list-memberships') # Lists the contact is a member of
      identity_profiles: List[HubSpotIdentityProfile] = Field(..., alias='identity-profiles') # Contact's identity profiles (e.g., email, cookie)
      merge_audits: List[Any] = Field(..., alias='merge-audits')
      associated_company: Optional[HubSpotAssociatedCompany] = Field(None, alias='associated-company') # Associated company details

      class Config:
          extra = 'allow'
          populate_by_name = True

  # Supporting models like HubSpotPropertyDetail, HubSpotIdentityProfile, etc., are also in app/models/webhook.py
  ```

- **Processing Workflow:**
  1.  Receives `HubSpotContactDataPayload`.
  2.  Extracts contact properties using `_extract_simple_properties`.
  3.  Checks if the contact data is complete for immediate processing using `_is_hubspot_contact_complete` helper. This check determines if enough information is present to attempt a classification or if a follow-up is needed.
  4.  **If complete:**
      - Prepares `ClassificationInput` from the HubSpot data using `prepare_classification_input`.
      - Classifies the lead data using `classification_manager.classify_lead_data`.
      - Updates the HubSpot lead with classification results and notifies n8n in the background via `_update_hubspot_lead_after_classification` (which handles creating a new lead and associating it with the contact).
  5.  **If incomplete:**
      - Triggers a Bland.ai call to gather missing information in the background via `_trigger_bland_call_for_hubspot`.
- **Response Model:** `GenericResponse[HubSpotWebhookResponseData]`
  ```python
  # app/api/v1/endpoints/webhooks/hubspot.py
  class HubSpotWebhookResponseData(BaseModel):
      status: str
      message: str
  ```

### 3. Voice Webhook (Bland.ai)

- **Endpoint:** `POST /api/v1/webhook/voice`
- **File:** `app/api/v1/endpoints/webhooks/voice.py`
- **Purpose:** Receives voice call transcripts, summaries, recordings, and other metadata from Bland.ai after an automated call has completed.
- **Request Model:** `app.models.bland.BlandWebhookPayload`
  ```python
  # app/models/bland.py
  class BlandWebhookPayload(BlandBaseModel):
      call_id: Optional[str] = None
      c_id: Optional[str] = None # Alternative call ID
      to: Optional[str] = None # Number called
      from_: Optional[str] = Field(None, alias="from") # Calling number
      call_length: Optional[float] = None # Duration in seconds
      status: Optional[str] = None # e.g., 'completed', 'failed'
      transcripts: Optional[List[BlandTranscriptEntry]] = None # Detailed transcript segments
      concatenated_transcript: Optional[str] = None # Full transcript as a single string
      summary: Optional[str] = None # Bland.ai's summary of the call
      recording_url: Optional[HttpUrl] = None # URL to the call recording
      variables: Optional[Dict[str, Any]] = None # Custom variables passed when initiating the call (can contain metadata like hubspot_contact_id, form_submission_data)
      metadata: Optional[Dict[str, Any]] = None # Additional metadata from Bland.ai
      # ... other fields like pathway_id, analysis, etc.
  ```
- **Processing Workflow:**
  1.  Receives `BlandWebhookPayload`.
  2.  Processes the transcript using `bland_manager.process_incoming_transcript` to extract structured data based on the call script/goals.
  3.  Checks for `hubspot_contact_id` and `hubspot_lead_id` in the payload's `variables` or `metadata` (these are passed when Stahla initiates the Bland.ai call).
  4.  If `hubspot_contact_id` is present, fetches existing contact details from HubSpot using `hubspot_manager.get_contact_by_id` to enrich the data available for classification.
  5.  Merges data from the call (extracted data, summary, recording URL), form submission data (if passed in `variables.metadata.form_submission_data`), and fetched HubSpot properties.
  6.  Prepares `ClassificationInput` using `prepare_classification_input` with the merged data.
  7.  Classifies the lead data using `classification_manager.classify_lead_data`.
  8.  Updates the `classification_input` object with any newly refined details extracted by the AI classification (e.g., more precise event details, confirmed product interest).
  9.  **HubSpot Integration:**
      - **If existing `hubspot_lead_id` and `hubspot_contact_id` were found in the call metadata:** Updates the existing HubSpot lead in the background using the `_update_hubspot_lead_after_classification` helper. This helper is designed to create a _new_ lead and associate it, so this flow implies the original intent was to gather more info for a contact that might not have had a lead yet, or to update a contact prior to lead creation.
      - **Otherwise (typically a new lead or updating a contact before lead creation):** Creates a new contact (if it doesn't exist or needs update) and a new lead in HubSpot in the background using the `_handle_hubspot_update` helper.
- **Response Model:** `GenericResponse[VoiceWebhookResponseData]`
  ```python
  # app/api/v1/endpoints/webhooks/voice.py
  class VoiceWebhookResponseData(BaseModel):
      status: str
      source: str # Indicates 'voice'
      action: str # e.g., 'classification_complete'
      classification: Optional[ClassificationOutput] = None # The result from classification_manager
      hubspot_contact_id: Optional[str] = None # ID of the created/updated HubSpot contact
      hubspot_lead_id: Optional[str] = None # ID of the created/updated HubSpot lead
  ```

### 4. Pricing Webhooks

- **File:** `app/api/v1/endpoints/webhooks/pricing.py`
- **Authentication:** All pricing webhooks require an API key via `Depends(get_api_key)`.

  #### a. Asynchronous Location Lookup

  - **Endpoint:** `POST /api/v1/webhook/location/lookup`
  - **Purpose:** Accepts a delivery location and triggers an asynchronous background task to calculate and cache the distance to the nearest Stahla branch. This is used to pre-warm the cache for faster quote generation later.
  - **Request Model:** `app.models.location.LocationLookupRequest`
    ```python
    # app/models/location.py
    class LocationLookupRequest(BaseModel):
        delivery_location: str = Field(..., description="Full delivery address for distance lookup.")
    ```
  - **Processing Workflow:**
    1.  Receives `delivery_location`.
    2.  Adds a background task to call `location_service.prefetch_distance`. This service handles the actual distance calculation (likely using Google Maps API) and caches the result in Redis.
    3.  Increments a Redis counter for total location lookups (`TOTAL_LOCATION_LOOKUPS_KEY`).
    4.  Returns a `202 Accepted` status immediately, indicating the task is scheduled.
  - **Response Model:** `GenericResponse[MessageResponse]`
    ```python
    # app/models/common.py
    class MessageResponse(BaseModel):
        message: str
    ```

  #### b. Synchronous Location Lookup (for Testing)

  - **Endpoint:** `POST /api/v1/webhook/location/lookup/sync`
  - **Purpose:** Accepts a delivery location, calculates the distance to the nearest branch synchronously, and returns the result. Primarily for testing the location service directly.
  - **Request Model:** `app.models.location.LocationLookupRequest` (same as async version)
  - **Processing Workflow:**
    1.  Receives `delivery_location`.
    2.  Calls `location_service.get_distance_to_nearest_branch` directly, which performs the calculation and returns the result without backgrounding.
    3.  Returns the `LocationLookupResponse` containing `DistanceResult` and processing time.
  - **Response Model:** `GenericResponse[LocationLookupResponse]`

    ```python
    # app/models/location.py
    class LocationLookupResponse(BaseModel):
        distance_result: Optional[DistanceResult] = None
        processing_time_ms: Optional[int] = None
        message: Optional[str] = None

    class DistanceResult(BaseModel):
        nearest_branch: BranchLocation
        delivery_location: str
        distance_miles: float
        distance_meters: int
        duration_seconds: int

    class BranchLocation(BaseModel):
        name: str
        address: str
    ```

  #### c. Quote Generation

  - **Endpoint:** `POST /api/v1/webhook/quote`
  - **Purpose:** Calculates a detailed price quote based on provided information. This is the core pricing engine endpoint.
  - **Request Model:** `app.models.quote.QuoteRequest`

    ```python
    # app/models/quote.py
    class QuoteRequest(BaseModel):
        request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        delivery_location: str
        trailer_type: str # Stahla trailer model ID
        rental_start_date: date
        rental_days: int
        usage_type: Literal["commercial", "event"]
        extras: List[ExtraInput] = Field(default_factory=list)

    class ExtraInput(BaseModel):
        extra_id: str # Identifier for the extra item
        qty: int
    ```

  - **Processing Workflow:**
    1.  Receives `QuoteRequest`.
    2.  Calls `quote_service.build_quote`. This service orchestrates:
        - Fetching product details and base rates.
        - Fetching delivery distance (ideally from cache populated by `/location/lookup`, or calculating it).
        - Applying pricing rules, seasonal adjustments, and delivery tier calculations.
        - Calculating costs for extras.
        - Assembling all details into a `QuoteResponse` object.
    3.  Calculates total processing time for the quote generation and updates the `QuoteResponse.metadata`.
    4.  Increments Redis counters for total and successful quote requests.
    5.  Returns the `GenericResponse[QuoteResponse]` containing the detailed quote.
    6.  Handles errors by logging, incrementing error counters, and returning an error response.
  - **Response Model:** `GenericResponse[QuoteResponse]`

    ```python
    # app/models/quote.py
    class QuoteResponse(BaseModel):
        request_id: str
        quote_id: str = Field(default_factory=lambda: f"QT-{uuid.uuid4()}")
        quote: QuoteBody
        location_details: Optional[LocationDetails] = None
        metadata: QuoteMetadata

    # QuoteBody, LocationDetails, QuoteMetadata, LineItem, DeliveryCostDetails, etc.,
    # are all defined in app/models/quote.py, providing a rich, structured quote.
    ```

## Webhook Data Models Deep Dive

The primary Pydantic models defining the structure of webhook payloads are crucial for data validation, clarity, and ensuring consistent interactions. They are located in the `app/models/` directory.

- **`app/models/webhook.py`**:

  - `FormPayload`: Captures all expected fields from a web form submission. Designed to align with `ClassificationInput` for easier data mapping. Includes fields for contact info, event details, location, product interest, site requirements, and metadata like `form_id` and `submission_timestamp`. Uses `Config.extra = 'allow'` to accommodate any additional fields a form might send.
  - `HubSpotWebhookEvent`: Represents a single event in a HubSpot webhook batch (though the current implementation uses `HubSpotContactDataPayload` for direct data pushes).
  - `HubSpotContactDataPayload`: A comprehensive model for the rich data HubSpot sends via its direct contact data webhooks (e.g., through Workflows). It includes the contact's `vid` (HubSpot ID), a detailed `properties` dictionary (using `HubSpotPropertyDetail` which includes value and versions), `form_submissions`, `list_memberships`, `identity_profiles` (tracking different ways a contact is identified), and `associated_company` details. Uses `populate_by_name = True` to handle HubSpot's snake_case and kebab-case field names.

- **`app/models/bland.py`**:

  - `BlandWebhookPayload`: Defines the structure for data received from Bland.ai after a call. Includes `call_id`, `concatenated_transcript`, `summary`, `recording_url`, and significantly, `variables`. The `variables` field is a dictionary that Stahla can populate when initiating the call, often used to pass `hubspot_contact_id`, `hubspot_lead_id`, or `form_submission_data` for context, which the webhook then uses to link the call back to the originating lead or form.
  - `BlandTranscriptEntry`: Represents individual segments of the call transcript with speaker and text.

- **`app/models/location.py`**:

  - `LocationLookupRequest`: Simple model with `delivery_location` (a string) for both asynchronous and synchronous distance lookups.
  - `LocationLookupResponse`: Contains an optional `DistanceResult` (with `nearest_branch`, `distance_miles`, `duration_seconds`) and `processing_time_ms` for the synchronous endpoint.
  - `BranchLocation`: Stores the name and address of a Stahla branch.
  - `DistanceResult`: Detailed result of a distance calculation including the nearest branch, delivery location, distance in miles and meters, and duration in seconds.

- **`app/models/quote.py`**:
  - `QuoteRequest`: Input for generating a quote. Includes `request_id`, `delivery_location`, `trailer_type` (product ID), `rental_start_date`, `rental_days`, `usage_type` (event/commercial), and a list of `ExtraInput` (extra item ID and quantity).
  - `QuoteResponse`: The comprehensive output. Contains the original `request_id`, a new `quote_id`, a `QuoteBody` object, `LocationDetails`, and `QuoteMetadata`.
  - `QuoteBody`: The core of the quote, including `line_items`, `subtotal`, `delivery_details` (with `DeliveryCostDetails`), `rental_details`, `product_details`, and `budget_details`.
  - `LineItem`: Represents individual items in the quote (e.g., trailer rental, delivery, extras) with description, quantity, unit price, and total.
  - `DeliveryCostDetails`: Detailed breakdown of how delivery cost was calculated (miles, reason, rates, multipliers).
  - `LocationDetails`: Information about the delivery address, nearest branch, distance, and drive time.
  - `RentalDetails`: Start/end dates, duration, pricing tier, seasonal adjustments.
  - `ProductDetails`: ID, name, description, rates, features of the main trailer.
  - `BudgetDetails`: Subtotal, estimated taxes/fees, total, rate equivalents, cost breakdown.
  - `QuoteMetadata`: Timestamps, version, source system, calculation time, warnings.

These models ensure data integrity and provide clear schemas for incoming webhook data and the structured data passed between services.

## Webhook Helper Functions Deep Dive

Common logic shared across webhook endpoints, especially for interacting with services like Bland.ai and HubSpot, is encapsulated in helper functions within `app/api/v1/endpoints/webhooks/helpers.py`. The `prepare_classification_input` function is a key component residing in `app/api/v1/endpoints/prepare.py`.

- **`app/api/v1/endpoints/webhooks/helpers.py`**:

  - `_is_form_complete(payload: FormPayload) -> bool`:

    - **Purpose:** Validates if a `FormPayload` from a web submission contains a predefined set of minimum required fields (e.g., name, email, phone, product interest, location, start date).
    - **Logic:** Checks that each required field in the payload is not None and not an empty string.
    - **Usage:** Called by the `/form` webhook to decide whether to classify the lead directly or trigger a follow-up call.

  - `_trigger_bland_call(payload: FormPayload)`:

    - **Purpose:** Initiates a Bland.ai outbound call if a form submission is incomplete.
    - **Logic:** Constructs a `BlandCallbackRequest`. Populates `request_data` with details from the `FormPayload` (name, email, product interest, etc.) for the AI agent to use. Populates `metadata` with `source: "web_form_incomplete"` and other form details for tracking. Sets the Bland.ai webhook URL to `/webhook/voice` to receive results. Calls `bland_manager.initiate_callback`.
    - **Usage:** Called as a background task by the `/form` webhook if `_is_form_complete` is false.

  - `_handle_hubspot_update(classification_result: ClassificationResult, input_data: ClassificationInput) -> Tuple[Optional[str], Optional[str]]`:

    - **Purpose:** Central function to create/update a HubSpot Contact and then create a _new_ HubSpot Lead (Deal). This is typically used for new leads originating from forms, voice calls, or emails where no pre-existing HubSpot Lead ID is known.
    - **Logic:**
      1.  Ensures `input_data.email` is present.
      2.  Creates/updates a HubSpot contact using `hubspot_manager.create_or_update_contact` with properties mapped from `input_data` and `classification_result.classification.metadata` (e.g., call summaries).
      3.  If contact creation/update is successful, prepares `HubSpotLeadProperties` by mapping data from `input_data` and `classification_result` (e.g., event type, stall count, AI classification details like `ai_lead_type`, `reasoning`, `routing_suggestion`).
      4.  Creates a new HubSpot lead using `hubspot_manager.create_lead`.
      5.  If lead creation is successful and the lead is not disqualified, it attempts to assign an owner using `hubspot_manager.get_next_owner_id()` and then updates the lead.
      6.  Triggers an n8n handoff automation via `trigger_n8n_handoff_automation` if the lead is not disqualified, passing all relevant data.
    - **Returns:** A tuple of `(contact_id, lead_id)`.
    - **Usage:** Called as a background task by `/form` and `/voice` webhooks for new lead creation flows.

  - `_is_hubspot_contact_complete(contact_properties: dict) -> bool`:

    - **Purpose:** Checks if data received directly from HubSpot (e.g., via a HubSpot workflow triggering the `/webhook/hubspot` endpoint) is sufficient to proceed with classification and lead creation, or if a Bland.ai call is needed to gather more info.
    - **Logic:** Checks for the presence and validity of key HubSpot contact properties (e.g., `firstname`, `email`, `phone`, `event_or_job_address`, `event_start_date`, `what_service_do_you_need_`). Critically, it also considers if mandatory _lead_ fields (like `quote_urgency`) can be derived. Currently, this function often returns `False` because some lead-specific qualifying information is usually not present in the initial HubSpot contact data alone, thus typically directing the flow towards a qualification call.
    - **Usage:** Called by the `/hubspot` webhook.

  - `_trigger_bland_call_for_hubspot(contact_id: str, contact_properties: dict)`:

    - **Purpose:** Initiates a Bland.ai call when the `/webhook/hubspot` endpoint receives contact data deemed incomplete by `_is_hubspot_contact_complete`.
    - **Logic:** Similar to `_trigger_bland_call`, but `request_data` is populated from `contact_properties` (HubSpot data). `metadata` includes `source: "hubspot_incomplete_contact"` and the `hubspot_contact_id` for tracking. Calls `bland_manager.initiate_callback`.
    - **Usage:** Called as a background task by the `/hubspot` webhook if data is incomplete.

  - `_update_hubspot_lead_after_classification(classification_result: ClassificationResult, input_data: ClassificationInput, contact_id: str)`:
    - **Purpose:** This helper is intended to create a _new_ HubSpot Lead and associate it with an _existing_ HubSpot Contact (identified by `contact_id`) after data (potentially from a Bland.ai call triggered for an existing contact) has been classified. It's distinct from `_handle_hubspot_update` which might also create the contact.
    - **Logic:**
      1.  Ensures `classification_output` is present.
      2.  Prepares `HubSpotLeadProperties` from `classification_result` and `input_data`.
      3.  Creates a new HubSpot lead using `hubspot_manager.create_lead`, ensuring it's associated with the provided `contact_id` (the `create_lead` service function handles the association if contact details are part of the `HubSpotLeadInput`).
      4.  If lead creation is successful, assigns an owner and triggers n8n handoff, similar to `_handle_hubspot_update`.
    - **Usage:** Called as a background task by the `/voice` webhook when a call was made for an existing HubSpot contact (identified by `hubspot_contact_id` in call metadata) and now a lead needs to be created based on the call outcome and classification. Also used by the `/hubspot` webhook if the initial data was deemed complete enough to classify and then create a lead.

- **`app/api/v1/endpoints/prepare.py`**:
  - `prepare_classification_input(source: str, raw_data: dict, extracted_data: dict) -> ClassificationInput`:
    - **Purpose:** A crucial utility to standardize and transform data from various sources (web forms, Bland.ai voice calls, direct HubSpot data) into a single, consistent `ClassificationInput` model. This model is then used by the `classification_manager`.
    - **Logic:** Takes a `source` string (e.g., "webform", "voice", "hubspot_webhook_direct"), the `raw_data` payload from the source, and a dictionary of `extracted_data` (which might be the raw payload itself or a processed version of it).
    - It then carefully maps fields from `extracted_data` to the corresponding fields in the `ClassificationInput` model, using `.get()` with defaults to handle missing fields gracefully. This includes contact information, event details, product interest, site requirements, and call-specific data like summaries and recording URLs.
    - **Returns:** An instance of `ClassificationInput`.
    - **Usage:** Called by all webhooks (`/form`, `/hubspot`, `/voice`) that feed into the lead classification process. This ensures the `classification_manager` receives data in a predictable format, regardless of its origin.

These helpers and the `prepare_classification_input` function are essential for modularizing the webhook logic, promoting code reuse, and centralizing complex interactions with external services and the internal classification system.
