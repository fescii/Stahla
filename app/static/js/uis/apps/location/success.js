export default class LocationSuccess extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/location/successful";
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
      console.error("Error fetching successful locations:", error);
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
        ${this.getSuccessStats()}
        ${this.getLocationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Successful Locations</h1>
        <p class="subtitle">Location lookups that completed successfully</p>
      </div>
    `;
  };

  getSuccessStats = () => {
    if (!this.locationsData.items || this.locationsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateStats(this.locationsData.items);

    return /* html */ `
      <div class="success-stats">
        <h3>Success Metrics</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.inServiceArea}</span>
            <span class="stat-label">In Service Area</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.fallbackUsed}</span>
            <span class="stat-label">Fallback Used</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgProcessingTime}ms</span>
            <span class="stat-label">Avg Processing</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.cacheHitRate}%</span>
            <span class="stat-label">Cache Hit Rate</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateStats = (locations) => {
    const inServiceArea = locations.filter(l => l.within_service_area).length;
    const fallbackUsed = locations.filter(l => l.fallback_used).length;
    const cacheHits = locations.filter(l => l.cache_hit).length;

    const processingTimes = locations
      .filter(l => l.processing_time_ms)
      .map(l => l.processing_time_ms);

    const avgProcessingTime = processingTimes.length > 0
      ? Math.round(processingTimes.reduce((sum, time) => sum + time, 0) / processingTimes.length)
      : 0;

    const cacheHitRate = Math.round((cacheHits / locations.length) * 100);

    return {
      inServiceArea,
      fallbackUsed,
      avgProcessingTime,
      cacheHitRate
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
    return /* html */ `
      <div class="location-card success-card" data-location-id="${location.id}" tabindex="0">
        <div class="location-header">
          <div class="location-status">
            <span class="status-indicator status-success"></span>
            <span class="status-text">Success</span>
            ${location.fallback_used ? /* html */ `<span class="fallback-badge">Fallback</span>` : ''}
            ${location.within_service_area ? /* html */ `<span class="service-badge">In Area</span>` : ''}
          </div>
          <div class="location-id">${location.id.slice(-8)}</div>
        </div>
        
        <div class="location-body">
          <div class="location-address">
            <h3>${location.delivery_location}</h3>
            ${location.original_query && location.original_query !== location.delivery_location ?
              /* html */ `<p class="original-query">Originally: ${location.original_query}</p>` : ''}
          </div>
          
          <div class="success-details">
            <div class="success-header">
              <span class="success-icon">✓</span>
              <span class="success-text">Location Successfully Resolved</span>
            </div>
            
            ${location.nearest_branch ? /* html */ `
              <div class="branch-section">
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
                
                ${location.distance_miles ? /* html */ `
                  <div class="distance-section">
                    <div class="distance-grid">
                      <div class="detail-item">
                        <span class="detail-label">Distance</span>
                        <span class="detail-value distance-value">${location.distance_miles} miles</span>
                      </div>
                      <div class="detail-item">
                        <span class="detail-label">Drive Time</span>
                        <span class="detail-value">${this.formatDuration(location.duration_seconds)}</span>
                      </div>
                    </div>
                  </div>
                ` : ''}
              </div>
            ` : ''}
            
            <div class="service-area-section">
              <div class="service-status ${location.within_service_area ? 'in-area' : 'out-area'}">
                <span class="service-icon">${location.within_service_area ? '✓' : '○'}</span>
                <span class="service-text">
                  ${location.within_service_area ? 'Within Service Area' : 'Outside Service Area'}
                </span>
                ${location.service_area_type ? /* html */ `
                  <span class="area-type">(${location.service_area_type})</span>
                ` : ''}
              </div>
            </div>
          </div>
          
          <div class="location-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Processing Time</span>
                <span class="detail-value performance-metric">${location.processing_time_ms ? `${location.processing_time_ms}ms` : 'N/A'}</span>
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
            
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Geocoding</span>
                <span class="detail-value ${location.geocoding_successful ? 'success' : 'failed'}">
                  ${location.geocoding_successful ? 'Successful' : 'Failed'}
                </span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Provider</span>
                <span class="detail-value">${location.geocoding_provider || location.distance_provider || 'N/A'}</span>
              </div>
            </div>
          </div>
          
          <div class="location-footer">
            <span class="timestamp">Completed: ${this.formatDate(location.lookup_completed_at || location.created_at)}</span>
            ${location.processing_time_ms && location.processing_time_ms < 1000 ? /* html */ `
              <span class="performance-badge fast">Fast</span>
            ` : location.processing_time_ms && location.processing_time_ms > 5000 ? /* html */ `
              <span class="performance-badge slow">Slow</span>
            ` : ''}
          </div>
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
        <h2>No Successful Locations</h2>
        <p>There are no successful location lookups to display at this time.</p>
      </div>
    `;
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
          color: var(--success-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
        }

        .success-stats {
          background: var(--create-background);
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

        .locations-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
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

        .success-card {
          border-left: 4px solid var(--success-color);
          background: linear-gradient(135deg, var(--background) 0%, var(--create-background) 100%);
        }

        .location-card:hover {
          border-color: var(--success-color);
        }

        .location-card:focus {
          outline: none;
          border-color: var(--success-color);
        }

        .location-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
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

        .status-text {
          font-size: 0.85rem;
          font-weight: 500;
          color: var(--success-color);
        }

        .fallback-badge {
          background: var(--alt-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .service-badge {
          background: var(--success-color);
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

        .success-details {
          background: var(--create-background);
          border: 1px solid var(--success-color);
          border-radius: 6px;
          padding: 12px;
        }

        .success-header {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 12px;
        }

        .success-icon {
          color: var(--success-color);
          font-weight: bold;
        }

        .success-text {
          font-weight: 500;
          font-size: 0.9rem;
          color: var(--success-color);
        }

        .branch-section {
          margin-bottom: 12px;
        }

        .branch-name {
          font-weight: 600;
          color: var(--accent-color);
        }

        .distance-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-top: 8px;
        }

        .distance-value {
          font-weight: 600;
          color: var(--success-color);
        }

        .service-area-section {
          padding-top: 8px;
          border-top: var(--border);
        }

        .service-status {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .service-status.in-area {
          color: var(--success-color);
        }

        .service-status.out-area {
          color: var(--alt-color);
        }

        .service-icon {
          font-weight: bold;
        }

        .service-text {
          font-weight: 500;
        }

        .area-type {
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

        .performance-metric {
          color: var(--accent-color);
          font-weight: 600;
        }

        .detail-value.success {
          color: var(--success-color);
        }

        .detail-value.failed {
          color: var(--error-color);
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

        .timestamp {
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        .performance-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .performance-badge.fast {
          background: var(--success-color);
          color: var(--white-color);
        }

        .performance-badge.slow {
          background: var(--alt-color);
          color: var(--white-color);
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
          
          .detail-row,
          .distance-grid {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .location-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }
      </style>
    `;
  };
}
