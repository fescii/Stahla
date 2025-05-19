export default class CodeDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0;
    
    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedSubmenu: false,
      expandedCategories: new Set(['overview'])
    };

    this.render();
  }
  
  isCodeCategoryActive(category) {
    const categoryMap = {
      'overview': ['introduction', 'problem-goal', 'approach'],
      'technical': ['technologies', 'features', 'structure'],
      'setup': ['setup', 'documentation']
    };
    
    return categoryMap[category]?.includes(this.state.activeSection) || false;
  }

  connectedCallback() {
    this._setupEventListeners();
  }

  disconnectedCallback() {
    // Clean up event listeners when element is removed
  }

  render() {
    this.renderCount++;
    console.log(`Rendering Code docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      <div class="code-docs">
        <div class="code-docs-content">
          <nav class="code-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="code-docs-main" class="code-docs-main">
            <div id="content-container" class="code-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="code-docs-header">
        <h1>Stahla AI SDR API</h1>
        <p>A comprehensive guide to the backend application designed to automate Sales Development Representative (SDR) tasks for Stahla.</p>
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
          <div class="nav-section ${this.isCodeCategoryActive('overview') ? 'active' : ''} ${this.state.expandedCategories.has('overview') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-category="overview">
              <span class="link-text">Overview</span>
              <span class="expand-icon">${this.state.expandedCategories.has('overview') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'introduction' ? 'active' : ''}" data-section="introduction">Introduction</a>
              <a class="nav-link sub ${this.state.activeSection === 'problem-goal' ? 'active' : ''}" data-section="problem-goal">Problem & Goal</a>
              <a class="nav-link sub ${this.state.activeSection === 'approach' ? 'active' : ''}" data-section="approach">Approach</a>
            </div>
          </div>
          
          <div class="nav-section ${this.isCodeCategoryActive('technical') ? 'active' : ''} ${this.state.expandedCategories.has('technical') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-category="technical">
              <span class="link-text">Technical Details</span>
              <span class="expand-icon">${this.state.expandedCategories.has('technical') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'technologies' ? 'active' : ''}" data-section="technologies">Key Technologies</a>
              <a class="nav-link sub ${this.state.activeSection === 'features' ? 'active' : ''}" data-section="features">Core Features</a>
              <a class="nav-link sub ${this.state.activeSection === 'structure' ? 'active' : ''}" data-section="structure">Project Structure</a>
            </div>
          </div>
          
          <div class="nav-section ${this.isCodeCategoryActive('setup') ? 'active' : ''} ${this.state.expandedCategories.has('setup') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-category="setup">
              <span class="link-text">Setup & Docs</span>
              <span class="expand-icon">${this.state.expandedCategories.has('setup') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'setup' ? 'active' : ''}" data-section="setup">Setup & Running</a>
              <a class="nav-link sub ${this.state.activeSection === 'documentation' ? 'active' : ''}" data-section="documentation">Documentation</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getContentForSection(section) {
    switch (section) {
      case 'introduction':
        return this.getIntroductionContent();
      case 'problem-goal':
        return this.getProblemGoalContent();
      case 'approach':
        return this.getApproachContent();
      case 'technologies':
        return this.getTechnologiesContent();
      case 'features':
        return this.getFeaturesContent();
      case 'structure':
        return this.getStructureContent();
      case 'setup':
        return this.getSetupContent();
      case 'documentation':
        return this.getDocumentationContent();
      default:
        return this.getIntroductionContent();
    }
  }

  _setupEventListeners() {
    this.shadowObj.addEventListener('click', (event) => {
      // Handle nav link clicks
      const navLink = event.target.closest('.nav-link');
      if (navLink) {
        const section = navLink.getAttribute('data-section');
        const category = navLink.getAttribute('data-category');
        
        if (category) {
          this._toggleCategoryExpansion(category);
        } else if (section) {
          this._navigateToSection(section);
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
    
    // Ensure the parent category is expanded when navigating to a subsection
    const categoryMap = {
      'introduction': 'overview',
      'problem-goal': 'overview',
      'approach': 'overview',
      'technologies': 'technical',
      'features': 'technical',
      'structure': 'technical',
      'setup': 'setup',
      'documentation': 'setup'
    };
    
    if (categoryMap[section]) {
      this.state.expandedCategories.add(categoryMap[section]);
    }
    
    // On mobile, collapse the nav after selection
    if (window.innerWidth <= 900) {
      this.state.expandedSubmenu = false;
    }
    
    this.render();
    
    // Scroll to top of content
    const mainElement = this.shadowObj.querySelector('#code-docs-main');
    if (mainElement) {
      mainElement.scrollTop = 0;
    }
  }

  getIntroductionContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Stahla AI SDR API</h2>
        <p>This project implements a FastAPI backend designed to automate Sales Development Representative (SDR) tasks for Stahla, including <strong>real-time price quoting</strong> and providing an <strong>operational dashboard backend</strong>.</p>
        
        <div class="overview-cards">
          <div class="overview-card">
            <div class="card-title">AI Automation</div>
            <div class="card-desc">Automates SDR tasks with AI-powered intake, classification, and pricing</div>
          </div>
          
          <div class="overview-card">
            <div class="card-title">Real-time Quotes</div>
            <div class="card-desc">Generates price quotes in under 500ms (P95)</div>
          </div>
          
          <div class="overview-card">
            <div class="card-title">Dashboard Backend</div>
            <div class="card-desc">Provides operational visibility for monitoring performance</div>
          </div>
          
          <div class="overview-card">
            <div class="card-title">HubSpot Integration</div>
            <div class="card-desc">Seamlessly integrates with HubSpot CRM for lead management</div>
          </div>
          <div class="overview-card">
            <div class="card-title">Maps Matrix</div>
            <div class="card-desc">>Uses Google Maps API for distance calculations and caching</div>
          </div>
          <div class="overview-card">
            <div class="card-title">Dashboard API</div>
            <div class="card-desc">Exposes API endpoints for monitoring system status and performance</div>
          </div>
        </div>
      </div>
    `;
  }

  getProblemGoalContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Problem & Goal</h2>
        
        <div class="problem-statement">
          <h3>The Problem</h3>
          <p>Manual handling of inbound calls, emails, and forms leads to:</p>
          <ul>
            <li>Missed context and information</li>
            <li>Slow response times</li>
            <li>Inconsistent lead routing</li>
            <li><strong>Delays in providing price quotes</strong></li>
          </ul>
          <p>These issues erode customer trust and result in lost revenue.</p>
        </div>
        
        <div class="goal-statement">
          <h3>The Goal</h3>
          <p>Create a reliable, scalable AI-driven intake and quoting flow that:</p>
          <ul>
            <li>Captures complete information</li>
            <li>Classifies opportunities accurately</li>
            <li>Integrates seamlessly with HubSpot</li>
            <li><strong>Generates quotes rapidly (&lt;500ms P95)</strong></li>
            <li>Enables quick human follow-up</li>
            <li>Provides operational visibility</li>
          </ul>
        </div>
        
        <div class="metrics-table">
          <h3>Key Performance Metrics</h3>
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>Target</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>First response time (SDR interaction)</td>
                <td>&lt;15 sec median</td>
              </tr>
              <tr class="highlighted">
                <td>Quote generation latency (<code>/webhook/pricing/quote</code>)</td>
                <td>&lt;500ms P95</td>
              </tr>
              <tr>
                <td>Data-field completeness in HubSpot</td>
                <td>≥95%</td>
              </tr>
              <tr>
                <td>Routing accuracy</td>
                <td>≥90%</td>
              </tr>
              <tr>
                <td>Qualified-lead-to-quote conversion increase</td>
                <td>+20%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  getApproachContent() {
    return /* html */`
      <div class="content-section active">
        <h2>High-Level Approach</h2>
        
        <div class="approach-steps">
          <div class="approach-step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h3>AI Intake Agent</h3>
              <p>Uses voice (Bland.ai), email parsing, and web form follow-ups to greet prospects, ask dynamic questions, and populate HubSpot.</p>
            </div>
          </div>
          
          <div class="approach-step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h3>Classification & Routing</h3>
              <p>Determines the appropriate business unit (Services, Logistics, Leads, or Disqualify) based on lead data and assigns the deal in HubSpot.</p>
            </div>
          </div>
          
          <div class="approach-step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h3>Real-time Pricing Agent</h3>
              <p>Provides instant price quotes via a secure webhook, using dynamically synced pricing rules from Google Sheets and cached Google Maps distance calculations.</p>
            </div>
          </div>
          
          <div class="approach-step">
            <div class="step-number">4</div>
            <div class="step-content">
              <h3>Human Handoff</h3>
              <p>Provides reps with summaries, context, and quotes for quick follow-up or disqualification.</p>
            </div>
          </div>
          
          <div class="approach-step">
            <div class="step-number">5</div>
            <div class="step-content">
              <h3>Operational Dashboard Backend</h3>
              <p>Exposes API endpoints for monitoring system status, cache performance, sync status, errors, recent requests, and limited cache/sync management.</p>
            </div>
          </div>
          
          <div class="approach-step">
            <div class="step-number">6</div>
            <div class="step-content">
              <h3>Extensible Framework</h3>
              <p>Built for future agent additions.</p>
            </div>
          </div>
          
          <div class="approach-step">
            <div class="step-number">7</div>
            <div class="step-content">
              <h3>Integration Layer</h3>
              <p>Uses n8n for managing specific webhook workflows (e.g., lead processing trigger).</p>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getTechnologiesContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Key Technologies</h2>
        
        <div class="tech-grid">
          <div class="tech-card">
            <div class="tech-icon">🔧</div>
            <div class="tech-name">Backend Framework</div>
            <div class="tech-value">FastAPI</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">📊</div>
            <div class="tech-name">CRM</div>
            <div class="tech-value">HubSpot</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">🗣️</div>
            <div class="tech-name">Voice AI</div>
            <div class="tech-value">Bland.ai</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">🧠</div>
            <div class="tech-name">Language Model</div>
            <div class="tech-value">Marvin AI (configurable)</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">⚙️</div>
            <div class="tech-name">Workflow Automation</div>
            <div class="tech-value">n8n</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">✓</div>
            <div class="tech-name">Data Validation</div>
            <div class="tech-value">Pydantic</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">💾</div>
            <div class="tech-name">Caching</div>
            <div class="tech-value">Redis</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">🗺️</div>
            <div class="tech-name">Geo-Services</div>
            <div class="tech-value">Google Maps API</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">📝</div>
            <div class="tech-name">Data Source (Pricing)</div>
            <div class="tech-value">Google Sheets API</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">📝</div>
            <div class="tech-name">Logging</div>
            <div class="tech-value">Logfire</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">🐳</div>
            <div class="tech-name">Containerization</div>
            <div class="tech-value">Docker, Docker Compose</div>
          </div>
          
          <div class="tech-card">
            <div class="tech-icon">🐍</div>
            <div class="tech-name">Language</div>
            <div class="tech-value">Python 3.11+</div>
          </div>
        </div>
      </div>
    `;
  }

  getFeaturesContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Core Features (v1 + Pricing)</h2>
        
        <div class="features-list">
          <div class="feature-item">
            <h3>Voice AI Intake Agent (Bland.ai)</h3>
            <p>Answers inbound calls and initiates callbacks for incomplete web forms within 1 minute.</p>
          </div>
          
          <div class="feature-item">
            <h3>Web Form & Email Intake</h3>
            <p>Processes submissions/emails via webhooks, using dynamic questioning and LLM parsing for emails.</p>
          </div>
          
          <div class="feature-item">
            <h3>Automated Follow-up</h3>
            <p>Initiates Bland.ai calls for missing web form data and sends auto-reply emails for incomplete email leads.</p>
          </div>
          
          <div class="feature-item">
            <h3>HubSpot Data Enrichment</h3>
            <p>Creates/updates Contacts & Deals with high completeness. Writes call summaries/recordings to HubSpot.</p>
          </div>
          
          <div class="feature-item">
            <h3>Classification & Routing Engine</h3>
            <p>Classifies leads (Services/Logistics/Leads/Disqualify) and routes deals to the correct HubSpot pipeline with round-robin owner assignment.</p>
          </div>
          
          <div class="feature-item highlight">
            <h3>Real-time Pricing Agent</h3>
            <ul>
              <li><code>/webhook/pricing/quote</code> endpoint for instant quote generation (secured by API Key).</li>
              <li><code>/webhook/pricing/location_lookup</code> endpoint for asynchronous distance calculation/caching.</li>
              <li>Dynamic sync of pricing rules, config, and branches from Google Sheets to Redis cache.</li>
              <li>Calculates quotes based on trailer type, duration, usage, extras, delivery distance (nearest branch), and seasonal multipliers.</li>
            </ul>
          </div>
          
          <div class="feature-item">
            <h3>Operational Dashboard Backend API</h3>
            <ul>
              <li>Endpoints (<code>/dashboard/...</code>) for monitoring status (requests, errors, cache, sync) and recent activity.</li>
              <li>Endpoints for managing cache (view/clear specific keys, clear pricing/maps cache) and triggering manual sheet sync.</li>
            </ul>
          </div>
          
          <div class="feature-item">
            <h3>Human-in-the-Loop Handoff</h3>
            <p>Sends email notifications to reps with summaries, checklists, and action links.</p>
          </div>
          
          <div class="feature-item">
            <h3>Configuration & Monitoring</h3>
            <p>Via <code>.env</code>, Pydantic settings, health check endpoints, and background logging to Redis for dashboard.</p>
          </div>
          
          <div class="feature-item">
            <h3>Logging</h3>
            <p>Structured logging via Logfire.</p>
          </div>
          
          <div class="feature-item">
            <h3>Workflow Integration</h3>
            <p>Connects with n8n for specific automation tasks.</p>
          </div>
        </div>
        
        <p class="note"><em>(See <code>docs/features.md</code> for more details)</em></p>
      </div>
    `;
  }

  getStructureContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Project Structure</h2>
        
        <div class="code-block">
<pre>
.
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── classify.py
│   │           ├── health.py
│   │           ├── hubspot.py
│   │           ├── documentation.py
│   │           ├── dash/
│   │           │   └── dashboard.py
│   │           └── webhooks/
│   │               ├── form.py
│   │               ├── helpers.py
│   │               ├── hubspot.py
│   │               ├── voice.py
│   │               └── pricing.py
│   ├── assets/
│   │   ├── call.json
│   │   ├── data.json
│   │   ├── edges.json
│   │   ├── knowledge.json
│   │   ├── location.json
│   │   ├── quote.json
│   │   └── script.md
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── middleware.py
│   │   ├── security.py
│   │   └── templating.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── bland.py
│   │   ├── blandlog.py
│   │   ├── classification.py
│   │   ├── common.py
│   │   ├── email.py
│   │   ├── error.py
│   │   ├── hubspot.py
│   │   ├── location.py
│   │   ├── pricing.py
│   │   ├── quote.py
│   │   ├── user.py
│   │   ├── webhook.py
│   │   └── dash/
│   │       ├── __init__.py
│   │       └── dashboard.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   ├── classify/
│   │   │   ├── __init__.py
│   │   │   ├── classification.py
│   │   │   ├── marvin.py
│   │   │   └── rules.py
│   │   ├── dash/
│   │   │   ├── __init__.py
│   │   │   ├── background.py
│   │   │   └── dashboard.py
│   │   ├── location/
│   │   │   ├── __init__.py
│   │   │   └── location.py
│   │   ├── mongo/
│   │   ├── quote/
│   │   │   ├── __init__.py
│   │   │   ├── quote.py
│   │   │   └── sync.py
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   └── redis.py
│   │   ├── bland.py
│   │   ├── email.py
│   │   ├── hubspot.py
│   │   └── n8n.py
│   ├── static/
│   ├── templates/
│   │   └── home.html
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── enhanced.py
│   │   └── location.py
│   ├── __init__.py
│   ├── gcp.json
│   └── main.py
├── docs/
│   ├── api.md
│   ├── faq.md
│   ├── features.md
│   ├── hubspot.md
│   ├── marvin.md
│   ├── services.md
│   └── webhooks.md
├── rest/
├── sheets/
├── tests/
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
</pre>
        </div>
        
        <div class="structure-highlight">
          <h3>Key Components</h3>
          <ul>
            <li><strong>api/endpoints/webhooks/pricing.py</strong> - Pricing webhook implementation</li>
            <li><strong>services/quote/</strong> - Real-time pricing logic</li>
            <li><strong>services/location/</strong> - Google Maps distance calculation</li>
            <li><strong>services/dash/</strong> - Dashboard backend</li>
            <li><strong>models/pricing.py</strong> - Data models for pricing</li>
            <li><strong>models/quote.py</strong> - Data models for quotes</li>
          </ul>
        </div>
      </div>
    `;
  }

  getSetupContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Setup & Running</h2>
        
        <div class="setup-steps">
          <div class="setup-step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h3>Clone the repository</h3>
              <div class="code-snippet">git clone <a href="https://github.com/your-repo.git">https://github.com/your-repo.git</a></div>
            </div>
          </div>
          
          <div class="setup-step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h3>Create and configure .env</h3>
              <ul>
                <li>Copy <code>.env.example</code> to <code>.env</code>.</li>
                <li>Fill in API keys: <code>HUBSPOT_API_KEY</code>, <code>BLAND_API_KEY</code>, <code>LOGFIRE_TOKEN</code>, <code>GOOGLE_MAPS_API_KEY</code>, <code>PRICING_WEBHOOK_API_KEY</code>, and your chosen <code>LLM_PROVIDER</code>'s key.</li>
                <li>Configure <code>GOOGLE_SHEET_ID</code> and the <code>GOOGLE_SHEET_*_RANGE</code> variables for products, generators, branches, and config tabs/ranges.</li>
                <li>Set up <code>GOOGLE_APPLICATION_CREDENTIALS</code> if using Google Service Account auth.</li>
                <li>Configure <code>REDIS_URL</code>.</li>
                <li>Configure <code>APP_BASE_URL</code>.</li>
                <li>Configure n8n settings if <code>N8N_ENABLED=true</code>.</li>
                <li>Adjust other settings as needed.</li>
              </ul>
            </div>
          </div>
          
          <div class="setup-step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h3>Install dependencies</h3>
              <div class="code-snippet">pip install -r requirements.txt</div>
            </div>
          </div>
          
          <div class="setup-step">
            <div class="step-number">4</div>
            <div class="step-content">
              <h3>Run locally using Uvicorn</h3>
              <div class="code-snippet">uvicorn app.main:app --reload --port 8000</div>
            </div>
          </div>
          
          <div class="setup-step">
            <div class="step-number">5</div>
            <div class="step-content">
              <h3>Run using Docker Compose</h3>
              <div class="code-snippet">docker-compose up --build</div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getDocumentationContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Documentation and API</h2>
        
        <p>Comprehensive documentation is available to understand the Stahla AI SDR application's architecture, features, and API.</p>
        
        <div class="docs-section">
          <h3>Detailed Guides</h3>
          <p>For in-depth information on specific aspects, please refer to the following documents in the <code>docs/</code> directory:</p>
          
          <div class="docs-grid">
            <div class="doc-card">
              <div class="doc-title"><code>api.md</code></div>
              <div class="doc-desc">Detailed specifications for all API endpoints.</div>
            </div>
            
            <div class="doc-card">
              <div class="doc-title"><code>features.md</code></div>
              <div class="doc-desc">A comprehensive list and description of core application features.</div>
            </div>
            
            <div class="doc-card">
              <div class="doc-title"><code>webhooks.md</code></div>
              <div class="doc-desc">In-depth explanation of webhook functionalities, including models, logic, and examples.</div>
            </div>
            
            <div class="doc-card">
              <div class="doc-title"><code>hubspot.md</code></div>
              <div class="doc-desc">HubSpot integration details, including custom Contact and Deal properties.</div>
            </div>
            
            <div class="doc-card">
              <div class="doc-title"><code>services.md</code></div>
              <div class="doc-desc">Overview of core services like Bland.ai, Google Sheets, Redis, etc.</div>
            </div>
            
            <div class="doc-card">
              <div class="doc-title"><code>marvin.md</code></div>
              <div class="doc-desc">Integration with Marvin AI for classification and data extraction.</div>
            </div>
            
            <div class="doc-card">
              <div class="doc-title"><code>faq.md</code></div>
              <div class="doc-desc">Frequently Asked Questions.</div>
            </div>
          </div>
        </div>
        
        <div class="docs-section">
          <h3>Live API Documentation</h3>
          <p>Once the application is running:</p>
          <ul>
            <li>Interactive API documentation (Swagger UI) is available at <code>/docs</code> on the application server.</li>
            <li>Alternative API documentation (ReDoc) is available at <code>/redoc</code> on the application server.</li>
            <li>The markdown documentation files from the <code>docs/</code> directory (e.g., <code>features.md</code>, <code>webhooks.md</code>) are also served as rendered HTML at <code>/api/v1/docs/{filename}</code> (e.g., <code>/api/v1/docs/webhooks.md</code>).</li>
          </ul>
        </div>
        
        <div class="future-section">
          <h3>Future Considerations (Post-v1)</h3>
          <ul>
            <li>SMS intake channel (e.g., via Twilio).</li>
            <li>Frontend UI for the Operational Dashboard.</li>
            <li>Integration with external monitoring/alerting systems for advanced metrics (latency P95, cache hit ratios, historical trends) and alerts.</li>
            <li>Refinement of HubSpot dynamic ID fetching and call data persistence.</li>
            <li>Dedicated Integration & Orchestration Layer (e.g., self-hosted n8n).</li>
          </ul>
        </div>
      </div>
    `;
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
        
        .code-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .code-docs-header {
          padding: 0;
        }
        
        .code-docs-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .code-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .code-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .code-docs-sidebar {
          width: 260px;
          position: sticky;
          top: 20px;
          height: 100vh;
          padding-right: 10px;
          overflow-y: auto;
          position: sticky;
          overflow: auto;
          -ms-overflow-style: none; /* IE 11 */
          scrollbar-width: none; /* Firefox 64 */
        }

        .code-docs-sidebar::-webkit-scrollbar {
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
        
        .mobile-toggle button {
          background: none;
          border: none;
          color: var(--text-color);
          cursor: pointer;
          padding: 5px;
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.9rem;
          font-weight: 600;
        }
        
        .expand-icon {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 16px;
          height: 16px;
          font-size: 14px;
          font-weight: 600;
          margin-left: 8px;
        }
        
        .link-text {
          flex: 1;
        }
        
        .code-docs-main {
          flex: 1;
          padding: 20px 0;
          min-width: 0;
        }
        
        .code-content-container {
          padding: 0;
        }
        
        .content-section {
          display: none;
          padding: 0;
          min-height: 100vh;
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
          font-size: 1.3rem;
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
        
        /* Overview cards */
        .overview-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 20px;
          margin: 30px 0;
        }
        
        .overview-card {
          background-color: var(--stat-background);
          border-radius: 8px;
          padding: 10px;
          transition: all 0.2s ease;
          display: flex;
          flex-direction: column;
        }
        
        .overview-card:hover {
          transform: translateY(-3px);
        }
        
        .card-icon {
          font-size: 2rem;
          margin-bottom: 15px;
        }
        
        .card-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 10px;
          font-size: 1.1rem;
        }
        
        .card-desc {
          color: var(--text-color);
          font-size: 0.9rem;
        }
        
        /* Problem & Goal section */
        .problem-statement, .goal-statement {
          margin-bottom: 30px;
        }
        
        .metrics-table {
          margin: 30px 0;
        }
        
        .metrics-table table {
          width: 100%;
          border-collapse: collapse;
          margin: 20px 0;
          font-size: 0.9rem;
        }
        
        .metrics-table th {
          background-color: var(--stat-background);
          padding: 12px 15px;
          text-align: left;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .metrics-table td {
          padding: 10px 15px;
          border-bottom: var(--border);
        }
        
        .metrics-table tr:last-child td {
          border-bottom: none;
        }
        
        .metrics-table tr.highlighted {
          background-color: var(--tab-background);
          font-weight: 500;
        }
        
        /* Approach steps */
        .approach-steps {
          margin: 30px 0;
        }
        
        .approach-step {
          display: flex;
          margin-bottom: 25px;
          position: relative;
        }
        
        .approach-step:last-child {
          margin-bottom: 0;
        }
        
        .step-number {
          width: 36px;
          height: 36px;
          background-color: var(--tab-background);
          color: var(--accent-color);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
          margin-right: 15px;
          flex-shrink: 0;
        }
        
        .step-content {
          flex: 1;
        }
        
        .step-content h3 {
          margin: 0 0 10px;
          font-size: 1.1rem;
        }
        
        .step-content p {
          margin: 0;
          font-size: 0.95rem;
        }
        
        /* Technologies grid */
        .tech-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 20px;
          margin: 30px 0;
        }
        
        .tech-card {
          background-color: var(--stat-background);
          border-radius: 8px;
          padding: 10px;
          transition: all 0.2s ease;
        }
        
        .tech-card:hover {
          transform: translateY(-3px);
        }
        
        .tech-icon {
          font-size: 1.5rem;
          margin-bottom: 10px;
        }
        
        .tech-name {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.95rem;
        }
        
        .tech-value {
          color: var(--accent-color);
          font-size: 0.9rem;
          font-weight: 500;
        }
        
        /* Features list */
        .features-list {
          margin: 30px 0;
        }
        
        .feature-item {
          margin-bottom: 25px;
          padding: 0;
        }
        
        .feature-item:last-child {
          margin-bottom: 0;
          padding-bottom: 0;
          border-bottom: none;
        }
        
        .feature-item h3 {
          margin: 0 0 10px;
          font-size: 1.1rem;
        }
        
        .feature-item p {
          margin: 0;
          font-size: 0.95rem;
        }
        
        .feature-item.highlight {
          background-color: var(--stat-background);
          padding: 10px 12px;
          border-radius: 8px;
        }
        
        .note {
          font-size: 0.9rem;
          color: var(--gray-color);
          margin-top: 30px;
        }
        
        /* Project structure */
        .code-block {
          background-color: var(--stat-background);
          border-radius: 8px;
          padding: 20px;
          margin: 25px 0;
          overflow-x: auto;
        }
        
        .code-block pre {
          margin: 0;
          font-family: var(--font-mono);
          font-size: 0.85rem;
          line-height: 1.5;
        }
        
        .structure-highlight {
          margin: 30px 0;
        }
        
        /* Setup steps */
        .setup-steps {
          margin: 30px 0;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .setup-steps > .setup-step {
          display: flex;
          flex-flow: row;
          gap: 3px;
        }
        
        .code-snippet {
          background-color: var(--stat-background);
          padding: 12px 15px;
          border-radius: 6px;
          font-family: var(--font-mono);
          font-size: 0.85rem;
          color: var(--text-color);
          margin: 10px 0;
          overflow-x: auto;
        }
        
        /* Documentation section */
        .docs-section {
          margin-bottom: 40px;
        }
        
        .docs-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 20px;
          margin: 25px 0;
        }
        
        .doc-card {
          background-color: var(--gray-background);
          border-radius: 8px;
          padding: 15px;
          border: var(--border);
          transition: all 0.2s ease;
        }
        
        .doc-card:hover {
          transform: translateY(-3px);
        }
        
        .doc-icon {
          font-size: 1.5rem;
          margin-bottom: 10px;
        }
        
        .doc-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.95rem;
        }
        
        .doc-desc {
          color: var(--text-color);
          font-size: 0.9rem;
        }
        
        .future-section {
          margin-top: 40px;
          padding-top: 20px;
          border-top: var(--border);
        }
        
        /* Mobile styles */
        @media (max-width: 900px) {
          .code-docs-content {
            flex-direction: column;
          }
          
          .code-docs-sidebar {
            width: 100%;
            position: relative;
            top: 0;
            height: auto;
            overflow: initial;
            margin-bottom: 20px;
          }
          
          .sidebar-content {
            overflow: hidden;
          }
          
          .mobile-toggle {
            display: block;
            padding: 10px 15px;
            border-bottom: var(--border);
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
          
          .overview-cards, .tech-grid, .docs-grid {
            grid-template-columns: 1fr;
          }
          
          .metrics-table {
            overflow-x: auto;
          }
          
          .metrics-table table {
            min-width: 500px;
          }
          
          .code-block {
            padding: 15px 10px;
          }
          
          .code-block pre {
            font-size: 0.75rem;
          }
        }
      </style>
    `;
  }
}