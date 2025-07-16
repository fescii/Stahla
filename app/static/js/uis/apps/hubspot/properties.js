export default class HubspotProperties extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/hubspot/properties/all";
    this.propertiesData = null;
    this._loading = true;
    this._empty = false;
    this.currentView = "all";
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.fetchProperties();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchProperties = async (endpoint = null) => {
    this._loading = true;
    this._empty = false;
    this.render();

    const apiUrl = endpoint || this.url;

    try {
      const response = await this.api.get(apiUrl, { content: "json" });

      if (response.status_code === 401) {
        this._loading = false;
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.propertiesData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.propertiesData = response.data;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching HubSpot properties:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.propertiesData = null;
      this.render();
    }
  };

  attachEventListeners = () => {
    // View switcher buttons
    const viewButtons = this.shadowObj.querySelectorAll('.view-btn');
    viewButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        const view = e.target.dataset.view;
        if (view && view !== this.currentView) {
          this.switchView(view);
        }
      });
    });

    // Property card interactions
    const propertyCards = this.shadowObj.querySelectorAll('.property-card');
    propertyCards.forEach(card => {
      card.addEventListener('click', () => {
        card.classList.toggle('expanded');
      });
    });

    // Search functionality
    const searchInput = this.shadowObj.querySelector('.search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.filterProperties(e.target.value);
      });
    }
  };

  switchView = (view) => {
    this.currentView = view;
    let endpoint;

    switch (view) {
      case 'contacts':
        endpoint = '/hubspot/properties/contacts';
        break;
      case 'leads':
        endpoint = '/hubspot/properties/leads';
        break;
      case 'all':
      default:
        endpoint = '/hubspot/properties/all';
        break;
    }

    this.fetchProperties(endpoint);
  };

  filterProperties = (searchTerm) => {
    const propertyCards = this.shadowObj.querySelectorAll('.property-card');
    const term = searchTerm.toLowerCase();

    propertyCards.forEach(card => {
      const propertyName = card.dataset.propertyName?.toLowerCase() || '';
      const propertyLabel = card.querySelector('.property-name')?.textContent?.toLowerCase() || '';
      const propertyType = card.querySelector('.property-type')?.textContent?.toLowerCase() || '';

      if (propertyName.includes(term) || propertyLabel.includes(term) || propertyType.includes(term)) {
        card.style.display = 'block';
      } else {
        card.style.display = 'none';
      }
    });
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

    if (this._empty || !this.propertiesData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getViewSwitcher()}
        ${this.getSearchBar()}
        ${this.getPropertiesStats()}
        ${this.getPropertiesList()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>HubSpot Properties</h1>
        <p class="subtitle">Property definitions and metadata from HubSpot CRM</p>
      </div>
    `;
  };

  getViewSwitcher = () => {
    return /* html */ `
      <div class="view-switcher">
        <button class="view-btn ${this.currentView === 'all' ? 'active' : ''}" data-view="all">
          All Properties
        </button>
        <button class="view-btn ${this.currentView === 'contacts' ? 'active' : ''}" data-view="contacts">
          Contact Properties
        </button>
        <button class="view-btn ${this.currentView === 'leads' ? 'active' : ''}" data-view="leads">
          Lead Properties
        </button>
      </div>
    `;
  };

  getSearchBar = () => {
    return /* html */ `
      <div class="search-container">
        <input type="text" class="search-input" placeholder="Search properties by name, type, or label..." />
        <span class="search-icon">🔍</span>
      </div>
    `;
  };

  getPropertiesStats = () => {
    if (!this.propertiesData || this.propertiesData.length === 0) {
      return '';
    }

    const stats = this.calculatePropertiesStats(this.propertiesData);

    return /* html */ `
      <div class="properties-stats">
        <h3>Properties Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalProperties}</span>
            <span class="stat-label">Total Properties</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.customProperties}</span>
            <span class="stat-label">Custom Properties</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.typeBreakdown.string || 0}</span>
            <span class="stat-label">Text Properties</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.typeBreakdown.enumeration || 0}</span>
            <span class="stat-label">Dropdown Properties</span>
          </div>
        </div>
      </div>
    `;
  };

  calculatePropertiesStats = (properties) => {
    const totalProperties = properties.length;
    const customProperties = properties.filter(p => p.hubspotDefined === false).length;

    const typeBreakdown = properties.reduce((acc, prop) => {
      const type = prop.type || 'unknown';
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {});

    return {
      totalProperties,
      customProperties,
      typeBreakdown
    };
  };

  getPropertiesList = () => {
    if (!this.propertiesData || this.propertiesData.length === 0) {
      return this.getEmptyMessage();
    }

    // Group properties by type for better organization
    const groupedProperties = this.groupPropertiesByType(this.propertiesData);

    return /* html */ `
      <div class="properties-container">
        ${Object.entries(groupedProperties).map(([type, properties]) =>
      this.getPropertyGroup(type, properties)
    ).join('')}
      </div>
    `;
  };

  groupPropertiesByType = (properties) => {
    return properties.reduce((groups, property) => {
      const type = property.type || 'unknown';
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(property);
      return groups;
    }, {});
  };

  getPropertyGroup = (type, properties) => {
    const typeDisplayName = this.getTypeDisplayName(type);

    return /* html */ `
      <div class="property-group">
        <div class="group-header">
          <h3>${typeDisplayName}</h3>
          <span class="group-count">${properties.length} properties</span>
        </div>
        <div class="properties-grid">
          ${properties.map(property => this.getPropertyCard(property)).join('')}
        </div>
      </div>
    `;
  };

  getTypeDisplayName = (type) => {
    const typeMap = {
      'string': 'Text Properties',
      'enumeration': 'Dropdown Properties',
      'number': 'Number Properties',
      'bool': 'Boolean Properties',
      'datetime': 'Date/Time Properties',
      'date': 'Date Properties',
      'phone_number': 'Phone Properties',
      'unknown': 'Other Properties'
    };

    return typeMap[type] || `${type.charAt(0).toUpperCase() + type.slice(1)} Properties`;
  };

  getPropertyCard = (property) => {
    return /* html */ `
      <div class="property-card" data-property-name="${property.name}" tabindex="0">
        <div class="property-header">
          <div class="property-info">
            <h4 class="property-name">${property.label || property.name}</h4>
            <span class="property-type type-${property.type}">${property.type}</span>
            ${property.hubspotDefined === false ? '<span class="custom-badge">Custom</span>' : ''}
          </div>
          ${this.getPropertyStatus(property)}
        </div>
        
        <div class="property-body">
          <div class="property-details">
            <div class="detail-item">
              <span class="detail-label">Name</span>
              <span class="detail-value property-name-value">${property.name}</span>
            </div>
            
            ${property.description ? /* html */ `
              <div class="detail-item">
                <span class="detail-label">Description</span>
                <p class="detail-value property-description">${property.description}</p>
              </div>
            ` : ''}
            
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Group</span>
                <span class="detail-value">${property.groupName || 'N/A'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Field Type</span>
                <span class="detail-value">${property.fieldType || property.type}</span>
              </div>
            </div>
            
            ${this.getPropertyOptions(property)}
            
            ${this.getPropertyMetadata(property)}
          </div>
        </div>
      </div>
    `;
  };

  getPropertyStatus = (property) => {
    const statusBadges = [];

    if (property.readOnlyValue) {
      statusBadges.push('<span class="status-badge readonly">Read Only</span>');
    }

    if (property.hidden) {
      statusBadges.push('<span class="status-badge hidden">Hidden</span>');
    }

    if (property.calculated) {
      statusBadges.push('<span class="status-badge calculated">Calculated</span>');
    }

    return statusBadges.length > 0 ? /* html */ `
      <div class="property-status">
        ${statusBadges.join('')}
      </div>
    ` : '';
  };

  getPropertyOptions = (property) => {
    if (!property.options || property.options.length === 0) {
      return '';
    }

    return /* html */ `
      <div class="property-options">
        <span class="detail-label">Options</span>
        <div class="options-list">
          ${property.options.slice(0, 5).map(option => /* html */ `
            <span class="option-tag">${option.label}</span>
          `).join('')}
          ${property.options.length > 5 ? /* html */ `
            <span class="option-more">+${property.options.length - 5} more</span>
          ` : ''}
        </div>
      </div>
    `;
  };

  getPropertyMetadata = (property) => {
    return /* html */ `
      <div class="property-metadata">
        <div class="metadata-row">
          <div class="detail-item">
            <span class="detail-label">Created</span>
            <span class="detail-value">${this.formatDate(property.createdAt)}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Updated</span>
            <span class="detail-value">${this.formatDate(property.updatedAt)}</span>
          </div>
        </div>
        
        ${property.modificationMetadata ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">Last Modified By</span>
            <span class="detail-value">${property.modificationMetadata.readOnlyDefinition ? 'System' : 'User'}</span>
          </div>
        ` : ''}
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
        <h2>No Properties Found</h2>
        <p>There are no HubSpot properties to display for the selected view.</p>
      </div>
    `;
  };

  formatDate = (dateString) => {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
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

        .view-switcher {
          display: flex;
          justify-content: center;
          gap: 8px;
          margin-bottom: 10px;
        }

        .view-btn {
          background: var(--background);
          border: var(--border);
          color: var(--text-color);
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 0.9rem;
          transition: all 0.2s ease;
        }

        .view-btn:hover {
          border-color: var(--hubspot-color);
          color: var(--hubspot-color);
        }

        .view-btn.active {
          background: var(--hubspot-color);
          color: var(--white-color);
          border-color: var(--hubspot-color);
        }

        .search-container {
          position: relative;
          max-width: 400px;
          margin: 0 auto 10px;
        }

        .search-input {
          width: 100%;
          padding: 10px 40px 10px 12px;
          border: var(--border);
          border-radius: 6px;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.9rem;
        }

        .search-input:focus {
          outline: none;
          border-color: var(--hubspot-color);
        }

        .search-icon {
          position: absolute;
          right: 12px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--gray-color);
          pointer-events: none;
        }

        .properties-stats {
          background: var(--hubspot-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .properties-stats h3 {
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

        .properties-container {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .property-group {
          background: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
        }

        .group-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 8px;
          border-bottom: var(--border);
        }

        .group-header h3 {
          margin: 0;
          color: var(--title-color);
          font-size: 1.2rem;
        }

        .group-count {
          background: var(--gray-background);
          color: var(--gray-color);
          font-size: 0.8rem;
          padding: 4px 8px;
          border-radius: 10px;
        }

        .properties-grid {
          display: grid;
          gap: 12px;
          grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
        }

        .property-card {
          background: var(--gray-background);
          border: var(--border);
          border-radius: 6px;
          padding: 12px;
          transition: all 0.2s ease;
          cursor: pointer;
          border-left: 3px solid var(--hubspot-color);
        }

        .property-card:hover {
          border-color: var(--hubspot-color);
        }

        .property-card:focus {
          outline: none;
          border-color: var(--hubspot-color);
        }

        .property-card.expanded .property-body {
          display: block;
        }

        .property-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 8px;
        }

        .property-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .property-name {
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .property-type {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          text-transform: uppercase;
        }

        .property-type.type-string {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .property-type.type-enumeration {
          background: var(--hubspot-color);
          color: var(--white-color);
        }

        .property-type.type-number {
          background: var(--success-color);
          color: var(--white-color);
        }

        .property-type.type-bool {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .property-type.type-datetime,
        .property-type.type-date {
          background: var(--create-color);
          color: var(--white-color);
        }

        .custom-badge {
          background: var(--error-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .property-status {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
        }

        .status-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 8px;
          font-weight: 500;
        }

        .status-badge.readonly {
          background: var(--gray-color);
          color: var(--white-color);
        }

        .status-badge.hidden {
          background: var(--alt-color);
          color: var(--white-color);
        }

        .status-badge.calculated {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .property-body {
          display: none;
        }

        .property-card.expanded .property-body {
          display: block;
          padding-top: 8px;
          border-top: var(--border);
        }

        .property-details {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .detail-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .detail-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
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

        .property-name-value {
          font-family: monospace;
          background: var(--background);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.8rem;
        }

        .property-description {
          margin: 0;
          line-height: 1.4;
          font-style: italic;
        }

        .property-options {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .options-list {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .option-tag {
          background: var(--hubspot-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .option-more {
          background: var(--gray-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
          font-style: italic;
        }

        .property-metadata {
          background: var(--background);
          border-radius: 4px;
          padding: 8px;
          margin-top: 4px;
        }

        .metadata-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
          margin-bottom: 8px;
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
          .properties-grid {
            grid-template-columns: 1fr;
          }
          
          .detail-row,
          .metadata-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .property-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 6px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .view-switcher {
            flex-direction: column;
            align-items: center;
          }

          .search-container {
            max-width: 100%;
          }
        }
      </style>
    `;
  };
}
