export default class QuotesHighest extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/quotes/highest";
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
      console.error("Error fetching highest value quotes:", error);
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
    if (!amount) return 'standard';
    if (amount >= 10000) return 'premium';
    if (amount >= 5000) return 'high';
    if (amount >= 2500) return 'medium';
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
        <h1>Highest Value Quotes</h1>
        <p class="subtitle">Quotes ordered by total amount (highest first)</p>
      </div>
    `;
  };

  getQuotesList = () => {
    if (!this.quotesData.items || this.quotesData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="quotes-grid">
        ${this.quotesData.items.map((quote, index) => this.getQuoteCard(quote, index)).join('')}
      </div>
    `;
  };

  getQuoteCard = (quote, index) => {
    const tierClass = this.getValueTier(quote.total_amount);
    const rankBadge = index < 3 ? this.getRankBadge(index + 1) : '';

    return /* html */ `
      <div class="quote-card ${tierClass}" data-quote-id="${quote.id}" tabindex="0">
        ${rankBadge}
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
              <span class="detail-value amount premium">${this.formatCurrency(quote.total_amount)}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">Product</span>
              <span class="detail-value">${quote.product_type || 'N/A'}</span>
            </div>
          </div>
          
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

  getRankBadge = (rank) => {
    const badges = {
      1: { icon: '👑', text: '#1', class: 'gold' },
      2: { icon: '🥈', text: '#2', class: 'silver' },
      3: { icon: '🥉', text: '#3', class: 'bronze' }
    };

    const badge = badges[rank];
    if (!badge) return '';

    return /* html */ `
      <div class="rank-badge ${badge.class}">
        <span class="rank-icon">${badge.icon}</span>
        <span class="rank-text">${badge.text}</span>
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
        <h2>No High-Value Quotes</h2>
        <p>There are no high-value quotes to display at this time.</p>
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
          margin-bottom: 2rem;
        }

        .header h1 {
          font-size: 1.875rem;
          font-weight: 700;
          margin: 0;
          padding: 0;
          color: var(--title-color);
          line-height: 1.2;
          letter-spacing: -0.01em;
        }

        .header .subtitle {
          color: var(--gray-color);
          margin: 0.25rem 0 0;
          padding: 0;
          font-size: 0.9rem;
          opacity: 0.9;
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
          grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
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

        .quote-card.premium {
          border: 2px solid transparent;
          background: linear-gradient(var(--stat-background), var(--stat-background)) padding-box,
                      var(--accent-linear) border-box;
          box-shadow: 0 8px 32px rgba(0, 96, 223, 0.15);
        }

        .quote-card.high {
          border-left: 4px solid var(--accent-color);
          background: linear-gradient(135deg, var(--stat-background) 0%, rgba(0, 96, 223, 0.05) 100%);
        }

        .quote-card.medium {
          border-left: 3px solid var(--success-color);
          background: linear-gradient(135deg, var(--stat-background) 0%, rgba(16, 185, 129, 0.05) 100%);
        }

        .quote-card:hover {
          transform: translateY(-8px);
          box-shadow: var(--card-box-shadow);
        }

        .quote-card.premium:hover {
          transform: translateY(-10px);
          box-shadow: 0 16px 48px rgba(0, 96, 223, 0.25);
        }

        .quote-card:focus {
          outline: 2px solid var(--accent-color);
          outline-offset: 2px;
        }

        .rank-badge {
          position: absolute;
          top: -8px;
          right: 16px;
          padding: 0.5rem 0.75rem;
          border-radius: 0 0 8px 8px;
          font-size: 0.75rem;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 0.25rem;
          z-index: 2;
        }

        .rank-badge.gold {
          background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
          color: #8B4513;
          box-shadow: 0 4px 12px rgba(255, 215, 0, 0.4);
        }

        .rank-badge.silver {
          background: linear-gradient(135deg, #C0C0C0 0%, #A8A8A8 100%);
          color: #404040;
          box-shadow: 0 4px 12px rgba(192, 192, 192, 0.4);
        }

        .rank-badge.bronze {
          background: linear-gradient(135deg, #CD7F32 0%, #B8860B 100%);
          color: #FFFFFF;
          box-shadow: 0 4px 12px rgba(205, 127, 50, 0.4);
        }

        .rank-icon {
          font-size: 1rem;
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
          background: linear-gradient(135deg, rgba(0, 96, 223, 0.05) 0%, rgba(0, 96, 223, 0.1) 100%);
          padding: 1rem;
          border-radius: 8px;
          border-left: 4px solid var(--accent-color);
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
          color: var(--accent-color);
          font-weight: 700;
        }

        .detail-value.amount.premium {
          font-size: 1.5rem;
          font-weight: 800;
          background: var(--accent-linear);
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .detail-value.location {
          font-size: 0.8rem;
          line-height: 1.3;
          color: var(--text-color);
          font-weight: 400;
        }

        .amount-breakdown {
          display: flex;
          gap: 1rem;
          background-color: rgba(107, 114, 128, 0.05);
          padding: 0.75rem;
          border-radius: 6px;
          margin: 0.5rem 0;
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
          color: var(--title-color);
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

          .quotes-grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
    `;
  };
}
