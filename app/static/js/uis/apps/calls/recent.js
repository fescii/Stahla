export default class CallsRecent extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/calls/recent";
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
      console.error("Error fetching recent calls:", error);
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
        ${this.getCallsStats()}
        ${this.getCallsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Recent Calls</h1>
        <p class="subtitle">Most recently processed calls with latest activity</p>
      </div>
    `;
  };

  getCallsStats = () => {
    if (!this.callsData.items || this.callsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateCallsStats(this.callsData.items);

    return /* html */ `
      <div class="calls-stats">
        <h3>Recent Activity Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalCalls}</span>
            <span class="stat-label">Total Calls</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.completedCalls}</span>
            <span class="stat-label">Completed</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgDuration}s</span>
            <span class="stat-label">Avg Duration</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">$${stats.totalCost}</span>
            <span class="stat-label">Total Cost</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateCallsStats = (calls) => {
    const totalCalls = calls.length;
    const completedCalls = calls.filter(call => call.status === 'completed').length;

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
      totalCalls,
      completedCalls,
      avgDuration,
      totalCost
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
      <div class="call-card recent-card" data-call-id="${call.id}" tabindex="0">
        <div class="call-header">
          <div class="call-info">
            <h3>Call ${call.id.slice(-6)}</h3>
            ${this.getStatusBadge(call.status)}
            ${this.getDurationBadge(call.duration_seconds)}
          </div>
          <div class="call-meta">
            <span class="call-time">${this.formatDate(call.created_at)}</span>
            ${call.cost ? /* html */ `<span class="call-cost">$${call.cost.toFixed(2)}</span>` : ''}
          </div>
        </div>
        
        <div class="call-body">
          ${this.getCallDetails(call)}
          
          ${this.getContactInfo(call)}
          
          ${this.getCallResults(call)}
          
          <div class="call-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Phone</span>
                <span class="metadata-value">${call.phone_number || 'N/A'}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Answered By</span>
                <span class="metadata-value">${call.answered_by || 'Unknown'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getStatusBadge = (status) => {
    if (!status) return '';

    const statusClass = this.getStatusClass(status);
    return /* html */ `<span class="status-badge status-${statusClass}">${status}</span>`;
  };

  getStatusClass = (status) => {
    switch (status) {
      case 'completed': return 'success';
      case 'failed': return 'failed';
      case 'cancelled': return 'cancelled';
      case 'no_answer': return 'no-answer';
      case 'busy': return 'busy';
      case 'in_progress': return 'progress';
      case 'pending': return 'pending';
      default: return 'unknown';
    }
  };

  getDurationBadge = (duration) => {
    if (duration === null || duration === undefined) return '';

    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    const formatted = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

    return /* html */ `<span class="duration-badge">${formatted}</span>`;
  };

  getCallDetails = (call) => {
    const details = [];

    if (call.task) details.push({ label: 'Task', value: call.task });
    if (call.pathway_id_used) details.push({ label: 'Pathway', value: call.pathway_id_used.slice(-8) });
    if (call.voice_id) details.push({ label: 'Voice', value: call.voice_id });
    if (call.ended_reason) details.push({ label: 'End Reason', value: call.ended_reason });

    if (details.length === 0) return '';

    return /* html */ `
      <div class="call-details">
        <div class="details-title">Call Details</div>
        
        <div class="details-grid">
          ${details.map(detail => /* html */ `
            <div class="detail-item">
              <span class="detail-label">${detail.label}</span>
              <span class="detail-value">${detail.value}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  };

  getContactInfo = (call) => {
    const contactInfo = [];

    if (call.contact_id) contactInfo.push({ icon: '👤', label: 'Contact ID', value: call.contact_id.slice(-8) });
    if (call.lead_id) contactInfo.push({ icon: '🎯', label: 'Lead ID', value: call.lead_id.slice(-8) });
    if (call.phone_number) contactInfo.push({ icon: '📞', label: 'Phone', value: call.phone_number });

    if (contactInfo.length === 0) return '';

    return /* html */ `
      <div class="contact-info">
        <div class="contact-title">Contact Information</div>
        
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
      </div>
    `;
  };

  getCallResults = (call) => {
    if (!call.summary && !call.transcript && !call.recording_url) {
      return '';
    }

    return /* html */ `
      <div class="call-results">
        <div class="results-title">Call Results</div>
        
        ${call.summary ? /* html */ `
          <div class="result-section">
            <span class="result-label">Summary</span>
            <p class="result-text">${call.summary}</p>
          </div>
        ` : ''}
        
        ${call.transcript ? /* html */ `
          <div class="result-section">
            <span class="result-label">Transcript</span>
            <p class="result-text transcript">${this.truncateText(call.transcript, 200)}</p>
          </div>
        ` : ''}
        
        ${call.recording_url ? /* html */ `
          <div class="result-section">
            <span class="result-label">Recording</span>
            <a href="${call.recording_url}" target="_blank" class="recording-link">
              🎵 Listen to Recording
            </a>
          </div>
        ` : ''}
      </div>
    `;
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
        <h2>No Recent Calls Found</h2>
        <p>There are no recent calls to display at this time.</p>
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

        .calls-stats {
          background: var(--gray-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .calls-stats h3 {
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

        .recent-card {
          border-left: 4px solid var(--accent-color);
        }

        .call-card:hover {
          border-color: var(--accent-color);
        }

        .call-card:focus {
          outline: none;
          border-color: var(--accent-color);
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

        .call-meta {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
        }

        .call-time {
          font-size: 0.85rem;
          color: var(--gray-color);
        }

        .call-cost {
          font-size: 0.85rem;
          color: var(--success-color);
          font-weight: 600;
        }

        .status-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          text-transform: capitalize;
        }

        .status-badge.status-success {
          background: var(--success-color);
          color: var(--white-color);
        }

        .status-badge.status-failed {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .status-badge.status-cancelled {
          background: var(--warning-color);
          color: var(--white-color);
        }

        .status-badge.status-no-answer {
          background: var(--gray-color);
          color: var(--white-color);
        }

        .status-badge.status-busy {
          background: var(--create-color);
          color: var(--white-color);
        }

        .status-badge.status-progress {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .status-badge.status-pending {
          background: var(--hubspot-color);
          color: var(--white-color);
        }

        .duration-badge {
          background: var(--gray-background);
          color: var(--text-color);
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

        .call-details,
        .contact-info,
        .call-results {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .details-title,
        .contact-title,
        .results-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 8px;
        }

        .detail-item {
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

        .contact-grid {
          display: flex;
          flex-direction: column;
          gap: 8px;
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

        .result-section {
          margin-bottom: 8px;
        }

        .result-section:last-child {
          margin-bottom: 0;
        }

        .result-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .result-text {
          margin: 0;
          font-size: 0.85rem;
          line-height: 1.4;
          color: var(--text-color);
        }

        .result-text.transcript {
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
          font-family: monospace;
          font-size: 0.8rem;
        }

        .recording-link {
          color: var(--accent-color);
          text-decoration: none;
          font-size: 0.85rem;
          font-weight: 500;
        }

        .recording-link:hover {
          text-decoration: underline;
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

          .details-grid {
            grid-template-columns: 1fr;
          }

          .call-meta {
            align-items: flex-start;
          }
        }
      </style>
    `;
  };
}
