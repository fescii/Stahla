export default class SheetGenerators extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/sheet/generators";
    this.generatorsData = null;
    this._block = false;
    this._empty = false;
    this._loading = true;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch generators data first
    this.fetchGeneratorsData();
    window.addEventListener("scroll", this.handleScroll);
    
    // Set up event listeners after initial render
    setTimeout(() => {
      this._setupEventListeners();
    }, 100);
  }

  disconnectedCallback() {
    window.removeEventListener("scroll", this.handleScroll);
  }

  // Fetch generators data using the API
  fetchGeneratorsData = async () => {
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
        console.log("Authentication required for generators access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.generatorsData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;
      
      // Log data structure to help debug inconsistencies
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.includes('dev')) {
        console.log('Generators data structure:', response.data);
      }
      
      this.generatorsData = response;
      this.render();

    } catch (error) {
      console.error("Error fetching generators data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for generators access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.generatorsData = null;
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
        this.fetchGeneratorsData();
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
    if (!this.generatorsData || !this.generatorsData.data || !this.generatorsData.data.data) {
      console.error('No data available to export');
      return;
    }

    try {
      const generators = this.generatorsData.data.data;
      // Create CSV content
      let csvContent = 'Generator Model,Event Rate (< 3 days),7-Day Rate,28-Day Rate\n';
      
      // Add each generator data row
      generators.forEach(generator => {
        // Format rates, handling null values
        const formatRateForCSV = (rate) => {
          return rate === null ? 'N/A' : rate;
        };
        
        const row = [
          `"${generator.name}"`,
          formatRateForCSV(generator.rate_event),
          formatRateForCSV(generator.rate_7_day),
          formatRateForCSV(generator.rate_28_day)
        ];
        csvContent += row.join(',') + '\n';
      });

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'generators.csv');
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
    if (this._empty || !this.generatorsData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show generators table with actual data
    return /* html */ `
      <div class="container">
        ${this._getHeaderHTML()}
        ${this._getGeneratorsTableHTML()}
      </div>
    `;
  };

  _getHeaderHTML = () => {
    const count = this.generatorsData.data.count || 0;
    
    return /* html */ `
    <div class="generators-header">
      <div class="generators-title">
        <h1>Generator Rentals</h1>
        <div class="generators-subtitle">
          <span>${count} ${count === 1 ? 'generator' : 'generators'} available</span>
        </div>
      </div>
      <div class="generators-actions">
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

  _getGeneratorsTableHTML = () => {
    const generators = this.generatorsData.data.data || [];
    
    if (!generators.length) {
      return /* html */ `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8h1a4 4 0 0 1 0 8h-1"></path>
          <path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path>
          <line x1="6" y1="1" x2="6" y2="4"></line>
          <line x1="10" y1="1" x2="10" y2="4"></line>
          <line x1="14" y1="1" x2="14" y2="4"></line>
        </svg>
        <h3>No generators available</h3>
        <p>There are no generator models to display at this time.</p>
      </div>
      `;
    }
    
    return /* html */ `
    <div class="generators-table-container">
      <div class="table-scroll-container">
        <table class="generators-table">
          <thead>
            <tr>
              <th class="sticky-column generator-name">Generator Model</th>
              <th>Event Rate<br><span class="rate-subtext">(< 3 days)</span></th>
              <th>Weekly Rate<br><span class="rate-subtext">(7 Day)</span></th>
              <th>Monthly Rate<br><span class="rate-subtext">(28 Day)</span></th>
              <th>Power Output</th>
            </tr>
          </thead>
          <tbody>
            ${generators.map(generator => this._getGeneratorRowHTML(generator)).join('')}
          </tbody>
        </table>
      </div>
    </div>
    `;
  };

  _getGeneratorRowHTML = (generator) => {
    // Extract the power output from the generator name (e.g., "3kW Generator" => "3kW")
    const powerOutput = generator.name.split(' ')[0];
    
    // Format rates, handling null values
    const formatRate = (rate) => {
      return rate === null ? '<span class="na-text">N/A</span>' : `$${rate.toLocaleString()}`;
    };
    
    return /* html */ `
    <tr>
      <td class="sticky-column generator-name">${generator.name}</td>
      <td class="price-cell">${formatRate(generator.rate_event)}</td>
      <td class="price-cell">${formatRate(generator.rate_7_day)}</td>
      <td class="price-cell">${formatRate(generator.rate_28_day)}</td>
      <td class="power-cell">
        <div class="power-rating">${powerOutput}</div>
      </td>
    </tr>
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
         An error occurred while fetching the generator data. Please check your connection and try again.
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
          background-color: var(--background);
          min-height: 100vh;
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

        /* Generators Header Styles */
        .generators-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .generators-title h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 0.25rem 0;
          color: var(--title-color);
        }

        .generators-subtitle {
          color: var(--gray-color);
          font-size: 0.875rem;
        }

        .generators-actions {
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

        /* Generators Table Styles */
        .generators-table-container {
          background-color: var(--background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          overflow: hidden;
          margin-bottom: 2rem;
        }

        .table-scroll-container {
          overflow-x: auto;
          max-width: 100%;
        }

        .generators-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
          font-size: 0.875rem;
        }

        .generators-table th {
          background-color: var(--stat-background);
          padding: 0.75rem 1rem;
          font-weight: 600;
          color: var(--title-color);
          border-bottom: var(--border);
          white-space: nowrap;
          position: sticky;
          top: 0;
          z-index: 10;
          text-align: center;
        }

        .generators-table td {
          padding: 0.75rem 1rem;
          border-bottom: var(--border);
          color: var(--text-color);
          text-align: center;
        }

        .sticky-column {
          position: sticky;
          left: 0;
          background-color: var(--background);
          z-index: 5;
          box-shadow: var(--image-shadow);
          text-align: left;
        }

        th.sticky-column {
          background-color: var(--stat-background);
          z-index: 15;
          text-align: left;
        }

        .generator-name {
          font-weight: 500;
          min-width: 180px;
          text-align: left;
        }

        .rate-subtext {
          font-size: 0.75rem;
          font-weight: normal;
          color: var(--gray-color);
        }

        .price-cell {
          text-align: center;
          font-variant-numeric: tabular-nums;
          font-feature-settings: "tnum";
          white-space: nowrap;
        }

        .power-cell {
          text-align: center;
        }

        .power-rating {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          background-color: var(--stat-background);
          color: var(--accent-color);
          border: var(--border-button);
          padding: 0.25rem 0.75rem;
          border-radius: 0.25rem;
          font-size: 0.875rem;
          font-weight: 500;
        }
        
        .na-text {
          color: var(--gray-color);
          font-style: italic;
          font-size: 0.875rem;
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

        /* Make the table rows alternating colors for better readability */
        .generators-table tbody tr:nth-child(odd) {
          background-color: var(--stat-background);
        }

        .generators-table tbody tr:hover {
          background-color: var(--hover-background);
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
          .generators-header {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .generators-actions {
            width: 100%;
          }
          
          .export-btn {
            flex: 1;
            justify-content: center;
          }
        }
      </style>
    `;
  }
}