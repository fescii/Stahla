export default class HubspotLeads extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/hubspot/leads/recent";
    this.leadsData = null;
    this._loading = true;
    this._empty = false;
    this.currentPage = 1;
    this.hasMore = false;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.fetchLeads();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchLeads = async (page = 1) => {
    this._loading = true;
    this._empty = false;
    this.render();

    try {
      const response = await this.api.get(`${this.url}?page=${page}`, { content: "json" });

      if (response.status_code === 401) {
        this._loading = false;
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.leadsData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.leadsData = response.data;
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching HubSpot leads:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.leadsData = null;
      this.render();
    }
  };

  attachEventListeners = () => {
    // Pagination buttons
    const prevBtn = this.shadowObj.querySelector('.pagination-btn.prev');
    const nextBtn = this.shadowObj.querySelector('.pagination-btn.next');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentPage > 1) {
          this.fetchLeads(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchLeads(this.currentPage + 1);
        }
      });
    }
  };

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody = () => {
    if (this._loading) {
      return /* html */ `<div class="container">${this.getLoader()}</div>`;
    }

    if (this._empty || !this.leadsData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getLeadStats()}
        ${this.getLeadsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>HubSpot Leads</h1>
        <p class="subtitle">Recent leads from HubSpot CRM</p>
      </div>
    `;
  };

  getLeadStats = () => {
    if (!this.leadsData.items || this.leadsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateLeadStats(this.leadsData.items);

    return /* html */ `
      <div class="lead-stats">
        <h3>Lead Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalLeads}</span>
            <span class="stat-label">Total Leads</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.qualifiedLeads}</span>
            <span class="stat-label">Qualified</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgEstValue}</span>
            <span class="stat-label">Avg Est. Value</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.needsFollowUp}</span>
            <span class="stat-label">Needs Follow-up</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateLeadStats = (leads) => {
    const totalLeads = leads.length;
    const qualifiedLeads = leads.filter(l =>
      l.properties.ai_lead_type === 'Qualified' ||
      l.properties.ai_lead_type === 'Hot Lead'
    ).length;

    const needsFollowUp = leads.filter(l => l.properties.needs_human_follow_up).length;

    const estimatedValues = leads
      .filter(l => l.properties.ai_estimated_value)
      .map(l => parseFloat(l.properties.ai_estimated_value));

    const avgEstValue = estimatedValues.length > 0
      ? `$${Math.round(estimatedValues.reduce((sum, val) => sum + val, 0) / estimatedValues.length)}`
      : '$0';

    return {
      totalLeads,
      qualifiedLeads,
      avgEstValue,
      needsFollowUp
    };
  };

  getLeadsList = () => {
    if (!this.leadsData.items || this.leadsData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="leads-grid">
        ${this.leadsData.items.map(lead => this.getLeadCard(lead)).join('')}
      </div>
    `;
  };

  getLeadCard = (lead) => {
    const props = lead.properties;

    return /* html */ `
      <div class="lead-card" data-lead-id="${lead.id}" tabindex="0">
        <div class="lead-header">
          <div class="lead-info">
            <h3>Lead ${lead.id.slice(-6)}</h3>
            ${this.getLeadTypeBadge(props.ai_lead_type)}
            ${props.quote_urgency ? /* html */ `<span class="urgency-badge urgency-${props.quote_urgency.toLowerCase()}">${props.quote_urgency}</span>` : ''}
          </div>
          <div class="hubspot-badge">HubSpot</div>
        </div>
        
        <div class="lead-body">
          ${this.getProjectInfo(props)}
          
          ${this.getAIInsights(props)}
          
          ${this.getEventDetails(props)}
          
          ${this.getLocationInfo(props)}
          
          <div class="lead-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Created</span>
                <span class="detail-value">${this.formatDate(lead.created_at)}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Updated</span>
                <span class="detail-value">${this.formatDate(lead.updated_at)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getLeadTypeBadge = (leadType) => {
    if (!leadType) return '';

    const badgeClass = leadType.toLowerCase().replace(/\s+/g, '-');
    return /* html */ `<span class="lead-type-badge type-${badgeClass}">${leadType}</span>`;
  };

  getProjectInfo = (props) => {
    return /* html */ `
      <div class="project-info">
        ${props.project_category ? /* html */ `
          <div class="info-item featured">
            <span class="info-label">Project Category</span>
            <span class="info-value project-category">${props.project_category}</span>
          </div>
        ` : ''}
        
        ${props.ai_estimated_value ? /* html */ `
          <div class="info-item">
            <span class="info-label">Estimated Value</span>
            <span class="info-value estimated-value">$${this.formatCurrency(props.ai_estimated_value)}</span>
          </div>
        ` : ''}
        
        ${this.getRequirements(props)}
      </div>
    `;
  };

  getRequirements = (props) => {
    const requirements = [];

    if (props.units_needed) requirements.push(`Units: ${props.units_needed}`);
    if (props.number_of_stalls) requirements.push(`Stalls: ${props.number_of_stalls}`);
    if (props.expected_attendance) requirements.push(`Attendance: ${props.expected_attendance}`);
    if (props.event_duration_days) requirements.push(`Duration: ${props.event_duration_days} days`);

    if (requirements.length === 0) return '';

    return /* html */ `
      <div class="info-item">
        <span class="info-label">Requirements</span>
        <div class="requirements-tags">
          ${requirements.map(req => /* html */ `<span class="requirement-tag">${req}</span>`).join('')}
        </div>
      </div>
    `;
  };

  getAIInsights = (props) => {
    if (!props.ai_lead_type && !props.ai_classification_reasoning && !props.ai_intended_use) {
      return '';
    }

    return /* html */ `
      <div class="ai-insights">
        <div class="ai-header">
          <span class="ai-icon">🤖</span>
          <span class="ai-title">AI Insights</span>
          ${props.ai_classification_confidence ? /* html */ `
            <span class="confidence-score">${Math.round(props.ai_classification_confidence * 100)}%</span>
          ` : ''}
        </div>
        
        ${props.ai_intended_use ? /* html */ `
          <div class="ai-item">
            <span class="ai-label">Intended Use</span>
            <span class="ai-value">${props.ai_intended_use}</span>
          </div>
        ` : ''}
        
        ${props.ai_classification_reasoning ? /* html */ `
          <div class="ai-item">
            <span class="ai-label">Reasoning</span>
            <p class="ai-reasoning">${props.ai_classification_reasoning}</p>
          </div>
        ` : ''}
        
        ${props.ai_routing_suggestion ? /* html */ `
          <div class="ai-item">
            <span class="ai-label">Routing Suggestion</span>
            <span class="ai-value routing">${props.ai_routing_suggestion}</span>
          </div>
        ` : ''}
      </div>
    `;
  };

  getEventDetails = (props) => {
    if (!props.rental_start_date && !props.rental_end_date && !props.weekend_service_needed && !props.ada_required) {
      return '';
    }

    return /* html */ `
      <div class="event-details">
        <div class="event-header">Event Details</div>
        
        ${props.rental_start_date || props.rental_end_date ? /* html */ `
          <div class="date-range">
            <div class="detail-row">
              ${props.rental_start_date ? /* html */ `
                <div class="detail-item">
                  <span class="detail-label">Start Date</span>
                  <span class="detail-value">${this.formatEventDate(props.rental_start_date)}</span>
                </div>
              ` : ''}
              ${props.rental_end_date ? /* html */ `
                <div class="detail-item">
                  <span class="detail-label">End Date</span>
                  <span class="detail-value">${this.formatEventDate(props.rental_end_date)}</span>
                </div>
              ` : ''}
            </div>
          </div>
        ` : ''}
        
        ${this.getServiceRequirements(props)}
      </div>
    `;
  };

  getServiceRequirements = (props) => {
    const requirements = [];

    if (props.ada_required) requirements.push('ADA Required');
    if (props.weekend_service_needed) requirements.push('Weekend Service');
    if (props.cleaning_service_needed) requirements.push('Cleaning Service');
    if (props.within_local_service_area) requirements.push('Local Service Area');

    if (requirements.length === 0) return '';

    return /* html */ `
      <div class="service-requirements">
        ${requirements.map(req => /* html */ `<span class="service-tag">${req}</span>`).join('')}
      </div>
    `;
  };

  getLocationInfo = (props) => {
    if (!props.within_local_service_area && !props.needs_human_follow_up) {
      return '';
    }

    return /* html */ `
      <div class="location-info">
        <div class="status-indicators">
          ${props.within_local_service_area !== undefined ? /* html */ `
            <span class="status-indicator ${props.within_local_service_area ? 'in-area' : 'out-area'}">
              ${props.within_local_service_area ? '✓ Service Area' : '○ Outside Area'}
            </span>
          ` : ''}
          
          ${props.needs_human_follow_up ? /* html */ `
            <span class="status-indicator follow-up">Needs Follow-up</span>
          ` : ''}
        </div>
      </div>
    `;
  };

  getPagination = () => {
    if (!this.leadsData || this.leadsData.total <= this.leadsData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.leadsData.total / this.leadsData.limit)}
        </span>
        <button class="pagination-btn next ${!this.hasMore ? 'disabled' : ''}" 
                ${!this.hasMore ? 'disabled' : ''}>
          Next
        </button>
      </div>
    `;
  };

  getLoader() {
    return /* html */ `
      <div class="loader-container">
        <div class="loader"></div>
      </div>
    `;
  }

  getEmptyMessage = () => {
    return /* html */ `
      <div class="empty-state">
        <h2>No Leads Found</h2>
        <p>There are no HubSpot leads to display at this time.</p>
      </div>
    `;
  };

  formatCurrency = (value) => {
    const num = parseFloat(value);
    if (isNaN(num)) return '0';
    return num.toLocaleString('en-US');
  };

  formatDate = (dateString) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  formatEventDate = (dateString) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  getStyles = () => {
    return /* html */ `
      <style>
        :host {
          display: block;
          width: 100%;
          background-color: var(--background);
          font-family: var(--font-text), sans-serif;
          line-height: 1.6;
          color: var(--text-color);
        }

        * {
          box-sizing: border-box;
        }

        .container {
          max-width: 100%;
          margin: 0 auto;
          padding: 20px 10px;
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .header {
          text-align: center;
          margin-bottom: 10px;
        }

        .header h1 {
          margin: 0 0 8px 0;
          font-size: 1.8rem;
          font-weight: 600;
          color: var(--hubspot-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
        }

        .lead-stats {
          background: var(--hubspot-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .lead-stats h3 {
          margin: 0 0 12px 0;
          color: var(--hubspot-color);
          font-size: 1.1rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 12px;
        }

        .stat-item {
          text-align: center;
          background: var(--background);
          border-radius: 6px;
          padding: 12px 8px;
        }

        .stat-count {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--hubspot-color);
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .leads-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
        }

        .lead-card {
          background: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          transition: all 0.2s ease;
          cursor: pointer;
          position: relative;
          border-left: 4px solid var(--hubspot-color);
        }

        .lead-card:hover {
          border-color: var(--hubspot-color);
        }

        .lead-card:focus {
          outline: none;
          border-color: var(--hubspot-color);
        }

        .lead-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .lead-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .lead-info h3 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .lead-type-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .lead-type-badge.type-qualified,
        .lead-type-badge.type-hot-lead {
          background: var(--success-color);
          color: var(--white-color);
        }

        .lead-type-badge.type-cold-lead {
          background: var(--gray-color);
          color: var(--white-color);
        }

        .lead-type-badge.type-warm-lead {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .urgency-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .urgency-badge.urgency-urgent {
          background: var(--error-color);
          color: var(--white-color);
        }

        .urgency-badge.urgency-standard {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .hubspot-badge {
          background: var(--hubspot-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 4px 8px;
          border-radius: 12px;
          font-weight: 500;
        }

        .lead-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .project-info {
          background: var(--create-background);
          border-radius: 6px;
          padding: 12px;
        }

        .info-item {
          margin-bottom: 8px;
        }

        .info-item:last-child {
          margin-bottom: 0;
        }

        .info-item.featured .info-value {
          font-size: 1rem;
          font-weight: 600;
        }

        .info-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .info-value {
          font-size: 0.9rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .project-category {
          color: var(--hubspot-color);
          font-weight: 600;
        }

        .estimated-value {
          color: var(--success-color);
          font-weight: 600;
        }

        .requirements-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .requirement-tag {
          background: var(--hubspot-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .ai-insights {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
          border-left: 3px solid var(--accent-color);
        }

        .ai-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
        }

        .ai-icon {
          font-size: 0.9rem;
        }

        .ai-title {
          font-weight: 600;
          color: var(--accent-color);
          font-size: 0.9rem;
        }

        .confidence-score {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 8px;
          margin-left: auto;
        }

        .ai-item {
          margin-bottom: 6px;
        }

        .ai-item:last-child {
          margin-bottom: 0;
        }

        .ai-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 2px;
        }

        .ai-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .ai-value.routing {
          color: var(--accent-color);
          font-weight: 600;
        }

        .ai-reasoning {
          margin: 0;
          font-size: 0.85rem;
          color: var(--text-color);
          line-height: 1.4;
          font-style: italic;
        }

        .event-details {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .event-header {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .service-requirements {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 8px;
        }

        .service-tag {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .location-info {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .status-indicators {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .status-indicator {
          font-size: 0.75rem;
          padding: 4px 8px;
          border-radius: 10px;
          font-weight: 500;
        }

        .status-indicator.in-area {
          background: var(--success-color);
          color: var(--white-color);
        }

        .status-indicator.out-area {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .status-indicator.follow-up {
          background: var(--error-color);
          color: var(--white-color);
        }

        .lead-details {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .detail-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .detail-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .detail-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 12px;
          margin-top: 20px;
        }

        .pagination-btn {
          background: var(--background);
          border: var(--border);
          color: var(--text-color);
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: all 0.2s ease;
        }

        .pagination-btn:hover:not(.disabled) {
          border-color: var(--accent-color);
          color: var(--accent-color);
        }

        .pagination-btn.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .pagination-info {
          font-size: 0.9rem;
          color: var(--gray-color);
          margin: 0 8px;
        }

        .loader-container {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 60px 20px;
        }

        .loader {
          width: 40px;
          height: 40px;
          border: 3px solid var(--gray-background);
          border-top: 3px solid var(--accent-color);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: var(--gray-color);
        }

        .empty-state h2 {
          margin: 0 0 8px 0;
          color: var(--title-color);
        }

        .empty-state p {
          margin: 0;
          font-size: 0.9rem;
        }

        @media (max-width: 768px) {
          .leads-grid {
            grid-template-columns: 1fr;
          }
          
          .detail-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .lead-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .requirements-tags,
          .service-requirements,
          .status-indicators {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      </style>
    `;
  };
}
