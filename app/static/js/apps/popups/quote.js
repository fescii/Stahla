export default class QuotePopup extends HTMLElement {
  constructor() {
    super();
    this.app = window.app;
    this.api = this.app.api;
    this.shadowObj = this.attachShadow({ mode: 'open' });

    // Component state
    this.state = {
      isLoading: false,
      error: null,
      result: null,
      secondResult: null,
      showComparison: false,
      quoteBody: null,
      isInitialized: false
    };

    // Don't render in constructor - wait for connectedCallback
  }

  connectedCallback() {
    // Prevent multiple initializations
    if (this.state.isInitialized) return;
    this.state.isInitialized = true;

    this.disableScroll();

    // Read attributes here where they're guaranteed to be available
    this.url = this.getAttribute('api');
    this.quoteData = this.getAttribute('quote-data');

    console.log('QuotePopup initialized with URL:', this.url, 'and quote data:', this.quoteData);

    // Render initial loading state
    this.render();
    this._setupEventListeners();

    // Parse quote data and start processing
    if (this.quoteData) {
      try {
        this.state.quoteBody = JSON.parse(this.quoteData);
        this._processQuote();
      } catch (error) {
        console.error('Error parsing quote data:', error);
        this.state.error = 'Invalid quote data provided';
        this.render();
      }
    } else {
      this.state.error = 'No quote data provided';
      this.render();
    }
  }

  disconnectedCallback() {
    this.enableScroll();
  }

  disableScroll() {
    let scrollTop = window.scrollY || document.documentElement.scrollTop;
    let scrollLeft = window.scrollX || document.documentElement.scrollLeft;
    document.body.classList.add("stop-scrolling");

    window.onscroll = function () {
      window.scrollTo(scrollLeft, scrollTop);
    };
  }

  enableScroll() {
    document.body.classList.remove("stop-scrolling");
    window.onscroll = function () { };
  }

  _setupEventListeners() {
    // Close modal handlers
    const overlay = this.shadowObj.querySelector('.overlay');
    const closeButton = this.shadowObj.querySelector('.close-button');

    if (overlay) {
      overlay.addEventListener('click', () => this._closeModal());
    }

    if (closeButton) {
      closeButton.addEventListener('click', () => this._closeModal());
    }

    // Modern tab switching
    const modernTabs = this.shadowObj.querySelectorAll('.modern-tab:not(.disabled)');
    const tabSlider = this.shadowObj.querySelector('.tab-slider');

    if (modernTabs && tabSlider) {
      modernTabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
          if (tab.classList.contains('disabled')) return;

          // Remove active from all tabs and content
          this.shadowObj
            .querySelectorAll('.modern-tab')
            .forEach((t) => t.classList.remove('active'));
          this.shadowObj
            .querySelectorAll('.modern-tab-content')
            .forEach((c) => {
              c.classList.remove('active');
              c.classList.remove('slide-in');
            });

          // Add active to clicked tab
          tab.classList.add('active');
          const tabName = tab.dataset.tab;
          const content = this.shadowObj.querySelector(`.${tabName}-tab`);

          if (content) {
            // Animate tab slider
            this._moveTabSlider(tab, tabSlider);

            // Add slide-in animation with delay
            setTimeout(() => {
              content.classList.add('active');
              content.classList.add('slide-in');
            }, 150);
          }

          // If switching to performance tab, trigger animations
          if (tabName === 'performance' && this.state.showComparison) {
            setTimeout(() => {
              const animatedElements = this.shadowObj.querySelectorAll(
                '.cached-bar, .metric-card-modern.highlight, .comparison-highlight'
              );
              animatedElements.forEach((el) => {
                el.classList.add('highlight-animation');
              });
            }, 400);
          }
        });
      });

      // Initialize tab slider position
      const activeTab = this.shadowObj.querySelector('.modern-tab.active');
      if (activeTab) {
        this._moveTabSlider(activeTab, tabSlider);
      }
    }

    // Copy results button
    const copyButton = this.shadowObj.querySelector('.copy-result');
    if (copyButton) {
      copyButton.addEventListener('click', () => {
        this._copyResultToClipboard();
      });
    }
  }

  _moveTabSlider(activeTab, tabSlider) {
    const tabRect = activeTab.getBoundingClientRect();
    const containerRect = activeTab.parentElement.getBoundingClientRect();
    const offsetLeft = tabRect.left - containerRect.left;
    const width = tabRect.width;

    tabSlider.style.transform = `translateX(${offsetLeft}px)`;
    tabSlider.style.width = `${width}px`;
  }

  _closeModal() {
    // Dispatch close event for cleanup
    this.dispatchEvent(new CustomEvent('quote-closed', {
      bubbles: true,
      cancelable: true
    }));

    // Enable scroll and remove modal
    this.enableScroll();
    this.remove();
  } async _processQuote() {
    if (!this.state.quoteBody || !this.url) {
      this.state.error = 'Missing quote data or API endpoint';
      this.render();
      return;
    }

    // Set initial loading state
    this.state.isLoading = true;
    this.state.error = null;
    this.render();

    try {
      // First API request - no timeout, wait for completion
      console.log('Starting first quote request...');
      this._updateLoadingMessage(
        'Generating your quote...',
        'Processing request without timeout. This may take up to several minutes for complex quotes.'
      );

      const firstStartTime = performance.now();

      console.log('Sending quote request with body:', this.state.quoteBody);

      // Remove any potential timeout by not setting one and letting it complete naturally
      const firstResponse = await this.api.post(this.url, {
        content: 'json',
        headers: {
          Authorization: 'Bearer 7%FRtf@34hi',
        },
        body: this.state.quoteBody,
        // Explicitly ensure no timeout
        timeout: 0
      });

      const firstEndTime = performance.now();
      const firstClientProcessingTime = Math.round(firstEndTime - firstStartTime);

      console.log('First quote response received after', firstClientProcessingTime, 'ms:', firstResponse);

      if (!firstResponse.success) {
        const errorMsg = firstResponse.error_message || 'Failed to generate quote';
        this.state.error = errorMsg;
        this.state.isLoading = false;
        console.error('Quote generation failed:', errorMsg, firstResponse);
        this.render();
        return;
      }

      // Add client-side processing time
      if (firstResponse.data) {
        firstResponse.data.client_processing_time_ms = firstClientProcessingTime;
        firstResponse.data.request_number = 1;
        firstResponse.data.cached = false;
      }

      this.state.result = firstResponse;
      console.log('First request completed successfully. Starting second request for performance comparison...');

      // Update loading message for second request and ensure first request is fully processed
      this._updateLoadingMessage(
        'Running performance comparison...',
        'First quote completed! Now demonstrating Redis caching speed with a second identical request.'
      );

      // Ensure we only start second request after first is completely done
      if (this.state.result?.success) {
        try {
          console.log('Starting second quote request for caching demonstration...');
          const secondStartTime = performance.now();

          // Second request - also no timeout
          const secondResponse = await this.api.post(this.url, {
            content: 'json',
            headers: {
              Authorization: 'Bearer 7%FRtf@34hi',
            },
            body: this.state.quoteBody,
            // Explicitly ensure no timeout
            timeout: 0
          });

          const secondEndTime = performance.now();
          const secondClientProcessingTime = Math.round(secondEndTime - secondStartTime);

          console.log('Second quote response received after', secondClientProcessingTime, 'ms:', secondResponse);

          if (secondResponse.data) {
            secondResponse.data.client_processing_time_ms = secondClientProcessingTime;
            secondResponse.data.request_number = 2;
            secondResponse.data.cached = true;
          }

          this.state.secondResult = secondResponse;
          this.state.showComparison = true;
          this.state.isLoading = false;

          console.log('Both requests completed. Rendering final results.');
          this.render();

          // Animate comparison highlights after rendering is complete
          setTimeout(() => {
            const comparisonElements = this.shadowObj.querySelectorAll('.comparison-highlight');
            comparisonElements.forEach((el) => {
              el.classList.add('highlight-animation');
            });
          }, 500);

        } catch (error) {
          console.error('Error on second quote request:', error);
          // Still show first result even if second fails
          this.state.isLoading = false;
          console.log('Second request failed, but showing first result anyway.');
          this.render();
        }
      } else {
        // If first request succeeded but we're not running second request
        this.state.isLoading = false;
        console.log('First request completed, no second request needed.');
        this.render();
      }
    } catch (error) {
      console.error('Error generating quote:', error);
      this.state.isLoading = false;
      this.state.error = 'An unexpected error occurred while generating the quote. Please try again.';
      this.render();
    }
  }

  _updateLoadingMessage(message, subtitle = null) {
    const loadingText = this.shadowObj.querySelector('.loading-text');
    const loadingSubtitle = this.shadowObj.querySelector('.loading-subtitle');

    if (loadingText) {
      loadingText.textContent = message;
    }

    if (loadingSubtitle && subtitle) {
      loadingSubtitle.textContent = subtitle;
    } else if (loadingSubtitle) {
      loadingSubtitle.textContent = 'Please wait while we process your request...';
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

  _formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  }

  _calculatePerformanceScore(processingTime) {
    let color, score;

    if (processingTime < 600) {
      color = 'var(--success-color)';
      score = 'Excellent';
    } else if (processingTime < 850) {
      color = 'var(--accent-color)';
      score = 'Good';
    } else if (processingTime < 1100) {
      color = 'var(--alt-color)';
      score = 'Average';
    } else {
      color = 'var(--error-color)';
      score = 'Slow';
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

  _createInteractiveChart(firstTime, secondTime, improvement) {
    const maxTime = Math.max(firstTime, secondTime);
    const firstPercentage = (firstTime / maxTime) * 100;
    const secondPercentage = (secondTime / maxTime) * 100;

    return /* html */ `
      <div class="interactive-chart-modern">
        <div class="chart-header-modern">
          <div class="chart-legend-modern">
            <div class="legend-item-modern">
              <div class="legend-color-modern fresh"></div>
              <span>Fresh Request</span>
            </div>
            <div class="legend-item-modern">
              <div class="legend-color-modern cached"></div>
              <span>Redis Cached</span>
            </div>
          </div>
          <div class="chart-improvement-modern">
            <span class="improvement-badge-modern">${improvement}% Faster</span>
          </div>
        </div>
        
        <div class="chart-bars-modern">
          <div class="chart-bar-group-modern">
            <div class="bar-label-modern">Fresh Request</div>
            <div class="bar-container-modern">
              <div class="bar-modern fresh-bar" style="width: ${firstPercentage}%">
                <div class="bar-value-modern">${firstTime}ms</div>
              </div>
            </div>
          </div>
          
          <div class="chart-bar-group-modern">
            <div class="bar-label-modern">Redis Cached</div>
            <div class="bar-container-modern">
              <div class="bar-modern cached-bar animated" style="width: ${secondPercentage}%">
                <div class="bar-value-modern">${secondTime}ms</div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="chart-footer-modern">
          <div class="time-saved-modern">
            <span class="metric-highlight-modern">${firstTime - secondTime}ms</span>
            <span class="metric-label-modern">Time Saved</span>
          </div>
          <div class="efficiency-rating-modern">
            <span class="metric-highlight-modern">${improvement < 50 ? 'Good' : improvement < 70 ? 'Great' : 'Excellent'}</span>
            <span class="metric-label-modern">Cache Efficiency</span>
          </div>
        </div>
      </div>
    `;
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
    this._setupEventListeners();
  }

  _renderContent() {
    if (this.state.isLoading) {
      return /* html */ `
        <div class="loading-container">
          ${this._getLoadingSpinner()}
          <p class="loading-text">Generating quote...</p>
          <p class="loading-subtitle">Please wait while we process your request...</p>
          <div class="loading-details">
            <small>⏱️ Requests will complete without timeout</small>
          </div>
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
          <p>Processing quote request...</p>
        </div>
      `;
    }

    return /* html */ `
      <div class="content-body-container">
        <div class="modern-tabs-wrapper">
          <div class="modern-tabs-container">
            <div class="tab-slider"></div>
            <div class="modern-tab active" data-tab="quote">
              <div class="tab-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14,2 14,8 20,8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10,9 9,9 8,9"></polyline>
                </svg>
              </div>
              <div class="tab-content-wrapper">
                <span class="tab-title">Quote Details</span>
                <span class="tab-subtitle">View pricing & specifications</span>
              </div>
            </div>
            
            <div class="modern-tab ${!this.state.showComparison ? 'disabled' : ''}" data-tab="performance">
              <div class="tab-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </div>
              <div class="tab-content-wrapper">
                <span class="tab-title">Performance Analysis</span>
                <span class="tab-subtitle">
                  ${!this.state.showComparison ? 'Running comparison...' : 'Redis caching performance'}
                </span>
              </div>
              ${!this.state.showComparison ? '' : `
                <div class="tab-status-indicator">
                  <div class="status-dot active"></div>
                </div>
              `}
            </div>
          </div>
        </div>
        
        <div class="tab-content-container">
          <div class="modern-tab-content quote-tab active slide-in">
            ${this._renderQuoteResult()}
          </div>
          
          <div class="modern-tab-content performance-tab">
            ${this._renderPerformanceComparison()}
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
        ${this._renderQuoteHeader(responseData, quote, metadata)}
        ${this._renderPricingOverview(quote)}
        ${this._renderLineItems(quote)}
        ${this._renderProductDetails(quote)}
        ${this._renderRentalDetails(quote)}
        ${this._renderDeliveryDetails(quote)}
        ${this._renderLocationDetails(locationDetails)}
        ${this._renderBudgetAnalysis(quote)}
        ${this._renderMetadata(responseData, metadata)}
      </div>
    `;
  }

  _renderQuoteHeader(responseData, quote, metadata) {
    return /* html */ `
      <div class="quote-header">
        <div class="quote-title-section">
          <div class="quote-id-badge">
            <span class="badge-label">Quote ID</span>
            <span class="badge-value">${responseData.quote_id || 'N/A'}</span>
          </div>
          <h2 class="product-title">${quote?.product_details?.product_name || 'Restroom Trailer Rental'}</h2>
          <p class="quote-subtitle">${quote?.product_details?.product_description || 'Professional restroom trailer rental service'}</p>
          ${quote.delivery_tier_applied ? `
            <div class="delivery-tier-info">
              <span class="tier-label">Delivery Tier:</span>
              <span class="tier-value">${quote.delivery_tier_applied}</span>
            </div>
          ` : ''}
        </div>
        
        <div class="quote-actions">
          <div class="quote-total">
            <span class="total-label">Estimated Total</span>
            <span class="total-amount">${this._formatCurrency(quote?.budget_details?.estimated_total || quote?.subtotal || 0)}</span>
            ${quote?.subtotal !== quote?.budget_details?.estimated_total ? `
              <span class="subtotal-note">Subtotal: ${this._formatCurrency(quote?.subtotal || 0)}</span>
            ` : ''}
          </div>
          <button class="copy-result">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect width="14" height="14" x="8" y="8" rx="2" ry="2"></rect>
              <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"></path>
            </svg>
            Copy Details
          </button>
        </div>
      </div>
    `;
  }

  _renderPricingOverview(quote) {
    return /* html */ `
      <div class="pricing-overview">
        <div class="overview-cards">
          <div class="overview-card primary">
            <div class="card-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
              </svg>
            </div>
            <div class="card-content">
              <span class="card-label">Estimated Total</span>
              <span class="card-value">${this._formatCurrency(quote?.budget_details?.estimated_total || quote?.subtotal || 0)}</span>
            </div>
          </div>
          
          <div class="overview-card">
            <div class="card-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
            </div>
            <div class="card-content">
              <span class="card-label">Daily Rate</span>
              <span class="card-value">${this._formatCurrency(quote?.budget_details?.daily_rate_equivalent || 0)}</span>
            </div>
          </div>
          
          <div class="overview-card">
            <div class="card-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
            </div>
            <div class="card-content">
              <span class="card-label">Delivery Distance</span>
              <span class="card-value">${quote?.delivery_details?.miles?.toFixed(1) || 'N/A'} mi</span>
            </div>
          </div>
          
          <div class="overview-card">
            <div class="card-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
            </div>
            <div class="card-content">
              <span class="card-label">Rental Period</span>
              <span class="card-value">${quote?.rental_details?.rental_days || 0} days</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderLineItems(quote) {
    if (!quote?.line_items || quote.line_items.length === 0) {
      return `
        <div class="detail-section">
          <h4>Line Items</h4>
          <div class="empty-state">No line items available</div>
        </div>
      `;
    }

    return /* html */ `
      <div class="detail-section">
        <h4>Line Items</h4>
        <div class="line-items-table">
          <div class="table-header">
            <span>Description</span>
            <span>Unit Price</span>
            <span>Qty</span>
            <span>Total</span>
          </div>
          ${quote.line_items.map(item => `
            <div class="table-row">
              <span class="item-description">${item.description || 'N/A'}</span>
              <span class="item-unit-price">${this._formatCurrency(item.unit_price || 0)}</span>
              <span class="item-quantity">${item.quantity || 1}</span>
              <span class="item-total">${this._formatCurrency(item.total || 0)}</span>
            </div>
          `).join('')}
          <div class="table-footer">
            <span class="footer-label">Subtotal</span>
            <span class="footer-total">${this._formatCurrency(quote.subtotal || 0)}</span>
          </div>
        </div>
        ${quote.notes ? `<div class="quote-notes"><strong>Note:</strong> ${quote.notes}</div>` : ''}
      </div>
    `;
  }

  _renderProductDetails(quote) {
    if (!quote?.product_details) return '';

    const product = quote.product_details;
    return /* html */ `
      <div class="detail-section">
        <h4>Product Information</h4>
        <div class="product-details">
          <div class="product-specs">
            <div class="spec-grid">
              <div class="spec-item">
                <span class="spec-label">Product ID</span>
                <span class="spec-value">${product.product_id || 'N/A'}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Stall Count</span>
                <span class="spec-value">${product.stall_count || 'N/A'}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">ADA Compliant</span>
                <span class="spec-value ${product.is_ada_compliant ? 'compliant' : 'not-compliant'}">
                  ${product.is_ada_compliant ? 'Yes' : 'No'}
                </span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Base Rate</span>
                <span class="spec-value">${this._formatCurrency(product.base_rate || 0)}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Adjusted Rate</span>
                <span class="spec-value">${this._formatCurrency(product.adjusted_rate || 0)}</span>
              </div>
              ${product.trailer_size_ft ? `
              <div class="spec-item">
                <span class="spec-label">Size</span>
                <span class="spec-value">${product.trailer_size_ft} ft</span>
              </div>
              ` : ''}
              ${product.capacity_persons ? `
              <div class="spec-item">
                <span class="spec-label">Capacity</span>
                <span class="spec-value">${product.capacity_persons} persons</span>
              </div>
              ` : ''}
            </div>
          </div>
          ${product.features && product.features.length > 0 ? `
            <div class="product-features">
              <span class="features-label">Features:</span>
              <div class="features-list">
                ${product.features.map(feature => `<span class="feature-tag">${feature}</span>`).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _renderRentalDetails(quote) {
    if (!quote?.rental_details) return '';

    const rental = quote.rental_details;
    return /* html */ `
      <div class="detail-section">
        <h4>Rental Information</h4>
        <div class="rental-details">
          <div class="rental-period">
            <div class="period-item start-date">
              <div class="period-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M8 2v4"></path>
                  <path d="M16 2v4"></path>
                  <rect width="18" height="18" x="3" y="4" rx="2"></rect>
                  <path d="M3 10h18"></path>
                  <circle cx="8" cy="16" r="2"></circle>
                </svg>
              </div>
              <span class="period-label">Start Date</span>
              <span class="period-value">${new Date(rental.rental_start_date).toLocaleDateString() || 'N/A'}</span>
              <span class="period-description">Rental begins</span>
            </div>
            <div class="period-item end-date">
              <div class="period-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M8 2v4"></path>
                  <path d="M16 2v4"></path>
                  <rect width="18" height="18" x="3" y="4" rx="2"></rect>
                  <path d="M3 10h18"></path>
                  <path d="m9 16 2 2 4-4"></path>
                </svg>
              </div>
              <span class="period-label">End Date</span>
              <span class="period-value">${new Date(rental.rental_end_date).toLocaleDateString() || 'N/A'}</span>
              <span class="period-description">Rental ends</span>
            </div>
            <div class="period-item duration">
              <div class="period-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <span class="period-label">Duration</span>
              <span class="period-value">${rental.rental_days || 0} days</span>
              <span class="period-description">Total period</span>
            </div>
          </div>
          
          <div class="rental-specs">
            <div class="spec-grid">
              <div class="spec-item">
                <span class="spec-label">Usage Type</span>
                <span class="spec-value">${rental.usage_type ? rental.usage_type.charAt(0).toUpperCase() + rental.usage_type.slice(1) : 'N/A'}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Pricing Tier</span>
                <span class="spec-value">${rental.pricing_tier_applied || 'N/A'}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Season</span>
                <span class="spec-value">${rental.seasonal_rate_name || 'N/A'}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Seasonal Multiplier</span>
                <span class="spec-value">${rental.seasonal_multiplier || 1.0}x</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Rental Weeks</span>
                <span class="spec-value">${rental.rental_weeks || 0}</span>
              </div>
              <div class="spec-item">
                <span class="spec-label">Rental Months</span>
                <span class="spec-value">${rental.rental_months || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderDeliveryDetails(quote) {
    if (!quote?.delivery_details) return '';

    const delivery = quote.delivery_details;
    return /* html */ `
      <div class="detail-section">
        <h4>Delivery & Logistics</h4>
        <div class="delivery-details">
          <div class="delivery-summary">
            <div class="summary-card">
              <div class="summary-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2"></path>
                  <path d="M15 18H9"></path>
                  <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14"></path>
                  <circle cx="17" cy="18" r="2"></circle>
                  <circle cx="7" cy="18" r="2"></circle>
                </svg>
              </div>
              <div class="summary-content">
                <span class="summary-label">Total Delivery Cost</span>
                <span class="summary-value">${this._formatCurrency(delivery.total_delivery_cost || 0)}</span>
              </div>
            </div>
          </div>
          
          <div class="delivery-breakdown">
            <div class="breakdown-grid">
              <div class="breakdown-item">
                <span class="breakdown-label">Distance</span>
                <span class="breakdown-value">${delivery.miles?.toFixed(2) || 'N/A'} miles</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Per Mile Rate (Applied)</span>
                <span class="breakdown-value">$${delivery.per_mile_rate_applied?.toFixed(2) || '0.00'}</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Per Mile Rate (Original)</span>
                <span class="breakdown-value">$${delivery.original_per_mile_rate?.toFixed(2) || '0.00'}</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Base Fee (Applied)</span>
                <span class="breakdown-value">${this._formatCurrency(delivery.base_fee_applied || 0)}</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Base Fee (Original)</span>
                <span class="breakdown-value">${this._formatCurrency(delivery.original_base_fee || 0)}</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Seasonal Multiplier</span>
                <span class="breakdown-value">${delivery.seasonal_multiplier_applied || 1.0}x</span>
              </div>
              <div class="breakdown-item">
                <span class="breakdown-label">Distance Estimated</span>
                <span class="breakdown-value ${delivery.is_distance_estimated ? 'estimated' : 'exact'}">
                  ${delivery.is_distance_estimated ? 'Yes' : 'No'}
                </span>
              </div>
            </div>
          </div>
          
          ${delivery.calculation_reason ? `
            <div class="delivery-note">
              <strong>Rate Calculation:</strong> ${delivery.calculation_reason}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _renderLocationDetails(locationDetails) {
    if (!locationDetails) return '';

    return /* html */ `
      <div class="detail-section">
        <h4>Location & Service Area</h4>
        <div class="location-details">
          <div class="location-summary">
            <div class="address-card">
              <div class="address-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
              </div>
              <div class="address-content">
                <span class="address-label">Delivery Address</span>
                <span class="address-value">${locationDetails.delivery_address || 'N/A'}</span>
              </div>
            </div>
          </div>
          
          <div class="service-info">
            <div class="service-grid">
              <div class="service-item">
                <span class="service-label">Nearest Branch</span>
                <span class="service-value">${locationDetails.nearest_branch || 'N/A'}</span>
              </div>
              <div class="service-item">
                <span class="service-label">Branch Address</span>
                <span class="service-value branch-address">${locationDetails.branch_address || 'N/A'}</span>
              </div>
              <div class="service-item">
                <span class="service-label">Service Area</span>
                <span class="service-value service-${locationDetails.service_area_type?.toLowerCase() || 'standard'}">
                  ${locationDetails.service_area_type || 'N/A'}
                </span>
              </div>
              <div class="service-item">
                <span class="service-label">Distance to Branch</span>
                <span class="service-value">${locationDetails.distance_miles?.toFixed(2) || 'N/A'} miles</span>
              </div>
              <div class="service-item">
                <span class="service-label">Estimated Drive Time</span>
                <span class="service-value">
                  ${locationDetails.estimated_drive_time_minutes ?
        `${Math.floor(locationDetails.estimated_drive_time_minutes / 60)}h ${locationDetails.estimated_drive_time_minutes % 60}m` :
        'N/A'}
                </span>
              </div>
              <div class="service-item">
                <span class="service-label">Location Estimated</span>
                <span class="service-value ${locationDetails.is_estimated_location ? 'estimated' : 'exact'}">
                  ${locationDetails.is_estimated_location ? 'Yes' : 'No'}
                </span>
              </div>
              ${locationDetails.geocoded_coordinates ? `
              <div class="service-item">
                <span class="service-label">Coordinates</span>
                <span class="service-value coordinates">
                  ${locationDetails.geocoded_coordinates.latitude?.toFixed(6)}, ${locationDetails.geocoded_coordinates.longitude?.toFixed(6)}
                </span>
              </div>
              ` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderBudgetAnalysis(quote) {
    if (!quote?.budget_details) return '';

    const budget = quote.budget_details;
    return /* html */ `
      <div class="detail-section">
        <h4>Budget Analysis</h4>
        <div class="budget-analysis">
          <div class="rate-comparison">
            <div class="rate-card daily">
              <div class="rate-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
              </div>
              <span class="rate-label">Daily Rate</span>
              <span class="rate-value">${this._formatCurrency(budget.daily_rate_equivalent || 0)}</span>
              <span class="rate-description">Per day cost</span>
            </div>
            <div class="rate-card weekly">
              <div class="rate-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                  <line x1="16" y1="2" x2="16" y2="6"></line>
                  <line x1="8" y1="2" x2="8" y2="6"></line>
                  <line x1="3" y1="10" x2="21" y2="10"></line>
                  <path d="m9 16 2 2 4-4"></path>
                </svg>
              </div>
              <span class="rate-label">Weekly Rate</span>
              <span class="rate-value">${this._formatCurrency(budget.weekly_rate_equivalent || 0)}</span>
              <span class="rate-description">Per week cost</span>
            </div>
            <div class="rate-card monthly">
              <div class="rate-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M8 2v4"></path>
                  <path d="M16 2v4"></path>
                  <rect width="18" height="18" x="3" y="4" rx="2"></rect>
                  <path d="M3 10h18"></path>
                  <path d="M8 14h.01"></path>
                  <path d="M12 14h.01"></path>
                  <path d="M16 14h.01"></path>
                  <path d="M8 18h.01"></path>
                  <path d="M12 18h.01"></path>
                  <path d="M16 18h.01"></path>
                </svg>
              </div>
              <span class="rate-label">Monthly Rate</span>
              <span class="rate-value">${this._formatCurrency(budget.monthly_rate_equivalent || 0)}</span>
              <span class="rate-description">Per month cost</span>
            </div>
          </div>
          
          ${budget.cost_breakdown ? `
            <div class="cost-breakdown">
              <h5>Cost Breakdown</h5>
              <div class="breakdown-chart">
                ${Object.entries(budget.cost_breakdown).map(([category, amount]) => {
      const percentage = ((amount / budget.subtotal) * 100).toFixed(1);
      return `
                    <div class="breakdown-item">
                      <div class="breakdown-bar">
                        <div class="breakdown-fill" style="width: ${percentage}%"></div>
                      </div>
                      <div class="breakdown-details">
                        <span class="breakdown-category">${category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' ')}</span>
                        <span class="breakdown-amount">${this._formatCurrency(amount)} (${percentage}%)</span>
                      </div>
                    </div>
                  `;
    }).join('')}
              </div>
            </div>
          ` : ''}
          
          <div class="budget-features">
            <div class="feature-item ${budget.is_delivery_free ? 'included' : 'not-included'}">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                ${budget.is_delivery_free ?
        '<polyline points="20 6 9 17 4 12"></polyline>' :
        '<line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line>'
      }
              </svg>
              <span>Free Delivery ${budget.is_delivery_free ? 'Included' : 'Not Included'}</span>
            </div>
            ${budget.discounts_applied ? `
              <div class="feature-item discount">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M8 12h8"></path>
                </svg>
                <span>Discount Applied: ${budget.discounts_applied}</span>
              </div>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  }

  _renderMetadata(responseData, metadata) {
    if (!metadata) return '';

    return /* html */ `
      <div class="detail-section">
        <h4>System Information</h4>
        <div class="metadata-details">
          <div class="metadata-grid">
            <div class="metadata-item">
              <span class="metadata-label">Request ID</span>
              <span class="metadata-value request-id">${responseData.request_id || 'N/A'}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Generated At</span>
              <span class="metadata-value">${new Date(metadata.generated_at).toLocaleString() || 'N/A'}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Valid Until</span>
              <span class="metadata-value">${new Date(metadata.valid_until).toLocaleString() || 'N/A'}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Processing Time</span>
              <span class="metadata-value">${metadata.calculation_time_ms || 'N/A'}ms</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">System Version</span>
              <span class="metadata-value">${metadata.version || 'N/A'}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Source System</span>
              <span class="metadata-value">${metadata.source_system || 'N/A'}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Calculation Method</span>
              <span class="metadata-value">${metadata.calculation_method || 'N/A'}</span>
            </div>
            <div class="metadata-item">
              <span class="metadata-label">Cache Status</span>
              <span class="metadata-value cache-${responseData.cached ? 'hit' : 'miss'}">
                ${responseData.cached ? 'Cached' : 'Fresh'}
              </span>
            </div>
          </div>
          
          ${metadata.data_sources ? `
            <div class="data-sources">
              <h5>Data Sources</h5>
              <div class="sources-grid">
                ${Object.entries(metadata.data_sources).map(([source, system]) => `
                  <div class="source-item">
                    <span class="source-label">${source.charAt(0).toUpperCase() + source.slice(1)}</span>
                    <span class="source-value">${system}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
          
          ${metadata.warnings && metadata.warnings.length > 0 ? `
            <div class="warnings-section">
              <h5>Warnings</h5>
              <div class="warnings-list">
                ${metadata.warnings.map(warning => `
                  <div class="warning-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                      <line x1="12" y1="9" x2="12" y2="13"></line>
                      <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    <span>${warning}</span>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }

  _renderPerformanceComparison() {
    if (!this.state.showComparison || !this.state.result || !this.state.secondResult) {
      return /* html */ `
        <div class="no-comparison">
          <div class="loading-comparison">
            <div class="comparison-loading-icon">
              <svg class="spinner" viewBox="0 0 50 50">
                <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
              </svg>
            </div>
            <h3>Preparing Performance Analysis</h3>
            <p>Running second request to demonstrate Redis caching performance...</p>
          </div>
        </div>
      `;
    }

    const firstTime = this.state.result.data?.client_processing_time_ms || 0;
    const secondTime = this.state.secondResult.data?.client_processing_time_ms || 0;
    const averageTime = this._calculateAverageProcessingTime(firstTime, secondTime);
    const improvement = this._calculatePercentageImprovement(firstTime, secondTime);
    const firstScore = this._calculatePerformanceScore(firstTime);
    const secondScore = this._calculatePerformanceScore(secondTime);
    const timeSaved = firstTime - secondTime;

    // Calculate efficiency rating
    const efficiencyRating = improvement < 30 ? 'Good' : improvement < 60 ? 'Great' : 'Excellent';

    return /* html */ `
      <div class="performance-comparison-modern">
        <!-- Hero Section -->
        <div class="comparison-hero">
          <div class="hero-content">
            <h3>🚀 Performance Analysis Dashboard</h3>
            <p class="hero-subtitle">Real-time comparison between fresh request and Redis cached response</p>
            <div class="hero-stats">
              <div class="hero-stat">
                <span class="stat-value">${improvement}%</span>
                <span class="stat-label">Performance Boost</span>
              </div>
              <div class="hero-stat">
                <span class="stat-value">${timeSaved}ms</span>
                <span class="stat-label">Time Saved</span>
              </div>
              <div class="hero-stat">
                <span class="stat-value">${efficiencyRating}</span>
                <span class="stat-label">Cache Rating</span>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Interactive Dashboard -->
        <div class="performance-dashboard">
          <!-- Response Time Metrics -->
          <div class="dashboard-section">
            <h4>⚡ Response Time Metrics</h4>
            <div class="metrics-grid-modern">
              <div class="metric-card-modern fresh">
                <div class="metric-header-modern">
                  <div class="metric-icon-modern">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                    </svg>
                  </div>
                  <span class="metric-badge-modern">Fresh Request</span>
                </div>
                <div class="metric-content-modern">
                  <div class="metric-value-modern" style="color: ${firstScore.color}">${firstTime}ms</div>
                  <div class="metric-score-modern ${firstScore.score.toLowerCase()}">${firstScore.score}</div>
                  <div class="metric-progress-modern">
                    <div class="progress-bar-modern" style="width: 100%; background: ${firstScore.color}"></div>
                  </div>
                </div>
              </div>
              
              <div class="metric-card-modern cached highlight">
                <div class="metric-header-modern">
                  <div class="metric-icon-modern">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                      <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
                      <path d="m9 14 2 2 4-4"></path>
                    </svg>
                  </div>
                  <span class="metric-badge-modern cached">Redis Cached</span>
                </div>
                <div class="metric-content-modern">
                  <div class="metric-value-modern comparison-highlight" style="color: ${secondScore.color}">${secondTime}ms</div>
                  <div class="metric-score-modern ${secondScore.score.toLowerCase()}">${secondScore.score}</div>
                  <div class="metric-progress-modern">
                    <div class="progress-bar-modern" style="width: ${(secondTime / firstTime) * 100}%; background: ${secondScore.color}"></div>
                  </div>
                </div>
              </div>
              
              <div class="metric-card-modern average">
                <div class="metric-header-modern">
                  <div class="metric-icon-modern">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                    </svg>
                  </div>
                  <span class="metric-badge-modern">Average Response</span>
                </div>
                <div class="metric-content-modern">
                  <div class="metric-value-modern" style="color: var(--accent-color)">${averageTime}ms</div>
                  <div class="metric-score-modern">Combined Average</div>
                  <div class="metric-progress-modern">
                    <div class="progress-bar-modern" style="width: ${(averageTime / firstTime) * 100}%; background: var(--accent-color)"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Interactive Performance Chart -->
          <div class="dashboard-section">
            <h4>📊 Interactive Performance Visualization</h4>
            <div class="chart-container-modern">
              ${this._createInteractiveChart(firstTime, secondTime, improvement)}
            </div>
          </div>
          
          <!-- Advanced Performance Insights -->
          <div class="dashboard-section">
            <h4>🔍 Performance Intelligence & Insights</h4>
            <div class="insights-grid-modern">
              <div class="insight-card-modern cache-efficiency">
                <div class="insight-header-modern">
                  <div class="insight-icon-modern">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"></path>
                    </svg>
                  </div>
                  <div class="insight-title-modern">Cache Efficiency</div>
                </div>
                <div class="insight-content-modern">
                  <div class="insight-value-modern">${improvement}%</div>
                  <div class="insight-description-modern">Response time improvement through Redis caching. ${improvement > 50 ? 'Exceptional performance boost!' : improvement > 30 ? 'Good optimization achieved.' : 'Moderate improvement detected.'}</div>
                </div>
              </div>
              
              <div class="insight-card-modern performance-boost">
                <div class="insight-header-modern">
                  <div class="insight-icon-modern">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                    </svg>
                  </div>
                  <div class="insight-title-modern">Time Optimization</div>
                </div>
                <div class="insight-content-modern">
                  <div class="insight-value-modern">${timeSaved}ms</div>
                  <div class="insight-description-modern">Milliseconds saved per cached request. At scale, this translates to significant performance gains.</div>
                </div>
              </div>
              
              <div class="insight-card-modern cache-score">
                <div class="insight-header-modern">
                  <div class="insight-icon-modern">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <path d="m9 12 2 2 4-4"></path>
                    </svg>
                  </div>
                  <div class="insight-title-modern">Overall Rating</div>
                </div>
                <div class="insight-content-modern">
                  <div class="insight-value-modern">${efficiencyRating}</div>
                  <div class="insight-description-modern">Overall caching performance score based on response time reduction.</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  getTemplate() {
    return /* html */ `
      <div class="overlay"></div>
      <section class="content">
        <div class="modal-header">
          <h2>Quote Results</h2>
          <button class="close-button">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          ${this._renderContent()}
        </div>
      </section>
      ${this.getStyles()}
    `;
  }

  getStyles() {
    return /* html */ `
      <style>
        :host {
          display: block;
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          z-index: 9999;
          font-family: var(--font-main), sans-serif;
          color: var(--text-color);
        }

        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        .overlay {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: var(--modal-overlay);
          cursor: pointer;
        }

        .content {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          background: var(--background);
          border-radius: 1rem;
          box-shadow: var(--modal-shadow);
          width: 95vw;
          max-width: 1400px;
          height: 90vh;
          max-height: 1000px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.5rem 0;
          border-bottom: var(--border);
          background: var(--background);
          position: sticky;
          top: 0;
          z-index: 10;
        }

        .modal-header h2 {
          font-size: 1.5rem;
          font-weight: 700;
          padding: 0 1.5rem;
          color: var(--title-color);
          margin: 0;
        }

        .close-button {
          background: none;
          border: none;
          color: var(--gray-color);
          cursor: pointer;
          padding: 0.5rem;
          border-radius: 0.5rem;
          transition: all 0.2s ease;
          margin-right: 1.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .close-button:hover {
          background: var(--hover-background);
          color: var(--text-color);
        }

        .modal-body {
          flex: 1;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        /* Content Body Container */
        .content-body-container {
          flex: 1;
          display: flex;
          flex-direction: column;
          height: 100%;
          overflow: hidden;
          background: var(--background);
        }

        .tab-content-container {
          flex: 1;
          overflow-y: auto;
          padding: 0 1.5rem;
          display: flex;
          flex-direction: column;
          background: var(--background);
        }

        /* Ensure tab content has proper spacing */
        .modern-tab-content {
          flex: 1;
          opacity: 0;
          transform: translateY(20px);
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          display: none;
          padding: 1rem 0;
        }

        .modern-tab-content.active {
          display: block;
          opacity: 1;
          transform: translateY(0);
        }

        .modern-tab-content.slide-in {
          animation: slideInContent 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
        }

        @keyframes slideInContent {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Loading States */
        .loading-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          padding: 2rem;
        }

        .spinner {
          width: 3rem;
          height: 3rem;
          margin-bottom: 1rem;
        }

        .path {
          stroke: var(--accent-color);
          stroke-linecap: round;
          animation: dash 1.5s ease-in-out infinite;
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
          font-size: 1rem;
          color: var(--title-color);
          text-align: center;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        .loading-subtitle {
          font-size: 0.875rem;
          color: var(--gray-color);
          text-align: center;
          margin-bottom: 1rem;
          line-height: 1.4;
        }

        .loading-details {
          text-align: center;
          margin-top: 1rem;
        }

        .loading-details small {
          font-size: 0.8rem;
          color: var(--gray-color);
          opacity: 0.7;
          background: var(--stat-background);
          padding: 0.5rem 1rem;
          border-radius: 1rem;
          border: var(--border);
        }

        /* Error States */
        .error-container, .no-results {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          padding: 2rem;
          text-align: center;
          color: var(--error-color);
        }

        .error-container svg {
          margin-bottom: 1rem;
        }

        /* Modern Tab Navigation */
        .modern-tabs-wrapper {
          position: sticky;
          top: 0;
          z-index: 10;
          background: var(--background);
          border-bottom: var(--border);
          padding: 0 2rem;
        }

        .modern-tabs-container {
          display: flex;
          position: relative;
          gap: 0.5rem;
          background: var(--stat-background);
          border-radius: 1rem;
          padding: 0.5rem;
          margin: 1rem 0;
        }

        .tab-slider {
          position: absolute;
          top: 0.5rem;
          bottom: 0.5rem;
          background: linear-gradient(135deg, var(--accent-color), var(--alt-color));
          border-radius: 0.75rem;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          z-index: 1;
        }

        .modern-tab {
          position: relative;
          z-index: 2;
          flex: 1;
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem 1.5rem;
          cursor: pointer;
          border-radius: 0.75rem;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          background: transparent;
          color: var(--gray-color);
          min-height: 4rem;
        }

        .modern-tab:hover:not(.disabled) {
          color: var(--text-color);
          transform: translateY(-1px);
        }

        .modern-tab.active {
          color: white;
          text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
        }

        .modern-tab.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .modern-tab.disabled:hover {
          transform: none;
        }

        .tab-icon {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 0.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--hover-background);
          transition: all 0.3s ease;
          flex-shrink: 0;
        }

        .modern-tab.active .tab-icon {
          background: rgba(255, 255, 255, 0.2);
          backdrop-filter: blur(10px);
        }

        .modern-tab.disabled .tab-icon {
          opacity: 0.6;
        }

        .tab-content-wrapper {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          flex: 1;
          min-width: 0;
        }

        .tab-title {
          font-weight: 700;
          font-size: 1rem;
          line-height: 1.2;
          transition: all 0.3s ease;
        }

        .tab-subtitle {
          font-size: 0.8rem;
          opacity: 0.8;
          line-height: 1.3;
          transition: all 0.3s ease;
        }

        .modern-tab.active .tab-subtitle {
          opacity: 0.9;
        }

        .tab-status-indicator {
          display: flex;
          align-items: center;
          justify-content: center;
          margin-left: auto;
        }

        .status-dot {
          width: 0.5rem;
          height: 0.5rem;
          border-radius: 50%;
          background: var(--success-color);
          animation: status-pulse 2s infinite;
        }

        .status-dot.active {
          box-shadow: 0 0 0 0 var(--success-color);
        }

        @keyframes status-pulse {
          0% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
          }
          
          70% {
            transform: scale(1);
            box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
          }
          
          100% {
            transform: scale(0.95);
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
          }
        }

        /* Legacy tab support for backward compatibility */
        .tabs-container {
          display: none;
          border-bottom: var(--border);
          background: var(--stat-background);
          padding: 0 2rem;
          position: sticky;
          top: 0;
          z-index: 5;
        }

        .tab {
          padding: 1rem 1.5rem;
          cursor: pointer;
          border-bottom: 3px solid transparent;
          color: var(--gray-color);
          font-weight: 600;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          position: relative;
          font-size: 0.9rem;
        }

        .tab:hover:not(.disabled) {
          color: var(--text-color);
          background: var(--hover-background);
        }

        .tab.active {
          color: var(--accent-color);
          border-bottom-color: var(--accent-color);
          background: var(--background);
        }

        .tab.disabled {
          color: var(--gray-color);
          cursor: not-allowed;
          opacity: 0.5;
        }

        .tab-indicator {
          display: inline-block;
          width: 0.5rem;
          height: 0.5rem;
          background: var(--accent-color);
          border-radius: 50%;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .tab-content {
          display: none;
          flex: 1;
          overflow-y: auto;
          padding: 2rem;
        }

        .tab-content.active {
          display: block;
        }

        /* Quote Result Layout */
        .quote-result {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        /* Quote Header */
        .quote-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 2rem;
          padding: 2rem;
          background: var(--stat-background);
          border-radius: 1rem;
          border: var(--border);
        }

        .quote-title-section {
          flex: 1;
        }

        .quote-id-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: var(--accent-color);
          color: white;
          padding: 0.5rem 1rem;
          border-radius: 2rem;
          font-size: 0.875rem;
          font-weight: 600;
          margin-bottom: 1rem;
        }

        .product-title {
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.5rem;
          line-height: 1.2;
        }

        .quote-subtitle {
          color: var(--gray-color);
          font-size: 1rem;
          line-height: 1.5;
        }

        .delivery-tier-info {
          margin-top: 1rem;
          padding: 0.75rem 1rem;
          background: var(--label-focus-background);
          border-radius: 0.5rem;
          border-left: 4px solid var(--accent-color);
        }

        .tier-label {
          font-size: 0.875rem;
          color: var(--gray-color);
          font-weight: 500;
        }

        .tier-value {
          font-size: 0.875rem;
          color: var(--text-color);
          font-weight: 600;
          margin-left: 0.5rem;
        }

        .quote-actions {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 1rem;
        }

        .quote-total {
          text-align: right;
        }

        .total-label {
          display: block;
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-bottom: 0.25rem;
        }

        .total-amount {
          font-size: 2rem;
          font-weight: 700;
          color: var(--accent-color);
        }

        .subtotal-note {
          display: block;
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-top: 0.25rem;
          font-weight: 500;
        }

        .copy-result {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.5rem;
          background: var(--action-linear);
          border: none;
          border-radius: 0.5rem;
          color: white;
          font-size: 0.875rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .copy-result:hover {
          background: var(--accent-linear);
          transform: translateY(-1px);
          box-shadow: var(--card-box-shadow);
        }

        /* Pricing Overview */
        .pricing-overview {
          margin-bottom: 1rem;
        }

        .overview-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .overview-card {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1.5rem;
          background: var(--background);
          border: var(--border);
          border-radius: 0.75rem;
          transition: all 0.2s ease;
        }

        .overview-card:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
        }

        .overview-card.primary {
          background: var(--label-focus-background);
          border-color: var(--accent-color);
        }

        .card-icon {
          width: 3rem;
          height: 3rem;
          border-radius: 0.75rem;
          background: var(--accent-color);
          color: white;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .card-content {
          flex: 1;
        }

        .card-label {
          display: block;
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-bottom: 0.25rem;
        }

        .card-value {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--title-color);
        }

        /* Detail Sections */
        .detail-section {
          background: var(--background);
          overflow: hidden;
        }

        .detail-section h4 {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          padding: 1.5rem 0;
          border-bottom: var(--border);
          margin: 0;
        }

        .detail-section h5 {
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 1rem;
        }

        /* Line Items Table */
        .line-items-table {
          padding: 1.5rem 0;
        }

        .table-header {
          display: grid;
          grid-template-columns: 2fr 1fr 80px 1fr;
          gap: 1rem;
          padding: 0.75rem 0;
          border-bottom: 2px solid var(--border);
          font-weight: 600;
          color: var(--title-color);
          font-size: 0.875rem;
        }

        .table-row {
          display: grid;
          grid-template-columns: 2fr 1fr 80px 1fr;
          gap: 1rem;
          padding: 1rem 0;
          border-bottom: var(--border);
          align-items: center;
        }

        .table-row:last-child {
          border-bottom: none;
        }

        .item-description {
          font-size: 0.9rem;
          color: var(--text-color);
          line-height: 1.4;
        }

        .item-unit-price, .item-total {
          font-weight: 600;
          color: var(--title-color);
        }

        .item-quantity {
          text-align: center;
          font-weight: 500;
          color: var(--text-color);
        }

        .table-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem 0;
          margin-top: 1rem;
          border-top: 2px solid var(--accent-color);
          font-weight: 700;
          font-size: 1.125rem;
        }

        .footer-label {
          color: var(--title-color);
        }

        .footer-total {
          color: var(--accent-color);
        }

        .quote-notes {
          margin-top: 1.5rem;
          padding: 1rem;
          background: var(--stat-background);
          border-radius: 0.5rem;
          color: var(--text-color);
          font-size: 0.875rem;
          line-height: 1.5;
        }

        .empty-state {
          padding: 2rem;
          text-align: center;
          color: var(--gray-color);
          font-style: italic;
        }

        /* Product Details */
        .product-details {
          padding: 1.5rem 0;
        }

        .spec-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
        }

        .spec-item {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 1.25rem;
          background: var(--stat-background);
          border: none;
          border-radius: 0.75rem;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .spec-item:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
          background: var(--label-focus-background);
        }

        .spec-item::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 3px;
          background: var(--accent-color);
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .spec-item:hover::before {
          opacity: 1;
        }

        .spec-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 0.25rem;
        }

        .spec-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--title-color);
          line-height: 1.2;
        }

        .spec-value.compliant {
          color: var(--success-color);
        }

        .spec-value.not-compliant {
          color: var(--error-color);
        }

        .product-features {
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: var(--border);
        }

        .features-label {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 0.75rem;
          display: block;
        }

        .features-list {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .feature-tag {
          padding: 0.375rem 0.75rem;
          background: var(--stat-background);
          border: var(--border);
          border-radius: 1rem;
          font-size: 0.875rem;
          color: var(--text-color);
        }

        /* Rental Details */
        .rental-details {
          padding: 1.5rem 0;
        }

        .rental-period {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .period-item {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 2rem 1.5rem;
          background: linear-gradient(135deg, var(--stat-background) 0%, var(--label-focus-background) 100%);
          border-radius: 1rem;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          transition: all 0.3s ease;
          overflow: hidden;
        }

        .period-item::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: var(--accent-color);
          transition: all 0.3s ease;
        }

        .period-item:hover {
          transform: translateY(-8px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }

        .period-item:hover::before {
          height: 6px;
          background: linear-gradient(90deg, var(--accent-color), var(--success-color));
        }

        .period-item.start-date::before {
          background: linear-gradient(90deg, #16A34A, #15803D);
        }

        .period-item.end-date::before {
          background: linear-gradient(90deg, #DC2626, #B91C1C);
        }

        .period-item.duration::before {
          background: linear-gradient(90deg, #2563EB, #1D4ED8);
        }

        .period-icon {
          width: 3rem;
          height: 3rem;
          margin-bottom: 1rem;
          padding: 0.75rem;
          background: var(--accent-color);
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }

        .period-item.start-date .period-icon {
          background: linear-gradient(135deg, #16A34A, #15803D);
        }

        .period-item.end-date .period-icon {
          background: linear-gradient(135deg, #DC2626, #B91C1C);
        }

        .period-item.duration .period-icon {
          background: linear-gradient(135deg, #2563EB, #1D4ED8);
        }

        .period-item:hover .period-icon {
          transform: scale(1.1);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .period-label {
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--gray-color);
          margin-bottom: 0.5rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .period-value {
          font-size: 1.5rem;
          font-weight: 800;
          color: var(--title-color);
          margin-bottom: 0.25rem;
          line-height: 1.1;
        }

        .period-description {
          font-size: 0.75rem;
          color: var(--gray-color);
          opacity: 0.8;
          font-weight: 500;
        }

        .rental-specs {
          margin-top: 1rem;
        }

        /* Delivery Details */
        .delivery-details {
          padding: 1.5rem 0;
        }

        .delivery-summary {
          margin-bottom: 2rem;
        }

        .summary-card {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1.5rem;
          background: var(--stat-background);
          border-radius: 0.75rem;
          border: var(--border);
        }

        .summary-icon {
          width: 3rem;
          height: 3rem;
          background: var(--accent-color);
          color: white;
          border-radius: 0.75rem;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .summary-content {
          flex: 1;
        }

        .summary-label {
          display: block;
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-bottom: 0.25rem;
        }

        .summary-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--title-color);
        }

        .delivery-breakdown {
          margin-top: 1.5rem;
        }

        .breakdown-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
        }

        .breakdown-item {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 1.25rem;
          background: var(--stat-background);
          border: none;
          border-radius: 0.75rem;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .breakdown-item:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
          background: var(--label-focus-background);
        }

        .breakdown-item::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 3px;
          background: var(--accent-color);
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .breakdown-item:hover::before {
          opacity: 1;
        }

        .breakdown-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 0.25rem;
        }

        .breakdown-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--title-color);
          line-height: 1.2;
        }

        .breakdown-value.estimated {
          color: var(--alt-color);
        }

        .breakdown-value.exact {
          color: var(--success-color);
        }

        .delivery-note {
          margin-top: 1.5rem;
          padding: 1rem;
          background: var(--label-focus-background);
          border-radius: 0.5rem;
          border-left: 4px solid var(--accent-color);
          color: var(--text-color);
          font-size: 0.875rem;
        }

        /* Location Details */
        .location-details {
          padding: 1.5rem 0;
        }

        .location-summary {
          margin-bottom: 2rem;
        }

        .address-card {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          padding: 1.5rem;
          background: var(--stat-background);
          border-radius: 0.75rem;
          border: var(--border);
        }

        .address-icon {
          width: 2.5rem;
          height: 2.5rem;
          background: var(--accent-color);
          color: white;
          border-radius: 0.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .address-content {
          flex: 1;
        }

        .address-label {
          display: block;
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-bottom: 0.5rem;
        }

        .address-value {
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
          line-height: 1.4;
        }

        .service-info {
          margin-top: 1.5rem;
        }

        .service-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
          gap: 1rem;
        }

        .service-item {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 1.25rem;
          background: var(--stat-background);
          border: none;
          border-radius: 0.75rem;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .service-item:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
          background: var(--label-focus-background);
        }

        .service-item::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 3px;
          background: var(--accent-color);
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .service-item:hover::before {
          opacity: 1;
        }

        .service-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 0.25rem;
        }

        .service-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--title-color);
          line-height: 1.2;
        }

        .service-value.service-remote {
          color: var(--error-color);
        }

        .service-value.service-standard {
          color: var(--success-color);
        }

        .service-value.service-local {
          color: var(--accent-color);
        }

        .service-value.branch-address {
          font-size: 0.95rem;
          font-weight: 500;
          line-height: 1.4;
        }

        .coordinates {
          font-family: var(--font-mono);
          font-size: 0.875rem;
        }

        /* Budget Analysis */
        .budget-analysis {
          padding: 1.5rem 0;
        }

        .rate-comparison {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .rate-card {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 2rem 1.5rem;
          background: linear-gradient(135deg, var(--stat-background) 0%, var(--label-focus-background) 100%);
          border-radius: 1rem;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
          transition: all 0.3s ease;
          overflow: hidden;
        }

        .rate-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: var(--accent-color);
          transition: all 0.3s ease;
        }

        .rate-card:hover {
          transform: translateY(-8px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }

        .rate-card:hover::before {
          height: 6px;
          background: linear-gradient(90deg, var(--accent-color), var(--success-color));
        }

        .rate-card.daily::before {
          background: linear-gradient(90deg, #3B82F6, #1D4ED8);
        }

        .rate-card.weekly::before {
          background: linear-gradient(90deg, #10B981, #059669);
        }

        .rate-card.monthly::before {
          background: linear-gradient(90deg, #8B5CF6, #7C3AED);
        }

        .rate-icon {
          width: 3rem;
          height: 3rem;
          margin-bottom: 1rem;
          padding: 0.75rem;
          background: var(--accent-color);
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }

        .rate-card.daily .rate-icon {
          background: linear-gradient(135deg, #3B82F6, #1D4ED8);
        }

        .rate-card.weekly .rate-icon {
          background: linear-gradient(135deg, #10B981, #059669);
        }

        .rate-card.monthly .rate-icon {
          background: linear-gradient(135deg, #8B5CF6, #7C3AED);
        }

        .rate-card:hover .rate-icon {
          transform: scale(1.1);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .rate-label {
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--gray-color);
          margin-bottom: 0.5rem;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .rate-value {
          font-size: 1.75rem;
          font-weight: 800;
          color: var(--title-color);
          margin-bottom: 0.25rem;
          line-height: 1.1;
        }

        .rate-description {
          font-size: 0.75rem;
          color: var(--gray-color);
          opacity: 0.8;
          font-weight: 500;
        }

        .cost-breakdown {
          margin-bottom: 2rem;
        }

        .breakdown-chart {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .breakdown-item {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .breakdown-bar {
          width: 100%;
          height: 0.75rem;
          background: var(--hover-background);
          border-radius: 0.25rem;
          overflow: hidden;
        }

        .breakdown-fill {
          height: 100%;
          background: var(--accent-color);
          transition: width 0.8s ease;
          border-radius: 0.25rem;
        }

        .breakdown-details {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .breakdown-category {
          font-weight: 600;
          color: var(--title-color);
        }

        .breakdown-amount {
          font-weight: 500;
          color: var(--text-color);
        }

        .budget-features {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .feature-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          border-radius: 0.5rem;
          background: var(--hover-background);
        }

        .feature-item.included {
          background: var(--label-focus-background);
          color: var(--success-color);
        }

        .feature-item.not-included {
          background: var(--error-background);
          color: var(--error-color);
        }

        .feature-item.discount {
          background: var(--stat-background);
          color: var(--alt-color);
        }

        /* Metadata */
        .metadata-details {
          padding: 1.5rem 0;
        }

        .metadata-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 1rem;
          margin-bottom: 2rem;
        }

        .metadata-item {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          padding: 1.25rem;
          background: var(--stat-background);
          border: none;
          border-radius: 0.75rem;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .metadata-item:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
          background: var(--label-focus-background);
        }

        .metadata-item::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 3px;
          background: var(--accent-color);
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .metadata-item:hover::before {
          opacity: 1;
        }

        .metadata-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 0.25rem;
        }

        .metadata-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--title-color);
          line-height: 1.2;
        }

        .metadata-value.request-id {
          font-family: var(--font-mono);
          font-size: 0.875rem;
        }

        .metadata-value.cache-hit {
          color: var(--success-color);
        }

        .metadata-value.cache-miss {
          color: var(--accent-color);
        }

        .data-sources {
          margin-bottom: 2rem;
        }

        .sources-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .source-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem;
          background: var(--stat-background);
          border-radius: 0.5rem;
          border: var(--border);
        }

        .source-label {
          font-weight: 600;
          color: var(--title-color);
        }

        .source-value {
          color: var(--text-color);
          font-size: 0.875rem;
        }

        .warnings-section {
          margin-top: 2rem;
        }

        .warnings-list {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .warning-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem;
          background: var(--error-background);
          color: var(--error-color);
          border-radius: 0.5rem;
          border-left: 4px solid var(--error-color);
        }

        /* Performance Comparison (existing styles maintained) */
        .performance-comparison {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .comparison-header {
          text-align: center;
        }

        .comparison-header h3 {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.5rem;
        }

        .comparison-subtitle {
          color: var(--gray-color);
          font-size: 0.875rem;
        }

        .performance-metrics {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
        }

        .metric-card {
          text-align: center;
          padding: 1.5rem;
          border: var(--border);
          border-radius: 0.75rem;
          background: var(--background);
        }

        .metric-card.cached {
          background: var(--stat-background);
        }

        .metric-card.improvement {
          background: var(--label-focus-background);
        }

        .metric-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--gray-color);
          margin-bottom: 0.5rem;
        }

        .metric-value {
          font-size: 2rem;
          font-weight: 700;
          margin-bottom: 0.25rem;
        }

        .metric-score {
          font-size: 0.875rem;
          color: var(--gray-color);
        }

        .comparison-chart {
          border: var(--border);
          border-radius: 0.75rem;
          padding: 1.5rem;
        }

        .comparison-chart h4 {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 1.5rem;
          text-align: center;
        }

        .comparison-bars {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .comparison-bar-container {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .comparison-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-color);
        }

        .comparison-bar-wrapper {
          background: var(--hover-background);
          border-radius: 0.375rem;
          overflow: hidden;
          height: 2.5rem;
          position: relative;
        }

        .comparison-bar {
          height: 100%;
          border-radius: 0.375rem;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 600;
          font-size: 0.875rem;
          transition: width 0.8s ease;
          position: relative;
        }

        .comparison-highlight {
          animation: highlight-pulse 2s infinite;
        }

        @keyframes highlight-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.8; }
        }

        .highlight-animation {
          animation: highlight-flash 1s ease-in-out;
        }

        @keyframes highlight-flash {
          0%, 100% { background-color: var(--success-color); }
          50% { background-color: var(--accent-color); }
        }

        .performance-insights {
          border: var(--border);
          border-radius: 0.75rem;
          padding: 1.5rem;
        }

        .performance-insights h4 {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 1.5rem;
          text-align: center;
        }

        .insight-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1rem;
        }

        .insight-card {
          display: flex;
          align-items: center;
          gap: 1rem;
          padding: 1rem;
          border: var(--border);
          border-radius: 0.5rem;
          background: var(--hover-background);
        }

        .insight-icon {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          flex-shrink: 0;
        }

        .insight-content {
          flex: 1;
        }

        .insight-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 0.25rem;
        }

        .insight-description {
          font-size: 0.8rem;
          color: var(--gray-color);
        }

        .no-comparison {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          text-align: center;
          color: var(--gray-color);
        }

        /* Mobile Responsiveness */
        @media (max-width: 768px) {
          .content {
            width: 98vw;
            height: 95vh;
            border-radius: 0.75rem;
          }

          .modal-header {
            padding: 1rem 1.5rem;
          }

          .modal-header h2 {
            font-size: 1.25rem;
          }

          .modern-tabs-wrapper {
            padding: 0 1rem;
          }

          .modern-tabs-container {
            flex-direction: column;
            gap: 0.5rem;
            margin: 0.5rem 0;
          }

          .tab-slider {
            display: none;
          }

          .modern-tab {
            background: var(--stat-background);
            border: var(--border);
            border-radius: 0.75rem;
            margin-bottom: 0.5rem;
            min-height: 3rem;
            padding: 0.75rem 1rem;
          }

          .modern-tab.active {
            background: linear-gradient(135deg, var(--accent-color), var(--alt-color));
            color: white;
          }

          .tab-content-wrapper {
            gap: 0.1rem;
          }

          .tab-title {
            font-size: 0.9rem;
          }

          .tab-subtitle {
            font-size: 0.75rem;
          }

          .tab-content {
            padding: 1rem;
          }

          .quote-header {
            flex-direction: column;
            gap: 1rem;
          }

          .quote-actions {
            align-items: stretch;
          }

          .overview-cards {
            grid-template-columns: repeat(2, 1fr);
          }

          .table-header, .table-row {
            grid-template-columns: 1fr;
            gap: 0.5rem;
          }

          .table-header {
            display: none;
          }

          .table-row {
            display: flex;
            flex-direction: column;
            padding: 1rem;
            background: var(--stat-background);
            border-radius: 0.5rem;
            margin-bottom: 1rem;
          }

          .item-description {
            font-weight: 600;
            margin-bottom: 0.5rem;
          }

          .item-unit-price:before { content: "Unit Price: "; color: var(--gray-color); }
          .item-quantity:before { content: "Quantity: "; color: var(--gray-color); }
          .item-total:before { content: "Total: "; color: var(--gray-color); }

          .spec-grid, .breakdown-grid, .service-grid, .metadata-grid {
            grid-template-columns: 1fr;
          }

          .rental-period {
            grid-template-columns: repeat(2, 1fr);
          }

          .rate-comparison {
            grid-template-columns: 1fr;
          }

          .performance-metrics {
            grid-template-columns: repeat(2, 1fr);
          }

          .insight-grid {
            grid-template-columns: 1fr;
          }

          .tabs-container {
            padding: 0 1rem;
          }

          .tab {
            padding: 0.75rem 1rem;
            font-size: 0.875rem;
          }
        }

        @media (max-width: 480px) {
          .overview-cards {
            grid-template-columns: 1fr;
          }

          .performance-metrics {
            grid-template-columns: 1fr;
          }

          .rental-period {
            grid-template-columns: 1fr;
          }

          .product-title {
            font-size: 1.5rem;
          }

          .total-amount {
            font-size: 1.5rem;
          }
        }

        /* Scrollbar Styling */
        ::-webkit-scrollbar {
          width: 3px;
        }

        ::-webkit-scrollbar-track {
          background: var(--scroll-bar-background);
          border-radius: 3px;
        }

        ::-webkit-scrollbar-thumb,
        ::-webkit-scrollbar-thumb {
          background: var(--scroll-bar-linear);
          border-radius: 3px;
        }

        /* Utility Classes */
        .stop-scrolling {
          height: 100%;
          overflow: hidden;
        }

        /* Modern Performance Comparison Styles */
        .performance-comparison-modern {
          display: flex;
          flex-direction: column;
          gap: 2rem;
          padding: 1rem;
        }

        .comparison-hero {
          background: linear-gradient(135deg, var(--stat-background), var(--background));
          border-radius: 1rem;
          padding: 2rem;
          text-align: center;
          border: var(--border);
        }

        .hero-content h3 {
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.5rem;
        }

        .hero-subtitle {
          color: var(--gray-color);
          margin-bottom: 2rem;
          font-size: 1rem;
        }

        .hero-stats {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 1.5rem;
        }

        .hero-stat {
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .stat-value {
          font-size: 2.5rem;
          font-weight: 800;
          color: var(--accent-color);
          margin-bottom: 0.25rem;
        }

        .stat-label {
          font-size: 0.875rem;
          color: var(--gray-color);
          font-weight: 500;
        }

        .performance-dashboard {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .dashboard-section {
          background: var(--background);
          padding: 1.5rem 0;
        }

        .dashboard-section h4 {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 1.5rem;
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .metrics-grid-modern {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1.5rem;
        }

        .metric-card-modern {
          background: var(--stat-background);
          border-radius: 0.75rem;
          padding: 1.5rem;
          border: var(--border);
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
        }

        .metric-card-modern:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }

        .metric-card-modern.highlight {
          border-color: var(--success-color);
          box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        }

        .metric-header-modern {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 1rem;
        }

        .metric-icon-modern {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--accent-color), var(--alt-color));
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }

        .metric-badge-modern {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .metric-badge-modern.cached {
          color: var(--success-color);
        }

        .metric-content-modern {
          text-align: center;
        }

        .metric-value-modern {
          font-size: 2.25rem;
          font-weight: 800;
          margin-bottom: 0.5rem;
          color: var(--title-color);
        }

        .metric-score-modern {
          font-size: 0.875rem;
          color: var(--gray-color);
          margin-bottom: 1rem;
        }

        .metric-progress-modern {
          height: 4px;
          background: var(--hover-background);
          border-radius: 2px;
          overflow: hidden;
        }

        .progress-bar-modern {
          height: 100%;
          border-radius: 2px;
          transition: width 1s ease;
          position: relative;
        }

        .chart-container-modern {
          background: var(--stat-background);
          border-radius: 0.75rem;
          padding: 1.5rem;
          border: var(--border);
        }

        .interactive-chart-modern {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .chart-header-modern {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .chart-legend-modern {
          display: flex;
          gap: 1.5rem;
        }

        .legend-item-modern {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .legend-color-modern {
          width: 1rem;
          height: 1rem;
          border-radius: 50%;
        }

        .legend-color-modern.fresh {
          background: var(--accent-color);
        }

        .legend-color-modern.cached {
          background: var(--success-color);
        }

        .improvement-badge-modern {
          background: linear-gradient(135deg, var(--success-color), #059669);
          color: white;
          padding: 0.5rem 1rem;
          border-radius: 2rem;
          font-weight: 600;
          font-size: 0.875rem;
        }

        .chart-bars-modern {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .chart-bar-group-modern {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .bar-label-modern {
          font-weight: 600;
          color: var(--title-color);
          font-size: 0.875rem;
        }

        .bar-container-modern {
          background: var(--hover-background);
          border-radius: 0.5rem;
          height: 3rem;
          position: relative;
          overflow: hidden;
        }

        .bar-modern {
          height: 100%;
          border-radius: 0.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 700;
          transition: width 1.2s cubic-bezier(0.4, 0, 0.2, 1);
          position: relative;
        }

        .fresh-bar {
          background: linear-gradient(135deg, var(--accent-color), var(--alt-color));
        }

        .cached-bar {
          background: linear-gradient(135deg, var(--success-color), #059669);
        }

        .bar-value-modern {
          font-weight: 700;
          text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
        }

        .chart-footer-modern {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 1rem;
          padding-top: 1rem;
          border-top: var(--border);
        }

        .time-saved-modern,
        .efficiency-rating-modern {
          text-align: center;
        }

        .metric-highlight-modern {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--accent-color);
          margin-bottom: 0.25rem;
        }

        .metric-label-modern {
          font-size: 0.875rem;
          color: var(--gray-color);
          font-weight: 500;
        }

        .insights-grid-modern {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .insight-card-modern {
          background: var(--stat-background);
          border-radius: 0.75rem;
          padding: 1.5rem;
          border: var(--border);
          transition: all 0.3s ease;
        }

        .insight-card-modern:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }

        .insight-header-modern {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .insight-icon-modern {
          width: 2.5rem;
          height: 2.5rem;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          background: linear-gradient(135deg, var(--accent-color), var(--alt-color));
        }

        .insight-card-modern.cache-efficiency .insight-icon-modern {
          background: linear-gradient(135deg, #f59e0b, #d97706);
        }

        .insight-card-modern.performance-boost .insight-icon-modern {
          background: linear-gradient(135deg, var(--success-color), #059669);
        }

        .insight-card-modern.cache-score .insight-icon-modern {
          background: linear-gradient(135deg, var(--accent-color), #6366f1);
        }

        .insight-title-modern {
          font-weight: 700;
          color: var(--title-color);
          font-size: 1rem;
        }

        .insight-content-modern {
          margin-bottom: 1rem;
        }

        .insight-value-modern {
          font-size: 1.75rem;
          font-weight: 800;
          color: var(--accent-color);
          margin-bottom: 0.5rem;
        }

        .insight-description-modern {
          color: var(--gray-color);
          font-size: 0.875rem;
          line-height: 1.5;
        }

        .loading-comparison {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 3rem;
          text-align: center;
        }

        .comparison-loading-icon {
          margin-bottom: 1.5rem;
        }

        .loading-comparison h3 {
          color: var(--title-color);
          margin-bottom: 0.5rem;
          font-size: 1.25rem;
          font-weight: 600;
        }

        .loading-comparison p {
          color: var(--gray-color);
          font-size: 0.875rem;
        }
      </style>
    `;
  }
}
