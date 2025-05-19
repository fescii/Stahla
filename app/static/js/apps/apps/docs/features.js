export default class FeaturesDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0;
    
    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedFeatures: new Set(),
      expandedSchemas: new Set(),
      expandedSubmenu: false,
      expandedCategories: new Set(['features'])
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
    console.log(`Rendering Features docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return `
      ${this.getStyles()}
      <div class="features-docs">
        <div class="features-docs-content">
          <nav class="features-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="features-docs-main" class="features-docs-main">
            <div id="content-container" class="features-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="features-docs-header">
        <h1>Stahla AI SDR Application Features</h1>
        <p>Key features aligned with AI SDR Product Requirements Document v1</p>
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
          <div class="nav-section ${this.isFeaturesActive() ? 'active' : ''} ${this.state.expandedCategories.has('features') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-section="features" data-category="features">
              <span class="link-text">Key Features</span>
              <span class="expand-icon">${this.state.expandedCategories.has('features') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'intake' ? 'active' : ''}" data-section="intake">AI Intake Agent</a>
              <a class="nav-link sub ${this.state.activeSection === 'hubspot' ? 'active' : ''}" data-section="hubspot">HubSpot Integration</a>
              <a class="nav-link sub ${this.state.activeSection === 'classification' ? 'active' : ''}" data-section="classification">Classification & Routing</a>
              <a class="nav-link sub ${this.state.activeSection === 'handoff' ? 'active' : ''}" data-section="handoff">Human-in-the-Loop Handoff</a>
              <a class="nav-link sub ${this.state.activeSection === 'followup' ? 'active' : ''}" data-section="followup">Intelligent Follow-Up</a>
              <a class="nav-link sub ${this.state.activeSection === 'config' ? 'active' : ''}" data-section="config">Configuration & Monitoring</a>
              <a class="nav-link sub ${this.state.activeSection === 'pricing' ? 'active' : ''}" data-section="pricing">Real-time Pricing Agent</a>
              <a class="nav-link sub ${this.state.activeSection === 'dashboard' ? 'active' : ''}" data-section="dashboard">Operational Dashboard</a>
              <a class="nav-link sub ${this.state.activeSection === 'workflow' ? 'active' : ''}" data-section="workflow">Workflow Integration</a>
              <a class="nav-link sub ${this.state.activeSection === 'nongoals' ? 'active' : ''}" data-section="nongoals">Non-Goals (v1)</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  isFeaturesActive() {
    const featuresSections = ['features', 'intake', 'hubspot', 'classification', 'handoff', 'followup', 'config', 'pricing', 'dashboard', 'workflow', 'nongoals'];
    return featuresSections.includes(this.state.activeSection);
  }

  getContentForSection(section) {
    switch(section) {
      case 'introduction':
        return this.getIntroductionSection();
      case 'features':
        return this.getFeaturesSection();
      case 'intake':
        return this.getIntakeSection();
      case 'hubspot':
        return this.getHubspotSection();
      case 'classification':
        return this.getClassificationSection();
      case 'handoff':
        return this.getHandoffSection();
      case 'followup':
        return this.getFollowupSection();
      case 'config':
        return this.getConfigSection();
      case 'pricing':
        return this.getPricingSection();
      case 'dashboard':
        return this.getDashboardSection();
      case 'workflow':
        return this.getWorkflowSection();
      case 'nongoals':
        return this.getNongoalsSection();
      default:
        return this.getIntroductionSection();
    }
  }

  getIntroductionSection() {
    return /* html */ `
      <section id="introduction" class="content-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
        ${this.getHeader()}
        <p>This document outlines the key features of the Stahla AI SDR application, based on the v1 Product Requirements Document. These features represent the core functionality of the application designed to automate and enhance the sales development representative (SDR) process.</p>
        
        <h3>Feature Categories</h3>
        <p>The application is built around several key feature categories, each addressing specific aspects of the SDR workflow from intake to handoff.</p>
        
        <div class="feature-overview">
          <div class="feature-card">
            <h4>AI Intake Agent</h4>
            <p>Multi-channel lead intake via voice calls, web forms, and email, with intelligent follow-up capabilities.</p>
          </div>
          <div class="feature-card">
            <h4>HubSpot Data Enrichment</h4>
            <p>Automatic creation and updating of HubSpot records with comprehensive lead information.</p>
          </div>
          <div class="feature-card">
            <h4>Classification & Routing</h4>
            <p>Intelligent categorization of leads and assignment to appropriate pipelines and owners.</p>
          </div>
          <div class="feature-card">
            <h4>Real-time Pricing Agent</h4>
            <p>Provides immediate pricing quotes based on product specifications and delivery location.</p>
          </div>
        </div>
      </section>
    `;
  }

  getFeaturesSection() {
    return /* html */ `
      <section id="features" class="content-section ${this.state.activeSection === 'features' ? 'active' : ''}">
        <h2>Key Features (Aligned with AI SDR PRD v1)</h2>
        <p>The Stahla AI SDR application includes a comprehensive set of features designed to automate and enhance the sales development representative workflow, from initial lead intake to sales representative handoff.</p>
        
        <p>Navigate to individual feature documentation using the sidebar or select from the options below:</p>
        
        <div class="features-grid">
          <div class="feature-item" data-feature="intake">
            <h3>AI Intake Agent</h3>
            <p>Multi-channel lead intake via voice calls, web forms, and email.</p>
          </div>
          <div class="feature-item" data-feature="hubspot">
            <h3>HubSpot Integration</h3>
            <p>Data enrichment and automatic record creation in HubSpot.</p>
          </div>
          <div class="feature-item" data-feature="classification">
            <h3>Classification & Routing</h3>
            <p>Intelligent lead categorization and assignment.</p>
          </div>
          <div class="feature-item" data-feature="handoff">
            <h3>Human-in-the-Loop</h3>
            <p>Seamless transition from AI to human representatives.</p>
          </div>
          <div class="feature-item" data-feature="followup">
            <h3>Intelligent Follow-Up</h3>
            <p>Automated follow-ups for incomplete information.</p>
          </div>
          <div class="feature-item" data-feature="config">
            <h3>Configuration & Monitoring</h3>
            <p>System settings and health monitoring capabilities.</p>
          </div>
          <div class="feature-item" data-feature="pricing">
            <h3>Real-time Pricing</h3>
            <p>Immediate quote generation for products and services.</p>
          </div>
          <div class="feature-item" data-feature="dashboard">
            <h3>Operational Dashboard</h3>
            <p>System status monitoring and management tools.</p>
          </div>
          <div class="feature-item" data-feature="workflow">
            <h3>Workflow Integration</h3>
            <p>Integration with n8n for advanced automation.</p>
          </div>
          <div class="feature-item" data-feature="nongoals">
            <h3>Non-Goals (v1)</h3>
            <p>Features explicitly excluded from the v1 release.</p>
          </div>
        </div>
      </section>
    `;
  }

  // This is the start of the individual feature sections
  
  getIntakeSection() {
    return /* html */ `
      <section id="intake" class="content-section ${this.state.activeSection === 'intake' ? 'active' : ''}">
        <h2>AI Intake Agent (Multi-Channel)</h2>
        <p>The AI Intake Agent serves as the primary interface for gathering lead information through multiple channels, providing a consistent experience while capturing comprehensive data.</p>
        
        <h3>Voice Channel (Bland.ai)</h3>
        <ul>
          <li><strong>Inbound Call Handling:</strong> Answers incoming calls directly, gathering information through natural, conversational dialogue.</li>
          <li><strong>Automated Callbacks:</strong> Initiates callbacks within approximately one minute for web form submissions with incomplete information.</li>
          <li><strong>Dynamic Questioning:</strong> Uses context-aware questioning to efficiently gather required information while maintaining a natural conversational flow.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example Bland.ai callback initialization
initiate_callback(
    request: BlandCallbackRequest,
    contact_id: str,
    background_tasks: BackgroundTasks
)</code></pre>
        </div>
        
        <h3>Web Form Channel</h3>
        <ul>
          <li><strong>Webhook Integration:</strong> Processes submissions via the <code>/api/v1/webhooks/form</code> endpoint.</li>
          <li><strong>Completeness Check:</strong> Evaluates incoming form data for completeness against required fields.</li>
          <li><strong>Follow-up Trigger:</strong> Automatically triggers voice follow-up via Bland.ai when form data is incomplete.</li>
        </ul>
        
        <h3>Email Channel</h3>
        <ul>
          <li><strong>Email Processing:</strong> Receives and processes emails through the <code>/api/v1/webhooks/email</code> webhook endpoint.</li>
          <li><strong>AI-Powered Extraction:</strong> Uses LLM technology (e.g., Marvin) to parse and extract structured data from unstructured email content.</li>
          <li><strong>Format Handling:</strong> Processes both plain text and HTML email formats for complete data extraction.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example email processing method
process_incoming_email(
    payload: EmailWebhookPayload
) -> ProcessingResult</code></pre>
        </div>
        
        <h3>Integration Points</h3>
        <p>The AI Intake Agent connects with multiple system components:</p>
        <ul>
          <li>Bland.ai service for voice interactions</li>
          <li>HubSpot service for recording lead information</li>
          <li>Classification engine for lead categorization</li>
          <li>Email service for follow-up communications</li>
        </ul>
      </section>
    `;
  }

  getHubspotSection() {
    return /* html */ `
      <section id="hubspot" class="content-section ${this.state.activeSection === 'hubspot' ? 'active' : ''}">
        <h2>HubSpot Data Enrichment & Write-Back</h2>
        <p>The HubSpot integration feature ensures all lead information is properly recorded in the CRM system with comprehensive data enrichment and automated record creation.</p>
        
        <h3>Contact & Deal Management</h3>
        <ul>
          <li><strong>Automatic Record Creation:</strong> Creates or updates HubSpot Contacts and Deals based on information gathered through the intake channels.</li>
          <li><strong>High Completeness Standard:</strong> Maintains ≥95% property completeness across key fields.</li>
          <li><strong>Target Fields:</strong> Ensures comprehensive data for lead type, product, duration, location, stalls, and budget fields.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example HubSpot contact creation
create_or_update_contact(
    contact_data: Dict[str, Any],
    create_if_not_exists: bool = True
) -> HubSpotContactResult</code></pre>
        </div>
        
        <h3>Call Details Integration</h3>
        <ul>
          <li><strong>Call Summary:</strong> Writes detailed call summary text to HubSpot for sales representative review.</li>
          <li><strong>Recording Access:</strong> Stores recording URL from Bland.ai in HubSpot custom object or activity.</li>
          <li><strong>Sales Rep Accessibility:</strong> Ensures easy access to call details directly within the HubSpot interface.</li>
        </ul>
        
        <h3>Custom Property Mapping</h3>
        <ul>
          <li><strong>Flexible Mapping:</strong> Maps extracted and classified data to custom HubSpot properties.</li>
          <li><strong>Configuration-Driven:</strong> Uses configuration files to define property mappings, allowing for easy updates.</li>
          <li><strong>Validation:</strong> Validates data types and formats before writing to HubSpot.</li>
        </ul>
        
        <h3>Implementation Details</h3>
        <p>The HubSpot integration uses the HubSpotManager service class to handle all CRM interactions:</p>
        <ul>
          <li><strong>Authentication:</strong> Uses OAuth tokens for secure API access.</li>
          <li><strong>Error Handling:</strong> Includes robust error handling with retry mechanisms for intermittent API issues.</li>
          <li><strong>Logging:</strong> Maintains detailed logs of all HubSpot operations for troubleshooting.</li>
          <li><strong>Rate Limiting:</strong> Implements request throttling to respect HubSpot API rate limits.</li>
        </ul>
      </section>
    `;
  }

  getClassificationSection() {
    return /* html */ `
      <section id="classification" class="content-section ${this.state.activeSection === 'classification' ? 'active' : ''}">
        <h2>Classification & Routing Engine</h2>
        <p>The Classification & Routing Engine categorizes incoming leads and directs them to the appropriate sales pipelines and representatives based on lead attributes.</p>
        
        <h3>Lead Classification</h3>
        <ul>
          <li><strong>Classification Categories:</strong> Determines lead category from four options:
            <ul>
              <li><code>Services</code>: For service-related inquiries</li>
              <li><code>Logistics</code>: For logistics and operations inquiries</li>
              <li><code>Leads</code>: For general sales opportunities</li>
              <li><code>Disqualify</code>: For leads that don't meet business criteria</li>
            </ul>
          </li>
          <li><strong>Classification Factors:</strong> Uses product type, size, geography, budget, and other attributes for categorization.</li>
          <li><strong>Engine Flexibility:</strong> Configurable to use either rule-based logic or AI (e.g., Marvin) for classification decisions.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example classification method
classify_lead(
    lead_data: Dict[str, Any],
    use_ai: bool = True
) -> ClassificationResult</code></pre>
        </div>
        
        <h3>Pipeline Assignment</h3>
        <ul>
          <li><strong>Automatic Deal Creation:</strong> Creates or updates HubSpot Deals in the appropriate pipeline.</li>
          <li><strong>Pipeline Mapping:</strong> Maps classification categories directly to HubSpot pipelines:
            <ul>
              <li>Services classification → Services pipeline</li>
              <li>Logistics classification → Logistics pipeline</li>
              <li>Leads classification → Leads pipeline</li>
            </ul>
          </li>
          <li><strong>Stage Setting:</strong> Places the deal in the correct initial stage based on classification.</li>
        </ul>
        
        <h3>Owner Assignment</h3>
        <ul>
          <li><strong>Round-Robin Mechanism:</strong> Assigns deal ownership using a round-robin approach within the appropriate team.</li>
          <li><strong>Team-Based Assignment:</strong> Routes leads to the designated business unit or team based on classification.</li>
          <li><strong>Assignment Tracking:</strong> Maintains assignment history for balanced distribution.</li>
        </ul>
        
        <h3>Implementation Location</h3>
        <p>The classification engine is located in the <code>app/services/classify/</code> directory, with the following key components:</p>
        <ul>
          <li><code>classify_service.py</code>: Main service class for classification operations</li>
          <li><code>rules.py</code>: Rule-based classification logic</li>
          <li><code>ai_classifier.py</code>: AI-based classification using LLM</li>
          <li><code>models.py</code>: Data models for classification operations</li>
        </ul>
      </section>
    `;
  }

  getHandoffSection() {
    return /* html */ `
      <section id="handoff" class="content-section ${this.state.activeSection === 'handoff' ? 'active' : ''}">
        <h2>Human-in-the-Loop Handoff</h2>
        <p>The Human-in-the-Loop Handoff feature ensures smooth transition from the AI intake process to human sales representatives, providing all necessary context and lead information.</p>
        
        <h3>Email Notifications</h3>
        <ul>
          <li><strong>Automatic Trigger:</strong> Sends notifications automatically upon successful lead classification and HubSpot record creation.</li>
          <li><strong>Recipient Targeting:</strong> Delivers notifications to the assigned sales representative or team based on the classification result.</li>
          <li><strong>Customized Content:</strong> Tailors notification content based on lead category and specific attributes.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example notification method
send_handoff_notification(
    classification_result: ClassificationResult,
    contact_result: HubSpotContactResult,
    lead_result: HubSpotApiResult
)</code></pre>
        </div>
        
        <h3>Notification Content</h3>
        <ul>
          <li><strong>TL;DR Summary:</strong> Provides a concise overview of the lead, highlighting key points and business potential.</li>
          <li><strong>Key Data Points:</strong> Includes extracted data fields such as contact information, product interest, timeline, budget, and other relevant details.</li>
          <li><strong>Next Steps Checklist:</strong> Offers suggested actions for the sales representative to take, based on lead attributes and classification.</li>
          <li><strong>Direct Links:</strong> Includes links to:
            <ul>
              <li>HubSpot Contact record</li>
              <li>HubSpot Deal record</li>
              <li>Call recording (if applicable)</li>
              <li>Call summary text</li>
            </ul>
          </li>
        </ul>
        
        <h3>Implementation Details</h3>
        <p>The handoff notification system leverages the EmailManager service for sending notifications with the following features:</p>
        <ul>
          <li><strong>HTML Templating:</strong> Uses HTML email templates with dynamic content insertion.</li>
          <li><strong>Delivery Verification:</strong> Includes delivery tracking to ensure notifications reach recipients.</li>
          <li><strong>Fallback Mechanisms:</strong> Implements fallback routing if primary recipient is unavailable.</li>
          <li><strong>Customization Options:</strong> Supports team-specific notification templates and content.</li>
        </ul>
      </section>
    `;
  }

  getFollowupSection() {
    return /* html */ `
      <section id="followup" class="content-section ${this.state.activeSection === 'followup' ? 'active' : ''}">
        <h2>Intelligent Follow-Up</h2>
        <p>The Intelligent Follow-Up feature ensures that incomplete lead information is addressed through automated, channel-specific follow-up mechanisms.</p>
        
        <h3>Web Form Follow-Up</h3>
        <ul>
          <li><strong>Completeness Assessment:</strong> Evaluates web form submissions against required field criteria.</li>
          <li><strong>Voice Call Trigger:</strong> Automatically initiates a Bland.ai voice call when required information is missing.</li>
          <li><strong>Context-Aware Conversation:</strong> Provides the AI agent with existing information to avoid repetitive questions.</li>
          <li><strong>Timing Optimization:</strong> Initiates callbacks within ~1 minute to maximize engagement while the lead is still actively interested.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example follow-up trigger for incomplete form
trigger_voice_followup(
    form_data: Dict[str, Any],
    missing_fields: List[str],
    contact_information: ContactInfo
)</code></pre>
        </div>
        
        <h3>Email Follow-Up</h3>
        <ul>
          <li><strong>Missing Field Detection:</strong> Identifies specific fields missing from email-based inquiries.</li>
          <li><strong>Automated Email Reply:</strong> Sends a response requesting the specific missing information.</li>
          <li><strong>Personalization:</strong> Customizes the reply based on available lead information and missing fields.</li>
          <li><strong>Reply Tracking:</strong> Monitors for responses to follow-up emails for continued processing.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example email follow-up method
send_auto_reply(
    original_payload: EmailWebhookPayload,
    missing_fields: List[str],
    extracted_data: Dict[str, Any]
)</code></pre>
        </div>
        
        <h3>Integration Points</h3>
        <p>The follow-up system connects with multiple components:</p>
        <ul>
          <li><strong>Bland.ai Service:</strong> For voice-based follow-ups</li>
          <li><strong>Email Service:</strong> For email follow-up communications</li>
          <li><strong>Data Validation:</strong> For determining missing or incomplete information</li>
          <li><strong>Tracking System:</strong> For monitoring follow-up outcomes</li>
        </ul>
      </section>
    `;
  }

  getConfigSection() {
    return /* html */ `
      <section id="config" class="content-section ${this.state.activeSection === 'config' ? 'active' : ''}">
        <h2>Configuration & Monitoring</h2>
        <p>The Configuration & Monitoring features provide robust systems for application settings management and operational health monitoring.</p>
        
        <h3>Environment-Based Settings</h3>
        <ul>
          <li><strong>Environment Files:</strong> Uses <code>.env</code> files for environment-specific configuration.</li>
          <li><strong>Pydantic Settings:</strong> Leverages Pydantic's settings management (<code>app/core/config.py</code>) for type-safe configuration.</li>
          <li><strong>Validation:</strong> Validates configuration values at application startup to prevent runtime errors.</li>
          <li><strong>Hierarchical Override:</strong> Supports multi-level configuration with appropriate override precedence.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example configuration schema
class AppSettings(BaseSettings):
    app_name: str = "Stahla AI SDR"
    debug: bool = False
    environment: str
    
    # API keys
    bland_api_key: SecretStr
    hubspot_api_key: SecretStr
    
    # Service URLs
    bland_base_url: HttpUrl
    hubspot_base_url: HttpUrl
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"</code></pre>
        </div>
        
        <h3>Health Checks</h3>
        <ul>
          <li><strong>Health Endpoint:</strong> Provides <code>/health</code> endpoint for comprehensive system status checks.</li>
          <li><strong>Ping Endpoint:</strong> Offers <code>/ping</code> endpoint for basic connectivity verification.</li>
          <li><strong>Component Status:</strong> Includes status checks for all critical external services (Bland.ai, HubSpot, Redis, MongoDB).</li>
          <li><strong>Self-Diagnostics:</strong> Performs internal diagnostics on critical application components.</li>
        </ul>
        
        <h3>Logging Integration</h3>
        <ul>
          <li><strong>Logfire Integration:</strong> Connects with Logfire for centralized log collection and observability.</li>
          <li><strong>Structured Logging:</strong> Uses structured logging format for machine-parseable logs.</li>
          <li><strong>Log Levels:</strong> Implements appropriate log levels for different environments (development vs. production).</li>
          <li><strong>Context Enrichment:</strong> Enhances logs with request ID, timestamp, and component information.</li>
        </ul>
        
        <h3>Implementation Notes</h3>
        <p>The configuration system is designed to be:</p>
        <ul>
          <li><strong>Secure:</strong> Handles sensitive values like API keys securely.</li>
          <li><strong>Flexible:</strong> Adapts to different deployment environments.</li>
          <li><strong>Maintainable:</strong> Centralizes configuration management to avoid scattered settings.</li>
          <li><strong>Transparent:</strong> Provides clear visibility into current configuration and system status.</li>
        </ul>
      </section>
    `;
  }

  getPricingSection() {
    return /* html */ `
      <section id="pricing" class="content-section ${this.state.activeSection === 'pricing' ? 'active' : ''}">
        <h2>Real-time Pricing Agent (Integrated)</h2>
        <p>The Real-time Pricing Agent provides immediate, accurate price quotes for products and services, integrating location-based delivery pricing and product configuration options.</p>
        
        <h3>Quote Generation Webhook</h3>
        <ul>
          <li><strong>Endpoint:</strong> <code>/api/v1/webhook/pricing/quote</code></li>
          <li><strong>Functionality:</strong> Generates real-time price quotes based on product specifications and delivery requirements.</li>
          <li><strong>Input Parameters:</strong> Accepts trailer type, rental duration, usage details, optional extras, and delivery location.</li>
          <li><strong>Data Source:</strong> Uses pricing data cached from Google Sheets for rapid response.</li>
          <li><strong>Security:</strong> Protected by API key authentication.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example quote generation endpoint
@router.post("/webhook/pricing/quote", response_model=QuoteResponse)
async def generate_quote(
    request: QuoteRequest,
    api_key: str = Depends(get_api_key),
    quote_service: QuoteService = Depends(get_quote_service)
) -> QuoteResponse:
    return await quote_service.generate_quote(request)</code></pre>
        </div>
        
        <h3>Location Lookup Webhook</h3>
        <ul>
          <li><strong>Endpoint:</strong> <code>/api/v1/webhook/pricing/location_lookup</code></li>
          <li><strong>Purpose:</strong> Pre-calculates and caches distance between delivery location and nearest branch.</li>
          <li><strong>Optimization:</strong> Designed to be called early in the process to minimize quote generation latency.</li>
          <li><strong>Implementation:</strong> Uses Google Maps API asynchronously for distance calculation.</li>
          <li><strong>Security:</strong> Protected by API key authentication.</li>
        </ul>
        
        <h3>Dynamic Configuration</h3>
        <ul>
          <li><strong>Google Sheets Integration:</strong> Syncs pricing data dynamically from configured Google Sheets.</li>
          <li><strong>Cached Components:</strong>
            <ul>
              <li>Pricing rules and base rates</li>
              <li>Delivery configuration and distance tiers</li>
              <li>Seasonal multipliers and promotional adjustments</li>
              <li>Branch locations and service areas</li>
            </ul>
          </li>
          <li><strong>Redis Caching:</strong> Stores all pricing data in Redis for high-performance access.</li>
          <li><strong>Background Synchronization:</strong> Periodically updates cached data to reflect Google Sheets changes.</li>
        </ul>
        
        <h3>Key Implementation Components</h3>
        <p>The pricing agent consists of several interconnected components:</p>
        <ul>
          <li><strong>Quote Service:</strong> Main service class for quote generation.</li>
          <li><strong>Location Service:</strong> Handles geocoding and distance calculations.</li>
          <li><strong>Pricing Engine:</strong> Applies business rules and calculations to determine final pricing.</li>
          <li><strong>Sync Manager:</strong> Manages synchronization with Google Sheets.</li>
          <li><strong>Cache Manager:</strong> Handles Redis caching operations for pricing data.</li>
        </ul>
      </section>
    `;
  }

  getDashboardSection() {
    return /* html */ `
      <section id="dashboard" class="content-section ${this.state.activeSection === 'dashboard' ? 'active' : ''}">
        <h2>Operational Dashboard API (Backend)</h2>
        <p>The Operational Dashboard API provides monitoring and management capabilities for the application's internal operations, offering insights into system performance and configuration.</p>
        
        <h3>Monitoring Endpoints</h3>
        <ul>
          <li><strong>Overview:</strong> <code>/api/v1/dashboard/overview</code> - Provides a summary of system status and key metrics.</li>
          <li><strong>Quote Metrics:</strong> Endpoints for monitoring quote requests, success rates, and processing times.</li>
          <li><strong>Location Lookups:</strong> Endpoints for tracking location lookup performance and cache efficiency.</li>
          <li><strong>Cache Performance:</strong> Metrics on cache size, key counts, and hit/miss rates.</li>
          <li><strong>External Services:</strong> Status information for dependent services including sync timestamps and API usage counts.</li>
          <li><strong>Error Summaries:</strong> Aggregated summaries of recent errors and their frequencies.</li>
          <li><strong>Request Logs:</strong> Recent request logs for diagnostic purposes.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example dashboard overview endpoint
@router.get("/dashboard/overview", response_model=DashboardOverview)
async def get_dashboard_overview(
    dashboard_service: DashboardService = Depends(get_dashboard_service),
    current_user: User = Depends(get_current_user)
) -> DashboardOverview:
    return await dashboard_service.get_overview()</code></pre>
        </div>
        
        <h3>Management Endpoints</h3>
        <ul>
          <li><strong>Sync Trigger:</strong> <code>/api/v1/dashboard/sync/trigger</code> - Manually initiates Google Sheet synchronization.</li>
          <li><strong>Cache Management:</strong> Endpoints for viewing and managing cache entries:
            <ul>
              <li><code>/api/v1/dashboard/cache/list</code> - Lists cache keys by pattern</li>
              <li><code>/api/v1/dashboard/cache/view</code> - Views specific cache entry contents</li>
              <li><code>/api/v1/dashboard/cache/clear</code> - Clears specific cache entries or patterns</li>
            </ul>
          </li>
        </ul>
        
        <h3>Data Sources</h3>
        <p>The dashboard API collects data from multiple sources:</p>
        <ul>
          <li><strong>Redis Counters:</strong> Performance metrics and counters stored in Redis.</li>
          <li><strong>Background Tasks:</strong> Information populated asynchronously by background processes.</li>
          <li><strong>Service Checks:</strong> Direct checks of external service connectivity and status.</li>
          <li><strong>Log Analysis:</strong> Processing of application logs for error and usage patterns.</li>
        </ul>
        
        <h3>Authentication</h3>
        <ul>
          <li><strong>Placeholder Authentication:</strong> The v1 implementation includes a basic authentication system for dashboard access.</li>
          <li><strong>Role-Based Access:</strong> Different dashboard functions are available based on user role.</li>
          <li><strong>API Key Access:</strong> Alternative access method using API keys for programmatic access.</li>
        </ul>
      </section>
    `;
  }

  getWorkflowSection() {
    return `
      <section id="workflow" class="content-section ${this.state.activeSection === 'workflow' ? 'active' : ''}">
        <h2>Workflow Integration</h2>
        <p>The Workflow Integration feature enables external orchestration and automation of the application's capabilities through n8n workflow integration.</p>
        
        <h3>n8n Connectivity</h3>
        <ul>
          <li><strong>Integration Purpose:</strong> Leverages n8n for orchestrating specific automation tasks and workflow sequences.</li>
          <li><strong>Workflow Types:</strong> Supports various workflow types including lead processing, follow-up sequences, and data synchronization.</li>
          <li><strong>Trigger Mechanisms:</strong> Offers both webhook-based triggers and scheduled execution of workflows.</li>
        </ul>
        
        <div class="code-block">
          <pre><code>// Example n8n webhook handler
@router.post("/webhook/n8n/{workflow_id}")
async def handle_n8n_webhook(
    workflow_id: str,
    payload: Dict[str, Any],
    n8n_service: N8nService = Depends(get_n8n_service)
):
    return await n8n_service.process_webhook(workflow_id, payload)</code></pre>
        </div>
        
        <h3>Implementation Details</h3>
        <p>The n8n integration includes several key components:</p>
        <ul>
          <li><strong>Webhook Endpoints:</strong> Custom endpoints that can be triggered by n8n workflows.</li>
          <li><strong>N8n Service:</strong> Internal service class that manages communication with n8n.</li>
          <li><strong>Workflow Templates:</strong> Predefined workflow templates that can be imported into n8n.</li>
          <li><strong>Authentication:</strong> Secure authentication mechanisms for n8n-triggered actions.</li>
        </ul>
        
        <h3>Common Workflow Scenarios</h3>
        <ul>
          <li><strong>Lead Processing:</strong> Orchestrated workflows for processing new leads through multiple services.</li>
          <li><strong>Follow-up Sequences:</strong> Time-based follow-up actions for leads that haven't responded.</li>
          <li><strong>Data Synchronization:</strong> Periodic workflows to synchronize data between systems.</li>
          <li><strong>Error Recovery:</strong> Automated retry and recovery workflows for failed operations.</li>
          <li><strong>Notifications:</strong> Advanced notification workflows beyond the basic email notifications.</li>
        </ul>
        
        <h3>Benefits</h3>
        <p>The n8n integration provides several advantages:</p>
        <ul>
          <li><strong>Visual Workflow Design:</strong> Enables non-developers to create and modify automation workflows.</li>
          <li><strong>Flexible Integration:</strong> Connects the application with additional third-party services.</li>
          <li><strong>Reduced Code Complexity:</strong> Moves complex workflow logic from code to n8n's visual interface.</li>
          <li><strong>Operational Agility:</strong> Allows rapid workflow changes without application code modifications.</li>
        </ul>
      </section>
    `;
  }

  getNongoalsSection() {
    return `
      <section id="nongoals" class="content-section ${this.state.activeSection === 'nongoals' ? 'active' : ''}">
        <h2>Non-Goals (for v1)</h2>
        <p>To maintain focus and ensure timely delivery, the following features have been explicitly excluded from the v1 release of the Stahla AI SDR application.</p>
        
        <h3>Excluded Features</h3>
        <ul>
          <li><strong>Full Analytics Dashboard:</strong> The v1 release relies on HubSpot's built-in reporting capabilities rather than implementing a comprehensive custom analytics dashboard.</li>
          <li><strong>SMS Intake Channel:</strong> While voice, web form, and email intake channels are supported, SMS is not included in the v1 scope.</li>
          <li><strong>Frontend for Operational Dashboard:</strong> The v1 release implements the backend API for the operational dashboard but not a fully implemented frontend interface.</li>
          <li><strong>Advanced Metrics:</strong> Complex metrics requiring external monitoring systems (e.g., P95 latency, historical trends, cache hit/miss ratios) are not included in v1.</li>
          <li><strong>Automated Alerting:</strong> Automated alerting based on dashboard metrics is not implemented in the v1 release.</li>
        </ul>
        
        <h3>Rationale</h3>
        <p>These features have been excluded from v1 for several reasons:</p>
        <ul>
          <li><strong>Focus on Core Functionality:</strong> Prioritizing the essential features that provide immediate business value.</li>
          <li><strong>Leveraging Existing Tools:</strong> Using HubSpot's native capabilities for functions like reporting where possible.</li>
          <li><strong>Scope Management:</strong> Maintaining a manageable scope to ensure timely delivery of the initial release.</li>
          <li><strong>User Feedback:</strong> Allowing for user feedback on v1 before committing resources to additional features.</li>
        </ul>
        
        <h3>Future Considerations</h3>
        <p>While excluded from v1, these features may be considered for future releases based on:</p>
        <ul>
          <li>User feedback and feature requests after the v1 release</li>
          <li>Business priorities and evolving requirements</li>
          <li>Resource availability for development and maintenance</li>
          <li>Integration possibilities with other systems and services</li>
        </ul>
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
      
      // Handle feature item clicks in the grid
      const featureItem = event.target.closest('.feature-item');
      if (featureItem) {
        const feature = featureItem.dataset.feature;
        if (feature) {
          this._navigateToSection(feature);
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
    
    // If navigating to a section within a category, ensure that category is expanded
    if (section === 'intake' || section === 'hubspot' || section === 'classification' ||
        section === 'handoff' || section === 'followup' || section === 'config' ||
        section === 'pricing' || section === 'dashboard' || section === 'workflow' ||
        section === 'nongoals') {
      this.state.expandedCategories.add('features');
    }
    
    this.render();
    
    // Scroll to top of content
    const mainElement = this.shadowObj.querySelector('#features-docs-main');
    if (mainElement) {
      mainElement.scrollTop = 0;
    }
  }

  getStyles() {
    return /* html */`
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
        
        .features-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .features-docs-header {
          padding: 0;
        }
        
        .features-docs-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .features-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .features-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .features-docs-sidebar {
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

        .features-docs-sidebar::-webkit-scrollbar {
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
        
        .features-docs-main {
          flex: 1;
          padding: 20px 0;
          min-width: 0;
        }
        
        .features-content-container {
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
        
        .features-content-container {
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
        
        .feature-overview {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .feature-card {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
        }
        
        .feature-card h4 {
          margin: 0 0 10px;
          color: var(--title-color);
        }
        
        .feature-card p {
          margin: 0;
          font-size: 0.9rem;
        }
        
        .features-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .feature-item {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .feature-item:hover {
          border-color: var(--accent-color);
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow-alt);
        }
        
        .feature-item h3 {
          margin: 0 0 10px;
          font-size: 1.2rem;
          color: var(--title-color);
        }
        
        .feature-item p {
          margin: 10px 0 0;
          font-size: 0.9rem;
        }
        
        @media (max-width: 900px) {
          .features-docs-content {
            flex-direction: column;
          }
          
          .features-docs-sidebar {
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
          
          .feature-overview,
          .features-grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
    `;
  }
}