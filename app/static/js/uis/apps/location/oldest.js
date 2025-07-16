export default class LocationOldest extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/location/oldest";
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
      console.error("Error fetching oldest locations:", error);
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
        <h1>Historic Locations</h1>
        <p class="subtitle">Oldest location lookups in the system</p>
      </div>
    `;
  };

  getLocationsList = () => {
    if (!this.locationsData.items || this.locationsData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="locations-grid">
        ${this.locationsData.items.map((location, index) => this.getLocationCard(location, index)).join('')}
      </div>
    `;
  };

  getLocationCard = (location, index) => {
    const isVintage = this.getLocationAge(location.created_at) > 30;

    return /* html */ `
      <div class="location-card ${isVintage ? 'vintage' : ''}" data-location-id="${location.id}" tabindex="0">
        <div class="location-header">
          <div class="location-status">
            <span class="status-indicator status-${location.status}"></span>
            <span class="status-text">${this.formatStatus(location.status)}</span>
            ${isVintage ? /* html */ `<span class="vintage-badge">Historic</span>` : ''}
          </div>
          <div class="age-info">
            <span class="age-badge">${this.formatAge(location.created_at)}</span>
            <div class="location-id">${location.id.slice(-8)}</div>
          </div>
        </div>
        
        <div class="location-body">
          <div class="location-address">
            <h3>${location.delivery_location}</h3>
            ${location.original_query && location.original_query !== location.delivery_location ?
              /* html */ `<p class="original-query">Originally: ${location.original_query}</p>` : ''}
          </div>
          
          ${location.lookup_successful ? this.getSuccessfulLookupInfo(location) : this.getFailedLookupInfo(location)}
          
          <div class="location-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Processing Time</span>
                <span class="detail-value">${location.processing_time_ms ? `${location.processing_time_ms}ms` : 'N/A'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">API Method</span>
                <span class="detail-value">${location.api_method_used || 'N/A'}</span>
              </div>
            </div>
            
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">API Calls</span>
                <span class="detail-value">${location.api_calls_made || 0}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Cache Status</span>
                <span class="detail-value ${location.cache_hit ? 'cache-hit' : 'cache-miss'}">${location.cache_hit ? 'Hit' : 'Miss'}</span>
              </div>
            </div>
          </div>
          
          <div class="location-footer">
            <span class="timestamp">Created: ${this.formatFullDate(location.created_at)}</span>
            ${location.lookup_completed_at ? /* html */ `
              <span class="completion-time">Completed: ${this.formatFullDate(location.lookup_completed_at)}</span>
            ` : ''}
          </div>
        </div>
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
        <h2>No Historic Locations</h2>
        <p>There are no historic location lookups to display at this time.</p>
      </div>
    `;
  };

  getLocationAge = (dateString) => {
    const now = new Date();
    const created = new Date(dateString);
    const diffTime = Math.abs(now - created);
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24)); // days
  };

  formatAge = (dateString) => {
    const days = this.getLocationAge(dateString);

    if (days < 7) {
      return `${days}d ago`;
    } else if (days < 30) {
      const weeks = Math.floor(days / 7);
      return `${weeks}w ago`;
    } else if (days < 365) {
      const months = Math.floor(days / 30);
      return `${months}mo ago`;
    } else {
      const years = Math.floor(days / 365);
      return `${years}y ago`;
    }
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

  formatFullDate = (dateString) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
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
          text-align: center;
          margin-bottom: 10px;
        }

        .header h1 {
          margin: 0 0 8px 0;
          font-size: 1.8rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
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

        .location-card:hover {
          border-color: var(--accent-color);
        }

        .location-card:focus {
          outline: none;
          border-color: var(--accent-color);
        }

        .location-card.vintage {
          background: linear-gradient(135deg, var(--background) 0%, var(--gray-background) 100%);
          border-color: var(--alt-color);
        }

        .location-card.vintage:hover {
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

        .status-indicator.status-success {
          background: var(--success-color);
        }

        .status-indicator.status-failed,
        .status-indicator.status-geocoding-failed,
        .status-indicator.status-distance-calculation-failed {
          background: var(--error-color);
        }

        .status-indicator.status-pending {
          background: var(--alt-color);
        }

        .status-indicator.status-processing {
          background: var(--accent-color);
          animation: pulse 2s infinite;
        }

        .status-indicator.status-fallback-used {
          background: var(--alt-color);
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

        .vintage-badge {
          background: var(--alt-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .age-info {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 4px;
        }

        .age-badge {
          font-size: 0.75rem;
          color: var(--gray-color);
          background: var(--gray-background);
          padding: 2px 6px;
          border-radius: 4px;
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

        .lookup-success {
          background: var(--create-background);
          border: var(--border);
          border-radius: 6px;
          padding: 12px;
        }

        .lookup-failed {
          background: var(--error-background);
          border: var(--border);
          border-radius: 6px;
          padding: 12px;
        }

        .success-header,
        .failed-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 8px;
        }

        .success-icon {
          color: var(--success-color);
          font-weight: bold;
        }

        .failed-icon {
          color: var(--error-color);
          font-weight: bold;
        }

        .success-text,
        .failed-text {
          font-weight: 500;
          font-size: 0.9rem;
        }

        .fallback-badge {
          background: var(--alt-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          margin-left: auto;
        }

        .failed-reason {
          font-size: 0.8rem;
          color: var(--error-color);
        }

        .branch-info,
        .distance-info,
        .service-area-info {
          margin-top: 8px;
        }

        .branch-name {
          font-weight: 600;
          color: var(--accent-color);
        }

        .distance {
          font-weight: 600;
          color: var(--success-color);
        }

        .service-area.in-area {
          color: var(--success-color);
          font-weight: 600;
        }

        .service-area.out-area {
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
          flex-direction: column;
          gap: 4px;
        }

        .timestamp,
        .completion-time {
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
          color: var(--title-color);
        }

        .empty-state p {
          margin: 0;
          font-size: 0.9rem;
        }

        @media (max-width: 768px) {
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

          .age-info {
            align-items: flex-start;
          }
        }
      </style>
    `;
  };
}
