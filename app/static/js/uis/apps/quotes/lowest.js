export default class QuotesLowest extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/quotes/lowest";
    this.quotesData = null;
    this._loading = true;
    this._empty = false;
    this.currentPage = 1;
    this.hasMore = false;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.fetchQuotes();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchQuotes = async (page = 1) => {
    this._loading = true;
    this._empty = false;
    this.render();

    try {
      const response = await this.api.get(`${this.url}?page=${page}`, { content: "json" });

      if (response.status_code === 401) {
        this._loading = false;
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.quotesData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.quotesData = response.data;
      this.currentPage = page;
      this.hasMore = this.quotesData.total > (this.quotesData.limit * page);

      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching lowest quotes:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.quotesData = null;
      this.render();
    }
  };

  attachEventListeners = () => {
    // Pagination buttons
    const prevBtn = this.shadowObj.querySelector('.pagination-btn.prev');
    const nextBtn = this.shadowObj.querySelector('.pagination-btn.next');

    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentPage > 1) {
          this.fetchQuotes(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchQuotes(this.currentPage + 1);
        }
      });
    }

    // Expand button interactions
    const expandButtons = this.shadowObj.querySelectorAll('.expand-btn');
    expandButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const detailsId = btn.getAttribute('aria-controls');
        if (detailsId) {
          this.toggleQuoteDetails(e, detailsId);
        }
      });
    });
  };

  toggleQuoteDetails = (event, detailsId) => {
    event.preventDefault();
    event.stopPropagation();

    const button = event.target.closest('.expand-btn');
    const details = this.shadowObj.getElementById(detailsId);

    if (!button || !details) return;

    const isExpanded = button.classList.contains('expanded');

    if (isExpanded) {
      button.classList.remove('expanded');
      details.classList.remove('expanded');
      button.setAttribute('aria-expanded', 'false');
    } else {
      button.classList.add('expanded');
      details.classList.add('expanded');
      button.setAttribute('aria-expanded', 'true');
    }
  };

  formatCurrency = (amount) => {
    if (!amount && amount !== 0) return 'N/A';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return 'Invalid Date';
    }
  };

  getStatusClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed':
        return 'success';
      case 'pending':
        return 'pending';
      case 'failed':
        return 'failed';
      case 'cancelled':
        return 'cancelled';
      default:
        return 'default';
    }
  };

  getSVGIcon = (type) => {
    const icons = {
      expand: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6,9 12,15 18,9"/>
      </svg>`,
      budget: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 6v6l4 2"/>
      </svg>`,
      currency: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="1" x2="12" y2="23"/>
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
      </svg>`
    };
    return icons[type] || icons.expand;
  };

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody = () => {
    if (this._loading) {
      return /* html */ `<div class="container">${this.getLoader()}</div>`;
    }

    if (this._empty || !this.quotesData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getQuotesTable()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Lowest Value Quotes</h1>
        <p class="subtitle">Most budget-friendly quotes (lowest amounts first)</p>
      </div>
    `;
  };

  getQuotesTable = () => {
    if (!this.quotesData.items || this.quotesData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="quotes-table">
        <div class="table-header">
          <div class="header-cell">Quote</div>
          <div class="header-cell">Amount</div>
          <div class="header-cell">Product</div>
          <div class="header-cell">Status</div>
          <div class="header-cell">Actions</div>
        </div>
        <div class="table-body">
          ${this.quotesData.items.map((quote, index) => this.getQuoteRow(quote, index)).join('')}
        </div>
      </div>
    `;
  };

  getQuoteRow = (quote, index) => {
    const uniqueId = `quote-${quote.id}`;
    const budgetBadge = this.getBudgetBadge(quote.total_amount);

    return /* html */ `
      <div class="quote-row" data-quote-id="${quote.id}">
        <div class="cell quote-cell">
          <div class="quote-main">
            ${budgetBadge}
            <div class="quote-info">
              <h4 class="quote-id">Quote #${quote.id}</h4>
              <span class="quote-date">${this.formatDate(quote.created_at)}</span>
            </div>
          </div>
        </div>
        
        <div class="cell amount-cell">
          <span class="amount-value">${this.formatCurrency(quote.total_amount)}</span>
          <span class="amount-tier">${this.getValueTier(quote.total_amount)}</span>
        </div>
        
        <div class="cell product-cell">
          <span class="product-type">${quote.product_type || 'N/A'}</span>
          <span class="stall-count">${quote.stall_count || 'N/A'} stalls</span>
        </div>
        
        <div class="cell status-cell">
          <div class="status-badge ${this.getStatusClass(quote.status)}">
            ${quote.status}
          </div>
        </div>
        
        <div class="cell actions-cell">
          <button class="expand-btn" aria-expanded="false" aria-controls="${uniqueId}-details">
            <span class="expand-icon">${this.getSVGIcon('expand')}</span>
          </button>
        </div>
        
        <div class="quote-details" id="${uniqueId}-details">
          <div class="details-grid">
            <div class="detail-section">
              <h5 class="section-title">
                ${this.getSVGIcon('currency')}
                Cost Breakdown
              </h5>
              <div class="detail-items">
                ${quote.rental_cost ? `<div class="detail-item">
                  <span class="detail-label">Rental Cost:</span>
                  <span class="detail-value">${this.formatCurrency(quote.rental_cost)}</span>
                </div>` : ''}
                ${quote.delivery_cost ? `<div class="detail-item">
                  <span class="detail-label">Delivery Cost:</span>
                  <span class="detail-value">${this.formatCurrency(quote.delivery_cost)}</span>
                </div>` : ''}
                <div class="detail-item">
                  <span class="detail-label">Total Amount:</span>
                  <span class="detail-value amount-highlight">${this.formatCurrency(quote.total_amount)}</span>
                </div>
              </div>
            </div>
            
            <div class="detail-section">
              <h5 class="section-title">Quote Details</h5>
              <div class="detail-items">
                <div class="detail-item">
                  <span class="detail-label">Duration:</span>
                  <span class="detail-value">${quote.rental_duration_days || 'N/A'} days</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Stall Count:</span>
                  <span class="detail-value">${quote.stall_count || 'N/A'}</span>
                </div>
                ${quote.delivery_location ? `<div class="detail-item">
                  <span class="detail-label">Location:</span>
                  <span class="detail-value">${quote.delivery_location}</span>
                </div>` : ''}
                ${quote.processing_time_ms ? `<div class="detail-item">
                  <span class="detail-label">Processing Time:</span>
                  <span class="detail-value">${quote.processing_time_ms}ms</span>
                </div>` : ''}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getBudgetBadge = (amount) => {
    if (!amount) return '';

    if (amount <= 1000) {
      return /* html */ `
        <div class="budget-badge economy">
          ${this.getSVGIcon('budget')}
          <span class="budget-text">Economy</span>
        </div>
      `;
    } else if (amount <= 2000) {
      return /* html */ `
        <div class="budget-badge budget">
          ${this.getSVGIcon('budget')}
          <span class="budget-text">Budget</span>
        </div>
      `;
    }

    return '';
  };

  getValueTier = (amount) => {
    if (!amount) return 'Unknown';
    if (amount <= 500) return 'Economy';
    if (amount <= 1000) return 'Budget';
    if (amount <= 2500) return 'Basic';
    return 'Standard';
  };

  getPagination = () => {
    if (!this.quotesData || this.quotesData.total <= this.quotesData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.quotesData.total / this.quotesData.limit)}
        </span>
        <button class="pagination-btn next ${!this.hasMore ? 'disabled' : ''}" 
                ${!this.hasMore ? 'disabled' : ''}>
          Next
        </button>
      </div>
    `;
  };

  getLoader() {
    return /* html */ `
      <div class="loader-container">
        <div class="loader"></div>
      </div>
    `;
  }

  getEmptyMessage = () => {
    return /* html */ `
      <div class="empty-state">
        <h2>No Budget-Friendly Quotes</h2>
        <p>There are no low-value quotes to display at this time.</p>
      </div>
    `;
  };

  getStyles = () => {
    return /* html */ `
      <style>
        :host {
          display: block;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }

        .container {
          padding: 24px;
          background: var(--background);
          color: var(--text-color);
          border-radius: 8px;
          max-width: 100%;
        }

        .header {
          margin-bottom: 24px;
          padding-bottom: 16px;
          border-bottom: var(--border);
        }

        .header h1 {
          font-size: 24px;
          font-weight: 600;
          color: var(--title-color);
          margin: 0 0 8px 0;
        }

        .subtitle {
          font-size: 14px;
          color: var(--gray-color);
          margin: 0;
        }

        .quotes-table {
          background: var(--background);
          border-radius: 8px;
          border: 1px solid var(--border-color);
          overflow: hidden;
          margin-bottom: 20px;
        }

        .table-header {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr auto;
          gap: 16px;
          background: var(--gray-background);
          padding: 16px;
          border-bottom: var(--border);
        }

        .header-cell {
          font-weight: 600;
          color: var(--title-color);
          font-size: 14px;
        }

        .table-body {
          display: flex;
          flex-direction: column;
        }

        .quote-row {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr 1fr auto;
          gap: 16px;
          padding: 16px;
          border-bottom: var(--border);
          transition: background-color 0.2s ease;
        }

        .quote-row:hover {
          background: var(--gray-background);
        }

        .quote-row:last-child {
          border-bottom: none;
        }

        .cell {
          display: flex;
          align-items: center;
        }

        .quote-cell {
          flex-direction: column;
          align-items: flex-start;
        }

        .quote-main {
          display: flex;
          align-items: center;
          gap: 12px;
          width: 100%;
        }

        .quote-info {
          flex: 1;
        }

        .quote-id {
          font-size: 14px;
          font-weight: 600;
          color: var(--title-color);
          margin: 0 0 4px 0;
        }

        .quote-date {
          font-size: 12px;
          color: var(--gray-color);
        }

        .amount-cell {
          flex-direction: column;
          align-items: flex-start;
        }

        .amount-value {
          font-size: 16px;
          font-weight: 600;
          color: var(--success-color);
          margin-bottom: 4px;
        }

        .amount-tier {
          font-size: 11px;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .product-cell {
          flex-direction: column;
          align-items: flex-start;
        }

        .product-type {
          font-size: 14px;
          color: var(--text-color);
          font-weight: 500;
          margin-bottom: 4px;
        }

        .stall-count {
          font-size: 12px;
          color: var(--gray-color);
        }

        .status-cell {
          justify-content: center;
        }

        .status-badge {
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          text-transform: capitalize;
        }

        .status-badge.success {
          background: var(--success-color);
          color: var(--white-color);
        }

        .status-badge.pending {
          background: var(--warning-color);
          color: var(--white-color);
        }

        .status-badge.failed {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .status-badge.cancelled {
          background: var(--gray-color);
          color: var(--white-color);
        }

        .status-badge.default {
          background: var(--gray-background);
          color: var(--text-color);
          border: 1px solid var(--border-color);
        }

        .actions-cell {
          justify-content: center;
        }

        .expand-btn {
          background: none;
          border: 1px solid var(--border-color);
          cursor: pointer;
          padding: 8px;
          border-radius: 4px;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .expand-btn:hover {
          background: var(--gray-background);
          border-color: var(--accent-color);
        }

        .expand-icon {
          width: 16px;
          height: 16px;
          color: var(--gray-color);
          transition: transform 0.2s ease;
        }

        .expand-btn.expanded .expand-icon {
          transform: rotate(180deg);
        }

        .expand-btn.expanded {
          background: var(--accent-color);
          border-color: var(--accent-color);
        }

        .expand-btn.expanded .expand-icon {
          color: var(--white-color);
        }

        .budget-badge {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }

        .budget-badge.economy {
          background: var(--success-color);
          color: var(--white-color);
        }

        .budget-badge.budget {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .budget-badge .icon {
          width: 12px;
          height: 12px;
        }

        .budget-text {
          font-weight: 600;
        }

        .quote-details {
          display: none;
          grid-column: 1 / -1;
          margin-top: 16px;
          padding: 20px;
          background: var(--gray-background);
          border-radius: 6px;
          border: 1px solid var(--border-color);
        }

        .quote-details.expanded {
          display: block;
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 20px;
        }

        .detail-section {
          background: var(--background);
          border-radius: 6px;
          padding: 16px;
          border: 1px solid var(--border-color);
        }

        .section-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          color: var(--title-color);
          font-size: 14px;
          margin: 0 0 12px 0;
        }

        .section-title .icon {
          width: 16px;
          height: 16px;
          color: var(--accent-color);
        }

        .detail-items {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .detail-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .detail-label {
          font-size: 12px;
          color: var(--gray-color);
          font-weight: 500;
        }

        .detail-value {
          font-size: 14px;
          color: var(--text-color);
          font-weight: 500;
        }

        .amount-highlight {
          color: var(--success-color);
          font-weight: 600;
        }

        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 16px;
          margin-top: 24px;
        }

        .pagination-btn {
          padding: 8px 16px;
          border: 1px solid var(--border-color);
          background: var(--background);
          color: var(--text-color);
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          transition: all 0.2s ease;
        }

        .pagination-btn:hover:not(.disabled) {
          background: var(--accent-color);
          color: var(--white-color);
          border-color: var(--accent-color);
        }

        .pagination-btn.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .pagination-info {
          font-size: 14px;
          color: var(--text-color);
          font-weight: 500;
        }

        .icon {
          width: 16px;
          height: 16px;
          fill: currentColor;
        }

        .loader-container {
          display: flex;
          justify-content: center;
          align-items: center;
          padding: 60px 20px;
        }

        .loader {
          width: 40px;
          height: 40px;
          border: 3px solid var(--border-color);
          border-top: 3px solid var(--accent-color);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .empty-state {
          text-align: center;
          padding: 60px 20px;
          color: var(--gray-color);
        }

        .empty-state h2 {
          margin: 0 0 8px 0;
          color: var(--title-color);
          font-size: 18px;
          font-weight: 600;
        }

        .empty-state p {
          margin: 0;
          font-size: 14px;
          line-height: 1.5;
        }

        /* Mobile Responsive */
        @media (max-width: 768px) {
          .container {
            padding: 16px;
          }

          .table-header,
          .quote-row {
            grid-template-columns: 1fr;
            gap: 12px;
          }

          .header-cell {
            display: none;
          }

          .cell {
            border-bottom: var(--border);
            padding-bottom: 8px;
          }

          .cell:last-child {
            border-bottom: none;
          }

          .quote-details {
            margin-top: 12px;
            padding: 16px;
          }

          .details-grid {
            grid-template-columns: 1fr;
            gap: 16px;
          }
        }
      </style>
    `;
  };
}
