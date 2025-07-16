export default class ClassifyDisqualified extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/mongo/classify/disqualified";
    this.classifyData = null;
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
    this.fetchClassifications();
  }

  disconnectedCallback() {
    // Cleanup if needed
  }

  fetchClassifications = async (page = 1) => {
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
        this.classifyData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._empty = false;
      this.classifyData = response.data;
      this.currentPage = response.data.page;
      this.hasMore = response.data.has_more;
      this.render();
      this.attachEventListeners();
    } catch (error) {
      console.error("Error fetching disqualified classifications:", error);
      if (error.status === 401) {
        this._loading = false;
        this.app.showLogin();
        return;
      }
      this._loading = false;
      this._empty = true;
      this.classifyData = null;
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
          this.fetchClassifications(this.currentPage - 1);
        }
      });
    }

    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        if (this.hasMore) {
          this.fetchClassifications(this.currentPage + 1);
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

    if (this._empty || !this.classifyData) {
      return /* html */ `<div class="container">${this.getEmptyMessage()}</div>`;
    }

    return /* html */ `
      <div class="container">
        ${this.getHeader()}
        ${this.getDisqualifiedStats()}
        ${this.getClassificationsList()}
        ${this.getPagination()}
      </div>
    `;
  };

  getHeader = () => {
    return /* html */ `
      <div class="header">
        <h1>Disqualified Classifications</h1>
        <p class="subtitle">Leads classified as disqualified or not suitable for services</p>
      </div>
    `;
  };

  getDisqualifiedStats = () => {
    if (!this.classifyData.items || this.classifyData.items.length === 0) {
      return '';
    }

    const stats = this.calculateDisqualifiedStats(this.classifyData.items);

    return /* html */ `
      <div class="disqualified-stats">
        <h3>Disqualification Analysis</h3>
        <div class="stats-grid">
          <div class="stat-item">
            <span class="stat-count">${stats.totalDisqualified}</span>
            <span class="stat-label">Disqualified</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.highConfidenceCount}</span>
            <span class="stat-label">High Confidence</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.avgConfidence}%</span>
            <span class="stat-label">Avg Confidence</span>
          </div>
          <div class="stat-item">
            <span class="stat-count">${stats.commonReasons}</span>
            <span class="stat-label">Top Reasons</span>
          </div>
        </div>
      </div>
    `;
  };

  calculateDisqualifiedStats = (classifications) => {
    const totalDisqualified = classifications.length;
    const highConfidenceCount = classifications.filter(c =>
      c.classification?.confidence >= 0.8
    ).length;

    const confidences = classifications
      .filter(c => c.classification?.confidence !== null && c.classification?.confidence !== undefined)
      .map(c => c.classification.confidence);

    const avgConfidence = confidences.length > 0
      ? Math.round((confidences.reduce((sum, conf) => sum + conf, 0) / confidences.length) * 100)
      : 0;

    // Count unique disqualification reasons
    const reasonsSet = new Set();
    classifications.forEach(c => {
      if (c.classification?.reasoning) {
        // Extract key phrases from reasoning for categorization
        const reasoning = c.classification.reasoning.toLowerCase();
        if (reasoning.includes('outside service area') || reasoning.includes('location')) {
          reasonsSet.add('Outside Service Area');
        } else if (reasoning.includes('budget') || reasoning.includes('price') || reasoning.includes('cost')) {
          reasonsSet.add('Budget Constraints');
        } else if (reasoning.includes('timeline') || reasoning.includes('date') || reasoning.includes('time')) {
          reasonsSet.add('Timeline Issues');
        } else if (reasoning.includes('competitor') || reasoning.includes('already have')) {
          reasonsSet.add('Competitor/Existing Service');
        } else if (reasoning.includes('incomplete') || reasoning.includes('insufficient')) {
          reasonsSet.add('Insufficient Information');
        } else {
          reasonsSet.add('Other Reasons');
        }
      }
    });

    return {
      totalDisqualified,
      highConfidenceCount,
      avgConfidence,
      commonReasons: reasonsSet.size
    };
  };

  getClassificationsList = () => {
    if (!this.classifyData.items || this.classifyData.items.length === 0) {
      return this.getEmptyMessage();
    }

    return /* html */ `
      <div class="classifications-grid">
        ${this.classifyData.items.map(classification => this.getClassificationCard(classification)).join('')}
      </div>
    `;
  };

  getClassificationCard = (classification) => {
    const classif = classification.classification;
    const input = classification.input;

    return /* html */ `
      <div class="classification-card disqualified-card" data-classification-id="${classification._id}" tabindex="0">
        <div class="classification-header">
          <div class="classification-info">
            <h3>Disqualified ${classification._id.slice(-6)}</h3>
            ${this.getDisqualificationBadge()}
            ${this.getConfidenceBadge(classif?.confidence)}
          </div>
          <div class="disqualified-indicator">
            <span class="disqualified-icon">🚫</span>
            <span class="source-badge source-${input?.source}">${input?.source || 'unknown'}</span>
          </div>
        </div>
        
        <div class="classification-body">
          ${this.getDisqualificationResults(classif)}
          
          ${this.getLeadSummary(input)}
          
          ${this.getDisqualificationAnalysis(classif)}
          
          <div class="classification-metadata">
            <div class="metadata-row">
              <div class="metadata-item">
                <span class="metadata-label">Disqualified</span>
                <span class="metadata-value">${this.formatDate(classification.created_at)}</span>
              </div>
              <div class="metadata-item">
                <span class="metadata-label">Confidence</span>
                <span class="metadata-value confidence-level">${this.getConfidenceLevel(classif?.confidence)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  getDisqualificationBadge = () => {
    return /* html */ `<span class="disqualification-badge">Disqualify</span>`;
  };

  getConfidenceBadge = (confidence) => {
    if (confidence === null || confidence === undefined) return '';

    const percentage = Math.round(confidence * 100);
    const level = this.getConfidenceClass(confidence);
    return /* html */ `<span class="confidence-badge confidence-${level}">${percentage}%</span>`;
  };

  getConfidenceClass = (confidence) => {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.6) return 'medium';
    return 'low';
  };

  getConfidenceLevel = (confidence) => {
    if (confidence === null || confidence === undefined) return 'Unknown';

    const percentage = Math.round(confidence * 100);
    if (confidence >= 0.8) return `High (${percentage}%)`;
    if (confidence >= 0.6) return `Medium (${percentage}%)`;
    return `Low (${percentage}%)`;
  };

  getDisqualificationResults = (classif) => {
    if (!classif) return '';

    return /* html */ `
      <div class="disqualification-results">
        <div class="results-title">Disqualification Results</div>
        
        <div class="result-highlights">
          <div class="highlight-item">
            <span class="highlight-label">Classification</span>
            <span class="highlight-value disqualified">Disqualify</span>
          </div>
          
          ${classif.routing_suggestion ? /* html */ `
            <div class="highlight-item">
              <span class="highlight-label">Routing</span>
              <span class="highlight-value routing">${classif.routing_suggestion}</span>
            </div>
          ` : ''}
        </div>
        
        ${classif.reasoning ? /* html */ `
          <div class="reasoning-section">
            <span class="detail-label">Disqualification Reasoning</span>
            <p class="reasoning-text">${classif.reasoning}</p>
          </div>
        ` : ''}
      </div>
    `;
  };

  getLeadSummary = (input) => {
    if (!input) return '';

    const leadInfo = [];

    if (input.firstname || input.lastname) {
      leadInfo.push({
        icon: '👤',
        label: 'Contact',
        value: [input.firstname, input.lastname].filter(n => n).join(' ')
      });
    }
    if (input.company) leadInfo.push({ icon: '🏢', label: 'Company', value: input.company });
    if (input.email) leadInfo.push({ icon: '📧', label: 'Email', value: input.email });
    if (input.intended_use) leadInfo.push({ icon: '🎯', label: 'Intended Use', value: input.intended_use });

    if (leadInfo.length === 0) return '';

    return /* html */ `
      <div class="lead-summary">
        <div class="summary-title">Lead Summary</div>
        
        <div class="summary-grid">
          ${leadInfo.map(info => /* html */ `
            <div class="summary-item">
              <span class="summary-icon">${info.icon}</span>
              <div class="summary-content">
                <span class="summary-label">${info.label}</span>
                <span class="summary-value">${info.value}</span>
              </div>
            </div>
          `).join('')}
        </div>
        
        ${this.getLeadDetails(input)}
      </div>
    `;
  };

  getLeadDetails = (input) => {
    const details = [];

    if (input.event_type) details.push({ label: 'Event Type', value: input.event_type });
    if (input.required_stalls) details.push({ label: 'Stalls Needed', value: input.required_stalls });
    if (input.guest_count) details.push({ label: 'Guest Count', value: input.guest_count });
    if (input.duration_days) details.push({ label: 'Duration', value: `${input.duration_days} days` });
    if (input.event_location_description) details.push({ label: 'Location', value: input.event_location_description });

    if (details.length === 0 && (!input.product_interest || input.product_interest.length === 0)) {
      return '';
    }

    return /* html */ `
      <div class="lead-details">
        ${details.length > 0 ? /* html */ `
          <div class="details-grid">
            ${details.map(detail => /* html */ `
              <div class="detail-item">
                <span class="detail-label">${detail.label}</span>
                <span class="detail-value">${detail.value}</span>
              </div>
            `).join('')}
          </div>
        ` : ''}
        
        ${input.product_interest && input.product_interest.length > 0 ? /* html */ `
          <div class="products-section">
            <span class="products-label">Products of Interest</span>
            <div class="product-tags">
              ${input.product_interest.map(product => /* html */ `
                <span class="product-tag">${product}</span>
              `).join('')}
            </div>
          </div>
        ` : ''}
        
        ${this.getRequirements(input)}
      </div>
    `;
  };

  getRequirements = (input) => {
    const requirements = [];

    if (input.ada_required) requirements.push('ADA Required');
    if (input.is_local) requirements.push('Local Service');

    if (requirements.length === 0) return '';

    return /* html */ `
      <div class="requirements-section">
        <span class="requirements-label">Requirements</span>
        <div class="requirement-tags">
          ${requirements.map(req => /* html */ `
            <span class="requirement-tag">${req}</span>
          `).join('')}
        </div>
      </div>
    `;
  };

  getDisqualificationAnalysis = (classif) => {
    if (!classif?.reasoning) return '';

    const analysis = this.analyzeDisqualification(classif.reasoning);

    return /* html */ `
      <div class="disqualification-analysis">
        <div class="analysis-title">Disqualification Analysis</div>
        
        <div class="analysis-content">
          <div class="analysis-item">
            <span class="analysis-label">Primary Reason</span>
            <span class="analysis-value reason-${analysis.category.toLowerCase().replace(' ', '-')}">${analysis.category}</span>
          </div>
          
          <div class="analysis-item">
            <span class="analysis-label">Actionable</span>
            <span class="analysis-value actionable-${analysis.actionable ? 'yes' : 'no'}">${analysis.actionable ? 'Yes' : 'No'}</span>
          </div>
          
          ${analysis.suggestion ? /* html */ `
            <div class="suggestion-section">
              <span class="analysis-label">Suggestion</span>
              <p class="suggestion-text">${analysis.suggestion}</p>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  };

  analyzeDisqualification = (reasoning) => {
    if (!reasoning) {
      return {
        category: 'Unknown',
        actionable: false,
        suggestion: 'No reasoning provided for disqualification'
      };
    }

    const lowerReasoning = reasoning.toLowerCase();

    if (lowerReasoning.includes('outside service area') || lowerReasoning.includes('location') || lowerReasoning.includes('geographic')) {
      return {
        category: 'Outside Service Area',
        actionable: false,
        suggestion: 'Consider expanding service area or referring to local partners'
      };
    }

    if (lowerReasoning.includes('budget') || lowerReasoning.includes('price') || lowerReasoning.includes('cost') || lowerReasoning.includes('expensive')) {
      return {
        category: 'Budget Constraints',
        actionable: true,
        suggestion: 'Offer alternative packages or flexible pricing options'
      };
    }

    if (lowerReasoning.includes('timeline') || lowerReasoning.includes('date') || lowerReasoning.includes('time') || lowerReasoning.includes('schedule')) {
      return {
        category: 'Timeline Issues',
        actionable: true,
        suggestion: 'Check for cancellations or offer waitlist options'
      };
    }

    if (lowerReasoning.includes('competitor') || lowerReasoning.includes('already have') || lowerReasoning.includes('existing')) {
      return {
        category: 'Competitor/Existing Service',
        actionable: false,
        suggestion: 'Keep in database for future opportunities'
      };
    }

    if (lowerReasoning.includes('incomplete') || lowerReasoning.includes('insufficient') || lowerReasoning.includes('missing')) {
      return {
        category: 'Insufficient Information',
        actionable: true,
        suggestion: 'Follow up to gather missing information'
      };
    }

    if (lowerReasoning.includes('not interested') || lowerReasoning.includes('no longer') || lowerReasoning.includes('cancelled')) {
      return {
        category: 'No Longer Interested',
        actionable: false,
        suggestion: 'Mark for future follow-up after 6 months'
      };
    }

    return {
      category: 'Other Reasons',
      actionable: false,
      suggestion: 'Review reasoning for potential process improvements'
    };
  };

  getPagination = () => {
    if (!this.classifyData || this.classifyData.total <= this.classifyData.limit) {
      return '';
    }

    return /* html */ `
      <div class="pagination">
        <button class="pagination-btn prev ${this.currentPage <= 1 ? 'disabled' : ''}" 
                ${this.currentPage <= 1 ? 'disabled' : ''}>
          Previous
        </button>
        <span class="pagination-info">
          Page ${this.currentPage} of ${Math.ceil(this.classifyData.total / this.classifyData.limit)}
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
        <h2>No Disqualified Classifications Found</h2>
        <p>There are no disqualified classifications to display at this time.</p>
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

        .disqualified-stats {
          background: var(--warning-background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 10px;
        }

        .disqualified-stats h3 {
          margin: 0 0 12px 0;
          color: var(--warning-color);
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
          color: var(--warning-color);
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .classifications-grid {
          display: grid;
          gap: 16px;
          grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
        }

        .classification-card {
          background: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 16px;
          transition: all 0.2s ease;
          cursor: pointer;
          position: relative;
        }

        .disqualified-card {
          border-left: 4px solid var(--warning-color);
        }

        .classification-card:hover {
          border-color: var(--warning-color);
        }

        .classification-card:focus {
          outline: none;
          border-color: var(--warning-color);
        }

        .classification-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 12px;
        }

        .classification-info {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }

        .classification-info h3 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .disqualified-indicator {
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .disqualified-icon {
          font-size: 1rem;
        }

        .disqualification-badge {
          background: var(--warning-color);
          color: var(--white-color);
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .confidence-badge {
          font-size: 0.7rem;
          padding: 2px 6px;
          border-radius: 10px;
          font-weight: 500;
        }

        .confidence-badge.confidence-high {
          background: var(--success-color);
          color: var(--white-color);
        }

        .confidence-badge.confidence-medium {
          background: var(--warning-color);
          color: var(--white-color);
        }

        .confidence-badge.confidence-low {
          background: var(--danger-color);
          color: var(--white-color);
        }

        .source-badge {
          font-size: 0.7rem;
          padding: 4px 8px;
          border-radius: 12px;
          font-weight: 500;
          text-transform: capitalize;
        }

        .source-badge.source-webform {
          background: var(--accent-color);
          color: var(--white-color);
        }

        .source-badge.source-voice {
          background: var(--create-color);
          color: var(--white-color);
        }

        .source-badge.source-email {
          background: var(--hubspot-color);
          color: var(--white-color);
        }

        .classification-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .disqualification-results,
        .lead-summary,
        .disqualification-analysis {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .results-title,
        .summary-title,
        .analysis-title {
          font-weight: 600;
          color: var(--title-color);
          margin-bottom: 8px;
          font-size: 0.9rem;
        }

        .result-highlights {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 8px;
        }

        .highlight-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .highlight-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .highlight-value {
          font-size: 0.9rem;
          font-weight: 600;
        }

        .highlight-value.disqualified {
          color: var(--warning-color);
        }

        .highlight-value.routing {
          color: var(--accent-color);
        }

        .reasoning-section {
          margin-top: 8px;
        }

        .reasoning-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          font-style: italic;
          color: var(--text-color);
          background: var(--background);
          padding: 8px;
          border-radius: 4px;
        }

        .summary-grid {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 8px;
        }

        .summary-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px;
          background: var(--background);
          border-radius: 4px;
        }

        .summary-icon {
          font-size: 1rem;
          width: 24px;
          text-align: center;
        }

        .summary-content {
          display: flex;
          flex-direction: column;
          gap: 2px;
          flex: 1;
        }

        .summary-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .summary-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .lead-details {
          margin-top: 8px;
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
          gap: 8px;
          margin-bottom: 8px;
        }

        .detail-item {
          background: var(--background);
          border-radius: 4px;
          padding: 8px;
          text-align: center;
        }

        .detail-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .detail-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .products-section,
        .requirements-section {
          margin-top: 8px;
        }

        .products-label,
        .requirements-label {
          display: block;
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
          margin-bottom: 4px;
        }

        .product-tags,
        .requirement-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .product-tag {
          background: var(--accent-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .requirement-tag {
          background: var(--create-color);
          color: var(--white-color);
          font-size: 0.75rem;
          padding: 2px 6px;
          border-radius: 8px;
        }

        .analysis-content {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }

        .analysis-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .analysis-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .analysis-value {
          font-size: 0.9rem;
          font-weight: 600;
        }

        .analysis-value.reason-outside-service-area {
          color: var(--danger-color);
        }

        .analysis-value.reason-budget-constraints {
          color: var(--warning-color);
        }

        .analysis-value.reason-timeline-issues {
          color: var(--accent-color);
        }

        .analysis-value.reason-competitor/existing-service {
          color: var(--gray-color);
        }

        .analysis-value.reason-insufficient-information {
          color: var(--create-color);
        }

        .analysis-value.reason-no-longer-interested {
          color: var(--danger-color);
        }

        .analysis-value.reason-other-reasons {
          color: var(--text-color);
        }

        .analysis-value.actionable-yes {
          color: var(--success-color);
        }

        .analysis-value.actionable-no {
          color: var(--gray-color);
        }

        .suggestion-section {
          margin-top: 8px;
          width: 100%;
        }

        .suggestion-text {
          margin: 4px 0 0 0;
          font-size: 0.85rem;
          line-height: 1.4;
          font-style: italic;
          color: var(--text-color);
        }

        .classification-metadata {
          background: var(--gray-background);
          border-radius: 6px;
          padding: 12px;
        }

        .metadata-row {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 12px;
        }

        .metadata-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .metadata-label {
          font-size: 0.75rem;
          color: var(--gray-color);
          text-transform: uppercase;
          letter-spacing: 0.025em;
        }

        .metadata-value {
          font-size: 0.85rem;
          color: var(--text-color);
          font-weight: 500;
        }

        .metadata-value.confidence-level {
          color: var(--text-color);
          font-weight: 600;
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
          border-color: var(--warning-color);
          color: var(--warning-color);
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
          border-top: 3px solid var(--warning-color);
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
          .classifications-grid {
            grid-template-columns: 1fr;
          }
          
          .metadata-row {
            grid-template-columns: 1fr;
            gap: 8px;
          }
          
          .classification-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .stats-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .details-grid {
            grid-template-columns: 1fr;
          }

          .result-highlights,
          .analysis-content {
            flex-direction: column;
            gap: 8px;
          }
        }
      </style>
    `;
  };
}
