export default class SheetProducts extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/sheet/products";
    this.productsData = null;
    this._block = false;
    this._empty = false;
    this._loading = true;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch products data first
    this.fetchProductsData();
    window.addEventListener("scroll", this.handleScroll);

    // Add click event listener for document to handle toggle extras
    this.shadowObj.addEventListener("click", this._handleExtrasToggle);

    // Set up other event listeners after initial render
    setTimeout(() => {
      this._setupEventListeners();
    }, 100);
  }

  disconnectedCallback() {
    window.removeEventListener("scroll", this.handleScroll);
    this.shadowObj.removeEventListener("click", this._handleExtrasToggle);
  }

  // Fetch products data using the API
  fetchProductsData = async () => {
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
        console.log("Authentication required for products access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.productsData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;

      // Log data structure to help debug inconsistencies
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.includes('dev')) {
        console.log('Products data structure:', response.data);
      }

      this.productsData = response;
      this.render();

    } catch (error) {
      console.error("Error fetching products data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for products access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.productsData = null;
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
        this.fetchProductsData();
      });
    }
  };

  handleScroll = () => {
    // Event handling for scroll if needed
  };

  // Toggle extras visibility when clicking the view extras button
  _handleExtrasToggle = (event) => {
    const extrasBtn = event.target.closest('.extras-btn');
    if (!extrasBtn) return;

    const productId = extrasBtn.dataset.productId;
    const extrasContainer = this.shadowObj.querySelector(`.extras-container[data-product-id="${productId}"]`);

    if (extrasContainer) {
      // Toggle the active class to show/hide the extras
      extrasContainer.classList.toggle('active');
      extrasBtn.classList.toggle('active');

      // Update button text and icon
      const span = extrasBtn.querySelector('span');
      const svg = extrasBtn.querySelector('svg polyline');

      if (extrasContainer.classList.contains('active')) {
        span.textContent = 'Hide Extras';
        svg.setAttribute('points', '18 15 12 9 6 15'); // Up arrow
      } else {
        span.textContent = 'View Extras';
        svg.setAttribute('points', '9 18 15 12 9 6'); // Right arrow
      }
    }
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
    if (!this.productsData || !this.productsData.data || !this.productsData.data.data) {
      console.error('No data available to export');
      return;
    }

    try {
      const products = this.productsData.data.data;
      // Create CSV content
      let csvContent = 'Product,Weekly (7 Day),28 Day Rate,2-5 Month Rate,6+ Month Rate,18+ Month Rate,Standard Event,Premium Event,Premium+ Event,Platinum Event\n';

      // Add each product data row
      products.forEach(product => {
        const row = [
          `"${product.name}"`,
          product.weekly_7_day,
          product.rate_28_day,
          product.rate_2_5_month,
          product.rate_6_plus_month,
          product.rate_18_plus_month,
          product.event_standard,
          product.event_premium,
          product.event_premium_plus,
          product.event_premium_platinum
        ];
        csvContent += row.join(',') + '\n';
      });

      // Create a blob and download link
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', 'product_pricing.csv');
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
    if (this._empty || !this.productsData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show products list with actual data
    return /* html */ `
      <div class="container">
        ${this._getHeaderHTML()}
        ${this._getProductsListHTML()}
      </div>
    `;
  };

  _getHeaderHTML = () => {
    const count = this.productsData.data.count || 0;

    return /* html */ `
    <div class="products-header">
      <div class="products-title">
        <h1>Product Pricing</h1>
        <div class="products-subtitle">
          <span>${count} products available</span>
        </div>
      </div>
      <div class="products-actions">
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

  _getProductsListHTML = () => {
    const products = this.productsData.data.data || [];

    if (!products.length) {
      return /* html */ `
      <div class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="3" y1="9" x2="21" y2="9"></line>
          <line x1="9" y1="21" x2="9" y2="9"></line>
        </svg>
        <h3>No products available</h3>
        <p>There are no products data to display at this time.</p>
      </div>
      `;
    }

    return /* html */ `
    <div class="products-list">
      ${products.map(product => this._getProductItemHTML(product)).join('')}
    </div>
    `;
  };

  _getProductItemHTML = (product) => {
    return /* html */ `
    <div class="product-item">
      <div class="product-header">
        <h3 class="product-name">${product.name}</h3>
      </div>
      
      <div class="pricing-sections">
        <div class="pricing-section">
          <h4 class="section-title">Rental Rates</h4>
          <div class="pricing-grid">
            <div class="price-item">
              <span class="price-label">Weekly (7 Day)</span>
              <span class="price-value">$${product.weekly_7_day.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">28 Day Rate</span>
              <span class="price-value">$${product.rate_28_day.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">2-5 Month Rate</span>
              <span class="price-value">$${product.rate_2_5_month.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">6+ Month Rate</span>
              <span class="price-value">$${product.rate_6_plus_month.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">18+ Month Rate</span>
              <span class="price-value">$${product.rate_18_plus_month.toLocaleString()}</span>
            </div>
          </div>
        </div>

        <div class="pricing-section">
          <h4 class="section-title">Event Pricing</h4>
          <div class="pricing-grid">
            <div class="price-item">
              <span class="price-label">Standard Event</span>
              <span class="price-value">$${product.event_standard.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">Premium Event</span>
              <span class="price-value">$${product.event_premium.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">Premium+ Event</span>
              <span class="price-value">$${product.event_premium_plus.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">Platinum Event</span>
              <span class="price-value">$${product.event_premium_platinum.toLocaleString()}</span>
            </div>
            <div class="price-item">
              <span class="price-label">Other Event</span>
              <span class="price-value">${product.event_18_plus ? '$' + product.event_18_plus.toLocaleString() : 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      ${this._getExtrasHTML(product)}
    </div>
    `;
  };

  _getExtrasHTML = (product) => {
    const extras = product.extras || {};
    const extrasList = Object.entries(extras).map(([key, value]) => {
      // Format the key for display by replacing underscores with spaces and capitalizing
      const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      return `
        <div class="extra-item">
          <div class="extra-label">${formattedKey}</div>
          <div class="extra-value">$${value.toLocaleString()}</div>
        </div>
      `;
    }).join('');

    return /* html */ `
    <div class="extras-container active" data-product-id="${product.id}">
      <div class="extras-content">
        <h4 class="extras-title">Additional Services</h4>
        <div class="extras-grid">
          ${extrasList}
        </div>
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
         An error occurred while fetching the products data. Please check your connection and try again.
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
          width: 100%;
          padding: 1.5rem;
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

        /* Products Header Styles */
        .products-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .products-title h1 {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0 0 0.25rem 0;
          color: var(--title-color);
        }

        .products-subtitle {
          color: var(--gray-color);
          font-size: 0.875rem;
        }

        .products-actions {
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

        /* Products List Styles */
        .products-list {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .product-item {
          padding: 10px 0 30px;
          transition: all 0.2s ease;
          border-bottom: var(--border);
          position: relative;
          overflow: hidden;
        }

        .product-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .product-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--title-color);
          margin: 0;
          line-height: 1.3;
        }

        .pricing-sections {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
          margin-bottom: 1rem;
        }

        .pricing-section {
          border-radius: 0.5rem;
          padding: 1rem 0;
        }

        .section-title {
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
          margin: 0;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          border-bottom: var(--border);
          padding-bottom: 0.5rem;
        }

        .pricing-grid {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .price-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem 0;
          border-bottom: var(--border);
        }

        .price-label {
          font-size: 1rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .price-value {
          font-size: 1rem;
          font-weight: 600;
          color: var(--accent-color);
          font-variant-numeric: tabular-nums;
          font-feature-settings: "tnum";
        }

        .extras-btn {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: none;
          padding: 0.5rem 1rem;
          border-radius: 0.375rem;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .extras-btn:hover {
          background: var(--accent-linear);
          transform: translateY(-1px);
        }

        .extras-btn.active {
          background: var(--accent-color);
        }

        .extras-container {
          max-height: 0;
          overflow: hidden;
          transition: max-height 0.3s ease-out;
        }

        .extras-container.active {
          max-height: 500px;
          transition: max-height 0.3s ease-in;
        }

        .extras-content {
          background-color: var(--stat-background);
          border-radius: 0.5rem;
          padding: 1rem;
          margin-top: 1rem;
          border: 1px solid var(--border);
        }

        .extras-title {
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--title-color);
          margin: 0 0 1rem 0;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          border-bottom: 1px solid var(--border);
          padding-bottom: 0.5rem;
        }

        .extras-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 1rem;
        }

        .extra-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 1rem;
          background-color: var(--background);
          border-radius: 0.5rem;
          border: 1px solid var(--border);
          transition: all 0.2s ease;
        }

        .extra-item:hover {
          box-shadow: var(--box-shadow);
          transform: translateY(-2px);
        }

        .extra-label {
          font-size: 0.875rem;
          color: var(--text-color);
          font-weight: 500;
          margin-bottom: 0.5rem;
          line-height: 1.4;
        }

        .extra-value {
          font-size: 1.125rem;
          font-weight: 700;
          color: var(--accent-color);
          font-variant-numeric: tabular-nums;
          font-feature-settings: "tnum";
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
        .products-table tbody tr:nth-child(odd):not(.extras-row) {
          background-color: var(--stat-background);
        }

        .products-table tbody tr:hover:not(.extras-row) {
          background-color: var(--hover-background);
        }

        /* Responsive adjustments */
        /* Responsive adjustments */
        @media (max-width: 768px) {
          .products-header {
            flex-direction: column;
            align-items: flex-start;
          }
          
          .products-actions {
            width: 100%;
          }
          
          .export-btn {
            flex: 1;
            justify-content: center;
          }

          .pricing-sections {
            grid-template-columns: 1fr;
            gap: 1rem;
          }

          .product-header {
            flex-direction: column;
            align-items: flex-start;
          }

          .extras-btn {
            width: 100%;
            justify-content: center;
          }

          .extras-grid {
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 0.75rem;
          }

          .extra-item {
            padding: 0.75rem;
          }

          .extra-value {
            font-size: 1rem;
          }
        }

        @media (max-width: 480px) {
          .container {
            padding: 1rem;
          }

          .products-list {
            gap: 1rem;
          }

          .product-item {
            padding: 1rem;
          }

          .product-name {
            font-size: 1.125rem;
          }

          .pricing-section {
            padding: 0.75rem;
          }

          .section-title {
            font-size: 0.8125rem;
          }
        }
      </style>
    `;
  }
}
