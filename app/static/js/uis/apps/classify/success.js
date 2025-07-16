export default class ClassifySuccess extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/classify/successful";
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
      console.error("Error fetching successful classifications:", error);
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
        ${this.getSuccessStats()}
        ${this.getClassificationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Successful Classifications</h1>
        <p class="subtitle">Classifications processed successfully with high confidence</p>
      </div>
    `;
  };

  getSuccessStats = () => {
    if (!this.classifyData.items || this.classifyData.items.length === 0) {
      return '';
    }

    const stats = this.calculateSuccessStats(this.classifyData.items);

    return /* html */ `
      <div class="success-stats">
        <h3>Success Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalSuccessful}</span>
            <span class="stat-label">Successful</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.highConfidenceCount}</span>
            <span class="stat-label">High Confidence</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgConfidence}%</span>
            <span class="stat-label">Avg Confidence</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.servicesLeads}</span>
            <span class="stat-label">Services/Leads</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateSuccessStats = (classifications) => {
    const totalSuccessful = classifications.length;
    const highConfidenceCount = classifications.filter(c =>
      c.classification?.confidence >= 0.8
    ).length;

    const confidences = classifications
      .filter(c => c.classification?.confidence !== null && c.classification?.confidence !== undefined)
      .map(c => c.classification.confidence);

    const avgConfidence = confidences.length > 0
      ? Math.round((confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length) * 100)
      : 0;

    const servicesLeads = classifications.filter(c =>
      c.classification?.lead_type === 'Services' || c.classification?.lead_type === 'Leads'
    ).length;

    return {
      totalSuccessful,
      highConfidenceCount,
      avgConfidence,
      servicesLeads
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
      <div class="classification-card success-card" data-classification-id="${classification._id}" tabindex="0">
        <div class="classification-header">
          <div class="classification-info">
            <h3>Success ${classification._id.slice(-6)}</h3>
            ${this.getLeadTypeBadge(classif?.lead_type)}
            ${this.getConfidenceBadge(classif?.confidence)}
          </div>
          <div class="success-indicator">
            <span class="success-icon">✅</span>
            <span class="source-badge source-${input?.source}">${input?.source || 'unknown'}</span>
          </div>
        </div>
        
        <div class="classification-body">
          ${this.getClassificationResults(classif)}
          
          ${this.getKeyDetails(input)}
          
          ${this.getContactSummary(input)}
          
          <div class="classification-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Processed</span>
                <span class="metadata-value">${this.formatDate(classification.created_at)}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Success Rate</span>
                <span class="metadata-value success-rate">${this.getSuccessRate(classif?.confidence)}%</span>
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
    return /* html */ `<span class="confidence-badge confidence-high">${percentage}%</span>`;
  };

  getSuccessRate = (confidence) => {
    if (confidence === null || confidence === undefined) return 0;
    return Math.round(confidence * 100);
  };

  getClassificationResults = (classif) => {
    if (!classif) return '';

    return /* html */ `
      <div class="classification-results">
        <div class="results-title">Classification Results</div>
        
        <div class="result-highlights">
          <div class="highlight-item">
            <span class="highlight-label">Lead Type</span>
            <span class="highlight-value type-${classif.lead_type?.toLowerCase()}">${classif.lead_type}</span>
          </div>
          
          ${classif.routing_suggestion ? /* html */ `
            <div class="highlight-item">
              <span class="highlight-label">Routing</span>
              <span class="highlight-value routing">${classif.routing_suggestion}</span>
            </div>
          ` : ''}
        </div>
        
        ${classif.reasoning ? /* html */ `
          <div class="reasoning-section">
            <span class="detail-label">AI Reasoning</span>
            <p class="reasoning-text">${classif.reasoning}</p>
          </div>
        ` : ''}
      </div>
    `;
  };

  getKeyDetails = (input) => {
    if (!input) return '';

    const keyDetails = [];

    if (input.intended_use) keyDetails.push({ label: 'Intended Use', value: input.intended_use });
    if (input.event_type) keyDetails.push({ label: 'Event Type', value: input.event_type });
    if (input.required_stalls) keyDetails.push({ label: 'Stalls Needed', value: input.required_stalls });
    if (input.guest_count) keyDetails.push({ label: 'Guest Count', value: input.guest_count });

    if (keyDetails.length === 0) return '';

    return /* html */ `
      <div class="key-details">
        <div class="details-title">Key Details</div>
        
        <div class="details-grid">
          ${keyDetails.map(detail => /* html */ `
            <div class="detail-card">
              <span class="detail-label">${detail.label}</span>
              <span class="detail-value">${detail.value}</span>
            </div>
          `).join('')}
        </div>
        
        ${this.getProductAndRequirements(input)}
      </div>
    `;
  };

  getProductAndRequirements = (input) => {
    const requirements = [];

    if (input.ada_required) requirements.push('ADA Required');
    if (input.duration_days) requirements.push(`${input.duration_days} days`);
    if (input.is_local) requirements.push('Local Service');

    if (!input.product_interest && requirements.length === 0) return '';

    return /* html */ `
      <div class="products-requirements">
        ${input.product_interest && input.product_interest.length > 0 ? /* html */ `
          <div class="detail-section">
            <span class="detail-label">Products</span>
            <div class="product-tags">
              ${input.product_interest.map(product => /* html */ `
                <span class="product-tag">${product}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
        
        ${requirements.length > 0 ? /* html */ `
          <div class="detail-section">
            <span class="detail-label">Requirements</span>
            <div class="requirement-tags">
              ${requirements.map(req => /* html */ `
                <span class="requirement-tag">${req}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  };

  getContactSummary = (input) => {
    if (!input.firstname && !input.email && !input.company && !input.event_location_description) {
      return '';
    }

    return /* html */ `
      <div class="contact-summary">
        <div class="summary-title">Contact Summary</div>
        
        <div class="summary-grid">
          ${input.firstname || input.lastname ? /* html */ `
            <div class="summary-item">
              <span class="summary-icon">👤</span>
              <span class="summary-text">${[input.firstname, input.lastname].filter(n => n).join(' ')}</span>
            </div>
          ` : ''}
          
          ${input.company ? /* html */ `
            <div class="summary-item">
              <span class="summary-icon">🏢</span>
              <span class="summary-text">${input.company}</span>
            </div>
          ` : ''}
          
          ${input.email ? /* html */ `
            <div class="summary-item">
              <span class="summary-icon">📧</span>
              <span class="summary-text">${input.email}</span>
            </div>
          ` : ''}
          
          ${input.event_location_description ? /* html */ `
            <div class="summary-item">
              <span class="summary-icon">📍</span>
              <span class="summary-text">${input.event_location_description}</span>
            </div>
          ` : ''}
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
        <h2>No Successful Classifications Found</h2>
        <p>There are no successful classifications to display at this time.</p>
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
          padding: 15px 0;
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .header {
          display: flex;
          flex-direction: column;
          flex-flow: column;
          gap: 0;
        }

        .header h1 {
          font-size: 24px;
          font-weight: 600;
          color: var(--title-color);
          margin: 0;
          padding: 0;
          line-height: 1.4;
        }

        .subtitle {
          font-size: 14px;
          color: var(--gray-color);
          margin: 0;
          padding: 0;
          line-height: 1.4;
        }

        .success-stats {
          background: var(--success-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .success-stats h3 {
          margin: 0 0 12px 0;
          color: var(--success-color);
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
          color: var(--success-color);
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
        }

        .success-card {
          border-left: 4px solid var(--success-color);
        }

        .classification-card:hover {
          border-color: var(--success-color);
        }

        .classification-card:focus {
          outline: none;
          border-color: var(--success-color);
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

        .success-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .success-icon {
          font-size: 1rem;
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

        .confidence-badge.confidence-high {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
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

        .classification-results,
        .key-details,
        .contact-summary {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .results-title,
        .details-title,
        .summary-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .result-highlights {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 8px;
        }

        .highlight-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .highlight-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .highlight-value {
          font-size: 0.9rem;
          font-weight: 600;
        }

        .highlight-value.type-services {
          color: var(--success-color);
        }

        .highlight-value.type-leads {
          color: var(--alt-color);
        }

        .highlight-value.type-logistics {
          color: var(--create-color);
        }

        .highlight-value.routing {
          color: var(--accent-color);
        }

        .reasoning-section {
          margin-top: 8px;
        }

        .reasoning-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          font-style: italic;
          color: var(--text-color);
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 8px;
          margin-bottom: 8px;
        }

        .detail-card {
          background: var(--background);
          border-radius: 4px;
          padding: 8px;
          text-align: center;
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
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .products-requirements {
          margin-top: 8px;
        }

        .detail-section {
          margin-bottom: 8px;
        }

        .detail-section:last-child {
          margin-bottom: 0;
        }

        .product-tags,
        .requirement-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 4px;
        }

        .product-tag {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .requirement-tag {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .summary-grid {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .summary-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 0;
        }

        .summary-icon {
          font-size: 0.9rem;
          width: 20px;
          text-align: center;
        }

        .summary-text {
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

        .metadata-value.success-rate {
          color: var(--success-color);
          font-weight: 600;
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
          border-color: var(--success-color);
          color: var(--success-color);
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
          border-top: 3px solid var(--success-color);
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

          .details-grid {
            grid-template-columns: 1fr;
          }

          .result-highlights {
            flex-direction: column;
            gap: 8px;
          }
        }
      </style>
    `;
  };
}
