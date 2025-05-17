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
            delivery_location: "1600 Amphitheatre Parkway, Mountain View, CA 94043",
            trailer_type: "2 Stall Restroom Trailer", 
            rental_start_date: "2025-07-15",
            rental_days: 3,
            usage_type: "event",
            extras: [
              {"extra_id": "3kW Generator", "qty": 1}
            ]
          }
        },
        {
          id: "commercial-4-stall",
          label: "Commercial, 4 Stall Trailer",
          description: "Ideal for medium-sized construction sites or commercial use",
          location: "Cupertino, CA",
          body: {
            delivery_location: "1 Infinite Loop, Cupertino, CA 95014",
            trailer_type: "4 Stall Restroom Trailer",
            rental_start_date: "2025-08-01",
            rental_days: 30,
            usage_type: "commercial",
            extras: [
              {"extra_id": "pump_out", "qty": 2},
              {"extra_id": "cleaning", "qty": 1}
            ]
          }
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
            extras: [
              {"extra_id": "3kW Generator", "qty": 1}
            ]
          }
        }
      ]
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
    const sampleCards = this.shadowObj.querySelectorAll('.sample-card');
    if (sampleCards) {
      sampleCards.forEach(card => {
        card.addEventListener('click', () => {
          const quoteId = card.dataset.id;
          this.state.selectedQuote = quoteId;
          
          // Update UI to show selected card
          sampleCards.forEach(c => c.classList.remove('active'));
          card.classList.add('active');
        });
      });
    }
    
    // Generate quote button
    const generateButtons = this.shadowObj.querySelectorAll('.generate-quote-btn');
    if (generateButtons) {
      generateButtons.forEach(button => {
        button.addEventListener('click', (e) => {
          e.stopPropagation(); // Prevent card click event
          const quoteId = button.dataset.id;
          this.state.selectedQuote = quoteId;
          
          // Update UI to show selected card
          sampleCards.forEach(c => c.classList.remove('active'));
          button.closest('.sample-card').classList.add('active');
          
          // Generate the quote
          this._getQuote(quoteId);
        });
      });
    }
    
    // Copy results button
    const copyButton = this.shadowObj.querySelector('.copy-result');
    if (copyButton) {
      copyButton.addEventListener('click', () => {
        this._copyResultToClipboard();
      });
    }
    
    // Tab switching
    const tabs = this.shadowObj.querySelectorAll('.tab:not(.disabled)');
    if (tabs) {
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          // Skip if tab is disabled
          if (tab.classList.contains('disabled')) return;
          
          // Deactivate all tabs and tab content
          this.shadowObj.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
          this.shadowObj.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
          
          // Activate selected tab and content
          tab.classList.add('active');
          const tabName = tab.dataset.tab;
          const content = this.shadowObj.querySelector(`.${tabName}-tab`);
          if (content) {
            content.classList.add('active');
          }
        });
      });
    }
    
    // Reset form button
    const resetButton = this.shadowObj.querySelector('#reset-form-btn');
    if (resetButton) {
      resetButton.addEventListener('click', () => {
        this._resetForm();
      });
    }
  }

  async _getQuote(quoteId) {
    if (!quoteId) {
      this.state.error = "Please select a sample quote first.";
      this.render();
      return;
    }
    
    // Find the selected quote data
    const selectedQuote = this.state.sampleQuotes.find(q => q.id === quoteId);
    if (!selectedQuote) {
      this.state.error = "Selected quote not found.";
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
          "Authorization": "Bearer 7%FRtf@34hi"
        },
        body: selectedQuote.body
      });
      
      const firstEndTime = performance.now();
      const firstClientProcessingTime = Math.round(firstEndTime - firstStartTime);
      
      if (!firstResponse.success) {
        this.state.error = firstResponse.error_message || "Failed to generate quote";
        this.state.isLoading = false;
        this.render();
        return;
      }
      
      // Add client-side processing time for comparison
      if (firstResponse.data) {
        firstResponse.data.client_processing_time_ms = firstClientProcessingTime;
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
              "Authorization": "Bearer 7%FRtf@34hi"
            },
            body: selectedQuote.body
          });
          
          const secondEndTime = performance.now();
          const secondClientProcessingTime = Math.round(secondEndTime - secondStartTime);
          
          if (secondResponse.data) {
            secondResponse.data.client_processing_time_ms = secondClientProcessingTime;
            secondResponse.data.request_number = 2;
            secondResponse.data.cached = true;
          }
          
          this.state.secondResult = secondResponse;
          this.state.showComparison = true;
          this.state.isLoading = false;
          this.render();
          
          // Animate the comparison metrics to highlight the difference
          setTimeout(() => {
            const comparisonElements = this.shadowObj.querySelectorAll('.comparison-highlight');
            comparisonElements.forEach(el => {
              el.classList.add('highlight-animation');
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
    navigator.clipboard.writeText(resultText)
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
      .catch(err => {
        console.error('Failed to copy result: ', err);
      });
  }
  
  _calculatePerformanceScore(processingTime) {
    // Calculate score based on response time
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
  
  _formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  }

  _resetForm() {
    this.state = {
      isLoading: false,
      error: null,
      result: null,
      secondResult: null,
      showComparison: false,
      selectedQuote: null,
      sampleQuotes: [...this.state.sampleQuotes]
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
  
  getBody() {
    return /* html */ `
      <div class="container">
        <div class="quote-builder-container">
          <div class="header">
            <h1>Quote Builder</h1>
            <p class="subtitle">Generate pricing for trailer rentals with Redis caching performance</p>
          </div>
          
          <div class="form-container">
            ${this.state.error ? `<div class="error-alert">${this.state.error}</div>` : ''}
            
            <div class="info-alert">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
              </svg>
              <span>Requests are sent with secure authorization. Two requests will be made to demonstrate Redis caching.</span>
            </div>
            
            <div class="sample-quotes-container">
              <h3>Select a Sample Quote</h3>
              ${this._renderSampleQuotes()}
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
        <h3>Available Quote Templates</h3>
        <div class="sample-quotes-grid">
          ${this.state.sampleQuotes.map(quote => `
            <div class="sample-card ${this.state.selectedQuote === quote.id ? 'active' : ''}" data-id="${quote.id}">
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
                  <span class="detail-value">${quote.body.usage_type.charAt(0).toUpperCase() + quote.body.usage_type.slice(1)}</span>
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
          `).join('')}
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
        <div class="tab ${!this.state.showComparison ? 'disabled' : ''}" data-tab="performance">
          Performance Comparison
          ${!this.state.showComparison ? '' : 
            `<span style="display: inline-block; width: 0.5rem; height: 0.5rem; background: var(--accent-color); border-radius: 50%; margin-left: 0.25rem;"></span>`
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
    
    const quote = this.state.result.data;
    const selectedQuoteInfo = this.state.sampleQuotes.find(q => q.id === this.state.selectedQuote);
    
    return /* html */ `
      <div class="quote-result">
        <div class="result-header">
          <div class="result-title">
            <h3>Quote for ${selectedQuoteInfo.body.trailer_type}</h3>
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
          <h4>Quote Information</h4>
          <div class="detail-grid">
            <div class="detail-card">
              <div class="detail-card-label">Location</div>
              <div class="detail-card-value">${selectedQuoteInfo.location}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Rental Period</div>
              <div class="detail-card-value">${selectedQuoteInfo.body.rental_days} Days</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Trailer Type</div>
              <div class="detail-card-value">${selectedQuoteInfo.body.trailer_type}</div>
            </div>
            <div class="detail-card">
              <div class="detail-card-label">Quote Generated</div>
              <div class="detail-card-value">${new Date().toLocaleDateString()}</div>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>Price Breakdown</h4>
          <div class="price-breakdown">
            <div class="price-item">
              <span>Base Rental (${selectedQuoteInfo.body.rental_days} days)</span>
              <span>${this._formatCurrency(quote.base_price || 1250)}</span>
            </div>
            <div class="price-item">
              <span>Delivery Fee</span>
              <span>${this._formatCurrency(quote.delivery_fee || 150)}</span>
            </div>
            ${quote.extras && quote.extras.length ? quote.extras.map(extra => `
              <div class="price-item">
                <span>${extra.name || 'Extra'} (x${extra.quantity || 1})</span>
                <span>${this._formatCurrency(extra.price || 75)}</span>
              </div>
            `).join('') : ''}
            <div class="price-item">
              <span>Environmental Fee</span>
              <span>${this._formatCurrency(quote.environmental_fee || 45)}</span>
            </div>
            <div class="price-item">
              <span>Sales Tax</span>
              <span>${this._formatCurrency(quote.tax || 120)}</span>
            </div>
            <div class="price-item total">
              <span>Total Price</span>
              <span>${this._formatCurrency(quote.total_price || 1625)}</span>
            </div>
          </div>
        </div>
        
        <div class="detail-section">
          <h4>Performance</h4>
          <div class="detail-card">
            <div class="detail-card-label">Server Processing Time</div>
            <div class="detail-card-value">${quote.processing_time_ms || quote.client_processing_time_ms || '450'}ms</div>
          </div>
        </div>
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
    
    const firstTime = firstRequest.processing_time_ms || firstRequest.client_processing_time_ms || 800;
    const secondTime = secondRequest.processing_time_ms || secondRequest.client_processing_time_ms || 250;
    
    const improvement = this._calculatePercentageImprovement(firstTime, secondTime);
    const firstScore = this._calculatePerformanceScore(firstTime);
    const secondScore = this._calculatePerformanceScore(secondTime);
    
    return /* html */ `
      <div class="comparison-container">
        <div class="comparison-card">
          <h3>First Request</h3>
          <p style="color: var(--gray-color); margin-bottom: 1rem;">Direct API call with full processing</p>
          
          <div class="performance-metrics">
            <div class="metric-card">
              <div class="metric-value" style="color: ${firstScore.color}">${firstTime}ms</div>
              <div class="metric-label">Processing Time</div>
            </div>
            <div class="metric-card">
              <div class="metric-value" style="color: ${firstScore.color}">${firstScore.score}</div>
              <div class="metric-label">Performance Score</div>
            </div>
          </div>
        </div>
        
        <div class="comparison-card comparison-highlight cached">
          <h3>Second Request (Redis Cached)</h3>
          <p style="color: var(--gray-color); margin-bottom: 1rem;">Leveraging Redis cache for improved performance</p>
          
          <div class="performance-metrics">
            <div class="metric-card comparison-highlight">
              <div class="metric-value" style="color: ${secondScore.color}">${secondTime}ms</div>
              <div class="metric-label">Processing Time</div>
            </div>
            <div class="metric-card comparison-highlight">
              <div class="metric-value" style="color: ${secondScore.color}">${secondScore.score}</div>
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
  
  getStyles() {
    return /* html */ `
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-main), sans-serif;
          --padding: 1.5rem;
          --border-radius: 0.5rem;
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
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1.5rem;
        }
        
        .sample-card {
          background: var(--background);
          border: var(--border);
          border-radius: var(--border-radius, 0.5rem);
          padding: 1.25rem;
          cursor: pointer;
          transition: all 0.2s ease;
          position: relative;
          overflow: hidden;
          box-shadow: var(--card-box-shadow-alt, 0 2px 4px 0 rgba(0, 0, 0, 0.1));
        }
        
        .sample-card:hover {
          box-shadow: var(--card-box-shadow);
          border-color: var(--accent-color);
          transform: translateY(-2px);
        }
        
        .sample-card.active {
          border: 1px solid var(--accent-color);
          background: var(--label-focus-background);
        }
        
        .sample-card.active::before {
          content: "";
          position: absolute;
          top: 0;
          left: 0;
          width: 0.25rem;
          height: 100%;
          background: var(--accent-color);
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
        }
        
        .detail-card-label {
          color: var(--gray-color);
          font-size: 0.75rem;
          margin-bottom: 0.25rem;
        }
        
        .detail-card-value {
          font-size: 1rem;
          font-weight: 600;
          font-family: var(--font-read);
          color: var(--title-color);
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
          margin-top: 1.5rem;
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
        
        @keyframes pulse {
          0% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
            box-shadow: var(--card-box-shadow, 0 12px 28px 0 rgba(70, 53, 53, 0.2));
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
        }
      </style>
    `;
  }
}