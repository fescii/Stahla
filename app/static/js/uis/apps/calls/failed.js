export default class CallsFailed extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/calls/failed";
    this.callsData = null;
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
    this.fetchCalls();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchCalls = async (page = 1) => {
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
        this.callsData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.callsData = response.data;
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching failed calls:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.callsData = null;
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
          this.fetchCalls(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchCalls(this.currentPage + 1);
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

    if (this._empty || !this.callsData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getFailureStats()}
        ${this.getCallsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Failed Calls</h1>
        <p class="subtitle">Calls that encountered errors or failed to complete successfully</p>
      </div>
    `;
  };

  getFailureStats = () => {
    if (!this.callsData.items || this.callsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateFailureStats(this.callsData.items);

    return /* html */ `
      <div class="failure-stats">
        <h3>Failure Analysis</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalFailed}</span>
            <span class="stat-label">Failed</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.retryCount}</span>
            <span class="stat-label">Retries</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.errorTypes}</span>
            <span class="stat-label">Error Types</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">$${stats.lostCost}</span>
            <span class="stat-label">Lost Cost</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateFailureStats = (calls) => {
    const totalFailed = calls.length;
    const retryCount = calls.reduce((sum, call) => sum + (call.retry_count || 0), 0);

    const errorTypesSet = new Set();
    calls.forEach(call => {
      if (call.error_message) {
        // Categorize errors
        const error = call.error_message.toLowerCase();
        if (error.includes('timeout') || error.includes('connection')) {
          errorTypesSet.add('Connection');
        } else if (error.includes('no answer') || error.includes('busy')) {
          errorTypesSet.add('No Answer');
        } else if (error.includes('invalid') || error.includes('format')) {
          errorTypesSet.add('Invalid Format');
        } else if (error.includes('rate') || error.includes('limit')) {
          errorTypesSet.add('Rate Limit');
        } else {
          errorTypesSet.add('System Error');
        }
      } else {
        errorTypesSet.add('Unknown Error');
      }
    });

    const costs = calls
      .filter(call => call.cost !== null && call.cost !== undefined)
      .map(call => call.cost);

    const lostCost = costs.length > 0
      ? costs.reduce((sum, cost) => sum + cost, 0).toFixed(2)
      : '0.00';

    return {
      totalFailed,
      retryCount,
      errorTypes: errorTypesSet.size,
      lostCost
    };
  };

  getCallsList = () => {
    if (!this.callsData.items || this.callsData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="calls-grid">
        ${this.callsData.items.map(call => this.getCallCard(call)).join('')}
      </div>
    `;
  };

  getCallCard = (call) => {
    return /* html */ `
      <div class="call-card failed-card" data-call-id="${call.id}" tabindex="0">
        <div class="call-header">
          <div class="call-info">
            <h3>Failed ${call.id.slice(-6)}</h3>
            ${this.getFailureBadge(call.status)}
            ${this.getRetryBadge(call.retry_count)}
          </div>
          <div class="failure-indicator">
            <span class="failure-icon">❌</span>
            ${call.cost ? /* html */ `<span class="call-cost lost-cost">-$${call.cost.toFixed(2)}</span>` : ''}
          </div>
        </div>
        
        <div class="call-body">
          ${this.getErrorDetails(call)}
          
          ${this.getCallAttemptInfo(call)}
          
          ${this.getRetryAnalysis(call)}
          
          <div class="call-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Failed At</span>
                <span class="metadata-value">${this.formatDate(call.created_at)}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Retryable</span>
                <span class="metadata-value retry-status">${this.isRetryable(call) ? 'Yes' : 'No'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getFailureBadge = (status) => {
    if (!status) return '';

    const statusClass = this.getStatusClass(status);
    return /* html */ `<span class="failure-badge status-${statusClass}">${status}</span>`;
  };

  getStatusClass = (status) => {
    switch (status) {
      case 'failed': return 'failed';
      case 'cancelled': return 'cancelled';
      case 'no_answer': return 'no-answer';
      case 'busy': return 'busy';
      default: return 'unknown';
    }
  };

  getRetryBadge = (retryCount) => {
    if (!retryCount || retryCount === 0) return '';

    return /* html */ `<span class="retry-badge">${retryCount} retries</span>`;
  };

  isRetryable = (call) => {
    if (!call.error_message) return false;

    const error = call.error_message.toLowerCase();
    return error.includes('timeout') ||
      error.includes('connection') ||
      error.includes('busy') ||
      error.includes('rate') ||
      error.includes('temporary');
  };

  getErrorDetails = (call) => {
    return /* html */ `
      <div class="error-details">
        <div class="error-title">Error Details</div>
        
        <div class="error-summary">
          <div class="error-item">
            <span class="error-label">Status</span>
            <span class="error-value status-${this.getStatusClass(call.status)}">${call.status}</span>
          </div>
          
          ${call.ended_reason ? /* html */ `
            <div class="error-item">
              <span class="error-label">End Reason</span>
              <span class="error-value end-reason">${call.ended_reason}</span>
            </div>
          ` : ''}
        </div>
        
        ${call.error_message ? /* html */ `
          <div class="error-message-section">
            <span class="error-label">Error Message</span>
            <p class="error-message">${call.error_message}</p>
          </div>
        ` : ''}
      </div>
    `;
  };

  getCallAttemptInfo = (call) => {
    const attemptInfo = [];

    if (call.phone_number) attemptInfo.push({ icon: '📞', label: 'Phone', value: call.phone_number });
    if (call.contact_id) attemptInfo.push({ icon: '👤', label: 'Contact', value: call.contact_id.slice(-8) });
    if (call.lead_id) attemptInfo.push({ icon: '🎯', label: 'Lead', value: call.lead_id.slice(-8) });

    if (attemptInfo.length === 0) return '';

    return /* html */ `
      <div class="attempt-info">
        <div class="attempt-title">Call Attempt Information</div>
        
        <div class="attempt-grid">
          ${attemptInfo.map(info => /* html */ `
            <div class="attempt-item">
              <span class="attempt-icon">${info.icon}</span>
              <div class="attempt-content">
                <span class="attempt-label">${info.label}</span>
                <span class="attempt-value">${info.value}</span>
              </div>
            </div>
          `).join('')}
        </div>
        
        ${this.getCallConfiguration(call)}
      </div>
    `;
  };

  getCallConfiguration = (call) => {
    const config = [];

    if (call.task) config.push({ label: 'Task', value: call.task });
    if (call.pathway_id_used) config.push({ label: 'Pathway', value: call.pathway_id_used.slice(-8) });
    if (call.voice_id) config.push({ label: 'Voice', value: call.voice_id });
    if (call.max_duration) config.push({ label: 'Max Duration', value: `${call.max_duration}m` });

    if (config.length === 0) return '';

    return /* html */ `
      <div class="call-config">
        <div class="config-grid">
          ${config.map(item => /* html */ `
            <div class="config-item">
              <span class="config-label">${item.label}</span>
              <span class="config-value">${item.value}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  };

  getRetryAnalysis = (call) => {
    const analysis = this.analyzeFailure(call);

    return /* html */ `
      <div class="retry-analysis">
        <div class="analysis-title">Failure Analysis</div>
        
        <div class="analysis-content">
          <div class="analysis-item">
            <span class="analysis-label">Category</span>
            <span class="analysis-value category-${analysis.category.toLowerCase().replace(' ', '-')}">${analysis.category}</span>
          </div>
          
          <div class="analysis-item">
            <span class="analysis-label">Retryable</span>
            <span class="analysis-value retryable-${analysis.retryable ? 'yes' : 'no'}">${analysis.retryable ? 'Yes' : 'No'}</span>
          </div>
          
          ${call.retry_count > 0 ? /* html */ `
            <div class="analysis-item">
              <span class="analysis-label">Retry Count</span>
              <span class="analysis-value retry-count">${call.retry_count}</span>
            </div>
          ` : ''}
        </div>
        
        ${analysis.recommendation ? /* html */ `
          <div class="recommendation-section">
            <span class="analysis-label">Recommendation</span>
            <p class="recommendation-text">${analysis.recommendation}</p>
          </div>
        ` : ''}
        
        ${call.retry_reason ? /* html */ `
          <div class="retry-reason-section">
            <span class="analysis-label">Retry Reason</span>
            <p class="retry-reason-text">${call.retry_reason}</p>
          </div>
        ` : ''}
      </div>
    `;
  };

  analyzeFailure = (call) => {
    if (!call.error_message) {
      return {
        category: 'Unknown Error',
        retryable: false,
        recommendation: 'Review call logs for more details'
      };
    }

    const error = call.error_message.toLowerCase();

    if (error.includes('timeout') || error.includes('connection')) {
      return {
        category: 'Connection Error',
        retryable: true,
        recommendation: 'Retry the call after checking network connectivity'
      };
    }

    if (error.includes('no answer') || error.includes('not answered')) {
      return {
        category: 'No Answer',
        retryable: true,
        recommendation: 'Try calling at a different time or use alternative contact methods'
      };
    }

    if (error.includes('busy')) {
      return {
        category: 'Line Busy',
        retryable: true,
        recommendation: 'Retry after a few minutes'
      };
    }

    if (error.includes('invalid') || error.includes('format')) {
      return {
        category: 'Invalid Number',
        retryable: false,
        recommendation: 'Verify and correct the phone number format'
      };
    }

    if (error.includes('rate') || error.includes('limit')) {
      return {
        category: 'Rate Limit',
        retryable: true,
        recommendation: 'Wait before retrying or reduce call frequency'
      };
    }

    if (error.includes('cancelled') || error.includes('aborted')) {
      return {
        category: 'Call Cancelled',
        retryable: false,
        recommendation: 'Check if call was manually cancelled or if there are system issues'
      };
    }

    return {
      category: 'System Error',
      retryable: false,
      recommendation: 'Contact system administrator for technical support'
    };
  };

  getPagination = () => {
    if (!this.callsData || this.callsData.total <= this.callsData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.callsData.total / this.callsData.limit)}
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
        <h2>No Failed Calls Found</h2>
        <p>There are no failed calls to display at this time.</p>
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

        .calls-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
        }

        .call-card {
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

        .call-card:hover {
          border-color: var(--danger-color);
        }

        .call-card:focus {
          outline: none;
          border-color: var(--danger-color);
        }

        .call-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .call-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .call-info h3 {
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

        .lost-cost {
          font-size: 0.85rem;
          color: var(--danger-color);
          font-weight: 600;
        }

        .failure-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          text-transform: capitalize;
        }

        .failure-badge.status-failed {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .failure-badge.status-cancelled {
          background: var(--warning-color);
          color: var(--white-color);
        }

        .failure-badge.status-no-answer {
          background: var(--gray-color);
          color: var(--white-color);
        }

        .failure-badge.status-busy {
          background: var(--create-color);
          color: var(--white-color);
        }

        .retry-badge {
          background: var(--warning-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .call-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .error-details,
        .attempt-info,
        .retry-analysis {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .error-title,
        .attempt-title,
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

        .error-value.status-failed {
          color: var(--danger-color);
        }

        .error-value.status-cancelled {
          color: var(--warning-color);
        }

        .error-value.status-no-answer {
          color: var(--gray-color);
        }

        .error-value.status-busy {
          color: var(--create-color);
        }

        .error-value.end-reason {
          color: var(--text-color);
        }

        .error-message-section {
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

        .attempt-grid {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 8px;
        }

        .attempt-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px;
          background: var(--background);
          border-radius: 4px;
        }

        .attempt-icon {
          font-size: 1rem;
          width: 24px;
          text-align: center;
        }

        .attempt-content {
          display: flex;
          flex-direction: column;
          gap: 2px;
          flex: 1;
        }

        .attempt-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .attempt-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .call-config {
          margin-top: 8px;
        }

        .config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 8px;
        }

        .config-item {
          background: var(--background);
          border-radius: 4px;
          padding: 8px;
          text-align: center;
        }

        .config-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .config-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
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

        .analysis-value.category-connection-error {
          color: var(--warning-color);
        }

        .analysis-value.category-no-answer {
          color: var(--gray-color);
        }

        .analysis-value.category-line-busy {
          color: var(--create-color);
        }

        .analysis-value.category-invalid-number {
          color: var(--danger-color);
        }

        .analysis-value.category-rate-limit {
          color: var(--accent-color);
        }

        .analysis-value.category-call-cancelled {
          color: var(--warning-color);
        }

        .analysis-value.category-system-error {
          color: var(--danger-color);
        }

        .analysis-value.retryable-yes {
          color: var(--success-color);
        }

        .analysis-value.retryable-no {
          color: var(--danger-color);
        }

        .analysis-value.retry-count {
          color: var(--warning-color);
        }

        .recommendation-section,
        .retry-reason-section {
          margin-top: 8px;
          width: 100%;
        }

        .recommendation-text,
        .retry-reason-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          font-style: italic;
          color: var(--text-color);
        }

        .call-metadata {
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
          .calls-grid {
            grid-template-columns: 1fr;
          }
          
          .metadata-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .call-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .config-grid {
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
