export default class CallsSuccess extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/calls/successful";
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
      console.error("Error fetching successful calls:", error);
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
        ${this.getSuccessStats()}
        ${this.getCallsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Successful Calls</h1>
        <p class="subtitle">Calls that completed successfully with positive outcomes</p>
      </div>
    `;
  };

  getSuccessStats = () => {
    if (!this.callsData.items || this.callsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateSuccessStats(this.callsData.items);

    return /* html */ `
      <div class="success-stats">
        <h3>Success Metrics</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalSuccessful}</span>
            <span class="stat-label">Successful</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgDuration}s</span>
            <span class="stat-label">Avg Duration</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">$${stats.totalCost}</span>
            <span class="stat-label">Total Cost</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.answeredCalls}</span>
            <span class="stat-label">Answered</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateSuccessStats = (calls) => {
    const totalSuccessful = calls.length;
    const answeredCalls = calls.filter(call => call.answered_by && call.answered_by !== 'Unknown').length;

    const durations = calls
      .filter(call => call.duration_seconds !== null && call.duration_seconds !== undefined)
      .map(call => call.duration_seconds);

    const avgDuration = durations.length > 0
      ? Math.round(durations.reduce((sum, duration) => sum + duration, 0) / durations.length)
      : 0;

    const costs = calls
      .filter(call => call.cost !== null && call.cost !== undefined)
      .map(call => call.cost);

    const totalCost = costs.length > 0
      ? costs.reduce((sum, cost) => sum + cost, 0).toFixed(2)
      : '0.00';

    return {
      totalSuccessful,
      avgDuration,
      totalCost,
      answeredCalls
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
      <div class="call-card success-card" data-call-id="${call.id}" tabindex="0">
        <div class="call-header">
          <div class="call-info">
            <h3>Success ${call.id.slice(-6)}</h3>
            ${this.getSuccessBadge()}
            ${this.getDurationBadge(call.duration_seconds)}
          </div>
          <div class="success-indicator">
            <span class="success-icon">✅</span>
            ${call.cost ? /* html */ `<span class="call-cost">$${call.cost.toFixed(2)}</span>` : ''}
          </div>
        </div>
        
        <div class="call-body">
          ${this.getCallResults(call)}
          
          ${this.getContactDetails(call)}
          
          ${this.getCallAnalysis(call)}
          
          <div class="call-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Completed</span>
                <span class="metadata-value">${this.formatDate(call.call_completed_at || call.created_at)}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Duration</span>
                <span class="metadata-value success-duration">${this.formatDuration(call.duration_seconds)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getSuccessBadge = () => {
    return /* html */ `<span class="success-badge">Completed</span>`;
  };

  getDurationBadge = (duration) => {
    if (duration === null || duration === undefined) return '';

    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    const formatted = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

    return /* html */ `<span class="duration-badge success-duration">${formatted}</span>`;
  };

  formatDuration = (duration) => {
    if (duration === null || duration === undefined) return 'N/A';

    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  };

  getCallResults = (call) => {
    return /* html */ `
      <div class="call-results">
        <div class="results-title">Call Results</div>
        
        <div class="result-highlights">
          <div class="highlight-item">
            <span class="highlight-label">Status</span>
            <span class="highlight-value status-success">Completed Successfully</span>
          </div>
          
          ${call.answered_by ? /* html */ `
            <div class="highlight-item">
              <span class="highlight-label">Answered By</span>
              <span class="highlight-value answered-by">${call.answered_by}</span>
            </div>
          ` : ''}
          
          ${call.ended_reason ? /* html */ `
            <div class="highlight-item">
              <span class="highlight-label">End Reason</span>
              <span class="highlight-value end-reason">${call.ended_reason}</span>
            </div>
          ` : ''}
        </div>
        
        ${call.summary ? /* html */ `
          <div class="summary-section">
            <span class="result-label">Call Summary</span>
            <p class="summary-text">${call.summary}</p>
          </div>
        ` : ''}
        
        ${call.recording_url ? /* html */ `
          <div class="recording-section">
            <span class="result-label">Recording</span>
            <a href="${call.recording_url}" target="_blank" class="recording-link">
              🎵 Listen to Recording
            </a>
          </div>
        ` : ''}
      </div>
    `;
  };

  getContactDetails = (call) => {
    const contactInfo = [];

    if (call.phone_number) contactInfo.push({ icon: '📞', label: 'Phone', value: call.phone_number });
    if (call.contact_id) contactInfo.push({ icon: '👤', label: 'Contact', value: call.contact_id.slice(-8) });
    if (call.lead_id) contactInfo.push({ icon: '🎯', label: 'Lead', value: call.lead_id.slice(-8) });

    if (contactInfo.length === 0) return '';

    return /* html */ `
      <div class="contact-details">
        <div class="contact-title">Contact Details</div>
        
        <div class="contact-grid">
          ${contactInfo.map(info => /* html */ `
            <div class="contact-item">
              <span class="contact-icon">${info.icon}</span>
              <div class="contact-content">
                <span class="contact-label">${info.label}</span>
                <span class="contact-value">${info.value}</span>
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

  getCallAnalysis = (call) => {
    if (!call.transcript && !call.analysis && !call.classification_payload) {
      return '';
    }

    return /* html */ `
      <div class="call-analysis">
        <div class="analysis-title">Call Analysis</div>
        
        ${call.transcript ? /* html */ `
          <div class="analysis-section">
            <span class="analysis-label">Transcript</span>
            <p class="transcript-text">${this.truncateText(call.transcript, 300)}</p>
          </div>
        ` : ''}
        
        ${call.analysis ? /* html */ `
          <div class="analysis-section">
            <span class="analysis-label">Analysis Results</span>
            <div class="analysis-content">
              ${this.formatAnalysis(call.analysis)}
            </div>
          </div>
        ` : ''}
        
        ${call.classification_payload ? /* html */ `
          <div class="analysis-section">
            <span class="analysis-label">Classification</span>
            <div class="classification-content">
              ${this.formatClassification(call.classification_payload)}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  };

  formatAnalysis = (analysis) => {
    if (typeof analysis === 'string') {
      return /* html */ `<p class="analysis-text">${analysis}</p>`;
    }

    if (typeof analysis === 'object') {
      return /* html */ `<pre class="analysis-json">${JSON.stringify(analysis, null, 2)}</pre>`;
    }

    return /* html */ `<p class="analysis-text">Analysis data available</p>`;
  };

  formatClassification = (classification) => {
    if (typeof classification === 'string') {
      return /* html */ `<p class="classification-text">${classification}</p>`;
    }

    if (typeof classification === 'object') {
      return /* html */ `<pre class="classification-json">${JSON.stringify(classification, null, 2)}</pre>`;
    }

    return /* html */ `<p class="classification-text">Classification data available</p>`;
  };

  truncateText = (text, maxLength) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
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
        <h2>No Successful Calls Found</h2>
        <p>There are no successful calls to display at this time.</p>
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

        .success-card {
          border-left: 4px solid var(--success-color);
        }

        .call-card:hover {
          border-color: var(--success-color);
        }

        .call-card:focus {
          outline: none;
          border-color: var(--success-color);
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

        .success-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .success-icon {
          font-size: 1rem;
        }

        .call-cost {
          font-size: 0.85rem;
          color: var(--success-color);
          font-weight: 600;
        }

        .success-badge {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .duration-badge.success-duration {
          background: var(--success-background);
          color: var(--success-color);
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

        .call-results,
        .contact-details,
        .call-analysis {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .results-title,
        .contact-title,
        .analysis-title {
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

        .highlight-value.status-success {
          color: var(--success-color);
        }

        .highlight-value.answered-by {
          color: var(--accent-color);
        }

        .highlight-value.end-reason {
          color: var(--text-color);
        }

        .summary-section,
        .recording-section {
          margin-top: 8px;
        }

        .result-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .summary-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          color: var(--text-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
        }

        .recording-link {
          color: var(--success-color);
          text-decoration: none;
          font-size: 0.85rem;
          font-weight: 500;
        }

        .recording-link:hover {
          text-decoration: underline;
        }

        .contact-grid {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 8px;
        }

        .contact-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px;
          background: var(--background);
          border-radius: 4px;
        }

        .contact-icon {
          font-size: 1rem;
          width: 24px;
          text-align: center;
        }

        .contact-content {
          display: flex;
          flex-direction: column;
          gap: 2px;
          flex: 1;
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

        .analysis-section {
          margin-bottom: 8px;
        }

        .analysis-section:last-child {
          margin-bottom: 0;
        }

        .analysis-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .transcript-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          color: var(--text-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
          font-family: monospace;
        }

        .analysis-text,
        .classification-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          color: var(--text-color);
        }

        .analysis-json,
        .classification-json {
          margin: 4px 0 0 0;
          font-size: 0.75rem;
          line-height: 1.3;
          color: var(--gray-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
          overflow-x: auto;
          white-space: pre-wrap;
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

        .metadata-value.success-duration {
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

          .result-highlights {
            flex-direction: column;
            gap: 8px;
          }
        }
      </style>
    `;
  };
}
