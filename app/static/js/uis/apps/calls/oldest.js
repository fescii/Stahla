export default class CallsOldest extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/calls/oldest";
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
      console.error("Error fetching oldest calls:", error);
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
        ${this.getHistoricalStats()}
        ${this.getCallsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Oldest Calls</h1>
        <p class="subtitle">Historical call records sorted by creation date</p>
      </div>
    `;
  };

  getHistoricalStats = () => {
    if (!this.callsData.items || this.callsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateHistoricalStats(this.callsData.items);

    return /* html */ `
      <div class="historical-stats">
        <h3>Historical Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalCalls}</span>
            <span class="stat-label">Total Calls</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.oldestAge}</span>
            <span class="stat-label">Oldest Call</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.completionRate}%</span>
            <span class="stat-label">Success Rate</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">$${stats.totalSpent}</span>
            <span class="stat-label">Total Spent</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateHistoricalStats = (calls) => {
    const totalCalls = calls.length;
    const completedCalls = calls.filter(call => call.status === 'completed').length;
    const completionRate = totalCalls > 0 ? Math.round((completedCalls / totalCalls) * 100) : 0;

    // Calculate oldest call age
    const oldestCall = calls.reduce((oldest, call) => {
      const callDate = new Date(call.created_at);
      const oldestDate = new Date(oldest.created_at);
      return callDate < oldestDate ? call : oldest;
    }, calls[0]);

    const oldestAge = this.getCallAge(oldestCall.created_at);

    const costs = calls
      .filter(call => call.cost !== null && call.cost !== undefined)
      .map(call => call.cost);

    const totalSpent = costs.length > 0
      ? costs.reduce((sum, cost) => sum + cost, 0).toFixed(2)
      : '0.00';

    return {
      totalCalls,
      oldestAge,
      completionRate,
      totalSpent
    };
  };

  getCallAge = (dateString) => {
    if (!dateString) return 'Unknown';

    const callDate = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - callDate);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays === 1) return '1 day';
    if (diffDays < 30) return `${diffDays} days`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} months`;
    return `${Math.floor(diffDays / 365)} years`;
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
    const callAge = this.getCallAge(call.created_at);

    return /* html */ `
      <div class="call-card oldest-card" data-call-id="${call.id}" tabindex="0">
        <div class="call-header">
          <div class="call-info">
            <h3>Call ${call.id.slice(-6)}</h3>
            ${this.getStatusBadge(call.status)}
            ${this.getAgeBadge(callAge)}
          </div>
          <div class="call-meta">
            <span class="call-date">${this.formatDate(call.created_at)}</span>
            ${call.cost ? /* html */ `<span class="call-cost">$${call.cost.toFixed(2)}</span>` : ''}
          </div>
        </div>
        
        <div class="call-body">
          ${this.getHistoricalDetails(call)}
          
          ${this.getContactHistory(call)}
          
          ${this.getCallOutcome(call)}
          
          <div class="call-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Age</span>
                <span class="metadata-value call-age">${callAge}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Duration</span>
                <span class="metadata-value">${this.formatDuration(call.duration_seconds)}</span>
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

  getAgeBadge = (age) => {
    return /* html */ `<span class="age-badge">${age} ago</span>`;
  };

  formatDuration = (duration) => {
    if (duration === null || duration === undefined) return 'N/A';

    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;
    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  };

  getHistoricalDetails = (call) => {
    const details = [];

    if (call.task) details.push({ label: 'Task', value: call.task });
    if (call.pathway_id_used) details.push({ label: 'Pathway', value: call.pathway_id_used.slice(-8) });
    if (call.voice_id) details.push({ label: 'Voice', value: call.voice_id });
    if (call.ended_reason) details.push({ label: 'End Reason', value: call.ended_reason });

    if (details.length === 0) return '';

    return /* html */ `
      <div class="historical-details">
        <div class="details-title">Historical Details</div>
        
        <div class="details-grid">
          ${details.map(detail => /* html */ `
            <div class="detail-item">
              <span class="detail-label">${detail.label}</span>
              <span class="detail-value">${detail.value}</span>
            </div>
          `).join('')}
        </div>
        
        ${this.getTimelineInfo(call)}
      </div>
    `;
  };

  getTimelineInfo = (call) => {
    const timeline = [];

    if (call.call_initiated_at) {
      timeline.push({
        event: 'Initiated',
        time: this.formatDate(call.call_initiated_at),
        icon: '🚀'
      });
    }

    if (call.call_completed_at) {
      timeline.push({
        event: 'Completed',
        time: this.formatDate(call.call_completed_at),
        icon: '✅'
      });
    } else if (call.status === 'failed') {
      timeline.push({
        event: 'Failed',
        time: this.formatDate(call.updated_at),
        icon: '❌'
      });
    }

    if (timeline.length === 0) return '';

    return /* html */ `
      <div class="timeline-info">
        <div class="timeline-events">
          ${timeline.map(event => /* html */ `
            <div class="timeline-event">
              <span class="timeline-icon">${event.icon}</span>
              <div class="timeline-content">
                <span class="timeline-event-name">${event.event}</span>
                <span class="timeline-event-time">${event.time}</span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  };

  getContactHistory = (call) => {
    const contactInfo = [];

    if (call.phone_number) contactInfo.push({ icon: '📞', label: 'Phone', value: call.phone_number });
    if (call.contact_id) contactInfo.push({ icon: '👤', label: 'Contact', value: call.contact_id.slice(-8) });
    if (call.lead_id) contactInfo.push({ icon: '🎯', label: 'Lead', value: call.lead_id.slice(-8) });
    if (call.answered_by) contactInfo.push({ icon: '🗣️', label: 'Answered By', value: call.answered_by });

    if (contactInfo.length === 0) return '';

    return /* html */ `
      <div class="contact-history">
        <div class="contact-title">Contact History</div>
        
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
        
        ${this.getRetryHistory(call)}
      </div>
    `;
  };

  getRetryHistory = (call) => {
    if (!call.retry_count || call.retry_count === 0) return '';

    return /* html */ `
      <div class="retry-history">
        <div class="retry-info">
          <span class="retry-label">Retry History</span>
          <div class="retry-details">
            <span class="retry-count">${call.retry_count} retries</span>
            ${call.retry_reason ? /* html */ `<span class="retry-reason">${call.retry_reason}</span>` : ''}
            ${call.last_retry_attempt_at ? /* html */ `
              <span class="retry-last">Last: ${this.formatDate(call.last_retry_attempt_at)}</span>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  };

  getCallOutcome = (call) => {
    if (!call.summary && !call.transcript && !call.recording_url && !call.error_message) {
      return '';
    }

    return /* html */ `
      <div class="call-outcome">
        <div class="outcome-title">Call Outcome</div>
        
        ${call.summary ? /* html */ `
          <div class="outcome-section">
            <span class="outcome-label">Summary</span>
            <p class="outcome-text">${call.summary}</p>
          </div>
        ` : ''}
        
        ${call.error_message ? /* html */ `
          <div class="outcome-section">
            <span class="outcome-label">Error</span>
            <p class="outcome-text error-text">${call.error_message}</p>
          </div>
        ` : ''}
        
        ${call.transcript ? /* html */ `
          <div class="outcome-section">
            <span class="outcome-label">Transcript</span>
            <p class="outcome-text transcript">${this.truncateText(call.transcript, 150)}</p>
          </div>
        ` : ''}
        
        ${call.recording_url ? /* html */ `
          <div class="outcome-section">
            <span class="outcome-label">Recording</span>
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
        <h2>No Oldest Calls Found</h2>
        <p>There are no historical calls to display at this time.</p>
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
          color: var(--create-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
        }

        .historical-stats {
          background: var(--gray-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .historical-stats h3 {
          margin: 0 0 12px 0;
          color: var(--create-color);
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
          color: var(--create-color);
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

        .oldest-card {
          border-left: 4px solid var(--create-color);
        }

        .call-card:hover {
          border-color: var(--create-color);
        }

        .call-card:focus {
          outline: none;
          border-color: var(--create-color);
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

        .call-date {
          font-size: 0.85rem;
          color: var(--gray-color);
        }

        .call-cost {
          font-size: 0.85rem;
          color: var(--create-color);
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

        .age-badge {
          background: var(--create-color);
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

        .historical-details,
        .contact-history,
        .call-outcome {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .details-title,
        .contact-title,
        .outcome-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 8px;
          margin-bottom: 8px;
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

        .timeline-info {
          margin-top: 8px;
        }

        .timeline-events {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .timeline-event {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px;
          background: var(--background);
          border-radius: 4px;
        }

        .timeline-icon {
          font-size: 1rem;
          width: 24px;
          text-align: center;
        }

        .timeline-content {
          display: flex;
          flex-direction: column;
          gap: 2px;
          flex: 1;
        }

        .timeline-event-name {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .timeline-event-time {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
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

        .retry-history {
          margin-top: 8px;
          background: var(--background);
          border-radius: 4px;
          padding: 8px;
        }

        .retry-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .retry-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .retry-details {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }

        .retry-count {
          font-size: 0.85rem;
          color: var(--warning-color);
          font-weight: 600;
        }

        .retry-reason {
          font-size: 0.8rem;
          color: var(--text-color);
          font-style: italic;
        }

        .retry-last {
          font-size: 0.8rem;
          color: var(--gray-color);
        }

        .outcome-section {
          margin-bottom: 8px;
        }

        .outcome-section:last-child {
          margin-bottom: 0;
        }

        .outcome-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .outcome-text {
          margin: 0;
          font-size: 0.85rem;
          line-height: 1.4;
          color: var(--text-color);
        }

        .outcome-text.error-text {
          color: var(--danger-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
        }

        .outcome-text.transcript {
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
          font-family: monospace;
          font-size: 0.8rem;
        }

        .recording-link {
          color: var(--create-color);
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

        .metadata-value.call-age {
          color: var(--create-color);
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
          border-color: var(--create-color);
          color: var(--create-color);
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
          border-top: 3px solid var(--create-color);
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

          .retry-details {
            flex-direction: column;
            gap: 4px;
          }
        }
      </style>
    `;
  };
}
