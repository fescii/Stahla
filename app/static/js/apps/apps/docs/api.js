export default class ApiDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0; // Add counter to track renders for debugging

    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedEndpoints: new Set(), // Track expanded/collapsed endpoints - will be populated after render
      expandedSchemas: new Set(),   // Track expanded/collapsed schemas
      expandedSubmenu: false,       // Track submenu state for mobile
      expandedCategories: new Set(['endpoints']) // Track expanded categories (starts with endpoints expanded)
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
    this.renderCount++; // Increment render count for debugging
    console.log(`Rendering API docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      <div class="api-docs">
        <div class="api-docs-content">
          <nav class="api-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="api-docs-main" class="api-docs-main">
            <div id="content-container" class="api-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="api-docs-header">
        <h1>Stahla AI SDR API</h1>
        <p>A comprehensive guide to integrating with the Stahla AI SDR API</p>
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
          <div class="nav-section ${this.state.activeSection === 'authentication' ? 'active' : ''}">
            <a class="nav-link" data-section="authentication">Authentication</a>
          </div>
          <div class="nav-section ${this.isEndpointsActive() ? 'active' : ''} ${this.state.expandedCategories.has('endpoints') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-section="endpoints" data-category="endpoints">
              <span class="link-text">API Endpoints</span>
              <span class="expand-icon">${this.state.expandedCategories.has('endpoints') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'health' ? 'active' : ''}" data-section="health">Health Check</a>
              <a class="nav-link sub ${this.state.activeSection === 'classification' ? 'active' : ''}" data-section="classification">Classification</a>
              <a class="nav-link sub ${this.state.activeSection === 'docs' ? 'active' : ''}" data-section="docs">Documentation</a>
              <a class="nav-link sub ${this.state.activeSection === 'webhooks' ? 'active' : ''}" data-section="webhooks">Webhooks</a>
              <a class="nav-link sub ${this.state.activeSection === 'dashboard' ? 'active' : ''}" data-section="dashboard">Dashboard</a>
              <a class="nav-link sub ${this.state.activeSection === 'auth' ? 'active' : ''}" data-section="auth">Auth</a>
              <a class="nav-link sub ${this.state.activeSection === 'bland' ? 'active' : ''}" data-section="bland">Bland AI</a>
              <a class="nav-link sub ${this.state.activeSection === 'test' ? 'active' : ''}" data-section="test">Testing</a>
              <a class="nav-link sub ${this.state.activeSection === 'errors' ? 'active' : ''}" data-section="errors">Error Logs</a>
            </div>
          </div>
          <div class="nav-section ${this.isExternalActive() ? 'active' : ''} ${this.state.expandedCategories.has('external') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-section="external" data-category="external">
              <span class="link-text">External APIs</span>
              <span class="expand-icon">${this.state.expandedCategories.has('external') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'blandai' ? 'active' : ''}" data-section="blandai">Bland.ai</a>
              <a class="nav-link sub ${this.state.activeSection === 'hubspot' ? 'active' : ''}" data-section="hubspot">HubSpot</a>
              <a class="nav-link sub ${this.state.activeSection === 'gmaps' ? 'active' : ''}" data-section="gmaps">Google Maps</a>
              <a class="nav-link sub ${this.state.activeSection === 'gsheets' ? 'active' : ''}" data-section="gsheets">Google Sheets</a>
              <a class="nav-link sub ${this.state.activeSection === 'n8n' ? 'active' : ''}" data-section="n8n">n8n</a>
            </div>
          </div>
          <div class="nav-section ${this.state.activeSection === 'error-handling' ? 'active' : ''}">
            <a class="nav-link" data-section="error-handling">Error Handling</a>
          </div>
        </div>
      </div>
    `;
  }

  isEndpointsActive() {
    const endpointSections = ['endpoints', 'health', 'classification', 'docs', 'webhooks', 'dashboard', 'auth', 'bland', 'test', 'errors'];
    return endpointSections.includes(this.state.activeSection);
  }

  isExternalActive() {
    const externalSections = ['external', 'blandai', 'hubspot', 'gmaps', 'gsheets', 'n8n'];
    return externalSections.includes(this.state.activeSection);
  }

  getMainContent() {
    return /* html */ `
      ${this.getIntroductionSection()}
      ${this.getAuthenticationSection()}
      ${this.getEndpointsSection()}
      ${this.getErrorHandlingSection()}
    `;
  }

  getIntroductionSection() {
    return /* html */ `
      <section id="introduction" class="content-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
        <h2>Introduction</h2>
        <p>This document provides a guide to the Stahla AI SDR API and the external APIs it interacts with. It details internal endpoints, authentication, request/response formats, and summarizes external API usage.</p>
        
        <h3>Base URL</h3>
        <div class="code-block">
          <pre><code>/api/v1</code></pre>
          <button class="copy-btn" data-text="/api/v1">Copy</button>
        </div>
        
        <h3>Response Format</h3>
        <p>All responses are returned in JSON format. Successful responses include a <code>data</code> property containing the requested information. Error responses include an <code>error</code> property with details about what went wrong.</p>
      </section>
    `;
  }

  getAuthenticationSection() {
    return /* html */ `
      <section id="authentication" class="content-section ${this.state.activeSection === 'authentication' ? 'active' : ''}">
        <h2>Authentication</h2>
        <p>Specific endpoints require authentication as noted:</p>
        <ul>
          <li><strong>Pricing Webhooks:</strong> Require an API key passed via the <code>Authorization: Bearer &lt;API_KEY&gt;</code> header.</li>
          <li><strong>Dashboard API:</strong> Requires authentication (placeholder implementation currently allows access).</li>
        </ul>
        
        <h3>API Key Authentication</h3>
        <p>Include your API key in the <code>Authorization</code> header for endpoints that require it:</p>
        <div class="code-block">
          <pre><code>Authorization: Bearer YOUR_API_KEY</code></pre>
          <button class="copy-btn" data-text="Authorization: Bearer YOUR_API_KEY">Copy</button>
        </div>
      </section>
    `;
  }

  getEndpointsSection() {
    return /* html */ `
      <section id="endpoints" class="content-section ${this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h2>API Endpoints</h2>
        <p>The API provides the following endpoints for interacting with the Stahla AI SDR system.</p>
        
        ${this.getHealthSection()}
        ${this.getClassificationSection()}
        ${this.getDocsSection()}
        ${this.getWebhooksSection()}
        ${this.getDashboardSection()}
        ${this.getAuthSection()}
        ${this.getBlandSection()}
        ${this.getTestSection()}
        ${this.getErrorsSection()}
      </section>
    `;
  }

  getHealthSection() {
    return /* html */ `
      <section id="health" class="endpoint-group ${this.state.activeSection === 'health' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Health Check</h3>
        
        <div class="endpoint" data-endpoint="health-check">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/health/</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Checks the health and status of the API application, including basic system metrics.</p>
            
            <h4>Authentication</h4>
            <p>Not Required</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>HealthCheckResponse</code> model containing <code>status</code>, <code>uptime</code>, <code>cpu_usage</code>, <code>memory_usage</code>.</p>
            <div class="code-block">
              <pre><code>{
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
}</code></pre>
              <button class="copy-btn" data-text='{"status":"ok","uptime":"1 day, 2:30:45","cpu_usage":15.5,"memory_usage":{"total":8192.0,"available":4096.0,"percent":50.0,"used":4096.0,"free":4096.0}}'>Copy</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getClassificationSection() {
    return /* html */ `
      <section id="classification" class="endpoint-group ${this.state.activeSection === 'classification' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Classification</h3>
        
        <div class="endpoint" data-endpoint="classification">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/classify/</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Takes input data (from forms, emails, calls) and classifies the lead type (Services, Logistics, Leads, Disqualify) using the configured method (rules or AI).</p>
            
            <h4>Authentication</h4>
            <p>Not Required (Assumed internal call or protected by ingress)</p>
            
            <h4>Request Body</h4>
            <p><code>ClassificationInput</code> model. Contains source, raw data, extracted data fields.</p>
            <div class="code-block">
              <pre><code>{
  "source": "form", // or "email", "call", etc.
  "raw_data": "string or object with raw input",
  "extracted_data": {
    "firstname": "John",
    "lastname": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "company": "Acme Corp",
    "job_title": "Logistics Manager",
    "product_interest": "Equipment Rental",
    "delivery_location": "123 Main St, Anytown, USA",
    "notes": "Looking for immediate availability",
    "timeline": "ASAP"
  },
  "metadata": {
    "ip_address": "192.168.1.1",
    "timestamp": "2025-05-18T14:30:00Z",
    "session_id": "abc123"
  }
}</code></pre>
              <button class="copy-btn" data-text='{"source":"form","raw_data":"string or object with raw input","extracted_data":{"firstname":"John","lastname":"Doe","email":"john.doe@example.com","phone":"+1234567890","company":"Acme Corp","job_title":"Logistics Manager","product_interest":"Equipment Rental","delivery_location":"123 Main St, Anytown, USA","notes":"Looking for immediate availability","timeline":"ASAP"},"metadata":{"ip_address":"192.168.1.1","timestamp":"2025-05-18T14:30:00Z","session_id":"abc123"}}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p><code>ClassificationResult</code> model. Contains the <code>ClassificationOutput</code> (lead_type, reasoning, confidence, metadata).</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "lead_type": "Services", // "Services", "Logistics", "Leads", "Disqualify"
    "reasoning": "Client is looking for equipment rental services with specific timeline and location requirements.",
    "confidence": 0.92,
    "metadata": {
      "method": "ai", // or "rules"
      "processing_time_ms": 350,
      "model_version": "classification-v3"
    }
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"lead_type":"Services","reasoning":"Client is looking for equipment rental services with specific timeline and location requirements.","confidence":0.92,"metadata":{"method":"ai","processing_time_ms":350,"model_version":"classification-v3"}},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getDocsSection() {
    return /* html */ `
      <section id="docs" class="endpoint-group ${this.state.activeSection === 'docs' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Documentation</h3>
        
        <div class="endpoint" data-endpoint="documentation">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/docs/{doc_path:path}</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Serves project documentation files (from the <code>/docs</code> directory) rendered as HTML pages.</p>
            
            <h4>Authentication</h4>
            <p>Not Required</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response</h4>
            <p>HTML content of the rendered Markdown file or 404 if not found.</p>
          </div>
        </div>
      </section>
    `;
  }

  getWebhooksSection() {
    return /* html */ `
      <section id="webhooks" class="endpoint-group ${this.state.activeSection === 'webhooks' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Webhooks</h3>
        
        <div class="endpoint" data-endpoint="form-webhook">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/webhook/form</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Receives web form submission data. Triggers lead classification and HubSpot updates if complete, or Bland.ai follow-up if incomplete.</p>
            
            <h4>Authentication</h4>
            <p>Not Required</p>
            
            <h4>Request Body</h4>
            <p><code>FormPayload</code> model (contains standard form fields).</p>
            <div class="code-block">
              <pre><code>{
  "firstname": "John",
  "lastname": "Doe",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "company": "Acme Corp",
  "job_title": "Logistics Manager",
  "product_interest": "Equipment Rental",
  "delivery_location": "123 Main St, Anytown, USA",
  "notes": "Looking for immediate availability",
  "timeline": "ASAP"
}</code></pre>
              <button class="copy-btn" data-text='{"firstname":"John","lastname":"Doe","email":"john.doe@example.com","phone":"+1234567890","company":"Acme Corp","job_title":"Logistics Manager","product_interest":"Equipment Rental","delivery_location":"123 Main St, Anytown, USA","notes":"Looking for immediate availability","timeline":"ASAP"}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p>Status message indicating form processing result.</p>
            <div class="code-block">
              <pre><code>// On complete form:
{
  "status": "success",
  "message": "Form processed and classification initiated.",
  "classification_result": { /* ClassificationOutput */ },
  "hubspot_update_status": "initiated"
}

// On incomplete form:
{
  "status": "incomplete",
  "message": "Form incomplete, initiating follow-up call."
}</code></pre>
              <button class="copy-btn" data-text='{"status":"success","message":"Form processed and classification initiated.","classification_result":{},"hubspot_update_status":"initiated"}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="voice-webhook">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/webhook/voice</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Receives call completion data from Bland.ai. Processes the transcript and triggers lead classification.</p>
            
            <h4>Authentication</h4>
            <p>Not Required</p>
            
            <h4>Request Body</h4>
            <p><code>BlandWebhookPayload</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "call_id": "bland_12345",
  "status": "completed",
  "duration": 240,
  "transcript": "Full conversation transcript...",
  "summary": "Summary of the conversation",
  "variables": {
    "firstname": "John",
    "lastname": "Doe",
    "company": "Acme Corp",
    "product_interest": "Equipment Rental",
    "delivery_location": "123 Main St, Anytown, USA"
  },
  "metadata": {
    "contact_id": "hubspot_contact_123",
    "request_id": "original_request_abc"
  }
}</code></pre>
              <button class="copy-btn" data-text='{"call_id":"bland_12345","status":"completed","duration":240,"transcript":"Full conversation transcript...","summary":"Summary of the conversation","variables":{"firstname":"John","lastname":"Doe","company":"Acme Corp","product_interest":"Equipment Rental","delivery_location":"123 Main St, Anytown, USA"},"metadata":{"contact_id":"hubspot_contact_123","request_id":"original_request_abc"}}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p>Status message indicating webhook processing result.</p>
            <div class="code-block">
              <pre><code>{
  "status": "success",
  "message": "Webhook processed, classification initiated."
}</code></pre>
              <button class="copy-btn" data-text='{"status":"success","message":"Webhook processed, classification initiated."}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="hubspot-webhook">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/webhook/hubspot</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Receives webhook events from HubSpot (e.g., contact updates).</p>
            
            <h4>Authentication</h4>
            <p>Not Required (Requires validation of HubSpot signature in a real implementation)</p>
            
            <h4>Request Body</h4>
            <p>Varies depending on the HubSpot webhook event type.</p>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "message": "HubSpot webhook received"
}</code></pre>
              <button class="copy-btn" data-text='{"message":"HubSpot webhook received"}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="pricing-location-lookup">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/webhook/pricing/location_lookup</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Accepts a delivery location and triggers an asynchronous background task to calculate the distance to the nearest branch using Google Maps and cache the result in Redis.</p>
            
            <h4>Authentication</h4>
            <p>Required (<code>Authorization: Bearer &lt;PRICING_WEBHOOK_API_KEY&gt;</code>)</p>
            
            <h4>Request Body</h4>
            <div class="code-block">
              <pre><code>{
  "delivery_location": "1600 Amphitheatre Parkway, Mountain View, CA"
}</code></pre>
              <button class="copy-btn" data-text='{"delivery_location":"1600 Amphitheatre Parkway, Mountain View, CA"}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "message": "Location lookup accepted for background processing."
}</code></pre>
              <button class="copy-btn" data-text='{"message":"Location lookup accepted for background processing."}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="pricing-quote">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/webhook/pricing/quote</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Calculates a comprehensive price quote with detailed information about the rental, product, location, and budget breakdown.</p>
            
            <h4>Authentication</h4>
            <p>Required (<code>Authorization: Bearer &lt;PRICING_WEBHOOK_API_KEY&gt;</code>)</p>
            
            <h4>Request Body</h4>
            <div class="code-block">
              <pre><code>{
  "request_id": "quote_req_12345",
  "delivery_location": "1600 Amphitheatre Parkway, Mountain View, CA",
  "trailer_type": "equipment_48ft",
  "rental_start_date": "2025-06-01",
  "rental_days": 30,
  "usage_type": "construction",
  "extras": ["ramps", "liftgate"]
}</code></pre>
              <button class="copy-btn" data-text='{"request_id":"quote_req_12345","delivery_location":"1600 Amphitheatre Parkway, Mountain View, CA","trailer_type":"equipment_48ft","rental_start_date":"2025-06-01","rental_days":30,"usage_type":"construction","extras":["ramps","liftgate"]}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "request_id": "quote_req_12345",
  "quote_id": "Q-12345678",
  "quote": {
    "line_items": [
      {
        "description": "Equipment Trailer 48ft Rental (30 days)",
        "unit_price": 75.00,
        "quantity": 30,
        "total": 2250.00
      },
      {
        "description": "Delivery Fee (Tier 2)",
        "unit_price": 250.00,
        "quantity": 1,
        "total": 250.00
      },
      {
        "description": "Ramps",
        "unit_price": 15.00,
        "quantity": 30,
        "total": 450.00
      },
      {
        "description": "Liftgate",
        "unit_price": 20.00,
        "quantity": 30,
        "total": 600.00
      }
    ],
    "subtotal": 3550.00,
    "delivery_tier_applied": "Tier 2 (26-50 miles)",
    "delivery_details": {
      "base_fee": 150.00,
      "distance_fee": 100.00,
      "total_delivery_fee": 250.00
    },
    "product_details": {
      "name": "Equipment Trailer 48ft",
      "dimensions": {
        "length_ft": 48,
        "width_ft": 8.5,
        "height_ft": 13.5
      },
      "capacity": {
        "weight_lbs": 40000,
        "volume_cuft": 5500
      },
      "features": ["Air Ride Suspension", "Steel Construction", "Multiple Tie-downs"]
    },
    "rental_details": {
      "start_date": "2025-06-01",
      "end_date": "2025-07-01",
      "days": 30,
      "pricing_tier": "monthly"
    },
    "budget_details": {
      "taxes": {
        "sales_tax_rate": 0.0825,
        "sales_tax_amount": 292.88
      },
      "fees": {
        "environmental_fee": 45.00,
        "processing_fee": 25.00
      },
      "daily_rate_equivalent": 118.33,
      "weekly_rate_equivalent": 828.33,
      "total_due": 3912.88
    },
    "notes": "Quote valid for 14 days. Damage protection available at additional cost."
  },
  "location_details": {
    "branch": {
      "id": "branch_ca_southbay",
      "name": "South Bay Branch",
      "address": "123 Industrial Way, Sunnyvale, CA 94085",
      "phone": "+14085551234",
      "email": "southbay@example.com"
    },
    "distance_km": 48.2,
    "distance_miles": 29.9,
    "service_area_tier": "Tier 2"
  },
  "metadata": {
    "quote_generated": "2025-05-18T14:35:22Z",
    "pricing_catalog_version": "2025-05-15",
    "distance_calculation_method": "google_maps"
  }
}</code></pre>
              <button class="copy-btn" data-text='{"request_id":"quote_req_12345","quote_id":"Q-12345678","quote":{"line_items":[{"description":"Equipment Trailer 48ft Rental (30 days)","unit_price":75.00,"quantity":30,"total":2250.00},{"description":"Delivery Fee (Tier 2)","unit_price":250.00,"quantity":1,"total":250.00},{"description":"Ramps","unit_price":15.00,"quantity":30,"total":450.00},{"description":"Liftgate","unit_price":20.00,"quantity":30,"total":600.00}],"subtotal":3550.00,"delivery_tier_applied":"Tier 2 (26-50 miles)","delivery_details":{"base_fee":150.00,"distance_fee":100.00,"total_delivery_fee":250.00},"product_details":{"name":"Equipment Trailer 48ft","dimensions":{"length_ft":48,"width_ft":8.5,"height_ft":13.5},"capacity":{"weight_lbs":40000,"volume_cuft":5500},"features":["Air Ride Suspension","Steel Construction","Multiple Tie-downs"]},"rental_details":{"start_date":"2025-06-01","end_date":"2025-07-01","days":30,"pricing_tier":"monthly"},"budget_details":{"taxes":{"sales_tax_rate":0.0825,"sales_tax_amount":292.88},"fees":{"environmental_fee":45.00,"processing_fee":25.00},"daily_rate_equivalent":118.33,"weekly_rate_equivalent":828.33,"total_due":3912.88},"notes":"Quote valid for 14 days. Damage protection available at additional cost."},"location_details":{"branch":{"id":"branch_ca_southbay","name":"South Bay Branch","address":"123 Industrial Way, Sunnyvale, CA 94085","phone":"+14085551234","email":"southbay@example.com"},"distance_km":48.2,"distance_miles":29.9,"service_area_tier":"Tier 2"},"metadata":{"quote_generated":"2025-05-18T14:35:22Z","pricing_catalog_version":"2025-05-15","distance_calculation_method":"google_maps"}}'>Copy</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getTestSection() {
    return /* html */ `
      <section id="test" class="endpoint-group ${this.state.activeSection === 'test' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Testing</h3>
        
        <div class="endpoint" data-endpoint="test-connection">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/test/connection</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Tests API connection and returns a detailed status report of all connected systems and dependencies.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>TestConnectionResponse</code> model containing detailed connection status.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "status": "operational",
    "api_version": "1.5.2",
    "timestamp": "2025-05-19T14:32:18Z",
    "environment": "production",
    "dependencies": {
      "database": {
        "status": "connected",
        "latency_ms": 5,
        "details": "PostgreSQL 14.5"
      },
      "redis": {
        "status": "connected",
        "latency_ms": 2,
        "details": "Redis 6.2.6"
      },
      "blob_storage": {
        "status": "connected",
        "latency_ms": 45,
        "details": "AWS S3"
      }
    },
    "external_services": {
      "bland_ai": {
        "status": "operational",
        "latency_ms": 120,
        "last_successful_call": "2025-05-19T14:30:12Z"
      },
      "hubspot": {
        "status": "operational",
        "latency_ms": 98,
        "last_successful_call": "2025-05-19T14:31:03Z"
      },
      "google_maps": {
        "status": "operational",
        "latency_ms": 76,
        "last_successful_call": "2025-05-19T14:29:45Z"
      }
    },
    "resource_usage": {
      "cpu_usage_percent": 12.5,
      "memory_usage_percent": 48.2,
      "disk_usage_percent": 37.8
    }
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"status":"operational","api_version":"1.5.2","timestamp":"2025-05-19T14:32:18Z","environment":"production","dependencies":{"database":{"status":"connected","latency_ms":5,"details":"PostgreSQL 14.5"},"redis":{"status":"connected","latency_ms":2,"details":"Redis 6.2.6"},"blob_storage":{"status":"connected","latency_ms":45,"details":"AWS S3"}},"external_services":{"bland_ai":{"status":"operational","latency_ms":120,"last_successful_call":"2025-05-19T14:30:12Z"},"hubspot":{"status":"operational","latency_ms":98,"last_successful_call":"2025-05-19T14:31:03Z"},"google_maps":{"status":"operational","latency_ms":76,"last_successful_call":"2025-05-19T14:29:45Z"}},"resource_usage":{"cpu_usage_percent":12.5,"memory_usage_percent":48.2,"disk_usage_percent":37.8}},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="test-mock-call">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/test/mock-call</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Generates a mock Bland.ai call for testing without actually placing a real call.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Request Body</h4>
            <p><code>MockCallRequest</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "success": true,
  "call_duration_seconds": 120,
  "conversation_type": "voicemail",
  "contact_id": "5678901",
  "scenario": "standard_follow_up"
}</code></pre>
              <button class="copy-btn" data-text='{"success":true,"call_duration_seconds":120,"conversation_type":"voicemail","contact_id":"5678901","scenario":"standard_follow_up"}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p><code>MockCallResponse</code> model containing simulated call results.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "mock_call_id": "mock_call_987654321",
    "status": "completed",
    "result": "success",
    "call_details": {
      "duration_seconds": 120,
      "start_time": "2025-05-19T15:00:00Z",
      "end_time": "2025-05-19T15:02:00Z",
      "conversation_type": "voicemail",
      "call_recording_url": "https://example.com/mock-recordings/987654321.mp3",
      "transcription": "Hello, this is a mock call transcription for testing purposes. The call simulated leaving a voicemail for the contact."
    },
    "contact_details": {
      "contact_id": "5678901",
      "phone": "+15551234567",
      "name": "Test Contact"
    },
    "mock_metadata": {
      "scenario": "standard_follow_up",
      "generated_at": "2025-05-19T15:00:00Z",
      "is_simulation": true
    }
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"mock_call_id":"mock_call_987654321","status":"completed","result":"success","call_details":{"duration_seconds":120,"start_time":"2025-05-19T15:00:00Z","end_time":"2025-05-19T15:02:00Z","conversation_type":"voicemail","call_recording_url":"https://example.com/mock-recordings/987654321.mp3","transcription":"Hello, this is a mock call transcription for testing purposes. The call simulated leaving a voicemail for the contact."},"contact_details":{"contact_id":"5678901","phone":"+15551234567","name":"Test Contact"},"mock_metadata":{"scenario":"standard_follow_up","generated_at":"2025-05-19T15:00:00Z","is_simulation":true}},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="test-webhook-trigger">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/test/webhook-trigger</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Triggers a test webhook event to validate webhook configurations and integrations.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token, Admin Only)</p>
            
            <h4>Request Body</h4>
            <p><code>WebhookTestRequest</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "webhook_url": "https://example.com/webhook-endpoint",
  "event_type": "call.completed",
  "include_sample_data": true,
  "timeout_seconds": 10
}</code></pre>
              <button class="copy-btn" data-text='{"webhook_url":"https://example.com/webhook-endpoint","event_type":"call.completed","include_sample_data":true,"timeout_seconds":10}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p><code>WebhookTestResponse</code> model with test results.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "test_id": "webhook_test_123456",
    "status": "success",
    "sent_at": "2025-05-19T15:10:00Z",
    "received_at": "2025-05-19T15:10:01Z",
    "response_time_ms": 783,
    "destination_status_code": 200,
    "destination_response": {
      "status": "received",
      "message": "Webhook processed successfully"
    },
    "event_details": {
      "event_type": "call.completed",
      "payload_size_bytes": 2048,
      "sample_data_included": true
    }
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"test_id":"webhook_test_123456","status":"success","sent_at":"2025-05-19T15:10:00Z","received_at":"2025-05-19T15:10:01Z","response_time_ms":783,"destination_status_code":200,"destination_response":{"status":"received","message":"Webhook processed successfully"},"event_details":{"event_type":"call.completed","payload_size_bytes":2048,"sample_data_included":true}},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getErrorsSection() {
    return /* html */ `
      <section id="errors" class="endpoint-group ${this.state.activeSection === 'errors' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Error Logs</h3>
        
        <div class="endpoint" data-endpoint="errors-list">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/errors/</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Retrieves a paginated list of system error logs with filtering options.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token, Admin Only)</p>
            
            <h4>Query Parameters</h4>
            <p>
              <code>page</code> (int, optional, default 1) - Page number for pagination<br>
              <code>page_size</code> (int, optional, default 50) - Number of items per page<br>
              <code>severity</code> (string, optional) - Filter by error severity (info, warning, error, critical)<br>
              <code>source</code> (string, optional) - Filter by error source (api, bland, database, etc.)<br>
              <code>start_date</code> (string, optional) - Filter errors after this date (ISO 8601 format)<br>
              <code>end_date</code> (string, optional) - Filter errors before this date (ISO 8601 format)
            </p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>PaginatedErrorLogResponse</code> model containing error log entries.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "items": [
      {
        "id": "err_123456789",
        "timestamp": "2025-05-19T12:34:56Z",
        "severity": "error",
        "source": "bland",
        "message": "Failed to complete Bland.ai call due to API timeout",
        "details": {
          "call_id": "call_987654321",
          "contact_id": "5678901",
          "error_code": "TIMEOUT_ERROR",
          "http_status": 504,
          "request_id": "req_123987",
          "stack_trace": "Error: Request timed out after 30000ms\n    at BlandClient.makeCall (/app/services/bland.js:156:23)\n    at processTicksAndRejections (node:internal/process/task_queues:95:5)"
        },
        "resolved": false,
        "resolution_notes": null
      },
      {
        "id": "err_123456788",
        "timestamp": "2025-05-19T12:30:22Z",
        "severity": "warning",
        "source": "database",
        "message": "Database query exceeded performance threshold",
        "details": {
          "query_id": "q_78901234",
          "execution_time_ms": 5482,
          "threshold_ms": 1000,
          "query_type": "SELECT",
          "table": "call_logs"
        },
        "resolved": true,
        "resolution_notes": "Added index on call_date column to improve query performance"
      }
    ],
    "page": 1,
    "page_size": 50,
    "total_items": 237,
    "total_pages": 5
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"items":[{"id":"err_123456789","timestamp":"2025-05-19T12:34:56Z","severity":"error","source":"bland","message":"Failed to complete Bland.ai call due to API timeout","details":{"call_id":"call_987654321","contact_id":"5678901","error_code":"TIMEOUT_ERROR","http_status":504,"request_id":"req_123987","stack_trace":"Error: Request timed out after 30000ms\n    at BlandClient.makeCall (/app/services/bland.js:156:23)\n    at processTicksAndRejections (node:internal/process/task_queues:95:5)"}}],"page":1,"page_size":50,"total_items":237,"total_pages":5},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="error-details">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/errors/{error_id}</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Retrieves detailed information about a specific error by ID.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token, Admin Only)</p>
            
            <h4>Path Parameters</h4>
            <p><code>error_id</code> (string) - ID of the error to retrieve</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>ErrorLogDetailResponse</code> model with complete error details.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "id": "err_123456789",
    "timestamp": "2025-05-19T12:34:56Z",
    "severity": "error",
    "source": "bland",
    "message": "Failed to complete Bland.ai call due to API timeout",
    "details": {
      "call_id": "call_987654321",
      "contact_id": "5678901",
      "error_code": "TIMEOUT_ERROR",
      "http_status": 504,
      "request_id": "req_123987",
      "request_body": {
        "phone_number": "+15551234567",
        "task": "Follow up on incomplete form",
        "voice_id": 0,
        "reduce_latency": true,
        "max_duration": 12
      },
      "response_body": {
        "error": "Gateway Timeout",
        "message": "The request timed out while waiting for a response from the Bland.ai API"
      },
      "stack_trace": "Error: Request timed out after 30000ms\n    at BlandClient.makeCall (/app/services/bland.js:156:23)\n    at processTicksAndRejections (node:internal/process/task_queues:95:5)",
      "user_id": "user_123456",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    },
    "resolved": false,
    "resolution_notes": null,
    "related_errors": [
      {
        "id": "err_123456780",
        "timestamp": "2025-05-19T12:20:12Z",
        "severity": "error",
        "message": "Similar timeout error from same source",
        "source": "bland"
      }
    ],
    "system_state": {
      "cpu_usage_percent": 78.5,
      "memory_usage_percent": 82.3,
      "active_connections": 145,
      "api_response_time_ms": 2345
    }
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"id":"err_123456789","timestamp":"2025-05-19T12:34:56Z","severity":"error","source":"bland","message":"Failed to complete Bland.ai call due to API timeout","details":{"call_id":"call_987654321","contact_id":"5678901","error_code":"TIMEOUT_ERROR","http_status":504,"request_id":"req_123987","request_body":{"phone_number":"+15551234567","task":"Follow up on incomplete form","voice_id":0,"reduce_latency":true,"max_duration":12},"response_body":{"error":"Gateway Timeout","message":"The request timed out while waiting for a response from the Bland.ai API"},"stack_trace":"Error: Request timed out after 30000ms\n    at BlandClient.makeCall (/app/services/bland.js:156:23)\n    at processTicksAndRejections (node:internal/process/task_queues:95:5)","user_id":"user_123456","ip_address":"192.168.1.100","user_agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"},"resolved":false,"resolution_notes":null,"related_errors":[{"id":"err_123456780","timestamp":"2025-05-19T12:20:12Z","severity":"error","message":"Similar timeout error from same source","source":"bland"}],"system_state":{"cpu_usage_percent":78.5,"memory_usage_percent":82.3,"active_connections":145,"api_response_time_ms":2345}},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="error-resolve">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/errors/{error_id}/resolve</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Marks a specific error as resolved with optional resolution notes.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token, Admin Only)</p>
            
            <h4>Path Parameters</h4>
            <p><code>error_id</code> (string) - ID of the error to resolve</p>
            
            <h4>Request Body</h4>
            <p><code>ErrorResolveRequest</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "resolution_notes": "Issue resolved by restarting the Bland.ai integration service",
  "resolution_type": "service_restart"
}</code></pre>
              <button class="copy-btn" data-text='{"resolution_notes":"Issue resolved by restarting the Bland.ai integration service","resolution_type":"service_restart"}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p><code>ErrorResolveResponse</code> model confirming resolution.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "id": "err_123456789",
    "resolved": true,
    "resolved_at": "2025-05-19T15:30:45Z",
    "resolved_by": "user_admin_789",
    "resolution_notes": "Issue resolved by restarting the Bland.ai integration service",
    "resolution_type": "service_restart"
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"id":"err_123456789","resolved":true,"resolved_at":"2025-05-19T15:30:45Z","resolved_by":"user_admin_789","resolution_notes":"Issue resolved by restarting the Bland.ai integration service","resolution_type":"service_restart"},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getBlandSection() {
    return /* html */ `
      <section id="bland" class="endpoint-group ${this.state.activeSection === 'bland' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Bland AI Calls</h3>
        
        <div class="endpoint" data-endpoint="bland-initiate">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/bland/initiate</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Initiates a Bland.ai callback to a specified phone number. Associates the call with a HubSpot Contact ID.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Query Parameters</h4>
            <p><code>contact_id</code> (string, required) - HubSpot Contact ID.</p>
            
            <h4>Request Body</h4>
            <p><code>BlandCallbackRequest</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "phone_number": "+12345678900",
  "task": "Follow up on incomplete form.",
  "voice_id": 0,
  "reduce_latency": true,
  "transfer_phone_number": null,
  "record": true,
  "max_duration": 12,
  "request_data": {},
  "tools": [],
  "pathway_id": null,
  "amd": true,
  "answered_by_enabled": false,
  "interruption_threshold": 100,
  "temperature": null,
  "first_sentence": null,
  "wait_for_greeting": false,
  "webhook_url": null,
  "language": "en",
  "model": null,
  "voice_settings": null
}</code></pre>
              <button class="copy-btn" data-text='{"phone_number":"+12345678900","task":"Follow up on incomplete form.","voice_id":0,"reduce_latency":true,"transfer_phone_number":null,"record":true,"max_duration":12,"request_data":{},"tools":[],"pathway_id":null,"amd":true,"answered_by_enabled":false,"interruption_threshold":100,"temperature":null,"first_sentence":null,"wait_for_greeting":false,"webhook_url":null,"language":"en","model":null,"voice_settings":null}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <p><code>GenericResponse[BlandApiResult]</code> (Status 202 Accepted)</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "call_id": "call_abc123",
    "status": "success",
    "message": "Call initiated successfully."
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"call_id":"call_abc123","status":"success","message":"Call initiated successfully."},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="bland-retry">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/bland/retry/{contact_id}</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Retries a Bland.ai call for a given HubSpot Contact ID.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Path Parameters</h4>
            <p><code>contact_id</code> (string) - HubSpot Contact ID of the original call.</p>
            
            <h4>Query Parameters</h4>
            <p><code>retry_reason</code> (string, optional) - Reason for retrying.</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>GenericResponse[BlandApiResult]</code> (Status 202 Accepted)</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "call_id": "call_retry_abc123",
    "status": "success",
    "message": "Call retry initiated successfully."
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"call_id":"call_retry_abc123","status":"success","message":"Call retry initiated successfully."},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="bland-stats">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/bland/stats</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Retrieves statistics about Bland.ai calls (e.g., total calls, completed, failed).</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>GenericResponse[BlandCallStats]</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "total_calls": 156,
    "pending_calls": 3,
    "in_progress_calls": 2,
    "completed_calls": 142,
    "failed_calls": 9,
    "last_updated": "2025-05-18T12:00:00Z"
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"total_calls":156,"pending_calls":3,"in_progress_calls":2,"completed_calls":142,"failed_calls":9,"last_updated":"2025-05-18T12:00:00Z"},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="bland-logs">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/bland/logs</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Lists all Bland.ai call logs with pagination and filtering.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Query Parameters</h4>
            <p>
              <code>page</code> (int, optional, default 1) - Page number<br>
              <code>page_size</code> (int, optional, default 10) - Number of items per page<br>
              <code>status</code> (BlandCallStatus enum, optional) - Filter by call status<br>
              <code>sort_field</code> (string, optional, default 'created_at') - Field to sort by<br>
              <code>sort_order</code> (string, optional, default 'desc') - Sort order ('asc' or 'desc')
            </p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>GenericResponse[PaginatedBlandCallResponse]</code> model.</p>
            <div class="code-block">
              <pre><code>{
  "data": {
    "items": [
      {
        "id": "call_log_123",
        "call_id": "call_abc123",
        "contact_id": "hubspot_contact_456",
        "phone_number": "+12345678900",
        "status": "completed",
        "created_at": "2025-05-18T10:00:00Z",
        "updated_at": "2025-05-18T10:05:30Z",
        "duration_seconds": 120,
        "call_recording_url": "https://example.com/recordings/call_abc123.mp3",
        "summary": "Call completed successfully. The customer expressed interest in Equipment Trailers and requested a follow-up next week.",
        "sentiment": "positive"
      },
      {
        "id": "call_log_124",
        "call_id": "call_abc124",
        "contact_id": "hubspot_contact_457",
        "phone_number": "+12345678901",
        "status": "failed",
        "created_at": "2025-05-18T10:10:00Z",
        "updated_at": "2025-05-18T10:10:45Z",
        "duration_seconds": 0,
        "call_recording_url": null,
        "summary": null,
        "sentiment": null,
        "error_message": "No answer after 5 rings"
      }
    ],
    "page": 1,
    "page_size": 10,
    "total_items": 156,
    "total_pages": 16
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"items":[{"id":"call_log_123","call_id":"call_abc123","contact_id":"hubspot_contact_456","phone_number":"+12345678900","status":"completed","created_at":"2025-05-18T10:00:00Z","updated_at":"2025-05-18T10:05:30Z","duration_seconds":120,"call_recording_url":"https://example.com/recordings/call_abc123.mp3","summary":"Call completed successfully. The customer expressed interest in Equipment Trailers and requested a follow-up next week.","sentiment":"positive"},{"id":"call_log_124","call_id":"call_abc124","contact_id":"hubspot_contact_457","phone_number":"+12345678901","status":"failed","created_at":"2025-05-18T10:10:00Z","updated_at":"2025-05-18T10:10:45Z","duration_seconds":0,"call_recording_url":null,"summary":null,"sentiment":null,"error_message":"No answer after 5 rings"}],"page":1,"page_size":10,"total_items":156,"total_pages":16},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="bland-logs-failed">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/bland/logs/failed</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Lists failed Bland.ai call logs with pagination.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Query Parameters</h4>
            <p><code>page</code> (int, optional, default 1), <code>page_size</code> (int, optional, default 10)</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>GenericResponse[PaginatedBlandCallResponse]</code> (same structure as <code>/logs</code> endpoint, filtered to failed calls).</p>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="bland-logs-completed">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/bland/logs/completed</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Lists completed Bland.ai call logs with pagination.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Query Parameters</h4>
            <p><code>page</code> (int, optional, default 1), <code>page_size</code> (int, optional, default 10)</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>GenericResponse[PaginatedBlandCallResponse]</code> (same structure as <code>/logs</code> endpoint).</p>
          </div>
        </div>
      </section>
    `;
  }

  getStyles() {
    return /* html */ `
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
        
        .api-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .api-docs-header {
          padding: 20px 0 0;
        }
        
        .api-docs-header h1 {
          font-size: 2rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .api-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .api-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .api-docs-sidebar {
          width: 250px;
          padding: 20px 0;
          height: 100vh;
          overflow-y: auto;
          position: sticky;
          top: 0;
        }
        
        .sidebar-content {
          padding: 0 1rem;
        }
        
        .mobile-toggle {
          display: none;
          margin-bottom: 1rem;
        }
        
        .mobile-toggle button {
          background: none;
          border: none;
          color: var(--text-color);
          cursor: pointer;
          padding: 0.5rem;
        }
        
        .nav-sections {
          display: flex;
          flex-direction: column;
        }
        
        .nav-section {
          margin-bottom: 0.5rem;
          position: relative;
        }
        
        .nav-section.collapsed .subnav {
          display: none;
        }
        
        .nav-section.expanded .subnav {
          display: block;
          animation: fadeIn 0.2s ease-in-out;
        }
        
        .nav-link {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.5rem 0;
          color: var(--text-color);
          text-decoration: none;
          cursor: pointer;
          font-size: 0.95rem;
        }
        
        .nav-link:hover {
          color: var(--accent-color);
        }
        
        .nav-link.active {
          color: var(--accent-color);
          font-weight: 500;
        }
        
        .nav-link.sub {
          padding-left: 1rem;
          font-size: 0.9rem;
        }
        
        .expand-icon {
          font-weight: bold;
        }
        
        .subnav {
          margin-top: 0.25rem;
          margin-bottom: 0.5rem;
        }
        
        .api-docs-main {
          padding: 20px 0;
          width: calc(100% - 270px);
          min-height: 100vh;
        }
        
        .api-content-container {
          max-width: 800px;
        }
        
        .content-section {
          display: none;
          animation: fadeIn 0.3s ease-in-out;
        }
        
        .content-section.active {
          display: block;
        }
        
        .endpoint-group {
          display: none;
          margin-bottom: 2rem;
        }
        
        .endpoint-group.active {
          display: block;
        }
        
        .endpoint {
          margin-bottom: 1.5rem;
          overflow: hidden;
        }
        
        .endpoint-header {
          display: flex;
          align-items: center;
          padding: 0.75rem 1rem;
          border-radius: 6px;
          background-color: var(--hover-background);
          cursor: pointer;
        }
        
        .endpoint-header:hover {
          background-color: var(--que-background);
        }
        
        .method {
          font-family: var(--font-mono);
          font-weight: 600;
          padding: 0.2rem 0.5rem;
          border-radius: 4px;
          margin-right: 0.75rem;
          font-size: 0.8rem;
        }
        
        .method.get {
          background-color: #34d39926;
          color: #0ca678;
        }
        
        .method.post {
          background-color: #228be624;
          color: #1971c2;
        }
        
        .method.put {
          background-color: #f59f0026;
          color: #e67700;
        }
        
        .method.delete {
          background-color: #ff8d6a26;
          color: var(--error-color);
        }
        
        .path {
          font-family: var(--font-mono);
          font-size: 0.9rem;
          flex: 1;
        }
        
        .toggle-btn {
          background: none;
          border: none;
          color: var(--gray-color);
          cursor: pointer;
          font-size: 1.25rem;
          padding: 0 0.5rem;
        }
        
        .endpoint-body {
          display: none;
          padding: 7px 0;
        }
        
        .endpoint.expanded .endpoint-body {
          display: block;
          animation: fadeIn 0.2s ease-in-out;
        }
        
        .endpoint.expanded .toggle-btn .icon {
          content: "-";
        }
        
        .loading {
          padding: 2rem;
          text-align: center;
          color: var(--gray-color);
        }
        
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        
        h2 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        h3 {
          font-size: 1.25rem;
          font-weight: 600;
          margin: 2rem 0 1rem;
          color: var(--title-color);
        }
        
        h4 {
          font-size: 1rem;
          font-weight: 600;
          margin: 1.5rem 0 0.5rem;
          color: var(--label-color);
        }
        
        p {
          margin-bottom: 1rem;
        }
        
        ul, ol {
          margin-left: 1.5rem;
          margin-bottom: 1.5rem;
        }
        
        li {
          margin-bottom: 0.25rem;
        }
        
        code {
          font-family: var(--font-mono);
          background-color: var(--hover-background);
          border-radius: 3px;
          padding: 0.2rem 0.4rem;
          font-size: 0.875rem;
        }
        
        .code-block {
          position: relative;
          margin: 1rem 0 1.5rem;
          background: var(--hover-background);
          border-radius: 6px;
          overflow: hidden;
        }
        
        .code-block pre {
          overflow-x: auto;
          padding: 1rem;
          font-family: var(--font-mono);
          font-size: 0.85rem;
        }
        
        .copy-btn {
          position: absolute;
          top: 0.5rem;
          right: 0.5rem;
          background: var(--background);
          border: var(--border);
          border-radius: 4px;
          padding: 0.25rem 0.5rem;
          font-size: 0.8rem;
          cursor: pointer;
          color: var(--gray-color);
          box-shadow: var(--card-box-shadow-alt);
        }
        
        .copy-btn:hover {
          background-color: var(--hover-background);
          color: var(--accent-color);
        }
        
        /* Mobile styles */
        @media (max-width: 768px) {
          .api-docs-content {
            flex-direction: column;
          }
          
          .api-docs-sidebar {
            flex: none;
            width: 100%;
            height: auto;
            border-right: none;
            border-bottom: var(--border);
            position: relative;
            padding: 1rem;
          }
          
          .mobile-toggle {
            display: block;
          }
          
          .nav-sections {
            display: none;
          }
          
          .nav-sections.expanded {
            display: flex;
          }
          
          .api-docs-main {
            padding: 1rem;
            min-height: auto;
          }
        }
      </style>
    `;
  }
  
  getContentForSection(section) {
    switch(section) {
      case 'introduction':
        return this.getIntroductionSection();
      case 'authentication':
        return this.getAuthenticationSection();
      case 'endpoints':
        return this.getEndpointsSection();
      case 'health':
        return this.getHealthSection();
      case 'classification':
        return this.getClassificationSection();
      case 'docs':
        return this.getDocsSection();
      case 'webhooks':
        return this.getWebhooksSection();
      case 'dashboard':
        return this.getDashboardSection();
      case 'auth':
        return this.getAuthSection();
      case 'bland':
        return this.getBlandSection();
      case 'test':
        return this.getTestSection();
      case 'errors':
        return this.getErrorsSection();
      case 'error-handling':
        return this.getErrorHandlingSection();
      case 'external':
        return this.getExternalAPIsSection();
      case 'blandai':
        return this.getBlandaiSection();
      case 'hubspot':
        return this.getHubspotSection();
      case 'gmaps':
        return this.getGmapsSection();
      case 'gsheets':
        return this.getGsheetsSection();
      case 'n8n':
        return this.getN8nSection();
      default:
        return `<div class="content-section active">
          <h2>Section Not Found</h2>
          <p>The requested section "${section}" does not exist or is not yet implemented.</p>
        </div>`;
    }
  }

  getAuthSection() {
    return /* html */ `
      <section id="auth" class="endpoint-group ${this.state.activeSection === 'auth' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Auth</h3>
        <p>Endpoints for managing user authentication and API keys.</p>
        
        <div class="endpoint" data-endpoint="auth-token">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/auth/token</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Generate a new authentication token.</p>
            
            <h4>Authentication</h4>
            <p>Required (Basic Auth with username/password)</p>
            
            <h4>Request Body</h4>
            <div class="code-block">
              <pre><code>{
  "username": "admin@example.com",
  "password": "secure_password",
  "scope": "admin" // Optional scope (admin, user, read-only)
}</code></pre>
              <button class="copy-btn" data-text='{"username":"admin@example.com","password":"secure_password","scope":"admin"}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "scope": "admin"
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer","expires_in":3600,"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","scope":"admin"},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="auth-refresh">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/auth/refresh</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Refresh an expired authentication token.</p>
            
            <h4>Authentication</h4>
            <p>Not Required</p>
            
            <h4>Request Body</h4>
            <div class="code-block">
              <pre><code>{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}</code></pre>
              <button class="copy-btn" data-text='{"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "scope": "admin"
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","token_type":"bearer","expires_in":3600,"refresh_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...","scope":"admin"},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="auth-revoke">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/auth/revoke</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Revoke an active authentication token.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "data": {
    "message": "Token successfully revoked"
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"message":"Token successfully revoked"},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="api-keys-list">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/auth/api-keys</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>List all API keys for the current user.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "data": {
    "api_keys": [
      {
        "id": "key_1234567890",
        "name": "Production API Key",
        "prefix": "sk_prod_",
        "created_at": "2025-05-18T10:00:00Z",
        "last_used_at": "2025-05-19T15:30:45Z",
        "permissions": ["read", "write"],
        "expires_at": null
      },
      {
        "id": "key_0987654321",
        "name": "Staging API Key",
        "prefix": "sk_staging_",
        "created_at": "2025-05-10T08:15:30Z",
        "last_used_at": "2025-05-18T09:45:12Z",
        "permissions": ["read"],
        "expires_at": "2025-06-18T08:15:30Z"
      }
    ]
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"api_keys":[{"id":"key_1234567890","name":"Production API Key","prefix":"sk_prod_","created_at":"2025-05-18T10:00:00Z","last_used_at":"2025-05-19T15:30:45Z","permissions":["read","write"],"expires_at":null},{"id":"key_0987654321","name":"Staging API Key","prefix":"sk_staging_","created_at":"2025-05-10T08:15:30Z","last_used_at":"2025-05-18T09:45:12Z","permissions":["read"],"expires_at":"2025-06-18T08:15:30Z"}]},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
        
        <div class="endpoint" data-endpoint="api-keys-create">
          <div class="endpoint-header">
            <span class="method post">POST</span>
            <span class="path">/api/v1/auth/api-keys</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Create a new API key.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Request Body</h4>
            <div class="code-block">
              <pre><code>{
  "name": "Development API Key",
  "permissions": ["read", "write"],
  "expires_in_days": 30 // Optional, defaults to never
}</code></pre>
              <button class="copy-btn" data-text='{"name":"Development API Key","permissions":["read","write"],"expires_in_days":30}'>Copy</button>
            </div>
            
            <h4>Response Body</h4>
            <div class="code-block">
              <pre><code>{
  "data": {
    "api_key": {
      "id": "key_2468135790",
      "name": "Development API Key",
      "prefix": "sk_dev_",
      "key": "sk_dev_9876543210abcdefghijklmnopqrstuvwxyz", // Full key, only shown once
      "created_at": "2025-05-19T16:00:00Z",
      "permissions": ["read", "write"],
      "expires_at": "2025-06-18T16:00:00Z"
    }
  },
  "error": null
}</code></pre>
              <button class="copy-btn" data-text='{"data":{"api_key":{"id":"key_2468135790","name":"Development API Key","prefix":"sk_dev_","key":"sk_dev_9876543210abcdefghijklmnopqrstuvwxyz","created_at":"2025-05-19T16:00:00Z","permissions":["read","write"],"expires_at":"2025-06-18T16:00:00Z"}},"error":null}'>Copy</button>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getErrorHandlingSection() {
    return /* html */ `
      <section id="error-handling" class="content-section ${this.state.activeSection === 'error-handling' ? 'active' : ''}">
        <h2>Error Handling</h2>
        <p>All errors are returned in a consistent format with HTTP status codes that reflect the type of error.</p>
        
        <h3>Error Response Format</h3>
        <p>All error responses include an <code>error</code> object with details about what went wrong:</p>
        <div class="code-block">
          <pre><code>{
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { /* Additional error context */ }
  }
}</code></pre>
          <button class="copy-btn" data-text='{"data":null,"error":{"code":"ERROR_CODE","message":"Human-readable error message","details":{}}}'>Copy</button>
        </div>
        
        <h3>Common Error Codes</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 1rem 0;">
          <thead>
            <tr style="background-color: var(--hover-background);">
              <th style="text-align: left; padding: 0.5rem; border: 1px solid var(--border-color);">HTTP Status</th>
              <th style="text-align: left; padding: 0.5rem; border: 1px solid var(--border-color);">Error Code</th>
              <th style="text-align: left; padding: 0.5rem; border: 1px solid var(--border-color);">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">400</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>INVALID_REQUEST</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The request was malformed or contained invalid parameters.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">401</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>UNAUTHORIZED</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">Authentication credentials were missing or invalid.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">403</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>FORBIDDEN</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The authenticated user doesn't have permission to access the requested resource.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">404</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>NOT_FOUND</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The requested resource was not found.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">409</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>CONFLICT</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The request conflicts with the current state of the resource.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">422</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>VALIDATION_ERROR</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The request was valid but contained validation errors.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">429</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>RATE_LIMIT_EXCEEDED</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The client has sent too many requests in a given time period.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">500</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>SERVER_ERROR</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">An unexpected server error occurred.</td>
            </tr>
            <tr>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">503</td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);"><code>SERVICE_UNAVAILABLE</code></td>
              <td style="padding: 0.5rem; border: 1px solid var(--border-color);">The service is temporarily unavailable or undergoing maintenance.</td>
            </tr>
          </tbody>
        </table>
        
        <h3>Validation Errors</h3>
        <p>Validation errors (422 status code) include field-specific error details:</p>
        <div class="code-block">
          <pre><code>{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation error",
    "details": {
      "fields": {
        "email": "Invalid email format",
        "phone": "Phone number must be in E.164 format"
      }
    }
  }
}</code></pre>
          <button class="copy-btn" data-text='{"data":null,"error":{"code":"VALIDATION_ERROR","message":"Validation error","details":{"fields":{"email":"Invalid email format","phone":"Phone number must be in E.164 format"}}}}'>Copy</button>
        </div>
        
        <h3>Error Handling Best Practices</h3>
        <ul>
          <li>Always check the HTTP status code and error response in your client code.</li>
          <li>Implement retry logic with exponential backoff for 429 and 5xx errors.</li>
          <li>Log detailed error information to help with debugging.</li>
          <li>Provide user-friendly error messages in your application UI.</li>
        </ul>
      </section>
    `;
  }

  getExternalAPIsSection() {
    return /* html */ `
      <section id="external" class="content-section ${this.state.activeSection === 'external' ? 'active' : ''}">
        <h2>External APIs</h2>
        <p>The Stahla AI SDR system integrates with several external APIs to provide its functionality. This section describes how these integrations work.</p>
        
        ${this.getBlandaiSection()}
        ${this.getHubspotSection()}
        ${this.getGmapsSection()}
        ${this.getGsheetsSection()}
        ${this.getN8nSection()}
      </section>
    `;
  }

  getBlandaiSection() {
    return /* html */ `
      <section id="blandai" class="endpoint-group ${this.state.activeSection === 'blandai' ? 'active' : ''}">
        <h3>Bland.ai</h3>
        <p>Integration with the Bland.ai voice AI system for automated follow-up calls.</p>
        
        <h4>Configuration</h4>
        <p>The integration requires a valid Bland.ai API key, which should be set in the system environment:</p>
        <div class="code-block">
          <pre><code>BLAND_API_KEY=your_bland_ai_api_key</code></pre>
        </div>
        
        <h4>Voice Configuration</h4>
        <p>The system uses Voice ID 0 (Female) by default for all calls. This can be customized in the system settings.</p>
        
        <h4>Call Flow</h4>
        <p>The typical flow for a Bland.ai call is:</p>
        <ol>
          <li>Incomplete form submission triggers follow-up call</li>
          <li>System creates contact in HubSpot if not exists</li>
          <li>Call request is sent to Bland.ai with task prompt</li>
          <li>Bland.ai places call and captures information</li>
          <li>Webhook returns results when call completes</li>
          <li>System processes call transcript and updates HubSpot</li>
        </ol>
        
        <h4>Task Prompts</h4>
        <p>The system sends a detailed task prompt to Bland.ai that includes:</p>
        <ul>
          <li>Introduction script with company info</li>
          <li>Data collection requirements</li>
          <li>Objection handling guidance</li>
          <li>Call termination instructions</li>
        </ul>
        
        <h4>APIs Used</h4>
        <ul>
          <li><code>POST /phone/call</code> - Place an outbound call</li>
          <li><code>GET /phone/call/{call_id}</code> - Get call status</li>
          <li><code>POST /webhooks</code> - Register webhook endpoints</li>
        </ul>
        
        <h4>Error Handling</h4>
        <p>Failed calls are automatically retried up to 3 times with a 2-hour delay between attempts. Persistent failures trigger a notification to the operations team.</p>
      </section>
    `;
  }

  getHubspotSection() {
    return /* html */ `
      <section id="hubspot" class="endpoint-group ${this.state.activeSection === 'hubspot' ? 'active' : ''}">
        <h3>HubSpot</h3>
        <p>Integration with HubSpot CRM for contact management, lead tracking, and sales pipeline.</p>
        
        <h4>Configuration</h4>
        <p>The integration requires valid HubSpot API credentials:</p>
        <div class="code-block">
          <pre><code>HUBSPOT_API_KEY=your_hubspot_api_key
HUBSPOT_PORTAL_ID=your_portal_id</code></pre>
        </div>
        
        <h4>Contact Management</h4>
        <p>The system creates and updates contacts in HubSpot with the following properties:</p>
        <ul>
          <li><code>firstname</code>, <code>lastname</code> - Contact name</li>
          <li><code>email</code>, <code>phone</code> - Contact information</li>
          <li><code>company</code>, <code>jobtitle</code> - Company information</li>
          <li><code>lead_type</code> - Classification result (Services, Logistics, Leads, Disqualify)</li>
          <li><code>lead_source</code> - How the lead was acquired (Form, Call, Email)</li>
          <li><code>bland_call_status</code> - Status of follow-up calls</li>
          <li><code>bland_call_transcript</code> - Transcript of the latest call</li>
          <li><code>product_interest</code> - Product or service of interest</li>
        </ul>
        
        <h4>Workflows</h4>
        <p>The integration triggers HubSpot workflows based on lead classification:</p>
        <ul>
          <li><strong>Services Lead Flow</strong> - Routes to equipment rental team</li>
          <li><strong>Logistics Lead Flow</strong> - Routes to transportation team</li>
          <li><strong>Sales Lead Flow</strong> - Routes to general sales team</li>
          <li><strong>Disqualified Lead Flow</strong> - Tags for no follow-up</li>
        </ul>
        
        <h4>APIs Used</h4>
        <ul>
          <li><code>POST /crm/v3/objects/contacts</code> - Create contacts</li>
          <li><code>PATCH /crm/v3/objects/contacts/{id}</code> - Update contacts</li>
          <li><code>POST /crm/v3/objects/contacts/search</code> - Search for contacts</li>
          <li><code>POST /crm/v3/objects/deals</code> - Create deals</li>
          <li><code>POST /communication-preferences/v3/subscriptions/status</code> - Manage email preferences</li>
        </ul>
        
        <h4>Webhook Integration</h4>
        <p>The system registers webhooks in HubSpot to get real-time updates on:</p>
        <ul>
          <li>Contact property changes</li>
          <li>Deal stage changes</li>
          <li>Form submissions</li>
        </ul>
      </section>
    `;
  }

  getGmapsSection() {
    return /* html */ `
      <section id="gmaps" class="endpoint-group ${this.state.activeSection === 'gmaps' ? 'active' : ''}">
        <h3>Google Maps</h3>
        <p>Integration with Google Maps Platform for location validation, distance calculations, and service area determination.</p>
        
        <h4>Configuration</h4>
        <p>The integration requires a valid Google Maps API key:</p>
        <div class="code-block">
          <pre><code>GOOGLE_MAPS_API_KEY=your_google_maps_api_key</code></pre>
        </div>
        
        <h4>Features Used</h4>
        <ul>
          <li><strong>Geocoding API</strong> - Convert addresses to coordinates</li>
          <li><strong>Distance Matrix API</strong> - Calculate distances between locations</li>
          <li><strong>Places API</strong> - Validate and autocomplete addresses</li>
        </ul>
        
        <h4>Usage in the System</h4>
        <p>The Google Maps integration is primarily used for:</p>
        <ul>
          <li>Validating customer delivery addresses</li>
          <li>Calculating distance between customer locations and nearest branch</li>
          <li>Determining delivery pricing tiers based on distance</li>
          <li>Displaying location information in quotes and order confirmations</li>
        </ul>
        
        <h4>Caching Strategy</h4>
        <p>To minimize API usage and costs, the system implements a multi-level caching strategy:</p>
        <ul>
          <li>Redis cache for geocoding results (30-day expiration)</li>
          <li>Database storage for commonly queried routes</li>
          <li>Batch processing for non-urgent distance calculations</li>
        </ul>
        
        <h4>APIs Used</h4>
        <ul>
          <li><code>GET /maps/api/geocode/json</code> - Geocode addresses</li>
          <li><code>GET /maps/api/distancematrix/json</code> - Calculate distances</li>
          <li><code>GET /maps/api/place/autocomplete/json</code> - Autocomplete addresses</li>
        </ul>
      </section>
    `;
  }

  getGsheetsSection() {
    return /* html */ `
      <section id="gsheets" class="endpoint-group ${this.state.activeSection === 'gsheets' ? 'active' : ''}">
        <h3>Google Sheets</h3>
        <p>Integration with Google Sheets API for data export, reporting, and collaborative workflows.</p>
        
        <h4>Configuration</h4>
        <p>The integration requires Google service account credentials:</p>
        <div class="code-block">
          <pre><code>GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
GOOGLE_SHEETS_TEMPLATE_ID=your_template_spreadsheet_id</code></pre>
        </div>
        
        <h4>Features Used</h4>
        <ul>
          <li><strong>Spreadsheets API</strong> - Read/write data to Google Sheets</li>
          <li><strong>Drive API</strong> - Create and share spreadsheets</li>
        </ul>
        
        <h4>Usage in the System</h4>
        <p>The Google Sheets integration is primarily used for:</p>
        <ul>
          <li>Generating weekly lead reports</li>
          <li>Exporting call transcripts for quality review</li>
          <li>Creating customer-facing quotes in a formatted template</li>
          <li>Maintaining pricing catalogs that can be updated by non-technical staff</li>
        </ul>
        
        <h4>Scheduled Reports</h4>
        <p>The system automatically generates the following scheduled reports:</p>
        <ul>
          <li><strong>Daily Lead Summary</strong> - All new leads from the previous day</li>
          <li><strong>Weekly Performance Report</strong> - Call statistics and lead conversion metrics</li>
          <li><strong>Monthly Analytics</strong> - Detailed analysis of lead sources and conversion rates</li>
        </ul>
        
        <h4>APIs Used</h4>
        <ul>
          <li><code>GET /v4/spreadsheets/{spreadsheetId}</code> - Get spreadsheet metadata</li>
          <li><code>GET /v4/spreadsheets/{spreadsheetId}/values/{range}</code> - Read values</li>
          <li><code>PUT /v4/spreadsheets/{spreadsheetId}/values/{range}</code> - Update values</li>
          <li><code>POST /v4/spreadsheets</code> - Create new spreadsheets</li>
        </ul>
      </section>
    `;
  }

  getN8nSection() {
    return /* html */ `
      <section id="n8n" class="endpoint-group ${this.state.activeSection === 'n8n' ? 'active' : ''}">
        <h3>n8n</h3>
        <p>Integration with n8n workflow automation platform for custom workflows and integrations with other services.</p>
        
        <h4>Configuration</h4>
        <p>The integration requires a valid n8n instance URL and API key:</p>
        <div class="code-block">
          <pre><code>N8N_INSTANCE_URL=https://n8n.example.com
N8N_API_KEY=your_n8n_api_key</code></pre>
        </div>
        
        <h4>Features Used</h4>
        <ul>
          <li><strong>Webhooks</strong> - Trigger n8n workflows from system events</li>
          <li><strong>Workflow API</strong> - Programmatically manage workflows</li>
        </ul>
        
        <h4>Usage in the System</h4>
        <p>The n8n integration enables the following capabilities:</p>
        <ul>
          <li>Custom notification workflows for lead status changes</li>
          <li>Integration with internal ticketing systems</li>
          <li>Automated data synchronization with additional CRM systems</li>
          <li>Custom reporting workflows to collate data from multiple sources</li>
        </ul>
        
        <h4>Implemented Workflows</h4>
        <p>The system uses the following n8n workflows:</p>
        <ul>
          <li><strong>Lead Notification</strong> - Sends alerts via Slack/Email when high-value leads are identified</li>
          <li><strong>Call Failure Handler</strong> - Creates tickets in support system for failed calls</li>
          <li><strong>Quote Approval</strong> - Routes quotes exceeding certain values for manager approval</li>
          <li><strong>CRM Sync</strong> - Synchronizes data between HubSpot and other internal systems</li>
        </ul>
        
        <h4>APIs Used</h4>
        <ul>
          <li><code>POST /webhook/{webhookId}</code> - Trigger workflows</li>
          <li><code>GET /workflows</code> - List available workflows</li>
          <li><code>POST /workflows/{id}/activate</code> - Activate workflows</li>
          <li><code>POST /executions</code> - Manually execute workflows</li>
        </ul>
      </section>
    `;
  }

  _setupEventListeners() {
    // Setup navigation event listeners (these don't change with content updates)
    // Handle section navigation links
    const navLinks = this.shadowObj.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const section = link.dataset.section;
        const category = link.dataset.category;
        
        if (category) {
          // Toggle category expansion
          this._toggleCategoryExpansion(category);
        } else if (section) {
          // Navigate to section
          this._navigateToSection(section);
        }
      });
    });
    
    // Handle mobile toggle
    const toggleNav = this.shadowObj.getElementById('toggle-nav');
    if (toggleNav) {
      toggleNav.addEventListener('click', () => {
        this.state.expandedSubmenu = !this.state.expandedSubmenu;
        const navSections = this.shadowObj.querySelector('.nav-sections');
        if (navSections) {
          if (this.state.expandedSubmenu) {
            navSections.classList.add('expanded');
          } else {
            navSections.classList.remove('expanded');
          }
        }
      });
    }
    
    // Set up the initial content event listeners
    this._setupContentEventListeners();
    
    // Expand all endpoints by default
    this._expandAllEndpoints();
  }
  
  /**
   * Set up event listeners for content elements that will be re-added when content changes
   */
  _setupContentEventListeners() {
    // Handle endpoint toggles
    const toggleButtons = this.shadowObj.querySelectorAll('#content-container .toggle-btn');
    toggleButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        e.stopPropagation();
        const endpoint = button.closest('.endpoint');
        const endpointId = endpoint.dataset.endpoint;
        
        this._toggleEndpoint(endpoint, endpointId, button);
      });
    });
    
    // Handle header clicks to toggle endpoints
    const endpointHeaders = this.shadowObj.querySelectorAll('#content-container .endpoint-header');
    endpointHeaders.forEach(header => {
      header.addEventListener('click', (e) => {
        // Don't trigger if they clicked directly on the toggle button
        if (e.target.closest('.toggle-btn')) {
          return;
        }
        
        const endpoint = header.closest('.endpoint');
        const endpointId = endpoint.dataset.endpoint;
        const toggleBtn = header.querySelector('.toggle-btn');
        
        if (toggleBtn) {
          this._toggleEndpoint(endpoint, endpointId, toggleBtn);
        }
      });
    });
    
    // Handle copy buttons
    const copyButtons = this.shadowObj.querySelectorAll('#content-container .copy-btn');
    copyButtons.forEach(button => {
      button.addEventListener('click', () => {
        const textToCopy = button.dataset.text;
        if (textToCopy) {
          navigator.clipboard.writeText(textToCopy)
            .then(() => {
              // Visual feedback for copy
              const originalText = button.textContent;
              button.textContent = 'Copied!';
              button.style.backgroundColor = 'var(--accent-color)';
              button.style.color = 'var(--white-color)';
              
              setTimeout(() => {
                button.textContent = originalText;
                button.style.backgroundColor = '';
                button.style.color = '';
              }, 1500);
            })
            .catch(err => console.error('Could not copy text: ', err));
        }
      });
    });
  }
  
  /**
   * Toggle category expansion in the sidebar
   * @param {string} category - The category to toggle
   */
  _toggleCategoryExpansion(category) {
    const navSection = this.shadowObj.querySelector(`.nav-section [data-category="${category}"]`).closest('.nav-section');
    
    if (this.state.expandedCategories.has(category)) {
      this.state.expandedCategories.delete(category);
      navSection.classList.remove('expanded');
      navSection.classList.add('collapsed');
      
      // Update the expand icon
      const expandIcon = navSection.querySelector('.expand-icon');
      if (expandIcon) expandIcon.textContent = '+';
    } else {
      this.state.expandedCategories.add(category);
      navSection.classList.add('expanded');
      navSection.classList.remove('collapsed');
      
      // Update the expand icon
      const expandIcon = navSection.querySelector('.expand-icon');
      if (expandIcon) expandIcon.textContent = '−';
    }
  }
  
  /**
   * Navigate to a specific section
   * @param {string} section - The section to navigate to
   */
  _navigateToSection(section) {
    // Update UI to show the active section without full re-render
    // The state will be updated inside _updateActiveSection
    this._updateActiveSection(section);
  }
  
  /**
   * Update UI to reflect the active section
   * @param {string} section - The active section
   */
  _updateActiveSection(section) {
    // Store the previous section for comparison
    const previousSection = this.state.activeSection;
    
    // 1. Update the state
    this.state.activeSection = section;
    
    // 2. Update navigation UI 
    // Remove active class from all nav links and sections
    const allNavLinks = this.shadowObj.querySelectorAll('.nav-link');
    allNavLinks.forEach(link => link.classList.remove('active'));
    
    const allNavSections = this.shadowObj.querySelectorAll('.nav-section');
    allNavSections.forEach(navSection => navSection.classList.remove('active'));
    
    // Add active class to current nav link
    const activeNavLink = this.shadowObj.querySelector(`.nav-link[data-section="${section}"]`);
    if (activeNavLink) {
      activeNavLink.classList.add('active');
      
      // Mark parent section as active if it's a sub-link
      const parentSection = activeNavLink.closest('.nav-section');
      if (parentSection) {
        parentSection.classList.add('active');
        
        // If it's a nested item, make sure we expand the parent
        if (activeNavLink.classList.contains('sub')) {
          const parentCategory = parentSection.querySelector('.nav-link.parent');
          if (parentCategory && parentCategory.dataset.category) {
            const category = parentCategory.dataset.category;
            if (!this.state.expandedCategories.has(category)) {
              this._toggleCategoryExpansion(category);
            }
          }
        }
      }
    }
    
    // 3. Ensure proper category expansion
    // If it's under endpoints, make sure the endpoints dropdown is expanded
    if (this.isEndpointsActive()) {
      if (!this.state.expandedCategories.has('endpoints')) {
        this._toggleCategoryExpansion('endpoints');
      }
    }
    
    // If it's under external APIs, make sure the external dropdown is expanded
    if (this.isExternalActive()) {
      if (!this.state.expandedCategories.has('external')) {
        this._toggleCategoryExpansion('external');
      }
    }
    
    // 4. ONLY update the content container's innerHTML, not the whole component
    const contentContainer = this.shadowObj.querySelector('#content-container');
    if (contentContainer) {
      console.log(`Updating content for section: ${section} (previous: ${previousSection})`);
      
      // Show loading state
      contentContainer.innerHTML = `<div class="loading">Loading content...</div>`;
      
      // Update only the content container with a small delay for loading state
      setTimeout(() => {
        contentContainer.innerHTML = this.getContentForSection(section);
        
        // Re-add event listeners for the new content elements
        this._setupContentEventListeners();
      }, 10);
    }
  }
  
  /**
   * Toggle an endpoint's expanded/collapsed state
   * @param {HTMLElement} endpoint - The endpoint element
   * @param {string} endpointId - The ID of the endpoint
   * @param {HTMLElement} button - The toggle button element
   */
  _toggleEndpoint(endpoint, endpointId, button) {
    if (this.state.expandedEndpoints.has(endpointId)) {
      this.state.expandedEndpoints.delete(endpointId);
      endpoint.classList.remove('expanded');
      endpoint.classList.add('collapsed');
      
      // Update the toggle button icon
      const icon = button.querySelector('.icon');
      if (icon) icon.textContent = '+';
    } else {
      this.state.expandedEndpoints.add(endpointId);
      endpoint.classList.add('expanded');
      endpoint.classList.remove('collapsed');
      
      // Update the toggle button icon
      const icon = button.querySelector('.icon');
      if (icon) icon.textContent = '−';
    }
  }
  
  getDashboardSection() {
    return /* html */ `
      <section id="dashboard" class="endpoint-group ${this.state.activeSection === 'dashboard' ? 'active' : this.state.activeSection === 'endpoints' ? 'active' : ''}">
        <h3>Dashboard</h3>
        
        <div class="endpoint" data-endpoint="dashboard-metrics">
          <div class="endpoint-header">
            <span class="method get">GET</span>
            <span class="path">/api/v1/dashboard/metrics</span>
            <button class="toggle-btn" aria-label="Toggle details">
              <span class="icon">+</span>
            </button>
          </div>
          <div class="endpoint-body">
            <p>Retrieves key performance metrics for the dashboard.</p>
            
            <h4>Authentication</h4>
            <p>Required (Bearer Token)</p>
            
            <h4>Query Parameters</h4>
            <p>
              <code>period</code> (string, optional, default 'day') - Time period for metrics: 'day', 'week', 'month', 'quarter', 'year'<br>
              <code>date</code> (string, optional) - Reference date in ISO format (defaults to current date)
            </p>
            
            <h4>Request Body</h4>
            <p>None</p>
            
            <h4>Response Body</h4>
            <p><code>DashboardMetricsResponse</code> model.</p>
          </div>
        </div>
      </section>
    `;
  }
}