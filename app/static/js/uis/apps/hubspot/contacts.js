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
      <div class="contacts-grid">
        ${this.contactsData.items.map(contact => this.getContactCard(contact)).join('')}
      </div>
    `;
  };

  getContactCard = (contact) => {
    const props = contact.properties;

    return /* html */ `
      <div class="contact-card" data-contact-id="${contact.id}" tabindex="0">
        <div class="contact-header">
          <div class="contact-name">
            <h3>${this.getFullName(props)}</h3>
            <span class="contact-id">ID: ${contact.id}</span>
          </div>
          <div class="hubspot-badge">HubSpot</div>
        </div>
        
        <div class="contact-body">
          ${this.getContactInfo(props)}
          
          ${this.getServiceInfo(props)}
          
          <div class="contact-details">
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Created</span>
                <span class="detail-value">${this.formatDate(contact.created_at)}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Updated</span>
                <span class="detail-value">${this.formatDate(contact.updated_at)}</span>
              </div>
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

  getContactInfo = (props) => {
    return /* html */ `
      <div class="contact-info">
        ${props.email ? /* html */ `
          <div class="info-item">
            <span class="info-icon">@</span>
            <span class="info-value">${props.email}</span>
          </div>
        ` : ''}
        
        ${props.phone ? /* html */ `
          <div class="info-item">
            <span class="info-icon">📞</span>
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
      <div class="info-item address">
        <span class="info-icon">📍</span>
        <span class="info-value">${fullAddress}</span>
      </div>
    `;
  };

  getServiceInfo = (props) => {
    if (!props.what_service_do_you_need_ && !props.your_message && !props.message) {
      return '';
    }

    return /* html */ `
      <div class="service-info">
        ${props.what_service_do_you_need_ ? /* html */ `
          <div class="service-item">
            <span class="service-label">Service Needed</span>
            <span class="service-value service-type">${props.what_service_do_you_need_}</span>
          </div>
        ` : ''}
        
        ${this.getServiceDetails(props)}
        
        ${props.your_message || props.message ? /* html */ `
          <div class="service-item message">
            <span class="service-label">Message</span>
            <p class="service-message">${props.your_message || props.message}</p>
          </div>
        ` : ''}
      </div>
    `;
  };

  getServiceDetails = (props) => {
    const details = [];

    if (props.how_many_restroom_stalls_) {
      details.push(`Restroom Stalls: ${props.how_many_restroom_stalls_}`);
    }
    if (props.how_many_shower_stalls_) {
      details.push(`Shower Stalls: ${props.how_many_shower_stalls_}`);
    }
    if (props.how_many_laundry_units_) {
      details.push(`Laundry Units: ${props.how_many_laundry_units_}`);
    }
    if (props.how_many_portable_toilet_stalls_) {
      details.push(`Portable Toilets: ${props.how_many_portable_toilet_stalls_}`);
    }

    if (details.length === 0) return '';

    return /* html */ `
      <div class="service-item">
        <span class="service-label">Requirements</span>
        <div class="service-details">
          ${details.map(detail => /* html */ `<span class="detail-tag">${detail}</span>`).join('')}
        </div>
      </div>
    `;
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
          text-align: center;
          margin-bottom: 10px;
        }

        .header h1 {
          margin: 0 0 8px 0;
          font-size: 1.8rem;
          font-weight: 600;
          color: var(--hubspot-color);
        }

        .subtitle {
          margin: 0;
          color: var(--gray-color);
          font-size: 0.95rem;
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

        .contacts-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
        }

        .contact-card {
          background: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          transition: all 0.2s ease;
          cursor: pointer;
          position: relative;
          border-left: 4px solid var(--hubspot-color);
        }

        .contact-card:hover {
          border-color: var(--hubspot-color);
        }

        .contact-card:focus {
          outline: none;
          border-color: var(--hubspot-color);
        }

        .contact-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .contact-name h3 {
          margin: 0 0 4px 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .contact-id {
          font-family: var(--font-mono);
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        .hubspot-badge {
          background: var(--hubspot-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 4px 8px;
          border-radius: 12px;
          font-weight: 500;
        }

        .contact-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .contact-info {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .info-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .info-item.address {
          align-items: flex-start;
        }

        .info-icon {
          font-size: 0.9rem;
          width: 20px;
          flex-shrink: 0;
        }

        .info-value {
          color: var(--text-color);
          font-size: 0.9rem;
        }

        .service-info {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .service-item {
          margin-bottom: 8px;
        }

        .service-item:last-child {
          margin-bottom: 0;
        }

        .service-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .service-value {
          font-size: 0.9rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .service-type {
          color: var(--hubspot-color);
          font-weight: 600;
        }

        .service-details {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .detail-tag {
          background: var(--hubspot-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 10px;
        }

        .service-message {
          margin: 0;
          font-size: 0.85rem;
          color: var(--text-color);
          line-height: 1.4;
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
          border-left: 3px solid var(--hubspot-color);
        }

        .contact-details {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .detail-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .detail-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .detail-value {
          font-size: 0.85rem;
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
          .contacts-grid {
            grid-template-columns: 1fr;
          }
          
          .detail-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .contact-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .service-details {
            flex-direction: column;
            align-items: flex-start;
          }
        }
      </style>
    `;
  };
}
