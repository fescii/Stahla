export default class LocationRecent extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/location/recent";
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
      console.error("Error fetching recent locations:", error);
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
        ${this.getLocationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Recent Locations</h1>
        <p class="subtitle">Most recently processed location lookups</p>
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
          <div class="header-cell details">Details</div>
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
      success: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22,4 12,14.01 9,11.01"/>
      </svg>`,
      failed: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>`,
      location: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>`,
      branch: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
        <circle cx="12" cy="7" r="4"/>
      </svg>`,
      distance: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <polyline points="12,6 12,12 16,14"/>
      </svg>`
    };
    return icons[type] || '';
  };

  getLocationRow = (location) => {
    const isSuccess = location.lookup_successful;

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
        
        <div class="cell details-cell">
          <div class="location-details">
            ${isSuccess ? this.getSuccessDetails(location) : this.getFailureDetails(location)}
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
            <div class="status-badge ${isSuccess ? 'success' : 'failed'}">
              ${this.getSVGIcon(isSuccess ? 'success' : 'failed')}
              <span>${isSuccess ? 'Success' : 'Failed'}</span>
            </div>
            ${location.fallback_used ? /* html */ `
              <div class="status-tag fallback">Fallback Used</div>
            ` : ''}
            <div class="completion-time">
              <span class="time-label">Processed</span>
              <span class="time-value">${this.formatDate(location.lookup_completed_at || location.created_at)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getSuccessDetails = (location) => {
    return /* html */ `
      ${location.nearest_branch ? /* html */ `
        <div class="detail-item">
          ${this.getSVGIcon('branch')}
          <span class="detail-text">${location.nearest_branch}</span>
        </div>
      ` : ''}
      
      ${location.distance_miles ? /* html */ `
        <div class="detail-item">
          ${this.getSVGIcon('distance')}
          <span class="detail-text">${location.distance_miles} miles • ${this.formatDuration(location.duration_seconds)}</span>
        </div>
      ` : ''}
      
      <div class="detail-item">
        ${this.getSVGIcon('location')}
        <span class="detail-text ${location.within_service_area ? 'in-area' : 'out-area'}">
          ${location.within_service_area ? 'In Service Area' : 'Outside Service Area'}
        </span>
      </div>
    `;
  };

  getFailureDetails = (location) => {
    return /* html */ `
      <div class="detail-item">
        ${this.getSVGIcon('failed')}
        <span class="detail-text error">Failed: ${this.formatStatus(location.status)}</span>
      </div>
    `;
  };

  getSuccessfulLookupInfo = (location) => {
    return /* html */ `
      <div class="lookup-success">
        <div class="success-header">
          <span class="success-icon">✓</span>
          <span class="success-text">Lookup Successful</span>
          ${location.fallback_used ? /* html */ `<span class="fallback-badge">Fallback Used</span>` : ''}
        </div>
        
        ${location.nearest_branch ? /* html */ `
          <div class="branch-info">
            <div class="detail-item">
              <span class="detail-label">Nearest Branch</span>
              <span class="detail-value branch-name">${location.nearest_branch}</span>
            </div>
            ${location.nearest_branch_address ? /* html */ `
              <div class="detail-item">
                <span class="detail-label">Branch Address</span>
                <span class="detail-value">${location.nearest_branch_address}</span>
              </div>
            ` : ''}
          </div>
        ` : ''}
        
        ${location.distance_miles ? /* html */ `
          <div class="distance-info">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Distance</span>
                <span class="detail-value distance">${location.distance_miles} miles</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Duration</span>
                <span class="detail-value">${this.formatDuration(location.duration_seconds)}</span>
              </div>
            </div>
          </div>
        ` : ''}
        
        <div class="service-area-info">
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">Service Area</span>
              <span class="detail-value service-area ${location.within_service_area ? 'in-area' : 'out-area'}">
                ${location.within_service_area ? 'Yes' : 'No'}
              </span>
            </div>
            ${location.service_area_type ? /* html */ `
              <div class="detail-item">
                <span class="detail-label">Area Type</span>
                <span class="detail-value">${location.service_area_type}</span>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  };

  getFailedLookupInfo = (location) => {
    return /* html */ `
      <div class="lookup-failed">
        <div class="failed-header">
          <span class="failed-icon">✗</span>
          <span class="failed-text">Lookup Failed</span>
        </div>
        <div class="failed-reason">
          Status: ${this.formatStatus(location.status)}
        </div>
      </div>
    `;
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
        <h2>No Recent Locations</h2>
        <p>There are no recent location lookups to display at this time.</p>
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

  formatDuration = (seconds) => {
    if (!seconds) return 'N/A';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes} min`;
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

        .location-row {
          display: grid;
          grid-template-columns: 2fr 2fr 1.5fr 1.5fr;
          border-bottom: var(--border);
          transition: background-color 0.2s ease;
          cursor: pointer;
        }

        .location-row:hover {
          background: var(--gray-background);
        }

        .location-row:last-child {
          border-bottom: none;
        }

        .cell {
          padding: 12px;
          border-right: 1px solid var(--border-color);
          display: flex;
          align-items: flex-start;
        }

        .cell:last-child {
          border-right: none;
        }

        .address-cell {
          flex-direction: column;
        }

        .address-info h4 {
          margin: 0 0 4px 0;
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--title-color);
          line-height: 1.3;
        }

        .location-id {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--gray-color);
          background: var(--gray-background);
          padding: 2px 4px;
          border-radius: 3px;
          display: inline-block;
          margin-bottom: 4px;
        }

        .original-query {
          margin: 0;
          font-size: 0.75rem;
          color: var(--gray-color);
          font-style: italic;
        }

        .details-cell {
          flex-direction: column;
        }

        .location-details {
          width: 100%;
        }

        .detail-item {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 6px;
        }

        .detail-item:last-child {
          margin-bottom: 0;
        }

        .icon {
          width: 14px;
          height: 14px;
          color: var(--accent-color);
          flex-shrink: 0;
        }

        .detail-text {
          font-size: 0.8rem;
          color: var(--text-color);
        }

        .detail-text.in-area {
          color: var(--success-color);
          font-weight: 600;
        }

        .detail-text.out-area {
          color: var(--error-color);
          font-weight: 600;
        }

        .detail-text.error {
          color: var(--error-color);
          font-weight: 600;
        }

        .performance-cell {
          flex-direction: column;
        }

        .performance-info {
          width: 100%;
        }

        .perf-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
          font-size: 0.8rem;
        }

        .perf-item:last-child {
          margin-bottom: 0;
        }

        .perf-label {
          color: var(--gray-color);
          font-size: 0.75rem;
        }

        .perf-value {
          color: var(--text-color);
          font-weight: 500;
        }

        .perf-value.cache-hit {
          color: var(--success-color);
          font-weight: 600;
        }

        .perf-value.cache-miss {
          color: var(--gray-color);
        }

        .status-cell {
          flex-direction: column;
          justify-content: space-between;
        }

        .status-info {
          width: 100%;
        }

        .status-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 8px;
          border-radius: 6px;
          font-size: 0.8rem;
          font-weight: 600;
          margin-bottom: 8px;
        }

        .status-badge.success {
          background: var(--success-color);
          color: var(--white-color);
        }

        .status-badge.failed {
          background: var(--error-color);
          color: var(--white-color);
        }

        .status-badge .icon {
          width: 12px;
          height: 12px;
        }

        .status-badge.success svg {
          color: var(--white-color);
        }

        .status-badge.failed svg {
          color: var(--white-color);
        }

        .status-tag {
          font-size: 0.65rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          margin-bottom: 8px;
          display: inline-block;
        }

        .status-tag.fallback {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .completion-time {
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
          .locations-table {
            display: block;
          }

          .table-header {
            display: none;
          }

          .location-row {
            display: block;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            margin-bottom: 12px;
            padding: 0;
          }

          .cell {
            display: block;
            border-right: none;
            border-bottom: var(--border);
            padding: 12px;
          }

          .cell:last-child {
            border-bottom: none;
          }

          .cell::before {
            content: attr(data-label);
            font-weight: 600;
            font-size: 0.75rem;
            color: var(--gray-color);
            text-transform: uppercase;
            letter-spacing: 0.025em;
            display: block;
            margin-bottom: 6px;
          }

          .address-cell::before { content: "Location"; }
          .details-cell::before { content: "Details"; }
          .performance-cell::before { content: "Performance"; }
          .status-cell::before { content: "Status"; }
        }
      </style>
    `;
  };
}
