export default class Quote extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/webhook/quote";

    // Component state
    this.state = {
      isLoading: false,
      error: null,
      result: null,
      secondResult: null,
      showComparison: false,
      selectedQuote: null,

      // Sample quotes for demonstration
      sampleQuotes: [
        {
          id: "event-2-stall",
          label: "Event, 2 Stall Trailer",
          description: "Perfect for small events with limited attendance",
          location: "Mountain View, CA",
          body: {
            delivery_location:
              "1600 Amphitheatre Parkway, Mountain View, CA 94043",
            trailer_type: "2 Stall Restroom Trailer",
            rental_start_date: "2025-07-15",
            rental_days: 3,
            usage_type: "event",
            extras: [{ extra_id: "3kW Generator", qty: 1 }],
          },
        },
        {
          id: "commercial-4-stall",
          label: "Commercial, 4 Stall Trailer",
          description:
            "Ideal for medium-sized construction sites or commercial use",
          location: "Cupertino, CA",
          body: {
            delivery_location: "1 Infinite Loop, Cupertino, CA 95014",
            trailer_type: "4 Stall Restroom Trailer",
            rental_start_date: "2025-08-01",
            rental_days: 30,
            usage_type: "commercial",
            extras: [
              { extra_id: "pump_out", qty: 2 },
              { extra_id: "cleaning", qty: 1 },
            ],
          },
        },
        {
          id: "event-8-stall",
          label: "Event, 8 Stall Trailer",
          description: "Premium solution for large events with high traffic",
          location: "Omaha, NE",
          body: {
            delivery_location: "123 Main St, Omaha, NE 68102",
            trailer_type: "8 Stall Restroom Trailer",
            rental_start_date: "2025-09-05",
            rental_days: 4,
            usage_type: "event",
            extras: [{ extra_id: "3kW Generator", qty: 1 }],
          },
        },
      ],
    };

    this.render();
    this._setupEventListeners();
  }

  connectedCallback() {
    // Do any setup when element is added to the DOM
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();

    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  _setupEventListeners() {
    // Select a sample quote card
    const sampleCards = this.shadowObj.querySelectorAll(".sample-card");
    if (sampleCards) {
      sampleCards.forEach((card) => {
        card.addEventListener("click", () => {
          const quoteId = card.dataset.id;
          this.state.selectedQuote = quoteId;

          // Update UI to show selected card
          sampleCards.forEach((c) => c.classList.remove("active"));
          card.classList.add("active");
        });
      });
    }

    // Generate quote button
    const generateButtons = this.shadowObj.querySelectorAll(
      ".generate-quote-btn"
    );
    if (generateButtons) {
      generateButtons.forEach((button) => {
        button.addEventListener("click", (e) => {
          e.stopPropagation(); // Prevent card click event
          const quoteId = button.dataset.id;
          this.state.selectedQuote = quoteId;

          // Update UI to show selected card
          sampleCards.forEach((c) => c.classList.remove("active"));
          button.closest(".sample-card").classList.add("active");

          // Generate the quote
          this._getQuote(quoteId);
        });
      });
    }

    // Copy results button
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

    // Reset form button
    const resetButton = this.shadowObj.querySelector("#reset-form-btn");
    if (resetButton) {
      resetButton.addEventListener("click", () => {
        this._resetForm();
      });
    }

    // Custom form event listeners
    const customForm = this.shadowObj.querySelector("#customQuoteForm");
    if (customForm) {
      const trailerTypeSelect = customForm.querySelector("#trailerType");
      const usageTypeSelect = customForm.querySelector("#usageType");
      const startDateInput = customForm.querySelector("#startDate");
      const endDateInput = customForm.querySelector("#endDate");
      const rentalDaysInput = customForm.querySelector("#rentalDays");
      const deliveryAddressInput = customForm.querySelector("#deliveryAddress");
      const generateCustomBtn = this.shadowObj.querySelector(
        ".generate-custom-quote-btn"
      );

      // Set minimum date to today
      const today = new Date().toISOString().split("T")[0];
      if (startDateInput) {
        startDateInput.min = today;
        startDateInput.value = today; // Default to today
      }
      if (endDateInput) {
        endDateInput.min = today;
        endDateInput.value = today; // Default to today
      }

      // Set default rental days
      if (rentalDaysInput) {
        rentalDaysInput.value = 1;
      }

      // Calculate rental days
      const calculateRentalDays = () => {
        const startDate = startDateInput?.value;
        const endDate = endDateInput?.value;

        if (!startDate) {
          console.error("Start date is required for rental calculation");
          if (rentalDaysInput) rentalDaysInput.value = 1;
          return 1;
        }

        if (!endDate) {
          if (rentalDaysInput) rentalDaysInput.value = 1;
          return 1;
        }

        const start = new Date(startDate);
        const end = new Date(endDate);

        if (isNaN(start.getTime()) || isNaN(end.getTime())) {
          console.error("Invalid date format");
          if (rentalDaysInput) rentalDaysInput.value = 1;
          return 1;
        }

        const timeDiff = end.getTime() - start.getTime();
        const dayDiff = Math.ceil(timeDiff / (1000 * 3600 * 24));
        const rentalDays = Math.max(1, dayDiff); // Minimum 1 day

        if (rentalDaysInput) {
          rentalDaysInput.value = rentalDays;
        }

        return rentalDays;
      };

      // Enable/disable generate button based on form validation
      const validateForm = () => {
        try {
          const isValid =
            trailerTypeSelect?.value?.trim() !== "" &&
            usageTypeSelect?.value?.trim() !== "" &&
            startDateInput?.value?.trim() !== "" &&
            endDateInput?.value?.trim() !== "" &&
            deliveryAddressInput?.value?.trim() !== "";

          if (!isValid) {
            console.log("Form validation failed:", {
              trailerType: trailerTypeSelect?.value,
              usageType: usageTypeSelect?.value,
              startDate: startDateInput?.value,
              endDate: endDateInput?.value,
              deliveryAddress: deliveryAddressInput?.value,
            });
          }

          // activate button
          if (generateCustomBtn) {
            generateCustomBtn.disabled = !isValid;
          }

          return isValid;
        } catch (error) {
          console.error("Validation error:", error);
          return false;
        }
      };

      // Add change listeners to required fields
      if (trailerTypeSelect) {
        trailerTypeSelect.addEventListener("change", validateForm);
      }
      if (usageTypeSelect) {
        usageTypeSelect.addEventListener("change", validateForm);
      }
      if (startDateInput) {
        startDateInput.addEventListener("change", () => {
          // Update end date minimum
          if (endDateInput) {
            endDateInput.min = startDateInput.value;
            if (endDateInput.value < startDateInput.value) {
              endDateInput.value = startDateInput.value;
            }
          }
          calculateRentalDays();
          validateForm();
        });
      }
      if (endDateInput) {
        endDateInput.addEventListener("change", () => {
          calculateRentalDays();
          validateForm();
        });
      }
      if (deliveryAddressInput) {
        deliveryAddressInput.addEventListener("input", validateForm);
      }

      // Initial calculations
      calculateRentalDays();
      validateForm();

      // Add click listener to generate button
      if (generateCustomBtn) {
        generateCustomBtn.addEventListener("click", () => {
          this._generateCustomQuote();
        });
      }
    }
  }

  async _getQuote(quoteId) {
    if (!quoteId) {
      this.state.error = "Please select a sample quote first.";
      console.error("Quote generation failed: No quote ID provided");
      this.render();
      return;
    }

    // Find the selected quote data
    const selectedQuote = this.state.sampleQuotes.find((q) => q.id === quoteId);
    if (!selectedQuote) {
      this.state.error = "Selected quote not found.";
      console.error(
        "Quote generation failed: Quote not found for ID:",
        quoteId
      );
      console.log(
        "Available quotes:",
        this.state.sampleQuotes.map((q) => q.id)
      );
      this.render();
      return;
    }

    console.log("Generating quote for:", quoteId, selectedQuote);

    this.state.isLoading = true;
    this.state.error = null;
    this.state.showComparison = false;
    this.render();

    try {
      // First API request
      const firstStartTime = performance.now();

      console.log("Sending quote request with body:", selectedQuote.body);

      const firstResponse = await this.api.post(this.url, {
        content: "json",
        headers: {
          Authorization: "Bearer 7%FRtf@34hi",
        },
        body: selectedQuote.body,
      });

      const firstEndTime = performance.now();
      const firstClientProcessingTime = Math.round(
        firstEndTime - firstStartTime
      );

      console.log("Quote response received:", firstResponse);

      if (!firstResponse.success) {
        const errorMsg =
          firstResponse.error_message || "Failed to generate quote";
        this.state.error = errorMsg;
        this.state.isLoading = false;
        console.error("Quote generation failed:", errorMsg, firstResponse);
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
      this._scrollToResults();

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
            body: selectedQuote.body,
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
          this._scrollToResults();

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
          console.error("Error on second quote request:", error);
          this.state.isLoading = false;
          this.render();
        }
      }, 1500); // Wait 1.5 seconds before making second request
    } catch (error) {
      console.error("Error generating quote:", error);
      this.state.isLoading = false;
      this.state.error = "An unexpected error occurred";
      this.render();
    }
  }

  _copyResultToClipboard() {
    if (!this.state.result) return;

    const resultText = JSON.stringify(this.state.result, null, 2);
    navigator.clipboard
      .writeText(resultText)
      .then(() => {
        const copyButton = this.shadowObj.querySelector(".copy-result");
        if (copyButton) {
          const originalText = copyButton.innerHTML;

          copyButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            Copied!
          `;

          setTimeout(() => {
            copyButton.innerHTML = originalText;
          }, 2000);
        }
      })
      .catch((err) => {
        console.error("Failed to copy result: ", err);
      });
  }

  _calculatePerformanceScore(processingTime) {
    // Calculate score based on response time
    let color, score;

    if (processingTime < 600) {
      color = "var(--success-color)";
      score = "Excellent";
    } else if (processingTime < 850) {
      color = "var(--accent-color)";
      score = "Good";
    } else if (processingTime < 1100) {
      color = "var(--alt-color)";
      score = "Average";
    } else {
      color = "var(--error-color)";
      score = "Slow";
    }

    return { color, score };
  }

  _getLoadingSpinner() {
    return /* html */ `
      <svg class="spinner" viewBox="0 0 50 50">
        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
      </svg>
    `;
  }

  _formatCurrency(amount) {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  }

  _resetForm() {
    this.state = {
      isLoading: false,
      error: null,
      result: null,
      secondResult: null,
      showComparison: false,
      selectedQuote: null,
      sampleQuotes: [...this.state.sampleQuotes],
    };

    this.render();
  }

  _calculateAverageProcessingTime(firstTime, secondTime) {
    return Math.round((firstTime + secondTime) / 2);
  }

  _calculatePercentageImprovement(firstTime, secondTime) {
    if (!firstTime || !secondTime) return 0;
    const improvement = ((firstTime - secondTime) / firstTime) * 100;
    return Math.round(improvement);
  }

  _createAnimatedBarChart(firstTime, secondTime) {
    const maxTime = Math.max(firstTime, secondTime);
    const firstWidth = (firstTime / maxTime) * 100;
    const secondWidth = (secondTime / maxTime) * 100;

    return /* html */ `
      <div class="comparison-bars">
        <div class="comparison-bar-container">
          <div class="comparison-label">First Request</div>
          <div class="comparison-bar-wrapper">
            <div class="comparison-bar" style="width: ${firstWidth}%; background: var(--accent-color);">
              <span>${firstTime}ms</span>
            </div>
          </div>
        </div>
        
        <div class="comparison-bar-container">
          <div class="comparison-label">Redis Cached</div>
          <div class="comparison-bar-wrapper">
            <div class="comparison-bar comparison-highlight" style="width: ${secondWidth}%; background: var(--success-color);">
              <span>${secondTime}ms</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderCustomForm() {
    return /* html */ `
      <div class="custom-form-container">
        <form class="quote-form" id="customQuoteForm">
          <div class="form-section">
            <h4 class="form-section-title">Product Selection</h4>
            
            <div class="form-group">
              <label for="trailerType">Restroom Trailer Type *</label>
              <select id="trailerType" name="trailerType" required>
                <option value="">Select a trailer type</option>
                <option value="1 Stall ADA Combo Trailer">1 Stall ADA Combo Trailer</option>
                <option value="2 Stall Restroom Trailer">2 Stall Restroom Trailer</option>
                <option value="3 Stall ADA Restroom Trailer">3 Stall ADA Restroom Trailer</option>
                <option value="4 Stall Restroom Trailer">4 Stall Restroom Trailer</option>
                <option value="8 Stall Restroom Trailer">8 Stall Restroom Trailer</option>
                <option value="10 Stall Restroom Trailer">10 Stall Restroom Trailer</option>
                <option value="3 Stall Combo Trailer">3 Stall Combo Trailer</option>
                <option value="8 Stall Shower Trailer">8 Stall Shower Trailer</option>
              </select>
            </div>

            <div class="form-group">
              <label for="usageType">Usage Type *</label>
              <select id="usageType" name="usageType" required>
                <option value="">Select usage type</option>
                <option value="event">Event</option>
                <option value="commercial">Commercial</option>
              </select>
            </div>

            <div class="form-group">
              <label>Extras (Optional)</label>
              <div class="extras-container">
                <div class="extra-item">
                  <input type="checkbox" id="pumpOut" name="extras" value="pump_out">
                  <label for="pumpOut">Pump Out</label>
                </div>
                <div class="extra-item">
                  <input type="checkbox" id="waterFill" name="extras" value="Fresh Water Tank Fill">
                  <label for="waterFill">Fresh Water</label>
                </div>
                <div class="extra-item">
                  <input type="checkbox" id="cleaning" name="extras" value="cleaning">
                  <label for="cleaning">Cleaning</label>
                </div>
                <div class="extra-item">
                  <input type="checkbox" id="restocking" name="extras" value="Restocking">
                  <label for="restocking">Restocking</label>
                </div>
              </div>
              <small style="color: var(--gray-color); font-size: 0.8rem;">Select multiple services as needed</small>
            </div>

            <div class="form-group">
              <label for="generator">Generator (Optional)</label>
              <select id="generator" name="generator">
                <option value="">No generator needed</option>
                <option value="3kW Generator">3kW Generator</option>
                <option value="7kW Generator">7kW Generator</option>
                <option value="20kW Generator">20kW Generator</option>
                <option value="30kW Generator">30kW Generator</option>
              </select>
            </div>
          </div>

          <div class="form-section dates">
            <h4 class="form-section-title">Rental Period</h4>
            <div class="dates">
              <div class="form-group date">
                <label for="startDate">Rental Start Date *</label>
                <input type="date" id="startDate" name="startDate" required>
              </div>

              <div class="form-group date">
                <label for="endDate">Rental End Date *</label>
                <input type="date" id="endDate" name="endDate" required>
              </div>
            </div>

            <div class="form-group">
              <label for="rentalDays">Rental Days</label>
              <input type="number" id="rentalDays" name="rentalDays" min="1" readonly>
              <small style="color: var(--gray-color); font-size: 0.8rem;">Calculated automatically (minimum 1 day)</small>
            </div>
          </div>

          <div class="form-section">
            <h4 class="form-section-title">Delivery Information</h4>
            
            <div class="form-group">
              <label for="deliveryAddress">Delivery Address *</label>
              <input type="text" id="deliveryAddress" name="deliveryAddress" 
                     placeholder="e.g., 1600 Amphitheatre Parkway, Mountain View, CA 94043" required>
              <small style="color: var(--gray-color); font-size: 0.8rem;">Enter the complete delivery address</small>
            </div>
          </div>
          
          <div class="form-actions">
            <button type="button" class="generate-custom-quote-btn" disabled>
              Generate Custom Quote
            </button>
          </div>
        </form>
      </div>
    `;
  }

  getBody() {
    return /* html */ `
      <div class="container">
        <div class="quote-builder-container">
          <div class="header">
            <h1>Quote Builder</h1>
            <p class="subtitle">Generate pricing for trailer rentals with Redis caching performance</p>
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
            
            <div class="two-column-layout">
              <div class="sample-quotes-column">
                <div class="sample-quotes-container">
                  <div class="header">
                    <h3>Select Sample Quote</h3>
                    <p class="subtitle">Choose a sample quote to generate pricing</p>
                  </div>
                  ${this._renderSampleQuotes()}
                </div>
              </div>
              
              <div class="custom-form-column">
                <div class="custom-quote-container">
                  <div class="header">
                    <h3>Custom Quote Builder</h3>
                    <p class="subtitle">Create your own quote with specific requirements</p>
                  </div>
                  ${this._renderCustomForm()}
                </div>
              </div>
            </div>
          </div>
          
          <div class="results-section">
            ${this._renderResultsSection()}
          </div>
        </div>
      </div>
    `;
  }

  _renderSampleQuotes() {
    return /* html */ `
      <div class="quick-options">
        <div class="sample-quotes-grid">
          ${this.state.sampleQuotes
            .map(
              (quote) => `
            <div class="sample-card ${
              this.state.selectedQuote === quote.id ? "active" : ""
            }" data-id="${quote.id}">
              <div class="card-header">
                <div>
                  <h3 class="card-title">${quote.label}</h3>
                  <p class="card-subtitle">${quote.description}</p>
                </div>
              </div>
              
              <div class="card-location">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
                ${quote.location}
              </div>
              
              <div class="card-details">
                <div class="detail-item">
                  <span class="detail-label">Trailer Type</span>
                  <span class="detail-value">${quote.body.trailer_type}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Rental Days</span>
                  <span class="detail-value">${quote.body.rental_days}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Usage</span>
                  <span class="detail-value">${
                    quote.body.usage_type.charAt(0).toUpperCase() +
                    quote.body.usage_type.slice(1)
                  }</span>
                </div>
              </div>
              
              <button class="generate-quote-btn" data-id="${quote.id}">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12h14"></path>
                  <path d="m12 5 7 7-7 7"></path>
                </svg>
                Generate Quote
              </button>
            </div>
          `
            )
            .join("")}
        </div>
      </div>
    `;
  }

  _renderResultsSection() {
    if (this.state.isLoading) {
      return /* html */ `
        <div class="loading-container">
          ${this._getLoadingSpinner()}
          <p class="loading-text">Generating quote...</p>
        </div>
      `;
    }

    if (this.state.error) {
      return /* html */ `
        <div class="error-container">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          ${this.state.error}
        </div>
      `;
    }

    if (!this.state.result) {
      return /* html */ `
        <div class="no-results">
          <p>Select a sample quote and click "Generate Quote" to see the results.</p>
        </div>
      `;
    }

    // If we have results, show the tabs
    return /* html */ `
      <div class="tabs-container">
        <div class="tab active" data-tab="quote">Quote Details</div>
        <div class="tab ${
          !this.state.showComparison ? "disabled" : ""
        }" data-tab="performance">
          Performance Comparison
          ${
            !this.state.showComparison
              ? ""
              : `<span style="display: inline-block; width: 0.5rem; height: 0.5rem; background: var(--accent-color); border-radius: 50%; margin-left: 0.25rem;"></span>`
          }
        </div>
      </div>
      
      <div class="tab-content quote-tab active">
        ${this._renderQuoteResult()}
      </div>
      
      <div class="tab-content performance-tab">
        ${this._renderPerformanceComparison()}
      </div>
    `;
  }

  _renderQuoteResult() {
    if (!this.state.result || !this.state.result.data) {
      return /* html */ `
        <div class="no-results">
          <p>No quote data available. Please try again.</p>
        </div>
      `;
    }

    const responseData = this.state.result.data;
    const quote = responseData.quote;
    const locationDetails = responseData.location_details;
    const metadata = responseData.metadata;

    const selectedQuoteInfo = this.state.sampleQuotes.find(
      (q) => q.id === this.state.selectedQuote
    );

    return /* html */ `
      <div class="quote-result">
        <div class="result-header">
          <div class="result-title">
            <h3>Quote #${
              responseData.quote_id
                ? responseData.quote_id.split("-").pop()
                : "N/A"
            }</h3>
            <p style="color: var(--gray-color); font-size: 0.875rem; margin-top: 0.25rem;">
              ${
                quote?.product_details?.product_name ||
                selectedQuoteInfo?.body?.trailer_type ||
                "N/A"
              }
            </p>
          </div>
          <div class="result-actions">
            <button class="copy-result">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect>
                <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
              </svg>
              Copy JSON
            </button>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>Quote Overview</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label quote-id">Quote ID</div>
              <div class="detail-card-value quote-id">${
                responseData.quote_id || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Subtotal</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote?.subtotal || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Generated</div>
              <div class="detail-card-value">${
                metadata?.generated_at
                  ? new Date(metadata.generated_at).toLocaleDateString()
                  : "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Valid Until</div>
              <div class="detail-card-value">${
                metadata?.valid_until
                  ? new Date(metadata.valid_until).toLocaleDateString()
                  : "N/A"
              }</div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>Line Items</h4>
          <div class="price-breakdown">
            ${
              quote?.line_items
                ?.map(
                  (item) => `
              <div class="price-item">
                <span>${item.description || "N/A"}</span>
                <span>${this._formatCurrency(item.total || 0)}</span>
              </div>
            `
                )
                .join("") ||
              '<div class="price-item"><span>No line items available</span><span>$0.00</span></div>'
            }
            <div class="price-item total">
              <span>Subtotal</span>
              <span>${this._formatCurrency(quote?.subtotal || 0)}</span>
            </div>
          </div>
        </div>

        ${
          quote?.rental_details
            ? `
        <div class="detail-section">
          <h4>Rental Details</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Start Date</div>
              <div class="detail-card-value">${
                quote.rental_details.rental_start_date || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">End Date</div>
              <div class="detail-card-value">${
                quote.rental_details.rental_end_date || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Duration</div>
              <div class="detail-card-value">${
                quote.rental_details.rental_days || 0
              } days</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Usage Type</div>
              <div class="detail-card-value">${
                quote.rental_details.usage_type || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Pricing Tier</div>
              <div class="detail-card-value">${
                quote.rental_details.pricing_tier_applied || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Season</div>
              <div class="detail-card-value">${
                quote.rental_details.seasonal_rate_name || "N/A"
              }</div>
            </div>
          </div>
        </div>
        `
            : ""
        }

        ${
          quote?.delivery_details
            ? `
        <div class="detail-section">
          <h4>Delivery Details</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Distance</div>
              <div class="detail-card-value">${
                quote.delivery_details.miles?.toFixed(2) || "N/A"
              } miles</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Delivery Cost</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.delivery_details.total_delivery_cost || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Rate Applied</div>
              <div class="detail-card-value">$${
                quote.delivery_details.per_mile_rate_applied?.toFixed(2) ||
                "0.00"
              }/mile</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Base Fee</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.delivery_details.base_fee_applied || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Seasonal Multiplier</div>
              <div class="detail-card-value">${
                quote.delivery_details.seasonal_multiplier_applied || 1.0
              }x</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Estimated Distance</div>
              <div class="detail-card-value">${
                quote.delivery_details.is_distance_estimated ? "Yes" : "No"
              }</div>
            </div>
          </div>
        </div>
        `
            : ""
        }

        ${
          locationDetails
            ? `
        <div class="detail-section">
          <h4>Location Information</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Delivery Address</div>
              <div class="detail-card-value">${
                locationDetails.delivery_address || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Nearest Branch</div>
              <div class="detail-card-value">${
                locationDetails.nearest_branch || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Branch Address</div>
              <div class="detail-card-value">${
                locationDetails.branch_address || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Service Area</div>
              <div class="detail-card-value">${
                locationDetails.service_area_type || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Drive Time</div>
              <div class="detail-card-value">${
                locationDetails.estimated_drive_time_minutes
                  ? `${Math.floor(
                      locationDetails.estimated_drive_time_minutes / 60
                    )}h ${locationDetails.estimated_drive_time_minutes % 60}m`
                  : "N/A"
              }</div>
            </div>
            ${
              locationDetails.geocoded_coordinates
                ? `
            <div class="detail-card">
              <div class="detail-card-label">Coordinates</div>
              <div class="detail-card-value">${
                locationDetails.geocoded_coordinates.latitude?.toFixed(6) ||
                "N/A"
              }, ${
                    locationDetails.geocoded_coordinates.longitude?.toFixed(
                      6
                    ) || "N/A"
                  }</div>
            </div>
            `
                : ""
            }
          </div>
        </div>
        `
            : ""
        }

        ${
          quote?.budget_details
            ? `
        <div class="detail-section">
          <h4>Budget Analysis</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Daily Rate Equivalent</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.budget_details.daily_rate_equivalent || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Weekly Rate Equivalent</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.budget_details.weekly_rate_equivalent || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Monthly Rate Equivalent</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.budget_details.monthly_rate_equivalent || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Free Delivery</div>
              <div class="detail-card-value">${
                quote.budget_details.is_delivery_free ? "Yes" : "No"
              }</div>
            </div>
          </div>
          ${
            quote.budget_details.cost_breakdown
              ? `
            <h5 class="enhanced-section-header">Cost Breakdown</h5>
            <div class="price-breakdown">
              ${Object.entries(quote.budget_details.cost_breakdown)
                .map(
                  ([category, amount]) => `
                <div class="price-item">
                  <span>${
                    category.charAt(0).toUpperCase() + category.slice(1)
                  }</span>
                  <span>${this._formatCurrency(amount || 0)}</span>
                </div>
              `
                )
                .join("")}
            </div>
          `
              : ""
          }
        </div>
        `
            : ""
        }

        ${
          quote?.product_details
            ? `
        <div class="detail-section">
          <h4>Product Information</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Product ID</div>
              <div class="detail-card-value">${
                quote.product_details.product_id || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Product Name</div>
              <div class="detail-card-value">${
                quote.product_details.product_name || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Base Rate</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.product_details.base_rate || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Adjusted Rate</div>
              <div class="detail-card-value">${this._formatCurrency(
                quote.product_details.adjusted_rate || 0
              )}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">ADA Compliant</div>
              <div class="detail-card-value">${
                quote.product_details.is_ada_compliant ? "Yes" : "No"
              }</div>
            </div>
            ${
              quote.product_details.stall_count
                ? `
            <div class="detail-card">
              <div class="detail-card-label">Stall Count</div>
              <div class="detail-card-value">${quote.product_details.stall_count}</div>
            </div>
            `
                : ""
            }
          </div>
        </div>
        `
            : ""
        }

        <div class="detail-section">
          <h4>Performance & Metadata</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Processing Time</div>
              <div class="detail-card-value">${
                metadata?.calculation_time_ms ||
                responseData.client_processing_time_ms ||
                "N/A"
              }${
      metadata?.calculation_time_ms
        ? "ms"
        : responseData.client_processing_time_ms
        ? "ms"
        : ""
    }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">System Version</div>
              <div class="detail-card-value">${metadata?.version || "N/A"}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Source System</div>
              <div class="detail-card-value">${
                metadata?.source_system || "N/A"
              }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Calculation Method</div>
              <div class="detail-card-value">${
                metadata?.calculation_method || "N/A"
              }</div>
            </div>
          </div>
          ${
            metadata?.data_sources
              ? `
            <h5 class="enhanced-section-header">Data Sources</h5>
            <div class="detail-grid">
              ${Object.entries(metadata.data_sources)
                .map(
                  ([source, value]) => `
                <div class="detail-card">
                  <div class="detail-card-label">${
                    source.charAt(0).toUpperCase() + source.slice(1)
                  }</div>
                  <div class="detail-card-value">${value || "N/A"}</div>
                </div>
              `
                )
                .join("")}
            </div>
          `
              : ""
          }
          ${
            metadata?.warnings && metadata.warnings.length > 0
              ? `
            <h5 class="enhanced-section-header warning">Warnings</h5>
            <div class="price-breakdown">
              ${metadata.warnings
                .map(
                  (warning) => `
                <div class="price-item warning-item-container">
                  <span>${warning}</span>
                  <span class="warning-icon">⚠️</span>
                </div>
              `
                )
                .join("")}
            </div>
          `
              : ""
          }
        </div>

        ${
          quote?.notes
            ? `
        <div class="detail-section">
          <h4>Notes</h4>
          <div class="notes-container">
            ${quote.notes}
          </div>
        </div>
        `
            : ""
        }
      </div>
    `;
  }

  _renderPerformanceComparison() {
    if (!this.state.showComparison || !this.state.secondResult) {
      return /* html */ `
        <div class="no-results">
          <p>Performance comparison will be available after a second request is made.</p>
        </div>
      `;
    }

    const firstRequest = this.state.result.data;
    const secondRequest = this.state.secondResult.data;

    const firstTime =
      firstRequest.metadata?.calculation_time_ms ||
      firstRequest.client_processing_time_ms ||
      800;
    const secondTime =
      secondRequest.metadata?.calculation_time_ms ||
      secondRequest.client_processing_time_ms ||
      250;

    const improvement = this._calculatePercentageImprovement(
      firstTime,
      secondTime
    );
    const firstScore = this._calculatePerformanceScore(firstTime);
    const secondScore = this._calculatePerformanceScore(secondTime);

    return /* html */ `
      <div class="comparison-container">
        <div class="comparison-card">
          <h3>First Request</h3>
          <p style="color: var(--gray-color); margin-bottom: 1rem;">Direct API call with full processing</p>
          
          <div class="performance-metrics">
            <div class="metric-card">
              <div class="metric-value" style="color: ${
                firstScore.color
              }">${firstTime}ms</div>
              <div class="metric-label">Processing Time</div>
            </div>
            <div class="metric-card">
              <div class="metric-value" style="color: ${firstScore.color}">${
      firstScore.score
    }</div>
              <div class="metric-label">Performance Score</div>
            </div>
          </div>
        </div>
        
        <div class="comparison-card comparison-highlight cached">
          <h3>Second Request (Redis Cached)</h3>
          <p style="color: var(--gray-color); margin-bottom: 1rem;">Leveraging Redis cache for improved performance</p>
          
          <div class="performance-metrics">
            <div class="metric-card comparison-highlight">
              <div class="metric-value" style="color: ${
                secondScore.color
              }">${secondTime}ms</div>
              <div class="metric-label">Processing Time</div>
            </div>
            <div class="metric-card comparison-highlight">
              <div class="metric-value" style="color: ${secondScore.color}">${
      secondScore.score
    }</div>
              <div class="metric-label">Performance Score</div>
            </div>
          </div>
        </div>
      </div>
      
      <div class="performance-dashboard">
        <div class="dashboard-header">
          <h3>Performance Comparison</h3>
          <div class="performance-pill">${improvement}% Faster</div>
        </div>
        
        ${this._createAnimatedBarChart(firstTime, secondTime)}
      </div>
      
      <div class="improvement-card comparison-highlight">
        <div class="improvement-value">${improvement}%</div>
        <div class="improvement-label">Performance Improvement with Redis Caching</div>
      </div>
      
      <div style="margin-top: 2rem;">
        <h3 style="margin-bottom: 1rem;">How Redis Caching Improves Performance</h3>
        <p style="margin-bottom: 1rem; line-height: 1.5;">
          The first request processes the quote calculation from scratch, involving complex pricing rules, database queries, and business logic.
          Redis saves this calculated result, allowing subsequent identical requests to retrieve the pre-computed data directly from memory.
        </p>
        <p style="margin-bottom: 1rem; line-height: 1.5;">
          Benefits include:
        </p>
        <ul style="margin-left: 1.5rem; margin-bottom: 1.5rem; line-height: 1.5;">
          <li>Significantly faster response times (${improvement}% improvement)</li>
          <li>Reduced server load during peak traffic periods</li>
          <li>Consistent performance even with complex pricing calculations</li>
          <li>Better user experience with near-instant quote generation</li>
        </ul>
      </div>
    `;
  }

  async _generateCustomQuote() {
    try {
      const form = this.shadowObj.querySelector("#customQuoteForm");
      if (!form) {
        console.error("Custom quote form not found");
        return;
      }

      const formData = new FormData(form);
      const trailerType = formData.get("trailerType");
      const usageType = formData.get("usageType");
      const generator = formData.get("generator");
      const startDate = formData.get("startDate");
      const endDate = formData.get("endDate");
      const rentalDays = parseInt(formData.get("rentalDays")) || 1;
      const deliveryAddress = formData.get("deliveryAddress");

      // Handle multiple extras selection from checkboxes
      const selectedExtras = [];
      const extrasCheckboxes = form.querySelectorAll(
        'input[name="extras"]:checked'
      );
      extrasCheckboxes.forEach((checkbox) => {
        selectedExtras.push({ extra_id: checkbox.value, qty: 1 });
      });

      // Add generator to extras if selected (optional)
      if (generator && generator.trim() !== "") {
        selectedExtras.push({ extra_id: generator, qty: 1 });
      }

      // Validate only required fields (extras and generator are optional)
      if (
        !trailerType ||
        !usageType ||
        !startDate ||
        !endDate ||
        !deliveryAddress
      ) {
        this._updateError("Please fill in all required fields.");
        return;
      }

      // Validate dates
      const startDateObj = new Date(startDate);
      const endDateObj = new Date(endDate);
      const today = new Date();
      today.setHours(0, 0, 0, 0);

      if (startDateObj < today) {
        this._updateError("Start date cannot be in the past.");
        return;
      }

      if (endDateObj < startDateObj) {
        this._updateError("End date cannot be before start date.");
        return;
      }

      // Clear any previous errors
      this.state.error = null;
      this._updateError(null);

      // Create custom quote body for API
      const customQuoteBody = {
        delivery_location: deliveryAddress,
        trailer_type: trailerType,
        rental_start_date: startDate,
        rental_days: rentalDays,
        usage_type: usageType,
        extras: selectedExtras,
      };

      console.log("Processing custom quote directly:", customQuoteBody);

      // Process the custom quote directly without adding to samples
      await this._processCustomQuoteDirectly(customQuoteBody);
    } catch (error) {
      console.error("Error generating custom quote:", error);
      this._updateError(
        "An unexpected error occurred while generating the quote."
      );
    }
  }

  _updateResultsSection(content) {
    const resultsSection = this.shadowObj.querySelector(".results-section");
    if (resultsSection) {
      resultsSection.innerHTML = content;
    }
  }

  _updateError(errorMessage) {
    this.state.error = errorMessage;
    this.state.isLoading = false;
    const resultsSection = this.shadowObj.querySelector(".results-section");
    if (resultsSection) {
      resultsSection.innerHTML = `
        <div class="error-container">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          ${errorMessage}
        </div>
      `;
    }
  }

  _setupResultsTabListeners() {
    // Set up tab switching for results section
    const tabs = this.shadowObj.querySelectorAll(
      ".tabs-container .tab:not(.disabled)"
    );
    if (tabs) {
      tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
          // Skip if tab is disabled
          if (tab.classList.contains("disabled")) return;

          // Deactivate all tabs and tab content in results section
          this.shadowObj
            .querySelectorAll(".tabs-container .tab")
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

    // Set up copy button if it exists
    const copyButton = this.shadowObj.querySelector(".copy-result");
    if (copyButton) {
      copyButton.addEventListener("click", () => {
        this._copyResultToClipboard();
      });
    }
  }

  _scrollToResults() {
    // Use setTimeout to ensure DOM is updated after render
    setTimeout(() => {
      const resultsSection = this.shadowObj.querySelector(".results-section");
      if (resultsSection && this.state.result) {
        // Scroll the results section into view with some offset to show the title
        resultsSection.scrollIntoView({
          behavior: "smooth",
          block: "start",
          inline: "nearest",
        });

        // Add a small delay and adjust scroll position to ensure title is visible
        setTimeout(() => {
          const rect = resultsSection.getBoundingClientRect();
          const offset = 80; // Offset to ensure title is fully visible

          if (rect.top < offset) {
            window.scrollBy({
              top: rect.top - offset,
              behavior: "smooth",
            });
          }
        }, 300);
      }
    }, 100);
  }

  async _processCustomQuoteDirectly(quoteBody) {
    try {
      // Update loading state in results section only
      this._updateResultsSection(
        '<div class="loading-container">' +
          this._getLoadingSpinner() +
          '<p class="loading-text">Generating custom quote...</p></div>'
      );

      console.log("Making API request for custom quote:", quoteBody);

      // First API request
      const firstStartTime = performance.now();

      const firstResponse = await this.api.post(this.url, {
        content: "json",
        headers: {
          Authorization: "Bearer 7%FRtf@34hi",
        },
        body: quoteBody,
      });

      const firstEndTime = performance.now();
      const firstClientProcessingTime = Math.round(
        firstEndTime - firstStartTime
      );

      if (!firstResponse.success) {
        this._updateError(
          firstResponse.error_message || "Failed to generate custom quote"
        );
        this._updateResultsSection(
          '<div class="no-results"><p>Failed to generate quote. Please try again.</p></div>'
        );
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
      this._updateResultsSection(this._renderQuoteResult());
      this._scrollToResults();

      // After a short delay, make a second request to demonstrate Redis caching
      setTimeout(async () => {
        this._updateResultsSection(
          '<div class="loading-container">' +
            this._getLoadingSpinner() +
            '<p class="loading-text">Making cached request...</p></div>'
        );

        try {
          const secondStartTime = performance.now();

          const secondResponse = await this.api.post(this.url, {
            content: "json",
            headers: {
              Authorization: "Bearer 7%FRtf@34hi",
            },
            body: quoteBody,
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
          this._updateResultsSection(this._renderResultsSection());

          // Activate tabs after rendering results with comparison
          this._setupResultsTabListeners();

          // Animate the comparison metrics
          setTimeout(() => {
            const comparisonElements = this.shadowObj.querySelectorAll(
              ".comparison-highlight"
            );
            comparisonElements.forEach((el) => {
              el.classList.add("highlight-animation");
            });
          }, 500);
        } catch (error) {
          console.error("Error on second quote request:", error);
          this._updateError("Error making cached request");
        }
      }, 1500);
    } catch (error) {
      console.error("Error processing custom quote:", error);
      this._updateError(
        "An unexpected error occurred while processing the quote."
      );
      this._updateResultsSection(
        '<div class="error-container"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>An unexpected error occurred</div>'
      );
    }
  }

  getStyles() {
    return /* html */ `
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-main), sans-serif;

        }
        
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        
        .container {
          display: flex;
          justify-content: center;
          align-items: flex-start;
          padding: 0 15px;
          background: var(--background);
        }
        
        .quote-builder-container {
          background: var(--background);
          width: 100%;
          max-width: 100%;
          padding: 1.5rem 0;
        }
        
        .header {
          margin-bottom: 2rem;
        }
        
        .header h1 {
          font-size: 2rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.5rem;
        }
        
        .header .subtitle {
          font-size: 1rem;
          color: var(--gray-color);
          margin-bottom: 1.5rem;
        }
        
        .form-container {
          margin-bottom: 2rem;
        }
        
        .error-alert {
          background: var(--error-background);
          color: var(--error-color);
          padding: 1rem;
          border-radius: 0.375rem;
          margin-bottom: 1.5rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .error-alert svg {
          flex-shrink: 0;
          width: 1.25rem;
          height: 1.25rem;
          color: var(--error-color);
        }
        
        .info-alert {
          background: var(--label-focus-background);
          color: var(--accent-color);
          padding: 1rem;
          border-radius: 0.375rem;
          margin-bottom: 1.5rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .info-alert svg {
          flex-shrink: 0;
          width: 1.25rem;
          height: 1.25rem;
          color: var(--accent-color);
        }
        
        .sample-quotes-container {
          margin-bottom: 2rem;
        }
        
        .sample-quotes-container h3 {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 1rem;
        }
        
        .sample-quotes-grid {
          display: flex;
          flex-flow: column;
          gap: 25px;
        }
        
        .sample-card {
          padding: 20px 0 25px;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
          border-bottom: var(--action-border);
        }
        
        .sample-card:hover {
          transform: translateY(-2px);
        }
        
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }
        
        .card-title {
          font-size: 1.25rem;
          margin-bottom: 0.25rem;
        }
        
        .card-subtitle {
          color: var(--gray-color);
        }
        
        .card-location {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          color: var(--text-color);
          font-size: 0.875rem;
          margin-bottom: 1rem;
        }
        
        .card-location svg {
          flex-shrink: 0;
          width: 1rem;
          height: 1rem;
        }
        
        .card-details {
          margin-top: 1rem;
          font-size: 0.875rem;
        }
        
        .detail-item {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.5rem;
          padding-bottom: 0.5rem;
          border-bottom: var(--border);
        }
        
        .detail-item:last-child {
          border-bottom: none;
          margin-bottom: 0;
          padding-bottom: 0;
        }
        
        .detail-label {
          color: var(--gray-color);
        }
        
        .detail-value {
          color: var(--title-color);
          font-weight: 500;
        }
        
        .generate-quote-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          margin-top: 1rem;
          padding: 0.5rem 1rem;
          border: none;
          border-radius: 0.25rem;
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s ease;
        }
        
        .generate-quote-btn:hover {
          background: var(--accent-alt);
        }
        
        .generate-quote-btn svg {
          width: 1rem;
          height: 1rem;
        }
        
        .results-section {
          margin-top: 2rem;
        }
        
        .no-results {
          padding: 10px 15px;
          text-align: center;
          color: var(--gray-color);
          background: var(--hover-background);
          border-radius: 12px;
        }
        
        .tabs-container {
          display: flex;
          border-bottom: var(--border);
          margin-bottom: 1.5rem;
        }
        
        .tab {
          padding: 0.75rem 1.25rem;
          cursor: pointer;
          position: relative;
          color: var(--gray-color);
          transition: color 0.2s ease;
        }
        
        .tab:not(.disabled):hover {
          color: var(--accent-color);
        }
        
        .tab.active {
          color: var(--accent-color);
          font-weight: 500;
        }
        
        .tab.active::after {
          content: "";
          position: absolute;
          bottom: -1px;
          left: 0;
          width: 100%;
          height: 2px;
          background: var(--accent-color);
        }
        
        .tab.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .tab-content {
          display: none;
          color: var(--text-color);
        }
        
        .tab-content.active {
          display: block;
        }
        
        .quote-result {
          background: var(--background);
          border: 0;
          padding: 0;
        }
        
        .result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
          padding-bottom: 1rem;
          border-bottom: var(--border);
        }
        
        .result-title {
          display: flex;
          align-items: center;
          color: var(--title-color);
          gap: 0.5rem;
        }
        
        .result-actions {
          display: flex;
          gap: 0.5rem;
        }
        
        .copy-result {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          padding: 0.5rem 0.75rem;
          border: var(--border-button);
          border-radius: 0.25rem;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.75rem;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .copy-result:hover {
          background: var(--hover-background);
          border-color: var(--accent-color);
        }
        
        .copy-result svg {
          width: 0.875rem;
          height: 0.875rem;
        }
        
        .result-tabs {
          margin-bottom: 1rem;
        }
        
        .detail-section {
          margin-bottom: 1.5rem;
        }
        
        .detail-section h4 {
          margin-bottom: 0.75rem;
          color: var(--title-color);
          font-size: 0.875rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-weight: 600;
        }
        
        .detail-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
          gap: 1rem;
        }
        
        .detail-card {
          background: var(--hover-background);
          padding: 1rem;
          border-radius: 12px;
          transition: all 0.2s ease;
        }
        
        .detail-card:hover {
          transform: translateY(-1px);
          box-shadow: var(--card-box-shadow-alt);
        }
        
        .detail-card-label {
          color: var(--gray-color);
          font-size: 0.75rem;
          margin-bottom: 0.25rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        
        .detail-card-value {
          font-size: 1rem;
          font-weight: 600;
          font-family: var(--font-read);
          color: var(--title-color);
          word-break: break-word;
        }

        .detail-card-value.quote-id {
          font-family: var(--font-mono, 'SF Mono', Consolas, monospace);
          font-size: 0.85rem;
          letter-spacing: 0.025em;
          text-transform: uppercase;
        }
        
        /* Enhanced section headers */
        .detail-section h5 {
          margin: 1rem 0 0.5rem;
          color: var(--title-color);
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-weight: 600;
          border-top: var(--border);
          padding-top: 1rem;
        }
        
        .detail-section h5:first-of-type {
          border-top: none;
          padding-top: 0;
        }
        
        /* Quote header styles */
        .result-header .result-title h3 {
          color: var(--title-color);
          font-size: 1.5rem;
          font-weight: 700;
          margin: 0;
        }
        
        .result-header .result-title p {
          color: var(--gray-color);
          font-size: 0.875rem;
          margin-top: 0.25rem;
          margin-bottom: 0;
        }
        
        /* Enhanced grid layouts for different content types */
        .detail-grid.compact {
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 0.75rem;
        }
        
        .detail-grid.wide {
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        }
        
        /* Special styling for coordinate values */
        .detail-card-value.coordinates {
          font-family: var(--font-mono, 'SF Mono', Consolas, monospace);
          font-size: 0.875rem;
          letter-spacing: 0.025em;
        }
        
        /* Warning and status indicators */
        .detail-card.warning {
          border-left: 4px solid var(--error-color);
          background: var(--error-background);
        }
        
        .detail-card.success {
          border-left: 4px solid var(--success-color);
          background: var(--hover-background);
        }
        
        .detail-card.info {
          border-left: 4px solid var(--accent-color);
          background: var(--label-focus-background);
        }
        
        /* Notes section styling */
        .notes-container {
          background: var(--hover-background);
          padding: 1rem;
          border-radius: 0.5rem;
          color: var(--text-color);
          line-height: 1.5;
          border-left: 4px solid var(--accent-color);
          margin-top: 0.5rem;
        }
        
        .notes-container p {
          margin: 0;
        }
        
        /* Cost breakdown enhancements */
        .cost-breakdown-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 0.75rem;
          margin-top: 1rem;
        }
        
        .cost-breakdown-item {
          background: var(--background);
          border: var(--border);
          border-radius: 0.5rem;
          padding: 0.75rem;
          text-align: center;
        }
        
        .cost-breakdown-label {
          color: var(--gray-color);
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 0.25rem;
        }
        
        .cost-breakdown-value {
          color: var(--title-color);
          font-size: 1.125rem;
          font-weight: 600;
          font-family: var(--font-read);
        }
        
        /* Data sources grid */
        .data-sources-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 0.5rem;
          margin-top: 0.5rem;
        }
        
        .data-source-item {
          background: var(--background);
          border: var(--border);
          border-radius: 0.5rem;
          padding: 0.5rem 0.75rem;
          font-size: 0.875rem;
        }
        
        .data-source-label {
          color: var(--gray-color);
          font-size: 0.75rem;
          margin-bottom: 0.125rem;
        }
        
        .data-source-value {
          color: var(--text-color);
          font-weight: 500;
        }
        
        /* Warning messages styling */
        .warnings-container {
          margin-top: 1rem;
        }
        
        .warning-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem 1rem;
          background: var(--error-background);
          color: var(--error-color);
          border-left: 4px solid var(--error-color);
          margin-bottom: 0.5rem;
          border-radius: 0 0.5rem 0.5rem 0;
        }
        
        .warning-item:last-child {
          margin-bottom: 0;
        }
        
        .warning-icon {
          flex-shrink: 0;
          margin-left: 0.5rem;
        }
        
        /* Enhanced price item variations */
        .price-item.subtotal {
          background: var(--label-focus-background);
          font-weight: 600;
          border-top: 2px solid var(--accent-color);
        }
        
        .price-item.delivery {
          background: var(--tab-background);
        }
        
        .price-item.generator {
          background: var(--user-background);
        }
        
        /* Metadata section enhancements */
        .metadata-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 0.75rem;
        }
        
        .metadata-card {
          background: var(--background);
          border: var(--border);
          border-radius: 0.5rem;
          padding: 0.75rem;
        }
        
        .metadata-label {
          color: var(--gray-color);
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 0.25rem;
        }
        
        .metadata-value {
          color: var(--title-color);
          font-weight: 500;
          font-size: 0.875rem;
        }
        
        /* Processing time indicator */
        .processing-time {
          display: inline-flex;
          align-items: center;
          gap: 0.25rem;
          background: var(--success-background, var(--hover-background));
          color: var(--success-color);
          padding: 0.25rem 0.5rem;
          border-radius: 0.5rem;
          font-size: 0.75rem;
          font-weight: 600;
        }
        
        .processing-time.slow {
          background: var(--error-background);
          color: var(--error-color);
        }
        
        .processing-time.medium {
          background: var(--hubspot-background);
          color: var(--alt-color);
        }
        
        .price-breakdown {
          border: var(--border);
          border-radius: 0.25rem;
          overflow: hidden;
        }
        
        .price-item {
          display: flex;
          justify-content: space-between;
          padding: 0.75rem 1rem;
          color: var(--text-color);
          border-bottom: var(--border);
        }
        
        .price-item:last-child {
          border-bottom: none;
        }
        
        .price-item.total {
          background: var(--hover-background);
          font-weight: 600;
        }
        
        .comparison-container {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
          margin-bottom: 1.5rem;
          justify-items: space-between;
        }
        
        .comparison-card {
          background: var(--background);
          border-radius: 0;
          padding: 0;
          position: relative;
        }

        .comparison-card:first-child {
          border-right: var(--border);
          padding-right: 1.5rem;
        }

        .comparison-card > h3 {
          margin-bottom: 0.5rem;
          color: var(--title-color);
          font-size: 1.125rem;
          font-weight: 600;
        }
        
        .comparison-card.cached::before {
          content: "Redis Cached";
          position: absolute;
          top: 0.5rem;
          right: 0.5rem;
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 0.25rem 0.5rem;
          border-radius: 0.25rem;
        }
        
        .performance-metrics {
          display: flex;
          justify-content: space-between;
          gap: 20px;
          padding: 15px 0 0;
        }
        
        .metric-card {
          background: var(--hover-background);
          padding: 10px 12px;
          width: calc(50% - 30px);
          border-radius: 12px;
          text-align: center;
        }
        
        .metric-value {
          font-size: 2rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }
        
        .metric-label {
          color: var(--gray-color);
          font-size: 0.875rem;
        }
        
        .comparison-highlight {
          transition: all 0.3s ease;
        }
        
        .highlight-animation {
          /* animation: pulse 2s ease-in-out; */
        }
        
        .improvement-card {
          border-top: var(--border);
          border-bottom: var(--border);
          padding: 1.5rem;
          text-align: center;
          margin-top: 1.5rem;
        }
        
        .improvement-value {
          font-size: 2.5rem;
          font-weight: 700;
          color: var(--accent-color);
          margin-bottom: 0.5rem;
        }
        
        .improvement-label {
          font-size: 1rem;
          color: var(--text-color);
        }
        
        .spinner {
          animation: rotate 2s linear infinite;
          width: 2rem;
          height: 2rem;
          margin: 2rem auto;
          display: block;
        }
        
        .spinner .path {
          stroke: var(--accent-color);
          stroke-linecap: round;
          animation: dash 1.5s ease-in-out infinite;
        }
        
        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          text-align: center;
        }
        
        .loading-text {
          margin-top: 1rem;
          color: var(--gray-color);
        }
        
        .error-container {
          background: var(--error-background);
          color: var(--error-color);
          padding: 1rem;
          border-radius: 0.25rem;
          margin-bottom: 1.5rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .error-container svg {
          flex-shrink: 0;
          width: 1.25rem;
          height: 1.25rem;
        }
        
        .quick-options {
          margin-top: 1.5rem;
          margin-bottom: 1.5rem;
        }
        
        .quick-options h3 {
          font-size: 1.125rem;
          font-weight: 600;
          margin-bottom: 1rem;
          color: var(--title-color);
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }
        
        .quick-options h3::before {
          content: "";
          display: block;
          width: 0.25rem;
          height: 1.25rem;
          background: var(--accent-color);
          border-radius: 0.125rem;
        }
        
        /* Comparison Bars from location.js */
        .comparison-bars {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        
        .comparison-bar-container {
          display: flex;
          align-items: start;
          flex-flow: column;
          gap: 1rem;
        }
        
        .comparison-label {
          width: 100%;
          font-size: 0.875rem;
          color: var(--text-color);
          white-space: nowrap;
        }
        
        .comparison-bar-wrapper {
          flex: 1;
          background: var(--hover-background);
          height: 40px;
          width: 100%;
          border-radius: 0.75rem;
          overflow: hidden;
          border: var(--border);
        }
        
        .comparison-bar {
          height: 100%;
          display: flex;
          align-items: start;
          justify-content: flex-end;
          padding: 0 0.75rem;
          color: var(--text-color);
          font-weight: 600;
          font-size: 0.875rem;
          transition: width 1.5s ease-in-out;
        }
        
        /* Performance Dashboard from location.js */
        .performance-dashboard {
          padding: 15px 0 0;
          border-top: var(--border);
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
          color: var(--white-color);
          border-radius: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 100px;
          background: var(--success-color);
        }
        
        /* Form Actions */
        .form-actions {
          display: flex;
          justify-content: flex-end;
          gap: 1rem;
        }
        
        .clear-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.25rem;
          border: var(--border);
          border-radius: 0.25rem;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .clear-btn:hover {
          background: var(--hover-background);
          color: var(--error-color);
        }
        
        .clear-btn svg {
          width: 1rem;
          height: 1rem;
        }
        
        /* Enhanced sections styling */
        .enhanced-section-header {
          color: var(--title-color);
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin: 1rem 0 0.5rem;
        }
        
        .enhanced-section-header.warning {
          color: var(--error-color);
        }
        
        .notes-container {
          background: var(--hover-background);
          padding: 1rem;
          border-radius: 0.5rem;
          color: var(--text-color);
          line-height: 1.5;
        }
        
        .warning-item-container {
          color: var(--error-color);
        }
        
        .warning-icon {
          margin-left: 0.5rem;
        }
        
        @keyframes pulse {
          0% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
            box-shadow: var(--card-box-shadow);
          }
          100% {
            transform: scale(1);
          }
        }
        
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
        
        @media (max-width: 768px) {
          .sample-quotes-grid {
            grid-template-columns: 1fr;
          }
          
          .comparison-container {
            grid-template-columns: 1fr;
          }
          
          .quote-builder {
            padding: 1rem;
          }
          
          .performance-metrics {
            grid-template-columns: 1fr;
          }
          
          .detail-grid {
            grid-template-columns: 1fr;
          }
          
          .result-header {
            flex-direction: column;
            gap: 1rem;
            align-items: flex-start;
          }
          
          .result-title h3 {
            font-size: 1.25rem;
          }
        }
        
        @media (max-width: 480px) {
          .detail-grid {
            grid-template-columns: 1fr;
          }
          
          .quote-builder-container {
            padding: 1rem 0;
          }
          
          .header h1 {
            font-size: 1.5rem;
          }
          
          .sample-card {
            padding: 1rem;
          }
        }

        /* Custom Form Styles */
        .custom-form-container {
          background: var(--background);
          border-radius: 0;
          padding: 0 0 0 10px;
          margin-top: 2rem;
        }

        .quote-form {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .form-section {
          border-bottom: var(--border);
          border-radius: 0;
          padding: 0 0 15px;
          background: var(--background);
        }

        .form-section-title {
          color: var(--title-color);
          font-size: 1.1rem;
          font-weight: 600;
          margin-bottom: 1rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-family: var(--font-main);
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }

        .form-section.dates > .dates {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
        }

        .form-section.dates > .dates > .form-group {
          min-width: 40%;
        }

        .form-group:last-child {
          margin-bottom: 0;
        }

        .form-group label {
          color: var(--label-color);
          font-weight: 500;
          font-size: 0.9rem;
          font-family: var(--font-main);
        }

        .form-group select,
        .form-group input {
          padding: 0.75rem;
          border: var(--input-border);
          border-radius: 0.375rem;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.9rem;
          font-family: var(--font-main);
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .form-group select:focus,
        .form-group input:focus {
          outline: none;
          border: var(--input-border-focus);
          background: var(--label-focus-background);
        }

        .form-group select:invalid,
        .form-group input:invalid {
          border: var(--input-border-error);
        }

        .form-group input[readonly] {
          background: var(--gray-background);
          color: var(--gray-color);
          cursor: not-allowed;
        }

        .form-group select[multiple] {
          min-height: 100px;
          padding: 0.5rem;
        }

        .form-group small {
          margin-top: 0.25rem;
          display: block;
          color: var(--gray-color);
          font-family: var(--font-main);
        }

        .generate-custom-quote-btn {
          background: var(--action-linear);
          color: var(--white-color);
          border: none;
          padding: 0.875rem 1.5rem;
          border-radius: 0.375rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          font-size: 0.9rem;
          font-family: var(--font-main);
          box-shadow: var(--box-shadow);
        }

        .generate-custom-quote-btn:hover:not(:disabled) {
          background: var(--accent-linear);
          transform: translateY(-1px);
          box-shadow: var(--card-box-shadow);
        }

        .generate-custom-quote-btn:disabled {
          background: var(--gray-color);
          cursor: not-allowed;
          opacity: 0.6;
          transform: none;
          box-shadow: none;
        }

        /* Two Column Layout */
        .two-column-layout {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0;
          margin-bottom: 2rem;
        }

        .sample-quotes-column {
          display: flex;
          border-right: var(--border);
          flex-direction: column;
          padding: 0 25px 0 0;
        }

        .custom-form-column {
          display: flex;
          flex-direction: column;
          padding: 0 0 0 20px;
        }

        .sample-quotes-container {
          margin-bottom: 0;
        }

        .custom-quote-container {
          margin-bottom: 0;
        }

        .custom-quote-container .header h3 {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 0.5rem;
        }

        .custom-quote-container .header .subtitle {
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-bottom: 1rem;
        }

        /* Enhanced extras selection styling */
        .extras-container {
          display: flex;
          flex-wrap: wrap;
          gap: 0.75rem;
          margin-top: 0.5rem;
        }

        .extra-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 0.75rem;
          background: var(--hover-background);
          border: var(--border);
          border-radius: 0.375rem;
          transition: all 0.2s ease;
          cursor: pointer;
        }

        .extra-item:hover {
          background: var(--label-focus-background);
          border-color: var(--accent-color);
        }

        .extra-item input[type="checkbox"] {
          margin: 0;
          cursor: pointer;
          accent-color: var(--accent-color);
        }

        .extra-item label {
          margin: 0;
          cursor: pointer;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-color);
        }

        .extra-item input[type="checkbox"]:checked + label {
          color: var(--accent-color);
          font-weight: 600;
        }

        /* Mobile responsiveness for two-column layout */
        @media (max-width: 968px) {
          .two-column-layout {
            grid-template-columns: 1fr;
            gap: 1.5rem;
          }
        }
      </style>
    `;
  }
}
