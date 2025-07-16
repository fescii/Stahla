export default class ClassifyRecent extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/classify/recent";
    this.classifyData = null;
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
    this.fetchClassifications();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchClassifications = async (page = 1) => {
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
        this.classifyData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.classifyData = response.data;
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching classifications:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.classifyData = null;
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
          this.fetchClassifications(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchClassifications(this.currentPage + 1);
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

    if (this._empty || !this.classifyData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getClassifyStats()}
        ${this.getClassificationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Recent Classifications</h1>
        <p class="subtitle">Most recent lead classifications from AI processing</p>
      </div>
    `;
  };

  getClassifyStats = () => {
    if (!this.classifyData.items || this.classifyData.items.length === 0) {
      return '';
    }

    const stats = this.calculateClassifyStats(this.classifyData.items);

    return /* html */ `
      <div class="classify-stats">
        <h3>Classification Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalClassifications}</span>
            <span class="stat-label">Total Classifications</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.servicesCount}</span>
            <span class="stat-label">Services</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.leadsCount}</span>
            <span class="stat-label">Leads</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgConfidence}%</span>
            <span class="stat-label">Avg Confidence</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateClassifyStats = (classifications) => {
    const totalClassifications = classifications.length;
    const servicesCount = classifications.filter(c => c.classification?.lead_type === 'Services').length;
    const leadsCount = classifications.filter(c => c.classification?.lead_type === 'Leads').length;

    const confidences = classifications
      .filter(c => c.classification?.confidence !== null && c.classification?.confidence !== undefined)
      .map(c => c.classification.confidence);

    const avgConfidence = confidences.length > 0
      ? Math.round((confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length) * 100)
      : 0;

    return {
      totalClassifications,
      servicesCount,
      leadsCount,
      avgConfidence
    };
  };

  getClassificationsList = () => {
    if (!this.classifyData.items || this.classifyData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="classifications-grid">
        ${this.classifyData.items.map(classification => this.getClassificationCard(classification)).join('')}
      </div>
    `;
  };

  getClassificationCard = (classification) => {
    const classif = classification.classification;
    const input = classification.input;

    return /* html */ `
      <div class="classification-card" data-classification-id="${classification._id}" tabindex="0">
        <div class="classification-header">
          <div class="classification-info">
            <h3>Classification ${classification._id.slice(-6)}</h3>
            ${this.getLeadTypeBadge(classif?.lead_type)}
            ${this.getConfidenceBadge(classif?.confidence)}
          </div>
          <div class="source-badge source-${input?.source}">${input?.source || 'unknown'}</div>
        </div>
        
        <div class="classification-body">
          ${this.getClassificationDetails(classif)}
          
          ${this.getInputDetails(input)}
          
          ${this.getContactInfo(input)}
          
          ${this.getEventDetails(input)}
          
          <div class="classification-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Created</span>
                <span class="metadata-value">${this.formatDate(classification.created_at)}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Status</span>
                <span class="metadata-value">${classification.status || 'completed'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getLeadTypeBadge = (leadType) => {
    if (!leadType) return '';

    const badgeClass = leadType.toLowerCase();
    return /* html */ `<span class="lead-type-badge type-${badgeClass}">${leadType}</span>`;
  };

  getConfidenceBadge = (confidence) => {
    if (confidence === null || confidence === undefined) return '';

    const percentage = Math.round(confidence * 100);
    let confidenceClass = 'low';

    if (percentage >= 80) confidenceClass = 'high';
    else if (percentage >= 60) confidenceClass = 'medium';

    return /* html */ `<span class="confidence-badge confidence-${confidenceClass}">${percentage}%</span>`;
  };

  getClassificationDetails = (classif) => {
    if (!classif) return '';

    return /* html */ `
      <div class="classification-details">
        <div class="classification-title">Classification Results</div>
        
        ${classif.routing_suggestion ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">Routing Suggestion</span>
            <span class="detail-value routing">${classif.routing_suggestion}</span>
          </div>
        ` : ''}
        
        ${classif.reasoning ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">AI Reasoning</span>
            <p class="detail-value reasoning">${classif.reasoning}</p>
          </div>
        ` : ''}
        
        ${classif.requires_human_review ? /* html */ `
          <div class="review-required">
            <span class="review-icon">⚠️</span>
            <span class="review-text">Requires Human Review</span>
          </div>
        ` : ''}
      </div>
    `;
  };

  getInputDetails = (input) => {
    if (!input) return '';

    return /* html */ `
      <div class="input-details">
        <div class="input-title">Input Details</div>
        
        ${input.intended_use ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">Intended Use</span>
            <span class="detail-value">${input.intended_use}</span>
          </div>
        ` : ''}
        
        ${input.event_type ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">Event Type</span>
            <span class="detail-value">${input.event_type}</span>
          </div>
        ` : ''}
        
        ${this.getProductInterests(input)}
        
        ${this.getRequirements(input)}
      </div>
    `;
  };

  getProductInterests = (input) => {
    const products = input.product_interest || [];
    if (products.length === 0) return '';

    return /* html */ `
      <div class="detail-item">
        <span class="detail-label">Product Interest</span>
        <div class="product-tags">
          ${products.map(product => /* html */ `<span class="product-tag">${product}</span>`).join('')}
        </div>
      </div>
    `;
  };

  getRequirements = (input) => {
    const requirements = [];

    if (input.required_stalls) requirements.push(`${input.required_stalls} stalls`);
    if (input.guest_count) requirements.push(`${input.guest_count} guests`);
    if (input.ada_required) requirements.push('ADA required');
    if (input.duration_days) requirements.push(`${input.duration_days} days`);

    if (requirements.length === 0) return '';

    return /* html */ `
      <div class="detail-item">
        <span class="detail-label">Requirements</span>
        <div class="requirement-tags">
          ${requirements.map(req => /* html */ `<span class="requirement-tag">${req}</span>`).join('')}
        </div>
      </div>
    `;
  };

  getContactInfo = (input) => {
    if (!input.firstname && !input.email && !input.phone && !input.company) {
      return '';
    }

    return /* html */ `
      <div class="contact-info">
        <div class="contact-title">Contact Information</div>
        
        <div class="contact-row">
          ${input.firstname || input.lastname ? /* html */ `
            <div class="contact-item">
              <span class="contact-label">Name</span>
              <span class="contact-value">${[input.firstname, input.lastname].filter(n => n).join(' ')}</span>
            </div>
          ` : ''}
          
          ${input.company ? /* html */ `
            <div class="contact-item">
              <span class="contact-label">Company</span>
              <span class="contact-value">${input.company}</span>
            </div>
          ` : ''}
        </div>
        
        <div class="contact-row">
          ${input.email ? /* html */ `
            <div class="contact-item">
              <span class="contact-label">Email</span>
              <span class="contact-value">${input.email}</span>
            </div>
          ` : ''}
          
          ${input.phone ? /* html */ `
            <div class="contact-item">
              <span class="contact-label">Phone</span>
              <span class="contact-value">${input.phone}</span>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  };

  getEventDetails = (input) => {
    if (!input.start_date && !input.event_location_description && !input.event_state) {
      return '';
    }

    return /* html */ `
      <div class="event-details">
        <div class="event-title">Event Details</div>
        
        ${input.start_date || input.end_date ? /* html */ `
          <div class="event-dates">
            <div class="contact-row">
              ${input.start_date ? /* html */ `
                <div class="contact-item">
                  <span class="contact-label">Start Date</span>
                  <span class="contact-value">${this.formatEventDate(input.start_date)}</span>
                </div>
              ` : ''}
              ${input.end_date ? /* html */ `
                <div class="contact-item">
                  <span class="contact-label">End Date</span>
                  <span class="contact-value">${this.formatEventDate(input.end_date)}</span>
                </div>
              ` : ''}
            </div>
          </div>
        ` : ''}
        
        ${input.event_location_description ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">Location</span>
            <span class="detail-value">${input.event_location_description}</span>
          </div>
        ` : ''}
        
        ${this.getLocationInfo(input)}
      </div>
    `;
  };

  getLocationInfo = (input) => {
    const locationItems = [];

    if (input.event_state) locationItems.push(`State: ${input.event_state}`);
    if (input.event_city) locationItems.push(`City: ${input.event_city}`);
    if (input.is_local !== undefined) locationItems.push(input.is_local ? 'Local Service' : 'Non-Local');

    if (locationItems.length === 0) return '';

    return /* html */ `
      <div class="detail-item">
        <span class="detail-label">Location Info</span>
        <div class="location-tags">
          ${locationItems.map(item => /* html */ `<span class="location-tag">${item}</span>`).join('')}
        </div>
      </div>
    `;
  };

  getPagination = () => {
    if (!this.classifyData || this.classifyData.total <= this.classifyData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.classifyData.total / this.classifyData.limit)}
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
        <h2>No Classifications Found</h2>
        <p>There are no recent classifications to display at this time.</p>
      </div>
    `;
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
          color: var(--accent-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
        }

        .classify-stats {
          background: var(--create-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .classify-stats h3 {
          margin: 0 0 12px 0;
          color: var(--accent-color);
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
          color: var(--accent-color);
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .classifications-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
        }

        .classification-card {
          background: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          transition: all 0.2s ease;
          cursor: pointer;
          position: relative;
          border-left: 4px solid var(--accent-color);
        }

        .classification-card:hover {
          border-color: var(--accent-color);
        }

        .classification-card:focus {
          outline: none;
          border-color: var(--accent-color);
        }

        .classification-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .classification-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .classification-info h3 {
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

        .lead-type-badge.type-services {
          background: var(--success-color);
          color: var(--white-color);
        }

        .lead-type-badge.type-leads {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .lead-type-badge.type-logistics {
          background: var(--create-color);
          color: var(--white-color);
        }

        .lead-type-badge.type-disqualify {
          background: var(--error-color);
          color: var(--white-color);
        }

        .confidence-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .confidence-badge.confidence-high {
          background: var(--success-color);
          color: var(--white-color);
        }

        .confidence-badge.confidence-medium {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .confidence-badge.confidence-low {
          background: var(--error-color);
          color: var(--white-color);
        }

        .source-badge {
          font-size: 0.7rem;
          padding: 4px 8px;
          border-radius: 12px;
          font-weight: 500;
          text-transform: capitalize;
        }

        .source-badge.source-webform {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .source-badge.source-voice {
          background: var(--create-color);
          color: var(--white-color);
        }

        .source-badge.source-email {
          background: var(--hubspot-color);
          color: var(--white-color);
        }

        .classification-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .classification-details,
        .input-details,
        .contact-info,
        .event-details {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .classification-title,
        .input-title,
        .contact-title,
        .event-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .detail-item {
          margin-bottom: 8px;
        }

        .detail-item:last-child {
          margin-bottom: 0;
        }

        .detail-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .detail-value {
          font-size: 0.9rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .detail-value.routing {
          color: var(--accent-color);
          font-weight: 600;
        }

        .detail-value.reasoning {
          margin: 0;
          line-height: 1.4;
          font-style: italic;
        }

        .review-required {
          display: flex;
          align-items: center;
          gap: 6px;
          background: var(--error-color);
          color: var(--white-color);
          padding: 6px 10px;
          border-radius: 6px;
          font-size: 0.85rem;
          font-weight: 500;
        }

        .product-tags,
        .requirement-tags,
        .location-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .product-tag {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .requirement-tag {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .location-tag {
          background: var(--alt-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .contact-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 8px;
        }

        .contact-row:last-child {
          margin-bottom: 0;
        }

        .contact-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .contact-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .contact-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .classification-metadata {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .metadata-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .metadata-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .metadata-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .metadata-value {
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
          .classifications-grid {
            grid-template-columns: 1fr;
          }
          
          .contact-row,
          .metadata-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .classification-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .product-tags,
          .requirement-tags,
          .location-tags {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      </style>
    `;
  };
}
