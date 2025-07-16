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
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching lowest value quotes:", error);
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

    // Quote cards click handlers
    const quoteCards = this.shadowObj.querySelectorAll('.quote-card');
    quoteCards.forEach(card => {
      card.addEventListener('click', () => {
        const quoteId = card.dataset.quoteId;
        console.log(`Quote clicked: ${quoteId}`);
        // Add navigation or detail view logic here
      });
    });
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
      return dateString;
    }
  };

  getStatusClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'completed': return 'status-success';
      case 'failed': return 'status-error';
      case 'expired': return 'status-warning';
      case 'processing': return 'status-processing';
      default: return 'status-pending';
    }
  };

  getValueTier = (amount) => {
    if (!amount) return 'minimal';
    if (amount <= 500) return 'minimal';
    if (amount <= 1000) return 'low';
    if (amount <= 2000) return 'budget';
    return 'standard';
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
        ${this.getQuotesList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Lowest Value Quotes</h1>
        <p class="subtitle">Quotes ordered by total amount (lowest first)</p>
      </div>
    `;
  };

  getQuotesList = () => {
    if (!this.quotesData.items || this.quotesData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="quotes-grid">
        ${this.quotesData.items.map(quote => this.getQuoteCard(quote)).join('')}
      </div>
    `;
  };

  getQuoteCard = (quote) => {
    const tierClass = this.getValueTier(quote.total_amount);

    return /* html */ `
      <div class="quote-card ${tierClass}" data-quote-id="${quote.id}" tabindex="0">
        <div class="quote-header">
          <div class="quote-id">
            <span class="label">Quote ID:</span>
            <span class="value">${quote.id}</span>
          </div>
          <div class="quote-status ${this.getStatusClass(quote.status)}">
            ${quote.status}
          </div>
        </div>
        
        <div class="quote-details">
          <div class="detail-row featured">
            <div class="detail-item featured-amount">
              <span class="detail-label">Total Amount</span>
              <span class="detail-value amount budget">${this.formatCurrency(quote.total_amount)}</span>
              ${quote.total_amount <= 500 ? '<span class="value-badge minimal">Budget Friendly</span>' : ''}
            </div>
            <div class="detail-item">
              <span class="detail-label">Product</span>
              <span class="detail-value">${quote.product_type || 'N/A'}</span>
            </div>
          </div>
          
          ${(quote.rental_cost || quote.delivery_cost) ? /* html */ `
            <div class="amount-breakdown">
              ${quote.rental_cost ? /* html */ `
                <div class="breakdown-item">
                  <span class="breakdown-label">Rental:</span>
                  <span class="breakdown-value">${this.formatCurrency(quote.rental_cost)}</span>
                </div>
              ` : ''}
              ${quote.delivery_cost ? /* html */ `
                <div class="breakdown-item">
                  <span class="breakdown-label">Delivery:</span>
                  <span class="breakdown-value">${this.formatCurrency(quote.delivery_cost)}</span>
                </div>
              ` : ''}
            </div>
          ` : ''}
          
          <div class="detail-row">
            <div class="detail-item">
              <span class="detail-label">Duration</span>
              <span class="detail-value">${quote.rental_duration_days || 'N/A'} days</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Stalls</span>
              <span class="detail-value">${quote.stall_count || 'N/A'}</span>
            </div>
          </div>
          
          ${quote.delivery_location ? /* html */ `
            <div class="detail-row full-width">
              <div class="detail-item">
                <span class="detail-label">Location</span>
                <span class="detail-value location">${quote.delivery_location}</span>
              </div>
            </div>
          ` : ''}
          
          <div class="quote-footer">
            <span class="timestamp">Created: ${this.formatDate(quote.created_at)}</span>
            ${quote.processing_time_ms ? /* html */ `
              <span class="processing-time">${quote.processing_time_ms}ms</span>
            ` : ''}
          </div>
        </div>
      </div>
    `;
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
        <h2>No Budget Quotes</h2>
        <p>There are no budget-friendly quotes to display at this time.</p>
      </div>
    `;
  };

  getStyles = () => {
    return /* html */ `
      <style>
        :host {
          display: block;
          width: 100%;
          background-color: var(--background);
          font-family: var(--font-text), sans-serif;
          line-height: 1.6;
          color: var(--text-color);
        }

        * {
          box-sizing: border-box;
        }

        .container {
          max-width: 100%;
          margin: 0 auto;
          padding: 20px 10px;
          position: relative;
          display: flex;
          flex-direction: column;
          height: max-content;
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

        .loader-container {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          min-height: 200px;
          min-width: 100%;
        }

        .loader {
          width: 20px;
          aspect-ratio: 1;
          border-radius: 50%;
          background: var(--accent-linear);
          display: grid;
          animation: l22-0 2s infinite linear;
        }

        .loader:before {
          content: "";
          grid-area: 1/1;
          margin: 15%;
          border-radius: 50%;
          background: var(--second-linear);
          transform: rotate(0deg) translate(150%);
          animation: l22 1s infinite;
        }

        .loader:after {
          content: "";
          grid-area: 1/1;
          margin: 15%;
          border-radius: 50%;
          background: var(--accent-linear);
          transform: rotate(0deg) translate(150%);
          animation: l22 1s infinite;
          animation-delay: -0.5s;
        }

        @keyframes l22-0 {
          100% { transform: rotate(1turn); }
        }

        @keyframes l22 {
          100% { transform: rotate(1turn) translate(150%); }
        }

        .quotes-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        @media (max-width: 768px) {
          .quotes-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
          }
        }

        .quote-card {
          background-color: var(--stat-background);
          border-radius: 12px;
          padding: 1.5rem;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          cursor: pointer;
          position: relative;
          overflow: hidden;
          border: var(--border);
        }

        .quote-card.minimal {
          border-left: 4px solid var(--success-color);
          background: linear-gradient(135deg, var(--stat-background) 0%, rgba(16, 185, 129, 0.05) 100%);
        }

        .quote-card.low {
          border-left: 3px solid #10b981;
          background: linear-gradient(135deg, var(--stat-background) 0%, rgba(16, 185, 129, 0.03) 100%);
        }

        .quote-card.budget {
          border-left: 2px solid #6ee7b7;
        }

        .quote-card:hover {
          transform: translateY(-5px);
          box-shadow: var(--card-box-shadow);
          background-color: var(--hover-background);
        }

        .quote-card.minimal:hover {
          background: linear-gradient(135deg, var(--hover-background) 0%, rgba(16, 185, 129, 0.08) 100%);
        }

        .quote-card:focus {
          outline: 2px solid var(--accent-color);
          outline-offset: 2px;
        }

        .quote-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
          padding-bottom: 0.75rem;
          border-bottom: var(--border);
        }

        .quote-id {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .quote-id .label {
          font-size: 0.75rem;
          color: var(--gray-color);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .quote-id .value {
          font-family: var(--font-mono);
          font-size: 0.875rem;
          color: var(--title-color);
          font-weight: 600;
        }

        .quote-status {
          padding: 0.25rem 0.75rem;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .status-success {
          background-color: rgba(16, 185, 129, 0.1);
          color: var(--success-color);
        }

        .status-error {
          background-color: rgba(239, 68, 68, 0.1);
          color: var(--error-color);
        }

        .status-warning {
          background-color: rgba(245, 158, 11, 0.1);
          color: #f59e0b;
        }

        .status-processing {
          background-color: rgba(59, 130, 246, 0.1);
          color: #3b82f6;
        }

        .status-pending {
          background-color: rgba(107, 114, 128, 0.1);
          color: var(--gray-color);
        }

        .quote-details {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .detail-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 1rem;
        }

        .detail-row.featured {
          grid-template-columns: 2fr 1fr;
          margin-bottom: 0.5rem;
        }

        .detail-row.full-width {
          grid-template-columns: 1fr;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .detail-item.featured-amount {
          background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(16, 185, 129, 0.1) 100%);
          padding: 1rem;
          border-radius: 8px;
          border-left: 4px solid var(--success-color);
          position: relative;
        }

        .detail-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          font-weight: 500;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .detail-value {
          font-size: 0.875rem;
          color: var(--title-color);
          font-weight: 600;
        }

        .detail-value.amount {
          font-size: 1.125rem;
          color: var(--success-color);
          font-weight: 700;
        }

        .detail-value.amount.budget {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--success-color);
        }

        .detail-value.location {
          font-size: 0.8rem;
          line-height: 1.3;
          color: var(--text-color);
          font-weight: 400;
        }

        .value-badge {
          position: absolute;
          top: 0.5rem;
          right: 0.5rem;
          padding: 0.125rem 0.5rem;
          border-radius: 12px;
          font-size: 0.625rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .value-badge.minimal {
          background: rgba(16, 185, 129, 0.15);
          color: var(--success-color);
        }

        .amount-breakdown {
          display: flex;
          gap: 1rem;
          background-color: rgba(16, 185, 129, 0.05);
          padding: 0.75rem;
          border-radius: 6px;
          margin: 0.5rem 0;
          border-left: 2px solid rgba(16, 185, 129, 0.3);
        }

        .breakdown-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.8rem;
        }

        .breakdown-label {
          color: var(--gray-color);
          font-weight: 500;
        }

        .breakdown-value {
          color: var(--success-color);
          font-weight: 600;
        }

        .quote-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1rem;
          padding-top: 0.75rem;
          border-top: var(--border);
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        .processing-time {
          font-family: var(--font-mono);
          background-color: rgba(107, 114, 128, 0.1);
          padding: 0.125rem 0.375rem;
          border-radius: 4px;
        }

        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 1rem;
          margin-top: 2rem;
        }

        .pagination-btn {
          padding: 0.5rem 1rem;
          border: var(--border-button);
          background-color: var(--stat-background);
          color: var(--text-color);
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.875rem;
          font-weight: 500;
          transition: all 0.2s ease;
        }

        .pagination-btn:hover:not(.disabled) {
          background-color: var(--accent-color);
          color: var(--white-color);
          border-color: var(--accent-color);
        }

        .pagination-btn.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .pagination-info {
          font-size: 0.875rem;
          color: var(--gray-color);
          font-weight: 500;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 3rem 1rem;
          min-height: 300px;
        }

        .empty-state h2 {
          color: var(--title-color);
          margin-bottom: 0.5rem;
          font-size: 1.5rem;
          font-weight: 600;
        }

        .empty-state p {
          color: var(--gray-color);
          font-size: 1rem;
          margin: 0;
        }

        @media (max-width: 480px) {
          .container {
            padding: 15px 8px;
          }

          .quote-card {
            padding: 1rem;
          }

          .detail-row {
            grid-template-columns: 1fr;
            gap: 0.75rem;
          }

          .detail-row.featured {
            grid-template-columns: 1fr;
          }

          .quote-header {
            flex-direction: column;
            gap: 0.75rem;
            align-items: flex-start;
          }

          .amount-breakdown {
            flex-direction: column;
            gap: 0.5rem;
          }
        }
      </style>
    `;
  };
}
