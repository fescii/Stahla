export default class LocationPending extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/location/pending";
    this.locationsData = null;
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
    this.fetchLocations();
    // Auto-refresh every 30 seconds for pending items
    this.refreshInterval = setInterval(() => {
      if (!this._loading) {
        this.fetchLocations(this.currentPage);
      }
    }, 30000);
  }

  disconnectedCallback() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  fetchLocations = async (page = 1) => {
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
        this.locationsData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.locationsData = response.data;
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching pending locations:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.locationsData = null;
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
          this.fetchLocations(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchLocations(this.currentPage + 1);
        }
      });
    }

    // Refresh button
    const refreshBtn = this.shadowObj.querySelector('#refresh-btn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => {
        this.fetchLocations(1);
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

    if (this._empty || !this.locationsData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getAutoRefreshIndicator()}
        ${this.getPendingStats()}
        ${this.getLocationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <div class="header-content">
          <h1>Pending Locations</h1>
          <p class="subtitle">Location lookups currently in queue or being processed</p>
        </div>
        <button class="refresh-btn" id="refresh-btn">Refresh</button>
      </div>
    `;
  };

  getAutoRefreshIndicator = () => {
    return /* html */ `
      <div class="auto-refresh-indicator">
        <span class="refresh-icon">⟳</span>
        <span>Auto-refreshing every 30 seconds</span>
      </div>
    `;
  };

  getPendingStats = () => {
    if (!this.locationsData.items || this.locationsData.items.length === 0) {
      return '';
    }

    const stats = this.calculatePendingStats(this.locationsData.items);

    return /* html */ `
      <div class="pending-stats">
        <h3>Queue Status</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalPending}</span>
            <span class="stat-label">Total Pending</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.processing}</span>
            <span class="stat-label">Processing</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgQueueTime}</span>
            <span class="stat-label">Avg Queue Time</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.oldestTime}</span>
            <span class="stat-label">Oldest Pending</span>
          </div>
        </div>
      </div>
    `;
  };

  calculatePendingStats = (locations) => {
    const totalPending = locations.length;
    const processing = locations.filter(l => l.status === 'processing').length;

    // Calculate queue times
    const now = new Date();
    const queueTimes = locations.map(l => {
      const created = new Date(l.created_at);
      return Math.floor((now - created) / (1000 * 60)); // minutes
    });

    const avgQueueTime = queueTimes.length > 0
      ? `${Math.round(queueTimes.reduce((sum, time) => sum + time, 0) / queueTimes.length)} min`
      : '0 min';

    const oldestTime = queueTimes.length > 0
      ? `${Math.max(...queueTimes)} min`
      : '0 min';

    return {
      totalPending,
      processing,
      avgQueueTime,
      oldestTime
    };
  };

  getLocationsList = () => {
    if (!this.locationsData.items || this.locationsData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="locations-table">
        <div class="table-header">
          <div class="header-cell">Location</div>
          <div class="header-cell">Queue Status</div>
          <div class="header-cell">Performance</div>
          <div class="header-cell">Queue Time</div>
        </div>
        <div class="table-body">
          ${this.locationsData.items.map(location => this.getLocationRow(location)).join('')}
        </div>
      </div>
    `;
  };

  getSVGIcon = (type) => {
    const icons = {
      pending: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6v6l4 2"/>
      </svg>`,
      processing: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2v4"/>
        <path d="m16.2 7.8 2.9-2.9"/>
        <path d="M18 12h4"/>
        <path d="m16.2 16.2 2.9 2.9"/>
        <path d="M12 18v4"/>
        <path d="m4.9 19.1 2.9-2.9"/>
        <path d="M2 12h4"/>
        <path d="m4.9 4.9 2.9 2.9"/>
      </svg>`,
      location: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>`,
      queue: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 12h18"/>
        <path d="M3 6h18"/>
        <path d="M3 18h18"/>
      </svg>`,
      cache: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2z"/>
        <path d="M8 21v-4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4"/>
      </svg>`,
      api: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M9 12l2 2 4-4"/>
        <path d="M21 12c-1 0-3-1-3-3s2-3 3-3 3 1 3 3-2 3-3 3"/>
        <path d="M3 12c1 0 3-1 3-3s-2-3-3-3-3 1-3 3 2 3 3 3"/>
      </svg>`,
      time: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6v6l4 2"/>
      </svg>`
    };
    return icons[type] || '';
  };

  getLocationRow = (location) => {
    const isProcessing = location.status === 'processing';
    const queueTime = this.calculateQueueTime(location.created_at);

    return /* html */ `
      <div class="table-row ${isProcessing ? 'processing' : 'pending'}" data-location-id="${location.id}" tabindex="0">
        <div class="table-cell location-cell">
          <div class="location-info">
            <div class="icon-status">
              ${this.getSVGIcon(isProcessing ? 'processing' : 'pending')}
              <span class="status-text">${this.formatStatus(location.status)}</span>
              ${isProcessing ? `<span class="processing-badge">Active</span>` : `<span class="pending-badge">Queued</span>`}
            </div>
            <div class="location-address">
              <div class="address-main">${location.delivery_location}</div>
              ${location.original_query && location.original_query !== location.delivery_location ?
        `<div class="address-original">Originally: ${location.original_query}</div>` : ''}
              <div class="location-id">ID: ${location.id.slice(-8)}</div>
            </div>
          </div>
        </div>

        <div class="table-cell queue-cell">
          <div class="queue-status">
            <div class="queue-info">
              ${this.getSVGIcon('queue')}
              <div class="queue-content">
                <div class="queue-label">${isProcessing ? 'Currently Processing' : 'Waiting in Queue'}</div>
                <div class="queue-description">
                  ${isProcessing
        ? 'This location lookup is being actively processed by the system.'
        : 'This location lookup is waiting in the processing queue and will be handled soon.'
      }
                </div>
              </div>
            </div>
            
            ${location.background_task_id ? /* html */ `
              <div class="task-info">
                <div class="task-label">Task ID</div>
                <div class="task-id">${location.background_task_id}</div>
              </div>
            ` : ''}
          </div>
        </div>

        <div class="table-cell performance-cell">
          <div class="performance-metrics">
            <div class="metric">
              ${this.getSVGIcon('api')}
              <span>API Calls: ${location.api_calls_made || 0}</span>
            </div>
            <div class="metric">
              ${this.getSVGIcon('cache')}
              <span class="${location.cache_hit ? 'cache-hit' : 'cache-miss'}">${location.cache_hit ? 'Cache Hit' : 'Cache Miss'}</span>
            </div>
            <div class="metric-small">Method: ${location.api_method_used || 'Pending'}</div>
          </div>
        </div>

        <div class="table-cell time-cell">
          <div class="time-info">
            <div class="queue-duration">
              ${this.getSVGIcon('time')}
              <span class="duration-value">${queueTime}</span>
            </div>
            <div class="timestamps">
              <div class="timestamp">Created: ${this.formatDate(location.created_at)}</div>
              <div class="timestamp">Updated: ${this.formatDate(location.updated_at)}</div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  calculateQueueTime = (createdAt) => {
    const now = new Date();
    const created = new Date(createdAt);
    const diffMs = now - created;
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 1) return 'Just now';
    if (diffMinutes < 60) return `${diffMinutes} min`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ${diffMinutes % 60}m`;

    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ${diffHours % 24}h`;
  };

  formatStatus = (status) => {
    const statusMap = {
      'pending': 'Pending',
      'processing': 'Processing',
      'success': 'Success',
      'failed': 'Failed',
      'fallback_used': 'Fallback Used',
      'geocoding_failed': 'Geocoding Failed',
      'distance_calculation_failed': 'Distance Calculation Failed'
    };
    return statusMap[status] || status;
  };

  formatDate = (dateString) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  getPagination = () => {
    if (!this.locationsData || this.locationsData.total <= this.locationsData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.locationsData.total / this.locationsData.limit)}
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
        <h2>No Pending Locations</h2>
        <p>All location lookups are being processed efficiently. No items currently in queue.</p>
      </div>
    `;
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

        .refresh-btn {
          background: linear-gradient(135deg, var(--alt-color) 0%, var(--accent-color) 100%);
          color: var(--white-color);
          border: none;
          border-radius: 6px;
          padding: 8px 16px;
          font-size: 0.9rem;
          cursor: pointer;
          transition: opacity 0.2s ease;
        }

        .refresh-btn:hover {
          opacity: 0.9;
        }

        .auto-refresh-indicator {
          display: flex;
          align-items: center;
          gap: 8px;
          background: var(--gray-background);
          color: var(--gray-color);
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 0.85rem;
        }

        .refresh-icon {
          animation: rotate 3s linear infinite;
        }

        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .pending-stats {
          background: linear-gradient(135deg, var(--background) 0%, var(--gray-background) 100%);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .pending-stats h3 {
          margin: 0 0 12px 0;
          color: var(--alt-color);
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
          color: var(--alt-color);
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .locations-table {
          background: var(--background);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }

        .table-header {
          display: grid;
          grid-template-columns: 2fr 2fr 1.5fr 1.5fr;
          background: var(--gray-background);
          border-bottom: var(--border);
        }

        .header-cell {
          padding: 12px;
          font-weight: 600;
          font-size: 0.85rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          border-right: 1px solid var(--border-color);
        }

        .header-cell:last-child {
          border-right: none;
        }

        .table-body {
          display: flex;
          flex-direction: column;
        }

        .table-row {
          display: grid;
          grid-template-columns: 2fr 2fr 1.5fr 1.5fr;
          border-bottom: var(--border);
          transition: background-color 0.2s ease;
          cursor: pointer;
        }

        .table-row:hover {
          background: var(--gray-background);
        }

        .table-row:last-child {
          border-bottom: none;
        }

        .table-row.pending {
          border-left: 4px solid var(--alt-color);
        }

        .table-row.processing {
          border-left: 4px solid var(--accent-color);
        }

        .table-cell {
          padding: 12px;
          border-right: 1px solid var(--border-color);
          display: flex;
          align-items: flex-start;
        }

        .table-cell:last-child {
          border-right: none;
        }

        .location-cell {
          flex-direction: column;
          gap: 8px;
        }

        .icon-status {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 4px;
        }

        .icon-status svg {
          color: var(--alt-color);
          flex-shrink: 0;
        }

        .table-row.processing .icon-status svg {
          color: var(--accent-color);
          animation: spin 2s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .status-text {
          font-size: 0.8rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .pending-badge {
          background: var(--alt-color);
          color: var(--white-color);
          font-size: 0.65rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          margin-left: auto;
        }

        .processing-badge {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.65rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          margin-left: auto;
        }

        .location-info {
          width: 100%;
        }

        .location-address {
          flex-grow: 1;
        }

        .address-main {
          font-weight: 600;
          color: var(--title-color);
          font-size: 0.9rem;
          line-height: 1.3;
          margin-bottom: 2px;
        }

        .address-original {
          font-size: 0.75rem;
          color: var(--gray-color);
          font-style: italic;
          margin-bottom: 4px;
        }

        .location-id {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--gray-color);
          background: var(--gray-background);
          padding: 2px 4px;
          border-radius: 3px;
          display: inline-block;
        }

        .queue-cell {
          flex-direction: column;
        }

        .queue-status {
          width: 100%;
        }

        .queue-info {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          margin-bottom: 8px;
        }

        .queue-info svg {
          color: var(--accent-color);
          margin-top: 2px;
          flex-shrink: 0;
        }

        .queue-content {
          flex-grow: 1;
        }

        .queue-label {
          font-weight: 600;
          font-size: 0.8rem;
          color: var(--title-color);
          margin-bottom: 2px;
        }

        .queue-description {
          font-size: 0.75rem;
          color: var(--gray-color);
          line-height: 1.3;
        }

        .task-info {
          margin-top: 8px;
        }

        .task-label {
          font-size: 0.7rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 2px;
        }

        .task-id {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--text-color);
          background: var(--gray-background);
          padding: 2px 4px;
          border-radius: 3px;
        }

        .performance-cell {
          flex-direction: column;
        }

        .performance-metrics {
          width: 100%;
        }

        .metric {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 6px;
          font-size: 0.8rem;
        }

        .metric svg {
          color: var(--accent-color);
          flex-shrink: 0;
        }

        .metric-small {
          font-size: 0.75rem;
          color: var(--gray-color);
          margin-bottom: 4px;
        }

        .cache-hit {
          color: var(--success-color);
          font-weight: 600;
        }

        .cache-miss {
          color: var(--gray-color);
        }

        .time-cell {
          flex-direction: column;
        }

        .time-info {
          width: 100%;
        }

        .queue-duration {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
        }

        .queue-duration svg {
          color: var(--alt-color);
          flex-shrink: 0;
        }

        .duration-value {
          font-weight: 600;
          color: var(--alt-color);
          font-size: 0.85rem;
        }

        .timestamps {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .timestamp {
          font-size: 0.7rem;
          color: var(--gray-color);
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
          color: var(--success-color);
        }

        .empty-state p {
          margin: 0;
          font-size: 0.9rem;
        }

        @media (max-width: 768px) {
          .locations-table {
            display: block;
          }

          .table-header {
            display: none;
          }

          .table-row {
            display: block;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            margin-bottom: 12px;
            padding: 0;
            border-left-width: 4px;
          }

          .table-cell {
            display: block;
            border-right: none;
            border-bottom: var(--border);
            padding: 12px;
          }

          .table-cell:last-child {
            border-bottom: none;
          }

          .table-cell::before {
            content: attr(data-label);
            font-weight: 600;
            font-size: 0.75rem;
            color: var(--gray-color);
            text-transform: uppercase;
            letter-spacing: 0.025em;
            display: block;
            margin-bottom: 6px;
          }

          .location-cell::before { content: "Location"; }
          .queue-cell::before { content: "Queue Status"; }
          .performance-cell::before { content: "Performance"; }
          .time-cell::before { content: "Queue Time"; }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      </style>
    `;
  };
}
