export default class SheetConfig extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/sheet/config";
    this.configData = null;
    this._block = false;
    this._empty = false;
    this._loading = true;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch config data first
    this.fetchConfigData();
    window.addEventListener("scroll", this.handleScroll);

    // Set up event listeners after initial render
    setTimeout(() => {
      this._setupEventListeners();
    }, 100);
  }

  disconnectedCallback() {
    window.removeEventListener("scroll", this.handleScroll);
  }

  // Fetch config data using the API
  fetchConfigData = async () => {
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
        console.log("Authentication required for config access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.configData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;

      // Log data structure to help debug inconsistencies
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.includes('dev')) {
        console.log('Config data structure:', response.data);
      }

      this.configData = response;
      this.render();

    } catch (error) {
      console.error("Error fetching config data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for config access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.configData = null;
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
        this.fetchConfigData();
      });
    }
  };

  handleScroll = () => {
    // Event handling for scroll if needed
  };

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
    if (!this.configData || !this.configData.data || !this.configData.data.data) {
      console.error('No data available to export');
      return;
    }

    try {
      const config = this.configData.data.data;
      // Create CSV content for seasonal multipliers
      let csvContent = 'Config Type: ' + config.config_type + '\n\n';

      // Add delivery config
      csvContent += 'Delivery Configuration\n';
      csvContent += 'Base Fee,Free Miles Threshold\n';
      csvContent += `${config.delivery_config.base_fee},${config.delivery_config.free_miles_threshold}\n\n`;

      // Add seasonal multipliers
      csvContent += 'Seasonal Multipliers\n';
      csvContent += 'Name,Start Date,End Date,Rate\n';

      config.seasonal_multipliers_config.tiers.forEach(tier => {
        const row = [
          `"${tier.name}"`,
          tier.start_date,
          tier.end_date,
          tier.rate
        ];
        csvContent += row.join(',') + '\n';
      });

      csvContent += '\nLast Updated: ' + config.last_updated_mongo;

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'pricing_config.csv');
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
    if (this._empty || !this.configData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show config data with actual data
    return /* html */ `
      <div class="container">
        ${this._getHeaderHTML()}
        ${this._getDeliveryConfigHTML()}
        ${this._getMultipliersLayoutHTML()}
      </div>
    `;
  };

  _getHeaderHTML = () => {
    const config = this.configData.data.data;
    const lastUpdated = new Date(config.last_updated_mongo).toLocaleString();

    return /* html */ `
    <div class="config-header">
      <div class="config-title">
        <h1>Pricing & Delivery Configuration</h1>
        <div class="config-subtitle">
          <span>Last updated: ${lastUpdated}</span>
        </div>
      </div>
      <div class="config-actions">
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

  _getDeliveryConfigHTML = () => {
    const config = this.configData.data.data;
    const deliveryConfig = config.delivery_config;

    return /* html */ `
    <div class="config-section">
      <h2 class="section-title">Delivery Configuration</h2>
      <div class="delivery-card">
        <div class="delivery-item">
          <span class="delivery-label">Base Delivery Fee</span>
          <span class="delivery-value">$${deliveryConfig.base_fee.toFixed(2)}</span>
        </div>
        <div class="delivery-item">
          <span class="delivery-label">Free Miles Threshold</span>
          <span class="delivery-value">${deliveryConfig.free_miles_threshold} miles</span>
        </div>
        <div class="delivery-item">
          <span class="delivery-label">Per Mile Rate</span>
          <span class="delivery-value">${deliveryConfig.per_mile_rate ? '$' + deliveryConfig.per_mile_rate.toFixed(2) : 'Not configured'}</span>
        </div>
      </div>
    </div>
    `;
  };

  _getMultipliersLayoutHTML = () => {
    const config = this.configData.data.data;
    const tiers = config.seasonal_multipliers_config.tiers || [];

    if (!tiers.length) {
      return /* html */ `
      <div class="config-section">
        <h2 class="section-title">Seasonal Rate Multipliers</h2>
        <div class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
          </svg>
          <h3>No seasonal multipliers configured</h3>
          <p>There are no seasonal rate multipliers available at this time.</p>
        </div>
      </div>
      `;
    }

    return /* html */ `
    <div class="config-section">
      <h2 class="section-title">Seasonal Rate Multipliers</h2>
      <div class="multipliers-grid">
        ${tiers.map(tier => this._getMultiplierCardHTML(tier)).join('')}
      </div>
    </div>
    `;
  };

  _getMultiplierCardHTML = (tier) => {
    // Format dates and check if the tier is currently active
    const startDate = new Date(tier.start_date);
    const endDate = new Date(tier.end_date);
    const now = new Date();
    const isActive = now >= startDate && now <= endDate;
    const status = isActive ? 'Active' : (now < startDate ? 'Upcoming' : 'Expired');
    const statusClass = isActive ? 'status-active' : (now < startDate ? 'status-upcoming' : 'status-expired');

    // Format display dates
    const startDateFormatted = startDate.toLocaleDateString();
    const endDateFormatted = endDate.toLocaleDateString();

    return /* html */ `
    <div class="multiplier-card">
      <div class="card-header">
        <h3 class="tier-name">${tier.name}</h3>
        <span class="status-badge ${statusClass}">${status}</span>
      </div>
      <div class="card-content">
        <div class="date-range">
          <div class="date-item">
            <span class="date-label">Start Date</span>
            <span class="date-value">${startDateFormatted}</span>
          </div>
          <div class="date-item">
            <span class="date-label">End Date</span>
            <span class="date-value">${endDateFormatted}</span>
          </div>
        </div>
        <div class="rate-display">
          <span class="rate-label">Rate Multiplier</span>
          <span class="rate-value">${tier.rate.toFixed(2)}x</span>
        </div>
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
    return `
      <div class="finish">
        <h2 class="finish__title">Something went wrong!</h2>
        <p class="desc">
         An error occurred while fetching the configuration data. Please check your connection and try again.
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
          padding: 15px 0;
          background-color: var(--background);
          width: 100%;
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

        /* Config Header Styles */
        .config-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .config-title h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 0.25rem 0;
          color: var(--title-color);
        }

        .config-subtitle {
          color: var(--gray-color);
          font-size: 0.875rem;
        }

        .config-actions {
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

        /* Config Section Styles */
        .config-section {
          margin-bottom: 2rem;
        }

        .section-title {
          font-size: 1.125rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: var(--title-color);
          padding-bottom: 0.5rem;
        }

        /* Delivery Card Styles */
        .delivery-card {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
          background-color: var(--background);
          border-radius: 0.5rem;
          background: var(--gray-background);
          padding: 1.5rem;
        }

        .delivery-item {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .delivery-label {
          font-size: 0.875rem;
          color: var(--gray-color);
        }

        .delivery-value {
          font-size: 1.25rem;
          font-weight: 500;
          color: var(--title-color);
        }

        /* Multipliers Grid Styles */
        .multipliers-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 1.5rem;
        }

        .multiplier-card {
          background-color: var(--background);
          border-radius: 0.5rem;
          padding: 1.5rem;
          transition: all 0.2s ease;
          border: var(--border);
        }

        .multiplier-card:hover {
          transform: translateY(-2px);
        }

        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
          padding-bottom: 1rem;
          border-bottom: var(--border);
        }

        .tier-name {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          margin: 0;
          line-height: 1.4;
        }

        .card-content {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .date-range {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        .date-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .date-label {
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .date-value {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-color);
        }

        .rate-display {
          text-align: center;
          padding: 1rem;
          background-color: var(--stat-background);
          border-radius: 0.375rem;
          border: 1px solid var(--border);
        }

        .rate-label {
          display: block;
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 0.5rem;
        }

        .rate-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--accent-color);
          font-variant-numeric: tabular-nums;
          font-feature-settings: "tnum";
        }

        .status-badge {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 500;
          white-space: nowrap;
        }

        .status-active {
          background-color: rgba(16, 185, 129, 0.2);
          color: #10b981;
        }

        .status-upcoming {
          background-color: rgba(59, 130, 246, 0.2);
          color: #3b82f6;
        }

        .status-expired {
          background-color: rgba(107, 114, 128, 0.2);
          color: #6b7280;
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
          .config-header {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .config-actions {
            width: 100%;
          }
          
          .export-btn {
            flex: 1;
            justify-content: center;
          }

          .multipliers-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
          }

          .date-range {
            grid-template-columns: 1fr;
            gap: 0.75rem;
          }

          .rate-value {
            font-size: 1.25rem;
          }
        }

        @media (max-width: 480px) {
          .container {
            padding: 1rem;
          }

          .multiplier-card {
            padding: 1rem;
          }

          .tier-name {
            font-size: 1rem;
          }

          .card-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }
        }
      </style>
    `;
  }
}
