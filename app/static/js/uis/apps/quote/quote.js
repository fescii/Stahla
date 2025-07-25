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
      selectedQuote: null,
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

  async _processQuote(quoteBody) {
    if (!quoteBody || !this.url) {
      this.state.error = 'Missing quote data or API endpoint';
      this.render();
      return;
    }

    // Set initial loading state
    this.state.isLoading = true;
    this.state.error = null;
    this._updateResultsSection(
      '<div class="loading-container">' +
      this._getLoadingSpinner() +
      '<p class="loading-text">Generating your quote...</p>' +
      '<p class="loading-subtitle">Please wait while we process your request...</p>' +
      '</div>'
    );

    try {
      console.log('Starting quote request...');
      console.log('Sending quote request with body:', quoteBody);

      const response = await this.api.post(this.url, {
        content: 'json',
        headers: {
          Authorization: 'Bearer 7%FRtf@34hi',
        },
        body: quoteBody,
        timeout: 0
      });

      console.log('Quote response received:', response);

      if (!response.success) {
        const errorMsg = response.error_message || 'Failed to generate quote';
        this.state.error = errorMsg;
        this.state.isLoading = false;
        console.error('Quote generation failed:', errorMsg, response);
        this._updateError(errorMsg);
        return;
      }

      this.state.result = response;
      this.state.isLoading = false;

      console.log('Quote request completed successfully.');
      this._updateResultsSection(this._renderQuoteResult());
      this._setupResultsTabListeners();

    } catch (error) {
      console.error('Error generating quote:', error);
      this.state.isLoading = false;
      this.state.error = 'An unexpected error occurred while generating the quote. Please try again.';
      this._updateError(this.state.error);
    }
  }

  _copyResultToClipboard() {
    if (!this.state.result) return;

    const resultText = JSON.stringify(this.state.result, null, 2);
    navigator.clipboard
      .writeText(resultText)
      .then(() => {
        const copyButton = this.shadowObj.querySelector('.copy-result');
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
        console.error('Failed to copy result: ', err);
      });
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
      selectedQuote: null,
    };

    this.render();
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
            ${this.state.error
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
            
            <div class="custom-quote-container">
              ${this._renderCustomForm()}
            </div>
          </div>
          
          <div class="results-section">
            ${this._renderResultsSection()}
          </div>
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
          <p class="loading-subtitle">Please wait while we process your request...</p>
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

    if (this.state.result) {
      return this._renderQuoteResult();
    }

    return /* html */ `
      <div class="results-info">
        <div class="info-container">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <div class="info-content">
            <h3>Quote Results</h3>
            <p>Fill out the form above and click "Generate Custom Quote" to get detailed pricing information for your restroom trailer rental.</p>
          </div>
        </div>
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

    return /* html */ `
      <div class="quote-result">
        <div class="result-header">
          <div class="result-title">
            <h3>Quote #${responseData.quote_id
        ? responseData.quote_id.split("-").pop()
        : "N/A"
      }</h3>
            <p style="color: var(--gray-color); font-size: 0.875rem; margin-top: 0.25rem;">
              ${quote?.product_details?.product_name || "N/A"}
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
              <div class="detail-card-value quote-id">${responseData.quote_id || "N/A"
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
              <div class="detail-card-value">${metadata?.generated_at
        ? new Date(metadata.generated_at).toLocaleDateString()
        : "N/A"
      }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Valid Until</div>
              <div class="detail-card-value">${metadata?.valid_until
        ? new Date(metadata.valid_until).toLocaleDateString()
        : "N/A"
      }</div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <h4>Line Items</h4>
          <div class="price-breakdown">
            ${quote?.line_items
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

        ${quote?.rental_details
        ? `
        <div class="detail-section">
          <h4>Rental Details</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Start Date</div>
              <div class="detail-card-value">${quote.rental_details.rental_start_date || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">End Date</div>
              <div class="detail-card-value">${quote.rental_details.rental_end_date || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Duration</div>
              <div class="detail-card-value">${quote.rental_details.rental_days || 0
        } days</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Usage Type</div>
              <div class="detail-card-value">${quote.rental_details.usage_type || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Pricing Tier</div>
              <div class="detail-card-value">${quote.rental_details.pricing_tier_applied || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Season</div>
              <div class="detail-card-value">${quote.rental_details.seasonal_rate_name || "N/A"
        }</div>
            </div>
          </div>
        </div>
        `
        : ""
      }

        ${quote?.delivery_details
        ? `
        <div class="detail-section">
          <h4>Delivery Details</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Distance</div>
              <div class="detail-card-value">${quote.delivery_details.miles?.toFixed(2) || "N/A"
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
              <div class="detail-card-value">$${quote.delivery_details.per_mile_rate_applied?.toFixed(2) ||
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
              <div class="detail-card-value">${quote.delivery_details.seasonal_multiplier_applied || 1.0
        }x</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Estimated Distance</div>
              <div class="detail-card-value">${quote.delivery_details.is_distance_estimated ? "Yes" : "No"
        }</div>
            </div>
          </div>
        </div>
        `
        : ""
      }

        ${locationDetails
        ? `
        <div class="detail-section">
          <h4>Location Information</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Delivery Address</div>
              <div class="detail-card-value">${locationDetails.delivery_address || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Nearest Branch</div>
              <div class="detail-card-value">${locationDetails.nearest_branch || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Branch Address</div>
              <div class="detail-card-value">${locationDetails.branch_address || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Service Area</div>
              <div class="detail-card-value">${locationDetails.service_area_type || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Drive Time</div>
              <div class="detail-card-value">${locationDetails.estimated_drive_time_minutes
          ? `${Math.floor(
            locationDetails.estimated_drive_time_minutes / 60
          )}h ${locationDetails.estimated_drive_time_minutes % 60}m`
          : "N/A"
        }</div>
            </div>
            ${locationDetails.geocoded_coordinates
          ? `
            <div class="detail-card">
              <div class="detail-card-label">Coordinates</div>
              <div class="detail-card-value">${locationDetails.geocoded_coordinates.latitude?.toFixed(6) ||
          "N/A"
          }, ${locationDetails.geocoded_coordinates.longitude?.toFixed(
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

        ${quote?.budget_details
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
              <div class="detail-card-value">${quote.budget_details.is_delivery_free ? "Yes" : "No"
        }</div>
            </div>
          </div>
          ${quote.budget_details.cost_breakdown
          ? `
            <h5 class="enhanced-section-header">Cost Breakdown</h5>
            <div class="price-breakdown">
              ${Object.entries(quote.budget_details.cost_breakdown)
            .map(
              ([category, amount]) => `
                <div class="price-item">
                  <span>${category.charAt(0).toUpperCase() + category.slice(1)
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

        ${quote?.product_details
        ? `
        <div class="detail-section">
          <h4>Product Information</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Product ID</div>
              <div class="detail-card-value">${quote.product_details.product_id || "N/A"
        }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Product Name</div>
              <div class="detail-card-value">${quote.product_details.product_name || "N/A"
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
              <div class="detail-card-value">${quote.product_details.is_ada_compliant ? "Yes" : "No"
        }</div>
            </div>
            ${quote.product_details.stall_count
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
              <div class="detail-card-value">${metadata?.calculation_time_ms ||
      responseData.client_processing_time_ms ||
      "N/A"
      }${metadata?.calculation_time_ms
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
              <div class="detail-card-value">${metadata?.source_system || "N/A"
      }</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Calculation Method</div>
              <div class="detail-card-value">${metadata?.calculation_method || "N/A"
      }</div>
            </div>
          </div>
          ${metadata?.data_sources
        ? `
            <h5 class="enhanced-section-header">Data Sources</h5>
            <div class="detail-grid">
              ${Object.entries(metadata.data_sources)
          .map(
            ([source, value]) => `
                <div class="detail-card">
                  <div class="detail-card-label">${source.charAt(0).toUpperCase() + source.slice(1)
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
          ${metadata?.warnings && metadata.warnings.length > 0
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

        ${quote?.notes
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

      console.log("Processing quote directly for custom quote:", customQuoteBody);

      // Process the quote directly instead of opening popup
      this._processQuote(customQuoteBody);
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

  getStyles() {
    return /* css */ `
      <style>
        /* ===== BASE STYLES ===== */
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

        /* ===== LAYOUT COMPONENTS ===== */
        .container {
          display: flex;
          justify-content: center;
          align-items: flex-start;
          padding: 15px 0;
          background: var(--background);
        }

        .quote-builder-container {
          background: var(--background);
          width: 100%;
          max-width: 100%;
          padding: 0;
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
        
        .form-container {
          margin-bottom: 2rem;
        }
        
        .custom-quote-container {
          margin-bottom: 2rem;
        }
        
        .results-section {
          margin-top: 2rem;
          padding: 2rem 0;
        }

        .results-info {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 200px;
          padding: 2rem;
        }

        .info-container {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 2rem;
          border: var(--border);
          border-radius: 0.75rem;
          background: var(--stat-background);
          max-width: 600px;
          text-align: left;
        }

        .info-container svg {
          color: var(--accent-color);
          flex-shrink: 0;
        }

        .info-content h3 {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 0.5rem;
        }

        .info-content p {
          color: var(--text-color);
          font-size: 0.9rem;
          line-height: 1.5;
        }

        /* ===== FORM COMPONENTS ===== */
        .form-group {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          margin-bottom: 1rem;
        }

        .form-group:last-child {
          margin-bottom: 0;
        }

        .form-group label {
          font-weight: 600;
          color: var(--label-color);
          font-size: 0.9rem;
          margin-bottom: 0.25rem;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
          padding: 0.75rem;
          border: var(--input-border);
          border-radius: 0.375rem;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.9rem;
          font-family: var(--font-main);
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        /* Date input calendar icon styling */
        .form-group input[type="date"] {
          color: var(--text-color);
          color-scheme: dark;
        }

        .form-group input[type="date"]::-webkit-calendar-picker-indicator {
          background-color: var(--accent-color);
          border-radius: 3px;
          cursor: pointer;
          filter: invert(0) sepia(1) saturate(5) hue-rotate(175deg);
        }

        .form-group input[type="date"]::-webkit-calendar-picker-indicator:hover {
          background-color: var(--title-color);
        }

        /* Firefox date input styling */
        .form-group input[type="date"]::-moz-calendar-picker-indicator {
          background-color: var(--accent-color);
          border-radius: 3px;
          cursor: pointer;
        }

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
          outline: none;
          border: var(--input-border-focus);
          background: var(--label-focus-background);
          color: var(--text-color);
        }

        .form-group input:invalid {
          border: var(--input-border-error);
        }

        .form-group input:valid {
          border: var(--input-border-focus);
        }

        .form-group select {
          cursor: pointer;
        }

        .form-group select option {
          color: var(--text-color);
          background: var(--background);
        }

        .form-group input::placeholder {
          color: var(--gray-color);
        }

        .form-group textarea {
          resize: vertical;
          min-height: 100px;
        }

        .form-group textarea::placeholder {
          color: var(--gray-color);
        }

        .form-group input[readonly] {
          background: var(--gray-background);
          color: var(--gray-color);
          cursor: not-allowed;
        }

        .form-actions {
          display: flex;
          justify-content: flex-end;
          gap: 1rem;
          margin-top: 1.5rem;
        }

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
          color: var(--label-color);
        }

        .extra-item input[type="checkbox"]:checked + label {
          color: var(--accent-color);
          font-weight: 600;
        }

        /* ===== BUTTONS ===== */
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

        /* ===== LOADING COMPONENTS ===== */
        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 2rem;
          gap: 1rem;
        }

        .spinner {
          width: 40px;
          height: 40px;
          animation: spin 1s linear infinite;
        }

        .spinner .path {
          stroke: var(--accent-color);
          stroke-linecap: round;
          stroke-dasharray: 90, 150;
          stroke-dashoffset: 0;
          animation: dash 1.5s ease-in-out infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
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

        .loading-text {
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
          margin: 0;
        }

        .loading-subtitle {
          font-size: 0.9rem;
          color: var(--gray-color);
          margin: 0;
        }

        /* ===== ERROR COMPONENTS ===== */
        .error-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          padding: 2rem;
          background: var(--error-background);
          border-radius: 0.75rem;
          border: 1px solid var(--error-color);
          color: var(--error-color);
          text-align: center;
        }

        .error-container svg {
          width: 24px;
          height: 24px;
          color: var(--error-color);
        }

        /* ===== ALERTS ===== */
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

        /* ===== RESULTS & TABS ===== */
        .no-results {
          padding: 10px 15px;
          text-align: center;
          color: var(--gray-color);
          background: var(--hover-background);
          border-radius: 12px;
        }

        /* ===== QUOTE RESULT COMPONENTS ===== */
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
        
        .result-title h3 {
          font-size: 1.5rem;
          font-weight: 700;
          margin: 0;
          color: var(--title-color);
        }
        
        .result-title p {
          color: var(--gray-color);
          font-size: 0.875rem;
          margin-top: 0.25rem;
          margin-bottom: 0;
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

        /* ===== DETAIL COMPONENTS ===== */
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
        
        .detail-section h5.warning {
          color: var(--error-color);
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

        .price-item.warning-item-container {
          color: var(--error-color);
        }
        
        .warning-icon {
          margin-left: 0.5rem;
        }

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

        /* ===== CUSTOM FORM STYLES ===== */
        .custom-form-container {
          background: var(--background);
          border-radius: 0;
          padding: 0;
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
          color: var(--label-color);
          font-size: 1.1rem;
          font-weight: 600;
          margin-bottom: 1rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          font-family: var(--font-main);
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

        .form-group small {
          margin-top: 0.25rem;
          display: block;
          color: var(--gray-color);
          font-family: var(--font-main);
        }

        /* Enhanced form styling for better theme integration */
        .form-group select:hover,
        .form-group input:hover {
          border-color: var(--accent-color);
        }

        .form-group select:disabled,
        .form-group input:disabled {
          background: var(--gray-background);
          color: var(--gray-color);
          cursor: not-allowed;
          opacity: 0.6;
        }

        /* ===== RESPONSIVE STYLES ===== */
        @media (max-width: 768px) {
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
          .quote-builder-container {
            padding: 1rem 0;
          }
          
          .header h1 {
            font-size: 1.5rem;
          }
          
          .form-actions {
            flex-direction: column;
          }
          
          .form-section.dates > .dates {
            flex-direction: column;
            gap: 1rem;
          }
        }
      </style>
    `;
  }
}
