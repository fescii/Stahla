export default class SheetStates extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/sheet/states";
    this.statesData = null;
    this._block = false;
    this._empty = false;
    this._loading = true;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch states data first
    this.fetchStatesData();
    window.addEventListener("scroll", this.handleScroll);

    // Set up event listeners after initial render
    setTimeout(() => {
      this._setupEventListeners();
    }, 100);
  }

  disconnectedCallback() {
    window.removeEventListener("scroll", this.handleScroll);
  }

  // Fetch states data using the API
  fetchStatesData = async () => {
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
        console.log("Authentication required for states access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.statesData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;

      // Log data structure to help debug inconsistencies
      if (
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1" ||
        window.location.hostname.includes("dev")
      ) {
        console.log("States data structure:", response.data);
      }

      this.statesData = response;
      this.render();
    } catch (error) {
      console.error("Error fetching states data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for states access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.statesData = null;
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
        this.fetchStatesData();
      });
    }
  };

  handleScroll = () => {
    // Event handling for scroll if needed
  };

  // Add event listeners for actions
  _setupEventListeners() {
    // Export button
    const exportBtn = this.shadowObj.querySelector(".export-btn");
    if (exportBtn) {
      exportBtn.addEventListener("click", this._handleExport);
    }
  }

  // Handle export functionality
  _handleExport = () => {
    // Check if we have data to export
    if (
      !this.statesData ||
      !this.statesData.data ||
      !this.statesData.data.data
    ) {
      console.error("No data available to export");
      return;
    }

    try {
      const states = this.statesData.data.data;
      // Create CSV content
      let csvContent = "State,Code\n";

      // Add each state data row
      states.forEach((state) => {
        const row = [`"${state.state}"`, `"${state.code}"`];
        csvContent += row.join(",") + "\n";
      });

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.setAttribute("href", url);
      link.setAttribute("download", "states.csv");
      link.style.visibility = "hidden";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error("Error exporting data:", error);
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
    if (this._empty || !this.statesData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show states layout with actual data
    return /* html */ `
      <div class="container">
        ${this._getHeaderHTML()}
        ${this._getStatesLayoutHTML()}
      </div>
    `;
  };

  _getHeaderHTML = () => {
    const count = this.statesData.data.count || 0;

    return /* html */ `
    <div class="states-header">
      <div class="states-title">
        <h1>Service States</h1>
        <div class="states-subtitle">
          <span>${count} ${count === 1 ? "state" : "states"} available</span>
        </div>
      </div>
      <div class="states-actions">
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

  _getStatesLayoutHTML = () => {
    const states = this.statesData.data.data || [];

    if (!states.length) {
      return /* html */ `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M20 9v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9"></path>
          <path d="M9 22V12h6v10M2 10.6L12 2l10 8.6"></path>
        </svg>
        <h3>No service states available</h3>
        <p>There are no states to display at this time.</p>
      </div>
      `;
    }

    return /* html */ `
    <div class="states-grid">
      ${states.map((state) => this._getStateCardHTML(state)).join("")}
    </div>
    `;
  };

  _getStateCardHTML = (state) => {
    return /* html */ `
    <div class="state-card">
      <div class="state-name">${state.state}</div>
      <div class="state-code">${state.code}</div>
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
         An error occurred while fetching the states data. Please check your connection and try again.
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
          width: 100%;
          background-color: var(--background);
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

        /* States Header Styles */
        .states-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .states-title h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 0.25rem 0;
          color: var(--title-color);
        }

        .states-subtitle {
          color: var(--gray-color);
          font-size: 0.875rem;
        }

        .states-actions {
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

        /* States Grid Layout */
        .states-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .state-card {
          background-color: var(--gray-background);
          border-radius: 0.75rem;
          padding: 8px 10px;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
        }

        .state-card:hover {
          transform: translateY(-2px);
        }

        .state-name {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 0.5rem;
          line-height: 1.3;
        }

        .state-code {
          font-family: var(--font-mono, 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace);
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--accent-color);
          background-color: var(--stat-background);
          padding: 0.25rem 0.5rem;
          border-radius: 0.375rem;
          display: inline-block;
          letter-spacing: 0.05em;
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
          .states-header {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .states-actions {
            width: 100%;
          }
          
          .export-btn {
            flex: 1;
            justify-content: center;
          }

          .states-grid {
            grid-template-columns: 1fr;
            gap: 0.75rem;
          }

          .state-card {
            padding: 1.25rem;
          }
        }

        @media (max-width: 480px) {
          .container {
            padding: 1rem;
          }

          .states-grid {
            gap: 0.5rem;
          }

          .state-card {
            padding: 1rem;
          }

          .state-name {
            font-size: 1rem;
          }
        }
      </style>
    `;
  };
}
