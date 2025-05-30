export default class SheetBranches extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/sheet/branches";
    this.branchesData = null;
    this._block = false;
    this._empty = false;
    this._loading = true;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch branches data first
    this.fetchBranchesData();
    window.addEventListener("scroll", this.handleScroll);

    // Set up event listeners after initial render
    setTimeout(() => {
      this._setupEventListeners();
    }, 100);
  }

  disconnectedCallback() {
    window.removeEventListener("scroll", this.handleScroll);
  }

  // Fetch branches data using the API
  fetchBranchesData = async () => {
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
        console.log("Authentication required for branches access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.branchesData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;

      // Log data structure to help debug inconsistencies
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.includes('dev')) {
        console.log('Branches data structure:', response.data);
      }

      this.branchesData = response;
      this.render();

    } catch (error) {
      console.error("Error fetching branches data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for branches access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.branchesData = null;
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
        this.fetchBranchesData();
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
    if (!this.branchesData || !this.branchesData.data || !this.branchesData.data.data) {
      console.error('No data available to export');
      return;
    }

    try {
      const branches = this.branchesData.data.data;
      // Create CSV content
      let csvContent = 'Branch Name,Address\n';

      // Add each branch data row
      branches.forEach(branch => {
        const row = [
          `"${branch.name}"`,
          `"${branch.address}"`
        ];
        csvContent += row.join(',') + '\n';
      });

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'branches.csv');
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
    if (this._empty || !this.branchesData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show branches layout with actual data
    return /* html */ `
      <div class="container">
        ${this._getHeaderHTML()}
        ${this._getBranchesLayoutHTML()}
      </div>
    `;
  };

  _getHeaderHTML = () => {
    const count = this.branchesData.data.count || 0;

    return /* html */ `
    <div class="branches-header">
      <div class="branches-title">
        <h1>Branch Locations</h1>
        <div class="branches-subtitle">
          <span>${count} ${count === 1 ? 'branch' : 'branches'} available</span>
        </div>
      </div>
      <div class="branches-actions">
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

  _getBranchesLayoutHTML = () => {
    const branches = this.branchesData.data.data || [];

    if (!branches.length) {
      return /* html */ `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
          <polyline points="9 22 9 12 15 12 15 22"></polyline>
        </svg>
        <h3>No branches available</h3>
        <p>There are no branch locations to display at this time.</p>
      </div>
      `;
    }

    return /* html */ `
    <div class="branches-grid">
      ${branches.map(branch => this._getBranchCardHTML(branch)).join('')}
    </div>
    `;
  };

  _getBranchCardHTML = (branch) => {
    // Encode the address for use in Google Maps URL
    const encodedAddress = encodeURIComponent(branch.address);
    const mapUrl = `https://www.google.com/maps/search/?api=1&query=${encodedAddress}`;

    return /* html */ `
    <div class="branch-card">
      <div class="branch-name">${branch.name}</div>
      <div class="branch-address">${branch.address}</div>
      <div class="branch-actions">
        <a href="${mapUrl}" target="_blank" class="map-link">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
            <line x1="8" y1="2" x2="8" y2="18"></line>
            <line x1="16" y1="6" x2="16" y2="22"></line>
          </svg>
          View on Map
        </a>
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
         An error occurred while fetching the branch data. Please check your connection and try again.
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

        /* Branches Header Styles */
        .branches-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .branches-title h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 0.25rem 0;
          color: var(--title-color);
        }

        .branches-subtitle {
          color: var(--gray-color);
          font-size: 0.875rem;
        }

        .branches-actions {
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

        /* Branches Grid Layout */
        .branches-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .branch-card {
          background-color: var(--background);
          border-radius: 0.75rem;
          box-shadow: var(--box-shadow);
          padding: 15px 15px;
          transition: all 0.2s ease;
          border: 1px solid var(--border-color, rgba(0, 0, 0, 0.05));
          position: relative;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .branch-card:hover {
          box-shadow: var(--card-box-shadow-alt);
          transform: translateY(-2px);
        }

        .branch-name {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          line-height: 1.3;
          margin: 0;
        }

        .branch-address {
          color: var(--text-color);
          font-family: var(--font-mono);
          font-size: 0.875rem;
          line-height: 1.4;
          font-weight: 500;
          flex-grow: 1;
        }

        .branch-actions {
          margin-top: auto;
          display: flex;
          justify-content: flex-end;
        }

        .map-link {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: none;
          margin: 6px 0 0;
          padding: 0.5rem 0.875rem;
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 500;
          text-decoration: none;
          cursor: pointer;
          transition: all 0.2s;
        }

        .map-link:hover {
          background: var(--accent-linear);
          transform: translateY(-1px);
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
          .branches-header {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .branches-actions {
            width: 100%;
          }
          
          .export-btn {
            flex: 1;
            justify-content: center;
          }

          .branches-grid {
            grid-template-columns: 1fr;
            gap: 0.75rem;
          }

          .branch-card {
            padding: 1.25rem;
          }
        }

        @media (max-width: 480px) {
          .container {
            padding: 1rem;
          }

          .branches-grid {
            gap: 0.5rem;
          }

          .branch-card {
            padding: 1rem;
          }

          .branch-name {
            font-size: 1rem;
          }

          .map-link {
            width: 100%;
            justify-content: center;
          }
        }
      </style>
    `;
  }
}
