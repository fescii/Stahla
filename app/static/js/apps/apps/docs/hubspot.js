export default class HubspotDocs extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.renderCount = 0;

    // Component state
    this.state = {
      activeSection: 'introduction',
      expandedCategories: new Set(['properties'])
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
    console.log(`Rendering HubSpot docs (${this.renderCount} times)`);
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      <div class="hubspot-docs">
        <div class="hubspot-docs-content">
          <nav class="hubspot-docs-sidebar">
            ${this.getSidebar()}
          </nav>
          <main id="hubspot-docs-main" class="hubspot-docs-main">
            <div id="content-container" class="hubspot-content-container">
              ${this.getContentForSection(this.state.activeSection)}
            </div>
          </main>
        </div>
      </div>
    `;
  }

  getHeader() {
    return /* html */ `
      <header class="hubspot-docs-header">
        <h1>HubSpot Integration & Custom Properties</h1>
        <p>A comprehensive guide to HubSpot integration and custom properties used within the Stahla AI SDR application</p>
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
          <div class="nav-section ${this.isPropertiesActive() ? 'active' : ''} ${this.state.expandedCategories.has('properties') ? 'expanded' : 'collapsed'}">
            <a class="nav-link parent" data-section="properties" data-category="properties">
              <span class="link-text">Property Categories</span>
              <span class="expand-icon">${this.state.expandedCategories.has('properties') ? '−' : '+'}</span>
            </a>
            <div class="subnav">
              <a class="nav-link sub ${this.state.activeSection === 'contact' ? 'active' : ''}" data-section="contact">Contact Information</a>
              <a class="nav-link sub ${this.state.activeSection === 'service' ? 'active' : ''}" data-section="service">Service/Product</a>
              <a class="nav-link sub ${this.state.activeSection === 'event' ? 'active' : ''}" data-section="event">Event/Job Details</a>
              <a class="nav-link sub ${this.state.activeSection === 'site' ? 'active' : ''}" data-section="site">Site Logistics</a>
              <a class="nav-link sub ${this.state.activeSection === 'ai' ? 'active' : ''}" data-section="ai">AI Interaction Data</a>
              <a class="nav-link sub ${this.state.activeSection === 'lead' ? 'active' : ''}" data-section="lead">Qualification & Routing</a>
              <a class="nav-link sub ${this.state.activeSection === 'consent' ? 'active' : ''}" data-section="consent">Consent & Preferences</a>
              <a class="nav-link sub ${this.state.activeSection === 'dropdown' ? 'active' : ''}" data-section="dropdown">Dropdown & Checkbox</a>
            </div>
          </div>
          <div class="nav-section ${this.state.activeSection === 'implementation' ? 'active' : ''}">
            <a class="nav-link" data-section="implementation">Implementation Notes</a>
          </div>
        </div>
      </div>
    `;
  }

  isPropertiesActive() {
    const propertiesSections = ['properties', 'contact', 'service', 'event', 'site', 'ai', 'lead', 'consent', 'dropdown'];
    return propertiesSections.includes(this.state.activeSection);
  }

  getContentForSection(section) {
    switch (section) {
      case 'introduction':
        return this.getIntroductionSection();
      case 'properties':
        return this.getPropertiesSection();
      case 'contact':
        return this.getContactSection();
      case 'service':
        return this.getServiceSection();
      case 'event':
        return this.getEventSection();
      case 'site':
        return this.getSiteSection();
      case 'ai':
        return this.getAISection();
      case 'lead':
        return this.getLeadSection();
      case 'consent':
        return this.getConsentSection();
      case 'dropdown':
        return this.getDropdownSection();
      case 'implementation':
        return this.getImplementationSection();
      default:
        return this.getIntroductionSection();
    }
  }

  getIntroductionSection() {
    return /* html */ `
      <section id="introduction" class="content-section ${this.state.activeSection === 'introduction' ? 'active' : ''}">
        ${this.getHeader()}
        <p>HubSpot integration is a core component of the Stahla AI SDR application, allowing for seamless data flow between the AI system and the customer relationship management (CRM) platform.</p>
        
        <h3>Custom Properties Overview</h3>
        <p>Custom properties in HubSpot allow us to store specialized data collected by the AI SDR system. These properties are organized into logical categories and are essential for maintaining comprehensive lead records and enabling intelligent routing and follow-up.</p>
        
        <div class="table-responsive">
          <table class="property-table overview-table">
            <thead>
              <tr>
                <th>Category</th>
                <th>Purpose</th>
                <th>Properties Count</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><a href="#" data-section="contact" class="category-link">Contact Information</a></td>
                <td>Basic and extended contact details</td>
                <td>5</td>
              </tr>
              <tr>
                <td><a href="#" data-section="service" class="category-link">Service Requirements</a></td>
                <td>Specifications about requested services</td>
                <td>5</td>
              </tr>
              <tr>
                <td><a href="#" data-section="event" class="category-link">Event/Job Details</a></td>
                <td>Event information and timelines</td>
                <td>5</td>
              </tr>
              <tr>
                <td><a href="#" data-section="ai" class="category-link">AI Interaction Data</a></td>
                <td>Conversation and classification data</td>
                <td>5</td>
              </tr>
            </tbody>
          </table>
        </div>
        
        <div class="property-overview">
          <div class="property-card">
            <h4>Contact Information</h4>
            <p>Basic and extended contact details for leads and customers.</p>
          </div>
          <div class="property-card">
            <h4>Service Requirements</h4>
            <p>Detailed specifications about the products and services requested.</p>
          </div>
          <div class="property-card">
            <h4>AI Interaction Data</h4>
            <p>Information about AI conversations, classifications, and routing decisions.</p>
          </div>
          <div class="property-card">
            <h4>Lead Qualification</h4>
            <p>Qualification criteria and scoring to determine lead quality and routing.</p>
          </div>
        </div>
      </section>
    `;
  }

  getPropertiesSection() {
    return /* html */ `
      <section id="properties" class="content-section ${this.state.activeSection === 'properties' ? 'active' : ''}">
        <h2>HubSpot Custom Property Categories</h2>
        <p>The Stahla AI SDR application uses a comprehensive set of custom properties in HubSpot to store and manage lead data. These properties are organized into logical categories for better management and usability.</p>
        
        <p>Navigate to individual property categories using the sidebar or select from the options below:</p>
        
        <div class="properties-grid">
          <div class="property-item" data-property="contact">
            <h3>Contact Information</h3>
            <p>Basic and extended contact details for leads and customers.</p>
          </div>
          <div class="property-item" data-property="service">
            <h3>Service/Product</h3>
            <p>Details about requested services, products, and specifications.</p>
          </div>
          <div class="property-item" data-property="event">
            <h3>Event/Job Details</h3>
            <p>Information about specific events, job requirements, and timelines.</p>
          </div>
          <div class="property-item" data-property="site">
            <h3>Site Logistics</h3>
            <p>Location, access, and other site-specific information.</p>
          </div>
          <div class="property-item" data-property="ai">
            <h3>AI Interaction Data</h3>
            <p>Conversation data, classifications, and AI processing information.</p>
          </div>
          <div class="property-item" data-property="lead">
            <h3>Qualification & Routing</h3>
            <p>Qualification criteria, scores, and routing information.</p>
          </div>
          <div class="property-item" data-property="consent">
            <h3>Consent & Preferences</h3>
            <p>Communication preferences, consent records, and opt-in statuses.</p>
          </div>
          <div class="property-item" data-property="dropdown">
            <h3>Dropdown & Checkbox</h3>
            <p>Standard values for dropdown fields and checkbox options.</p>
          </div>
        </div>
      </section>
    `;
  }

  getContactSection() {
    return /* html */ `
      <section id="contact" class="content-section ${this.state.activeSection === 'contact' ? 'active' : ''}">
        <h2>Contact Information Properties</h2>
        <p>These properties store basic and extended contact information for leads and customers.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">email</td>
                <td class="property-type">Single line text</td>
                <td class="property-description">Email</td>
              </tr>
              <tr>
                <td class="property-name">firstname</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">First name</td>
              </tr>
              <tr>
                <td class="property-name">lastname</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">Last name</td>
              </tr>
              <tr>
                <td class="property-name">phone</td>
                <td class="property-type">Phone number</td>
                <td class="property-description">Phone number</td>
              </tr>
              <tr>
                <td class="property-name">message</td>
                <td class="property-type">Multi-line text</td>
                <td class="property-description">Message</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getServiceSection() {
    return /* html */ `
      <section id="service" class="content-section ${this.state.activeSection === 'service' ? 'active' : ''}">
        <h2>Service/Product Requirements Properties</h2>
        <p>These properties capture detailed information about the products and services requested by the lead.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">what_service_do_you_need_</td>
                <td class="property-type">Multiple checkboxes</td>
                <td class="property-description">What services do you need?</td>
              </tr>
              <tr>
                <td class="property-name">how_many_restroom_stalls_</td>
                <td class="property-type">Number</td>
                <td class="property-description">How Many Restroom Stalls?</td>
              </tr>
              <tr>
                <td class="property-name">how_many_shower_stalls_</td>
                <td class="property-type">Number</td>
                <td class="property-description">How Many Shower Stalls?</td>
              </tr>
              <tr>
                <td class="property-name">how_many_laundry_units_</td>
                <td class="property-type">Number</td>
                <td class="property-description">How many laundry Units?</td>
              </tr>
              <tr>
                <td class="property-name">how_many_portable_toilet_stalls_</td>
                <td class="property-type">Number</td>
                <td class="property-description">How Many Portable Toilet Stalls?</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getEventSection() {
    return /* html */ `
      <section id="event" class="content-section ${this.state.activeSection === 'event' ? 'active' : ''}">
        <h2>Event/Job Details Properties</h2>
        <p>These properties store information about specific events, job requirements, and timelines.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">event_start_date</td>
                <td class="property-type">Date Picker</td>
                <td class="property-description">Event start date</td>
              </tr>
              <tr>
                <td class="property-name">event_end_date</td>
                <td class="property-type">Date Picker</td>
                <td class="property-description">Event end date</td>
              </tr>
              <tr>
                <td class="property-name">event_duration_days</td>
                <td class="property-type">Number (integer)</td>
                <td class="property-description">Number of days the prospect needs the units</td>
              </tr>
              <tr>
                <td class="property-name">rental_start_date</td>
                <td class="property-type">Date picker</td>
                <td class="property-description">When the unit(s) will be needed on site</td>
              </tr>
              <tr>
                <td class="property-name">rental_end_date</td>
                <td class="property-type">Date picker</td>
                <td class="property-description">Expected end date or pickup date for the rental</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getSiteSection() {
    return /* html */ `
      <section id="site" class="content-section ${this.state.activeSection === 'site' ? 'active' : ''}">
        <h2>Site Logistics Properties</h2>
        <p>These properties capture location, access, and other site-specific information.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">event_or_job_address</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">Event or Job Address</td>
              </tr>
              <tr>
                <td class="property-name">site_obstacles</td>
                <td class="property-type">Multi-line text</td>
                <td class="property-description">Notes on access limitations or obstacles at the site</td>
              </tr>
              <tr>
                <td class="property-name">onsite_contact_name</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">Alternate on-site contact name for coordination</td>
              </tr>
              <tr>
                <td class="property-name">site_working_hours</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">Working hours or access times at the site</td>
              </tr>
              <tr>
                <td class="property-name">site_ground_type</td>
                <td class="property-type">Dropdown (select)</td>
                <td class="property-description">Ground/terrain at the drop-off location</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getAISection() {
    return /* html */ `
      <section id="ai" class="content-section ${this.state.activeSection === 'ai' ? 'active' : ''}">
        <h2>AI Interaction Data Properties</h2>
        <p>These properties store information about AI conversations, classifications, and routing decisions.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">call_recording_url</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">URL link to the recorded call</td>
              </tr>
              <tr>
                <td class="property-name">call_summary</td>
                <td class="property-type">Multi-line text</td>
                <td class="property-description">AI-generated summary of what was discussed on the call</td>
              </tr>
              <tr>
                <td class="property-name">ai_call_summary</td>
                <td class="property-type">Multi-line text</td>
                <td class="property-description">Summary of the AI-qualified call details</td>
              </tr>
              <tr>
                <td class="property-name">ai_call_sentiment</td>
                <td class="property-type">Dropdown (select)</td>
                <td class="property-description">Assessment of prospect sentiment/tone</td>
              </tr>
              <tr>
                <td class="property-name">ai_classification_confidence</td>
                <td class="property-type">Number (decimal)</td>
                <td class="property-description">Confidence score (0–1) for the AI's classification</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getLeadSection() {
    return /* html */ `
      <section id="lead" class="content-section ${this.state.activeSection === 'lead' ? 'active' : ''}">
        <h2>Lead Qualification & Routing Properties</h2>
        <p>These properties support qualification criteria, scoring, and routing information for leads.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">project_category</td>
                <td class="property-type">Dropdown (select)</td>
                <td class="property-description">Type of inquiry or project for the lead; used to tailor qualification flow and branching logic</td>
              </tr>
              <tr>
                <td class="property-name">units_needed</td>
                <td class="property-type">Multi-line text</td>
                <td class="property-description">Summary of quantity and type of units required</td>
              </tr>
              <tr>
                <td class="property-name">ai_lead_type</td>
                <td class="property-type">Dropdown (select)</td>
                <td class="property-description">AI‑determined category of the lead</td>
              </tr>
              <tr>
                <td class="property-name">ai_routing_suggestion</td>
                <td class="property-type">Single-line text</td>
                <td class="property-description">Pipeline or stage the AI recommends routing this lead into</td>
              </tr>
              <tr>
                <td class="property-name">ai_qualification_notes</td>
                <td class="property-type">Multi-line text</td>
                <td class="property-description">Key notes from the AI's qualification assessment</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getConsentSection() {
    return /* html */ `
      <section id="consent" class="content-section ${this.state.activeSection === 'consent' ? 'active' : ''}">
        <h2>Consent & Preferences Properties</h2>
        <p>These properties manage communication preferences, consent records, and opt-in statuses.</p>
        
        <div class="table-responsive">
          <table class="property-table">
            <thead>
              <tr>
                <th class="property-name-col">Property Name</th>
                <th class="property-type-col">Type</th>
                <th class="property-desc-col">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td class="property-name">by_submitting_this_form_you_consent_to_receive_texts</td>
                <td class="property-type">Single checkbox</td>
                <td class="property-description">I consent to receive texts on the phone number provided</td>
              </tr>
              <tr>
                <td class="property-name">partner_referral_consent</td>
                <td class="property-type">Single checkbox</td>
                <td class="property-description">Indicates if prospect agreed to share info with partner companies</td>
              </tr>
              <tr>
                <td class="property-name">ada</td>
                <td class="property-type">Single Checkbox</td>
                <td class="property-description">Check this box if you need the Americans with Disabilities Act (ADA) standards for accessibility</td>
              </tr>
              <tr>
                <td class="property-name">ada_required</td>
                <td class="property-type">Single checkbox</td>
                <td class="property-description">Indicates if ADA-compliant (handicap accessible) facilities are needed</td>
              </tr>
              <tr>
                <td class="property-name">weekend_service_needed</td>
                <td class="property-type">Single checkbox</td>
                <td class="property-description">Indicates if service is required over the weekend</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    `;
  }

  getDropdownSection() {
    return /* html */ `
      <section id="dropdown" class="content-section ${this.state.activeSection === 'dropdown' ? 'active' : ''}">
        <div class="hubspot-header">
          <h2>Dropdown & Checkbox Values</h2>
          <p>Standard values used in dropdown fields and checkbox options throughout the HubSpot properties.</p>
        </div>
        
        <div class="dropdown-values-container">
          <!-- Service Types Section -->
          <div class="dropdown-category-card">
            <div class="dropdown-category-header">
              <div class="dropdown-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>
              <div>
                <h3>Service Request Options</h3>
                <p class="category-prop-info">Property: <code>what_service_do_you_need_</code> (Multiple checkboxes)</p>
              </div>
            </div>
            <p class="category-description">Types of service options that clients can select in forms and interactions</p>
            
            <div class="dropdown-values service-values">
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Restroom Trailer</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Restroom Trailer</span>
                  <span class="dropdown-value-usage">High usage</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Shower Trailer</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Shower Trailer</span>
                  <span class="dropdown-value-usage">Medium usage</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Laundry Trailer</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Laundry Trailer</span>
                  <span class="dropdown-value-usage">Medium usage</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Porta Potty</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Porta Potty</span>
                  <span class="dropdown-value-usage">High usage</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Trailer Repair / Pump Out</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Trailer Repair / Pump Out</span>
                  <span class="dropdown-value-usage">Medium usage</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Other</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Other</span>
                  <span class="dropdown-value-usage">Low usage</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Project Category Section -->
          <div class="dropdown-category-card">
            <div class="dropdown-category-header">
              <div class="dropdown-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                </svg>
              </div>
              <div>
                <h3>Project Category Options</h3>
                <p class="category-prop-info">Property: <code>project_category</code> (Dropdown)</p>
              </div>
            </div>
            <p class="category-description">Type of inquiry or project for the lead; used to tailor qualification flow and branching logic</p>
            
            <div class="dropdown-values priority-values">
              <div class="priority-card high-priority">
                <div class="priority-header">
                  <div class="priority-indicator"></div>
                  <h4>Event / Porta Potty</h4>
                </div>
                <div class="priority-details">
                  <div class="priority-timeline">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <span>Event-based service</span>
                  </div>
                  <div class="priority-description">
                    <p>Events requiring portable toilet solutions</p>
                  </div>
                  <div class="priority-code-wrapper">
                    <span class="dropdown-value-code">Event / Porta Potty</span>
                  </div>
                </div>
              </div>
              
              <div class="priority-card medium-priority">
                <div class="priority-header">
                  <div class="priority-indicator"></div>
                  <h4>Construction / Porta Potty</h4>
                </div>
                <div class="priority-details">
                  <div class="priority-timeline">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <span>Construction site service</span>
                  </div>
                  <div class="priority-description">
                    <p>Construction projects requiring porta potty facilities</p>
                  </div>
                  <div class="priority-code-wrapper">
                    <span class="dropdown-value-code">Construction / Porta Potty</span>
                  </div>
                </div>
              </div>
              
              <div class="priority-card low-priority">
                <div class="priority-header">
                  <div class="priority-indicator"></div>
                  <h4>Small Event / Trailer / Local</h4>
                </div>
                <div class="priority-details">
                  <div class="priority-timeline">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <span>Small local event service</span>
                  </div>
                  <div class="priority-description">
                    <p>Local small events requiring trailer facilities</p>
                  </div>
                  <div class="priority-code-wrapper">
                    <span class="dropdown-value-code">Small Event / Trailer / Local</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div class="dropdown-values priority-values additional-options">
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Small Event / Trailer / Not Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Small Event / Trailer / Not Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Large Event / Trailer / Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Large Event / Trailer / Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Large Event / Trailer / Not Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Large Event / Trailer / Not Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Disaster Relief / Trailer / Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Disaster Relief / Trailer / Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Disaster Relief / Trailer / Not Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Disaster Relief / Trailer / Not Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Construction / Company Trailer / Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Construction / Company Trailer / Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Construction / Company Trailer / Not Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Construction / Company Trailer / Not Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Facility / Trailer / Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Facility / Trailer / Local</span>
                </div>
              </div>
              
              <div class="dropdown-value-item">
                <div class="dropdown-item-header">
                  <span class="dropdown-value-label">Facility / Trailer / Not Local</span>
                </div>
                <div class="dropdown-value-meta">
                  <span class="dropdown-value-code">Facility / Trailer / Not Local</span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Quote Urgency Options -->
          <div class="dropdown-category-card">
            <div class="dropdown-category-header">
              <div class="dropdown-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="16" y1="2" x2="16" y2="6"></line>
                  <line x1="8" y1="2" x2="8" y2="6"></line>
                  <line x1="3" y1="10" x2="21" y2="10"></line>
                </svg>
              </div>
              <div>
                <h3>Quote Urgency Options</h3>
                <p class="category-prop-info">Property: <code>quote_urgency</code> (Dropdown)</p>
              </div>
            </div>
            <p class="category-description">Indicates how quickly the prospect wants a quote or follow-up</p>
            
            <div class="timeline-slider">
              <div class="timeline-track">
                <div class="timeline-marker urgent">
                  <div class="timeline-point"></div>
                  <div class="timeline-label">Immediate/Urgent</div>
                  <div class="timeline-sublabel">ASAP</div>
                </div>
                
                <div class="timeline-marker this-week">
                  <div class="timeline-point"></div>
                  <div class="timeline-label">Short-Term</div>
                  <div class="timeline-sublabel">Within days</div>
                </div>
                
                <div class="timeline-marker within-2-weeks">
                  <div class="timeline-point"></div>
                  <div class="timeline-label">Medium-Term</div>
                  <div class="timeline-sublabel">Next few weeks</div>
                </div>
                
                <div class="timeline-marker within-month">
                  <div class="timeline-point"></div>
                  <div class="timeline-label">Long-Term/Planning</div>
                  <div class="timeline-sublabel">Future planning</div>
                </div>
                
                <div class="timeline-marker one-to-three">
                  <div class="timeline-point"></div>
                  <div class="timeline-label">Other</div>
                  <div class="timeline-sublabel">Custom timeframe</div>
                </div>
              </div>
              
              <div class="timeline-codes">
                <div class="timeline-code-item">
                  <span class="dropdown-value-label">Values:</span>
                  <div class="timeline-code-list">
                    <span class="dropdown-value-code">Immediate/Urgent</span>
                    <span class="dropdown-value-code">Short-Term</span>
                    <span class="dropdown-value-code">Medium-Term</span>
                    <span class="dropdown-value-code">Long-Term/Planning</span>
                    <span class="dropdown-value-code">Other</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Ground Surface Type Options -->
          <div class="dropdown-category-card">
            <div class="dropdown-category-header">
              <div class="dropdown-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                  <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                  <line x1="12" y1="22.08" x2="12" y2="12"></line>
                </svg>
              </div>
              <div>
                <h3>Site Ground Surface Type</h3>
                <p class="category-prop-info">Property: <code>site_ground_type</code> (Dropdown)</p>
              </div>
            </div>
            <p class="category-description">Ground/terrain information at the drop-off location for installation planning</p>
            
            <div class="classification-cards">
              <div class="classification-card hot">
                <div class="classification-card-header">
                  <div class="classification-indicator"></div>
                  <h4>Cement</h4>
                </div>
                <div class="classification-card-body">
                  <p>Solid cement or concrete surface at the installation location</p>
                  <div class="classification-attributes">
                    <div class="classification-attribute">
                      <span class="attribute-label">Surface Type:</span>
                      <span class="attribute-value">Hard, flat surface</span>
                    </div>
                    <div class="classification-attribute">
                      <span class="attribute-label">Setup Difficulty:</span>
                      <span class="attribute-value">Low - Easiest surface</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="classification-card warm">
                <div class="classification-card-header">
                  <div class="classification-indicator"></div>
                  <h4>Gravel</h4>
                </div>
                <div class="classification-card-body">
                  <p>Gravel surface that may require leveling and stabilization</p>
                  <div class="classification-attributes">
                    <div class="classification-attribute">
                      <span class="attribute-label">Surface Type:</span>
                      <span class="attribute-value">Semi-stable surface</span>
                    </div>
                    <div class="classification-attribute">
                      <span class="attribute-label">Setup Difficulty:</span>
                      <span class="attribute-value">Medium - May need leveling</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="classification-card cold">
                <div class="classification-card-header">
                  <div class="classification-indicator"></div>
                  <h4>Dirt</h4>
                </div>
                <div class="classification-card-body">
                  <p>Dirt or soil surface that may require preparation for stability</p>
                  <div class="classification-attributes">
                    <div class="classification-attribute">
                      <span class="attribute-label">Surface Type:</span>
                      <span class="attribute-value">Variable stability</span>
                    </div>
                    <div class="classification-attribute">
                      <span class="attribute-label">Setup Difficulty:</span>
                      <span class="attribute-value">Medium - Weather dependent</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div class="classification-card not-qualified">
                <div class="classification-card-header">
                  <div class="classification-indicator"></div>
                  <h4>Grass</h4>
                </div>
                <div class="classification-card-body">
                  <p>Grass surface that may require additional considerations</p>
                  <div class="classification-attributes">
                    <div class="classification-attribute">
                      <span class="attribute-label">Surface Type:</span>
                      <span class="attribute-value">Soft, variable surface</span>
                    </div>
                    <div class="classification-attribute">
                      <span class="attribute-label">Setup Difficulty:</span>
                      <span class="attribute-value">High - Weather sensitive</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- AI Call Sentiment Options -->
          <div class="dropdown-category-card">
            <div class="dropdown-category-header">
              <div class="dropdown-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <div>
                <h3>AI Call Sentiment Options</h3>
                <p class="category-prop-info">Property: <code>ai_call_sentiment</code> (Dropdown)</p>
              </div>
            </div>
            <p class="category-description">AI-determined assessment of prospect sentiment and conversation tone</p>
            
            <div class="sentiment-values">
              <div class="sentiment-card positive">
                <div class="sentiment-content">
                  <h4>Positive</h4>
                  <p>Prospect exhibited enthusiastic engagement, showed clear interest, and responded positively to information provided</p>
                  <div class="sentiment-actions">
                    <span class="dropdown-value-code">positive</span>
                  </div>
                </div>
              </div>
              
              <div class="sentiment-card neutral">
                <div class="sentiment-content">
                  <h4>Neutral</h4>
                  <p>Prospect was business-like, factual, and neither particularly excited nor disinterested in the conversation</p>
                  <div class="sentiment-actions">
                    <span class="dropdown-value-code">neutral</span>
                  </div>
                </div>
              </div>
              
              <div class="sentiment-card negative">
                <div class="sentiment-content">
                  <h4>Negative</h4>
                  <p>Prospect exhibited frustration, impatience, or dissatisfaction during the conversation</p>
                  <div class="sentiment-actions">
                    <span class="dropdown-value-code">negative</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- AI Lead Type Options -->
          <div class="dropdown-category-card">
            <div class="dropdown-category-header">
              <div class="dropdown-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                  <circle cx="9" cy="7" r="4"></circle>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                </svg>
              </div>
              <div>
                <h3>AI Lead Type Options</h3>
                <p class="category-prop-info">Property: <code>ai_lead_type</code> (Dropdown)</p>
              </div>
            </div>
            <p class="category-description">AI-determined category of lead for appropriate routing and handling</p>
            
            <div class="lead-type-grid">
              <div class="lead-type-card">
                <div class="lead-type-content">
                  <h4>Services</h4>
                  <p>Lead primarily interested in our core service offerings</p>
                  <div class="lead-type-meta">
                    <span class="dropdown-value-code">Services</span>
                  </div>
                </div>
              </div>
              
              <div class="lead-type-card">
                <div class="lead-type-content">
                  <h4>Logistics</h4>
                  <p>Lead focused on logistics, delivery, and operational details</p>
                  <div class="lead-type-meta">
                    <span class="dropdown-value-code">Logistics</span>
                  </div>
                </div>
              </div>
              
              <div class="lead-type-card">
                <div class="lead-type-content">
                  <h4>Leads</h4>
                  <p>Lead with high potential requiring specialized sales attention</p>
                  <div class="lead-type-meta">
                    <span class="dropdown-value-code">Leads</span>
                  </div>
                </div>
              </div>
              
              <div class="lead-type-card">
                <div class="lead-type-content">
                  <h4>Disqualify</h4>
                  <p>Lead that does not meet basic qualification criteria</p>
                  <div class="lead-type-meta">
                    <span class="dropdown-value-code">Disqualify</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    `;
  }

  getImplementationSection() {
    return /* html */ `
      <section id="implementation" class="content-section ${this.state.activeSection === 'implementation' ? 'active' : ''}">
        <h2>Implementation Notes</h2>
        <p>Technical information about implementing and managing HubSpot custom properties within the Stahla AI SDR application.</p>
        
        <h3>Property Creation</h3>
        <p>Custom properties are created in HubSpot programmatically using the HubSpot API. The creation process is managed through the application's configuration system to ensure consistency.</p>
        
        <div class="code-block">
          <pre><code># Example of creating a custom property via the HubSpot API
import hubspot
from hubspot.crm.properties import (
    PropertyCreate,
    PropertyGroup,
    PropertyGroupCreate,
)

# Initialize the client
client = hubspot.Client.create(api_key=API_KEY)

# Create a property
property_create = PropertyCreate(
    name="stahla_ai_classification",
    label="AI Lead Classification",
    type="enumeration",
    field_type="select",
    group_name="stahla_ai_properties",
    options=[
        {"label": "Hot - Ready to purchase", "value": "hot"},
        {"label": "Warm - Actively considering", "value": "warm"},
        {"label": "Cold - Information gathering", "value": "cold"},
        {"label": "Not Qualified - Doesn't meet criteria", "value": "not_qualified"},
    ],
)

response = client.crm.properties.core_api.create(
    object_type="contacts", 
    property_create=property_create)</code></pre>
          <button class="copy-btn" data-text="import hubspot
from hubspot.crm.properties import PropertyCreate

client = hubspot.Client.create(api_key=API_KEY)

property_create = PropertyCreate(
    name='stahla_ai_classification',
    label='AI Lead Classification',
    type='enumeration',
    field_type='select',
    group_name='stahla_ai_properties',
    options=[
        {'label': 'Hot - Ready to purchase', 'value': 'hot'},
        {'label': 'Warm - Actively considering', 'value': 'warm'},
        {'label': 'Cold - Information gathering', 'value': 'cold'},
        {'label': 'Not Qualified - Doesn\'t meet criteria', 'value': 'not_qualified'},
    ],
)

response = client.crm.properties.core_api.create(
    object_type='contacts', 
    property_create=property_create)">Copy</button>
        </div>
        
        <h3>Property Groups</h3>
        <p>Custom properties are organized into logical groups for better organization in the HubSpot interface:</p>
        <ul>
          <li><strong>stahla_contact_properties</strong> - Contact information properties</li>
          <li><strong>stahla_service_properties</strong> - Service and product properties</li>
          <li><strong>stahla_event_properties</strong> - Event and job properties</li>
          <li><strong>stahla_site_properties</strong> - Site logistics properties</li>
          <li><strong>stahla_ai_properties</strong> - AI interaction properties</li>
          <li><strong>stahla_qualification_properties</strong> - Lead qualification properties</li>
          <li><strong>stahla_consent_properties</strong> - Consent and preferences properties</li>
        </ul>
        
        <h3>HubSpot Integration Flow</h3>
        <p>The integration between the Stahla AI SDR application and HubSpot involves several components:</p>
        <ol>
          <li>Webhook receiver for HubSpot events</li>
          <li>API client for reading and writing HubSpot data</li>
          <li>Data transformers for converting between application and HubSpot formats</li>
          <li>Background workers for asynchronous updates</li>
          <li>Logging and error handling specific to HubSpot operations</li>
        </ol>
      </section>
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
        
        .hubspot-docs {
          width: 100%;
          padding: 0 10px;
          margin: 0;
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .hubspot-docs-header {
          padding: 0;
        }
        
        .hubspot-docs-header h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          line-height: 1.4;
          color: var(--title-color);
        }
        
        .hubspot-docs-header p {
          font-size: 1rem;
          margin: 0;
          padding: 0;
          color: var(--gray-color);
        }
        
        .hubspot-docs-content {
          display: flex;
          width: 100%;
          flex-flow: row-reverse;
          justify-content: space-between;
          gap: 20px;
        }
        
        .hubspot-docs-sidebar {
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

        .hubspot-docs-sidebar::-webkit-scrollbar {
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
        
        .hubspot-docs-main {
          flex: 1;
          padding: 20px 0;
          min-width: 0;
        }
        
        .hubspot-content-container {
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
        
        .property-overview {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .property-card {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
        }
        
        .property-card h4 {
          font-size: 1rem;
          margin: 0 0 10px;
          color: var(--title-color);
        }
        
        .property-card p {
          font-size: 0.9rem;
          margin: 0;
          color: var(--text-color);
        }
        
        .properties-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
          margin: 20px 0;
        }
        
        .property-item {
          padding: 15px;
          background-color: var(--stat-background);
          border-radius: 6px;
          border: var(--border);
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .property-item:hover {
          transform: translateY(-2px);
        }
        
        .property-item h3 {
          margin: 0 0 10px;
          font-size: 1.2rem;
          color: var(--title-color);
        }
        
        .property-item p {
          margin: 10px 0 0;
          font-size: 0.9rem;
        }
        
        .table-responsive {
          overflow-x: auto;
          border-top-left-radius: 8px;
          border-top-right-radius: 8px;
          border-bottom-left-radius: 8px;
          border-bottom-right-radius: 8px;
          margin: 20px 0;
          max-width: 100%; /* Ensure table container doesn't overflow */
          display: block; /* Force block-level display */
        }
        
        /* Property tables styling */
        .property-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.9rem;
          background-color: var(--background);
          table-layout: fixed; /* Using fixed layout for better control of column widths */
          border-spacing: 0;
        }
        
        .property-table thead {
          background-color: var(--stat-background);
          position: sticky;
          top: 0;
        }
        
        .property-table th {
          padding: 12px 15px;
          text-align: left;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .property-table td {
          padding: 10px 15px;
          color: var(--text-color);
          vertical-align: top;
          line-height: 1.4; /* Improve line spacing for readability */
          box-sizing: border-box; /* Ensure padding is included in width calculations */
        }
        
        .property-table tr {
          height: 100%; /* Ensure rows take full height */
        }
        
        .property-table tr:nth-child(even) {
          background-color: var(--stat-background);
        }
        
        .property-table tr:last-child td {
          border-bottom: none;
        }
        
        .property-name-col {
          width: 30%; /* Fixed width for property name column */
          min-width: 150px; /* Ensure minimum readable width */
          overflow: hidden; /* Hide overflow */
        }
        
        .property-type-col {
          width: 20%; /* Fixed width for type column */
          min-width: 100px; /* Ensure minimum readable width */
          overflow: hidden; /* Hide overflow */
        }
        
        .property-desc-col {
          width: 50%; /* Fixed width for description column */
          min-width: 200px; /* Ensure minimum readable width */
        }
        
         .category-link {
          color: var(--text-color);
          text-decoration: none;
          font-weight: 500;
        }
        
        .category-link:hover {
          text-decoration: none;
        }
        
        .property-name {
          white-space: normal; /* Allow text to wrap normally */
          word-break: break-word; /* Break long words if necessary */
          display: block;
          width: 100%; /* Take full width of parent cell */
          font-family: var(--font-mono); /* From the duplicate rule below */
          color: var(--accent-color); /* From the duplicate rule below */
        }
        
        .property-type {
          color: var(--gray-color);
        }
        
        .value-list {
          list-style-type: none;
          padding: 0 0 0 10px;
          margin: 10px 0;
        }
        
        .value-list li {
          padding: 5px 0;
          font-size: 0.9rem;
          position: relative;
        }
        
        .value-list li::before {
          content: '•';
          position: absolute;
          left: -10px;
          color: var(--accent-color);
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
        
        /* HubSpot specific styling */
        .hubspot-header {
          padding: 0;
        }
        
        .hubspot-header h2 {
          color: var(--title-color);
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
        }
        
        .property-name.hubspot-property {
          color: var(--text-color);
        }
        
        /* Dropdown & Checkbox Values section styling */
        .dropdown-values-container {
          display: flex;
          flex-direction: column;
          gap: 40px;
          margin: 20px 0;
        }
        
        .dropdown-category-card {
          padding: 10px 0;
          transition: all 0.3s ease;
        }
        
        .dropdown-category-header {
          display: flex;
          align-items: center;
          gap: 15px;
          margin-bottom: 10px;
        }
        
        .dropdown-icon {
          background-color: var(--tab-background);
          color: var(--accent-color);
          border-radius: 8px;
          width: 42px;
          height: 42px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        
        .dropdown-category-card h3 {
          margin: 0 0;
          font-size: 1.25rem;
          color: var(--title-color);
          font-weight: 600;
        }
        
        .category-prop-info {
          font-size: 0.9rem;
          color: var(--gray-color);
          margin: 0;
        }

        .dropdown-category-card .category-prop-info {
          margin: 0;
        }
        
        .category-description {
          color: var(--text-color);
          font-size: 0.95rem;
          margin-bottom: 25px;
          max-width: 100%;
        }
        
        /* Service type values styling */
        .service-values {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 15px;
        }
        
        .dropdown-value-item {
          background-color: var(--background);
          border-radius: 8px;
          padding: 18px;
          border: var(--border);
          display: flex;
          flex-direction: column;
          gap: 12px;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .dropdown-value-item:hover {
          transform: translateY(-2px);
        }
        
        .dropdown-item-header {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .service-icon {
          width: 36px;
          height: 36px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--white-color);
          flex-shrink: 0;
        }
        
        .service-icon.venue {
          background-color: #4338ca;
        }
        
        .service-icon.equipment {
          background-color: #0891b2;
        }
        
        .service-icon.full-service {
          background-color: #9333ea;
        }
        
        .service-icon.av {
          background-color: #ea580c;
        }
        
        .service-icon.staffing {
          background-color: #16a34a;
        }
        
        .service-icon.other {
          background-color: #64748b;
        }
        
        .dropdown-value-label {
          font-weight: 500;
          color: var(--title-color);
          font-size: 1rem;
        }
        
        .dropdown-value-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding-top: 8px;
          border-top: var(--border);
        }
        
        .dropdown-value-code {
          font-family: var(--font-mono);
          font-size: 0.8rem;
          background-color: var(--background);
          padding: 4px 8px 4px 12px;
          border-radius: 4px;
          color: var(--accent-color);
          position: relative;
        }

        .dropdown-value-code::before {
          content: '-';
          font-weight: 600;
          color: var(--text-color);
          position: absolute;
          top: 50%;
          left: 0;
          transform: translateY(-50%);
        }
        
        .dropdown-value-usage {
          font-size: 0.8rem;
          color: var(--gray-color);
        }
        
        /* Priority values styling */
        .priority-values {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 20px;
        }
        
        .priority-card {
          border-radius: 10px;
          padding: 0;
          overflow: hidden;
          transition: all 0.3s ease;
        }
        
        .priority-header {
          padding: 5px 0;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .priority-indicator {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }
        
        .priority-header h4 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .priority-details {
          padding: 0;
        }
        
        .priority-timeline {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 15px;
          color: var(--gray-color);
          font-size: 0.9rem;
        }
        
        .priority-description p {
          color: var(--text-color);
          margin: 0;
          font-size: 0.95rem;
          line-height: 1.5;
        }
        
        .priority-code-wrapper {
          margin-top: 15px;
          display: flex;
        }
        
        .high-priority {
          border-top: none
        }
        
        .high-priority .priority-indicator {
          background-color: #e53e3e;
        }
        
        .medium-priority {
          border-top: none;
        }
        
        .medium-priority .priority-indicator {
          background-color: #dd6b20;
        }
        
        .low-priority {
          border-top: none;
        }
        
        .low-priority .priority-indicator {
          background-color: #38a169;
        }
        
        /* Timeline slider styling */
        .timeline-slider {
          margin-top: 30px;
          padding: 0 20px;
        }
        
        .timeline-track {
          position: relative;
          display: flex;
          justify-content: space-between;
          padding-bottom: 50px;
        }
        
        .timeline-track::before {
          content: "";
          position: absolute;
          top: 15px;
          left: 0;
          right: 0;
          height: 4px;
          background: linear-gradient(to right, 
            #e53e3e 0%, #e53e3e 16%, 
            #dd6b20 16%, #dd6b20 33%, 
            #d97706 33%, #d97706 50%, 
            #65a30d 50%, #65a30d 67%, 
            #0891b2 67%, #0891b2 84%, 
            #3b82f6 84%, #3b82f6 100%);
          border-radius: 2px;
        }
        
        .timeline-marker {
          display: flex;
          flex-direction: column;
          align-items: center;
          position: relative;
          width: 16.66%;
          z-index: 2;
        }
        
        .timeline-point {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          border: var(--border);
          margin-bottom: 15px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .timeline-marker:hover .timeline-point {
          transform: scale(1.3);
        }
        
        .timeline-label {
          font-weight: 600;
          font-size: 0.9rem;
          color: var(--title-color);
          margin-bottom: 4px;
          text-align: center;
        }
        
        .timeline-sublabel {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-align: center;
        }
        
        .timeline-marker.urgent .timeline-point {
          border-color: #e53e3e;
          box-shadow: 0 0 0 3px rgba(254, 226, 226, 0.8);
        }
        
        .timeline-marker.this-week .timeline-point {
          border-color: #dd6b20;
          box-shadow: 0 0 0 3px rgba(254, 235, 220, 0.8);
        }
        
        .timeline-marker.within-2-weeks .timeline-point {
          border-color: #d97706;
          box-shadow: 0 0 0 3px rgba(255, 237, 213, 0.8);
        }
        
        .timeline-marker.within-month .timeline-point {
          border-color: #65a30d;
          box-shadow: 0 0 0 3px rgba(236, 253, 245, 0.8);
        }
        
        .timeline-marker.one-to-three .timeline-point {
          border-color: #0891b2;
          box-shadow: 0 0 0 3px rgba(224, 242, 254, 0.8);
        }
        
        .timeline-marker.three-plus .timeline-point {
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(219, 234, 254, 0.8);
        }
        
        .timeline-codes {
          display: flex;
          justify-content: start;
          margin: 0;
        }
        
        .timeline-code-item {
          display: flex;
          flex-direction: column;
          align-items: start;
          gap: 10px;
        }

        .timeline-code-item .dropdown-value-label {
          font-size: 0.95rem;
          font-weight: 500;
          color: var(--title-color);
        }

        .timeline-code-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          justify-content: center;
        }
        
        /* Classification cards styling */
        .classification-cards {
          display: flex;
          flex-flow: column;
          gap: 25px;
          margin-top: 25px;
        }
        
        .classification-card {
          border-radius: 10px;
          overflow: hidden;
          transition: all 0.3s ease;
        }
        
        .classification-card-header {
          padding: 0;
          display: flex;
          align-items: center;
          gap: 12px;
        }
        
        .classification-card-header h4 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .classification-card-body {
          padding: 0;
        }
        
        .classification-card-body p {
          margin: 0 0 15px 0;
          line-height: 1.5;
          color: var(--text-color);
        }
        
        .classification-attributes {
          background-color: var(--stat-background);
          border-radius: 6px;
          padding: 12px 15px;
          margin: 15px 0;
        }
        
        .classification-attribute {
          display: flex;
          justify-content: space-between;
          padding: 5px 0;
          border-bottom: var(--border);
        }
        
        .classification-attribute:last-child {
          border-bottom: none;
        }
        
        .attribute-label {
          font-size: 0.85rem;
          color: var(--gray-color);
        }
        
        .attribute-value {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--text-color);
        }
        
        .classification-code-wrapper {
          margin-top: 15px;
          display: flex;
          justify-content: flex-end;
        }
        
        .classification-indicator {
          width: 12px;
          height: 12px;
          border-radius: 50%;
        }
        
        .hot .classification-indicator {
          background-color: rgba(229, 62, 62, 0.1);
        }
        
        .warm .classification-indicator {
          background-color: rgba(221, 107, 32, 0.1);
        }
        
        .warm .classification-indicator {
          background-color: #dd6b20;
        }
        
        
        .cold .classification-indicator{
          background-color: rgba(49, 130, 206, 0.1);
        }
        
        .cold .classification-indicator {
          background-color: #3182ce;
        }
        
        
        .not-qualified .classification-indicator {
          background-color: rgba(113, 128, 150, 0.1);
        }
        
        .not-qualified .classification-indicator {
          background-color: #718096;
        }
        
        @media (max-width: 900px) {
          .hubspot-docs-content {
            flex-direction: column;
          }
          
          .hubspot-docs-sidebar {
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
          
          .table-responsive {
            margin: 15px -10px;
           /* border-radius: 6px; */
            box-shadow: none;
            border-left: none;
            border-right: none;
          }
          
          .property-table {
            font-size: 0.85rem;
          }
          
          .property-table th,
          .property-table td {
            padding: 8px 10px;
          }
          
          .dropdown-category-card {
            padding: 20px 15px;
          }
          
          .service-values,
          .priority-values, 
          .classification-cards {
            grid-template-columns: 1fr;
          }
          
          .timeline-track {
            flex-direction: column;
            gap: 40px;
            padding-left: 40px;
            padding-bottom: 0;
          }
          
          .timeline-track::before {
            top: 0;
            bottom: 0;
            right: auto;
            left: 6px;
            width: 4px;
            height: auto;
            background: linear-gradient(to bottom, 
              #e53e3e 0%, #e53e3e 16%, 
              #dd6b20 16%, #dd6b20 33%, 
              #d97706 33%, #d97706 50%, 
              #65a30d 50%, #65a30d 67%, 
              #0891b2 67%, #0891b2 84%, 
              #3b82f6 84%, #3b82f6 100%);
          }
          
          .timeline-marker {
            width: 100%;
            align-items: flex-start;
          }
          
          .timeline-point {
            position: absolute;
            left: -40px;
            top: 0;
          }
          
          /* Additional options styling for project category */
        .additional-options {
          margin-top: 25px;
          border-top: 1px dashed #e2e8f0;
          padding-top: 25px;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        }
        
        /* Sentiment cards styling */
        .sentiment-values {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 20px;
          margin-top: 25px;
        }
        
        .sentiment-card {
          display: flex;
          align-items: flex-start;
          gap: 15px;
          border-radius: 10px;
          padding: 20px;
          transition: all 0.3s ease;
        }
        
        .sentiment-card:hover {
          transform: translateY(-3px);
        }
        
        .sentiment-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          padding: 8px;
          flex-shrink: 0;
        }
        
        .positive .sentiment-indicator {
          color: #38a169;
          background-color: rgba(56, 161, 105, 0.1);
        }
        
        .neutral .sentiment-indicator {
          color: #3182ce;
          background-color: rgba(49, 130, 206, 0.1);
        }
        
        .negative .sentiment-indicator {
          color: #e53e3e;
          background-color: rgba(229, 62, 62, 0.1);
        }
        
        .sentiment-content {
          flex: 1;
        }
        
        .sentiment-content h4 {
          margin: 0 0 10px 0;
          font-size: 1.1rem;
          color: var(--title-color);
        }
        
        .sentiment-content p {
          font-size: 0.9rem;
          margin: 0 0 15px 0;
          color: var(--text-color);
        }
        
        .sentiment-actions {
          display: flex;
          justify-content: flex-end;
        }
        
        /* Lead type grid styling */
        .lead-type-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 20px;
          margin-top: 25px;
        }
        
        .lead-type-card {
          border-radius: 10px;
          overflow: hidden;
          transition: all 0.3s ease;
        }
        
        .lead-type-card:hover {
          transform: translateY(-3px);
        }
        
        .lead-type-icon {
          background-color: var(--stat-background);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          color: var(--accent-color);
        }
        
        .lead-type-content {
          padding: 20px;
        }
        
        .lead-type-content h4 {
          margin: 0 0 10px 0;
          font-size: 1.1rem;
          color: var(--title-color);
        }
        
        .lead-type-content p {
          font-size: 0.9rem;
          margin: 0 0 15px 0;
          color: var(--text-color);
        }
        
        .lead-type-meta {
          display: flex;
          justify-content: flex-end;
          border-top: var(--border);
          padding-top: 15px;
          margin-top: 10px;
        }
            border-left: none;
            border-right: none;
          }
          
          .property-table {
            font-size: 0.85rem;
          }
          
          .property-table th,
          .property-table td {
            padding: 8px 10px;
          }
          
          .dropdown-values, 
          .priority-values,
          .timeline-grid,
          .classification-grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
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

      // Handle property item clicks in the grid
      const propertyItem = event.target.closest('.property-item');
      if (propertyItem) {
        const property = propertyItem.dataset.property;
        if (property) {
          this._navigateToSection(property);
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

    // If navigating to a section within a category, ensure that category is expanded
    if (section === 'contact' || section === 'service' || section === 'event' ||
      section === 'site' || section === 'ai' || section === 'lead' ||
      section === 'consent' || section === 'dropdown') {
      this.state.expandedCategories.add('properties');
    }

    this.render();

    // Scroll to top of content
    const mainElement = this.shadowObj.querySelector('#hubspot-docs-main');
    if (mainElement) {
      mainElement.scrollTop = 0;
    }
  }
}