export default class ServicesStatus extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/services/status";
    this.statusData = null;
    this._block = false;
    this._empty = false;
    this._loading = true;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch status data first
    this.fetchStatusData();

    // Set up refresh timer and event listeners
    setTimeout(() => {
      this._setupEventListeners();
      this._setupRefreshTimer();
    }, 100);
  }

  disconnectedCallback() {
    this._clearRefreshTimer();
  }

  // Fetch services status data using the API
  fetchStatusData = async () => {
    this._loading = true;
    this._block = true;
    this.render(); // Re-render to show loader

    try {
      const response = await this.api.get(this.url, { content: "json" });
      // Check for 401 Unauthorized response
      if (
        response.status_code === 401 ||
        (response.error_message &&
          response.error_message.includes("validate credentials"))
      ) {
        console.log("Authentication required for status access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.statusData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;

      this.statusData = response;
      this.render();

    } catch (error) {
      console.error("Error fetching services status data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for status access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.statusData = null;
      this.render();
      this.activateRefresh();
    }
  };

  activateRefresh = () => {
    const retryBtn = this.shadowObj.querySelector("button.finish");
    if (retryBtn) {
      retryBtn.addEventListener("click", () => {
        // Reset states
        this._block = false;
        this._empty = false;

        // Start fetch again
        this.fetchStatusData();
      });
    }
  };

  // Auto-refresh status data every 60 seconds
  _setupRefreshTimer() {
    this._refreshTimer = setInterval(() => {
      if (!this._block) {
        this.fetchStatusData();
      }
    }, 60000); // 1 minute refresh
  }

  _clearRefreshTimer() {
    if (this._refreshTimer) {
      clearInterval(this._refreshTimer);
      this._refreshTimer = null;
    }
  }

  // Add event listeners for actions
  _setupEventListeners() {
    // Export button
    const exportBtn = this.shadowObj.querySelector('.export-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', this._handleExport);
    }

    // Service pill interactions
    const servicePills = this.shadowObj.querySelectorAll('.service-pill');
    servicePills.forEach(pill => {
      // Click handler
      pill.addEventListener('click', (e) => {
        const serviceName = pill.dataset.service;
        this._handleServicePillClick(serviceName, pill);
      });

      // Keyboard handler
      pill.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const serviceName = pill.dataset.service;
          this._handleServicePillClick(serviceName, pill);
        }
      });

      // Animation on hover
      pill.addEventListener('mouseenter', () => {
        pill.style.transform = 'translateY(-2px)';
      });

      pill.addEventListener('mouseleave', () => {
        pill.style.transform = 'translateY(0)';
      });
    });
  }

  _handleServicePillClick = (serviceName, pillElement) => {
    // Add a brief animation to indicate interaction
    pillElement.style.transform = 'scale(0.98)';
    setTimeout(() => {
      pillElement.style.transform = 'translateY(-2px)';
    }, 100);

    // You can add additional functionality here, like showing service details
    console.log(`Service clicked: ${serviceName}`);
  };

  // Handle export functionality
  _handleExport = () => {
    // Check if we have data to export
    if (!this.statusData || !this.statusData.data || !this.statusData.data.services) {
      console.error('No data available to export');
      return;
    }

    try {
      const services = this.statusData.data.services;
      const lastUpdated = this.statusData.data.last_updated;

      // Create CSV content
      let csvContent = 'Service Name,Status,Message,Timestamp\n';

      // Add each service data row
      services.forEach(service => {
        const row = [
          `"${service.service_name}"`,
          `"${service.status}"`,
          `"${service.message}"`,
          `"${service.timestamp}"`
        ];
        csvContent += row.join(',') + '\n';
      });

      csvContent += `\nLast Updated,"${lastUpdated}"`;

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'services_status.csv');
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error exporting data:', error);
    }
  };

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody = () => {
    // Show loader when loading
    if (this._loading) {
      return /* html */ `<div class="container">${this.getLoader()}</div>`;
    }

    // Show error message if empty and no data
    if (this._empty || !this.statusData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show status with actual data
    return /* html */ `
      <div class="container">
        ${this._getHeaderHTML()}
        <div class="status-content-grid">
          ${this._getStatusGridHTML()}
          ${this._getStatusDetailsHTML()}
        </div>
      </div>
    `;
  };

  _getHeaderHTML = () => {
    const services = this.statusData.data.services || [];
    const lastUpdated = new Date(this.statusData.data.last_updated).toLocaleString();

    // Count services by status
    const statusCount = {
      ok: services.filter(s => s.status === 'ok').length,
      warning: services.filter(s => s.status === 'warning').length,
      error: services.filter(s => s.status === 'error').length,
      unknown: services.filter(s => !['ok', 'warning', 'error'].includes(s.status)).length
    };

    // Overall status
    let overallStatus = 'operational';
    let overallMessage = 'All systems operational';

    if (statusCount.error > 0) {
      overallStatus = 'outage';
      overallMessage = 'System outage detected';
    } else if (statusCount.warning > 0) {
      overallStatus = 'degraded';
      overallMessage = 'Degraded performance';
    }

    return /* html */ `
    <div class="status-header">
      <div class="status-title">
        <div class="status-indicator ${overallStatus}">
          <span class="status-dot"></span>
          <span class="status-text">${overallMessage}</span>
        </div>
        <div class="status-subtitle">
          <span>Last updated: ${lastUpdated}</span>
          <span class="auto-refresh-indicator">Auto-refreshes every minute</span>
        </div>
      </div>
      <div class="status-actions">
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export
        </button>
      </div>
    </div>
    
    <div class="dashboard-overview">
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Total Services</div>
                <div class="stat-icon icon-services">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
                        <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
                        <line x1="6" y1="6" x2="6.01" y2="6"></line>
                        <line x1="6" y1="18" x2="6.01" y2="18"></line>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${services.length}</div>
            <div class="stat-details">
                <span class="stat-success">${statusCount.ok} Operational</span> &bull;
                <span class="stat-error">${statusCount.error + statusCount.warning} Issues</span>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Operational</div>
                <div class="stat-icon icon-operational">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${statusCount.ok}</div>
            <div class="stat-details">
                <span class="stat-success">Services running normally</span>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Issues</div>
                <div class="stat-icon icon-issues">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${statusCount.error + statusCount.warning}</div>
            <div class="stat-details">
                ${statusCount.warning > 0 ? `<span class="stat-warning">${statusCount.warning} Warning</span>` : ''}
                ${statusCount.warning > 0 && statusCount.error > 0 ? ' &bull; ' : ''}
                ${statusCount.error > 0 ? `<span class="stat-error">${statusCount.error} Error</span>` : ''}
                ${statusCount.error === 0 && statusCount.warning === 0 ? '<span>No issues detected</span>' : ''}
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Last Updated</div>
                <div class="stat-icon icon-time">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${new Date(this.statusData.data.last_updated).toLocaleDateString()}</div>
            <div class="stat-details">
                <span>${new Date(this.statusData.data.last_updated).toLocaleTimeString()}</span>
            </div>
        </div>
    </div>
    `;
  };

  _getStatusGridHTML = () => {
    const services = this.statusData.data.services || [];

    if (!services.length) {
      return /* html */ `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect>
          <line x1="6" y1="6" x2="6.01" y2="6"></line>
          <line x1="6" y1="18" x2="6.01" y2="18"></line>
        </svg>
        <h3>No service status available</h3>
        <p>There is no service status data to display at this time.</p>
      </div>
      `;
    }

    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Service Status</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">
           <div class="services-grid">
             ${services.map(service => this._getServicePillHTML(service)).join('')}
           </div>
        </div>
    </div>
    `;
  };

  _getServicePillHTML = (service) => {
    // Format timestamp
    const timestamp = new Date(service.timestamp).toLocaleDateString();

    // Determine status text and class
    const isOk = service.status.toLowerCase() === 'ok' || service.status.toLowerCase() === 'operational';
    const statusClass = isOk ? 'status-ok' : 'status-error';
    const statusText = isOk ? 'OK' : 'Error';

    // Format service name
    const formattedName = service.service_name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');

    return /* html */ `
    <div class="service-pill" title="${service.message || ''}" tabindex="0" role="button" aria-label="Service: ${formattedName}, Status: ${service.status}" data-service="${service.service_name}">
      <div class="service-pill-header">
        <div class="service-pill-name">${formattedName}</div>
        <div class="service-pill-status ${statusClass}">${statusText}</div>
      </div>
      <div class="service-pill-date">Last sync: ${timestamp}</div>
    </div>
    `;
  };



  _getStatusDetailsHTML = () => {
    // Create a timeline of status updates
    const services = this.statusData.data.services || [];

    if (!services.length) {
      return '';
    }

    // Sort services by timestamp (newest first)
    const sortedServices = [...services].sort((a, b) =>
      new Date(b.timestamp) - new Date(a.timestamp)
    );

    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Status History</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">
           <div class="services-grid">
             ${sortedServices.map(service => this._getHistoryPillHTML(service)).join('')}
           </div>
        </div>
    </div>
    `;
  };

  _getHistoryPillHTML = (service) => {
    const timestamp = new Date(service.timestamp).toLocaleDateString();
    const formattedName = service.service_name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');

    // Determine status text and class
    const isOk = service.status.toLowerCase() === 'ok' || service.status.toLowerCase() === 'operational';
    const statusClass = isOk ? 'status-ok' : 'status-error';
    const statusText = isOk ? 'OK' : 'Error';

    return /* html */ `
    <div class="service-pill" title="${service.message || ''}" tabindex="0" role="button" aria-label="Service: ${formattedName}, Status: ${service.status}">
      <div class="service-pill-header">
        <div class="service-pill-name">${formattedName}</div>
        <div class="service-pill-status ${statusClass}">${statusText}</div>
      </div>
      <div class="service-pill-date">${timestamp}</div>
    </div>
    `;
  };

  getLoader() {
    return `
      <div class="loader-container">
        <div class="loader"></div>
      </div>
    `;
  }

  getWrongMessage = () => {
    return /* html */ `
      <div class="finish">
        <h2 class="finish__title">Something went wrong!</h2>
        <p class="desc">
         An error occurred while fetching the service status data. Please check your connection and try again.
        </p>
        <button class="finish">Retry</button>
      </div>
    `;
  };

  getStyles = () => {
    return /* css */ `
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-main), -apple-system, BlinkMacSystemFont, sans-serif;
          color: var(--text-color);
        }

        * {
          box-sizing: border-box;
        }

        .container {
          padding: 1.5rem;
          width: 100%;
          background-color: var(--background);
          min-height: 100vh;
        }

        .status-content-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          margin-top: 2rem;
        }

        @media (max-width: 780px) {
          .status-content-grid {
            display: flex;
            flex-flow: column;
            gap: 1.5rem;
          }
        }

        .loader-container {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100%;
          min-height: 300px;
        }

        .loader {
          border: 4px solid rgba(0, 0, 0, 0.1);
          border-left-color: var(--accent-color);
          border-radius: 50%;
          width: 40px;
          height: 40px;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .finish {
          text-align: center;
          padding: 3rem 1rem;
          max-width: 500px;
          margin: 0 auto;
          background: var(--background);
          border-radius: 8px;
          box-shadow: var(--card-box-shadow-alt);
        }

        .finish__title {
          font-size: 1.5rem;
          margin-bottom: 1rem;
          color: var(--title-color);
        }

        .desc {
          color: var(--gray-color);
          margin-bottom: 2rem;
        }

        button.finish {
          background: var(--action-linear);
          color: var(--white-color);
          border: none;
          padding: 0.5rem 1.5rem;
          border-radius: 0.375rem;
          font-weight: 500;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        button.finish:hover {
          background: var(--accent-linear);
        }

        /* Status Header Styles */
        .status-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .status-indicator {
          display: inline-flex;
          align-items: center;
          margin-bottom: 0.5rem;
          padding: 0.375rem 0.75rem;
          border-radius: 9999px;
          font-weight: 500;
        }

        .status-indicator.operational {
          background: var(--success-background);
          color: var(--accent-color);
          border: 1px solid var(--success-border);
        }

        .status-indicator.degraded {
          background: var(--warning-background);
          color: var(--warning-color);
          border: 1px solid var(--warning-border);
        }

        .status-indicator.outage {
          background: var(--error-background);
          color: var(--error-color);
          border: 1px solid var(--error-border);
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-right: 0.5rem;
        }

        .operational .status-dot {
          background-color: var(--accent-color);
          box-shadow: 0 0 0 2px var(--success-background);
        }

        .degraded .status-dot {
          background-color: var(--warning-color);
          box-shadow: 0 0 0 2px var(--warning-background);
        }

        .outage .status-dot {
          background-color: var(--error-color);
          box-shadow: 0 0 0 2px var(--error-background);
        }

        .status-subtitle {
          display: flex;
          flex-direction: column;
          color: var(--gray-color);
          font-size: 0.875rem;
          gap: 0.25rem;
        }

        .auto-refresh-indicator {
          display: flex;
          align-items: center;
          font-size: 0.75rem;
          color: var(--gray-color);
          opacity: 0.8;
        }

        .status-actions {
          display: flex;
          gap: 0.75rem;
        }

        .export-btn {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          background: var(--action-linear);
          color: var(--white-color);
          border: var(--action-border);
          padding: var(--spacing-sm) var(--spacing-md);
          border-radius: var(--border-radius-md);
          font-weight: var(--font-weight-medium);
          font-size: var(--font-size-sm);
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .export-btn:hover {
          background: var(--accent-linear);
          transform: translateY(-1px);
          box-shadow: var(--hover-box-shadow);
        }

        .export-btn svg {
          stroke-width: 2px;
        }

        /* Dashboard Overview Styles - Match overview.js */
        .dashboard-overview {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1.25rem;
          margin: 1.5rem 0 2rem;
        }

        .stat-card {
          background-color: var(--stat-background);
          border-radius: 12px;
          padding: 1.25rem;
          box-shadow: var(--card-box-shadow-alt);
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
        }

        .stat-card:after {
          content: "";
          position: absolute;
          top: 0;
          right: 0;
          height: 4px;
          width: 100%;
          background: var(--accent-linear);
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .stat-card:hover {
          transform: translateY(-5px);
          box-shadow: var(--card-box-shadow);
        }

        .stat-card:hover:after {
          opacity: 1;
        }

        .stat-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .stat-title {
          font-weight: 600;
          color: var(--gray-color);
          font-size: 0.92rem;
          text-transform: capitalize;
          letter-spacing: 0.5px;
        }

        .stat-icon {
          width: 42px;
          height: 42px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--white-color);
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
          transform: rotate(0deg);
          transition: transform 0.3s ease;
        }

        .stat-card:hover .stat-icon {
          transform: rotate(5deg) scale(1.05);
        }

        .icon-services { background: var(--action-linear); }
        .icon-operational { background: var(--accent-linear); }
        .icon-issues { background: var(--error-linear); }
        .icon-time { background: var(--second-linear); }

        .stat-value {
          font-size: 2.25rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.75rem;
          font-family: var(--font-main), sans-serif;
          letter-spacing: -0.02em;
          line-height: 1;
        }

        .stat-details {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.875rem;
          flex-wrap: wrap;
          position: relative;
        }

        .stat-details:before {
          content: "";
          position: absolute;
          left: 0;
          top: -0.5rem;
          width: 2rem;
          height: 2px;
          background: var(--accent-linear);
          opacity: 0.5;
          transition: width 0.3s ease;
        }

        .stat-card:hover .stat-details:before {
          width: 3rem;
        }

        .stat-success {
          color: var(--success-color);
          font-weight: 500;
        }

        .stat-warning {
          color: var(--alt-color);
          font-weight: 500;
        }

        .stat-error {
          color: var(--error-color);
          font-weight: 500;
        }

        /* Panel Styles - Match overview.js */
        .panel {
          background-color: var(--hover-background);
          border-radius: 8px;
          padding: 0;
          box-shadow: var(--card-box-shadow-alt);
          transition: box-shadow 0.2s ease;
          overflow: hidden;
        }

        .panel:hover {
          box-shadow: var(--card-box-shadow);
        }

        .panel-header {
          padding: 12px 1.25rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: relative;
          box-shadow: 0 1px 0 rgba(107, 114, 128, 0.1);
        }

        .panel-header:after {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          height: 100%;
          width: 4px;
          background: var(--accent-linear);
          opacity: 0.7;
        }

        .panel-title {
          padding: 0;
          margin: 0;
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          font-family: var(--font-main), sans-serif;
          letter-spacing: -0.01em;
        }

        .panel-actions {
          display: flex;
          gap: 0.5rem;
          color: var(--gray-color);
        }

        .panel-body {
          padding: 1.25rem;
        }

        /* Services Grid - Match overview.js */
        .services-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 1rem;
          width: 100%;
        }
        
        @media (max-width: 768px) {
          .services-grid {
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          }
        }
        
        @media (min-width: 1024px) {
          .services-grid {
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem;
          }
        }

        .service-pill {
          display: flex;
          flex-direction: column;
          padding: 0.9rem 1rem;
          background-color: var(--stat-background);
          border-radius: 8px;
          transition: all 0.2s ease;
          cursor: pointer;
          box-shadow: var(--card-box-shadow-alt);
          position: relative;
          overflow: hidden;
        }
        
        .service-pill:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
          background-color: var(--hover-background);
        }
        
        .service-pill:active {
          transform: translateY(0) scale(0.98);
        }
        
        .service-pill-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 4px;
        }
        
        .service-pill-name {
          font-weight: 600;
          color: var(--title-color);
          font-size: 0.95rem;
          letter-spacing: -0.01em;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }
        
        .service-pill-status {
          font-size: 0.8rem;
          font-weight: 600;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          min-width: 40px;
          text-align: center;
        }
        
        .service-pill-status.status-ok {
          color: var(--accent-color);
          background-color: rgba(0, 96, 223, 0.1);
        }
        
        .service-pill-status.status-error {
          color: var(--error-color);
          background-color: rgba(236, 75, 25, 0.1);
        }
        
        .service-pill-date {
          font-size: 0.75rem;
          color: var(--gray-color);
          margin-top: 2px;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }

        /* Empty state styles */
        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4rem 1rem;
          text-align: center;
          background-color: var(--background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
        }

        .empty-state svg {
          color: var(--gray-color);
          margin-bottom: 1rem;
          opacity: 0.5;
        }

        .empty-state h3 {
          font-size: 1.125rem;
          margin: 0 0 0.5rem 0;
          color: var(--title-color);
        }

        .empty-state p {
          color: var(--gray-color);
          margin: 0;
          max-width: 300px;
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
          .status-header {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .status-actions {
            width: 100%;
            justify-content: flex-end;
          }
          
          .export-btn {
            flex: 1;
            justify-content: center;
          }
          
          .services-grid {
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: var(--spacing-md);
          }
          
          .dashboard-overview {
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          }
        }

        @media (max-width: 480px) {
          .services-grid {
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }
          
          .dashboard-overview {
            grid-template-columns: 1fr;
          }
        }

        @media (min-width: 1024px) {
          .services-grid {
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem;
          }
        }
      </style>
    `;
  }
}
