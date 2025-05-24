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
      secondResult: null,
      selectedLocation: "",
      showComparison: false,
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

    // Tab switching
    const tabs = this.shadowObj.querySelectorAll(".tab:not(.disabled)");
    if (tabs) {
      tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
          // Skip if tab is disabled
          if (tab.classList.contains("disabled")) return;

          // Deactivate all tabs and tab content
          this.shadowObj
            .querySelectorAll(".tab")
            .forEach((t) => t.classList.remove("active"));
          this.shadowObj
            .querySelectorAll(".tab-content")
            .forEach((c) => c.classList.remove("active"));

          // Activate selected tab and content
          tab.classList.add("active");
          const tabName = tab.dataset.tab;
          const content = this.shadowObj.querySelector(`.${tabName}-tab`);
          if (content) {
            content.classList.add("active");
          }
        });
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
    this.state.showComparison = false;
    this.render();

    try {
      // First API request
      const firstStartTime = performance.now();

      const firstResponse = await this.api.post(this.url, {
        content: "json",
        headers: {
          Authorization: "Bearer 7%FRtf@34hi",
        },
        body: {
          delivery_location: this.state.selectedLocation,
        },
      });

      const firstEndTime = performance.now();
      const firstClientProcessingTime = Math.round(
        firstEndTime - firstStartTime
      );

      if (!firstResponse.success) {
        this.state.error =
          firstResponse.error_message || "Failed to lookup location";
        this.state.isLoading = false;
        this.render();
        return;
      }

      // Add client-side processing time for comparison
      if (firstResponse.data) {
        firstResponse.data.client_processing_time_ms =
          firstClientProcessingTime;
        firstResponse.data.request_number = 1;
        firstResponse.data.cached = false;
      }

      this.state.result = firstResponse;
      this.state.isLoading = false;
      this.render();

      // After a short delay, make a second request to demonstrate Redis caching
      setTimeout(async () => {
        this.state.isLoading = true;
        this.render();

        try {
          const secondStartTime = performance.now();

          const secondResponse = await this.api.post(this.url, {
            content: "json",
            headers: {
              Authorization: "Bearer 7%FRtf@34hi",
            },
            body: {
              delivery_location: this.state.selectedLocation,
            },
          });

          const secondEndTime = performance.now();
          const secondClientProcessingTime = Math.round(
            secondEndTime - secondStartTime
          );

          if (secondResponse.data) {
            secondResponse.data.client_processing_time_ms =
              secondClientProcessingTime;
            secondResponse.data.request_number = 2;
            secondResponse.data.cached = true;
          }

          this.state.secondResult = secondResponse;
          this.state.showComparison = true;
          this.state.isLoading = false;
          this.render();

          // Animate the comparison metrics to highlight the difference
          setTimeout(() => {
            const comparisonElements = this.shadowObj.querySelectorAll(
              ".comparison-highlight"
            );
            comparisonElements.forEach((el) => {
              el.classList.add("highlight-animation");
            });
          }, 500);
        } catch (error) {
          console.error("Error on second location lookup:", error);
          this.state.isLoading = false;
          this.render();
        }
      }, 1500); // Wait 1.5 seconds before making second request
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
      secondResult: null,
      selectedLocation: "",
      showComparison: false,
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

  _calculatePerformanceScore(processingTime) {
    // Calculate score based on relation to 950ms benchmark
    const benchmark = 950;
    const percentage = Math.min(
      100,
      Math.max(0, 100 - (processingTime / benchmark) * 100)
    );

    if (percentage >= 80)
      return { score: "Excellent", color: "var(--success-color)" };
    if (percentage >= 60)
      return { score: "Good", color: "var(--accent-color)" };
    if (percentage >= 40)
      return { score: "Average", color: "var(--alt-color)" };
    return { score: "Slow", color: "var(--error-color)" };
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
            ${
              this.state.error
                ? `<div class="error-alert">${this.state.error}</div>`
                : ""
            }
            
            <div class="info-alert">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>Requests are sent with secure authorization. Two requests will be made to demonstrate Redis caching.</span>
            </div>
            
            <form class="location-form">
              <div class="input-group">
                <label for="location-input">Delivery Location</label>
                <div class="input-wrapper">
                  <input 
                    type="text" 
                    id="location-input" 
                    class="location-input ${
                      this.state.selectedLocation ? "with-value" : ""
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
                <button type="submit" class="lookup-btn" ${
                  this.state.isLoading ? "disabled" : ""
                }>
                  ${
                    this.state.isLoading
                      ? this._getLoadingSpinner() +
                        (this.state.result
                          ? "Processing Second Request..."
                          : "Looking up...")
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
    const performance = this._calculatePerformanceScore(processingTime);

    // Calculate hours and minutes from seconds
    const durationHours = Math.floor(distanceResult.duration_seconds / 3600);
    const durationMinutes = Math.floor(
      (distanceResult.duration_seconds % 3600) / 60
    );

    const secondResult = this.state.secondResult;
    const showComparison =
      this.state.showComparison && secondResult && secondResult.data;

    let performanceComparisonHtml = "";

    if (showComparison) {
      const firstTime = processingTime;
      const secondTime = secondResult.data.processing_time_ms;
      const timeDifference = firstTime - secondTime;
      const percentImprovement = Math.round((timeDifference / firstTime) * 100);

      performanceComparisonHtml = /* html */ `
        <div class="performance-comparison">
          <h3 class="comparison-title">Redis Cache Comparison</h3>
          <div class="comparison-metrics">
            <div class="comparison-metric">
              <div class="metric-icon request-first-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <div class="metric-content">
                <span class="comparison-label">First Request</span>
                <span class="comparison-value">${firstTime}ms</span>
                <span class="request-badge">Uncached</span>
              </div>
            </div>
            <div class="comparison-metric">
              <div class="metric-icon request-second-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
                  <line x1="7" y1="2" x2="7" y2="22"></line>
                  <line x1="17" y1="2" x2="17" y2="22"></line>
                  <line x1="2" y1="12" x2="22" y2="12"></line>
                  <line x1="2" y1="7" x2="7" y2="7"></line>
                  <line x1="2" y1="17" x2="7" y2="17"></line>
                  <line x1="17" y1="17" x2="22" y2="17"></line>
                  <line x1="17" y1="7" x2="22" y2="7"></line>
                </svg>
              </div>
              <div class="metric-content">
                <span class="comparison-label">Second Request</span>
                <span class="comparison-value comparison-highlight">${secondTime}ms</span>
                <span class="request-badge cached">Cached</span>
              </div>
            </div>
            <div class="comparison-metric improvement">
              <div class="metric-icon improvement-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                  <polyline points="17 6 23 6 23 12"></polyline>
                </svg>
              </div>
              <div class="metric-content">
                <span class="comparison-label">Improvement</span>
                <span class="comparison-value comparison-highlight">
                  ${timeDifference}ms (${percentImprovement}%)
                </span>
              </div>
            </div>
          </div>
          <div class="comparison-visual">
            <h4 class="visual-title">Response Time Comparison</h4>
            <div class="comparison-bar-container">
              <div class="bar-label-container">
                <div class="metric-icon request-first-icon mini-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <polyline points="12 6 12 12 16 14"></polyline>
                  </svg>
                </div>
                <div class="comparison-label">First Request</div>
              </div>
              <div class="comparison-bar first" style="width: 100%;">
                <span class="bar-value">${firstTime}ms</span>
              </div>
            </div>
            <div class="comparison-bar-container">
              <div class="bar-label-container">
                <div class="metric-icon request-second-icon mini-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
                    <line x1="7" y1="2" x2="7" y2="22"></line>
                    <line x1="17" y1="2" x2="17" y2="22"></line>
                    <line x1="2" y1="12" x2="22" y2="12"></line>
                  </svg>
                </div>
                <div class="comparison-label">Second Request</div>
              </div>
              <div class="comparison-bar second" style="width: ${Math.max(
                5,
                (secondTime / firstTime) * 100
              )}%;">
                <span class="bar-value">${secondTime}ms</span>
              </div>
            </div>
          </div>
          <div class="comparison-explanation">
            <div class="explanation-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M8 14s1.5 2 4 2 4-2 4-2"></path>
                <line x1="9" y1="9" x2="9.01" y2="9"></line>
                <line x1="15" y1="9" x2="15.01" y2="9"></line>
              </svg>
            </div>
            <div class="explanation-content">
              <h4>Redis Caching Performance</h4>
              <p>The second request is faster because the result is cached in Redis, demonstrating the performance benefits of caching in our application. Redis provides in-memory data storage with high-speed access.</p>
            </div>
          </div>
        </div>
      `;
    }

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
        
        <div class="result-tabs">
          <div class="tab active" data-tab="details">Details</div>
          <div class="tab ${
            showComparison ? "" : "disabled"
          }" data-tab="comparison">${
      showComparison ? "Performance Comparison" : "Awaiting Second Request..."
    }</div>
        </div>
        
        <div class="tab-content details-tab active">
          <div class="performance-dashboard">
            <div class="dashboard-header">
              <h3>Processing Performance</h3>
              <div class="performance-pill" style="background-color: ${
                performance.color
              }">
                <span>${performance.score}</span>
              </div>
            </div>
            
            <div class="dashboard-content">
              <div class="stats-column">
                <div class="stat-tiles">
                  <div class="stat-tile">
                    <div class="stat-icon benchmark-icon">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"></path>
                      </svg>
                    </div>
                    <div class="stat-content">
                      <div class="stat-value">950ms</div>
                      <div class="stat-label">Benchmark Target</div>
                    </div>
                  </div>
                  
                  <div class="stat-tile">
                    <div class="stat-icon client-icon">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                        <line x1="8" y1="21" x2="16" y2="21"></line>
                        <line x1="12" y1="17" x2="12" y2="21"></line>
                      </svg>
                    </div>
                    <div class="stat-content">
                      <div class="stat-value">${
                        result.data.client_processing_time_ms
                      }ms</div>
                      <div class="stat-label">Client Processing</div>
                    </div>
                  </div>
                  
                  <div class="stat-tile">
                    <div class="stat-icon request-icon">
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline>
                        <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
                      </svg>
                    </div>
                    <div class="stat-content">
                      <div class="stat-value">#${
                        result.data.request_number || 1
                      }</div>
                      <div class="stat-label">Request</div>
                    </div>
                  </div>
                </div>
                
                <div class="performance-scale">
                  <div class="scale-marker" style="background-color: var(--error-color)"></div>
                  <div class="scale-marker" style="background-color: var(--warning-color)"></div>
                  <div class="scale-marker" style="background-color: var(--accent-color)"></div>
                  <div class="scale-marker" style="background-color: var(--success-color)"></div>
                  <div class="scale-labels">
                    <span>Slow</span>
                    <span>Average</span>
                    <span>Good</span>
                    <span>Excellent</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

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
              <p class="delivery-address">${
                distanceResult.delivery_location
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
              <p class="branch-address">${
                distanceResult.nearest_branch.address
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
                <div class="metric-value">${durationHours} hours ${durationMinutes} minutes</div>
                <div class="metric-secondary">${distanceResult.duration_seconds.toLocaleString()} seconds total</div>
              </div>
            </div>
          </div>
          
          <div class="message-container">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <p class="message">${result.data.message}</p>
          </div>
          
          ${
            showComparison
              ? ""
              : `
            <div class="awaiting-second-request">
              <div class="loading-indicator">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
              </div>
              <p>Performing second request to demonstrate Redis caching...</p>
            </div>
          `
          }
        </div>
        
        <div class="tab-content comparison-tab ${
          showComparison ? "" : "hidden"
        }">
          ${performanceComparisonHtml}
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
        }
        
        .copy-result svg {
          width: 0.875rem;
          height: 0.875rem;
        }
        
        /* Tab Navigation */
        .result-tabs {
          display: flex;
          border-bottom: 1px solid var(--border-color);
          margin-bottom: 1.5rem;
          overflow-x: auto;
          scrollbar-width: none;
        }
        
        .result-tabs::-webkit-scrollbar {
          display: none;
        }
        
        .tab {
          padding: 0.875rem 1.25rem;
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--gray-color);
          border-bottom: 2px solid transparent;
          cursor: pointer;
          transition: all 0.2s ease;
          white-space: nowrap;
        }
        
        .tab:hover:not(.disabled) {
          color: var(--primary-color);
        }
        
        .tab.active {
          color: var(--primary-color);
          border-bottom-color: var(--primary-color);
        }
        
        .tab.disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .tab-content {
          display: none;
        }
        
        .tab-content.active {
          display: block;
        }
        
        .tab-content.hidden {
          display: none;
        }
        
        /* Performance Dashboard */
        .performance-dashboard {
          background: var(--background-color);
          padding: 0 0 20px 0;
          margin-bottom: 1.5rem;
          border-bottom: var(--border);
        }
        
        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }
        
        .dashboard-header h3 {
          font-size: 1.125rem;
          font-weight: 600;
          margin: 0;
          color: var(--title-color);
        }
        
        .performance-pill {
          padding: 0.375rem 1rem;
          font-size: 0.875rem;
          font-weight: 600;
          color: white;
          border-radius: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 100px;
          background: var(--primary-linear);
        }
        
        .dashboard-content {
          display: grid;
          grid-template-columns: 1fr 2fr;
          gap: 2rem;
          align-items: center;
        }
        
        .gauge-column {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
        }
        
        .gauge-label {
          margin-top: 0.5rem;
          font-size: 0.875rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .stats-column {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }
        
        .stat-tiles {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
          width: 100%;
        }
        
        .stat-tile {
          background-color: var(--background-color);
          border-radius: 0.75rem;
          padding: 1rem;
          display: flex;
          width: max-content;
          align-items: center;
          gap: 0.75rem;
          border: var(--border);
          transition: transform 0.2s ease, border-bottom 0.2s ease;
        }
        
        .stat-tile:hover {
          transform: translateY(-3px);
        }
        
        .stat-icon {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 0.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          flex-shrink: 0;
        }
        
        .benchmark-icon {
          background: linear-gradient(145deg, #3c82f6 0%, #1e40af 100%);
        }
        
        .client-icon {
          background: linear-gradient(145deg, #8b5cf6 0%, #6d28d9 100%);
        }
        
        .request-icon {
          background: linear-gradient(145deg, #ec4899 0%, #be185d 100%);
        }
        
        .stat-content {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }
        
        .stat-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--title-color);
        }
        
        .stat-label {
          font-size: 0.75rem;
          font-weight: 500;
          color: var(--gray-color);
        }
        
        .performance-scale {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          margin-top: 0.5rem;
        }
        
        .scale-marker {
          display: flex;
          gap: 0.25rem;
          height: 0.375rem;
          border-radius: 1rem;
        }
        
        .scale-marker:nth-child(1) {
          width: 25%;
        }
        
        .scale-marker:nth-child(2) {
          width: 50%;
        }
        
        .scale-marker:nth-child(3) {
          width: 75%;
        }
        
        .scale-marker:nth-child(4) {
          width: 100%;
        }
        
        .scale-labels {
          display: flex;
          justify-content: space-between;
          font-size: 0.75rem;
          color: var(--gray-color);
          margin-top: 0.25rem;
        }
        
        .performance-gauge {
          width: 160px;
          height: 160px;
          position: relative;
        }
        
        .gauge {
          transform: rotate(-90deg);
        }
        
        .gauge-background {
          fill: none;
          stroke: var(--border-color);
          stroke-width: 10;
        }
        
        .gauge-value {
          fill: none;
          stroke-width: 10;
          stroke-linecap: round;
          transform-origin: center;
          transform: rotate(0deg);
          transition: stroke-dasharray 1s ease;
        }
        
        .gauge-text {
          font-size: 1.5rem;
          font-weight: 700;
          transform: rotate(90deg);
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
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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
        
        /* Icons for performance comparison */
        .request-first-icon {
          background: linear-gradient(145deg, #3b82f6 0%, #1e40af 100%);
          color: white;
        }
        
        .request-second-icon {
          background: linear-gradient(145deg, #10b981 0%, #047857 100%);
          color: white;
        }
        
        .improvement-icon {
          background: linear-gradient(145deg, #f59e0b 0%, #b45309 100%);
          color: white;
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
        
        /* Comparison Tab */
        .performance-comparison {
          padding: 0;
        }
        
        .comparison-title {
          display: none;
          font-size: 1.125rem;
          font-weight: 600;
          margin: 0 0 1.25rem 0;
          color: var(--title-color);
          text-align: center;
        }
        
        .comparison-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .comparison-metric {
          padding: 1rem;
          border-radius: 0.5rem;
          border: var(--border);
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        
        .comparison-metric.improvement {
          border: 1px solid var(--success-color);
          background-color: var(--card-bg);
          border-bottom: 2px solid var(--success-color);
        }
        
        .comparison-metric .metric-content {
          display: grid;
          flex-direction: column;
          align-items: flex-start;
          gap: 0.25rem;
        }
        
        .comparison-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--gray-color);
        }
        
        .comparison-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-color);
        }
        
        .comparison-highlight {
          transition: color 0.3s ease;
        }
        
        .highlight-animation {
          animation: highlight-pulse 2s ease;
        }
        
        .request-badge {
          font-size: 0.75rem;
          font-weight: 600;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
          background-color: var(--tab-background);
          color: var(--gray-color);
          align-self: center;
        }
        
        .request-badge.cached {
          background-color: rgba(16, 185, 129, 0.1);
          color: var(--success-color);
        }
        
        .comparison-visual {
          background-color: var(--background-color);
          padding: 1.25rem 0 0;
        }
        
        .visual-title {
          font-size: 1rem;
          font-weight: 600;
          margin: 0 0 1rem 0;
          color: var(--title-color);
        }
        
        .comparison-bar-container {
          display: flex;
          align-items: center;
          margin-bottom: 1rem;
          gap: 1rem;
        }
        
        .bar-label-container {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          width: 150px;
          flex-shrink: 0;
        }
        
        .mini-icon {
          width: 1.75rem;
          height: 1.75rem;
        }
        
        .comparison-bar {
          height: 2rem;
          border-radius: 0.25rem;
          display: flex;
          align-items: center;
          padding: 0 0.75rem;
          position: relative;
          min-width: 4rem;
          transition: width 1s ease-out;
          flex-grow: 1;
        }
        
        .comparison-bar.first {
          background-color: var(--tab-background);
          color: var(--primary-color);
        }
        
        .comparison-bar.second {
          background-color: rgba(16, 185, 129, 0.2);
          color: var(--success-color);
        }
        
        .bar-value {
          font-weight: 600;
          font-size: 0.875rem;
          white-space: nowrap;
        }
        
        .comparison-explanation {
          border-radius: 0.5rem;
          padding: 1.25rem 0;
          display: flex;
          align-items: flex-start;
          gap: 1rem;
        }
        
        .explanation-icon {
          background: var(--accent-linear);
          color: white;
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 50%;
          display: none;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        
        .explanation-content {
          flex: 1;
        }
        
        .explanation-content h4 {
          font-size: 1rem;
          font-weight: 600;
          margin: 0 0 0.5rem 0;
          color: var(--title-color);
        }
        
        .explanation-content p {
          margin: 0;
          font-size: 0.875rem;
          line-height: 1.5;
          color: var(--text-color);
        }
        
        /* Awaiting second request */
        .awaiting-second-request {
          background-color: var(--tab-background);
          padding: 1.25rem;
          border-radius: 0.5rem;
          text-align: center;
          margin-top: 1.5rem;
        }
        
        .awaiting-second-request p {
          color: var(--primary-color);
          font-size: 0.875rem;
          font-weight: 500;
          margin: 0.75rem 0 0 0;
        }
        
        .loading-indicator {
          display: flex;
          gap: 0.5rem;
          justify-content: center;
        }
        
        .dot {
          width: 0.75rem;
          height: 0.75rem;
          background-color: var(--primary-color);
          border-radius: 50%;
          animation: pulse 1.5s infinite ease-in-out;
        }
        
        .dot:nth-child(2) {
          animation-delay: 0.2s;
        }
        
        .dot:nth-child(3) {
          animation-delay: 0.4s;
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
        
        @keyframes highlight-pulse {
          0% {
            color: var(--text-color);
          }
          30% {
            color: var(--success-color);
          }
          100% {
            color: var(--text-color);
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
          
          .gauge-column {
            margin-bottom: 1rem;
          }
          
          .stat-tiles {
            grid-template-columns: 1fr;
          }
          
          .comparison-metrics {
            grid-template-columns: 1fr;
          }
          
          .comparison-bar-container {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }
          
          .comparison-bar-container .comparison-label {
            width: auto;
            text-align: left;
            padding-right: 0;
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
