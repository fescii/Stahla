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
  }

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
        ${this._getStatusGridHTML()}
        ${this._getStatusDetailsHTML()}
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
    <div class="status-grid">
      ${services.map(service => this._getServiceCardHTML(service)).join('')}
    </div>
    `;
  };

  _getServiceCardHTML = (service) => {
    // Format timestamp
    const timestamp = new Date(service.timestamp).toLocaleString();
    
    // Determine status class
    let statusClass = 'unknown';
    let statusIcon = '';
    
    switch (service.status) {
      case 'ok':
        statusClass = 'operational';
        statusIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>';
        break;
      case 'warning':
        statusClass = 'degraded';
        statusIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>';
        break;
      case 'error':
        statusClass = 'outage';
        statusIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>';
        break;
      default:
        statusIcon = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    }
    
    // Format service name
    const formattedName = service.service_name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
    
    return /* html */ `
    <div class="service-card ${statusClass}" data-service="${service.service_name}">
      <div class="service-icon">
        ${this._getServiceIcon(service.service_name)}
      </div>
      <div class="service-info">
        <h3 class="service-name">${formattedName}</h3>
        <div class="service-status">
          <span class="status-icon">${statusIcon}</span>
          <span class="status-message">${service.message}</span>
        </div>
        <div class="service-time">${timestamp}</div>
      </div>
    </div>
    `;
  };

  _getServiceIcon = (serviceName) => {
    // Map service names to appropriate icons
    switch (serviceName) {
      case 'mongodb':
        return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
        </svg>`;
      case 'redis':
        return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/>
          <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>
        </svg>`;
      case 'bland_ai':
        return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0-3 3v1a3 3 0 0 0-3 3v2a3 3 0 0 0 3 3h12a3 3 0 0 0 3-3v-2a3 3 0 0 0-3-3h-9V9a1 1 0 0 1 1-1h8a3 3 0 0 0 3-3V3a3 3 0 0 0-3-3z"/>
          <circle cx="8" cy="16" r="1"/>
          <circle cx="16" cy="16" r="1"/>
        </svg>`;
      case 'google_sheets':
        return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="3" y1="15" x2="21" y2="15"/>
          <line x1="9" y1="3" x2="9" y2="21"/>
          <line x1="15" y1="3" x2="15" y2="21"/>
        </svg>`;
      case 'hubspot':
        return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" id="hubspot">
          <path fill="currentColor" d="M22.75 14.358c0-3.056-2.221-5.587-5.132-6.033V5.437c.815-.347 1.313-1.116 1.313-2.011 0-1.223-.974-2.245-2.189-2.245s-2.175 1.022-2.175 2.245c0 .895.499 1.664 1.313 2.011v2.869a5.979 5.979 0 0 0-1.989.638c-1.286-.98-5.472-4.017-7.865-5.85a2.46 2.46 0 0 0 .093-.647A2.443 2.443 0 0 0 3.681 0 2.441 2.441 0 0 0 1.25 2.447a2.442 2.442 0 0 0 2.431 2.452c.456 0 .88-.136 1.248-.356l7.6 5.377-.002-.001a6.099 6.099 0 0 0-1.9 4.434c0 1.373.452 2.639 1.211 3.656l-2.305 2.334a1.892 1.892 0 0 0-.652-.117c-.503 0-.974.197-1.327.553-.354.356-.549.834-.549 1.341s.196.98.549 1.336c.354.356.829.544 1.328.544.503 0 .974-.183 1.332-.544a1.888 1.888 0 0 0 .461-1.903l2.329-2.353a6.006 6.006 0 0 0 3.693 1.261c3.347 0 6.053-2.733 6.053-6.103zm-6.055 3.229c-1.774 0-3.213-1.448-3.213-3.234s1.438-3.234 3.213-3.234c1.774 0 3.213 1.448 3.213 3.234s-1.439 3.234-3.213 3.234z"></path>
        </svg>`;
      default:
        return `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
          <line x1="6" y1="6" x2="6.01" y2="6"/>
          <line x1="6" y1="18" x2="6.01" y2="18"/>
        </svg>`;
    }
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
    <div class="status-details">
      <h2 class="details-title">Status History</h2>
      <div class="status-timeline">
        ${sortedServices.map(service => {
          const timestamp = new Date(service.timestamp);
          const formattedName = service.service_name
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
            
          let statusBadge = '';
          switch (service.status) {
            case 'ok':
              statusBadge = '<span class="status-badge operational">Operational</span>';
              break;
            case 'warning':
              statusBadge = '<span class="status-badge degraded">Degraded</span>';
              break;
            case 'error':
              statusBadge = '<span class="status-badge outage">Outage</span>';
              break;
            default:
              statusBadge = '<span class="status-badge unknown">Unknown</span>';
          }
          
          return /* html */ `
          <div class="timeline-item">
            <div class="timeline-content">
              <div class="timeline-dot ${service.status === 'ok' ? 'operational' : (service.status === 'warning' ? 'degraded' : (service.status === 'error' ? 'outage' : 'unknown'))}"></div>
              <div class="timeline-header">
                <h3 class="timeline-service">${formattedName}</h3>
                ${statusBadge}
              </div>
              <p class="timeline-message">${service.message}</p>
              <div class="timeline-time">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                ${timestamp.toLocaleString()}
              </div>
            </div>
          </div>
          `;
        }).join('')}
      </div>
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
          background-color: rgba(16, 185, 129, 0.1);
          color: rgb(16, 185, 129);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-indicator.degraded {
          background-color: rgba(245, 158, 11, 0.1);
          color: rgb(245, 158, 11);
          border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .status-indicator.outage {
          background-color: rgba(239, 68, 68, 0.1);
          color: rgb(239, 68, 68);
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-right: 0.5rem;
        }

        .operational .status-dot {
          background-color: rgb(16, 185, 129);
          box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
        }

        .degraded .status-dot {
          background-color: rgb(245, 158, 11);
          box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
        }

        .outage .status-dot {
          background-color: rgb(239, 68, 68);
          box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.2);
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
          gap: 0.5rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: var(--action-border);
          padding: 0.5rem 1rem;
          border-radius: 0.375rem;
          font-weight: 500;
          font-size: 0.875rem;
          cursor: pointer;
          transition: all 0.2s;
        }

        .export-btn:hover {
          background: var(--accent-linear);
        }

        .export-btn svg {
          stroke-width: 2px;
        }

        /* Status Grid Styles */
        .status-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .service-card {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1.25rem;
          background-color: var(--background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          border-left: 4px solid transparent;
          transition: transform 0.2s, box-shadow 0.2s;
        }

        .service-card:hover {
          transform: translateY(-2px);
          box-shadow: var(--hover-box-shadow);
        }

        .service-card.operational {
          border-left-color: rgb(16, 185, 129);
        }

        .service-card.degraded {
          border-left-color: rgb(245, 158, 11);
        }

        .service-card.outage {
          border-left-color: rgb(239, 68, 68);
        }

        .service-card.unknown {
          border-left-color: rgb(107, 114, 128);
        }

        .service-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 48px;
          height: 48px;
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          color: var(--accent-color);
        }

        .service-info {
          flex: 1;
          min-width: 0;
        }

        .service-name {
          font-size: 1rem;
          font-weight: 600;
          margin: 0 0 0.375rem 0;
          color: var(--title-color);
        }

        .service-status {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.375rem;
        }

        .status-icon {
          color: inherit;
        }

        .operational .status-icon {
          color: rgb(16, 185, 129);
        }

        .degraded .status-icon {
          color: rgb(245, 158, 11);
        }

        .outage .status-icon {
          color: rgb(239, 68, 68);
        }

        .status-message {
          font-size: 0.875rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .service-time {
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        /* Status Details Styles */
        .status-details {
          margin-top: 3rem;
        }

        .details-title {
          font-size: 1.25rem;
          font-weight: 600;
          margin-bottom: 1.5rem;
          color: var(--title-color);
          padding-bottom: 0.5rem;
          border-bottom: var(--border);
        }

        .status-timeline {
          position: relative;
        }

        .status-timeline:before {
          content: '';
          position: absolute;
          top: 0;
          bottom: 0;
          left: 17px;
          width: 2px;
          background-color: var(--border-color);
          z-index: 1;
        }

        .timeline-item {
          position: relative;
          margin-bottom: 1.5rem;
        }

        .timeline-item:last-child {
          margin-bottom: 0;
        }

        .timeline-dot {
          position: absolute;
          left: 1rem;
          top: 1.25rem;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background-color: rgb(107, 114, 128);
          border: 4px solid var(--background);
          z-index: 2;
        }

        .timeline-dot.operational {
          background-color: rgb(16, 185, 129);
        }

        .timeline-dot.degraded {
          background-color: rgb(245, 158, 11);
        }

        .timeline-dot.outage {
          background-color: rgb(239, 68, 68);
        }

        .timeline-content {
          background-color: var(--background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          padding: 1.25rem 1rem 1rem 2.5rem;
          position: relative;
        }

        .timeline-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }

        .timeline-service {
          font-size: 1rem;
          font-weight: 600;
          margin: 0;
          color: var(--title-color);
        }

        .status-badge {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .status-badge.operational {
          background-color: rgba(16, 185, 129, 0.1);
          color: rgb(16, 185, 129);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .status-badge.degraded {
          background-color: rgba(245, 158, 11, 0.1);
          color: rgb(245, 158, 11);
          border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .status-badge.outage {
          background-color: rgba(239, 68, 68, 0.1);
          color: rgb(239, 68, 68);
          border: 1px solid rgba(239, 68, 68, 0.2);
        }

        .status-badge.unknown {
          background-color: rgba(107, 114, 128, 0.1);
          color: rgb(107, 114, 128);
          border: 1px solid rgba(107, 114, 128, 0.2);
        }

        .timeline-message {
          font-size: 0.875rem;
          margin: 0 0 0.5rem 0;
          color: var(--text-color);
        }

        .timeline-time {
          display: flex;
          align-items: center;
          gap: 0.375rem;
          font-size: 0.75rem;
          color: var(--gray-color);
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
          
          .timeline-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }
        }
      </style>
    `;
  }
}
