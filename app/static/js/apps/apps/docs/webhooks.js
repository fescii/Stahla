export default class WebhooksDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0;
    
    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedWebhooks: new Set(),
      expandedSchemas: new Set(),
      expandedSubmenu: false,
      expandedCategories: new Set(['webhooks'])
    };

    this.render();
  }

  connectedCallback() {
    this._setupEventListeners();
  }

  disconnectedCallback() {
    // Clean up event listeners when element is removed
  }

  render() {
    this.renderCount++;
    console.log(`Rendering Webhooks docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return `
      ${this.getStyles()}
      <div class="webhooks-docs">
        <div class="webhooks-docs-content">
          <nav class="webhooks-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="webhooks-docs-main" class="webhooks-docs-main">
            <div id="content-container" class="webhooks-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="webhooks-docs-header">
        <h1>Stahla AI SDR Webhooks</h1>
        <p>A comprehensive guide to the webhooks used within the Stahla AI SDR application</p>
      </header>
    `;
  }

  getSidebar() {
    return /* html */ `
      <div class="sidebar-content">
        <div class="mobile-toggle">
          <button id="toggle-nav">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="nav-sections ${this.state.expandedSubmenu ? 'expanded' : ''}">
          <div class="nav-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
            <a class="nav-link" data-section="introduction">Introduction</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'router' ? 'active' : ''}">
            <a class="nav-link" data-section="router">Common Webhook Router</a>
          </div>
          <div class="nav-section ${this.isWebhooksActive() ? 'active' : ''} ${this.state.expandedCategories.has('webhooks') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-section="webhooks" data-category="webhooks">
              <span class="link-text">Webhook Endpoints</span>
              <span class="expand-icon">${this.state.expandedCategories.has('webhooks') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'form' ? 'active' : ''}" data-section="form">Form Webhook</a>
              <a class="nav-link sub ${this.state.activeSection === 'hubspot' ? 'active' : ''}" data-section="hubspot">HubSpot Webhook</a>
              <a class="nav-link sub ${this.state.activeSection === 'voice' ? 'active' : ''}" data-section="voice">Voice Webhook</a>
              <a class="nav-link sub ${this.state.activeSection === 'pricing' ? 'active' : ''}" data-section="pricing">Pricing Webhooks</a>
            </div>
          </div>
          <div class="nav-section ${this.state.activeSection === 'models' ? 'active' : ''}">
            <a class="nav-link" data-section="models">Webhook Data Models</a>
          </div>
          <div class="nav-section ${this.state.activeSection === 'helpers' ? 'active' : ''}">
            <a class="nav-link" data-section="helpers">Helper Functions</a>
          </div>
        </div>
      </div>
    `;
  }

  isWebhooksActive() {
    const webhookSections = ['webhooks', 'form', 'hubspot', 'voice', 'pricing'];
    return webhookSections.includes(this.state.activeSection);
  }

  getContentForSection(section) {
    switch(section) {
      case 'introduction':
        return this.getIntroductionSection();
      case 'router':
        return this.getRouterSection();
      case 'webhooks':
        return this.getWebhooksSection();
      case 'form':
        return this.getFormSection();
      case 'hubspot':
        return this.getHubspotSection();
      case 'voice':
        return this.getVoiceSection();
      case 'pricing':
        return this.getPricingSection();
      case 'models':
        return this.getModelsSection();
      case 'helpers':
        return this.getHelpersSection();
      default:
        return this.getIntroductionSection();
    }
  }

  getIntroductionSection() {
    return /* html */ `
      <section id="introduction" class="content-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
        ${this.getHeader()}
        <p>Webhooks are crucial for receiving real-time data from external services (like web forms, HubSpot, Bland.ai) and for internal asynchronous processing.</p>
        
        <h3>Overview of Webhooks</h3>
        <p>The Stahla AI SDR application uses webhooks to handle various real-time events and asynchronous processing tasks:</p>
        
        <div class="webhook-overview">
          <div class="webhook-card">
            <h4>Form Webhook</h4>
            <p>Processes web form submissions, classifies leads, and initiates follow-up calls if needed.</p>
          </div>
          <div class="webhook-card">
            <h4>HubSpot Webhook</h4>
            <p>Handles contact data from HubSpot, allowing real-time reaction to CRM changes.</p>
          </div>
          <div class="webhook-card">
            <h4>Voice Webhook</h4>
            <p>Receives call transcripts and metadata from Bland.ai for processing and classification.</p>
          </div>
          <div class="webhook-card">
            <h4>Pricing Webhooks</h4>
            <p>Handles location lookups and quote generation for pricing services.</p>
          </div>
        </div>
      </section>
    `;
  }

  getRouterSection() {
    return /* html */ `
      <section id="router" class="content-section ${this.state.activeSection === 'router' ? 'active' : ''}">
        <h2>Common Webhook Router</h2>
        <p>All webhook endpoints are grouped under the <code>/api/v1/webhook</code> base path. This is defined in <code>app/api/v1/api.py</code>.</p>
        
        <div class="code-block">
          <pre><code># app/api/v1/api.py
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
# ...</code></pre>
          <button class="copy-btn" data-text="webhook_router = APIRouter()
webhook_router.include_router(webhooks_form.router)
webhook_router.include_router(webhooks_hubspot.router)
webhook_router.include_router(webhooks_voice.router)
webhook_router.include_router(webhooks_pricing.router)

api_router_v1.include_router(
    webhook_router, prefix='/webhook', tags=['Webhooks'])">Copy</button>
        </div>
        
        <p>This structure provides a clear organization for webhook endpoints and makes it easy to identify webhook-related functionality in the API documentation.</p>
      </section>
    `;
  }

  getWebhooksSection() {
    return /* html */ `
      <section id="webhooks" class="content-section ${this.state.activeSection === 'webhooks' ? 'active' : ''}">
        <h2>Webhook Endpoints</h2>
        <p>The Stahla AI SDR application provides several webhook endpoints for receiving external events and triggering internal processes.</p>
        
        <div class="webhooks-grid">
          <div class="webhook-item" data-webhook="form">
            <h3>Form Webhook</h3>
            <code>POST /api/v1/webhook/form</code>
            <p>Receives and processes form submissions, classifies leads, and triggers follow-up actions.</p>
          </div>
          <div class="webhook-item" data-webhook="hubspot">
            <h3>HubSpot Webhook</h3>
            <code>POST /api/v1/webhook/hubspot</code>
            <p>Handles contact data from HubSpot to enable real-time reactions to CRM changes.</p>
          </div>
          <div class="webhook-item" data-webhook="voice">
            <h3>Voice Webhook</h3>
            <code>POST /api/v1/webhook/voice</code>
            <p>Processes call data and transcripts from Bland.ai after automated calls complete.</p>
          </div>
          <div class="webhook-item" data-webhook="pricing">
            <h3>Pricing Webhooks</h3>
            <code>POST /api/v1/webhook/location/lookup</code>
            <code>POST /api/v1/webhook/quote</code>
            <p>Handles location lookups and quote generation for pricing services.</p>
          </div>
        </div>
        
        <p>Click on each webhook above for detailed information about its purpose, request model, processing workflow, and response model.</p>
      </section>
    `;
  }

  getFormSection() {
    return /* html */ `
      <section id="form" class="content-section ${this.state.activeSection === 'form' ? 'active' : ''}">
        <h2>Form Webhook</h2>
        <div class="endpoint-details">
          <div class="endpoint-url">
            <strong>Endpoint:</strong> 
            <code>POST /api/v1/webhook/form</code>
          </div>
          <div class="endpoint-file">
            <strong>File:</strong> 
            <code>app/api/v1/endpoints/webhooks/form.py</code>
          </div>
          <div class="endpoint-purpose">
            <strong>Purpose:</strong> 
            <p>Receives form submissions from web forms.</p>
          </div>
        </div>
        
        <h3>Request Model</h3>
        <p><code>app.models.webhook.FormPayload</code></p>
        <div class="code-block">
          <pre><code># app/models/webhook.py
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
        extra = 'allow' # Allows any other fields submitted by the form</code></pre>
        </div>
        
        <h3>Processing Workflow</h3>
        <ol>
          <li>Receives <code>FormPayload</code>.</li>
          <li>Checks if the form data is complete using <code>_is_form_complete</code> helper.</li>
          <li><strong>If incomplete:</strong>
            <ul>
              <li>Triggers a follow-up call via Bland.ai using <code>_trigger_bland_call</code> helper in the background.</li>
              <li>Returns an "incomplete" status.</li>
            </ul>
          </li>
          <li><strong>If complete:</strong>
            <ul>
              <li>Converts <code>FormPayload</code> to <code>ClassificationInput</code> using <code>prepare_classification_input</code>.</li>
              <li>Triggers lead classification using <code>classification_manager.classify_lead_data</code>.</li>
              <li>If classification is successful, triggers a HubSpot contact/deal update using <code>_handle_hubspot_update</code> helper in the background.</li>
              <li>Returns a "success" status with classification results.</li>
            </ul>
          </li>
        </ol>
        
        <h3>Response Model</h3>
        <p><code>GenericResponse[FormWebhookResponseData]</code></p>
        <div class="code-block">
          <pre><code># app/api/v1/endpoints/webhooks/form.py
class FormWebhookResponseData(BaseModel):
    status: str
    message: str
    classification_result: Optional[Any] = None
    hubspot_update_status: Optional[str] = None</code></pre>
        </div>
      </section>
    `;
  }

  getHubspotSection() {
    return /* html */ `
      <section id="hubspot" class="content-section ${this.state.activeSection === 'hubspot' ? 'active' : ''}">
        <h2>HubSpot Webhook</h2>
        <div class="endpoint-details">
          <div class="endpoint-url">
            <strong>Endpoint:</strong> 
            <code>POST /api/v1/webhook/hubspot</code>
          </div>
          <div class="endpoint-file">
            <strong>File:</strong> 
            <code>app/api/v1/endpoints/webhooks/hubspot.py</code>
          </div>
          <div class="endpoint-purpose">
            <strong>Purpose:</strong> 
            <p>Handles direct contact data payloads from HubSpot, typically triggered by HubSpot Workflows (e.g., when a contact property changes or a new contact is created meeting certain criteria). This allows Stahla to react to changes in HubSpot CRM in real-time.</p>
          </div>
        </div>
        
        <h3>Request Model</h3>
        <p><code>app.models.webhook.HubSpotContactDataPayload</code></p>
        <div class="code-block">
          <pre><code># app/models/webhook.py
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

# Supporting models like HubSpotPropertyDetail, HubSpotIdentityProfile, etc., are also in app/models/webhook.py</code></pre>
        </div>
        
        <h3>Processing Workflow</h3>
        <ol>
          <li>Receives <code>HubSpotContactDataPayload</code>.</li>
          <li>Extracts contact properties using <code>_extract_simple_properties</code>.</li>
          <li>Checks if the contact data is complete for immediate processing using <code>_is_hubspot_contact_complete</code> helper.</li>
          <li><strong>If complete:</strong>
            <ul>
              <li>Prepares <code>ClassificationInput</code> from the HubSpot data using <code>prepare_classification_input</code>.</li>
              <li>Classifies the lead data using <code>classification_manager.classify_lead_data</code>.</li>
              <li>Updates the HubSpot lead with classification results and notifies n8n in the background via <code>_update_hubspot_lead_after_classification</code>.</li>
            </ul>
          </li>
          <li><strong>If incomplete:</strong>
            <ul>
              <li>Triggers a Bland.ai call to gather missing information in the background via <code>_trigger_bland_call_for_hubspot</code>.</li>
            </ul>
          </li>
        </ol>
        
        <h3>Response Model</h3>
        <p><code>GenericResponse[HubSpotWebhookResponseData]</code></p>
        <div class="code-block">
          <pre><code># app/api/v1/endpoints/webhooks/hubspot.py
class HubSpotWebhookResponseData(BaseModel):
    status: str
    message: str</code></pre>
        </div>
      </section>
    `;
  }

  getVoiceSection() {
    return /* html */ `
      <section id="voice" class="content-section ${this.state.activeSection === 'voice' ? 'active' : ''}">
        <h2>Voice Webhook (Bland.ai)</h2>
        <div class="endpoint-details">
          <div class="endpoint-url">
            <strong>Endpoint:</strong> 
            <code>POST /api/v1/webhook/voice</code>
          </div>
          <div class="endpoint-file">
            <strong>File:</strong> 
            <code>app/api/v1/endpoints/webhooks/voice.py</code>
          </div>
          <div class="endpoint-purpose">
            <strong>Purpose:</strong> 
            <p>Receives voice call transcripts, summaries, recordings, and other metadata from Bland.ai after an automated call has completed.</p>
          </div>
        </div>
        
        <h3>Request Model</h3>
        <p><code>app.models.bland.BlandWebhookPayload</code></p>
        <div class="code-block">
          <pre><code># app/models/bland.py
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
    # ... other fields like pathway_id, analysis, etc.</code></pre>
        </div>
        
        <h3>Processing Workflow</h3>
        <ol>
          <li>Receives <code>BlandWebhookPayload</code>.</li>
          <li>Processes the transcript using <code>bland_manager.process_incoming_transcript</code> to extract structured data.</li>
          <li>Checks for <code>hubspot_contact_id</code> and <code>hubspot_lead_id</code> in the payload's <code>variables</code> or <code>metadata</code>.</li>
          <li>If <code>hubspot_contact_id</code> is present, fetches existing contact details from HubSpot.</li>
          <li>Merges data from the call, form submission data (if available), and fetched HubSpot properties.</li>
          <li>Prepares <code>ClassificationInput</code> using <code>prepare_classification_input</code> with the merged data.</li>
          <li>Classifies the lead data using <code>classification_manager.classify_lead_data</code>.</li>
          <li>Updates the <code>classification_input</code> object with any newly refined details.</li>
          <li><strong>HubSpot Integration:</strong>
            <ul>
              <li><strong>If existing <code>hubspot_lead_id</code> and <code>hubspot_contact_id</code> were found:</strong> Updates the existing HubSpot lead.</li>
              <li><strong>Otherwise:</strong> Creates a new contact (if needed) and a new lead in HubSpot.</li>
            </ul>
          </li>
        </ol>
        
        <h3>Response Model</h3>
        <p><code>GenericResponse[VoiceWebhookResponseData]</code></p>
        <div class="code-block">
          <pre><code># app/api/v1/endpoints/webhooks/voice.py
class VoiceWebhookResponseData(BaseModel):
    status: str
    source: str # Indicates 'voice'
    action: str # e.g., 'classification_complete'
    classification: Optional[ClassificationOutput] = None # The result from classification_manager
    hubspot_contact_id: Optional[str] = None # ID of the created/updated HubSpot contact
    hubspot_lead_id: Optional[str] = None # ID of the created/updated HubSpot lead</code></pre>
        </div>
      </section>
    `;
  }

  getPricingSection() {
    return /* html */ `
      <section id="pricing" class="content-section ${this.state.activeSection === 'pricing' ? 'active' : ''}">
        <h2>Pricing Webhooks</h2>
        <div class="endpoint-details">
          <div class="endpoint-file">
            <strong>File:</strong> 
            <code>app/api/v1/endpoints/webhooks/pricing.py</code>
          </div>
          <div class="endpoint-auth">
            <strong>Authentication:</strong> 
            <p>All pricing webhooks require an API key via <code>Depends(get_api_key)</code>.</p>
          </div>
        </div>
        
        <h3>Asynchronous Location Lookup</h3>
        <div class="endpoint-details">
          <div class="endpoint-url">
            <strong>Endpoint:</strong> 
            <code>POST /api/v1/webhook/location/lookup</code>
          </div>
          <div class="endpoint-purpose">
            <strong>Purpose:</strong> 
            <p>Accepts a delivery location and triggers an asynchronous background task to calculate and cache the distance to the nearest Stahla branch. This is used to pre-warm the cache for faster quote generation later.</p>
          </div>
        </div>
        
        <h4>Request Model</h4>
        <p><code>app.models.location.LocationLookupRequest</code></p>
        <div class="code-block">
          <pre><code># app/models/location.py
class LocationLookupRequest(BaseModel):
    delivery_location: str = Field(..., description="Full delivery address for distance lookup.")</code></pre>
        </div>
        
        <h4>Processing Workflow</h4>
        <ol>
          <li>Receives <code>delivery_location</code>.</li>
          <li>Adds a background task to call <code>location_service.prefetch_distance</code>.</li>
          <li>Increments a Redis counter for total location lookups.</li>
          <li>Returns a <code>202 Accepted</code> status immediately.</li>
        </ol>
        
        <h4>Response Model</h4>
        <p><code>GenericResponse[MessageResponse]</code></p>
        <div class="code-block">
          <pre><code># app/models/common.py
class MessageResponse(BaseModel):
    message: str</code></pre>
        </div>
        
        <h3>Synchronous Location Lookup (for Testing)</h3>
        <div class="endpoint-details">
          <div class="endpoint-url">
            <strong>Endpoint:</strong> 
            <code>POST /api/v1/webhook/location/lookup/sync</code>
          </div>
          <div class="endpoint-purpose">
            <strong>Purpose:</strong> 
            <p>Accepts a delivery location, calculates the distance to the nearest branch synchronously, and returns the result. Primarily for testing the location service directly.</p>
          </div>
        </div>
        
        <h4>Request Model</h4>
        <p><code>app.models.location.LocationLookupRequest</code> (same as async version)</p>
        
        <h4>Processing Workflow</h4>
        <ol>
          <li>Receives <code>delivery_location</code>.</li>
          <li>Calls <code>location_service.get_distance_to_nearest_branch</code> directly.</li>
          <li>Returns the <code>LocationLookupResponse</code> containing results.</li>
        </ol>
        
        <h4>Response Model</h4>
        <p><code>GenericResponse[LocationLookupResponse]</code></p>
        <div class="code-block">
          <pre><code># app/models/location.py
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
    address: str</code></pre>
        </div>
        
        <h3>Quote Generation</h3>
        <div class="endpoint-details">
          <div class="endpoint-url">
            <strong>Endpoint:</strong> 
            <code>POST /api/v1/webhook/quote</code>
          </div>
          <div class="endpoint-purpose">
            <strong>Purpose:</strong> 
            <p>Calculates a detailed price quote based on provided information. This is the core pricing engine endpoint.</p>
          </div>
        </div>
        
        <h4>Request Model</h4>
        <p><code>app.models.quote.QuoteRequest</code></p>
        <div class="code-block">
          <pre><code># app/models/quote.py
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
    qty: int</code></pre>
        </div>
        
        <h4>Processing Workflow</h4>
        <ol>
          <li>Receives <code>QuoteRequest</code>.</li>
          <li>Calls <code>quote_service.build_quote</code>, which:
            <ul>
              <li>Fetches product details and base rates.</li>
              <li>Fetches delivery distance (from cache or calculates it).</li>
              <li>Applies pricing rules, seasonal adjustments, and delivery tier calculations.</li>
              <li>Calculates costs for extras.</li>
              <li>Assembles all details into a <code>QuoteResponse</code> object.</li>
            </ul>
          </li>
          <li>Calculates total processing time and updates <code>QuoteResponse.metadata</code>.</li>
          <li>Increments Redis counters for total and successful quote requests.</li>
          <li>Returns the detailed quote.</li>
        </ol>
        
        <h4>Response Model</h4>
        <p><code>GenericResponse[QuoteResponse]</code></p>
        <div class="code-block">
          <pre><code># app/models/quote.py
class QuoteResponse(BaseModel):
    request_id: str
    quote_id: str = Field(default_factory=lambda: f"QT-{uuid.uuid4()}")
    quote: QuoteBody
    location_details: Optional[LocationDetails] = None
    metadata: QuoteMetadata

# QuoteBody, LocationDetails, QuoteMetadata, LineItem, DeliveryCostDetails, etc.,
# are all defined in app/models/quote.py, providing a rich, structured quote.</code></pre>
        </div>
      </section>
    `;
  }

  getModelsSection() {
    return /* html */ `
      <section id="models" class="content-section ${this.state.activeSection === 'models' ? 'active' : ''}">
        <h2>Webhook Data Models Deep Dive</h2>
        <p>The primary Pydantic models defining the structure of webhook payloads are crucial for data validation, clarity, and ensuring consistent interactions. They are located in the <code>app/models/</code> directory.</p>
        
        <h3>app/models/webhook.py</h3>
        <ul>
          <li><strong>FormPayload:</strong> Captures all expected fields from a web form submission. Designed to align with <code>ClassificationInput</code> for easier data mapping. Includes fields for contact info, event details, location, product interest, site requirements, and metadata like <code>form_id</code> and <code>submission_timestamp</code>. Uses <code>Config.extra = 'allow'</code> to accommodate any additional fields a form might send.</li>
          <li><strong>HubSpotWebhookEvent:</strong> Represents a single event in a HubSpot webhook batch (though the current implementation uses <code>HubSpotContactDataPayload</code> for direct data pushes).</li>
          <li><strong>HubSpotContactDataPayload:</strong> A comprehensive model for the rich data HubSpot sends via its direct contact data webhooks (e.g., through Workflows). It includes the contact's <code>vid</code> (HubSpot ID), a detailed <code>properties</code> dictionary (using <code>HubSpotPropertyDetail</code> which includes value and versions), <code>form_submissions</code>, <code>list_memberships</code>, <code>identity_profiles</code> (tracking different ways a contact is identified), and <code>associated_company</code> details. Uses <code>populate_by_name = True</code> to handle HubSpot's snake_case and kebab-case field names.</li>
        </ul>
        
        <h3>app/models/bland.py</h3>
        <ul>
          <li><strong>BlandWebhookPayload:</strong> Defines the structure for data received from Bland.ai after a call. Includes <code>call_id</code>, <code>concatenated_transcript</code>, <code>summary</code>, <code>recording_url</code>, and significantly, <code>variables</code>. The <code>variables</code> field is a dictionary that Stahla can populate when initiating the call, often used to pass <code>hubspot_contact_id</code>, <code>hubspot_lead_id</code>, or <code>form_submission_data</code> for context, which the webhook then uses to link the call back to the originating lead or form.</li>
          <li><strong>BlandTranscriptEntry:</strong> Represents individual segments of the call transcript with speaker and text.</li>
        </ul>
        
        <h3>app/models/location.py</h3>
        <ul>
          <li><strong>LocationLookupRequest:</strong> Simple model with <code>delivery_location</code> (a string) for both asynchronous and synchronous distance lookups.</li>
          <li><strong>LocationLookupResponse:</strong> Contains an optional <code>DistanceResult</code> (with <code>nearest_branch</code>, <code>distance_miles</code>, <code>duration_seconds</code>) and <code>processing_time_ms</code> for the synchronous endpoint.</li>
          <li><strong>BranchLocation:</strong> Stores the name and address of a Stahla branch.</li>
          <li><strong>DistanceResult:</strong> Detailed result of a distance calculation including the nearest branch, delivery location, distance in miles and meters, and duration in seconds.</li>
        </ul>
        
        <h3>app/models/quote.py</h3>
        <ul>
          <li><strong>QuoteRequest:</strong> Input for generating a quote. Includes <code>request_id</code>, <code>delivery_location</code>, <code>trailer_type</code> (product ID), <code>rental_start_date</code>, <code>rental_days</code>, <code>usage_type</code> (event/commercial), and a list of <code>ExtraInput</code> (extra item ID and quantity).</li>
          <li><strong>QuoteResponse:</strong> The comprehensive output. Contains the original <code>request_id</code>, a new <code>quote_id</code>, a <code>QuoteBody</code> object, <code>LocationDetails</code>, and <code>QuoteMetadata</code>.</li>
          <li><strong>QuoteBody:</strong> The core of the quote, including <code>line_items</code>, <code>subtotal</code>, <code>delivery_details</code> (with <code>DeliveryCostDetails</code>), <code>rental_details</code>, <code>product_details</code>, and <code>budget_details</code>.</li>
          <li><strong>LineItem:</strong> Represents individual items in the quote (e.g., trailer rental, delivery, extras) with description, quantity, unit price, and total.</li>
          <li><strong>DeliveryCostDetails:</strong> Detailed breakdown of how delivery cost was calculated (miles, reason, rates, multipliers).</li>
          <li><strong>LocationDetails:</strong> Information about the delivery address, nearest branch, distance, and drive time.</li>
          <li><strong>RentalDetails:</strong> Start/end dates, duration, pricing tier, seasonal adjustments.</li>
          <li><strong>ProductDetails:</strong> ID, name, description, rates, features of the main trailer.</li>
          <li><strong>BudgetDetails:</strong> Subtotal, estimated taxes/fees, total, rate equivalents, cost breakdown.</li>
          <li><strong>QuoteMetadata:</strong> Timestamps, version, source system, calculation time, warnings.</li>
        </ul>
        
        <p>These models ensure data integrity and provide clear schemas for incoming webhook data and the structured data passed between services.</p>
      </section>
    `;
  }

  getHelpersSection() {
    return /* html */ `
      <section id="helpers" class="content-section ${this.state.activeSection === 'helpers' ? 'active' : ''}">
        <h2>Webhook Helper Functions Deep Dive</h2>
        <p>Common logic shared across webhook endpoints, especially for interacting with services like Bland.ai and HubSpot, is encapsulated in helper functions within <code>app/api/v1/endpoints/webhooks/helpers.py</code>. The <code>prepare_classification_input</code> function is a key component residing in <code>app/api/v1/endpoints/prepare.py</code>.</p>
        
        <h3>app/api/v1/endpoints/webhooks/helpers.py</h3>
        
        <h4>_is_form_complete(payload: FormPayload) -> bool</h4>
        <ul>
          <li><strong>Purpose:</strong> Validates if a <code>FormPayload</code> from a web submission contains a predefined set of minimum required fields (e.g., name, email, phone, product interest, location, start date).</li>
          <li><strong>Logic:</strong> Checks that each required field in the payload is not None and not an empty string.</li>
          <li><strong>Usage:</strong> Called by the <code>/form</code> webhook to decide whether to classify the lead directly or trigger a follow-up call.</li>
        </ul>
        
        <h4>_trigger_bland_call(payload: FormPayload)</h4>
        <ul>
          <li><strong>Purpose:</strong> Initiates a Bland.ai outbound call if a form submission is incomplete.</li>
          <li><strong>Logic:</strong> Constructs a <code>BlandCallbackRequest</code>. Populates <code>request_data</code> with details from the <code>FormPayload</code> (name, email, product interest, etc.) for the AI agent to use. Populates <code>metadata</code> with <code>source: "web_form_incomplete"</code> and other form details for tracking. Sets the Bland.ai webhook URL to <code>/webhook/voice</code> to receive results. Calls <code>bland_manager.initiate_callback</code>.</li>
          <li><strong>Usage:</strong> Called as a background task by the <code>/form</code> webhook if <code>_is_form_complete</code> is false.</li>
        </ul>
        
        <h4>_handle_hubspot_update(classification_result: ClassificationResult, input_data: ClassificationInput) -> Tuple[Optional[str], Optional[str]]</h4>
        <ul>
          <li><strong>Purpose:</strong> Central function to create/update a HubSpot Contact and then create a <em>new</em> HubSpot Lead (Deal). This is typically used for new leads originating from forms, voice calls, or emails where no pre-existing HubSpot Lead ID is known.</li>
          <li><strong>Logic:</strong>
            <ol>
              <li>Ensures <code>input_data.email</code> is present.</li>
              <li>Creates/updates a HubSpot contact using <code>hubspot_manager.create_or_update_contact</code> with properties mapped from <code>input_data</code> and <code>classification_result.classification.metadata</code> (e.g., call summaries).</li>
              <li>If contact creation/update is successful, prepares <code>HubSpotLeadProperties</code> by mapping data from <code>input_data</code> and <code>classification_result</code> (e.g., event type, stall count, AI classification details like <code>ai_lead_type</code>, <code>reasoning</code>, <code>routing_suggestion</code>).</li>
              <li>Creates a new HubSpot lead using <code>hubspot_manager.create_lead</code>.</li>
              <li>If lead creation is successful and the lead is not disqualified, it attempts to assign an owner using <code>hubspot_manager.get_next_owner_id()</code> and then updates the lead.</li>
              <li>Triggers an n8n handoff automation via <code>trigger_n8n_handoff_automation</code> if the lead is not disqualified, passing all relevant data.</li>
            </ol>
          </li>
          <li><strong>Returns:</strong> A tuple of <code>(contact_id, lead_id)</code>.</li>
          <li><strong>Usage:</strong> Called as a background task by <code>/form</code> and <code>/voice</code> webhooks for new lead creation flows.</li>
        </ul>
        
        <h4>_is_hubspot_contact_complete(contact_properties: dict) -> bool</h4>
        <ul>
          <li><strong>Purpose:</strong> Checks if data received directly from HubSpot is sufficient to proceed with classification and lead creation, or if a Bland.ai call is needed to gather more info.</li>
          <li><strong>Logic:</strong> Checks for the presence and validity of key HubSpot contact properties (e.g., <code>firstname</code>, <code>email</code>, <code>phone</code>, <code>event_or_job_address</code>, <code>event_start_date</code>, <code>what_service_do_you_need_</code>). Critically, it also considers if mandatory <em>lead</em> fields (like <code>quote_urgency</code>) can be derived. Currently, this function often returns <code>False</code> because some lead-specific qualifying information is usually not present in the initial HubSpot contact data alone, thus typically directing the flow towards a qualification call.</li>
          <li><strong>Usage:</strong> Called by the <code>/hubspot</code> webhook.</li>
        </ul>
        
        <h4>_trigger_bland_call_for_hubspot(contact_id: str, contact_properties: dict)</h4>
        <ul>
          <li><strong>Purpose:</strong> Initiates a Bland.ai call when the <code>/webhook/hubspot</code> endpoint receives contact data deemed incomplete by <code>_is_hubspot_contact_complete</code>.</li>
          <li><strong>Logic:</strong> Similar to <code>_trigger_bland_call</code>, but <code>request_data</code> is populated from <code>contact_properties</code> (HubSpot data). <code>metadata</code> includes <code>source: "hubspot_incomplete_contact"</code> and the <code>hubspot_contact_id</code> for tracking. Calls <code>bland_manager.initiate_callback</code>.</li>
          <li><strong>Usage:</strong> Called as a background task by the <code>/hubspot</code> webhook if data is incomplete.</li>
        </ul>
        
        <h4>_update_hubspot_lead_after_classification(classification_result: ClassificationResult, input_data: ClassificationInput, contact_id: str)</h4>
        <ul>
          <li><strong>Purpose:</strong> This helper is intended to create a <em>new</em> HubSpot Lead and associate it with an <em>existing</em> HubSpot Contact (identified by <code>contact_id</code>) after data (potentially from a Bland.ai call triggered for an existing contact) has been classified.</li>
          <li><strong>Logic:</strong>
            <ol>
              <li>Ensures <code>classification_output</code> is present.</li>
              <li>Prepares <code>HubSpotLeadProperties</code> from <code>classification_result</code> and <code>input_data</code>.</li>
              <li>Creates a new HubSpot lead using <code>hubspot_manager.create_lead</code>, ensuring it's associated with the provided <code>contact_id</code>.</li>
              <li>If lead creation is successful, assigns an owner and triggers n8n handoff, similar to <code>_handle_hubspot_update</code>.</li>
            </ol>
          </li>
          <li><strong>Usage:</strong> Called as a background task by the <code>/voice</code> webhook when a call was made for an existing HubSpot contact (identified by <code>hubspot_contact_id</code> in call metadata) and now a lead needs to be created based on the call outcome and classification. Also used by the <code>/hubspot</code> webhook if the initial data was deemed complete enough to classify and then create a lead.</li>
        </ul>
        
        <h3>app/api/v1/endpoints/prepare.py</h3>
        <h4>prepare_classification_input(source: str, raw_data: dict, extracted_data: dict) -> ClassificationInput</h4>
        <ul>
          <li><strong>Purpose:</strong> A crucial utility to standardize and transform data from various sources (web forms, Bland.ai voice calls, direct HubSpot data) into a single, consistent <code>ClassificationInput</code> model. This model is then used by the <code>classification_manager</code>.</li>
          <li><strong>Logic:</strong> Takes a <code>source</code> string (e.g., "webform", "voice", "hubspot_webhook_direct"), the <code>raw_data</code> payload from the source, and a dictionary of <code>extracted_data</code> (which might be the raw payload itself or a processed version of it). It then carefully maps fields from <code>extracted_data</code> to the corresponding fields in the <code>ClassificationInput</code> model, using <code>.get()</code> with defaults to handle missing fields gracefully.</li>
          <li><strong>Returns:</strong> An instance of <code>ClassificationInput</code>.</li>
          <li><strong>Usage:</strong> Called by all webhooks (<code>/form</code>, <code>/hubspot</code>, <code>/voice</code>) that feed into the lead classification process. This ensures the <code>classification_manager</code> receives data in a predictable format, regardless of its origin.</li>
        </ul>
        
        <p>These helpers and the <code>prepare_classification_input</code> function are essential for modularizing the webhook logic, promoting code reuse, and centralizing complex interactions with external services and the internal classification system.</p>
      </section>
    `;
  }

  _setupEventListeners() {
    // Handle navigation link clicks
    this.shadowObj.addEventListener('click', (event) => {
      const navLink = event.target.closest('.nav-link');
      if (navLink) {
        const section = navLink.dataset.section;
        const category = navLink.dataset.category;
        
        if (category) {
          this._toggleCategoryExpansion(category);
        } else if (section) {
          this._navigateToSection(section);
        }
      }
      
      // Handle webhook item clicks in the grid
      const webhookItem = event.target.closest('.webhook-item');
      if (webhookItem) {
        const webhook = webhookItem.dataset.webhook;
        if (webhook) {
          this._navigateToSection(webhook);
        }
      }
      
      // Toggle mobile nav
      if (event.target.closest('#toggle-nav')) {
        this.state.expandedSubmenu = !this.state.expandedSubmenu;
        this.render();
      }
      
      // Handle copy button clicks
      const copyBtn = event.target.closest('.copy-btn');
      if (copyBtn) {
        const textToCopy = copyBtn.dataset.text;
        if (textToCopy) {
          navigator.clipboard.writeText(textToCopy).then(() => {
            const originalText = copyBtn.innerText;
            copyBtn.innerText = 'Copied!';
            setTimeout(() => {
              copyBtn.innerText = originalText;
            }, 2000);
          });
        }
      }
    });
  }
  
  /**
   * Toggle category expansion in the sidebar
   * @param {string} category - The category to toggle
   */
  _toggleCategoryExpansion(category) {
    if (this.state.expandedCategories.has(category)) {
      this.state.expandedCategories.delete(category);
    } else {
      this.state.expandedCategories.add(category);
    }
    this.render();
  }
  
  /**
   * Navigate to a specific section
   * @param {string} section - The section to navigate to
   */
  _navigateToSection(section) {
    this.state.activeSection = section;
    this.render();
  }

  getStyles() {
    return /* CSS */`
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-main);
          color: var(--text-color);
          line-height: 1.6;
        }
        
        *,
        *:after,
        *:before {
          box-sizing: border-box;
          font-family: inherit;
          -webkit-box-sizing: border-box;
        }

        *:focus {
          outline: inherit !important;
        }

        *::-webkit-scrollbar {
          width: 3px;
        }

        *::-webkit-scrollbar-track {
          background: var(--scroll-bar-background);
        }

        *::-webkit-scrollbar-thumb {
          width: 3px;
          background: var(--scroll-bar-linear);
          border-radius: 50px;
        }
        
        .webhooks-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .webhooks-docs-header {
          padding: 0;
        }
        
        .webhooks-docs-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .webhooks-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .webhooks-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .webhooks-docs-sidebar {
          width: 260px;
          position: sticky;
          top: 20px;
          height: calc(100vh - 40px);
          padding-right: 10px;
          overflow-y: auto;
          position: sticky;
          overflow: auto;
          -ms-overflow-style: none; /* IE 11 */
          scrollbar-width: none; /* Firefox 64 */
        }

        .webhooks-docs-sidebar::-webkit-scrollbar {
          display: none;
        }
        
        .sidebar-content {
          border-radius: 8px;
          background-color: var(--background);
        }
        
        .nav-sections {
          padding: 0;
        }
        
        .nav-section {
          padding: 0;
          margin-bottom: 5px;
        }
        
        .nav-link {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 15px;
          font-size: 0.9rem;
          color: var(--text-color);
          text-decoration: none;
          border-radius: 6px;
          cursor: pointer;
          transition: background-color 0.2s;
        }
        
        .nav-link:hover {
          background-color: var(--hover-background);
        }
        
        .nav-link.active {
          background-color: var(--tab-background);
          color: var(--accent-color);
          font-weight: 500;
        }
        
        .nav-link.parent {
          font-weight: 600;
          color: var(--text-color);
        }
        
        .nav-link.sub {
          padding-left: 32px;
          font-size: 0.9rem;
          position: relative;
          display: flex;
        }

        div.subnav > a.nav-link.sub::before {
          content: '-';
          position: absolute;
          left: 16px;
          top: 50%;
          transform: translateY(-50%);
          z-index: 1;
        }
        
        .subnav {
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.3s ease-out;
        }
        
        .nav-section.expanded .subnav {
          max-height: 500px;
          transition: max-height 0.5s ease-in;
        }
        
        .nav-section.collapsed .subnav {
          max-height: 0;
        }
        
        .mobile-toggle {
          display: none;
        }
        
        .webhooks-docs-main {
          flex: 1;
          padding: 20px 0;
          min-width: 0;
        }
        
        .webhooks-content-container {
          padding: 0;
        }
        
        .content-section {
          display: none;
          padding: 0;
          background-color: var(--background);
          border-radius: 8px;
        }
        
        .content-section.active {
          display: block;
        }
        
        .content-section h2 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 20px;
          color: var(--title-color);
        }
        
        .content-section h3 {
          font-size: 1.4rem;
          font-weight: 500;
          margin: 30px 0 15px;
          color: var(--title-color);
        }
        
        .content-section h4 {
          font-size: 1.1rem;
          font-weight: 500;
          margin: 25px 0 10px;
          color: var(--title-color);
        }
        
        .content-section p {
          margin: 0 0 15px;
        }
        
        .content-section ul, .content-section ol {
          margin: 0 0 15px;
          padding-left: 25px;
        }
        
        .content-section li {
          margin-bottom: 8px;
        }
        
        .content-section code {
          font-family: var(--font-mono);
          background-color: var(--stat-background);
          padding: 2px 5px;
          border-radius: 4px;
          font-size: 0.9em;
        }
        
        .code-block {
          position: relative;
          margin: 15px 0;
          border-radius: 8px;
          overflow: hidden;
        }
        
        .code-block pre {
          margin: 0;
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 8px;
          overflow-x: auto;
          font-family: var(--font-mono);
          font-size: 0.85rem;
        }
        
        .code-block code {
          background: none;
          padding: 0;
          border-radius: 0;
          font-family: var(--font-mono);
        }
        
        .copy-btn {
          position: absolute;
          top: 5px;
          right: 5px;
          padding: 3px 8px;
          background-color: var(--background);
          border: var(--border-button);
          color: var(--text-color);
          border-radius: 4px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .copy-btn:hover {
          background-color: var(--hover-background);
        }
        
        .webhook-overview {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .webhook-card {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
        }
        
        .webhook-card h4 {
          margin: 0 0 10px;
          color: var(--title-color);
        }
        
        .webhook-card p {
          margin: 0;
          font-size: 0.9rem;
        }
        
        .webhooks-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .webhook-item {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .webhook-item:hover {
          border-color: var(--accent-color);
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow-alt);
        }
        
        .webhook-item h3 {
          margin: 0 0 10px;
          font-size: 1.2rem;
          color: var(--title-color);
        }
        
        .webhook-item code {
          display: block;
          margin: 5px 0;
          font-size: 0.85rem;
        }
        
        .webhook-item p {
          margin: 10px 0 0;
          font-size: 0.9rem;
        }
        
        .endpoint-details {
          background-color: var(--stat-background);
          padding: 15px;
          border-radius: 6px;
          margin-bottom: 20px;
        }
        
        .endpoint-details > div {
          margin-bottom: 10px;
        }
        
        .endpoint-details > div:last-child {
          margin-bottom: 0;
        }
        
        .endpoint-url code, .endpoint-file code {
          background: var(--background);
        }
        
        @media (max-width: 900px) {
          .webhooks-docs-content {
            flex-direction: column;
          }
          
          .webhooks-docs-sidebar {
            width: 100%;
            position: relative;
            top: 0;
            height: auto;
            max-height: 300px;
            overflow-y: hidden;
          }
          
          .mobile-toggle {
            display: block;
            padding: 10px 15px;
            border-bottom: var(--border);
          }
          
          .mobile-toggle button {
            background: none;
            border: none;
            color: var(--text-color);
            cursor: pointer;
            padding: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          
          .nav-sections {
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.3s ease-out;
            padding: 0;
          }
          
          .nav-sections.expanded {
            max-height: 500px;
            overflow-y: auto;
            transition: max-height 0.5s ease-in;
            padding: 15px 0;
          }
        }
      </style>
    `;
  }
}