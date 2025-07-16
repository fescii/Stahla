export default class HubspotContacts extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/hubspot/contacts/recent";
    this.contactsData = null;
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
    this.fetchContacts();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchContacts = async (page = 1) => {
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
        this.contactsData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.contactsData = response.data;
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching HubSpot contacts:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.contactsData = null;
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
          this.fetchContacts(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchContacts(this.currentPage + 1);
        }
      });
    }
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

    if (this._empty || !this.contactsData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getContactStats()}
        ${this.getContactsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>HubSpot Contacts</h1>
        <p class="subtitle">Recent contacts from HubSpot CRM</p>
      </div>
    `;
  };

  getContactStats = () => {
    if (!this.contactsData.items || this.contactsData.items.length === 0) {
      return '';
    }

    const stats = this.calculateContactStats(this.contactsData.items);

    return /* html */ `
      <div class="contact-stats">
        <h3>Contact Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalContacts}</span>
            <span class="stat-label">Total Contacts</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.withEmail}</span>
            <span class="stat-label">With Email</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.withPhone}</span>
            <span class="stat-label">With Phone</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.withAddress}</span>
            <span class="stat-label">With Address</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateContactStats = (contacts) => {
    const totalContacts = contacts.length;
    const withEmail = contacts.filter(c => c.properties.email).length;
    const withPhone = contacts.filter(c => c.properties.phone).length;
    const withAddress = contacts.filter(c => c.properties.address || c.properties.city).length;

    return {
      totalContacts,
      withEmail,
      withPhone,
      withAddress
    };
  };

  getContactsList = () => {
    if (!this.contactsData.items || this.contactsData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="contacts-table">
        <div class="table-header">
          <div class="header-cell name">Contact</div>
          <div class="header-cell contact-info">Contact Info</div>
          <div class="header-cell service">Service</div>
          <div class="header-cell dates">Created / Updated</div>
        </div>
        <div class="table-body">
          ${this.contactsData.items.map(contact => this.getContactRow(contact)).join('')}
        </div>
      </div>
    `;
  };

  getContactRow = (contact) => {
    const props = contact.properties;

    return /* html */ `
      <div class="contact-row" data-contact-id="${contact.id}" tabindex="0">
        <div class="cell name-cell">
          <div class="contact-name">
            <h4>${this.getFullName(props)}</h4>
            <span class="contact-id">ID: ${contact.id}</span>
          </div>
        </div>
        
        <div class="cell contact-info-cell">
          <div class="contact-details">
            ${props.email ? /* html */ `
              <div class="detail-item">
                ${this.getSVGIcon('email')}
                <span class="detail-text">${props.email}</span>
              </div>
            ` : ''}
            
            ${props.phone ? /* html */ `
              <div class="detail-item">
                ${this.getSVGIcon('phone')}
                <span class="detail-text">${props.phone}</span>
              </div>
            ` : ''}
            
            ${this.getAddressInfo(props)}
          </div>
        </div>
        
        <div class="cell service-cell">
          ${this.getServiceInfo(props)}
        </div>
        
        <div class="cell dates-cell">
          <div class="date-info">
            <div class="date-item">
              <span class="date-label">Created</span>
              <span class="date-value">${this.formatDate(contact.created_at)}</span>
            </div>
            <div class="date-item">
              <span class="date-label">Updated</span>
              <span class="date-value">${this.formatDate(contact.updated_at)}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getFullName = (props) => {
    const firstname = props.firstname || '';
    const lastname = props.lastname || '';
    const fullName = `${firstname} ${lastname}`.trim();
    return fullName || 'Unknown Contact';
  };

  getSVGIcon = (type) => {
    const icons = {
      email: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
        <polyline points="22,6 12,13 2,6"/>
      </svg>`,
      phone: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
      </svg>`,
      location: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
        <circle cx="12" cy="10" r="3"/>
      </svg>`
    };
    return icons[type] || '';
  };

  getContactInfo = (props) => {
    return /* html */ `
      <div class="contact-info">
        ${props.email ? /* html */ `
          <div class="info-item">
            ${this.getSVGIcon('email')}
            <span class="info-value">${props.email}</span>
          </div>
        ` : ''}
        
        ${props.phone ? /* html */ `
          <div class="info-item">
            ${this.getSVGIcon('phone')}
            <span class="info-value">${props.phone}</span>
          </div>
        ` : ''}
        
        ${this.getAddressInfo(props)}
      </div>
    `;
  };

  getAddressInfo = (props) => {
    const addressParts = [];
    if (props.address) addressParts.push(props.address);
    if (props.city) addressParts.push(props.city);
    if (props.state) addressParts.push(props.state);
    if (props.zip) addressParts.push(props.zip);

    const fullAddress = addressParts.join(', ');

    if (!fullAddress) return '';

    return /* html */ `
      <div class="detail-item">
        ${this.getSVGIcon('location')}
        <span class="detail-text">${fullAddress}</span>
      </div>
    `;
  };

  getServiceInfo = (props) => {
    if (!props.what_service_do_you_need_ && !props.your_message && !props.message) {
      return /* html */ `<div class="no-service">No service information</div>`;
    }

    return /* html */ `
      <div class="service-info">
        ${props.what_service_do_you_need_ ? /* html */ `
          <div class="service-type">${props.what_service_do_you_need_}</div>
        ` : ''}
        
        ${this.getServiceDetails(props)}
        
        ${props.your_message || props.message ? /* html */ `
          <div class="service-message">${this.truncateText(props.your_message || props.message, 100)}</div>
        ` : ''}
      </div>
    `;
  };

  getServiceDetails = (props) => {
    const details = [];

    if (props.how_many_restroom_stalls_) {
      details.push(`Restroom: ${props.how_many_restroom_stalls_}`);
    }
    if (props.how_many_shower_stalls_) {
      details.push(`Shower: ${props.how_many_shower_stalls_}`);
    }
    if (props.how_many_laundry_units_) {
      details.push(`Laundry: ${props.how_many_laundry_units_}`);
    }
    if (props.how_many_portable_toilet_stalls_) {
      details.push(`Portable: ${props.how_many_portable_toilet_stalls_}`);
    }

    if (details.length === 0) return '';

    return /* html */ `
      <div class="service-details">
        ${details.join(' • ')}
      </div>
    `;
  };

  truncateText = (text, maxLength) => {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  getPagination = () => {
    if (!this.contactsData || this.contactsData.total <= this.contactsData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.contactsData.total / this.contactsData.limit)}
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
        <h2>No Contacts Found</h2>
        <p>There are no HubSpot contacts to display at this time.</p>
      </div>
    `;
  };

  formatDate = (dateString) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
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
          gap: 20px;
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

        .contact-stats {
          background: var(--hubspot-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .contact-stats h3 {
          margin: 0 0 12px 0;
          color: var(--hubspot-color);
          font-size: 1.1rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 12px;
        }

        .stat-item {
          text-align: center;
          background: var(--background);
          border-radius: 6px;
          padding: 12px 8px;
        }

        .stat-count {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--hubspot-color);
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .contacts-table {
          background: var(--background);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }

        .table-header {
          display: grid;
          grid-template-columns: 1.5fr 2fr 1.5fr 1fr;
          background: var(--gray-background);
          border-bottom: 1px solid var(--border-color);
        }

        .header-cell {
          padding: 12px 16px;
          font-size: 0.8rem;
          font-weight: 600;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          border-right: 1px solid var(--border-color);
        }

        .header-cell:last-child {
          border-right: none;
        }

        .table-body {
          display: flex;
          flex-direction: column;
        }

        .contact-row {
          display: grid;
          grid-template-columns: 1.5fr 2fr 1.5fr 1fr;
          border-bottom: 1px solid var(--border-color);
          transition: background-color 0.2s ease;
          cursor: pointer;
        }

        .contact-row:last-child {
          border-bottom: none;
        }

        .contact-row:hover {
          background: var(--gray-background);
        }

        .contact-row:focus {
          outline: none;
          background: var(--hubspot-background);
        }

        .cell {
          padding: 16px;
          border-right: 1px solid var(--border-color);
          display: flex;
          flex-direction: column;
          justify-content: center;
        }

        .cell:last-child {
          border-right: none;
        }

        .name-cell .contact-name h4 {
          margin: 0 0 4px 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .contact-id {
          font-family: var(--font-mono);
          font-size: 0.7rem;
          color: var(--gray-color);
        }

        .contact-details {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .detail-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .icon {
          width: 14px;
          height: 14px;
          color: var(--hubspot-color);
          flex-shrink: 0;
        }

        .detail-text {
          font-size: 0.85rem;
          color: var(--text-color);
        }

        .service-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .service-type {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--hubspot-color);
          margin-bottom: 4px;
        }

        .service-details {
          font-size: 0.75rem;
          color: var(--gray-color);
          line-height: 1.3;
        }

        .service-message {
          font-size: 0.75rem;
          color: var(--text-color);
          line-height: 1.3;
          font-style: italic;
        }

        .no-service {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-style: italic;
        }

        .date-info {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .date-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .date-label {
          font-size: 0.7rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .date-value {
          font-size: 0.75rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 12px;
          margin-top: 20px;
        }

        .pagination-btn {
          background: var(--background);
          border: var(--border);
          color: var(--text-color);
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: all 0.2s ease;
        }

        .pagination-btn:hover:not(.disabled) {
          border-color: var(--accent-color);
          color: var(--accent-color);
        }

        .pagination-btn.disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .pagination-info {
          font-size: 0.9rem;
          color: var(--gray-color);
          margin: 0 8px;
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
          border: 3px solid var(--gray-background);
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
        }

        .empty-state p {
          margin: 0;
          font-size: 0.9rem;
        }

        @media (max-width: 768px) {
          .table-header {
            display: none;
          }
          
          .contact-row {
            display: flex;
            flex-direction: column;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            margin-bottom: 12px;
            background: var(--background);
          }
          
          .contact-row:last-child {
            border-bottom: 1px solid var(--border-color);
          }
          
          .cell {
            border-right: none;
            border-bottom: 1px solid var(--border-color);
            padding: 12px 16px;
          }
          
          .cell:last-child {
            border-bottom: none;
          }
          
          .cell::before {
            content: attr(data-label);
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--gray-color);
            text-transform: uppercase;
            letter-spacing: 0.025em;
            display: block;
            margin-bottom: 4px;
          }
          
          .name-cell::before { content: "Contact"; }
          .contact-info-cell::before { content: "Contact Info"; }
          .service-cell::before { content: "Service"; }
          .dates-cell::before { content: "Dates"; }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .date-info {
            flex-direction: row;
            gap: 16px;
          }
        }
      </style>
    `;
  };
}
