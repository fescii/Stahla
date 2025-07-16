export default class ClassifyFailed extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/classify/failed";
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
      console.error("Error fetching failed classifications:", error);
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
        ${this.getFailureStats()}
        ${this.getClassificationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Failed Classifications</h1>
        <p class="subtitle">Classifications that encountered processing errors or failures</p>
      </div>
    `;
  };

  getFailureStats = () => {
    if (!this.classifyData.items || this.classifyData.items.length === 0) {
      return '';
    }

    const stats = this.calculateFailureStats(this.classifyData.items);

    return /* html */ `
      <div class="failure-stats">
        <h3>Failure Analysis</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalFailed}</span>
            <span class="stat-label">Failed</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.errorTypes}</span>
            <span class="stat-label">Error Types</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.retryableErrors}</span>
            <span class="stat-label">Retryable</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.dataErrors}</span>
            <span class="stat-label">Data Issues</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateFailureStats = (classifications) => {
    const totalFailed = classifications.length;
    const errorTypesSet = new Set();
    let retryableErrors = 0;
    let dataErrors = 0;

    classifications.forEach(c => {
      if (c.error?.error_type) {
        errorTypesSet.add(c.error.error_type);

        if (c.error.error_type.includes('timeout') ||
          c.error.error_type.includes('connection') ||
          c.error.error_type.includes('rate_limit')) {
          retryableErrors++;
        }

        if (c.error.error_type.includes('validation') ||
          c.error.error_type.includes('missing') ||
          c.error.error_type.includes('invalid')) {
          dataErrors++;
        }
      }
    });

    return {
      totalFailed,
      errorTypes: errorTypesSet.size,
      retryableErrors,
      dataErrors
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
    const error = classification.error;
    const input = classification.input;

    return /* html */ `
      <div class="classification-card failed-card" data-classification-id="${classification._id}" tabindex="0">
        <div class="classification-header">
          <div class="classification-info">
            <h3>Failed ${classification._id.slice(-6)}</h3>
            ${this.getErrorTypeBadge(error?.error_type)}
            ${this.getSeverityBadge(error?.severity)}
          </div>
          <div class="failure-indicator">
            <span class="failure-icon">❌</span>
            <span class="source-badge source-${input?.source}">${input?.source || 'unknown'}</span>
          </div>
        </div>
        
        <div class="classification-body">
          ${this.getErrorDetails(error)}
          
          ${this.getInputSummary(input)}
          
          ${this.getFailureAnalysis(error)}
          
          <div class="classification-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Failed At</span>
                <span class="metadata-value">${this.formatDate(classification.created_at)}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Retryable</span>
                <span class="metadata-value retry-status">${this.isRetryable(error?.error_type) ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getErrorTypeBadge = (errorType) => {
    if (!errorType) return '';

    const badgeClass = this.getErrorTypeClass(errorType);
    return /* html */ `<span class="error-type-badge type-${badgeClass}">${errorType}</span>`;
  };

  getErrorTypeClass = (errorType) => {
    if (!errorType) return 'unknown';

    const lowerType = errorType.toLowerCase();
    if (lowerType.includes('timeout') || lowerType.includes('connection')) return 'connection';
    if (lowerType.includes('validation') || lowerType.includes('invalid')) return 'validation';
    if (lowerType.includes('missing') || lowerType.includes('required')) return 'data';
    if (lowerType.includes('rate') || lowerType.includes('limit')) return 'rate';
    return 'system';
  };

  getSeverityBadge = (severity) => {
    if (!severity) return '';

    return /* html */ `<span class="severity-badge severity-${severity.toLowerCase()}">${severity}</span>`;
  };

  isRetryable = (errorType) => {
    if (!errorType) return false;
    const lowerType = errorType.toLowerCase();
    return lowerType.includes('timeout') ||
      lowerType.includes('connection') ||
      lowerType.includes('rate_limit') ||
      lowerType.includes('temporary');
  };

  getErrorDetails = (error) => {
    if (!error) return '';

    return /* html */ `
      <div class="error-details">
        <div class="error-title">Error Details</div>
        
        <div class="error-summary">
          ${error.error_type ? /* html */ `
            <div class="error-item">
              <span class="error-label">Error Type</span>
              <span class="error-value type-${this.getErrorTypeClass(error.error_type)}">${error.error_type}</span>
            </div>
          ` : ''}
          
          ${error.severity ? /* html */ `
            <div class="error-item">
              <span class="error-label">Severity</span>
              <span class="error-value severity-${error.severity.toLowerCase()}">${error.severity}</span>
            </div>
          ` : ''}
        </div>
        
        ${error.error_message ? /* html */ `
          <div class="error-message-section">
            <span class="error-label">Error Message</span>
            <p class="error-message">${error.error_message}</p>
          </div>
        ` : ''}
        
        ${error.stack_trace ? /* html */ `
          <div class="stack-trace-section">
            <span class="error-label">Stack Trace</span>
            <pre class="stack-trace">${error.stack_trace}</pre>
          </div>
        ` : ''}
      </div>
    `;
  };

  getInputSummary = (input) => {
    if (!input) return '';

    const keyFields = [];

    if (input.firstname || input.lastname) {
      keyFields.push({ label: 'Contact', value: [input.firstname, input.lastname].filter(n => n).join(' ') });
    }
    if (input.email) keyFields.push({ label: 'Email', value: input.email });
    if (input.company) keyFields.push({ label: 'Company', value: input.company });
    if (input.intended_use) keyFields.push({ label: 'Intended Use', value: input.intended_use });
    if (input.event_type) keyFields.push({ label: 'Event Type', value: input.event_type });

    if (keyFields.length === 0) return '';

    return /* html */ `
      <div class="input-summary">
        <div class="input-title">Input Data Summary</div>
        
        <div class="input-grid">
          ${keyFields.map(field => /* html */ `
            <div class="input-field">
              <span class="field-label">${field.label}</span>
              <span class="field-value">${field.value}</span>
            </div>
          `).join('')}
        </div>
        
        ${this.getAdditionalInputDetails(input)}
      </div>
    `;
  };

  getAdditionalInputDetails = (input) => {
    const details = [];

    if (input.required_stalls) details.push(`${input.required_stalls} stalls`);
    if (input.guest_count) details.push(`${input.guest_count} guests`);
    if (input.duration_days) details.push(`${input.duration_days} days`);
    if (input.ada_required) details.push('ADA required');
    if (input.is_local) details.push('Local service');

    if (details.length === 0 && (!input.product_interest || input.product_interest.length === 0)) {
      return '';
    }

    return /* html */ `
      <div class="additional-details">
        ${details.length > 0 ? /* html */ `
          <div class="detail-tags">
            ${details.map(detail => /* html */ `
              <span class="detail-tag">${detail}</span>
            `).join('')}
          </div>
        ` : ''}
        
        ${input.product_interest && input.product_interest.length > 0 ? /* html */ `
          <div class="products-section">
            <span class="products-label">Products of Interest</span>
            <div class="product-tags">
              ${input.product_interest.map(product => /* html */ `
                <span class="product-tag">${product}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  };

  getFailureAnalysis = (error) => {
    if (!error) return '';

    const analysis = this.analyzeFailure(error);

    return /* html */ `
      <div class="failure-analysis">
        <div class="analysis-title">Failure Analysis</div>
        
        <div class="analysis-content">
          <div class="analysis-item">
            <span class="analysis-label">Category</span>
            <span class="analysis-value category-${analysis.category}">${analysis.category}</span>
          </div>
          
          <div class="analysis-item">
            <span class="analysis-label">Retryable</span>
            <span class="analysis-value retry-${analysis.retryable ? 'yes' : 'no'}">${analysis.retryable ? 'Yes' : 'No'}</span>
          </div>
          
          ${analysis.recommendation ? /* html */ `
            <div class="recommendation-section">
              <span class="analysis-label">Recommendation</span>
              <p class="recommendation-text">${analysis.recommendation}</p>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  };

  analyzeFailure = (error) => {
    if (!error || !error.error_type) {
      return {
        category: 'Unknown',
        retryable: false,
        recommendation: 'Review error logs for more details'
      };
    }

    const errorType = error.error_type.toLowerCase();

    if (errorType.includes('timeout') || errorType.includes('connection')) {
      return {
        category: 'Network',
        retryable: true,
        recommendation: 'Retry the classification after a brief delay'
      };
    }

    if (errorType.includes('validation') || errorType.includes('invalid')) {
      return {
        category: 'Data Validation',
        retryable: false,
        recommendation: 'Check input data format and required fields'
      };
    }

    if (errorType.includes('missing') || errorType.includes('required')) {
      return {
        category: 'Missing Data',
        retryable: false,
        recommendation: 'Ensure all required fields are provided'
      };
    }

    if (errorType.includes('rate') || errorType.includes('limit')) {
      return {
        category: 'Rate Limiting',
        retryable: true,
        recommendation: 'Wait before retrying or reduce request frequency'
      };
    }

    return {
      category: 'System Error',
      retryable: false,
      recommendation: 'Contact system administrator for assistance'
    };
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
        <h2>No Failed Classifications Found</h2>
        <p>There are no failed classifications to display at this time.</p>
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
          color: var(--danger-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
        }

        .failure-stats {
          background: var(--danger-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .failure-stats h3 {
          margin: 0 0 12px 0;
          color: var(--danger-color);
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
          color: var(--danger-color);
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

        .failed-card {
          border-left: 4px solid var(--danger-color);
        }

        .classification-card:hover {
          border-color: var(--danger-color);
        }

        .classification-card:focus {
          outline: none;
          border-color: var(--danger-color);
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

        .failure-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .failure-icon {
          font-size: 1rem;
        }

        .error-type-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .error-type-badge.type-connection {
          background: var(--warning-color);
          color: var(--white-color);
        }

        .error-type-badge.type-validation {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .error-type-badge.type-data {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .error-type-badge.type-rate {
          background: var(--create-color);
          color: var(--white-color);
        }

        .error-type-badge.type-system {
          background: var(--gray-color);
          color: var(--white-color);
        }

        .severity-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .severity-badge.severity-high {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .severity-badge.severity-medium {
          background: var(--warning-color);
          color: var(--white-color);
        }

        .severity-badge.severity-low {
          background: var(--success-color);
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

        .error-details,
        .input-summary,
        .failure-analysis {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .error-title,
        .input-title,
        .analysis-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .error-summary {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 8px;
        }

        .error-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .error-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .error-value {
          font-size: 0.9rem;
          font-weight: 600;
        }

        .error-value.type-connection {
          color: var(--warning-color);
        }

        .error-value.type-validation {
          color: var(--danger-color);
        }

        .error-value.type-data {
          color: var(--accent-color);
        }

        .error-value.type-rate {
          color: var(--create-color);
        }

        .error-value.type-system {
          color: var(--gray-color);
        }

        .error-value.severity-high {
          color: var(--danger-color);
        }

        .error-value.severity-medium {
          color: var(--warning-color);
        }

        .error-value.severity-low {
          color: var(--success-color);
        }

        .error-message-section,
        .stack-trace-section {
          margin-top: 8px;
        }

        .error-message {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          color: var(--text-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
        }

        .stack-trace {
          margin: 4px 0 0 0;
          font-size: 0.75rem;
          line-height: 1.3;
          color: var(--gray-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
          overflow-x: auto;
          white-space: pre-wrap;
          font-family: monospace;
        }

        .input-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 8px;
          margin-bottom: 8px;
        }

        .input-field {
          background: var(--background);
          border-radius: 4px;
          padding: 8px;
          text-align: center;
        }

        .field-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .field-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .additional-details {
          margin-top: 8px;
        }

        .detail-tags,
        .product-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 4px;
        }

        .detail-tag {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .product-tag {
          background: var(--create-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .products-section {
          margin-top: 8px;
        }

        .products-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .analysis-content {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }

        .analysis-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .analysis-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .analysis-value {
          font-size: 0.9rem;
          font-weight: 600;
        }

        .analysis-value.category-network {
          color: var(--warning-color);
        }

        .analysis-value.category-data {
          color: var(--accent-color);
        }

        .analysis-value.category-missing {
          color: var(--danger-color);
        }

        .analysis-value.category-rate {
          color: var(--create-color);
        }

        .analysis-value.category-system {
          color: var(--gray-color);
        }

        .analysis-value.retry-yes {
          color: var(--success-color);
        }

        .analysis-value.retry-no {
          color: var(--danger-color);
        }

        .recommendation-section {
          margin-top: 8px;
          width: 100%;
        }

        .recommendation-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          font-style: italic;
          color: var(--text-color);
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

        .metadata-value.retry-status {
          color: var(--text-color);
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
          border-color: var(--danger-color);
          color: var(--danger-color);
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
          border-top: 3px solid var(--danger-color);
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

          .input-grid {
            grid-template-columns: 1fr;
          }

          .error-summary,
          .analysis-content {
            flex-direction: column;
            gap: 8px;
          }
        }
      </style>
    `;
  };
}
