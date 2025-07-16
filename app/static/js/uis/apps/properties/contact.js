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

      // Extract properties array from response
      let properties = [];
      if (response.data.properties) {
        properties = response.data.properties;
      } else if (Array.isArray(response.data)) {
        properties = response.data;
      }

      this._loading = false;
      this._empty = properties.length === 0;
      this.propertiesData = properties;
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
    // Group filter
    const groupFilter = this.shadowObj.querySelector('.group-filter');
    if (groupFilter) {
      groupFilter.addEventListener('change', (e) => {
        this.filterByGroup(e.target.value);
      });
    }

    // Expand button interactions
    const expandButtons = this.shadowObj.querySelectorAll('.expand-btn');
    expandButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const propertyRow = btn.closest('.property-row');
        const isExpanded = propertyRow.classList.contains('expanded');

        // Toggle expansion
        propertyRow.classList.toggle('expanded');

        // Update aria attributes
        btn.setAttribute('aria-expanded', !isExpanded);

        // Animate the expand icon
        const expandIcon = btn.querySelector('.expand-icon');
        if (expandIcon) {
          expandIcon.style.transform = isExpanded ? 'rotate(0deg)' : 'rotate(180deg)';
        }
      });
    });
  };

  filterByGroup = (groupName) => {
    const propertyRows = this.shadowObj.querySelectorAll('.property-row');

    propertyRows.forEach(row => {
      const rowGroup = row.querySelector('.property-group')?.textContent || '';

      if (groupName === 'all' || rowGroup === groupName) {
        row.style.display = 'grid';
      } else {
        row.style.display = 'none';
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

    return /* html */ `
      <div class="properties-table">
        <div class="table-header">
          <div class="header-cell">Property</div>
          <div class="header-cell">Group</div>
          <div class="header-cell">Type</div>
          <div class="header-cell">Actions</div>
        </div>
        <div class="table-body">
          ${this.propertiesData.map(property => this.getPropertyRow(property)).join('')}
        </div>
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

  getPropertyRow = (property) => {
    const uniqueId = `property-${property.name}`;

    return /* html */ `
      <div class="property-row" data-property-name="${property.name}">
        <div class="cell property-cell">
          <div class="property-main">
            <div class="property-info">
              <h4 class="property-title">${property.label || property.name}</h4>
              <span class="property-name">${property.name}</span>
            </div>
          </div>
        </div>
        
        <div class="cell type-cell">
          <span class="property-group">${property.groupName || 'Default'}</span>
        </div>
        
        <div class="cell status-cell">
          <div class="type-info">
            <span class="property-type type-${property.type}">${property.type}</span>
            <span class="field-type">${property.fieldType || property.type}</span>
          </div>
        </div>
        
        <div class="cell actions-cell">
          <button class="expand-btn" aria-expanded="false" aria-controls="${uniqueId}-details">
            <span class="expand-icon">${this.getSVGIcon('expand')}</span>
          </button>
        </div>
        
        <div class="property-details" id="${uniqueId}-details">
          <div class="details-grid">
            <div class="detail-section">
              <h5 class="section-title">
                ${this.getSVGIcon('info')}
                Basic Information
              </h5>
              <div class="detail-items">
                ${property.description ? `<div class="detail-item">
                  <span class="detail-label">Description:</span>
                  <span class="detail-value">${property.description}</span>
                </div>` : ''}
                <div class="detail-item">
                  <span class="detail-label">Group:</span>
                  <span class="detail-value">${property.groupName || 'N/A'}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Field Type:</span>
                  <span class="detail-value">${property.fieldType || property.type}</span>
                </div>
                ${property.displayOrder >= 0 ? `<div class="detail-item">
                  <span class="detail-label">Display Order:</span>
                  <span class="detail-value">${property.displayOrder}</span>
                </div>` : ''}
              </div>
            </div>
            
            ${this.getPropertyOptionsSection(property)}
            ${this.getPropertyConfigurationSection(property)}
            ${this.getPropertyMetadataSection(property)}
          </div>
        </div>
      </div>
    `;
  };

  getSVGIcon = (type) => {
    const icons = {
      string: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 7V4a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v3M4 7h16M4 7v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7"/>
        <path d="M9 11h6"/>
      </svg>`,
      enumeration: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M6 9l6 6 6-6"/>
      </svg>`,
      expand: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6,9 12,15 18,9"/>
      </svg>`,
      info: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 16v-4"/>
        <path d="M12 8h.01"/>
      </svg>`,
      options: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <path d="M9 9h6v6H9z"/>
      </svg>`,
      metadata: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14,2 14,8 20,8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10,9 9,9 8,9"/>
      </svg>`,
      property: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10 2v20M14 2v20M4 7h16M4 17h16"/>
      </svg>`
    };
    return icons[type] || icons.property;
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

  getPropertyOptionsSection = (property) => {
    if (!property.options || property.options.length === 0) {
      return '';
    }

    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('options')}
          Available Options (${property.options.length})
        </h5>
        <div class="detail-items">
          <div class="options-list">
            ${property.options.slice(0, 8).map(option => `
              <span class="option-tag">${option.label}</span>
            `).join('')}
            ${property.options.length > 8 ? `
              <span class="option-more">+${property.options.length - 8} more</span>
            ` : ''}
          </div>
        </div>
      </div>
    `;
  };

  getPropertyConfigurationSection = (property) => {
    const configs = [];

    if (property.hasUniqueValue) configs.push('Unique Values');
    if (property.formField) configs.push('Form Field');
    if (property.referencedObjectType) configs.push(`References: ${property.referencedObjectType}`);

    if (configs.length === 0) return '';

    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('settings')}
          Configuration
        </h5>
        <div class="detail-items">
          <div class="config-tags">
            ${configs.map(config => `
              <span class="config-tag">${config}</span>
            `).join('')}
          </div>
        </div>
      </div>
    `;
  };

  getPropertyMetadataSection = (property) => {
    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('metadata')}
          Metadata
        </h5>
        <div class="detail-items">
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
          
          ${property.createdUserId ? `
            <div class="detail-item">
              <span class="detail-label">Created By</span>
              <span class="detail-value">${property.createdUserId}</span>
            </div>
          ` : ''}
        </div>
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

  getStyles() {
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
          display: flex;
          flex-direction: column;
          flex-flow: column;
          gap: 0;
          margin-bottom: 20px;
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

        .view-switcher {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
          padding: 4px;
          background: var(--gray-background);
          border-radius: 8px;
          width: fit-content;
        }

        .view-btn {
          padding: 8px 16px;
          border: none;
          background: transparent;
          color: var(--text-color);
          border-radius: 6px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s ease;
        }

        .view-btn.active {
          background: var(--hubspot-color);
          color: var(--white-color);
        }

        .view-btn:hover:not(.active) {
          background: var(--background);
        }

        .properties-summary {
          margin-bottom: 20px;
          padding: 12px 16px;
          background: var(--gray-background);
          border-radius: 6px;
          border: 1px solid var(--border-color);
        }

        .summary-text {
          font-size: 14px;
          color: var(--text-color);
          font-weight: 500;
        }

        .properties-table {
          background: var(--background);
          border-radius: 8px;
          border: 1px solid var(--border-color);
          overflow: hidden;
        }

        .table-header {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr auto;
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

        .property-row {
          display: grid;
          grid-template-columns: 2fr 1fr 1fr auto;
          gap: 16px;
          padding: 16px;
          border-bottom: var(--border);
          transition: background-color 0.2s ease;
        }
        
        .property-row:last-child {
          border-bottom: none;
        }

        .cell {
          display: flex;
          align-items: center;
        }

        .property-cell {
          flex-direction: column;
          align-items: flex-start;
        }

        .property-main {
          display: flex;
          align-items: center;
          width: 100%;
        }

        .property-info {
          flex: 1;
        }

        .property-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--title-color);
          margin: 0 0 4px 0;
        }

        .property-name {
          font-size: 12px;
          color: var(--gray-color);
          font-family: monospace;
        }

        .type-cell {
          flex-direction: column;
          align-items: flex-start;
        }

        .property-group {
          background: var(--gray-background);
          color: var(--text-color);
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
          border: 1px solid var(--border-color);
        }

        .status-cell {
          flex-direction: column;
          align-items: flex-start;
        }

        .type-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .property-type {
          background: var(--success-color);
          color: var(--white-color);
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }

        /* Type-specific colors */
        .property-type.type-string {
          background: var(--success-color);
        }

        .property-type.type-enumeration {
          background: var(--alt-color);
        }

        .property-type.type-number {
          background: var(--accent-color);
        }

        .property-type.type-bool {
          background: var(--gray-color);
        }

        .property-type.type-datetime,
        .property-type.type-date {
          background: var(--error-color);
        }

        .field-type {
          font-size: 11px;
          color: var(--gray-color);
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
          border-color: var(--hubspot-color);
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
          background: var(--hubspot-color);
          border-color: var(--hubspot-color);
        }

        .expand-btn.expanded .expand-icon {
          color: var(--white-color);
        }

        .property-details {
          display: none;
          grid-column: 1 / -1;
          margin-top: 16px;
          padding: 20px;
          background: var(--gray-background);
          border-radius: 6px;
          border: 1px solid var(--border-color);
        }

        .property-row.expanded .property-details {
          display: block;
        }

        .details-grid {
          display: grid;
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
          color: var(--hubspot-color);
        }

        .detail-items {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .detail-item {
          display: flex;
          align-items: flex-start;
          gap: 8px;
        }

        .detail-label {
          font-size: 12px;
          color: var(--gray-color);
          font-weight: 500;
          min-width: 80px;
        }

        .detail-value {
          font-size: 14px;
          color: var(--text-color);
          flex: 1;
        }

        .validation-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .validation-tag {
          background: var(--success-color);
          color: var(--white-color);
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
        }

        .options-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .options-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 8px;
        }

        .option-item {
          background: var(--background);
          border: 1px solid var(--border-color);
          padding: 8px 12px;
          border-radius: 4px;
          display: flex;
          flex-direction: column;
        }

        .option-label {
          font-size: 13px;
          color: var(--text-color);
          font-weight: 500;
        }

        .option-value {
          font-size: 11px;
          color: var(--gray-color);
          font-family: monospace;
        }

        .show-more-btn {
          background: none;
          border: 1px solid var(--border-color);
          color: var(--text-color);
          padding: 8px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          display: flex;
          align-items: center;
          gap: 6px;
          transition: all 0.2s ease;
        }

        .show-more-btn:hover {
          background: var(--gray-background);
          border-color: var(--hubspot-color);
        }

        .metadata-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 12px;
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
          border-top: 3px solid var(--hubspot-color);
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
          .property-row {
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

          .property-details {
            margin-top: 12px;
            padding: 16px;
          }

          .details-grid {
            gap: 16px;
          }

          .options-grid {
            grid-template-columns: 1fr;
          }

          .metadata-grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
    `;
  }
}
