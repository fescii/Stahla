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

      // Handle the structured response based on current view
      if (Array.isArray(response.data)) {
        // Direct array response
        this.propertiesData = response.data;
      } else if (response.data && typeof response.data === 'object') {
        // Structured response with contacts/leads/summary
        if (this.currentView === 'contacts' && response.data.contacts?.properties) {
          this.propertiesData = response.data.contacts.properties;
        } else if (this.currentView === 'leads' && response.data.leads?.properties) {
          this.propertiesData = response.data.leads.properties;
        } else if (this.currentView === 'all') {
          // Combine both contacts and leads properties for 'all' view
          const contactProps = response.data.contacts?.properties || [];
          const leadProps = response.data.leads?.properties || [];
          this.propertiesData = [...contactProps, ...leadProps];
        } else if (response.data.properties) {
          // Fallback: direct properties array
          this.propertiesData = response.data.properties;
        } else if (response.data.results) {
          // Fallback: results array
          this.propertiesData = response.data.results;
        } else {
          console.warn('Unexpected data structure for view:', this.currentView, response.data);
          this.propertiesData = [];
        }
      } else {
        console.warn('Unexpected data structure:', response.data);
        this.propertiesData = [];
      }

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

    // Expand button interactions
    const expandButtons = this.shadowObj.querySelectorAll('.expand-btn');
    expandButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();

        const detailsId = btn.getAttribute('aria-controls');
        if (detailsId) {
          this.togglePropertyDetails(e, detailsId);
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

  getPropertiesStats = () => {
    if (!this.propertiesData || !Array.isArray(this.propertiesData) || this.propertiesData.length === 0) {
      return '';
    }

    const stats = this.calculatePropertiesStats(this.propertiesData);

    return /* html */ `
      <div class="properties-summary">
        <span class="summary-text">
          Showing ${stats.totalProperties} properties 
          (${stats.customProperties} custom)
        </span>
      </div>
    `;
  };

  calculatePropertiesStats = (properties) => {
    // Ensure properties is an array
    if (!Array.isArray(properties)) {
      console.warn('Properties is not an array:', properties);
      return {
        totalProperties: 0,
        customProperties: 0,
        typeBreakdown: {}
      };
    }

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
    if (!this.propertiesData || !Array.isArray(this.propertiesData) || this.propertiesData.length === 0) {
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
    if (!Array.isArray(properties)) {
      console.warn('Properties is not an array in groupPropertiesByType:', properties);
      return {};
    }

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

  getSVGIcon = (type) => {
    const icons = {
      string: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 7V4a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v3M4 7h16M4 7v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V7"/>
        <path d="M9 11h6"/>
      </svg>`,
      enumeration: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M6 9l6 6 6-6"/>
      </svg>`,
      number: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <text x="12" y="16" text-anchor="middle" font-size="12" fill="currentColor">#</text>
        <rect x="3" y="3" width="18" height="18" rx="2"/>
      </svg>`,
      date: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
        <line x1="16" y1="2" x2="16" y2="6"/>
        <line x1="8" y1="2" x2="8" y2="6"/>
        <line x1="3" y1="10" x2="21" y2="10"/>
      </svg>`,
      bool: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 12l2 2 4-4"/>
        <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z"/>
      </svg>`,
      custom: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
      </svg>`,
      hubspot: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"/>
      </svg>`,
      required: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>`,
      expand: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6,9 12,15 18,9"/>
      </svg>`,
      info: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <path d="M12 16v-4"/>
        <path d="M12 8h.01"/>
      </svg>`,
      validation: `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 12l2 2 4-4"/>
        <circle cx="12" cy="12" r="10"/>
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
            <span class="property-type">${this.getTypeDisplay(property.type)}</span>
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
              </div>
            </div>
            
            ${this.getValidationSection(property)}
            ${this.getOptionsSection(property)}
            ${this.getMetadataSection(property)}
          </div>
        </div>
      </div>
    `;
  }; getValidationInfo = (property) => {
    const validations = [];
    if (property.required) validations.push('Required');
    if (property.calculated) validations.push('Calculated');
    if (property.readOnly) validations.push('Read Only');

    return validations.length > 0 ?
      `<div class="validation-tags">${validations.map(v => `<span class="validation-tag">${v}</span>`).join('')}</div>` : '';
  };

  getOptionsInfo = (property) => {
    if (!property.options || property.options.length === 0) return '';

    const displayOptions = property.options.slice(0, 3);
    const hasMore = property.options.length > 3;

    return /* html */ `
      <div class="config-item">
        <span class="config-label">Options:</span>
        <div class="options-list">
          ${displayOptions.map(option => `<span class="option-item">${option.label || option.value}</span>`).join('')}
          ${hasMore ? `<span class="option-more">+${property.options.length - 3} more</span>` : ''}
        </div>
      </div>
    `;
  };

  getTypeDisplay = (type) => {
    const typeMap = {
      'string': 'Text',
      'enumeration': 'Dropdown',
      'number': 'Number',
      'bool': 'Boolean',
      'datetime': 'Date/Time',
      'date': 'Date',
      'phone_number': 'Phone',
      'unknown': 'Other'
    };
    return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
  };

  getValidationSection = (property) => {
    const validations = [];
    if (property.required) validations.push('Required');
    if (property.calculated) validations.push('Calculated');
    if (property.readOnly) validations.push('Read Only');

    if (validations.length === 0) return '';

    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('validation')}
          Validation Rules
        </h5>
        <div class="validation-tags">
          ${validations.map(v => `<span class="validation-tag">${v}</span>`).join('')}
        </div>
      </div>
    `;
  };

  getOptionsSection = (property) => {
    if (!property.options || property.options.length === 0) return '';

    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('options')}
          Available Options (${property.options.length})
        </h5>
        <div class="options-container">
          <div class="options-grid">
            ${property.options.slice(0, 6).map(option => /* html */ `
              <div class="option-item">
                <span class="option-label">${option.label || option.value}</span>
                ${option.value !== option.label ? `<span class="option-value">${option.value}</span>` : ''}
              </div>
            `).join('')}
          </div>
          ${property.options.length > 6 ? /* html */ `
            <button class="show-more-btn" onclick="this.previousElementSibling.classList.toggle('expanded')">
              ${this.getSVGIcon('expand')}
              Show ${property.options.length - 6} more options
            </button>
            <div class="options-grid hidden">
              ${property.options.slice(6).map(option => /* html */ `
                <div class="option-item">
                  <span class="option-label">${option.label || option.value}</span>
                  ${option.value !== option.label ? `<span class="option-value">${option.value}</span>` : ''}
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      </div>
    `;
  };

  getMetadataSection = (property) => {
    return /* html */ `
      <div class="detail-section">
        <h5 class="section-title">
          ${this.getSVGIcon('metadata')}
          Metadata
        </h5>
        <div class="metadata-grid">
          ${property.createdAt ? `<div class="detail-item">
            <span class="detail-label">Created:</span>
            <span class="detail-value">${this.formatDate(property.createdAt)}</span>
          </div>` : ''}
          ${property.updatedAt ? `<div class="detail-item">
            <span class="detail-label">Updated:</span>
            <span class="detail-value">${this.formatDate(property.updatedAt)}</span>
          </div>` : ''}
          ${property.modificationMetadata ? `<div class="detail-item">
            <span class="detail-label">Modified by:</span>
            <span class="detail-value">${property.modificationMetadata.readOnlyDefinition ? 'System' : 'User'}</span>
          </div>` : ''}
        </div>
      </div>
    `;
  };

  getLoader = () => {
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

  togglePropertyDetails = (event, detailsId) => {
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
          border-bottom: 1px solid var(--border-color);
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
          border-bottom: 1px solid var(--border-color);
          transition: background-color 0.2s ease;
        }

        .property-row:hover {
          background: var(--gray-background);
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

        .property-details.expanded {
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
            border-bottom: 1px solid var(--border-color);
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