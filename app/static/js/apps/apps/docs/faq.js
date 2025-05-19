export default class FAQDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0;
    
    // Component state
    this.state = {
      activeSection: 'general-questions',
      expandedSubmenu: false,
      expandedCategories: new Set(['general'])
    };

    this.render();
  }
  
  isFaqCategoryActive(category) {
    const categoryMap = {
      'general': ['general-questions', 'technical-questions'],
      'features': ['feature-questions', 'setup-development'],
      'help': ['troubleshooting']
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
    console.log(`Rendering FAQ docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      <div class="faq-docs">
        <div class="faq-docs-content">
          <nav class="faq-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="faq-docs-main" class="faq-docs-main">
            <div id="content-container" class="faq-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="faq-docs-header">
        <h1>Frequently Asked Questions (FAQ) - Stahla AI SDR</h1>
        <p>This FAQ provides answers to common questions about the Stahla AI SDR application.</p>
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
          <div class="nav-section ${this.isFaqCategoryActive('general') ? 'active' : ''} ${this.state.expandedCategories.has('general') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-category="general">
              <span class="link-text">General Information</span>
              <span class="expand-icon">${this.state.expandedCategories.has('general') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'general-questions' ? 'active' : ''}" data-section="general-questions">Overview & Benefits</a>
              <a class="nav-link sub ${this.state.activeSection === 'technical-questions' ? 'active' : ''}" data-section="technical-questions">Technical Details</a>
            </div>
          </div>
          
          <div class="nav-section ${this.isFaqCategoryActive('features') ? 'active' : ''} ${this.state.expandedCategories.has('features') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-category="features">
              <span class="link-text">Features & Components</span>
              <span class="expand-icon">${this.state.expandedCategories.has('features') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'feature-questions' ? 'active' : ''}" data-section="feature-questions">Core Features</a>
              <a class="nav-link sub ${this.state.activeSection === 'setup-development' ? 'active' : ''}" data-section="setup-development">Setup & Development</a>
            </div>
          </div>
          
          <div class="nav-section ${this.isFaqCategoryActive('help') ? 'active' : ''} ${this.state.expandedCategories.has('help') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-category="help">
              <span class="link-text">Help & Support</span>
              <span class="expand-icon">${this.state.expandedCategories.has('help') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'troubleshooting' ? 'active' : ''}" data-section="troubleshooting">Troubleshooting</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getContentForSection(section) {
    switch (section) {
      case 'general-questions':
        return this.getGeneralQuestionsContent();
      case 'technical-questions':
        return this.getTechnicalQuestionsContent();
      case 'feature-questions':
        return this.getFeatureQuestionsContent();
      case 'setup-development':
        return this.getSetupDevelopmentContent();
      case 'troubleshooting':
        return this.getTroubleshootingContent();
      default:
        return this.getGeneralQuestionsContent();
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
      'general-questions': 'general',
      'technical-questions': 'general',
      'feature-questions': 'features',
      'setup-development': 'features',
      'troubleshooting': 'help'
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
    const mainElement = this.shadowObj.querySelector('#faq-docs-main');
    if (mainElement) {
      mainElement.scrollTop = 0;
    }
  }

  getGeneralQuestionsContent() {
    return /* html */`
      <div class="content-section active">
        <h2>General Questions</h2>
        <div class="faq-category">
          <div class="faq-item">
            <div class="faq-question">Q1: What is the Stahla AI SDR application?</div>
            <div class="faq-answer">
              <p>The Stahla AI SDR is a backend application designed to automate Sales Development Representative (SDR) tasks for Stahla. It handles inbound communication (calls, web forms, emails), enriches lead data in HubSpot, classifies and routes leads, provides real-time price quotes, and offers an operational dashboard backend for monitoring.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q2: What are the main problems this application solves?</div>
            <div class="faq-answer">
              <p>It addresses issues like missed context from manual lead handling, slow response times, inconsistent lead routing, and delays in providing price quotes. The goal is to improve efficiency, data accuracy, customer trust, and ultimately, revenue.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q3: What are the key benefits of using this system?</div>
            <div class="faq-answer">
              <ul>
                <li>Faster lead response times (target &lt;15 sec median for SDR interaction).</li>
                <li>Rapid price quote generation (target &lt;500ms P95).</li>
                <li>Improved data completeness in HubSpot (target ≥95%).</li>
                <li>More accurate lead routing (target ≥90%).</li>
                <li>Potential for increased qualified-lead-to-quote conversion (target +20%).</li>
                <li>Streamlined human handoff with comprehensive lead information.</li>
                <li>Operational visibility through a dashboard backend.</li>
              </ul>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q4: Who is the target user for this application?</div>
            <div class="faq-answer">
              <p>The primary users are Stahla's sales and operations teams. The system automates many SDR tasks, allowing sales representatives to focus on qualified leads and closing deals.</p>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getTechnicalQuestionsContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Technical Questions</h2>
        <div class="faq-category">
          <div class="faq-item">
            <div class="faq-question">Q5: What are the main technologies used in this project?</div>
            <div class="faq-answer">
              <div class="faq-tech-grid">
                <div class="tech-item">
                  <div class="tech-name">Backend Framework</div>
                  <div class="tech-desc">FastAPI (Python)</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">CRM Integration</div>
                  <div class="tech-desc">HubSpot API</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Voice AI</div>
                  <div class="tech-desc">Bland.ai</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Language Model</div>
                  <div class="tech-desc">Marvin AI (configurable)</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Workflow Automation</div>
                  <div class="tech-desc">n8n</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Data Validation</div>
                  <div class="tech-desc">Pydantic</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Caching</div>
                  <div class="tech-desc">Redis</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Geo-Services</div>
                  <div class="tech-desc">Google Maps API</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Pricing Data</div>
                  <div class="tech-desc">Google Sheets API</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Logging</div>
                  <div class="tech-desc">Logfire</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Containerization</div>
                  <div class="tech-desc">Docker, Docker Compose</div>
                </div>
                <div class="tech-item">
                  <div class="tech-name">Language</div>
                  <div class="tech-desc">Python 3.11+</div>
                </div>
              </div>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q6: How is the application deployed?</div>
            <div class="faq-answer">
              <p>The application is designed to be containerized using Docker and orchestrated with Docker Compose. It can also be run locally using Uvicorn for development.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q7: How is configuration managed?</div>
            <div class="faq-answer">
              <p>Configuration is managed through <code>.env</code> files and Pydantic settings models (located in <code>app/core/config.py</code>). This includes API keys, database URLs, Google Sheet IDs, and other operational parameters.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q8: How does the system ensure security, especially for API endpoints?</div>
            <div class="faq-answer">
              <p>Specific webhooks, like the pricing quote and location lookup endpoints, are secured using API Key authentication. The application also uses Pydantic for data validation, which helps prevent injection attacks. Further security measures can be implemented as needed (e.g., OAuth2 for dashboard access).</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q9: How is data cached for performance?</div>
            <div class="faq-answer">
              <p>Redis is used for caching. This includes:</p>
              <ul>
                <li>Pricing rules, product catalogs, branch locations, and configuration synced from Google Sheets.</li>
                <li>Google Maps Distance Matrix API results for delivery calculations.</li>
                <li>Data for the operational dashboard (e.g., counters, logs).</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getFeatureQuestionsContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Feature-Specific Questions</h2>
        <div class="faq-category">
          <div class="faq-item">
            <div class="faq-question">Q10: How does the Voice AI (Bland.ai) integration work?</div>
            <div class="faq-answer">
              <p>Bland.ai is used to:</p>
              <ul>
                <li>Answer inbound calls directly.</li>
                <li>Initiate automated callbacks to leads who submitted incomplete web forms, asking dynamic questions to gather missing information.</li>
                <li>Call summaries and recording URLs are logged to HubSpot.</li>
              </ul>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q11: How are web forms and emails processed?</div>
            <div class="faq-answer">
              <ul>
                <li><strong>Web Forms:</strong> Submissions are received via a webhook (<code>/api/v1/webhooks/form</code>). If data is incomplete, an automated Bland.ai call is triggered.</li>
                <li><strong>Emails:</strong> Incoming emails are processed via a webhook (<code>/api/v1/webhooks/email</code>). An LLM (like Marvin AI) is used to parse email content and extract relevant lead data. Automated replies can be sent for incomplete information.</li>
              </ul>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q12: How does the lead classification and routing engine work?</div>
            <div class="faq-answer">
              <p>The engine (located in <code>app/services/classify/</code>) classifies leads into categories like 'Services', 'Logistics', 'Leads', or 'Disqualify'. This can be based on rules or AI (e.g., Marvin). Based on the classification, HubSpot Deals are assigned to the correct pipeline and owner (using round-robin).</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q13: How does the real-time pricing agent work?</div>
            <div class="faq-answer">
              <ul>
                <li>A secure webhook (<code>/api/v1/webhook/pricing/quote</code>) provides instant price quotes.</li>
                <li>It uses pricing rules, trailer types, duration, usage, extras, delivery distance (to the nearest branch), and seasonal multipliers.</li>
                <li>Pricing data and branch locations are dynamically synced from Google Sheets and cached in Redis.</li>
                <li>A separate webhook (<code>/api/v1/webhook/pricing/location_lookup</code>) handles asynchronous calculation and caching of delivery distances using Google Maps to optimize quote speed.</li>
              </ul>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q14: What information does the Operational Dashboard API provide?</div>
            <div class="faq-answer">
              <p>The dashboard backend API (endpoints under <code>/api/v1/dashboard/</code>) provides:</p>
              <ul>
                <li><strong>Monitoring data:</strong> Status of quote requests, location lookups, cache performance, external service status, error summaries, and recent request logs.</li>
                <li><strong>Management functions:</strong> Manual triggering of Google Sheet sync, and tools to view/clear specific cache keys.</li>
              </ul>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q15: How are HubSpot custom properties managed?</div>
            <div class="faq-answer">
              <p>The system is designed to create/update HubSpot Contacts and Deals, populating a defined set of custom properties. Details of these properties (e.g., for lead type, product interest, budget, location details, pricing components) are documented in <code>/docs/hubspot</code>.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q16: What kind of webhooks does the application expose and consume?</div>
            <div class="faq-answer">
              <h4>Exposed (Incoming):</h4>
              <table class="webhook-table">
                <thead>
                  <tr>
                    <th>Endpoint</th>
                    <th>Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td class="webhook-path">/api/v1/webhooks/form</td>
                    <td class="webhook-desc">For web form submissions</td>
                  </tr>
                  <tr>
                    <td class="webhook-path">/api/v1/webhooks/hubspot</td>
                    <td class="webhook-desc">For events from HubSpot (e.g., deal updates)</td>
                  </tr>
                  <tr>
                    <td class="webhook-path">/api/v1/webhooks/voice</td>
                    <td class="webhook-desc">For events from Bland.ai (e.g., call completion, transcripts)</td>
                  </tr>
                  <tr>
                    <td class="webhook-path">/api/v1/webhook/pricing/quote</td>
                    <td class="webhook-desc">For synchronous price quote requests</td>
                  </tr>
                  <tr>
                    <td class="webhook-path">/api/v1/webhook/pricing/location_lookup</td>
                    <td class="webhook-desc">For asynchronous location/distance calculations</td>
                  </tr>
                </tbody>
              </table>
              
              <h4>Consumed (Outgoing):</h4>
              <p>The system makes calls to Bland.ai API, HubSpot API, Google Maps API, Google Sheets API, and potentially n8n webhooks.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q17: How is n8n used in the system?</div>
            <div class="faq-answer">
              <p>n8n is used as a workflow automation tool to connect with and manage specific webhook workflows, such as triggering lead processing sequences or other automation tasks that are external to the core application logic.</p>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getSetupDevelopmentContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Setup and Development</h2>
        <div class="faq-category">
          <div class="faq-item">
            <div class="faq-question">Q18: How do I set up the project for development?</div>
            <div class="faq-answer">
              <ol class="setup-steps">
                <li class="setup-step">
                  <div class="step-title">Clone the repository</div>
                  <div class="step-desc">Get the source code onto your local machine.</div>
                </li>
                <li class="setup-step">
                  <div class="step-title">Create environment configuration</div>
                  <div class="step-desc">Create a <code>.env</code> file from <code>.env.example</code> and fill in all required API keys and configuration details (HubSpot, Bland.ai, Logfire, Google Maps, Google Sheets, Redis, etc.).</div>
                </li>
                <li class="setup-step">
                  <div class="step-title">Install dependencies</div>
                  <div class="step-desc">Install Python dependencies using pip:</div>
                  <div class="code-snippet">pip install -r requirements.txt</div>
                </li>
                <li class="setup-step">
                  <div class="step-title">Run the application</div>
                  <div class="step-desc">Run locally using Uvicorn:</div>
                  <div class="code-snippet">uvicorn app.main:app --reload --port 8000</div>
                </li>
              </ol>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q19: How can I run the application using Docker?</div>
            <div class="faq-answer">
              <p>Use Docker Compose to build and run the containerized application:</p>
              <div class="code-snippet">docker-compose up --build</div>
              <p>Ensure your <code>.env</code> file is correctly configured as Docker Compose will use it.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q20: Where can I find API documentation?</div>
            <div class="faq-answer">
              <p>Once the application is running:</p>
              <ul>
                <li>Interactive API documentation: <code>http://localhost:8000/docs</code></li>
                <li>Alternative API documentation (ReDoc): <code>http://localhost:8000/redoc</code></li>
                <li>Detailed endpoint specifications are also in <code>/docs/api</code>.</li>
                <li>Other conceptual documentation (features, webhooks, etc.) is in the <code>/docs</code> directory and some are served via <code>/adocs/{doc}</code>.</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getTroubleshootingContent() {
    return /* html */`
      <div class="content-section active">
        <h2>Troubleshooting & Support</h2>
        <div class="faq-category">
          <div class="faq-item">
            <div class="faq-question">Q21: What should I do if I encounter an error?</div>
            <div class="faq-answer">
              <ol>
                <li>Check the application logs (Logfire, or console output if running locally).</li>
                <li>Verify your <code>.env</code> configuration, especially API keys and service URLs.</li>
                <li>Check the status of external services (HubSpot, Bland.ai, Google Cloud Platform).</li>
                <li>Use the health check endpoints (<code>/health</code>, <code>/ping</code>) to verify basic application responsiveness.</li>
                <li>Consult the operational dashboard API for error summaries if accessible.</li>
              </ol>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q22: How are pricing rules updated?</div>
            <div class="faq-answer">
              <p>Pricing rules, product details, branch locations, and other related configurations are managed in Google Sheets. The application periodically syncs this data into its Redis cache. A manual sync can also be triggered via the dashboard API.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q23: What if HubSpot API limits are reached?</div>
            <div class="faq-answer">
              <p>The application should be designed with HubSpot API limits in mind, using batch operations where possible and efficient data retrieval. If limits are consistently hit, it may require optimizing API call patterns or requesting a limit increase from HubSpot.</p>
            </div>
          </div>
          <div class="faq-item">
            <div class="faq-question">Q24: How can I clear the cache if needed?</div>
            <div class="faq-answer">
              <p>The Operational Dashboard API provides endpoints to view and clear specific cache keys or groups of keys (e.g., all pricing data, all maps data). This can be useful for forcing a refresh of configuration or troubleshooting stale data issues.</p>
            </div>
          </div>
        </div>
        
        <div class="support-grid">
          <div class="support-card">
            <div class="support-title">Documentation</div>
            <div class="support-desc">Access comprehensive documentation in the <code>docs/</code> directory for detailed information on all system components.</div>
          </div>
          <div class="support-card">
            <div class="support-title">Dashboard</div>
            <div class="support-desc">Use the operational dashboard to monitor system health, view logs, and manage cache data.</div>
          </div>
          <div class="support-card">
            <div class="support-title">Health Checks</div>
            <div class="support-desc">Regularly check the <code>/health</code> and <code>/ping</code> endpoints to verify the system is responsive.</div>
          </div>
          <div class="support-card">
            <div class="support-title">Contact Support</div>
            <div class="support-desc">For additional assistance, contact the development team through the support channels specified in the project README.</div>
          </div>
        </div>
        
        <p><em>This FAQ is based on the project documentation as of May 2024. For the most current information, please refer to the main README and other documents in the <code>docs/</code> directory.</em></p>
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
        
        .faq-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .faq-docs-header {
          padding: 0;
        }
        
        .faq-docs-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .faq-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .faq-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .faq-docs-sidebar {
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

        .faq-docs-sidebar::-webkit-scrollbar {
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
          justify-content: space-between;
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
        
        .faq-docs-main {
          flex: 1;
          padding: 20px 0;
          min-width: 0;
        }
        
        .faq-content-container {
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
        
        .content-section ol {
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
        
        /* FAQ specific styling */
        .faq-item {
          margin-bottom: 25px;
          padding-bottom: 15px;
          border-bottom: var(--border);
        }
        
        .faq-item:last-child {
          border-bottom: none;
        }
        
        .faq-question {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 10px;
          font-size: 1.05rem;
        }
        
        .faq-answer {
          color: var(--text-color);
          margin: 0;
        }
        
        .faq-answer ul {
          margin-top: 10px;
          margin-bottom: 10px;
        }
        
        .faq-answer li {
          margin-bottom: 5px;
        }
        
        .faq-category h3 {
          padding-bottom: 10px;
          margin-bottom: 20px;
        }
        
        .faq-tech-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 15px;
          margin: 15px 0;
        }
        
        .tech-item {
          background-color: var(--stat-background);
          padding: 12px 15px;
          border-radius: 6px;
          border: var(--border);
          transition: all 0.2s ease;
        }
        
        .tech-item:hover {
          transform: translateY(-2px);
        }
        
        .tech-name {
          font-weight: 500;
          color: var(--title-color);
          margin-bottom: 5px;
          font-size: 0.95rem;
        }
        
        .tech-desc {
          color: var(--gray-color);
          font-size: 0.85rem;
          margin: 0;
        }
        
        .webhook-table {
          width: 100%;
          border-collapse: collapse;
          margin: 20px 0;
          font-size: 0.9rem;
          border-radius: 8px;
          overflow: hidden;
          table-layout: fixed;
        }
        
        .webhook-table th {
          background-color: var(--stat-background);
          padding: 12px 15px;
          text-align: left;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .webhook-table th:first-child {
          width: 33%;
        }
        
        .webhook-table td {
          padding: 10px 15px;
          border-bottom: var(--border);
        }
        
        .webhook-table tr:last-child td {
          border-bottom: none;
        }
        
        .webhook-table tr:nth-child(even) {
          background-color: var(--stat-background);
        }
        
        .webhook-path {
          font-family: var(--font-mono);
          color: var(--accent-color);
        }
        
        .webhook-desc {
          color: var(--text-color);
        }
        
        .support-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 20px;
          margin: 0 0 25px;
        }
        
        .support-card {
          border-radius: 8px;
          padding: 7px 10px;
          border: var(--border);
          transition: all 0.2s ease;
        }
        
        .support-card:hover {
          transform: translateY(-2px);
        }
        
        .support-icon {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          background-color: var(--tab-background);
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 15px;
          color: var(--accent-color);
          font-size: 1.5rem;
        }
        
        .support-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 10px;
          font-size: 1.1rem;
        }
        
        .support-desc {
          color: var(--text-color);
          font-size: 0.9rem;
          margin: 0;
        }
        
        .content-section ol.setup-steps {
          counter-reset: step-counter;
          list-style: none;
          padding: 0;
          margin: 20px 0;
        }
        
        .setup-step {
          position: relative;
          padding-left: 45px;
          padding-bottom: 30px;
          counter-increment: step-counter;
        }
        
        .setup-step:last-child {
          padding-bottom: 10px;
        }
        
        .setup-step:before {
          content: counter(step-counter);
          position: absolute;
          left: 0;
          top: 0;
          width: 30px;
          height: 30px;
          background-color: var(--tab-background);
          color: var(--accent-color);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 600;
        }
        
        .setup-step:after {
          content: "";
          position: absolute;
          left: 15px;
          top: 30px;
          bottom: 0;
          width: 1px;
          background-color: var(--border-color);
        }
        
        .setup-step:last-child:after {
          display: none;
        }
        
        .step-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 10px;
          font-size: 1.05rem;
        }
        
        .step-desc {
          color: var(--text-color);
          margin: 0;
        }
        
        .code-snippet {
          background-color: var(--stat-background);
          padding: 15px;
          border-radius: 6px;
          font-family: var(--font-mono);
          font-size: 0.85rem;
          color: var(--text-color);
          margin: 15px 0;
          overflow-x: auto;
        }
        
        /* Mobile styles */
        @media (max-width: 900px) {
          .faq-docs-content {
            flex-direction: column;
          }
          
          .faq-docs-sidebar {
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
          
          .faq-tech-grid {
            grid-template-columns: 1fr;
          }
          
          .support-grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
    `;
  }
}