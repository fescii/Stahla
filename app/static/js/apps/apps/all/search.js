export default class CacheSearch extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/cache/search";
    this.searchData = null;
    this._block = false;
    this._empty = false;
    this._loading = false;
    this.searchOptions = [
      { value: "pricing:catalog", label: "Pricing Catalog" },
      { value: "pricing:*", label: "All Pricing Data" },
      { value: "maps:distance:*", label: "Maps Distance Cache" },
      { value: "maps:*", label: "All Maps Data" },
      { value: "dash:requests:quote:*", label: "Quote Request Counters" },
      { value: "dash:requests:location:*", label: "Location Lookup Counters" },
      { value: "dash:cache:pricing:*", label: "Pricing Cache Counters" },
      { value: "dash:cache:maps:*", label: "Maps Cache Counters" },
      { value: "dash:*", label: "All Dashboard Counters" },
      { value: "sync:last_successful_timestamp", label: "Last Sync Timestamp" },
      { value: "sync:*", label: "All Sync Data" }
    ];
    this.selectedOption = "pricing:catalog";
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
    // Set up event listeners after each render
    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  connectedCallback() {
    // Set up search form and event listeners after the component is connected
    setTimeout(() => {
      this._setupEventListeners();
    }, 100);
  }

  _setupEventListeners() {
    // Search form submission
    const searchForm = this.shadowObj.querySelector('.search-form');
    if (searchForm) {
      searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        e.stopPropagation();
        this._handleSearch();
        return false;
      });
    }

    // Search option change
    const searchSelect = this.shadowObj.querySelector('#search-select');
    if (searchSelect) {
      searchSelect.addEventListener('change', (e) => {
        this.selectedOption = e.target.value;
      });
    }      
    
    // Export button
    const exportBtn = this.shadowObj.querySelector('.export-btn');
    if (exportBtn) {
      exportBtn.addEventListener('click', this._handleExport);
    }
    
    // Set up pricing entry toggle buttons if they exist
    this._setupPricingEntryListeners();
    
    // Set up counter tabs if they exist
    this._setupCounterTabListeners();
  }
  
  // Set up event listeners for counter tabs
  _setupCounterTabListeners() {
    // Counter tab switching
    const counterTabs = this.shadowObj.querySelectorAll('.counter-tabs .tab');
    if (counterTabs && counterTabs.length > 0) {
      counterTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          // Remove active class from all tabs
          counterTabs.forEach(t => t.classList.remove('active'));
          // Add active class to clicked tab
          tab.classList.add('active');
          
          // Hide all tab content
          const tabContents = this.shadowObj.querySelectorAll('.counter-tabs .tab-content');
          tabContents.forEach(content => content.classList.add('hidden'));
          
          // Show the selected tab content
          const tabId = tab.getAttribute('data-tab') + '-tab';
          const selectedContent = this.shadowObj.getElementById(tabId);
          if (selectedContent) {
            selectedContent.classList.remove('hidden');
          }
        });
      });
    }
  }
  
  // Set up event listeners for pricing entries toggle buttons
  _setupPricingEntryListeners() {
    // Set up pricing tabs if they exist
    const pricingTabs = this.shadowObj.querySelectorAll('.pricing-tab');
    if (pricingTabs && pricingTabs.length > 0) {
      pricingTabs.forEach(tab => {
        tab.addEventListener('click', () => {
          // Remove active class from all tabs
          pricingTabs.forEach(t => t.classList.remove('active'));
          // Add active class to clicked tab
          tab.classList.add('active');
          
          // Hide all tab content
          const tabContents = this.shadowObj.querySelectorAll('.pricing-tab-content');
          tabContents.forEach(content => content.classList.remove('active'));
          
          // Show the selected tab content
          const tabId = tab.dataset.tab;
          const selectedContent = this.shadowObj.querySelector(`.pricing-tab-content[data-tab="${tabId}"]`);
          if (selectedContent) {
            selectedContent.classList.add('active');
          }
        });
      });
    }
  }

  // Handle search action
  _handleSearch = async () => {
    if (this._block || !this.selectedOption) return;

    this._loading = true;
    this._block = true;
    this.render();

    try {
      const response = await this.api.get(`${this.url}?pattern=${this.selectedOption}`, { content: "json" });
      
      // Check for 401 Unauthorized response
      if (
        response.status_code === 401 ||
        (response.error_message &&
          response.error_message.includes("validate credentials"))
      ) {
        console.log("Authentication required for search access");
        this._loading = false;
        this._block = false;
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this._block = false;
        this.searchData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;
      
      this.searchData = response;
      this.render();
      
      // Set up event listeners for the newly rendered content
      setTimeout(() => {
        this._setupPricingEntryListeners();
        this._setupCounterTabListeners();
      }, 100);

    } catch (error) {
      console.error("Error searching cache:", error);
      this._loading = false;
      this._block = false;
      this._empty = true;
      this.searchData = null;
      this.render();
    }
  };

  // Handle export functionality
  _handleExport = () => {
    // Check if we have data to export
    if (!this.searchData || !this.searchData.data) {
      console.error('No data available to export');
      return;
    }

    try {
      // Get the data to export
      const dataToExport = this.searchData.data;
      
      // Convert to JSON string
      const jsonString = JSON.stringify(dataToExport, null, 2);
      
      // Create a blob and download link
      const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'cache_search_results.json');
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
    return /* html */ `
      <div class="container">
        ${this._getSearchFormHTML()}
        ${this._loading ? this.getLoader() : ''}
        ${!this._loading && this._empty ? this._getEmptyStateHTML() : ''}
        ${!this._loading && this.searchData ? this._getResultsHTML() : ''}
      </div>
    `;
  };

  _getSearchFormHTML = () => {
    return /* html */ `
    <div class="search-header">
      <h1 class="search-title">Cache Search</h1>
      <form class="search-form" onsubmit="return false;">
        <div class="search-input-group">
          <div class="select-wrapper">
            <select id="search-select" class="search-select">
              ${this.searchOptions.map(option => 
                `<option value="${option.value}" ${this.selectedOption === option.value ? 'selected' : ''}>${option.label}</option>`
              ).join('')}
            </select>
            <svg class="select-arrow" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <button type="submit" class="search-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            Search
          </button>
        </div>
      </form>
    </div>
    `;
  };

  _getEmptyStateHTML = () => {
    return /* html */ `
    <div class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
      <h3>No results found</h3>
      <p>No cache entries were found matching your search criteria.</p>
    </div>
    `;
  };

  _getResultsHTML = () => {
    if (!this.searchData || !this.searchData.data || this.searchData.data.length === 0) {
      return this._getEmptyStateHTML();
    }

    // Get the data from the response
    const data = this.searchData.data;
    
    // Check which type of data was returned based on the selected option
    if (this.selectedOption.includes('pricing:catalog')) {
      return this._getPricingCatalogHTML(data[0]);
    } else if (this.selectedOption === 'pricing:*') {
      return this._getAllPricingDataHTML(data);
    } else if (this.selectedOption.includes('dash:cache:maps')) {
      return this._getMapsCountersHTML(data);
    } else if (this.selectedOption.includes('maps:distance:')) {
      return this._getMapsDistanceHTML(data);
    } else if (this.selectedOption.includes('maps:')) {
      return this._getMapsDistanceHTML(data);
    } else if (this.selectedOption.includes('dash:')) {
      return this._getDashboardCountersHTML(data);
    } else if (this.selectedOption.includes('sync:')) {
      return this._getSyncDataHTML(data);
    } else {
      // Generic rendering for unknown data types
      return this._getGenericDataHTML(data);
    }
  };

  // Helper method to format durations from seconds
  _formatDuration = (seconds) => {
    if (typeof seconds !== 'number') return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${remainingSeconds}s`;
    }
  };

  // Helper to format tab names
  _formatTabName = (name) => {
    return name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };
  
  // Method for displaying maps cache counters data
  _getMapsCountersHTML = (data) => {
    if (!data || data.length === 0) {
      return this._getEmptyStateHTML();
    }
    
    // Find hits and misses counters
    const hitsCounter = data.find(item => item.key === 'dash:cache:maps:hits');
    const missesCounter = data.find(item => item.key === 'dash:cache:maps:misses');
    
    // Extract hits and misses values
    const hits = hitsCounter ? parseInt(hitsCounter.value_preview) : 0;
    const misses = missesCounter ? parseInt(missesCounter.value_preview) : 0;
    const total = hits + misses;
    
    // Calculate hit rate percentage
    const hitRate = total > 0 ? ((hits / total) * 100).toFixed(1) : 0;
    
    // Get formatted timestamp for the most recent counter
    const lastUpdated = hitsCounter?.timestamp || missesCounter?.timestamp 
      ? new Date(Math.max(
          hitsCounter?.timestamp ? new Date(hitsCounter.timestamp).getTime() : 0, 
          missesCounter?.timestamp ? new Date(missesCounter.timestamp).getTime() : 0
        )).toLocaleString() 
      : 'Unknown';
    
    // Template with hit rate card and counter cards
    return /* html */ `
      <div class="results-container">
        <div class="results-header">
          <h2 class="results-title">Maps Cache Counters</h2>
          <div class="results-meta">
            <span>Last Updated: <strong>${lastUpdated}</strong></span>
          </div>
          <button class="export-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Export JSON
          </button>
        </div>
        
        <div class="maps-cache-overview">
          <div class="hit-rate-card">
            <h3 class="hit-rate-title">Cache Hit Rate</h3>
            <div class="hit-rate-value ${parseFloat(hitRate) >= 90 ? 'high' : parseFloat(hitRate) >= 70 ? 'medium' : 'low'}">
              ${hitRate}%
            </div>
            <div class="hit-rate-detail">
              <span>${total.toLocaleString()} total requests</span>
            </div>
          </div>
          
          <div class="maps-counters">
            <div class="counter-card hits">
              <h3 class="counter-name">Cache Hits</h3>
              <p class="counter-value">${hits.toLocaleString()}</p>
              <p class="counter-percentage">${total > 0 ? ((hits / total) * 100).toFixed(1) : 0}%</p>
              <div class="counter-bar">
                <div class="counter-bar-fill" style="width: ${total > 0 ? ((hits / total) * 100) : 0}%"></div>
              </div>
            </div>
            
            <div class="counter-card misses">
              <h3 class="counter-name">Cache Misses</h3>
              <p class="counter-value">${misses.toLocaleString()}</p>
              <p class="counter-percentage">${total > 0 ? ((misses / total) * 100).toFixed(1) : 0}%</p>
              <div class="counter-bar">
                <div class="counter-bar-fill" style="width: ${total > 0 ? ((misses / total) * 100) : 0}%"></div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="maps-counters-explainer">
          <h3>About Cache Hit Rate</h3>
          <p>
            The hit rate shows how often the application is able to retrieve maps data from the cache 
            rather than making external API calls. A higher hit rate indicates better performance and 
            reduced external API usage.
          </p>
          <div class="optimization-tips">
            <h4>Optimization Tips</h4>
            <ul>
              ${parseFloat(hitRate) < 70 ? `
                <li>Consider increasing the TTL (time-to-live) for map cache entries.</li>
                <li>Review the most common location lookups and ensure they're being cached.</li>
                <li>Check the cache eviction policy to ensure important entries aren't being removed prematurely.</li>
              ` : ''}
              ${parseFloat(hitRate) >= 70 && parseFloat(hitRate) < 90 ? `
                <li>Your maps cache is performing reasonably well, but there's room for improvement.</li>
                <li>Consider analyzing which routes have the most misses and preemptively cache popular routes.</li>
                <li>Review cache size limits to ensure you have adequate capacity for your traffic patterns.</li>
              ` : ''}
              ${parseFloat(hitRate) >= 90 ? `
                <li>Your maps cache is performing well! Continue monitoring for any changes.</li>
                <li>Consider slight adjustments to TTL values to maintain this high performance.</li>
              ` : ''}
            </ul>
          </div>
        </div>
      </div>
    `;
  };

  // Method for displaying pricing catalog data
  _getPricingCatalogHTML = (catalogData) => {
    if (!catalogData || !catalogData.value_preview) {
      return this._getEmptyStateHTML();
    }

    const valuePreview = catalogData.value_preview;
    const lastUpdated = catalogData.timestamp ? new Date(catalogData.timestamp).toLocaleString() : 'Unknown';

    return /* html */ `<div class="results-container">
      <div class="results-header">
        <h2 class="results-title">Cache Results</h2>
        <div class="results-meta">
          <span>Cache Key: <strong>${catalogData.key}</strong></span>
          <span>Last Updated: <strong>${lastUpdated}</strong></span>
          <span>TTL: <strong>${catalogData.ttl === -1 ? 'No Expiration' : catalogData.ttl}</strong></span>
        </div>
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export JSON
        </button>
      </div>

      <div class="tabs">
        <button class="tab active" data-tab="products">Products</button>
        <button class="tab" data-tab="generators">Generators</button>
        <button class="tab" data-tab="delivery">Delivery</button>
        <button class="tab" data-tab="seasonal">Seasonal</button>
      </div>

      <div class="tab-content" id="products-tab">
        <h3 class="section-title">Products</h3>
        <div class="product-cards">
          ${Object.entries(valuePreview.products).map(([id, product]) => this._getProductCardHTML(product)).join('')}
        </div>
      </div>

      <div class="tab-content hidden" id="generators-tab">
        <h3 class="section-title">Generators</h3>
        <div class="generators-table">
          <table>
            <thead>
              <tr>
                <th>Generator</th>
                <th>Event Rate</th>
                <th>7 Day Rate</th>
                <th>28 Day Rate</th>
              </tr>
            </thead>
            <tbody>
              ${Object.entries(valuePreview.generators).map(([id, generator]) => `
                <tr>
                  <td>${generator.name}</td>
                  <td>${generator.rate_event === null ? '<span class="na-text">N/A</span>' : '$' + generator.rate_event.toLocaleString()}</td>
                  <td>$${generator.rate_7_day.toLocaleString()}</td>
                  <td>$${generator.rate_28_day.toLocaleString()}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>

      <div class="tab-content hidden" id="delivery-tab">
        <h3 class="section-title">Delivery Rates</h3>
        <div class="delivery-info">
          <div class="info-card">
            <h4>Base Delivery Fee</h4>
            <p class="price">${valuePreview.delivery.base_fee === 0 ? 'Free' : '$' + valuePreview.delivery.base_fee.toLocaleString()}</p>
          </div>
          <div class="info-card">
            <h4>Free Delivery Threshold</h4>
            <p class="highlight">${valuePreview.delivery.free_miles_threshold} miles</p>
          </div>
        </div>
        <h4 class="subsection-title">Per Mile Rates by Region</h4>
        <div class="delivery-rates">
          ${Object.entries(valuePreview.delivery.per_mile_rates).map(([region, rate]) => `
            <div class="rate-card">
              <h5 class="region">${region.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</h5>
              <p class="rate">$${rate.toFixed(2)}/mile</p>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="tab-content hidden" id="seasonal-tab">
        <h3 class="section-title">Seasonal Multipliers</h3>
        <div class="info-card standard-rate">
          <h4>Standard Rate</h4>
          <p class="multiplier">${valuePreview.seasonal_multipliers.standard}x</p>
        </div>
        <h4 class="subsection-title">Seasonal Tiers</h4>
        <div class="seasonal-tiers">
          ${valuePreview.seasonal_multipliers.tiers.map(tier => {
            const startDate = new Date(tier.start_date).toLocaleDateString();
            const endDate = new Date(tier.end_date).toLocaleDateString();
            return `
              <div class="tier-card">
                <h5>${tier.name}</h5>
                <p class="dates">${startDate} - ${endDate}</p>
                <p class="multiplier">${tier.rate}x</p>
              </div>
            `;
          }).join('')}
        </div>
      </div>
    </div>

    <script>
      // Tab switching functionality
      const tabs = this.shadowRoot.querySelectorAll('.tab');
      tabs.forEach(tab => {
        tab.addEventListener('click', () => {
          // Remove active class from all tabs
          tabs.forEach(t => t.classList.remove('active'));
          // Add active class to clicked tab
          tab.classList.add('active');
          
          // Hide all tab content
          const tabContents = this.shadowRoot.querySelectorAll('.tab-content');
          tabContents.forEach(content => content.classList.add('hidden'));
          
          // Show the selected tab content
          const tabId = tab.getAttribute('data-tab') + '-tab';
          const selectedContent = this.shadowRoot.getElementById(tabId);
          selectedContent.classList.remove('hidden');
        });
      });
    </script>
    `;
  };

  _getProductCardHTML = (product) => {
    return /* html */ `
    <div class="product-card">
      <h4 class="product-name">${product.name}</h4>
      <div class="product-rates">
        <div class="rate-group">
          <h5>Event Rates</h5>
          <div class="rate-item">
            <span>Standard</span>
            <span class="rate">$${product.event_standard.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>Premium</span>
            <span class="rate">$${product.event_premium.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>Premium+</span>
            <span class="rate">$${product.event_premium_plus.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>Platinum</span>
            <span class="rate">$${product.event_premium_platinum.toLocaleString()}</span>
          </div>
        </div>
        <div class="rate-group">
          <h5>Extended Rates</h5>
          <div class="rate-item">
            <span>Weekly</span>
            <span class="rate">$${product.weekly_7_day.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>28 Day</span>
            <span class="rate">$${product.rate_28_day.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>2-5 Month</span>
            <span class="rate">$${product.rate_2_5_month.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>6+ Month</span>
            <span class="rate">$${product.rate_6_plus_month.toLocaleString()}</span>
          </div>
          <div class="rate-item">
            <span>18+ Month</span>
            <span class="rate">$${product.rate_18_plus_month.toLocaleString()}</span>
          </div>
        </div>
      </div>
      <div class="extras">
        <h5>Extras</h5>
        <div class="extras-items">
          ${Object.entries(product.extras).map(([name, price]) => `
            <div class="extra-item">
              <span>${name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
              <span class="price">$${price.toLocaleString()}</span>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
    `;
  };
  
  // Method to display all pricing data (pricing:*)
  _getAllPricingDataHTML = (data) => {
    if (!data || data.length === 0) {
      return this._getEmptyStateHTML();
    }
    
    // Find the catalog entry if it exists
    const catalogEntry = data.find(item => item.key === 'pricing:catalog');
    
    // Special case: If we only have the catalog entry, extract products, generators, etc. from it
    if (data.length === 1 && catalogEntry) {
      // Parse the catalog data if needed
      let catalogData = catalogEntry.value_preview;
      if (typeof catalogData === 'string') {
        try {
          catalogData = JSON.parse(catalogData);
        } catch (e) {
          console.error('Error parsing catalog data:', e);
          catalogData = {};
        }
      }
      
      // Create synthetic entries from the catalog data for display
      const syntheticEntries = [];
      
      // Add products
      if (catalogData.products) {
        Object.entries(catalogData.products).forEach(([id, product]) => {
          syntheticEntries.push({
            key: `pricing:product:${id}`,
            value_preview: product,
            ttl: catalogEntry.ttl,
            timestamp: catalogEntry.timestamp
          });
        });
      }
      
      // Add generators
      if (catalogData.generators) {
        Object.entries(catalogData.generators).forEach(([id, generator]) => {
          syntheticEntries.push({
            key: `pricing:generator:${id}`,
            value_preview: generator,
            ttl: catalogEntry.ttl,
            timestamp: catalogEntry.timestamp
          });
        });
      }
      
      // Add delivery info
      if (catalogData.delivery) {
        syntheticEntries.push({
          key: 'pricing:delivery:rates',
          value_preview: catalogData.delivery,
          ttl: catalogEntry.ttl,
          timestamp: catalogEntry.timestamp
        });
      }
      
      // Add seasonal info
      if (catalogData.seasonal_multipliers) {
        syntheticEntries.push({
          key: 'pricing:seasonal:multipliers',
          value_preview: catalogData.seasonal_multipliers,
          ttl: catalogEntry.ttl,
          timestamp: catalogEntry.timestamp
        });
      }
      
      // Replace data with our synthetic entries plus the original catalog
      data = [catalogEntry, ...syntheticEntries];
    }
    
    // Group pricing entries by type
    const productEntries = data.filter(item => item.key.includes('product:'));
    const generatorEntries = data.filter(item => item.key.includes('generator:'));
    const deliveryEntries = data.filter(item => item.key.includes('delivery:'));
    const otherEntries = data.filter(item => 
      !item.key.includes('product:') && 
      !item.key.includes('generator:') && 
      !item.key.includes('delivery:') &&
      item.key !== 'pricing:catalog'
    );
    
    // Filter out the catalog entry from the data array
    const filteredData = data.filter(item => item.key !== 'pricing:catalog');
    
    return /* html */ `
    <div class="results-container">
      <div class="results-header">
        <h2 class="results-title">All Pricing Data</h2>
        <div class="results-meta">
          <span>Results Found: <strong>${filteredData.length}</strong></span>
        </div>
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export JSON
        </button>
      </div>
      
      <div class="pricing-data-container">
        ${catalogEntry ? this._renderCatalogPreview(catalogEntry) : ''}
        
        <div class="pricing-entries-section">
          <div class="pricing-tabs">
            <button class="pricing-tab active" data-tab="all">All Entries (${filteredData.length})</button>
            ${productEntries.length > 0 ? `<button class="pricing-tab" data-tab="products">Products (${productEntries.length})</button>` : ''}
            ${generatorEntries.length > 0 ? `<button class="pricing-tab" data-tab="generators">Generators (${generatorEntries.length})</button>` : ''}
            ${deliveryEntries.length > 0 ? `<button class="pricing-tab" data-tab="delivery">Delivery (${deliveryEntries.length})</button>` : ''}
            ${otherEntries.length > 0 ? `<button class="pricing-tab" data-tab="other">Other (${otherEntries.length})</button>` : ''}
          </div>
          
          <div class="pricing-tab-content active" data-tab="all">
            <div class="pricing-entries">
              ${filteredData.map(item => this._renderPricingEntry(item)).join('')}
            </div>
          </div>
          
          ${productEntries.length > 0 ? `
          <div class="pricing-tab-content" data-tab="products">
            <div class="pricing-entries">
              ${productEntries.map(item => this._renderPricingEntry(item)).join('')}
            </div>
          </div>
          ` : ''}
          
          ${generatorEntries.length > 0 ? `
          <div class="pricing-tab-content" data-tab="generators">
            <div class="pricing-entries">
              ${generatorEntries.map(item => this._renderPricingEntry(item)).join('')}
            </div>
          </div>
          ` : ''}
          
          ${deliveryEntries.length > 0 ? `
          <div class="pricing-tab-content" data-tab="delivery">
            <div class="pricing-entries">
              ${deliveryEntries.map(item => this._renderPricingEntry(item)).join('')}
            </div>
          </div>
          ` : ''}
          
          ${otherEntries.length > 0 ? `
          <div class="pricing-tab-content" data-tab="other">
            <div class="pricing-entries">
              ${otherEntries.map(item => this._renderPricingEntry(item)).join('')}
            </div>
          </div>
          ` : ''}
        </div>
      </div>
    </div>
    `;
  };
  
  // Helper to render a pricing catalog preview
  _renderCatalogPreview = (catalogEntry) => {
    if (!catalogEntry || !catalogEntry.value_preview) return '';
    
    try {
      const catalog = typeof catalogEntry.value_preview === 'string' 
        ? JSON.parse(catalogEntry.value_preview) 
        : catalogEntry.value_preview;
      
      const lastUpdated = catalog.last_updated 
        ? new Date(catalog.last_updated).toLocaleString() 
        : (catalogEntry.timestamp 
            ? new Date(catalogEntry.timestamp).toLocaleString() 
            : 'Unknown');
      
      return /* html */ `
      <div class="catalog-preview">
        <h3 class="section-title">Pricing Catalog Overview</h3>
        <div class="catalog-info">
          <div class="info-box">
            <h4>Last Updated</h4>
            <p>${lastUpdated}</p>
          </div>
          <div class="info-box">
            <h4>Products</h4>
            <p>${catalog.products ? Object.keys(catalog.products).length : 0}</p>
          </div>
          <div class="info-box">
            <h4>Generators</h4>
            <p>${catalog.generators ? Object.keys(catalog.generators).length : 0}</p>
          </div>
          <div class="info-box">
            <h4>Seasonal Tiers</h4>
            <p>${catalog.seasonal_multipliers && catalog.seasonal_multipliers.tiers ? catalog.seasonal_multipliers.tiers.length : 0}</p>
          </div>
        </div>
        
        <div class="current-seasonal-info">
          <h4>Current Season</h4>
          ${this._getCurrentSeasonalTier(catalog)}
        </div>
      </div>
      `;
    } catch (e) {
      console.error('Error rendering catalog preview:', e);
      return '';
    }
  };
  
  // Helper to get the current seasonal tier information
  _getCurrentSeasonalTier = (catalog) => {
    if (!catalog.seasonal_multipliers || !catalog.seasonal_multipliers.tiers) {
      return '<p>Standard Rate (1.0x)</p>';
    }
    
    const now = new Date();
    const currentTier = catalog.seasonal_multipliers.tiers.find(tier => {
      const startDate = new Date(tier.start_date);
      const endDate = new Date(tier.end_date);
      return now >= startDate && now <= endDate;
    });
    
    if (!currentTier) {
      return `<p>Standard Rate (${catalog.seasonal_multipliers.standard}x)</p>`;
    }
    
    return `
    <div class="current-tier">
      <p class="tier-name">${currentTier.name}</p>
      <p class="tier-rate">${currentTier.rate}x multiplier</p>
      <p class="tier-dates">
        ${new Date(currentTier.start_date).toLocaleDateString()} - 
        ${new Date(currentTier.end_date).toLocaleDateString()}
      </p>
    </div>
    `;
  };
  
  // Helper to render a single pricing entry
  _renderPricingEntry = (item) => {
    // Format the timestamp if available
    const timestamp = item.timestamp ? new Date(item.timestamp).toLocaleString() : 'N/A';
    
    // Parse the value preview if it's a string
    let valuePreview = item.value_preview;
    if (typeof valuePreview === 'string') {
      try {
        valuePreview = JSON.parse(valuePreview);
      } catch (e) {
        // Keep as is if not valid JSON
      }
    }
    
    // Determine the entry type
    let entryType = 'Unknown';
    let entryIcon = '';
    let displayKey = item.key;
    
    if (item.key === 'pricing:catalog') {
      entryType = 'Complete Catalog';
      entryIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 3v18h18"></path>
          <path d="M18.4 9a9 9 0 0 0-9.2 8.8"></path>
          <path d="M13 5a9 9 0 0 0-9.6 7.6"></path>
          <path d="M19 14a9 9 0 0 0-8.7 6.5"></path>
        </svg>
      `;
    } else if (item.key.includes('product:')) {
      entryType = 'Product';
      // Extract just the product name without the prefix
      displayKey = item.key.replace('pricing:product:', '');
      entryIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path>
          <path d="m3.3 7 8.7 5 8.7-5"></path>
          <path d="M12 12v10"></path>
        </svg>
      `;
    } else if (item.key.includes('generator:')) {
      entryType = 'Generator';
      // Extract just the generator name without the prefix
      displayKey = item.key.replace('pricing:generator:', '');
      entryIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 7 4.25 4.75A1 1 0 0 1 4.63 3l2.87-.71a1 1 0 0 1 1.17.57L10 5.25"></path>
          <path d="m14 7 1.75-2.25a1 1 0 0 0-.38-1.75l-2.87-.71a1 1 0 0 0-1.17.57L10 5.25"></path>
          <path d="M5 15h14"></path>
          <path d="M5 9v12h14V9"></path>
        </svg>
      `;
    } else if (item.key.includes('delivery:')) {
      entryType = 'Delivery';
      // Extract just the delivery info without the prefix
      displayKey = item.key.replace('pricing:delivery:', '');
      entryIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      `;
    } else if (item.key.includes('seasonal:')) {
      entryType = 'Seasonal';
      // Extract just the seasonal info without the prefix
      displayKey = item.key.replace('pricing:seasonal:', '');
      entryIcon = `
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M12 6v6l4 2"></path>
        </svg>
      `;
    } else {
      // For other keys, try to remove the pricing: prefix if it exists
      displayKey = item.key.replace('pricing:', '');
    }
    
    // Create a formatted preview of the data
    let formattedPreview = '';
    
    if (typeof valuePreview === 'object' && valuePreview !== null) {
      if (entryType === 'Product' && valuePreview.name) {
        formattedPreview = `
          <div class="quick-info">
            <div class="info-row"><strong>Name:</strong> ${valuePreview.name}</div>
            ${valuePreview.event_standard ? `<div class="info-row"><strong>Standard Rate:</strong> $${valuePreview.event_standard.toLocaleString()}</div>` : ''}
            ${valuePreview.weekly_7_day ? `<div class="info-row"><strong>Weekly Rate:</strong> $${valuePreview.weekly_7_day.toLocaleString()}</div>` : ''}
            ${valuePreview.rate_28_day ? `<div class="info-row"><strong>28 Day Rate:</strong> $${valuePreview.rate_28_day.toLocaleString()}</div>` : ''}
          </div>
          <div class="full-product-info">
            <h4>All Rates</h4>
            <div class="rates-grid">
              <div class="rate-section">
                <h5>Event Rates</h5>
                <div class="rate-item"><span>Standard:</span> <span>$${valuePreview.event_standard?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>Premium:</span> <span>$${valuePreview.event_premium?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>Premium+:</span> <span>$${valuePreview.event_premium_plus?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>Platinum:</span> <span>$${valuePreview.event_premium_platinum?.toLocaleString() || 'N/A'}</span></div>
              </div>
              <div class="rate-section">
                <h5>Extended Rates</h5>
                <div class="rate-item"><span>Weekly:</span> <span>$${valuePreview.weekly_7_day?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>28 Day:</span> <span>$${valuePreview.rate_28_day?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>2-5 Month:</span> <span>$${valuePreview.rate_2_5_month?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>6+ Month:</span> <span>$${valuePreview.rate_6_plus_month?.toLocaleString() || 'N/A'}</span></div>
                <div class="rate-item"><span>18+ Month:</span> <span>$${valuePreview.rate_18_plus_month?.toLocaleString() || 'N/A'}</span></div>
              </div>
            </div>
            ${valuePreview.extras ? `
            <div class="extras-section">
              <h5>Extras</h5>
              <div class="extras-grid">
                ${Object.entries(valuePreview.extras).map(([name, price]) => `
                  <div class="extra-item">
                    <span>${name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    <span class="price">$${price.toLocaleString()}</span>
                  </div>
                `).join('')}
              </div>
            </div>
            ` : ''}
          </div>
        `;
      } else if (entryType === 'Generator' && valuePreview.name) {
        formattedPreview = `
          <div class="quick-info">
            <div class="info-row"><strong>Name:</strong> ${valuePreview.name}</div>
            ${valuePreview.rate_event !== undefined ? `<div class="info-row"><strong>Event Rate:</strong> ${valuePreview.rate_event === null ? 'N/A' : '$' + valuePreview.rate_event.toLocaleString()}</div>` : ''}
            ${valuePreview.rate_7_day ? `<div class="info-row"><strong>Weekly Rate:</strong> $${valuePreview.rate_7_day.toLocaleString()}</div>` : ''}
            ${valuePreview.rate_28_day ? `<div class="info-row"><strong>28 Day Rate:</strong> $${valuePreview.rate_28_day.toLocaleString()}</div>` : ''}
          </div>
        `;
      } else if (item.key.includes('delivery:') && valuePreview.per_mile_rates) {
        formattedPreview = `
          <div class="quick-info">
            <div class="info-row"><strong>Base Fee:</strong> ${valuePreview.base_fee === 0 ? 'Free' : '$' + valuePreview.base_fee.toLocaleString()}</div>
            <div class="info-row"><strong>Free Miles Threshold:</strong> ${valuePreview.free_miles_threshold || 0} miles</div>
          </div>
          <div class="delivery-rates-container">
            <h4>Per Mile Rates by Region</h4>
            <div class="rates-grid">
              ${Object.entries(valuePreview.per_mile_rates).map(([region, rate]) => `
                <div class="region-rate">
                  <span class="region-name">${region.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                  <span class="region-price">$${rate.toFixed(2)}/mile</span>
                </div>
              `).join('')}
            </div>
          </div>
        `;
      } else if (item.key.includes('seasonal:') && valuePreview.tiers) {
        const now = new Date();
        const currentTier = valuePreview.tiers.find(tier => {
          const startDate = new Date(tier.start_date);
          const endDate = new Date(tier.end_date);
          return now >= startDate && now <= endDate;
        });
        
        formattedPreview = `
          <div class="quick-info">
            <div class="info-row"><strong>Standard Rate:</strong> ${valuePreview.standard}x</div>
            ${currentTier ? `<div class="info-row"><strong>Current Tier:</strong> ${currentTier.name} (${currentTier.rate}x)</div>` : ''}
            <div class="info-row"><strong>Number of Tiers:</strong> ${valuePreview.tiers.length}</div>
          </div>
          <div class="seasonal-tiers-container">
            <h4>Seasonal Pricing Tiers</h4>
            <div class="tiers-grid">
              ${valuePreview.tiers.map(tier => {
                const startDate = new Date(tier.start_date).toLocaleDateString();
                const endDate = new Date(tier.end_date).toLocaleDateString();
                const isActive = now >= new Date(tier.start_date) && now <= new Date(tier.end_date);
                return `
                  <div class="tier-card ${isActive ? 'active-tier' : ''}">
                    <h5>${tier.name}</h5>
                    <div class="tier-dates">${startDate} - ${endDate}</div>
                    <div class="tier-rate">${tier.rate}x</div>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `;
      } else {
        // For other object types, show a compact JSON representation
        formattedPreview = `<pre class="json-preview">${JSON.stringify(valuePreview, null, 2)}</pre>`;
      }
    } else {
      formattedPreview = `<pre class="json-preview">${String(valuePreview)}</pre>`;
    }
    
    return `
      <div class="pricing-entry expanded">
        <div class="entry-header">
          <div class="entry-type">
            ${entryIcon}
            <span>${entryType}</span>
          </div>
          <h4 class="entry-key">${displayKey}</h4>
          <div class="entry-meta">
            <span class="entry-ttl ${item.ttl === -1 ? 'no-expiry' : ''}">TTL: ${item.ttl === -1 ? 'No Expiration' : item.ttl + 's'}</span>
            <span class="entry-timestamp">Updated: ${timestamp}</span>
          </div>
        </div>
        <div class="entry-content">
          ${formattedPreview}
        </div>
      </div>
    `;
  };

  // Method for displaying maps distance cache data
  _getMapsDistanceHTML = (data) => {
    if (!data || data.length === 0) {
      return this._getEmptyStateHTML();
    }
    
    // Log the first item to see the actual data structure
    console.log("Maps data structure:", data.length > 0 ? data[0] : null);
    
    // Sort data by distance - show closest first, then furthest
    const sortedData = [...data].sort((a, b) => {
      // First try to sort by distance if available
      const distanceA = a.value_preview && a.value_preview.distance_miles ? parseFloat(a.value_preview.distance_miles) : 
                       (a.value_preview && a.value_preview.distance_meters ? parseFloat(a.value_preview.distance_meters) / 1609.34 : Number.MAX_VALUE);
      const distanceB = b.value_preview && b.value_preview.distance_miles ? parseFloat(b.value_preview.distance_miles) : 
                       (b.value_preview && b.value_preview.distance_meters ? parseFloat(b.value_preview.distance_meters) / 1609.34 : Number.MAX_VALUE);
      
      if (distanceA !== Number.MAX_VALUE || distanceB !== Number.MAX_VALUE) return distanceA - distanceB;
      
      // If no distance available, fall back to timestamp
      const timeA = a.value_preview && a.value_preview.timestamp ? new Date(a.value_preview.timestamp) : 0;
      const timeB = b.value_preview && b.value_preview.timestamp ? new Date(b.value_preview.timestamp) : 0;
      
      if (timeA !== 0 || timeB !== 0) return timeB - timeA;
      
      // Otherwise sort by key
      return String(a.key).localeCompare(String(b.key));
    });

    return /* html */ `
    <div class="results-container">
      <div class="results-header">
        <h2 class="results-title">Maps Distance Cache</h2>
        <div class="results-meta">
          <span>Results Found: <strong>${data.length}</strong></span>
        </div>
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export JSON
        </button>
      </div>

      <div class="maps-distance-table">
        <table>
          <thead>
            <tr>
              <th>Route</th>
              <th>Distance (miles)</th>
              <th>Duration</th>
              <th>TTL</th>
            </tr>
          </thead>
          <tbody>
            ${sortedData.map(item => {
              // Try to parse the value_preview if it's a string
              let preview = item.value_preview;
              if (typeof preview === 'string') {
                try {
                  preview = JSON.parse(preview);
                } catch (e) {
                  // If parsing fails, keep it as is
                  preview = { raw: preview };
                }
              }
              
              // If preview is not an object at this point, create an empty one
              preview = preview || {};
              
              // Extract route info from the key if possible
              const keyParts = item.key.split(':');
              const keyInfo = keyParts.length > 2 ? keyParts[2] : '';
              const routeInfo = keyInfo.replace(/_/g, ' ');
              
              // Get branch information (this is the "From" location)
              const nearestBranch = preview.nearest_branch || {};
              const branchName = nearestBranch.name || 'N/A';
              const branchAddress = nearestBranch.address || 'N/A';
              
              // Get delivery location (this is the "To" location)
              const deliveryLocation = preview.delivery_location || 'N/A';
              
              // Set origin (From) and destination (To) using the branch address and delivery location
              let origin = branchAddress !== 'N/A' ? branchAddress : 'Unknown';
              let destination = deliveryLocation !== 'N/A' ? deliveryLocation : 'Unknown';
              
              // If both are still unknown, try to extract from key
              if (origin === 'Unknown' && destination === 'Unknown' && routeInfo) {
                const routeParts = routeInfo.split('_to_');
                if (routeParts.length === 2) {
                  origin = routeParts[0].replace(/_/g, ' ');
                  destination = routeParts[1].replace(/_/g, ' ');
                }
              }
              
              // Format the distance if available, otherwise N/A
              const distance = preview.distance_miles 
                ? preview.distance_miles.toFixed(1) 
                : (preview.distance_meters 
                  ? (preview.distance_meters / 1609.34).toFixed(1)
                  : 'N/A');
              
              // Format the duration
              const duration = preview.duration 
                ? this._formatDuration(preview.duration) 
                : (preview.duration_seconds 
                  ? this._formatDuration(preview.duration_seconds)
                  : 'N/A');
              
              // Get updated timestamp (not used in UI)
              /* const updated = preview.timestamp 
                ? new Date(preview.timestamp).toLocaleString() 
                : (preview.updated_at 
                  ? new Date(preview.updated_at).toLocaleString()
                  : 'N/A'); */
              
              // Format TTL
              const ttl = item.ttl === -1 ? 'No Expiration' : `${item.ttl}s`;
              
              // Check if we have any additional data to show
              const hasAdditionalData = 
                preview.travel_mode || 
                preview.status || 
                (preview.legs && preview.legs.length > 0) ||
                (preview.polyline && preview.polyline.length > 0);
              
              return `
                <tr>
                  <td>
                    <div class="route-info">
                      <div>
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"></circle>
                          <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon>
                        </svg>
                        <strong>From:</strong> ${origin}
                      </div>
                      <div>
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                          <circle cx="12" cy="10" r="3"></circle>
                        </svg>
                        <strong>To:</strong> ${destination}
                      </div>
                      ${branchName !== 'N/A' ? `
                      <div class="branch-info">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="9 22 9 12 15 12 15 22"></polyline>
                        </svg>
                        <strong>Branch:</strong> ${branchName}
                      </div>
                      ` : ''}
                    </div>
                  </td>
                  <td>
                    ${distance === 'N/A' ? 'N/A' : `
                    <div class="distance-info" style="display: flex; justify-content: center; align-items: center;">
                      <span class="distance-value">${distance}</span>
                      <span class="distance-unit">miles</span>
                    </div>
                    `}
                  </td>
                  <td>
                    ${duration === 'N/A' ? 'N/A' : `
                    <div class="duration-info" style="display: flex; justify-content: center; align-items: center; flex-direction: column;">
                      <span class="duration-value">${duration}</span>
                      ${preview.traffic_model ? `<span class="traffic-model">(${preview.traffic_model})</span>` : ''}
                    </div>
                    `}
                  </td>
                  <td>
                    <div style="display: flex; justify-content: center;">
                      <span class="ttl-badge ${item.ttl === -1 ? 'no-expiry' : ''}">${ttl}</span>
                    </div>
                  </td>
                </tr>
                ${hasAdditionalData ? `
                <tr class="details-row">
                  <td colspan="4">
                    <div class="route-details">
                      ${preview.travel_mode ? `<div class="detail-item"><strong>Travel Mode:</strong> ${preview.travel_mode}</div>` : ''}
                      ${preview.status ? `<div class="detail-item"><strong>Status:</strong> ${preview.status}</div>` : ''}
                      ${preview.legs && preview.legs.length ? `
                        <div class="detail-item">
                          <strong>Legs:</strong> ${preview.legs.length}
                          ${preview.legs.map((leg, index) => `
                            <div class="leg-detail">
                              <span>Leg ${index + 1}:</span> 
                              ${leg.distance ? `${(leg.distance.value / 1609.34).toFixed(1)} miles` : ''} 
                              ${leg.duration ? `(${this._formatDuration(leg.duration.value)})` : ''}
                            </div>
                          `).join('')}
                        </div>
                      ` : ''}
                    </div>
                  </td>
                </tr>
                ` : ''}
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>
    `;
  };

  // Method for displaying dashboard counters data
  _getDashboardCountersHTML = (data) => {
    if (!data || data.length === 0) {
      return this._getEmptyStateHTML();
    }

    // Group counters by type
    const counterGroups = data.reduce((acc, item) => {
      const parts = item.key.split(':');
      const group = parts.length > 2 ? parts[2] : 'other';
      
      if (!acc[group]) {
        acc[group] = [];
      }
      
      acc[group].push(item);
      return acc;
    }, {});

    // Special handling for Maps Cache Counters
    if (this.selectedOption.includes('dash:cache:maps')) {
      return this._getMapsCountersHTML(data);
    }

    return /* html */ `
    <div class="results-container">
      <div class="results-header">
        <h2 class="results-title">Dashboard Counters</h2>
        <div class="results-meta">
          <span>Results Found: <strong>${data.length}</strong></span>
        </div>
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export JSON
        </button>
      </div>

      <div class="counter-tabs">
        <div class="tabs">
          ${Object.keys(counterGroups).map((group, index) => `
            <button class="tab ${index === 0 ? 'active' : ''}" data-tab="${group}">${this._formatTabName(group)}</button>
          `).join('')}
        </div>

        ${Object.entries(counterGroups).map(([group, items], index) => `
          <div class="tab-content ${index === 0 ? '' : 'hidden'}" id="${group}-tab">
            <h3 class="section-title">${this._formatTabName(group)} Counters</h3>
            <div class="counter-cards">
              ${items.map(item => {
                const value = typeof item.value_preview === 'number' 
                  ? item.value_preview.toLocaleString() 
                  : (item.value_preview?.count || '0').toLocaleString();
                
                const keyParts = item.key.split(':');
                const name = keyParts[keyParts.length - 1].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                return `
                  <div class="counter-card">
                    <h4 class="counter-name">${name}</h4>
                    <p class="counter-value">${value}</p>
                    <p class="counter-key">${item.key}</p>
                  </div>
                `;
              }).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    </div>
    `;
  };

  // Method for displaying sync data
  _getSyncDataHTML = (data) => {
    if (!data || data.length === 0) {
      return this._getEmptyStateHTML();
    }

    return /* html */ `
    <div class="results-container">
      <div class="results-header">
        <h2 class="results-title">Sync Data</h2>
        <div class="results-meta">
          <span>Results Found: <strong>${data.length}</strong></span>
        </div>
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export JSON
        </button>
      </div>

      <div class="sync-cards">
        ${data.map(item => {
          const key = item.key;
          //  remove three dots from the end of the value_preview if present
          const cleanedValuePreview = item.value_preview.replace(/\.\.\.$/, '');
          const timestamp = new Date(cleanedValuePreview).toLocaleString();
          console.log("Sync timestamp:", timestamp);
          const now = new Date();
          const syncTime = cleanedValuePreview ? new Date(cleanedValuePreview) : null;

          let status = 'unknown';
          let timeSinceSync = 'N/A';
          
          if (syncTime) {
            const diffMs = now - syncTime;
            const diffHrs = diffMs / (1000 * 60 * 60);
            
            if (diffHrs < 1) {
              status = 'success';
              timeSinceSync = `${Math.round(diffMs / (1000 * 60))} minutes ago`;
            } else if (diffHrs < 24) {
              status = 'warning';
              timeSinceSync = `${Math.round(diffHrs)} hours ago`;
            } else {
              status = 'error';
              timeSinceSync = `${Math.round(diffHrs / 24)} days ago`;
            }
          }
          
          return `
            <div class="sync-card ${status}">
              <div class="sync-header">
                <h4>${key.replace(/sync:|_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h4>
                <div class="sync-status-dot"></div>
              </div>
              <div class="sync-body">
                <div class="sync-info">
                  <div class="sync-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"></circle>
                      <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <span>Last Sync: <strong>${timestamp}</strong></span>
                  </div>
                  <div class="sync-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M23 12a11 11 0 1 1-22 0 11 11 0 0 1 22 0z"></path>
                      <path d="M15 9l-6 6"></path>
                      <path d="M9 9l6 6"></path>
                    </svg>
                    <span>Time Since: <strong>${timeSinceSync}</strong></span>
                  </div>
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
    `;
  };

  // Method for displaying generic data
  _getGenericDataHTML = (data) => {
    if (!data || data.length === 0) {
      return this._getEmptyStateHTML();
    }

    return /* html */ `
    <div class="results-container">
      <div class="results-header">
        <h2 class="results-title">Cache Results</h2>
        <div class="results-meta">
          <span>Results Found: <strong>${data.length}</strong></span>
        </div>
        <button class="export-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          Export JSON
        </button>
      </div>

      <div class="generic-cards">
        ${data.map(item => {
          const valuePreview = typeof item.value_preview === 'object' 
            ? JSON.stringify(item.value_preview, null, 2).substring(0, 200) + (JSON.stringify(item.value_preview, null, 2).length > 200 ? '...' : '')
            : String(item.value_preview).substring(0, 200) + (String(item.value_preview).length > 200 ? '...' : '');
          
          return `
            <div class="generic-card">
              <div class="generic-card-header">
                <h4 class="generic-key">${item.key}</h4>
                <div class="ttl-badge ${item.ttl === -1 ? 'no-expiry' : ''}">${item.ttl === -1 ? 'No Expiration' : item.ttl + 's'}</div>
              </div>
              <div class="generic-card-body">
                <pre class="value-preview">${valuePreview}</pre>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    </div>
    `;
  };

  // Helper method to format durations from seconds
  _formatDuration = (seconds) => {
    if (typeof seconds !== 'number') return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${remainingSeconds}s`;
    }
  };

  // Helper to format tab names
  getLoader() {
    return `
      <div class="loader-container">
        <div class="loader"></div>
      </div>
    `;
  }

  getStyles = () => {
    return /* css */ `
      <style>
        :host {
          display: block;
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
        }

        .search-header {
          margin-bottom: 2rem;
        }

        .search-title {
          font-size: 1.75rem;
          font-weight: 600;
          margin: 0 0 1.5rem 0;
          color: var(--title-color);
        }

        .search-form {
          margin-bottom: 2rem;
        }

        .search-input-group {
          display: flex;
          gap: 1rem;
          max-width: 500px;
        }

        .select-wrapper {
          position: relative;
          flex: 1;
        }

        .search-select {
          width: 100%;
          padding: 0.75rem 1rem;
          font-size: 1rem;
          background-color: var(--background);
          border: var(--border);
          border-radius: 0.375rem;
          color: var(--text-color);
          appearance: none;
          cursor: pointer;
        }

        .select-arrow {
          position: absolute;
          right: 1rem;
          top: 50%;
          transform: translateY(-50%);
          pointer-events: none;
          color: var(--text-color);
        }

        .search-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1.25rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: var(--action-border);
          border-radius: 0.375rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .search-btn:hover {
          background: var(--accent-linear);
        }

        .loader-container {
          display: flex;
          justify-content: center;
          align-items: center;
          height: 200px;
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

        /* Results Styles */
        .results-container {
          margin-top: 1rem;
        }

        .results-header {
          display: flex;
          flex-direction: column;
          margin-bottom: 1.5rem;
        }

        .results-title {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 1rem 0;
          color: var(--title-color);
        }

        .results-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          margin-bottom: 1rem;
          font-size: 0.875rem;
          color: var(--gray-color);
        }

        .export-btn {
          align-self: flex-start;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: var(--action-border);
          border-radius: 0.375rem;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .export-btn:hover {
          background: var(--accent-linear);
        }

        /* Tabs styling */
        .tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1.5rem;
          border-bottom: var(--border);
          padding-bottom: 0.5rem;
        }

        .tab {
          padding: 0.5rem 1rem;
          border-radius: 0.375rem;
          background: transparent;
          border: 1px solid var(--border-color);
          color: var(--text-color);
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .tab:hover {
          background: var(--stat-background);
        }

        .tab.active {
          background: var(--action-linear);
          color: var(--white-color);
          border-color: var(--accent-color);
        }

        .tab-content {
          margin-bottom: 2rem;
        }

        .hidden {
          display: none;
        }

        .section-title {
          font-size: 1.25rem;
          font-weight: 600;
          margin: 0 0 1.25rem 0;
          color: var(--title-color);
        }

        .subsection-title {
          font-size: 1.125rem;
          font-weight: 500;
          margin: 1.5rem 0 1rem 0;
          color: var(--title-color);
        }

        /* Product cards */
        .product-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1.5rem;
        }

        .product-card {
          padding: 1.25rem;
          background-color: var(--background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          transition: transform 0.2s, box-shadow 0.2s;
          border-top: 4px solid var(--accent-color);
        }

        .product-card:hover {
          transform: translateY(-2px);
          box-shadow: var(--hover-box-shadow);
        }

        .product-name {
          font-size: 1.125rem;
          font-weight: 600;
          margin: 0 0 1rem 0;
          color: var(--title-color);
          border-bottom: var(--border);
          padding-bottom: 0.75rem;
        }

        .product-rates {
          display: flex;
          flex-wrap: wrap;
          gap: 1.5rem;
          margin-bottom: 1.25rem;
        }

        .rate-group {
          flex: 1;
          min-width: 120px;
        }

        .rate-group h5 {
          font-size: 0.875rem;
          font-weight: 600;
          margin: 0 0 0.75rem 0;
          color: var(--gray-color);
          text-transform: uppercase;
        }

        .rate-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
        }

        .rate {
          font-weight: 600;
          color: var(--accent-color);
        }

        .extras h5 {
          font-size: 0.875rem;
          font-weight: 600;
          margin: 0 0 0.75rem 0;
          color: var(--gray-color);
          text-transform: uppercase;
          border-top: var(--border);
          padding-top: 0.75rem;
        }

        .extras-items {
                   display: grid;
          grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          gap: 0.5rem;
        }

        .extra-item {
          display: flex;
          flex-direction: column;
          font-size: 0.8125rem;
        }

        .price {
          font-weight: 600;
          color: var(--text-color);
        }

        /* Maps styles */
        .route-info {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .route-info div {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }

        .route-info svg {
          opacity: 0.7;
          flex-shrink: 0;
        }
        
        .route-info strong {
          display: inline-block;
          min-width: 3.5rem;
        }

        .route-key {
          margin-top: 0.5rem;
          padding-top: 0.5rem;
          border-top: var(--border);
          opacity: 0.7;
          font-size: 0.75rem !important;
          word-break: break-all;
        }

        .branch-info, .delivery-location {
          color: var(--gray-color);
          font-size: 0.8125rem !important;
          margin-top: 0.3rem;
        }

        .branch-address {
          font-style: italic;
          font-size: 0.75rem;
          margin-left: 0.25rem;
        }

        .distance-info, .duration-info {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
        }

        .distance-value, .duration-value {
          font-weight: 600;
          color: var(--accent-color);
        }

        .distance-unit, .traffic-model {
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        .maps-distance-table {
          overflow-x: auto;
        }

        .ttl-badge {
          display: inline-block;
          padding: 0.25rem 0.5rem;
          border-radius: 1rem;
          font-size: 0.75rem;
          background-color: var(--accent-color);
          color: white;
        }

        .ttl-badge.no-expiry {
          background-color: var(--gray-color);
        }

        .details-row {
          background-color: var(--stat-background);
        }
        
        /* Additional styles for distance table cells */
        .distance-info, .duration-info {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.25rem;
        }
        
        .duration-info {
          flex-direction: column;
          align-items: center;
        }
        
        .distance-value, .duration-value {
          font-weight: 600;
        }
        
        .distance-unit, .traffic-model {
          color: var(--gray-color);
          font-size: 0.8rem;
        }

        .route-details {
          padding: 0.75rem 1rem;
          font-size: 0.8125rem;
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .detail-item {
          flex: 1;
          min-width: 200px;
        }

        .leg-detail {
          padding-left: 1rem;
          margin-top: 0.25rem;
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        /* Generators table */
        .generators-table {
          overflow-x: auto;
        }

        table {
          width: 100%;
          border-collapse: collapse;
        }

        th {
          background-color: var(--stat-background);
          color: var(--title-color);
          font-weight: 600;
          text-align: left;
          padding: 0.75rem 1rem;
          font-size: 0.875rem;
        }
        
        /* Center alignment for specific columns in maps distance table */
        .maps-distance-table th:nth-child(2),
        .maps-distance-table th:nth-child(3),
        .maps-distance-table th:nth-child(4) {
          text-align: center;
        }
        
        .maps-distance-table td:nth-child(2),
        .maps-distance-table td:nth-child(3),
        .maps-distance-table td:nth-child(4) {
          text-align: center;
        }

        td {
          padding: 0.75rem 1rem;
          border-bottom: var(--border);
        }

        tr:last-child td {
          border-bottom: none;
        }

        .na-text {
          color: var(--gray-color);
          font-style: italic;
        }

        /* Delivery styles */
        .delivery-info {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }

        .info-card {
          flex: 1;
          min-width: 200px;
          padding: 1.25rem;
          background-color: var(--background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          text-align: center;
        }

        .info-card h4 {
          font-size: 1rem;
          font-weight: 500;
          margin: 0 0 0.5rem 0;
          color: var(--text-color);
        }

        .info-card .price,
        .info-card .highlight {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          color: var(--accent-color);
        }

        .delivery-rates {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1rem;
        }

        .rate-card {
          padding: 1rem;
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          text-align: center;
        }

        .rate-card .region {
          font-size: 0.875rem;
          font-weight: 500;
          margin: 0 0 0.375rem 0;
          color: var(--text-color);
        }

        .rate-card .rate {
          font-size: 1.125rem;
          font-weight: 600;
          margin: 0;
          color: var(--accent-color);
        }

        /* Generic card styles */
        .generic-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
          gap: 1.25rem;
          margin-top: 1.5rem;
        }

        .generic-card {
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          overflow: hidden;
          transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        }

        .generic-card:hover {
          transform: translateY(-3px);
          box-shadow: var(--box-shadow-hover);
        }

        .generic-card-header {
          padding: 1rem;
          background-color: var(--background);
          border-bottom: var(--border);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .generic-key {
          margin: 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--title-color);
          word-break: break-all;
        }

        .ttl-badge {
          font-size: 0.75rem;
          padding: 0.25rem 0.5rem;
          border-radius: 2rem;
          background-color: var(--accent-color);
          color: var(--background);
          font-weight: 500;
        }

        .ttl-badge.no-expiry {
          background-color: var(--gray-color);
        }

        .generic-card-body {
          padding: 1rem;
        }

        .value-preview {
          margin: 0;
          font-size: 0.85rem;
          color: var(--text-color);
          white-space: pre-wrap;
          word-break: break-all;
          max-height: 200px;
          overflow-y: auto;
          background-color: #f7f8fa;
          padding: 0.75rem;
          border-radius: 0.375rem;
        }
        
        /* All Pricing Data styles */
        .pricing-data-container {
          margin-top: 1.5rem;
        }
        
        .catalog-preview {
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          padding: 1.5rem;
          margin-bottom: 2rem;
          box-shadow: var(--box-shadow);
        }
        
        .catalog-info {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1rem;
          margin-top: 1rem;
          margin-bottom: 1.5rem;
        }
        
        /* Pricing Tabs Navigation */
        .pricing-tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1.5rem;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 0.5rem;
        }
        
        .pricing-tab {
          background-color: var(--background);
          border: 1px solid var(--border-color);
          border-radius: 0.375rem;
          padding: 0.5rem 1rem;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-color);
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .pricing-tab:hover {
          background-color: var(--stat-background);
        }
        
        .pricing-tab.active {
          background-color: var(--accent-color);
          color: white;
          border-color: var(--accent-color);
        }
        
        .pricing-tab-content {
          display: none;
        }
        
        .pricing-tab-content.active {
          display: block;
        }
        
        .info-box {
          background-color: var(--background);
          border-radius: 0.5rem;
          padding: 1rem;
          text-align: center;
          border: var(--border);
          transition: transform 0.2s;
        }
        
        .info-box:hover {
          transform: translateY(-3px);
        }
        
        .info-box h4 {
          margin: 0 0 0.5rem 0;
          font-size: 0.9rem;
          color: var(--gray-color);
        }
        
        .info-box p {
          margin: 0;
          font-size: 1.5rem;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .current-seasonal-info {
          background-color: var(--background);
          border-radius: 0.5rem;
          padding: 1rem;
          border: var(--border);
        }
        
        .current-seasonal-info h4 {
          margin: 0 0 1rem 0;
          font-size: 1rem;
          color: var(--title-color);
          text-align: center;
        }
        
        .current-tier {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        
        .tier-name {
          margin: 0 0 0.25rem 0;
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--accent-color);
        }
        
        .tier-rate {
          margin: 0 0 0.25rem 0;
          font-size: 1.1rem;
          font-weight: 500;
        }
        
        .tier-dates {
          margin: 0;
          font-size: 0.9rem;
          color: var(--gray-color);
        }
        
        .pricing-entries-section {
          margin-top: 2rem;
        }
        
        .pricing-entries {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        
        .pricing-entry {
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          box-shadow: var(--box-shadow);
          overflow: hidden;
          transition: all 0.3s;
          border: 1px solid var(--border-color);
          position: relative;
        }
        
        .pricing-entry:hover {
          transform: translateY(-3px);
          box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        .entry-header {
          padding: 1rem 1.25rem;
          background-color: var(--background);
          border-bottom: var(--border);
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
          align-items: center;
          gap: 0.75rem;
        }
        
        .entry-type {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
          background-color: rgba(var(--accent-color-rgb), 0.1);
          padding: 0.3rem 0.6rem;
          border-radius: 1rem;
          align-self: flex-start;
        }
        
        .entry-type svg {
          color: var(--accent-color);
        }
        
        .entry-type span {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--accent-color);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .entry-key {
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
          word-break: break-all;
          flex: 1;
        }
        
        .entry-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
          font-size: 0.8rem;
        }
        
        .entry-ttl {
          background-color: var(--accent-color);
          color: white;
          padding: 0.25rem 0.5rem;
          border-radius: 2rem;
        }
        
        .entry-ttl.no-expiry {
          background-color: var(--gray-color);
        }
        
        .entry-timestamp {
          color: var(--gray-color);
        }
        
        .entry-content {
          padding: 1.5rem;
          max-height: 800px;
          overflow-y: auto;
          border-top: 1px solid var(--border-color);
          opacity: 1;
        }
        
        .quick-info {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          background-color: var(--background);
          padding: 1rem;
          border-radius: 0.375rem;
          border: 1px solid var(--border-color);
        }
        
        .info-row {
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
          font-size: 0.9rem;
          padding-bottom: 0.5rem;
          border-bottom: 1px dashed rgba(var(--border-color-rgb), 0.5);
        }
        
        .info-row:last-child {
          border-bottom: none;
          padding-bottom: 0;
        }
        
        .info-row strong {
          font-weight: 600;
          color: var(--text-color);
          min-width: 120px;
        }
        
        .json-preview {
          margin: 0;
          font-size: 0.85rem;
          font-family: monospace;
          white-space: pre-wrap;
          word-break: break-all;
          background-color: #f7f8fa;
          padding: 1rem;
          border-radius: 0.375rem;
          overflow-x: auto;
        }
        
        /* Product price styling */
        .full-product-info {
          margin-top: 1.5rem;
        }
        
        .rates-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
          margin: 1rem 0;
        }
        
        .rate-section {
          background-color: var(--background);
          border: 1px solid var(--border-color);
          border-radius: 0.375rem;
          padding: 1rem;
        }
        
        .rate-section h5 {
          margin: 0 0 1rem 0;
          font-size: 0.95rem;
          color: var(--accent-color);
          padding-bottom: 0.5rem;
          border-bottom: 1px solid var(--border-color);
        }
        
        .rate-item {
          display: flex;
          justify-content: space-between;
          padding: 0.5rem 0;
          font-size: 0.9rem;
          border-bottom: 1px dashed rgba(var(--border-color-rgb), 0.3);
        }
        
        .rate-item:last-child {
          border-bottom: none;
        }
        
        .extras-section {
          margin-top: 1.5rem;
        }
        
        .extras-section h5 {
          margin: 0 0 1rem 0;
          font-size: 0.95rem;
          color: var(--accent-color);
        }
        
        .extras-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 1rem;
        }
        
        .extra-item {
          background-color: var(--background);
          border: 1px solid var(--border-color);
          border-radius: 0.375rem;
          padding: 0.75rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.85rem;
        }
        
        .extra-item .price {
          font-weight: 600;
          color: var(--accent-color);
        }
        
        /* Maps Cache Counters styles */
        .maps-cache-overview {
          display: flex;
          flex-wrap: wrap;
          gap: 1.5rem;
          margin-bottom: 2rem;
        }
        
        .hit-rate-card {
          flex: 1;
          min-width: 250px;
          background-color: var(--background);
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: var(--box-shadow);
          text-align: center;
          border: 1px solid var(--border-color);
        }
        
        .hit-rate-title {
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
          color: var(--title-color);
        }
        
        .hit-rate-value {
          font-size: 3rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
        }
        
        .hit-rate-value.high {
          color: var(--success-color);
        }
        
        .hit-rate-value.medium {
          color: var(--warning-color, #f6b93b);
        }
        
        .hit-rate-value.low {
          color: var(--error-color);
        }
        
        .hit-rate-detail {
          font-size: 0.9rem;
          color: var(--gray-color);
        }
        
        .maps-counters {
          flex: 2;
          min-width: 300px;
          display: flex;
          flex-wrap: wrap;
          gap: 1rem;
        }
        
        .maps-counters .counter-card {
          flex: 1;
          min-width: 150px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        
        .maps-counters .counter-card .counter-name {
          font-weight: 600;
          font-size: 1rem;
          margin: 0 0 0.5rem 0;
          color: var(--title-color);
        }
        
        .counter-percentage {
          font-size: 1rem;
          font-weight: 500;
          margin: 0 0 0.75rem 0;
        }
        
        .counter-bar {
          width: 100%;
          height: 8px;
          background-color: rgba(0, 0, 0, 0.1);
          border-radius: 4px;
          overflow: hidden;
          margin-top: 0.5rem;
        }
        
        .counter-bar-fill {
          height: 100%;
          border-radius: 4px;
        }
        
        .hits .counter-bar-fill {
          background-color: var(--success-color);
        }
        
        .misses .counter-bar-fill {
          background-color: var(--error-color);
        }
        
        .maps-counters-explainer {
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          padding: 1.5rem;
          margin-top: 1rem;
        }
        
        .maps-counters-explainer h3 {
          margin: 0 0 0.75rem 0;
          font-size: 1.1rem;
          color: var(--title-color);
        }
        
        .maps-counters-explainer p {
          margin: 0 0 1rem 0;
          font-size: 0.95rem;
          color: var(--text-color);
          line-height: 1.5;
        }
        
        .optimization-tips h4 {
          margin: 0 0 0.5rem 0;
          font-size: 0.95rem;
          color: var(--accent-color);
        }
        
        .optimization-tips ul {
          margin: 0;
          padding-left: 1.5rem;
        }
        
        .optimization-tips li {
          margin-bottom: 0.3rem;
          font-size: 0.9rem;
        }
        
        .stats-card {
          background-color: var(--background);
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: var(--box-shadow);
          text-align: center;
          max-width: 300px;
          margin: 0 auto;
          border: 1px solid var(--border-color);
        }
        
        .stats-card h3 {
          margin: 0 0 1rem 0;
          font-size: 1.1rem;
          color: var(--title-color);
        }
        
        .stat-value {
          font-size: 2.5rem;
          font-weight: 700;
          color: var(--accent-color);
          margin-bottom: 0.5rem;
        }
        
        .stat-desc {
          font-size: 0.9rem;
          color: var(--gray-color);
        }
        
        .stats-card.hit-rate {
          background: linear-gradient(145deg, var(--background), var(--stat-background));
        }
        
        .counter-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 1.5rem;
          margin-top: 1.5rem;
        }
        
        .counter-card {
          background-color: var(--background);
          border-radius: 0.5rem;
          border: 1px solid var(--border-color);
          box-shadow: var(--box-shadow);
          padding: 1.25rem;
          text-align: center;
          transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
          position: relative;
          overflow: hidden;
        }
        
        .counter-card.hits {
          border-color: rgba(var(--success-color-rgb), 0.5);
        }
        
        .counter-card.misses {
          border-color: rgba(var(--error-color-rgb), 0.5);
        }
        
        .counter-card:hover {
          transform: translateY(-3px);
          box-shadow: var(--box-shadow-hover);
        }
        
        .counter-icon {
          position: absolute;
          top: 10px;
          right: 10px;
          opacity: 0.2;
        }
        
        .counter-icon.hit {
          color: var(--success-color);
        }
        
        .counter-icon.miss {
          color: var(--error-color);
        }
        
        .counter-name {
          font-weight: 600;
          font-size: 1rem;
          margin: 0 0 0.5rem 0;
          color: var(--title-color);
        }
        
        .counter-value {
          font-size: 1.5rem;
          font-weight: 700;
          margin: 0.5rem 0;
          color: var(--accent-color);
        }
        
        .counter-card.hits .counter-value {
          color: var(--success-color);
        }
        
        .counter-card.misses .counter-value {
          color: var(--error-color);
        }
        
        .counter-key {
          font-size: 0.75rem;
          color: var(--gray-color);
          margin: 0.5rem 0 0 0;
          opacity: 0.7;
        }
      </style>
    `;
  }
}
