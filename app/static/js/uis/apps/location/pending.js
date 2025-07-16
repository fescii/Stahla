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
      <div class="locations-grid">
        ${this.locationsData.items.map(location => this.getLocationCard(location)).join('')}
      </div>
    `;
  };

  getLocationCard = (location) => {
    const isProcessing = location.status === 'processing';
    const queueTime = this.calculateQueueTime(location.created_at);

    return /* html */ `
      <div class="location-card ${isProcessing ? 'processing' : 'pending'}" data-location-id="${location.id}" tabindex="0">
        <div class="location-header">
          <div class="location-status">
            <span class="status-indicator status-${location.status}"></span>
            <span class="status-text">${this.formatStatus(location.status)}</span>
            ${isProcessing ? /* html */ `<span class="processing-badge">Active</span>` : /* html */ `<span class="pending-badge">Queued</span>`}
          </div>
          <div class="queue-info">
            <span class="queue-time">${queueTime}</span>
            <div class="location-id">${location.id.slice(-8)}</div>
          </div>
        </div>
        
        <div class="location-body">
          <div class="location-address">
            <h3>${location.delivery_location}</h3>
            ${location.original_query && location.original_query !== location.delivery_location ?
              /* html */ `<p class="original-query">Originally: ${location.original_query}</p>` : ''}
          </div>
          
          <div class="pending-details">
            <div class="pending-header">
              <span class="pending-icon">${isProcessing ? '⚡' : '⏱'}</span>
              <span class="pending-text">
                ${isProcessing ? 'Currently Processing' : 'Waiting in Queue'}
              </span>
            </div>
            
            <div class="pending-info">
              <p class="pending-message">
                ${isProcessing
        ? 'This location lookup is being actively processed by the system.'
        : 'This location lookup is waiting in the processing queue and will be handled soon.'
      }
              </p>
              
              ${location.background_task_id ? /* html */ `
                <div class="task-info">
                  <span class="detail-label">Task ID</span>
                  <span class="detail-value task-id">${location.background_task_id}</span>
                </div>
              ` : ''}
            </div>
          </div>
          
          <div class="location-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Queue Time</span>
                <span class="detail-value queue-duration">${queueTime}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">API Calls</span>
                <span class="detail-value">${location.api_calls_made || 0}</span>
              </div>
            </div>
            
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Method</span>
                <span class="detail-value">${location.api_method_used || 'Pending'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Cache Check</span>
                <span class="detail-value ${location.cache_hit ? 'cache-hit' : 'cache-miss'}">${location.cache_hit ? 'Hit' : 'Miss'}</span>
              </div>
            </div>
          </div>
          
          <div class="location-footer">
            <div class="timestamps">
              <span class="timestamp">Created: ${this.formatDate(location.created_at)}</span>
              <span class="timestamp">Updated: ${this.formatDate(location.updated_at)}</span>
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
          padding: 20px 10px;
          position: relative;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }

        .header-content {
          text-align: left;
        }

        .header h1 {
          margin: 0 0 4px 0;
          font-size: 1.8rem;
          font-weight: 600;
          color: var(--alt-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
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

        .locations-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
        }

        .location-card {
          background: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          transition: all 0.2s ease;
          cursor: pointer;
          position: relative;
        }

        .location-card.pending {
          border-left: 4px solid var(--alt-color);
          background: linear-gradient(135deg, var(--background) 0%, var(--gray-background) 100%);
        }

        .location-card.processing {
          border-left: 4px solid var(--accent-color);
          background: linear-gradient(135deg, var(--background) 0%, var(--create-background) 100%);
        }

        .location-card:hover {
          border-color: var(--alt-color);
        }

        .location-card:focus {
          outline: none;
          border-color: var(--alt-color);
        }

        .location-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .location-status {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
        }

        .status-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
        }

        .status-indicator.status-pending {
          background: var(--alt-color);
          animation: pulse 2s infinite;
        }

        .status-indicator.status-processing {
          background: var(--accent-color);
          animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }

        .status-text {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--text-color);
        }

        .pending-badge {
          background: var(--alt-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .processing-badge {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .queue-info {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
        }

        .queue-time {
          font-size: 0.8rem;
          color: var(--alt-color);
          font-weight: 600;
        }

        .location-id {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--gray-color);
          background: var(--gray-background);
          padding: 2px 6px;
          border-radius: 4px;
        }

        .location-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .location-address h3 {
          margin: 0 0 4px 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
          line-height: 1.3;
        }

        .original-query {
          margin: 0;
          font-size: 0.8rem;
          color: var(--gray-color);
          font-style: italic;
        }

        .pending-details {
          background: linear-gradient(135deg, var(--gray-background) 0%, var(--background) 100%);
          border: var(--border);
          border-radius: 6px;
          padding: 12px;
        }

        .pending-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
        }

        .pending-icon {
          color: var(--alt-color);
          font-weight: bold;
        }

        .pending-text {
          font-weight: 500;
          font-size: 0.9rem;
          color: var(--alt-color);
        }

        .pending-message {
          margin: 0 0 8px 0;
          font-size: 0.85rem;
          color: var(--text-color);
          line-height: 1.4;
        }

        .task-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .task-id {
          font-family: var(--font-mono);
          font-size: 0.8rem;
          color: var(--gray-color);
        }

        .location-details {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .detail-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 8px;
        }

        .detail-row:last-child {
          margin-bottom: 0;
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

        .queue-duration {
          color: var(--alt-color);
          font-weight: 600;
        }

        .cache-hit {
          color: var(--success-color);
        }

        .cache-miss {
          color: var(--gray-color);
        }

        .location-footer {
          padding-top: 8px;
          border-top: var(--border);
        }

        .timestamps {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .timestamp {
          font-size: 0.75rem;
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
          .header {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
          }

          .locations-grid {
            grid-template-columns: 1fr;
          }
          
          .detail-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .location-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .queue-info {
            align-items: flex-start;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .timestamps {
            align-items: flex-start;
          }
        }
      </style>
    `;
  };
}
