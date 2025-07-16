export default class PropertiesLead extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/hubspot/properties/leads";
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
      console.error("Error fetching lead properties:", error);
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

    // Search functionality
    const searchInput = this.shadowObj.querySelector('.search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.filterProperties(e.target.value);
      });
    }

    // Type filter
    const typeFilter = this.shadowObj.querySelector('.type-filter');
    if (typeFilter) {
      typeFilter.addEventListener('change', (e) => {
        this.filterByType(e.target.value);
      });
    }
  };

  filterProperties = (searchTerm) => {
    const propertyRows = this.shadowObj.querySelectorAll('.property-row');
    const term = searchTerm.toLowerCase();

    propertyRows.forEach(row => {
      const propertyName = row.dataset.propertyName?.toLowerCase() || '';
      const propertyLabel = row.querySelector('.property-name')?.textContent?.toLowerCase() || '';
      const propertyType = row.querySelector('.property-type')?.textContent?.toLowerCase() || '';

      if (propertyName.includes(term) || propertyLabel.includes(term) || propertyType.includes(term)) {
        row.style.display = 'block';
      } else {
        row.style.display = 'none';
      }
    });
  };

  filterByType = (type) => {
    const propertyRows = this.shadowObj.querySelectorAll('.property-row');

    propertyRows.forEach(row => {
      const rowType = row.dataset.propertyType || '';

      if (type === 'all' || rowType === type) {
        row.style.display = 'block';
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
        <h1>Lead Properties</h1>
        <p class="subtitle">HubSpot lead/deal property definitions and configurations</p>
      </div>
    `;
  };

  getUniqueTypes = () => {
    if (!this.propertiesData) return [];

    const types = new Set();
    this.propertiesData.forEach(prop => {
      if (prop.type) {
        types.add(prop.type);
      }
    });

    return Array.from(types).sort();
  };

  getTypeDisplayName = (type) => {
    const typeMap = {
      'string': 'Text',
      'enumeration': 'Dropdown',
      'number': 'Number',
      'bool': 'Boolean',
      'datetime': 'Date/Time',
      'date': 'Date',
      'phone_number': 'Phone'
    };

    return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
  };

  calculatePropertiesStats = (properties) => {
    const totalProperties = properties.length;
    const customProperties = properties.filter(p => p.hubspotDefined === false).length;
    const calculatedProperties = properties.filter(p => p.calculated).length;
    const typeCount = new Set(properties.map(p => p.type).filter(t => t)).size;

    return {
      totalProperties,
      customProperties,
      calculatedProperties,
      typeCount
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
          <h3>${typeDisplayName} Properties</h3>
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
      <div class="property-row" 
           data-property-name="${property.name}" 
           data-property-type="${property.type || ''}" 
           tabindex="0">
        <div class="cell property-cell">
          <div class="property-info">
            <h4 class="property-name">${property.label || property.name}</h4>
            <span class="property-internal">${property.name}</span>
            ${property.description ? `<p class="property-description">${property.description}</p>` : ''}
          </div>
          <div class="property-badges">
            ${property.hubspotDefined === false ? '<span class="custom-badge">Custom</span>' : ''}
            ${property.calculated ? '<span class="calculated-badge">Calculated</span>' : ''}
          </div>
        </div>
        
        <div class="cell group-cell">
          <span class="group-name">${property.groupName || 'Default'}</span>
        </div>
        
        <div class="cell type-cell">
          <span class="property-type type-${property.type}">${property.type}</span>
          <span class="field-type">${property.fieldType || property.type}</span>
        </div>
        
        <div class="cell actions-cell">
          ${this.getPropertyStatus(property)}
          <button class="expand-btn" aria-expanded="false" aria-controls="${uniqueId}-details">
            <span class="expand-icon">${this.getSVGIcon('chevron-down')}</span>
          </button>
        </div>
        
        <div class="property-details" id="${uniqueId}-details">
          <div class="details-grid">
            ${this.getPropertyOptionsSection(property)}
            ${this.getLeadSpecificInfoSection(property)}
            ${this.getPropertyConfigurationSection(property)}
            ${this.getPropertyMetadataSection(property)}
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

    if (property.searchableInGlobalSearch) {
      statusBadges.push('<span class="status-badge searchable">Searchable</span>');
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
          ${property.options.slice(0, 6).map(option => /* html */ `
            <span class="option-tag">${option.label}</span>
          `).join('')}
          ${property.options.length > 6 ? /* html */ `
            <span class="option-more">+${property.options.length - 6} more</span>
          ` : ''}
        </div>
      </div>
    `;
  };

  getLeadSpecificInfo = (property) => {
    const leadFields = [];

    // Check for lead/deal specific properties based on common patterns
    if (property.name.includes('deal') || property.name.includes('pipeline') ||
      property.name.includes('stage') || property.name.includes('amount')) {
      leadFields.push('Deal/Pipeline Property');
    }

    if (property.name.includes('lead') || property.name.includes('classification') ||
      property.name.includes('qualification')) {
      leadFields.push('Lead Classification');
    }

    if (property.referencedObjectType) {
      leadFields.push(`References: ${property.referencedObjectType}`);
    }

    if (leadFields.length === 0) return '';

    return /* html */ `
      <div class="lead-specific-info">
        <span class="detail-label">Lead/Deal Context</span>
        <div class="lead-info-tags">
          ${leadFields.map(field => /* html */ `
            <span class="lead-info-tag">${field}</span>
          `).join('')}
        </div>
      </div>
    `;
  };

  getPropertyConfiguration = (property) => {
    const configs = [];

    if (property.hasUniqueValue) configs.push('Unique Values');
    if (property.formField) configs.push('Form Field');
    if (property.externalOptions) configs.push('External Options');

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
        <h2>No Lead Properties Found</h2>
        <p>There are no lead properties to display at this time.</p>
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

  getSVGIcon = (type) => {
    const icons = {
      'chevron-down': '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6,9 12,15 18,9"></polyline></svg>',
      'options': '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"></path></svg>',
      'settings': '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>',
      'info': '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4m0-4h.01"></path></svg>',
      'deal': '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10"></path></svg>'
    };
    return icons[type] || icons['info'];
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

  getLeadSpecificInfoSection = (property) => {
    const leadFields = [];

    if (property.referencedObjectType) {
      leadFields.push(`References: ${property.referencedObjectType}`);
    }

    if (property.calculated) {
      leadFields.push('Calculated Field');
    }

    if (leadFields.length === 0) return '';

    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('deal')}
          Lead/Deal Context
        </h5>
        <div class="detail-items">
          <div class="lead-info-tags">
            ${leadFields.map(field => `
              <span class="lead-info-tag">${field}</span>
            `).join('')}
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
          ${this.getSVGIcon('info')}
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
