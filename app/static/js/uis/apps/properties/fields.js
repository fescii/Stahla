export default class PropertiesFields extends HTMLElement {
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

      // Handle different response structures
      let properties = [];
      if (response.data.contacts && response.data.leads) {
        // Combined response with contacts and leads
        properties = [
          ...response.data.contacts.properties,
          ...response.data.leads.properties
        ];
      } else if (response.data.properties) {
        // Single type response
        properties = response.data.properties;
      } else if (Array.isArray(response.data)) {
        // Direct array response
        properties = response.data;
      }

      this._loading = false;
      this._empty = properties.length === 0;
      this.propertiesData = properties;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching property fields:", error);
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

    // Field type filter
    const typeFilter = this.shadowObj.querySelector('.type-filter');
    if (typeFilter) {
      typeFilter.addEventListener('change', (e) => {
        this.filterByType(e.target.value);
      });
    }

    // Search functionality
    const searchInput = this.shadowObj.querySelector('.search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.filterFields(e.target.value);
      });
    }

    // Field item interactions
    const fieldItems = this.shadowObj.querySelectorAll('.field-item');
    fieldItems.forEach(item => {
      item.addEventListener('click', () => {
        item.classList.toggle('expanded');
      });
    });
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

  filterByType = (type) => {
    const fieldItems = this.shadowObj.querySelectorAll('.field-item');

    fieldItems.forEach(item => {
      const itemType = item.dataset.fieldType || '';

      if (type === 'all' || itemType === type) {
        item.style.display = 'block';
      } else {
        item.style.display = 'none';
      }
    });
  };

  filterFields = (searchTerm) => {
    const fieldItems = this.shadowObj.querySelectorAll('.field-item');
    const term = searchTerm.toLowerCase();

    fieldItems.forEach(item => {
      const fieldName = item.dataset.fieldName?.toLowerCase() || '';
      const fieldLabel = item.querySelector('.field-name')?.textContent?.toLowerCase() || '';
      const fieldType = item.querySelector('.field-type')?.textContent?.toLowerCase() || '';

      if (fieldName.includes(term) || fieldLabel.includes(term) || fieldType.includes(term)) {
        item.style.display = 'block';
      } else {
        item.style.display = 'none';
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
        ${this.getControls()}
        ${this.getFieldsStats()}
        ${this.getFieldsList()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Property Fields</h1>
        <p class="subtitle">Field definitions and configurations for all property types</p>
      </div>
    `;
  };

  getViewSwitcher = () => {
    return /* html */ `
      <div class="view-switcher">
        <button class="view-btn ${this.currentView === 'all' ? 'active' : ''}" data-view="all">
          All Fields
        </button>
        <button class="view-btn ${this.currentView === 'contacts' ? 'active' : ''}" data-view="contacts">
          Contact Fields
        </button>
        <button class="view-btn ${this.currentView === 'leads' ? 'active' : ''}" data-view="leads">
          Lead Fields
        </button>
      </div>
    `;
  };

  getControls = () => {
    const types = this.getUniqueTypes();

    return /* html */ `
      <div class="controls">
        <div class="search-container">
          <input type="text" class="search-input" placeholder="Search field names, labels, or types..." />
          <span class="search-icon">🔍</span>
        </div>
        
        <div class="filter-container">
          <select class="type-filter">
            <option value="all">All Field Types</option>
            ${types.map(type => /* html */ `
              <option value="${type}">${this.getTypeDisplayName(type)}</option>
            `).join('')}
          </select>
        </div>
      </div>
    `;
  };

  getUniqueTypes = () => {
    if (!this.propertiesData) return [];

    const types = new Set();
    this.propertiesData.forEach(prop => {
      if (prop.fieldType) {
        types.add(prop.fieldType);
      } else if (prop.type) {
        types.add(prop.type);
      }
    });

    return Array.from(types).sort();
  };

  getTypeDisplayName = (type) => {
    const typeMap = {
      'text': 'Text Field',
      'textarea': 'Text Area',
      'select': 'Dropdown',
      'radio': 'Radio Buttons',
      'checkbox': 'Checkboxes',
      'number': 'Number Field',
      'date': 'Date Picker',
      'datetime': 'Date/Time Picker',
      'string': 'String Field',
      'enumeration': 'Enumeration',
      'bool': 'Boolean Field',
      'phone_number': 'Phone Field'
    };

    return typeMap[type] || type.charAt(0).toUpperCase() + type.slice(1);
  };

  getFieldsStats = () => {
    if (!this.propertiesData || this.propertiesData.length === 0) {
      return '';
    }

    const stats = this.calculateFieldsStats(this.propertiesData);

    return /* html */ `
      <div class="fields-stats">
        <h3>Fields Overview</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalFields}</span>
            <span class="stat-label">Total Fields</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.formFields}</span>
            <span class="stat-label">Form Fields</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.requiredFields}</span>
            <span class="stat-label">Required Fields</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.fieldTypes}</span>
            <span class="stat-label">Field Types</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateFieldsStats = (properties) => {
    const totalFields = properties.length;
    const formFields = properties.filter(p => p.formField).length;
    const requiredFields = properties.filter(p => p.displayOrder >= 0).length;
    const fieldTypes = new Set(
      properties.map(p => p.fieldType || p.type).filter(t => t)
    ).size;

    return {
      totalFields,
      formFields,
      requiredFields,
      fieldTypes
    };
  };

  getFieldsList = () => {
    if (!this.propertiesData || this.propertiesData.length === 0) {
      return this.getEmptyMessage();
    }

    // Group fields by field type for better organization
    const groupedFields = this.groupFieldsByType(this.propertiesData);

    return /* html */ `
      <div class="fields-container">
        ${Object.entries(groupedFields).map(([type, fields]) =>
      this.getFieldGroup(type, fields)
    ).join('')}
      </div>
    `;
  };

  groupFieldsByType = (properties) => {
    return properties.reduce((groups, property) => {
      const type = property.fieldType || property.type || 'unknown';
      if (!groups[type]) {
        groups[type] = [];
      }
      groups[type].push(property);
      return groups;
    }, {});
  };

  getFieldGroup = (type, fields) => {
    const typeDisplayName = this.getTypeDisplayName(type);

    return /* html */ `
      <div class="field-group">
        <div class="group-header">
          <h3>${typeDisplayName}</h3>
          <span class="group-count">${fields.length} fields</span>
        </div>
        <div class="fields-list">
          ${fields.map(field => this.getFieldItem(field)).join('')}
        </div>
      </div>
    `;
  };

  getFieldItem = (field) => {
    const fieldType = field.fieldType || field.type || 'unknown';

    return /* html */ `
      <div class="field-item" 
           data-field-name="${field.name}" 
           data-field-type="${fieldType}" 
           tabindex="0">
        <div class="field-header">
          <div class="field-info">
            <h4 class="field-name">${field.label || field.name}</h4>
            <span class="field-type type-${fieldType}">${fieldType}</span>
            ${field.formField ? '<span class="form-badge">Form Field</span>' : ''}
            ${field.displayOrder >= 0 ? '<span class="required-badge">Required</span>' : ''}
          </div>
          ${this.getFieldStatus(field)}
        </div>
        
        <div class="field-body">
          <div class="field-details">
            <div class="detail-item">
              <span class="detail-label">Internal Name</span>
              <span class="detail-value field-name-value">${field.name}</span>
            </div>
            
            ${field.description ? /* html */ `
              <div class="detail-item">
                <span class="detail-label">Description</span>
                <p class="detail-value field-description">${field.description}</p>
              </div>
            ` : ''}
            
            <div class="detail-row">
              <div class="detail-item">
                <span class="detail-label">Group</span>
                <span class="detail-value">${field.groupName || 'Default'}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Display Order</span>
                <span class="detail-value">${field.displayOrder >= 0 ? field.displayOrder : 'N/A'}</span>
              </div>
            </div>
            
            ${this.getFieldOptions(field)}
            
            ${this.getFieldConfiguration(field)}
            
            ${this.getFieldMetadata(field)}
          </div>
        </div>
      </div>
    `;
  };

  getFieldStatus = (field) => {
    const statusBadges = [];

    if (field.readOnlyValue) {
      statusBadges.push('<span class="status-badge readonly">Read Only</span>');
    }

    if (field.hidden) {
      statusBadges.push('<span class="status-badge hidden">Hidden</span>');
    }

    if (field.calculated) {
      statusBadges.push('<span class="status-badge calculated">Calculated</span>');
    }

    if (field.hasUniqueValue) {
      statusBadges.push('<span class="status-badge unique">Unique</span>');
    }

    return statusBadges.length > 0 ? /* html */ `
      <div class="field-status">
        ${statusBadges.join('')}
      </div>
    ` : '';
  };

  getFieldOptions = (field) => {
    if (!field.options || field.options.length === 0) {
      return '';
    }

    return /* html */ `
      <div class="field-options">
        <span class="detail-label">Available Options (${field.options.length})</span>
        <div class="options-list">
          ${field.options.slice(0, 5).map(option => /* html */ `
            <span class="option-tag" title="${option.description || ''}">${option.label}</span>
          `).join('')}
          ${field.options.length > 5 ? /* html */ `
            <span class="option-more">+${field.options.length - 5} more options</span>
          ` : ''}
        </div>
        ${field.options.length > 5 ? /* html */ `
          <div class="all-options" style="display: none;">
            ${field.options.slice(5).map(option => /* html */ `
              <span class="option-tag" title="${option.description || ''}">${option.label}</span>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  };

  getFieldConfiguration = (field) => {
    const configs = [];

    if (field.hasUniqueValue) configs.push('Unique Values Required');
    if (field.searchableInGlobalSearch) configs.push('Globally Searchable');
    if (field.referencedObjectType) configs.push(`References: ${field.referencedObjectType}`);
    if (field.externalOptions) configs.push('External Options Source');

    if (configs.length === 0) return '';

    return /* html */ `
      <div class="field-configuration">
        <span class="detail-label">Configuration Settings</span>
        <div class="config-tags">
          ${configs.map(config => /* html */ `
            <span class="config-tag">${config}</span>
          `).join('')}
        </div>
      </div>
    `;
  };

  getFieldMetadata = (field) => {
    return /* html */ `
      <div class="field-metadata">
        <div class="metadata-row">
          <div class="detail-item">
            <span class="detail-label">Created</span>
            <span class="detail-value">${this.formatDate(field.createdAt)}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Updated</span>
            <span class="detail-value">${this.formatDate(field.updatedAt)}</span>
          </div>
        </div>
        
        <div class="detail-row">
          <div class="detail-item">
            <span class="detail-label">HubSpot Defined</span>
            <span class="detail-value">${field.hubspotDefined ? 'Yes' : 'No'}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Modification Allowed</span>
            <span class="detail-value">${field.modificationMetadata?.readOnlyDefinition ? 'No' : 'Yes'}</span>
          </div>
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
        <h2>No Property Fields Found</h2>
        <p>There are no property fields to display for the selected view.</p>
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
          padding: 15px 0;
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
          border-color: var(--accent-color);
          color: var(--accent-color);
        }

        .view-btn.active {
          background: var(--accent-color);
          color: var(--white-color);
          border-color: var(--accent-color);
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
          max-width: 350px;
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
          border-color: var(--accent-color);
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

        .type-filter {
          padding: 8px 12px;
          border: var(--border);
          border-radius: 6px;
          background: var(--background);
          color: var(--text-color);
          font-size: 0.9rem;
          cursor: pointer;
        }

        .type-filter:focus {
          outline: none;
          border-color: var(--accent-color);
        }

        .fields-stats {
          background: var(--create-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .fields-stats h3 {
          margin: 0 0 12px 0;
          color: var(--accent-color);
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
          color: var(--accent-color);
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .fields-container {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .field-group {
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

        .fields-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .field-item {
          border: var(--border);
          border-radius: 6px;
          padding: 12px;
          transition: all 0.2s ease;
          cursor: pointer;
        }

        .field-item:hover {
          border-color: var(--accent-color);
        }

        .field-item:focus {
          outline: none;
          border-color: var(--accent-color);
        }

        .field-item.expanded .field-body {
          display: block;
        }

        .field-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .field-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .field-name {
          margin: 0;
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .field-type {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
          text-transform: uppercase;
          background: var(--accent-color);
          color: var(--white-color);
        }

        /* Type-specific colors */
        .field-type.type-text,
        .field-type.type-string {
          background: var(--success-color);
        }

        .field-type.type-textarea {
          background: var(--hubspot-color);
        }

        .field-type.type-select,
        .field-type.type-enumeration {
          background: var(--alt-color);
        }

        .field-type.type-number {
          background: var(--accent-color);
        }

        .field-type.type-date,
        .field-type.type-datetime {
          background: var(--error-color);
        }

        .field-type.type-checkbox,
        .field-type.type-booleancheckbox,
        .field-type.type-bool {
          background: var(--gray-color);
        }

        .form-badge {
          background: var(--success-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .required-badge {
          background: var(--error-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .field-status {
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
          background: var(--create-color);
          color: var(--white-color);
        }

        .status-badge.unique {
          background: var(--hubspot-color);
          color: var(--white-color);
        }

        .field-body {
          display: none;
          padding-top: 12px;
          border-top: var(--border);
          margin-top: 8px;
        }

        .field-details {
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

        .field-name-value {
          font-family: monospace;
          background: var(--background);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.8rem;
        }

        .field-description {
          margin: 0;
          line-height: 1.4;
          font-style: italic;
        }

        .field-options {
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
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
          cursor: help;
        }

        .option-more {
          background: var(--gray-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
          font-style: italic;
          cursor: pointer;
        }

        .field-configuration {
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

        .field-metadata {
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
          .detail-row,
          .metadata-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .field-header {
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

          .view-switcher {
            flex-direction: column;
            align-items: center;
          }
        }
      </style>
    `;
  };
}
