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
        
        <div class="cell details-cell">
          <div class="location-details">
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
            <div class="status-badge success">
              ${this.getSVGIcon('success')}
              <span>Success</span>
            </div>
            ${location.fallback_used ? /* html */ `
              <div class="status-tag fallback">Fallback Used</div>
            ` : ''}
            <div class="completion-time">
              <span class="time-label">Completed</span>
              <span class="time-value">${this.formatDate(location.lookup_completed_at || location.created_at)}</span>
            </div>
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
          border-bottom: var(--border);
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
          background: var(--create-background);
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

        .location-details {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .detail-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .icon {
          width: 14px;
          height: 14px;
          color: var(--success-color);
          flex-shrink: 0;
        }

        .detail-text {
          font-size: 0.85rem;
          color: var(--text-color);
        }

        .detail-text.in-area {
          color: var(--success-color);
          font-weight: 500;
        }

        .detail-text.out-area {
          color: var(--warning-color);
          font-weight: 500;
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

        .status-badge.success {
          background: var(--success-color);
          color: var(--white-color);
        }

        .status-badge .icon {
          width: 12px;
          height: 12px;
          color: currentColor;
        }

        .status-tag {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .status-tag.fallback {
          background: var(--warning-color);
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
            border-bottom: var(--border);
          }
          
          .cell {
            border-right: none;
            border-bottom: var(--border);
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
          .details-cell::before { content: "Details"; }
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
