export default class PropertiesContact extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/hubspot/properties/contacts";
    this.propertiesData = null;
    this._loading = true;
    this._empty = false;
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

  fetchProperties = async () => {
    this._loading = true;
    this._empty = false;
    this.render();

    try {
      const response = await this.api.get(this.url, { content: "json" });

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
      console.error("Error fetching contact properties:", error);
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

    // Group filter
    const groupFilter = this.shadowObj.querySelector('.group-filter');
    if (groupFilter) {
      groupFilter.addEventListener('change', (e) => {
        this.filterByGroup(e.target.value);
      });
    }
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

  filterByGroup = (groupName) => {
    const propertyCards = this.shadowObj.querySelectorAll('.property-card');

    propertyCards.forEach(card => {
      const cardGroup = card.dataset.propertyGroup || '';

      if (groupName === 'all' || cardGroup === groupName) {
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
        ${this.getControls()}
        ${this.getPropertiesStats()}
        ${this.getPropertiesList()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Contact Properties</h1>
        <p class="subtitle">HubSpot contact property definitions and configurations</p>
      </div>
    `;
  };

  getControls = () => {
    const groups = this.getUniqueGroups();

    return /* html */ `
      <div class="controls">
        <div class="search-container">
          <input type="text" class="search-input" placeholder="Search contact properties..." />
          <span class="search-icon">🔍</span>
        </div>
        
        <div class="filter-container">
          <select class="group-filter">
            <option value="all">All Groups</option>
            ${groups.map(group => /* html */ `
              <option value="${group}">${group}</option>
            `).join('')}
          </select>
        </div>
      </div>
    `;
  };

  getUniqueGroups = () => {
    if (!this.propertiesData) return [];

    const groups = new Set();
    this.propertiesData.forEach(prop => {
      if (prop.groupName) {
        groups.add(prop.groupName);
      }
    });

    return Array.from(groups).sort();
  };

  getPropertiesStats = () => {
    if (!this.propertiesData || this.propertiesData.length === 0) {
      return '';
    }

    const stats = this.calculatePropertiesStats(this.propertiesData);

    return /* html */ `
      <div class="properties-stats">
        <h3>Contact Properties Overview</h3>
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
            <span class="stat-count">${stats.requiredProperties}</span>
            <span class="stat-label">Required Properties</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.groupCount}</span>
            <span class="stat-label">Property Groups</span>
          </div>
        </div>
      </div>
    `;
  };

  calculatePropertiesStats = (properties) => {
    const totalProperties = properties.length;
    const customProperties = properties.filter(p => p.hubspotDefined === false).length;
    const requiredProperties = properties.filter(p => p.displayOrder >= 0).length;
    const groupCount = new Set(properties.map(p => p.groupName).filter(g => g)).size;

    return {
      totalProperties,
      customProperties,
      requiredProperties,
      groupCount
    };
  };

  getPropertiesList = () => {
    if (!this.propertiesData || this.propertiesData.length === 0) {
      return this.getEmptyMessage();
    }

    // Group properties by group name
    const groupedProperties = this.groupPropertiesByGroup(this.propertiesData);

    return /* html */ `
      <div class="properties-container">
        ${Object.entries(groupedProperties).map(([group, properties]) =>
      this.getPropertyGroup(group, properties)
    ).join('')}
      </div>
    `;
  };

  groupPropertiesByGroup = (properties) => {
    return properties.reduce((groups, property) => {
      const group = property.groupName || 'Other';
      if (!groups[group]) {
        groups[group] = [];
      }
      groups[group].push(property);
      return groups;
    }, {});
  };

  getPropertyGroup = (groupName, properties) => {
    return /* html */ `
      <div class="property-group">
        <div class="group-header">
          <h3>${groupName}</h3>
          <span class="group-count">${properties.length} properties</span>
        </div>
        <div class="properties-grid">
          ${properties.map(property => this.getPropertyCard(property)).join('')}
        </div>
      </div>
    `;
  };

  getPropertyCard = (property) => {
    return /* html */ `
      <div class="property-card" 
           data-property-name="${property.name}" 
           data-property-group="${property.groupName || ''}" 
           tabindex="0">
        <div class="property-header">
          <div class="property-info">
            <h4 class="property-name">${property.label || property.name}</h4>
            <span class="property-type type-${property.type}">${property.type}</span>
            ${property.hubspotDefined === false ? '<span class="custom-badge">Custom</span>' : ''}
            ${property.displayOrder >= 0 ? '<span class="required-badge">Required</span>' : ''}
          </div>
          ${this.getPropertyStatus(property)}
        </div>
        
        <div class="property-body">
          <div class="property-details">
            <div class="detail-item">
              <span class="detail-label">Internal Name</span>
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
                <span class="detail-label">Field Type</span>
                <span class="detail-value">${property.fieldType || property.type}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Display Order</span>
                <span class="detail-value">${property.displayOrder >= 0 ? property.displayOrder : 'N/A'}</span>
              </div>
            </div>
            
            ${this.getPropertyOptions(property)}
            
            ${this.getPropertyConfiguration(property)}
            
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
        <span class="detail-label">Available Options</span>
        <div class="options-list">
          ${property.options.slice(0, 8).map(option => /* html */ `
            <span class="option-tag">${option.label}</span>
          `).join('')}
          ${property.options.length > 8 ? /* html */ `
            <span class="option-more">+${property.options.length - 8} more</span>
          ` : ''}
        </div>
      </div>
    `;
  };

  getPropertyConfiguration = (property) => {
    const configs = [];

    if (property.hasUniqueValue) configs.push('Unique Values');
    if (property.formField) configs.push('Form Field');
    if (property.referencedObjectType) configs.push(`References: ${property.referencedObjectType}`);

    if (configs.length === 0) return '';

    return /* html */ `
      <div class="property-configuration">
        <span class="detail-label">Configuration</span>
        <div class="config-tags">
          ${configs.map(config => /* html */ `
            <span class="config-tag">${config}</span>
          `).join('')}
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
        
        ${property.createdUserId ? /* html */ `
          <div class="detail-item">
            <span class="detail-label">Created By</span>
            <span class="detail-value">${property.createdUserId}</span>
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
        <h2>No Contact Properties Found</h2>
        <p>There are no contact properties to display at this time.</p>
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

        .controls {
          display: flex;
          gap: 12px;
          align-items: center;
          justify-content: center;
          flex-wrap: wrap;
        }

        .search-container {
          position: relative;
          max-width: 300px;
          flex: 1;
        }

        .search-input {
          width: 100%;
          padding: 8px 35px 8px 12px;
          border: var(--border);
          border-radius: 6px;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.9rem;
        }

        .search-input:focus {
          outline: none;
          border-color: var(--alt-color);
        }

        .search-icon {
          position: absolute;
          right: 10px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--gray-color);
          pointer-events: none;
        }

        .filter-container {
          display: flex;
          gap: 8px;
        }

        .group-filter {
          padding: 8px 12px;
          border: var(--border);
          border-radius: 6px;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.9rem;
          cursor: pointer;
        }

        .group-filter:focus {
          outline: none;
          border-color: var(--alt-color);
        }

        .properties-stats {
          background: var(--create-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .properties-stats h3 {
          margin: 0 0 12px 0;
          color: var(--alt-color);
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
          color: var(--alt-color);
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
          border-left: 3px solid var(--alt-color);
        }

        .property-card:hover {
          border-color: var(--alt-color);
        }

        .property-card:focus {
          outline: none;
          border-color: var(--alt-color);
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
          background: var(--alt-color);
          color: var(--white-color);
        }

        .property-type.type-number {
          background: var(--success-color);
          color: var(--white-color);
        }

        .property-type.type-bool {
          background: var(--create-color);
          color: var(--white-color);
        }

        .property-type.type-datetime,
        .property-type.type-date {
          background: var(--hubspot-color);
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

        .required-badge {
          background: var(--accent-color);
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
          background: var(--alt-color);
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

        .property-configuration {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .config-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .config-tag {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
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

          .controls {
            flex-direction: column;
            align-items: stretch;
          }

          .search-container {
            max-width: 100%;
          }
        }
      </style>
    `;
  };
}
