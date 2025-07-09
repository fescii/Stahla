export default class LocationLookup extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/webhook/location/lookup/sync";

    // Component state
    this.state = {
      isLoading: false,
      error: null,
      result: null,
      selectedLocation: "",
    };

    // Sample locations for quick testing
    this.sampleLocations = [
      "123 Peachtree St NE, Atlanta, GA 30303",
      "350 5th Ave, New York, NY 10118",
      "233 S Wacker Dr, Chicago, IL 60606",
      "1 Ferry Building, San Francisco, CA 94111",
      "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
      "400 Broad St, Seattle, WA 98109",
    ];

    this.render();
  }

  connectedCallback() {
    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();

    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  _setupEventListeners() {
    // Form submission
    const form = this.shadowObj.querySelector(".location-form");
    if (form) {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        this._handleSubmit();
      });
    }

    // Input field
    const locationInput = this.shadowObj.querySelector("#location-input");
    if (locationInput) {
      locationInput.addEventListener("input", (e) => {
        this.state.selectedLocation = e.target.value;
        if (e.target.value) {
          e.target.classList.add("with-value");
        } else {
          e.target.classList.remove("with-value");
        }
      });

      // Add focus events for animation
      locationInput.addEventListener("focus", () => {
        locationInput.parentElement.classList.add("focused");
      });

      locationInput.addEventListener("blur", () => {
        locationInput.parentElement.classList.remove("focused");
        if (locationInput.value) {
          locationInput.classList.add("with-value");
        }
      });

      // Set initial state if there's a value
      if (this.state.selectedLocation) {
        locationInput.classList.add("with-value");
      }
    }

    // Sample location buttons
    const sampleButtons = this.shadowObj.querySelectorAll(".sample-location");
    if (sampleButtons) {
      sampleButtons.forEach((button) => {
        button.addEventListener("click", () => {
          const locationInput = this.shadowObj.querySelector("#location-input");
          if (locationInput) {
            locationInput.value = button.dataset.location;
            locationInput.classList.add("with-value");
            this.state.selectedLocation = button.dataset.location;
          }
        });
      });
    }

    // Clear button
    const clearButton = this.shadowObj.querySelector(".clear-btn");
    if (clearButton) {
      clearButton.addEventListener("click", () => {
        this._resetForm();
      });
    }

    // Copy result button
    const copyButton = this.shadowObj.querySelector(".copy-result");
    if (copyButton) {
      copyButton.addEventListener("click", () => {
        this._copyResultToClipboard();
      });
    }
  }

  _handleSubmit = async () => {
    if (!this.state.selectedLocation.trim()) {
      this.state.error = "Please enter a delivery location";
      this.render();
      return;
    }

    this.state.isLoading = true;
    this.state.error = null;
    this.render();

    try {
      const response = await this.api.post(this.url, {
        content: "json",
        headers: {
          Authorization: "Bearer 7%FRtf@34hi",
        },
        body: {
          delivery_location: this.state.selectedLocation,
        },
      });

      if (!response.success) {
        this.state.error =
          response.error_message || "Failed to lookup location";
        this.state.isLoading = false;
        this.render();
        return;
      }

      this.state.result = response;
      this.state.isLoading = false;
      this.render();
    } catch (error) {
      console.error("Error looking up location:", error);
      this.state.isLoading = false;
      this.state.error = "An unexpected error occurred";
      this.render();
    }
  };

  _resetForm() {
    const locationInput = this.shadowObj.querySelector("#location-input");
    if (locationInput) {
      locationInput.value = "";
      locationInput.classList.remove("with-value");
    }

    this.state = {
      isLoading: false,
      error: null,
      result: null,
      selectedLocation: "",
    };

    this.render();
  }

  _copyResultToClipboard() {
    if (!this.state.result) return;

    const resultText = JSON.stringify(this.state.result, null, 2);
    navigator.clipboard
      .writeText(resultText)
      .then(() => {
        const copyButton = this.shadowObj.querySelector(".copy-result");
        if (copyButton) {
          const originalText = copyButton.textContent;
          copyButton.textContent = "Copied!";
          setTimeout(() => {
            copyButton.textContent = originalText;
          }, 2000);
        }
      })
      .catch((err) => {
        console.error("Failed to copy result: ", err);
      });
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody() {
    return /* html */ `
      <div class="container">
        <div class="location-lookup-container">
          <div class="header">
            <h1>Location Lookup</h1>
            <p class="subtitle">Find the nearest branch for a delivery location</p>
          </div>
          
          <div class="form-container">
            ${this.state.error
        ? `<div class="error-alert">${this.state.error}</div>`
        : ""
      }
            
            <form class="location-form">
              <div class="input-group">
                <label for="location-input">Delivery Location</label>
                <div class="input-wrapper">
                  <input 
                    type="text" 
                    id="location-input" 
                    class="location-input ${this.state.selectedLocation ? "with-value" : ""
      }" 
                    placeholder="Enter a delivery address (e.g. 123 Main St, City, State ZIP)" 
                    value="${this.state.selectedLocation}"
                    required
                  />
                  <svg class="input-icon" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                    <circle cx="12" cy="10" r="3"></circle>
                  </svg>
                </div>
              </div>
              
              <div class="quick-options">
                <h3>Quick Search Options</h3>
                <div class="sample-locations">
                  ${this.sampleLocations
        .map(
          (location) => `
                    <button 
                      type="button" 
                      class="sample-location" 
                      data-location="${location}"
                    >
                      ${location.split(",")[0]}
                    </button>
                  `
        )
        .join("")}
                </div>
              </div>
              
              <div class="form-actions">
                <button type="button" class="clear-btn">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                  Clear
                </button>
                <button type="submit" class="lookup-btn" ${this.state.isLoading ? "disabled" : ""
      }>
                  ${this.state.isLoading
        ? this._getLoadingSpinner() + "Looking up..."
        : "Lookup Location"
      }
                </button>
              </div>
            </form>
          </div>
          
          ${this.state.result ? this._getResultTemplate() : ""}
        </div>
      </div>
    `;
  }

  _getResultTemplate() {
    const result = this.state.result;
    if (!result || !result.data || !result.data.distance_result) {
      return "";
    }

    const distanceResult = result.data.distance_result;
    const processingTime = result.data.processing_time_ms;

    // Calculate hours and minutes from seconds
    const durationHours = Math.floor(distanceResult.duration_seconds / 3600);
    const durationMinutes = Math.floor(
      (distanceResult.duration_seconds % 3600) / 60
    );

    // Format duration display
    const formatDuration = (totalSeconds) => {
      const hours = Math.floor(totalSeconds / 3600);
      const minutes = Math.floor((totalSeconds % 3600) / 60);

      if (hours > 0) {
        return `${hours} hours ${minutes} minutes`;
      } else {
        return `${minutes} minutes`;
      }
    };

    return /* html */ `
      <div class="result-container">
        <div class="result-header">
          <h2>Location Results</h2>
          <button type="button" class="copy-result">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            Copy JSON
          </button>
        </div>
        
        <div class="result-content">
          <div class="result-grid">
            <div class="detail-card address-card">
              <div class="card-header">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
                <h3>Delivery Location</h3>
              </div>
              <p class="branch-name">Lead Address</p>
              <p class="delivery-address">${distanceResult.delivery_location
      }</p>
            </div>
            
            <div class="detail-card branch-card">
              <div class="card-header">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="3" y1="9" x2="21" y2="9"></line>
                  <line x1="3" y1="15" x2="21" y2="15"></line>
                  <line x1="9" y1="3" x2="9" y2="21"></line>
                  <line x1="15" y1="3" x2="15" y2="21"></line>
                </svg>
                <h3>Nearest Branch</h3>
              </div>
              <p class="branch-name">${distanceResult.nearest_branch.name}</p>
              <p class="branch-address">${distanceResult.nearest_branch.address
      }</p>
            </div>
          </div>
          
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="2" y1="12" x2="22" y2="12"></line>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
                </svg>
              </div>
              <div class="metric-content">
                <h4>Distance</h4>
                <div class="metric-value">${distanceResult.distance_miles.toFixed(
        2
      )} miles</div>
                <div class="metric-secondary">${(
        distanceResult.distance_meters / 1000
      ).toFixed(2)} kilometers</div>
              </div>
            </div>
            
            <div class="metric-card">
              <div class="metric-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <div class="metric-content">
                <h4>Travel Time</h4>
                <div class="metric-value">${formatDuration(distanceResult.duration_seconds)}</div>
                <div class="metric-secondary">${distanceResult.duration_seconds.toLocaleString()} seconds total</div>
              </div>
            </div>
            
            <div class="metric-card service-area-card">
              <div class="metric-icon ${(distanceResult.within_service_area === true) ? 'service-area-yes' : 'service-area-no'}">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  ${(distanceResult.within_service_area === true)
        ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>'
        : '<circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>'
      }
                </svg>
              </div>
              <div class="metric-content">
                <h4>Service Area</h4>
                <div class="metric-value ${(distanceResult.within_service_area === true) ? 'within-service' : (distanceResult.within_service_area === false) ? 'outside-service' : 'unknown-service'}">
                  ${(distanceResult.within_service_area === true) ? 'Within Area' : (distanceResult.within_service_area === false) ? 'Outside Area' : 'Unknown'}
                </div>
                <div class="metric-secondary">
                  ${(distanceResult.within_service_area === true) ? 'Service available' : (distanceResult.within_service_area === false) ? 'Outside coverage zone' : 'Coverage status unavailable'}
                </div>
              </div>
            </div>
          </div>
          
          ${result.data.message ? `
          <div class="message-container">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <p class="message">${result.data.message}</p>
          </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _getLoadingSpinner() {
    return /* html */ `
      <svg class="spinner" viewBox="0 0 50 50">
        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
      </svg>
    `;
  }

  getStyles() {
    return /* html */ `
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-text);
          color: var(--text-color);
          --primary-color: var(--accent-color);
          --primary-hover: var(--accent-alt);
          --success-color: var(--success-color);
          --warning-color: var(--alt-color);
          --error-color: var(--error-color);
          --info-color: var(--accent-color);
          --background-color: var(--background);
          --border-color: var(--border);
          --card-bg: var(--author-background);
        }

        * {
          box-sizing: border-box;
        }
        
        .container {
          width: 100%;
          margin: 0;
          padding: 2rem 15px 20px;
        }
        
        .location-lookup-container {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        
        h1 {
          font-size: 1.875rem;
          font-weight: 600;
          margin: 0 0 0.5rem 0;
          color: var(--title-color);
          line-height: 1.2;
        }
        
        .subtitle {
          font-size: 1rem;
          color: var(--gray-color);
          margin: 0;
        }
        
        /* Form Styling */
        .form-container {
          background-color: var(--background-color);
          border-bottom: var(--border);
          padding: 1.5rem 0;
        }
        
        .location-form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        
        .input-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          position: relative;
        }
        
        .input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }
        
        .input-icon {
          position: absolute;
          right: 1rem;
          color: var(--gray-color);
          pointer-events: none;
          transition: color 0.2s ease;
        }
        
        label {
          font-weight: 500;
          font-size: 0.875rem;
          color: var(--title-color);
          transition: color 0.2s ease;
        }
        
        .location-input {
          width: 100%;
          padding: 0.875rem 1rem;
          font-size: 1rem;
          border: var(--input-border);
          border-radius: 0.5rem;
          background-color: var(--background-color);
          transition: all 0.2s ease;
          padding-right: 3rem;
        }
        
        .location-input::placeholder {
          color: var(--gray-color);
          opacity: 0.7;
        }
        
        .location-input:focus {
          outline: none;
          border: var(--input-border-focus);
          border-bottom: 2px solid var(--primary-color);
        }
        
        .location-input.with-value {
          border-color: var(--primary-color);
          color: var(--primary-color);
        }
        
        .location-input.with-value + .input-icon {
          color: var(--primary-color);
        }
        
        .input-group.focused label {
          color: var(--primary-color);
        }
        
        .quick-options {
          margin-top: 0.5rem;
        }
        
        .quick-options h3 {
          font-size: 0.875rem;
          font-weight: 500;
          margin: 0 0 0.75rem 0;
          color: var(--gray-color);
        }
        
        .sample-locations {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 0.75rem;
        }
        
        .sample-location {
          padding: 0.75rem 1rem;
          background-color: var(--card-bg);
          border: var(--border);
          border-radius: 0.5rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-color);
          cursor: pointer;
          transition: all 0.2s;
          text-align: left;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          position: relative;
          z-index: 1;
        }
        
        .sample-location::before {
          content: "";
          position: absolute;
          inset: 0;
          border-radius: 0.5rem;
          background-color: var(--primary-color);
          opacity: 0;
          z-index: -1;
          transition: opacity 0.2s ease;
        }
        
        .sample-location:hover {
          border-color: var(--primary-color);
          color: var(--primary-color);
          transform: translateY(-2px);
          border-bottom: 2px solid var(--primary-color);
        }
        
        .sample-location:active {
          transform: translateY(0);
        }
        
        .form-actions {
          display: flex;
          justify-content: flex-end;
          gap: 1rem;
          margin-top: 0.5rem;
        }
        
        .clear-btn {
          padding: 0.75rem 1.25rem;
          background-color: transparent;
          border: var(--border-button);
          border-radius: 0.5rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-color);
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .clear-btn:hover {
          background-color: var(--card-bg);
          border: var(--action-border);
          color: var(--primary-color);
        }
        
        .clear-btn:active {
          transform: scale(0.98);
        }
        
        .lookup-btn {
          padding: 0.75rem 1.5rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: none;
          border-radius: 0.5rem;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          position: relative;
          overflow: hidden;
          z-index: 1;
        }
        
        .lookup-btn::before {
          content: "";
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: var(--accent-linear);
          transition: left 0.3s ease;
          z-index: -1;
        }
        
        .lookup-btn:hover:not(:disabled)::before {
          left: 0;
        }
        
        .lookup-btn:active:not(:disabled) {
          transform: scale(0.98);
        }
        
        .lookup-btn:disabled {
          opacity: 0.7;
          cursor: not-allowed;
        }
        
        .error-alert {
          padding: 0.875rem 1rem;
          background-color: var(--error-background);
          border-left: 3px solid var(--error-color);
          color: var(--error-color);
          border-radius: 0.375rem;
          margin-bottom: 1.25rem;
          font-size: 0.875rem;
          border-bottom: 2px solid var(--error-color);
        }
        
        .info-alert {
          padding: 0.875rem 1rem;
          background-color: var(--tab-background);
          border-left: 3px solid var(--accent-color);
          color: var(--accent-color);
          border-radius: 0.375rem;
          margin-bottom: 1.25rem;
          font-size: 0.875rem;
          display: flex;
          align-items: center;
          gap: 0.75rem;
          border-bottom: 2px solid var(--accent-color);
        }
        
        .info-alert svg {
          width: 1.125rem;
          height: 1.125rem;
          flex-shrink: 0;
        }
        
        /* Result Styling */
        .result-container {
          background-color: var(--background-color);
          padding: 0;
          overflow: hidden;
        }
        
        .result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.25rem;
        }
        
        .result-header h2 {
          font-size: 1.25rem;
          font-weight: 600;
          margin: 0;
          color: var(--title-color);
        }
        
        .copy-result {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 0.75rem;
          background-color: var(--card-bg);
          border: var(--border-button);
          border-radius: 0.375rem;
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--text-color);
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .copy-result:hover {
          background-color: var(--background-color);
          border: var(--topic-border-active);
          color: var(--primary-color);
          transform: translateY(-2px);
        }
        
        .copy-result:active {
          transform: translateY(0);
        }        .copy-result svg {
          width: 0.875rem;
          height: 0.875rem;
        }

        /* Result Grid */
        .result-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .detail-card {
          padding: 1.25rem;
          border-radius: 0.75rem;
          background: var(--card-bg);
        }
        
        .card-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 1rem;
        }
        
        .card-header svg {
          color: var(--primary-color);
        }
        
        .card-header h3 {
          font-size: 1rem;
          font-weight: 600;
          margin: 0;
          color: var(--title-color);
        }
        
        .delivery-address, .branch-name, .branch-address {
          margin: 0;
          font-size: 0.875rem;
          line-height: 1.5;
        }
        
        .branch-name {
          font-weight: 600;
          margin-bottom: 0.25rem;
          color: var(--title-color);
        }
        
        /* Metrics Grid */
        .metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .metric-card {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          padding: 1.25rem;
          background-color: var(--card-bg);
          border-radius: 0.75rem;
          border-bottom: 2px solid var(--border-color);
        }
        
        .metric-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 9999px;
          background-color: var(--tab-background);
          color: var(--primary-color);
          flex-shrink: 0;
        }

        .metric-card .metric-content {
          flex: unset;
          width: max-content;
        }
        
        .metric-content h4 {
          font-size: 0.875rem;
          font-weight: 600;
          margin: 0 0 0.5rem 0;
          color: var(--title-color);
        }
        
        .metric-value {
          font-weight: 600;
          font-size: 1rem;
          color: var(--text-color);
          margin-bottom: 0.25rem;
        }
        
        .metric-secondary {
          font-size: 0.75rem;
          color: var(--gray-color);
        }
        
        /* Service Area specific styles */
        .service-area-card .metric-icon.service-area-yes {
          background: linear-gradient(145deg, #10b981 0%, #047857 100%);
          color: white;
        }
        
        .service-area-card .metric-icon.service-area-no {
          background: linear-gradient(145deg, #ef4444 0%, #dc2626 100%);
          color: white;
        }
        
        .metric-value.within-service {
          color: #10b981;
          font-weight: 700;
        }
        
        .metric-value.outside-service {
          color: #ef4444;
          font-weight: 700;
        }
        
        .metric-value.unknown-service {
          color: #f59e0b;
          font-weight: 700;
        }
        
        .service-area-card .metric-secondary {
          color: var(--gray-color);
          font-style: italic;
        }
        
        .message-container {
          padding: 1rem;
          background-color: var(--tab-background);
          border-radius: 0.5rem;
          display: flex;
          align-items: flex-start;
          gap: 0.75rem;
        }
        
        .message-container svg {
          color: var(--primary-color);
          flex-shrink: 0;
          margin-top: 0.125rem;
        }
         .message {
          margin: 0;
          font-size: 0.875rem;
          color: var(--primary-color);
          font-weight: 500;
          line-height: 1.5;
        }

        /* Loading Spinner */
        .spinner {
          animation: rotate 2s linear infinite;
          width: 1.125rem;
          height: 1.125rem;
          margin-right: 0.5rem;
        }
        
        .spinner .path {
          stroke: var(--white-color);
          stroke-linecap: round;
          animation: dash 1.5s ease-in-out infinite;
        }
        
        /* Animations */
        @keyframes rotate {
          100% {
            transform: rotate(360deg);
          }
        }
        
        @keyframes dash {
          0% {
            stroke-dasharray: 1, 150;
            stroke-dashoffset: 0;
          }
          50% {
            stroke-dasharray: 90, 150;
            stroke-dashoffset: -35;
          }
          100% {
            stroke-dasharray: 90, 150;
            stroke-dashoffset: -124;
          }
        }
         @keyframes pulse {
          0%, 100% {
            transform: scale(0.75);
            opacity: 0.5;
          }
          50% {
            transform: scale(1);
            opacity: 1;
          }
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          .sample-locations {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          }
          
          .dashboard-content {
            grid-template-columns: 1fr;
            gap: 2rem;
          }
          
          .form-actions {
            flex-direction: column-reverse;
          }
          
          .clear-btn, .lookup-btn {
            width: 100%;
            justify-content: center;
          }
        }
      </style>
    `;
  }
}
