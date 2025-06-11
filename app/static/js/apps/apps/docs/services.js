export default class ServicesDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0;

    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedServices: new Set(),
      expandedSchemas: new Set(),
      expandedSubmenu: false,
      expandedCategories: new Set(['services'])
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
    console.log(`Rendering Services docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return `
      ${this.getStyles()}
      <div class="services-docs">
        <div class="services-docs-content">
          <nav class="services-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="services-docs-main" class="services-docs-main">
            <div id="content-container" class="services-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return `
      <header class="services-docs-header">
        <h1>Stahla AI SDR Application Services</h1>
        <p>A comprehensive guide to the services and utilities that power the Stahla AI SDR application</p>
      </header>
    `;
  }

  getSidebar() {
    return `
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
          <div class="nav-section ${this.isServicesActive() ? 'active' : ''} ${this.state.expandedCategories.has('services') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-section="services" data-category="services">
              <span class="link-text">Core Services</span>
              <span class="expand-icon">${this.state.expandedCategories.has('services') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'bland' ? 'active' : ''}" data-section="bland">Bland AI Service</a>
              <a class="nav-link sub ${this.state.activeSection === 'hubspot' ? 'active' : ''}" data-section="hubspot">HubSpot Service</a>
              <a class="nav-link sub ${this.state.activeSection === 'n8n' ? 'active' : ''}" data-section="n8n">n8n Integration</a>
              <a class="nav-link sub ${this.state.activeSection === 'auth' ? 'active' : ''}" data-section="auth">Authentication</a>
              <a class="nav-link sub ${this.state.activeSection === 'classify' ? 'active' : ''}" data-section="classify">Classification</a>
              <a class="nav-link sub ${this.state.activeSection === 'dashboard' ? 'active' : ''}" data-section="dashboard">Dashboard</a>
              <a class="nav-link sub ${this.state.activeSection === 'location' ? 'active' : ''}" data-section="location">Location</a>
              <a class="nav-link sub ${this.state.activeSection === 'mongo' ? 'active' : ''}" data-section="mongo">MongoDB</a>
              <a class="nav-link sub ${this.state.activeSection === 'quote' ? 'active' : ''}" data-section="quote">Quoting</a>
              <a class="nav-link sub ${this.state.activeSection === 'redis' ? 'active' : ''}" data-section="redis">Redis</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  isServicesActive() {
    const servicesSections = ['services', 'bland', 'hubspot', 'n8n', 'auth', 'classify', 'dashboard', 'location', 'mongo', 'quote', 'redis'];
    return servicesSections.includes(this.state.activeSection);
  }

  getContentForSection(section) {
    switch (section) {
      case 'introduction':
        return this.getIntroductionSection();
      case 'services':
        return this.getServicesSection();
      case 'bland':
        return this.getBlandSection();
      case 'hubspot':
        return this.getHubspotSection();
      case 'n8n':
        return this.getN8nSection();
      case 'auth':
        return this.getAuthSection();
      case 'classify':
        return this.getClassifySection();
      case 'dashboard':
        return this.getDashboardSection();
      case 'location':
        return this.getLocationSection();
      case 'mongo':
        return this.getMongoSection();
      case 'quote':
        return this.getQuoteSection();
      case 'redis':
        return this.getRedisSection();
      default:
        return this.getIntroductionSection();
    }
  }

  getIntroductionSection() {
    return `
      <section id="introduction" class="content-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
        <h2>Application Services and Utilities</h2>
        <p>This document outlines the various services and utility modules used within the Stahla AI SDR application. These components handle core business logic, interactions with external APIs, and data processing.</p>
        
        <h3>Services Overview</h3>
        <p>The application is built around a set of specialized service classes, each responsible for specific domains of functionality. These services encapsulate business logic, API interactions, and data operations, providing a clean and maintainable architecture.</p>
        
        <div class="service-overview">
          <div class="service-card">
            <h4>Bland AI Service</h4>
            <p>Manages interactions with the Bland.ai API for voice calls and conversations.</p>
          </div>
          <div class="service-card">
            <h4>HubSpot Service</h4>
            <p>Manages CRM operations through the HubSpot API for contacts, companies, deals, and tickets.</p>
          </div>
          <div class="service-card">
            <h4>Classification Service</h4>
            <p>Determines lead type and quality through rule-based and AI-powered classification.</p>
          </div>
        </div>
      </section>
    `;
  }

  getServicesSection() {
    return `
      <section id="services" class="content-section ${this.state.activeSection === 'services' ? 'active' : ''}">
        <h2>Core Services</h2>
        <p>The Stahla AI SDR application is structured around a set of specialized service classes that handle specific domains of functionality. Each service encapsulates related business logic, API interactions, and data operations.</p>
        
        <p>Navigate to individual service documentation using the sidebar or select from the options below:</p>
        
        <div class="services-grid">
          <div class="service-item" data-service="bland">
            <h3>Bland AI Service</h3>
            <p>Manages interactions with the Bland.ai API for voice calls.</p>
          </div>
          <div class="service-item" data-service="hubspot">
            <h3>HubSpot Service</h3>
            <p>Interacts with the HubSpot CRM API for lead management.</p>
          </div>
          <div class="service-item" data-service="n8n">
            <h3>n8n Integration</h3>
            <p>Facilitates workflow automation through n8n webhooks.</p>
          </div>
          <div class="service-item" data-service="auth">
            <h3>Authentication</h3>
            <p>Manages API keys and authentication processes.</p>
          </div>
          <div class="service-item" data-service="classify">
            <h3>Classification</h3>
            <p>Classifies leads using rules and AI.</p>
          </div>
          <div class="service-item" data-service="dashboard">
            <h3>Dashboard</h3>
            <p>Provides dashboard data and analytics.</p>
          </div>
          <div class="service-item" data-service="location">
            <h3>Location</h3>
            <p>Handles geocoding and location-based processing.</p>
          </div>
          <div class="service-item" data-service="mongo">
            <h3>MongoDB</h3>
            <p>Provides database interaction services.</p>
          </div>
          <div class="service-item" data-service="quote">
            <h3>Quoting</h3>
            <p>Manages product/service quote generation and lifecycle.</p>
          </div>
          <div class="service-item" data-service="redis">
            <h3>Redis</h3>
            <p>Provides caching and temporary storage services.</p>
          </div>
        </div>
      </section>
    `;
  }

  // This is the start of the individual service sections

  getBlandSection() {
    return `
      <section id="bland" class="content-section ${this.state.activeSection === 'bland' ? 'active' : ''}">
        <h2>Bland AI Service</h2>
        <p>The Bland AI Service manages all interactions with the Bland.ai API, facilitating voice calls, managing call pathways, and synchronizing tool definitions with Bland.ai.</p>
        
        <h3>Class: BlandAIManager</h3>
        <div class="code-block">
          <pre><code>class BlandAIManager:
    def __init__(
        self, 
        api_key: str, 
        base_url: str, 
        pathway_id: Optional[str] = None, 
        mongo_service: Optional[MongoService] = None, 
        background_tasks: Optional[BackgroundTasks] = None
    )</code></pre>
        </div>
        
        <h3>Key Responsibilities</h3>
        <ul>
          <li>Loading call pathway definitions from local JSON files (<code>app/assets/call.json</code>).</li>
          <li>Loading tool definitions for location and quoting from local JSON files (<code>app/assets/location.json</code>, <code>app/assets/quote.json</code>).</li>
          <li>Synchronizing pathways and tools with Bland.ai by updating existing configurations or creating new ones if necessary.</li>
          <li>Initiating outbound calls via the Bland.ai API (<code>POST /v1/calls</code>).</li>
          <li>Making HTTP requests to the Bland.ai API using an <code>httpx.AsyncClient</code>.</li>
          <li>Logging call events, API interactions, and errors, potentially to a MongoDB instance if configured.</li>
          <li>Checking the connection status to the Bland.ai API.</li>
        </ul>
        
        <h3>Core Methods</h3>
        <h4>Internal Methods</h4>
        <ul>
          <li><code>_load_pathway_definition()</code>: Loads the call pathway from <code>app/assets/call.json</code>.</li>
          <li><code>_load_location_tool_definition()</code>: Loads the location tool definition from <code>app/assets/location.json</code>.</li>
          <li><code>_load_quote_tool_definition()</code>: Loads the quote tool definition from <code>app/assets/quote.json</code>.</li>
          <li><code>_sync_pathway()</code>: Updates the specified Bland.ai pathway with the loaded definition.</li>
          <li><code>_sync_location_tool()</code>: Updates the specified Bland.ai location tool.</li>
          <li><code>_sync_quote_tool()</code>: Updates the specified Bland.ai quote tool.</li>
          <li><code>sync_bland()</code>: Performs all synchronization tasks for pathway and tools.</li>
          <li><code>_make_request()</code>: A helper to execute HTTP requests to the Bland.ai API, handling responses and errors.</li>
        </ul>
        
        <h4>Public Methods</h4>
        <ul>
          <li><code>initiate_callback(request: BlandCallbackRequest, contact_id: str, background_tasks: BackgroundTasks)</code>: Initiates a call.</li>
          <li><code>process_webhook_data(payload: BlandWebhookPayload)</code>: Processes incoming webhook data from Bland.ai after a call.</li>
          <li><code>check_connection()</code>: Verifies connectivity with the Bland.ai API.</li>
          <li><code>close()</code>: Closes the underlying <code>httpx.AsyncClient</code>.</li>
        </ul>
      </section>
    `;
  }

  getHubspotSection() {
    return `
      <section id="hubspot" class="content-section ${this.state.activeSection === 'hubspot' ? 'active' : ''}">
        <h2>HubSpot Service</h2>
        <p>The HubSpot Service manages all interactions with the HubSpot CRM API, handling creation, reading, updating, and deleting (archiving) HubSpot objects like Contacts, Companies, Deals, and Tickets.</p>
        
        <h3>Class: HubSpotManager</h3>
        <div class="code-block">
          <pre><code>class HubSpotManager:
    def __init__(self, access_token: str)</code></pre>
        </div>
        
        <h3>Key Responsibilities</h3>
        <ul>
          <li>CRUD operations for Contacts, Companies, Deals, and Tickets.</li>
          <li>Searching HubSpot objects using various criteria.</li>
          <li>Managing associations between different HubSpot objects (e.g., associating a Contact with a Company, a Deal with a Contact).</li>
          <li>Fetching HubSpot owners, pipelines, and pipeline stages, with caching mechanisms to improve performance.</li>
          <li>Converting date strings to HubSpot-compatible millisecond timestamps.</li>
          <li>Handling HubSpot API errors gracefully and logging them.</li>
        </ul>
        
        <h3>Core Methods</h3>
        
        <h4>Object-Specific Methods</h4>
        <ul>
          <li><strong>Contacts:</strong> <code>create_contact</code>, <code>get_contact</code>, <code>update_contact</code>, <code>delete_contact</code>, <code>create_or_update_contact</code></li>
          <li><strong>Companies:</strong> <code>create_company</code>, <code>get_company</code>, <code>update_company</code>, <code>delete_company</code>, <code>create_or_update_company</code></li>
          <li><strong>Deals:</strong> <code>create_deal</code>, <code>get_deal</code>, <code>update_deal</code>, <code>delete_deal</code></li>
          <li><strong>Tickets:</strong> <code>create_ticket</code>, <code>get_ticket</code>, <code>update_ticket</code>, <code>delete_ticket</code></li>
          <li><strong>Generic Search:</strong> <code>search_objects(object_type: str, search_request: HubSpotSearchRequest)</code></li>
        </ul>
        
        <h4>Association Methods</h4>
        <ul>
          <li><code>associate_objects(from_object_type: str, from_object_id: str, to_object_type: str, to_object_id: str, association_type: Union[str, int])</code></li>
          <li><code>batch_associate_objects(...)</code></li>
          <li>Specific association helpers like <code>associate_contact_to_company</code>, <code>associate_deal_to_contact</code>, etc.</li>
        </ul>
        
        <h4>Pipeline, Stage, and Owner Methods</h4>
        <ul>
          <li><code>get_pipelines(object_type: Literal["deal", "ticket"])</code></li>
          <li><code>get_pipeline_id(object_type: Literal["deal", "ticket"], pipeline_name: str)</code></li>
          <li><code>get_pipeline_stages(object_type: Literal["deal", "ticket"], pipeline_id: str)</code></li>
          <li><code>get_stage_id(object_type: Literal["deal", "ticket"], pipeline_name: str, stage_name: str)</code></li>
          <li><code>get_owners(email: Optional[str] = None, owner_id: Optional[str] = None)</code></li>
          <li><code>get_owner_id_by_email(email: str)</code></li>
        </ul>
        
        <h4>Helper Methods</h4>
        <ul>
          <li><code>_convert_date_to_timestamp_ms(date_str: Optional[str])</code></li>
          <li><code>_handle_api_error(e: Exception, context: str, object_id: Optional[str] = None)</code></li>
          <li><code>check_connection()</code></li>
        </ul>
      </section>
    `;
  }

  getN8nSection() {
    return `
      <section id="n8n" class="content-section ${this.state.activeSection === 'n8n' ? 'active' : ''}">
        <h2>n8n Integration Service</h2>
        <p>The n8n Integration Service facilitates sending data to an n8n (workflow automation tool) webhook, typically used for handoff automation after a lead has been classified and processed.</p>
        
        <h3>Key Functions</h3>
        
        <h4>send_to_n8n_webhook</h4>
        <div class="code-block">
          <pre><code>async def send_to_n8n_webhook(
    payload: Dict[str, Any], 
    webhook_url: Optional[str], 
    api_key: Optional[str]
)</code></pre>
        </div>
        <ul>
          <li>Sends the provided <code>payload</code> dictionary as JSON to the specified <code>webhook_url</code>.</li>
          <li>Uses the <code>N8N_WEBHOOK_URL</code> from settings by default.</li>
          <li>If an <code>api_key</code> (default from <code>N8N_API_KEY</code> in settings) is provided, it includes it in a custom header named <code>Stahla</code>.</li>
          <li>Logs the interaction and handles HTTP errors.</li>
          <li>Uses a shared <code>httpx.AsyncClient</code>.</li>
        </ul>
        
        <h4>trigger_n8n_handoff_automation</h4>
        <div class="code-block">
          <pre><code>async def trigger_n8n_handoff_automation(
    classification_result: ClassificationResult,
    input_data: ClassificationInput,
    contact_result: Optional[HubSpotApiResult],
    lead_result: Optional[HubSpotApiResult]
)</code></pre>
        </div>
        <ul>
          <li>Prepares a structured payload containing details about the lead, event, classification, call, routing, and HubSpot entities.</li>
          <li>Pulls data primarily from <code>input_data</code> and <code>classification_result</code>.</li>
          <li>Includes HubSpot contact and lead IDs and URLs if available.</li>
          <li>Determines the target team email list based on classification metadata.</li>
          <li>Skips handoff if the lead is classified as "Disqualify".</li>
          <li>Calls <code>send_to_n8n_webhook</code> to send the composed payload.</li>
        </ul>
        
        <h4>Client Management</h4>
        <ul>
          <li><code>close_n8n_client()</code>: Closes the shared <code>httpx.AsyncClient</code>.</li>
        </ul>
        
        <h3>Configuration</h3>
        <p>Relies on <code>N8N_WEBHOOK_URL</code> and <code>N8N_API_KEY</code> from <code>app.core.config.settings</code>.</p>
      </section>
    `;
  }

  getAuthSection() {
    return `
      <section id="auth" class="content-section ${this.state.activeSection === 'auth' ? 'active' : ''}">
        <h2>Authentication Service</h2>
        <p>The Authentication Service manages authentication and authorization, primarily focusing on API key validation and potentially user management if integrated with a user database.</p>
        
        <h3>Key Responsibilities</h3>
        <ul>
          <li>Validates API keys (e.g., passed in headers like <code>X-API-Key</code>).</li>
          <li>Checks if an API key is active and possesses the required permissions for a requested operation.</li>
          <li>Defines Pydantic models for <code>APIKey</code> (with fields like key, user_id, permissions, active status) and potentially <code>User</code>.</li>
          <li>Includes functions to create API keys, retrieve key details (possibly from <code>MongoService</code>), and verify keys against required permissions.</li>
          <li>Uses FastAPI's <code>Security</code> utilities for dependency injection to protect endpoints.</li>
          <li>May use libraries like <code>passlib</code> for password hashing if user credential management is involved.</li>
        </ul>
        
        <h3>Dependencies</h3>
        <p><code>MongoService</code> (for storing API keys/users), FastAPI, <code>passlib</code>.</p>
      </section>
    `;
  }

  getClassifySection() {
    return `
      <section id="classify" class="content-section ${this.state.activeSection === 'classify' ? 'active' : ''}">
        <h2>Classification Services</h2>
        <p>The Classification Services handle lead/interaction classification, determining the nature, urgency, and appropriate next steps based on input data.</p>
        
        <h3>Main Classification Orchestrator</h3>
        <h4>Class: ClassificationService</h4>
        <div class="code-block">
          <pre><code>class ClassificationService:
    def __init__(self, marvin_service: Optional[MarvinService] = None)</code></pre>
        </div>
        
        <h4>Key Responsibilities</h4>
        <ul>
          <li>Accepts <code>ClassificationInput</code> (data from calls, emails, forms).</li>
          <li>Applies predefined rules from <code>app/services/classify/rules.py</code>.</li>
          <li>If necessary, invokes an LLM (e.g., via <code>MarvinService</code>) for more complex classification.</li>
          <li>Produces a <code>ClassificationResult</code> detailing the classification type, metadata, urgency, and actions.</li>
        </ul>
        
        <h4>Core Methods</h4>
        <ul>
          <li><code>classify_input(input_data: ClassificationInput)</code>: Main classification method.</li>
          <li><code>_apply_rules(input_data: ClassificationInput)</code>: Internal method for rule application.</li>
          <li><code>_invoke_llm_classification(input_data: ClassificationInput)</code>: Internal method for LLM interaction.</li>
        </ul>
        
        <h3>Marvin AI Integration</h3>
        <h4>Class: MarvinService</h4>
        <div class="code-block">
          <pre><code>class MarvinService:
    def __init__(self, api_key: str, model_name: Optional[str])</code></pre>
        </div>
        
        <h4>Key Responsibilities</h4>
        <ul>
          <li>Initializes and configures the Marvin client (API keys, model selection).</li>
          <li>Provides wrapper methods for Marvin's functionalities.</li>
          <li>Manages API communication with the Marvin service, including error handling and retries.</li>
        </ul>
        
        <h4>Core Methods</h4>
        <ul>
          <li><code>classify_with_marvin(text_to_classify: str, categories: List[str], instructions: Optional[str])</code>: Classifies text.</li>
          <li><code>extract_data_with_marvin(text_to_extract_from: str, data_model: Type[BaseModel], instructions: Optional[str])</code>: Extracts structured data.</li>
        </ul>
        
        <h3>Rule Definitions</h3>
        <p>The <code>app/services/classify/rules.py</code> module contains the specific rule-based logic used by the <code>ClassificationService</code>.</p>
        
        <h4>Key Features</h4>
        <ul>
          <li>A collection of functions, each implementing a specific rule by evaluating conditions on <code>ClassificationInput</code> data.</li>
          <li>Rules can return partial or full <code>ClassificationResult</code> components.</li>
          <li>Includes a mechanism to apply these rules in a defined order or priority.</li>
        </ul>
      </section>
    `;
  }

  getDashboardSection() {
    return `
      <section id="dashboard" class="content-section ${this.state.activeSection === 'dashboard' ? 'active' : ''}">
        <h2>Dashboard Services</h2>
        <p>The Dashboard Services provide backend logic for the application's dashboard, including data aggregation, background task management, and monitoring.</p>
        
        <h3>Dashboard Logic</h3>
        <h4>Class: DashboardService</h4>
        <div class="code-block">
          <pre><code>class DashboardService:
    def __init__(
        self,
        mongo_service: MongoService,
        hubspot_manager: Optional[HubSpotManager] = null,
        redis_service: Optional[RedisService] = null,
        bland_manager: Optional[BlandAIManager] = null
    )</code></pre>
        </div>
        
        <h4>Key Responsibilities</h4>
        <ul>
          <li>Fetching data for dashboard widgets (e.g., call stats, lead conversion, error logs, HubSpot sync status).</li>
          <li>Interacting with <code>MongoService</code> (application data), <code>HubSpotManager</code> (CRM data), <code>RedisService</code> (cache), <code>BlandAIManager</code> (call system status).</li>
          <li>May use <code>app/services/dash/background.py</code> for pre-computed data or to trigger computations.</li>
        </ul>
        
        <h4>Core Methods</h4>
        <ul>
          <li><code>get_overview_metrics()</code>: High-level statistics.</li>
          <li><code>get_recent_activity_feed()</code>: List of recent events.</li>
          <li><code>get_call_volume_trends()</code>: Data for charts.</li>
          <li><code>get_hubspot_sync_status()</code>: HubSpot synchronization status.</li>
        </ul>
        
        <h3>Background Task Management</h3>
        <p>The <code>app/services/dash/background.py</code> module manages background tasks related to dashboard data aggregation, report generation, or other long-running processes.</p>
        
        <h4>Key Features</h4>
        <ul>
          <li>May define a <code>DashboardBackgroundProcessor</code> class or similar.</li>
          <li>Functions to enqueue tasks (e.g., using FastAPI's <code>BackgroundTasks</code> or a dedicated queue).</li>
          <li>Task execution logic such as <code>update_dashboard_summary_data()</code> or <code>trigger_long_running_report_generation(params)</code>.</li>
        </ul>
        
        <h3>Background Task Monitoring</h3>
        <p>The <code>app/services/dash/background_check.py</code> module implements health checks and status monitoring for background tasks or services.</p>
        
        <h4>Key Functions</h4>
        <ul>
          <li><code>check_background_task_status(task_id: str)</code>: Status of a specific task.</li>
          <li><code>get_background_services_health()</code>: Aggregated health of background processes.</li>
          <li><code>get_last_successful_run_time(task_name: str)</code>: Timestamp of last successful run for recurring tasks.</li>
        </ul>
      </section>
    `;
  }

  getLocationSection() {
    return `
      <section id="location" class="content-section ${this.state.activeSection === 'location' ? 'active' : ''}">
        <h2>Location Service</h2>
        <p>The Location Service centralizes location-based functionalities, serving as the primary interface for geocoding, distance calculation, and locality determination.</p>
        
        <h3>Class: LocationService</h3>
        <div class="code-block">
          <pre><code>class LocationService:
    def __init__(self, geocoding_provider: Optional[str] = None, cache_ttl: int = 3600)</code></pre>
        </div>
        
        <h3>Key Responsibilities</h3>
        <ul>
          <li>Provides a consistent API for geocoding addresses/descriptions.</li>
          <li>Calculates distances between geographic points.</li>
          <li>Determines if a location is "local" based on service hubs and drive times.</li>
          <li>Manages geocoding provider interactions (e.g., Nominatim) and result caching.</li>
        </ul>
        
        <h3>Core Methods</h3>
        <ul>
          <li><code>geocode(address_details) -> Optional[Coordinates]</code>: Converts an address to geographic coordinates.</li>
          <li><code>calculate_distance(point1: Coordinates, point2: Coordinates) -> float</code>: Calculates the distance between two points.</li>
          <li><code>estimate_drive_time(distance_km: float) -> float</code>: Estimates driving time based on distance.</li>
          <li><code>is_local(coordinates: Coordinates) -> bool</code>: Determines if coordinates are within a local service area.</li>
          <li><code>determine_locality(address_details) -> LocalityResult</code>: Analyzes an address for service area categorization.</li>
        </ul>
        
        <h3>Dependencies</h3>
        <p><code>geopy</code> library, caching mechanism (e.g., in-memory, Redis), location-related Pydantic models.</p>
      </section>
    `;
  }

  getMongoSection() {
    return `
      <section id="mongo" class="content-section ${this.state.activeSection === 'mongo' ? 'active' : ''}">
        <h2>MongoDB Service</h2>
        <p>The MongoDB Service provides a dedicated interface for all MongoDB interactions, abstracting direct driver calls and providing methods tailored to the application's data models and query needs.</p>
        
        <h3>Class: MongoService</h3>
        <div class="code-block">
          <pre><code>class MongoService:
    def __init__(self, connection_string: str, database_name: str)</code></pre>
        </div>
        
        <h3>Key Responsibilities</h3>
        <ul>
          <li>Managing MongoDB connections.</li>
          <li>Providing CRUD operations for various collections (e.g., <code>calls</code>, <code>logs</code>, <code>users</code>, <code>api_keys</code>).</li>
          <li>Implementing specific query methods (e.g., <code>find_call_by_id</code>, <code>save_classification_result</code>).</li>
          <li>Handling data transformation between Pydantic models and MongoDB documents.</li>
        </ul>
        
        <h3>Core Methods</h3>
        <ul>
          <li><code>get_collection(collection_name: str)</code>: Retrieves a MongoDB collection.</li>
          <li><code>insert_document(collection_name: str, document: dict)</code>: Inserts a document into a collection.</li>
          <li><code>find_document_by_id(collection_name: str, document_id: str)</code>: Retrieves a document by ID.</li>
          <li>Other CRUD operations and specialized query methods.</li>
        </ul>
        
        <h3>Dependencies</h3>
        <p><code>motor</code> (async MongoDB driver), Pydantic models. Requires MongoDB connection settings.</p>
      </section>
    `;
  }

  getQuoteSection() {
    return `
      <section id="quote" class="content-section ${this.state.activeSection === 'quote' ? 'active' : ''}">
        <h2>Quoting Services</h2>
        <p>The Quoting Services handle product/service quoting, including generation, management, and synchronization.</p>
        
        <h3>Quote Management</h3>
        <h4>Class: QuoteService</h4>
        <div class="code-block">
          <pre><code>class QuoteService:
    def __init__(
        self,
        mongo_service: MongoService,
        hubspot_manager: Optional[HubSpotManager] = null
    )</code></pre>
        </div>
        
        <h4>Key Responsibilities</h4>
        <ul>
          <li>Fetching product/service details and pricing.</li>
          <li>Applying business logic for calculations (discounts, taxes).</li>
          <li>Generating quote documents/data (<code>QuoteModel</code>).</li>
          <li>Storing and retrieving quotes.</li>
          <li>Potentially integrating with <code>HubSpotManager</code> to link quotes with CRM records.</li>
        </ul>
        
        <h4>Core Methods</h4>
        <ul>
          <li><code>create_quote(quote_request: QuoteRequestModel) -> QuoteModel</code>: Creates a new quote.</li>
          <li><code>get_quote_by_id(quote_id: str) -> Optional[QuoteModel]</code>: Retrieves a quote.</li>
          <li><code>update_quote_status(quote_id: str, status: str)</code>: Updates quote status.</li>
        </ul>
        
        <h3>Quote Authentication/Authorization</h3>
        <p>The <code>app/services/quote/auth.py</code> module handles authentication or authorization specific to the quoting functionality.</p>
        
        <h4>Key Features</h4>
        <ul>
          <li>Could define a <code>QuoteServiceAuthenticator</code> or specific FastAPI dependencies.</li>
          <li>Functions like <code>verify_quote_access_token(token: str)</code>.</li>
          <li>If using the main API key system, it might contain helpers to check for quote-specific permissions.</li>
        </ul>
        
        <h3>Quote Synchronization</h3>
        <p>The <code>app/services/quote/sync.py</code> module manages synchronization tasks related to quotes.</p>
        
        <h4>Key Features</h4>
        <ul>
          <li>May define a <code>QuoteSyncManager</code> or similar.</li>
          <li>Functions like <code>sync_quotes_to_hubspot()</code> and <code>sync_product_catalog_from_source()</code>.</li>
          <li>Can be triggered by periodic background tasks or event-driven processes.</li>
        </ul>
      </section>
    `;
  }

  getRedisSection() {
    return `
      <section id="redis" class="content-section ${this.state.activeSection === 'redis' ? 'active' : ''}">
        <h2>Redis Service</h2>
        <p>The Redis Service provides a centralized interface for interacting with a Redis cache, abstracting direct client calls.</p>
        
        <h3>Class: RedisService</h3>
        <div class="code-block">
          <pre><code>class RedisService:
    def __init__(self, redis_url: str)</code></pre>
        </div>
        
        <h3>Key Responsibilities</h3>
        <ul>
          <li>Managing Redis connections.</li>
          <li>Providing methods for basic Redis operations (<code>get</code>, <code>set</code>, <code>delete</code>, <code>expire</code>).</li>
          <li>Handling serialization/deserialization of cached objects.</li>
        </ul>
        
        <h3>Core Methods</h3>
        <ul>
          <li><code>async get_value(key: str) -> Optional[Any]</code>: Retrieves a value from Redis.</li>
          <li><code>async set_value(key: str, value: Any, expire_seconds: Optional[int] = None)</code>: Stores a value in Redis.</li>
          <li><code>async delete_key(key: str)</code>: Deletes a key from Redis.</li>
          <li><code>async check_connection()</code>: Verifies connectivity with Redis.</li>
        </ul>
        
        <h3>Dependencies</h3>
        <p><code>aioredis</code> (async Redis client). Requires Redis connection URL.</p>
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

      // Handle service item clicks in the grid
      const serviceItem = event.target.closest('.service-item');
      if (serviceItem) {
        const service = serviceItem.dataset.service;
        if (service) {
          this._navigateToSection(service);
        }
      }

      // Toggle mobile nav
      if (event.target.closest('#toggle-nav')) {
        this.state.expandedSubmenu = !this.state.expandedSubmenu;
        this.render();
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
    return /* css */ `
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-text);
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
          width: 0;
          display: none;
          visibility: hidden;
        }

        *::-webkit-scrollbar-track {
          display: none;
          visibility: hidden;
          background: var(--scroll-bar-background);
        }

        *::-webkit-scrollbar-thumb {
          width: 0;
          display: none;
          visibility: hidden;
          background: var(--scroll-bar-linear);
          border-radius: 50px;
        }
        
        .services-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .services-docs-header {
          padding: 20px 0 0;
        }
        
        .services-docs-header h1 {
          font-size: 2rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .services-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .services-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .services-docs-sidebar {
          width: 260px;
          position: sticky;
          top: 20px;
          height: calc(100vh - 40px);
          overflow-y: auto;
          position: sticky;
          overflow: auto;
          -ms-overflow-style: none; /* IE 11 */
          scrollbar-width: none; /* Firefox 64 */
        }

        .services-docs-sidebar::-webkit-scrollbar {
          display: none;
        }
        
        .sidebar-content {
          background-color: var(--background);
        }
        
        .nav-sections {
          padding: 15px 0;
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
          font-weight: 500;
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
        
        .services-docs-main {
          flex: 1;
          min-width: 0;
        }
        
        .services-content-container {
          padding: 0;
        }
        
        .content-section {
          display: none;
          padding: 20px;
          background-color: var(--background);
        }
        
        .content-section.active {
          display: block;
        }
        
        .content-section h2 {
          font-size: 1.75rem;
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
          border-radius: 4px;
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .copy-btn:hover {
          background-color: var(--hover-background);
        }
        
        .service-overview {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .service-card {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
        }
        
        .service-card h4 {
          margin: 0 0 10px;
          color: var(--title-color);
        }
        
        .service-card p {
          margin: 0;
          font-size: 0.9rem;
        }
        
        .services-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .service-item {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .service-item:hover {
          border-color: var(--accent-color);
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow-alt);
        }
        
        .service-item h3 {
          margin: 0 0 10px;
          font-size: 1.2rem;
          color: var(--title-color);
        }
        
        .service-item p {
          margin: 0;
          font-size: 0.9rem;
        }
        
        @media (max-width: 900px) {
          .services-docs-content {
            flex-direction: column;
          }
          
          .services-docs-sidebar {
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