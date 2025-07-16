export default class LocationFailed extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/location/failed";
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
  }

  disconnectedCallback() {
    // Cleanup if needed
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
      console.error("Error fetching failed locations:", error);
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
        ${this.getFailureStats()}
        ${this.getLocationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Failed Locations</h1>
        <p class="subtitle">Location lookups that encountered errors</p>
      </div>
    `;
  };

  getFailureStats = () => {
    if (!this.locationsData.items || this.locationsData.items.length === 0) {
      return '';
    }

    const failureTypes = this.locationsData.items.reduce((acc, location) => {
      const status = location.status;
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    }, {});

    return /* html */ `
      <div class="failure-stats">
        <h3>Failure Analysis</h3>
        <div class="stats-grid">
          ${Object.entries(failureTypes).map(([status, count]) => /* html */ `
            <div class="stat-item">
              <span class="stat-count">${count}</span>
              <span class="stat-label">${this.formatStatus(status)}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  };

  getLocationsList = () => {
    if (!this.locationsData.items || this.locationsData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="locations-table">
        <div class="table-header">
          <div class="header-cell address">Location</div>
          <div class="header-cell error">Error Details</div>
          <div class="header-cell performance">Performance</div>
          <div class="header-cell status">Status</div>
        </div>
        <div class="table-body">
          ${this.locationsData.items.map(location => this.getLocationRow(location)).join('')}
        </div>
      </div>
    `;
  };

  getSVGIcon = (type) => {
    const icons = {
      error: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>`,
      warning: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>`,
      location: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>`,
      api: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v6m0 6v6"/>
        <path d="m21 12-6-3-6 3-6-3"/>
      </svg>`,
      cache: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12.89 1.45l8 4-8 4-8-4 8-4z"/>
        <path d="M4 9.5l8 4 8-4"/>
        <path d="M4 14.5l8 4 8-4"/>
      </svg>`
    };
    return icons[type] || '';
  };

  getLocationRow = (location) => {
    return /* html */ `
      <div class="location-row" data-location-id="${location.id}" tabindex="0">
        <div class="cell address-cell">
          <div class="address-info">
            <h4>${location.delivery_location}</h4>
            <span class="location-id">ID: ${location.id.slice(-8)}</span>
            ${location.original_query && location.original_query !== location.delivery_location ?
              /* html */ `<p class="original-query">Originally: ${location.original_query}</p>` : ''}
          </div>
        </div>
        
        <div class="cell error-cell">
          <div class="error-details">
            <div class="error-item">
              ${this.getSVGIcon('error')}
              <span class="error-type">${this.formatStatus(location.status)}</span>
            </div>
            
            <div class="error-item">
              ${this.getSVGIcon('warning')}
              <span class="error-context">${this.getErrorContext(location)}</span>
            </div>
            
            ${location.api_method_used ? /* html */ `
              <div class="error-item">
                ${this.getSVGIcon('api')}
                <span class="api-method">Method: ${location.api_method_used}</span>
              </div>
            ` : ''}
          </div>
        </div>
        
        <div class="cell performance-cell">
          <div class="performance-info">
            <div class="perf-item">
              <span class="perf-label">Processing</span>
              <span class="perf-value">${location.processing_time_ms ? `${location.processing_time_ms}ms` : 'N/A'}</span>
            </div>
            <div class="perf-item">
              <span class="perf-label">API Calls</span>
              <span class="perf-value">${location.api_calls_made || 0}</span>
            </div>
            <div class="perf-item">
              <span class="perf-label">Cache</span>
              <span class="perf-value ${location.cache_hit ? 'cache-hit' : 'cache-miss'}">${location.cache_hit ? 'Hit' : 'Miss'}</span>
            </div>
          </div>
        </div>
        
        <div class="cell status-cell">
          <div class="status-info">
            <div class="status-badge failed">
              ${this.getSVGIcon('error')}
              <span>Failed</span>
            </div>
            <div class="failure-badge">${this.getFailureBadge(location.status)}</div>
            <div class="failure-time">
              <span class="time-label">Failed</span>
              <span class="time-value">${this.formatDate(location.created_at)}</span>
            </div>
            ${location.fallback_used ? /* html */ `
              <div class="status-tag fallback">Fallback Attempted</div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  };

  getFailureBadge = (status) => {
    const badges = {
      'failed': 'General',
      'geocoding_failed': 'Geocoding',
      'distance_calculation_failed': 'Distance'
    };
    return badges[status] || 'Error';
  };

  getErrorContext = (location) => {
    if (location.status === 'geocoding_failed') {
      return 'Unable to determine coordinates for the provided address';
    } else if (location.status === 'distance_calculation_failed') {
      return 'Could not calculate distance to nearest branch';
    } else if (location.status === 'failed') {
      return 'General lookup failure occurred during processing';
    }
    return 'Unknown error occurred during location lookup';
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
        <h2>No Failed Locations</h2>
        <p>Great news! There are currently no failed location lookups.</p>
      </div>
    `;
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
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
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
          background: var(--error-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .failure-stats h3 {
          margin: 0 0 12px 0;
          color: var(--error-color);
          font-size: 1.1rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
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
          color: var(--error-color);
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
          border-bottom: 1px solid var(--border-color);
        }

        .header-cell {
          padding: 12px 16px;
          font-size: 0.8rem;
          font-weight: 600;
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

        .location-row {
          display: grid;
          grid-template-columns: 2fr 2fr 1.5fr 1.5fr;
          border-bottom: 1px solid var(--border-color);
          transition: background-color 0.2s ease;
          cursor: pointer;
        }

        .location-row:last-child {
          border-bottom: none;
        }

        .location-row:hover {
          background: var(--gray-background);
        }

        .location-row:focus {
          outline: none;
          background: var(--error-background);
        }

        .cell {
          padding: 16px;
          border-right: 1px solid var(--border-color);
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .cell:last-child {
          border-right: none;
        }

        .address-info h4 {
          margin: 0 0 4px 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
          line-height: 1.3;
        }

        .location-id {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--gray-color);
        }

        .original-query {
          margin: 4px 0 0 0;
          font-size: 0.75rem;
          color: var(--gray-color);
          font-style: italic;
        }

        .error-details {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .error-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .icon {
          width: 14px;
          height: 14px;
          color: var(--danger-color);
          flex-shrink: 0;
        }

        .error-type {
          font-size: 0.85rem;
          color: var(--danger-color);
          font-weight: 600;
        }

        .error-context {
          font-size: 0.8rem;
          color: var(--text-color);
        }

        .api-method {
          font-size: 0.8rem;
          color: var(--gray-color);
        }

        .performance-info {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .perf-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .perf-label {
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        .perf-value {
          font-size: 0.8rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .perf-value.cache-hit {
          color: var(--success-color);
        }

        .perf-value.cache-miss {
          color: var(--warning-color);
        }

        .status-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .status-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 8px;
          border-radius: 6px;
          font-size: 0.8rem;
          font-weight: 500;
        }

        .status-badge.failed {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .status-badge .icon {
          width: 12px;
          height: 12px;
          color: currentColor;
        }

        .failure-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          background: var(--warning-color);
          color: var(--white-color);
        }

        .failure-time {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .time-label {
          font-size: 0.7rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .time-value {
          font-size: 0.75rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .status-tag {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .status-tag.fallback {
          background: var(--alt-color);
          color: var(--white-color);
        }
          background: var(--error-color);
        }

        .status-text {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--error-color);
        }

        .failure-badge {
          background: var(--error-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
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

        .failure-details {
          background: var(--error-background);
          border: 1px solid var(--error-color);
          border-radius: 6px;
          padding: 12px;
        }

        .failure-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
        }

        .failure-icon {
          color: var(--error-color);
          font-weight: bold;
        }

        .failure-text {
          font-weight: 500;
          font-size: 0.9rem;
          color: var(--error-color);
        }

        .failure-info {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .failure-type {
          color: var(--error-color);
          font-weight: 600;
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

        .detail-value.success {
          color: var(--success-color);
        }

        .detail-value.failed {
          color: var(--error-color);
        }

        .detail-value.attempted {
          color: var(--alt-color);
        }

        .detail-value.not-attempted {
          color: var(--gray-color);
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
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .timestamp,
        .task-id {
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
          .table-header {
            display: none;
          }
          
          .location-row {
            display: flex;
            flex-direction: column;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 12px;
            background: var(--background);
          }
          
          .location-row:last-child {
            border-bottom: 1px solid var(--border-color);
          }
          
          .cell {
            border-right: none;
            border-bottom: 1px solid var(--border-color);
            padding: 12px 16px;
          }
          
          .cell:last-child {
            border-bottom: none;
          }
          
          .cell::before {
            content: attr(data-label);
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--gray-color);
            text-transform: uppercase;
            letter-spacing: 0.025em;
            display: block;
            margin-bottom: 4px;
          }
          
          .address-cell::before { content: "Location"; }
          .error-cell::before { content: "Error Details"; }
          .performance-cell::before { content: "Performance"; }
          .status-cell::before { content: "Status"; }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      </style>
    `;
  };
}
