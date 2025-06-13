export default class LatencyOverview extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dash/latency/overview";
    this.latencyData = null;
    this.refreshInterval = null;
    this._loading = true;
    this._error = false;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.fetchLatencyData();
    // Auto-refresh every 1 minute
    this.refreshInterval = setInterval(() => {
      this.fetchLatencyData();
    }, 60000);
  }

  disconnectedCallback() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }

  fetchLatencyData = async () => {
    this._loading = true;
    this._error = false;
    this.render();

    try {
      const response = await this.api.get(this.url, { content: "json" });

      if (response && response.success !== false) {
        this.latencyData = response;
        this._loading = false;
        this._error = false;
      } else {
        this._error = true;
        this._loading = false;
      }
    } catch (error) {
      console.error("Failed to fetch latency data:", error);
      this._error = true;
      this._loading = false;
    }

    this.render();
  }

  getStatusColor(status) {
    switch (status) {
      case 'good': return 'var(--success-color)';
      case 'warning': return 'var(--alt-color)';
      case 'critical': return 'var(--error-color)';
      default: return 'var(--gray-color)';
    }
  }

  getStatusIcon(status) {
    switch (status) {
      case 'good': return '✓';
      case 'warning': return '⚠';
      case 'critical': return '✗';
      default: return '?';
    }
  }

  formatLatency(ms) {
    if (ms === null || ms === undefined) return 'N/A';

    // For very small values (microseconds)
    if (ms < 1) return `${(ms * 1000).toFixed(1)}μs`;

    // For values under 1000ms, show actual number
    if (ms < 1000) return `${ms.toFixed(1)}ms`;

    // For values 1000ms and above, use compact format
    if (ms < 10000) return `${(ms / 1000).toFixed(2)}k ms`;
    if (ms < 100000) return `${(ms / 1000).toFixed(1)}k ms`;
    if (ms < 1000000) return `${Math.round(ms / 1000)}k ms`;

    // For very large values (millions)
    return `${(ms / 1000000).toFixed(1)}M ms`;
  }

  formatTrend(trend) {
    switch (trend) {
      case 'improving': return '↗ Improving';
      case 'degrading': return '↘ Degrading';
      case 'stable': return '→ Stable';
      case 'increasing': return '↗ Increasing';
      case 'decreasing': return '↘ Decreasing';
      default: return '- Unknown';
    }
  }

  getServiceDisplayName(service) {
    const names = {
      'quote': 'Quote Service',
      'location': 'Location Service',
      'gmaps': 'Google Maps API',
      'redis': 'Redis Cache'
    };
    return names[service] || service;
  }

  getTemplate() {
    if (this._loading) {
      return this.getLoadingTemplate();
    }

    if (this._error || !this.latencyData) {
      return this.getErrorTemplate();
    }

    return /* html */`
      ${this.getCSS()}
      <div class="latency-overview">
        <div class="metrics-grid">
          ${this.getPercentileSection()}
          ${this.getAverageSection()}
          ${this.getTrendSection()}
          ${this.getSpikeSection()}
          <!--${this.getAlertsSection()}-->
        </div>

        <div class="summary">
          <div class="summary-item">
            <span class="label">Total Samples:</span>
            <span class="value">${this.latencyData.percentiles.total_samples}</span>
          </div>
          <div class="summary-item">
            <span class="label">Services Active:</span>
            <span class="value">${this.latencyData.percentiles.services_with_data}</span>
          </div>
          <div class="summary-item">
            <span class="label">Overall Status:</span>
            <span class="value status-${this.latencyData.overall_status}">${this.latencyData.overall_status}</span>
          </div>
          <div class="summary-item">
            <span class="label">Health Score:</span>
            <span class="value">${this.latencyData.system_health_score}%</span>
          </div>
          <div class="summary-item">
            <span class="label">Total Spikes:</span>
            <span class="value">${this.latencyData.spikes.total_spikes}</span>
          </div>
          <div class="summary-item">
            <span class="label">Last Updated:</span>
            <span class="value">${new Date(this.latencyData.generated_at).toLocaleTimeString()}</span>
          </div>
        </div>
      </div>
    `;
  }

  getPercentileSection() {
    const services = ['quote', 'location', 'gmaps', 'redis'];

    return /* html */`
      <div class="metric-section">
        <h3>Response Time Percentiles</h3>
        <div class="service-cards">
          ${services.map(service => {
      const data = this.latencyData.percentiles[service];
      if (!data) return '';

      return /* html */`
              <div class="service-card">
                <div class="service-header">
                  <span class="service-name">${this.getServiceDisplayName(service)}</span>
                  <span class="status-badge status-${data.status}">
                    ${this.getStatusIcon(data.status)} ${data.status}
                  </span>
                </div>
                <div class="metrics">
                  <div class="metric">
                    <span class="metric-label">P50</span>
                    <span class="metric-value">${this.formatLatency(data.p50)}</span>
                  </div>
                  <div class="metric">
                    <span class="metric-label">P90</span>
                    <span class="metric-value">${this.formatLatency(data.p90)}</span>
                  </div>
                  <div class="metric">
                    <span class="metric-label">P95</span>
                    <span class="metric-value">${this.formatLatency(data.p95)}</span>
                  </div>
                  <div class="metric">
                    <span class="metric-label">P99</span>
                    <span class="metric-value">${this.formatLatency(data.p99)}</span>
                  </div>
                </div>
                <div class="sample-count">
                  ${data.sample_count} samples
                </div>
              </div>
            `;
    }).join('')}
        </div>
      </div>
    `;
  }

  getAverageSection() {
    const services = ['quote', 'location', 'gmaps', 'redis'];

    return /* html */`
      <div class="metric-section">
        <h3>Average Response Times</h3>
        <div class="service-cards">
          ${services.map(service => {
      const data = this.latencyData.averages[service];
      if (!data) return '';

      return /* html */`
              <div class="service-card average-card">
                <div class="service-header">
                  <span class="service-name">${this.getServiceDisplayName(service)}</span>
                  <span class="status-badge status-${data.status}">
                    ${this.getStatusIcon(data.status)} ${data.status}
                  </span>
                </div>
                <div class="average-display">
                  <span class="average-value">${this.formatLatency(data.average_ms)}</span>
                  <div class="average-meta">
                    <span class="average-label">Average</span>
                    <span class="sample-count-inline">${data.sample_count} samples</span>
                  </div>
                </div>
              </div>
            `;
    }).join('')}
        </div>
      </div>
    `;
  }

  getTrendSection() {
    const services = ['quote', 'location', 'gmaps', 'redis'];

    return /* html */`
      <div class="metric-section">
        <h3>Performance Trends</h3>
        <div class="service-cards">
          ${services.map(service => {
      const data = this.latencyData.trends[service];
      if (!data) return '';

      return /* html */`
              <div class="service-card">
                <div class="service-header">
                  <span class="service-name">${this.getServiceDisplayName(service)}</span>
                  <span class="trend-badge trend-${data.trend}">
                    ${this.formatTrend(data.trend)}
                  </span>
                </div>
                <div class="trend-stats">
                  <div class="stat">
                    <span class="stat-label">Min</span>
                    <span class="stat-value">${this.formatLatency(data.statistics.min_ms)}</span>
                  </div>
                  <div class="stat">
                    <span class="stat-label">Avg</span>
                    <span class="stat-value">${this.formatLatency(data.statistics.average_ms)}</span>
                  </div>
                  <div class="stat">
                    <span class="stat-label">Max</span>
                    <span class="stat-value">${this.formatLatency(data.statistics.max_ms)}</span>
                  </div>
                </div>
                <div class="sample-count">
                  ${data.sample_count} samples
                </div>
              </div>
            `;
    }).join('')}
        </div>
      </div>
    `;
  }

  getSpikeSection() {
    const services = ['quote', 'location', 'gmaps', 'redis'];

    return /* html */`
      <div class="metric-section">
        <h3>Latency Spikes</h3>
        <div class="service-cards">
          ${services.map(service => {
      const data = this.latencyData.spikes[service];
      if (!data) return '';

      return /* html */`
              <div class="service-card">
                <div class="service-header">
                  <span class="service-name">${this.getServiceDisplayName(service)}</span>
                  <span class="spike-count ${data.spike_count > 0 ? 'has-spikes' : 'no-spikes'}">
                    ${data.spike_count} spikes
                  </span>
                </div>
                <div class="spike-stats">
                  <div class="stat">
                    <span class="stat-label">Max Factor</span>
                    <span class="stat-value">${data.max_spike_factor ? `${data.max_spike_factor}x` : 'N/A'}</span>
                  </div>
                  <div class="stat">
                    <span class="stat-label">Affected Endpoint</span>
                    <span class="stat-value endpoint">${data.most_affected_endpoint || 'None'}</span>
                  </div>
                </div>
              </div>
            `;
    }).join('')}
        </div>
      </div>
    `;
  }

  getAlertsSection() {
    const alertsData = this.latencyData.alerts || {};
    const activeAlerts = alertsData.active_alerts || [];

    return /* html */`
      <div class="metric-section">
        <h3>Active Alerts</h3>
        <div class="alerts-summary">
          <div class="alert-counts">
            <div class="alert-count critical">
              <span class="count">${alertsData.critical_count || 0}</span>
              <span class="label">Critical</span>
            </div>
            <div class="alert-count warning">
              <span class="count">${alertsData.warning_count || 0}</span>
              <span class="label">Warning</span>
            </div>
            <div class="alert-count info">
              <span class="count">${alertsData.info_count || 0}</span>
              <span class="label">Info</span>
            </div>
          </div>
          <div class="overall-severity">
            <span class="severity-badge severity-${alertsData.overall_severity}">
              ${alertsData.overall_severity || 'info'}
            </span>
          </div>
        </div>
        ${activeAlerts.length > 0 ? `
          <div class="active-alerts-list">
            ${activeAlerts.map(alert => `
              <div class="alert-item severity-${alert.severity}">
                <span class="alert-service">${alert.service}</span>
                <span class="alert-message">${alert.message}</span>
              </div>
            `).join('')}
          </div>
        ` : `
          <div class="no-alerts">
            <span>No active alerts</span>
          </div>
        `}
      </div>
    `;
  }

  getLoadingTemplate() {
    return /* html */`
      ${this.getCSS()}
      <div class="latency-overview loading">
        <div class="loader">
          <div class="spinner"></div>
          <p>Loading latency data...</p>
        </div>
      </div>
    `;
  }

  getErrorTemplate() {
    return /* html */`
      ${this.getCSS()}
      <div class="latency-overview error">
        <div class="error-message">
          <span class="error-icon">⚠</span>
          <h3>Failed to load latency data</h3>
          <p>Please check your connection and try again.</p>
          <button class="retry-btn" onclick="this.getRootNode().host.fetchLatencyData()">
            Retry
          </button>
        </div>
      </div>
    `;
  }

  getCSS() {
    return /* html */`
      <style>
        :host {
          display: block;
          width: 100%;
          font-family: var(--font-main);
        }

        .latency-overview {
          border-top: var(--border);
          border-bottom: var(--border);
          padding: 1rem 0 2rem 0;
          margin: 0 0 3rem 0;
          color: var(--text-color);
          background: var(--background);
        }

        .metrics-grid {
          display: grid;
          gap: 2rem;
          margin-bottom: 2rem;
        }

        .overall-status.status-good {
          background: color-mix(in srgb, var(--success-color) 15%, transparent);
          color: var(--success-color);
          border: 1px solid color-mix(in srgb, var(--success-color) 30%, transparent);
        }

        .overall-status.status-warning {
          background: color-mix(in srgb, var(--alt-color) 15%, transparent);
          color: var(--alt-color);
          border: 1px solid color-mix(in srgb, var(--alt-color) 30%, transparent);
        }

        .overall-status.status-critical {
          background: color-mix(in srgb, var(--error-color) 15%, transparent);
          color: var(--error-color);
          border: 1px solid color-mix(in srgb, var(--error-color) 30%, transparent);
        }

        .metrics-grid {
          display: grid;
          gap: 2rem;
          margin-bottom: 2rem;
        }

        .metric-section h3 {
          margin: 0 0 1rem 0;
          color: var(--title-color);
          font-size: 1.1rem;
          font-weight: 600;
        }

        .service-cards {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1rem;
        }

        .service-card {
          background: var(--stat-background);
          border: none;
          border-radius: 6px;
          padding: 1rem;
          transition: all 0.2s ease;
        }

        .service-card:hover {
          background: var(--hover-background);
          box-shadow: var(--card-box-shadow-alt);
        }

        .service-card.average-card {
          background: var(--stat-background);
          border: none;
          padding: 0.75rem;
          box-shadow: none;
        }

        .service-card.average-card:hover {
          background: var(--hover-background);
          box-shadow: none;
        }

        .service-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .service-name {
          font-weight: 600;
          color: var(--title-color);
          font-size: 0.9rem;
        }

        .status-badge, .trend-badge, .spike-count {
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
        }

        .status-badge.status-good, .spike-count.no-spikes {
          background: color-mix(in srgb, var(--success-color) 15%, transparent);
          color: var(--success-color);
        }

        .status-badge.status-warning {
          background: color-mix(in srgb, var(--alt-color) 15%, transparent);
          color: var(--alt-color);
        }

        .status-badge.status-critical, .spike-count.has-spikes {
          background: color-mix(in srgb, var(--error-color) 15%, transparent);
          color: var(--error-color);
        }

        .trend-badge.trend-stable, .trend-badge.trend-improving {
          background: color-mix(in srgb, var(--success-color) 15%, transparent);
          color: var(--success-color);
        }

        .trend-badge.trend-degrading, .trend-badge.trend-increasing {
          background: color-mix(in srgb, var(--alt-color) 15%, transparent);
          color: var(--alt-color);
        }

        .metrics {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 0.75rem;
        }

        .metric, .stat {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .metric-label, .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
        }

        .metric-value, .stat-value {
          font-size: 0.9rem;
          color: var(--text-color);
          font-weight: 600;
          font-family: var(--font-mono);
        }

        .stat-value.endpoint {
          font-family: var(--font-main);
          font-size: 0.8rem;
          text-align: right;
          max-width: 120px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .average-display {
          text-align: center;
          margin: 1rem 0;
        }

        .average-card .average-display {
          margin: 0.75rem 0;
          padding: 0.75rem;
          background: color-mix(in srgb, var(--accent-color) 5%, transparent);
          border-radius: 6px;
          border: 1px solid color-mix(in srgb, var(--accent-color) 15%, transparent);
        }

        .average-value {
          display: block;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--accent-color);
          font-family: var(--font-mono);
          margin-bottom: 0.25rem;
        }

        .average-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .average-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
        }

        .sample-count-inline {
          font-size: 0.75rem;
          color: var(--gray-color);
          background: color-mix(in srgb, var(--gray-color) 10%, transparent);
          padding: 0.2rem 0.5rem;
          border-radius: 12px;
          font-weight: 500;
        }

        .trend-stats, .spike-stats {
          display: grid;
          gap: 0.5rem;
        }

        .sample-count {
          margin-top: 0.75rem;
          padding-top: 0.75rem;
          border-top: 1px solid color-mix(in srgb, var(--gray-color) 20%, transparent);
          font-size: 0.8rem;
          color: var(--gray-color);
          text-align: center;
        }

        .summary {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1rem;
          padding: 1rem;
          background: var(--gray-background);
          border-radius: 6px;
          border: var(--border);
        }

        .summary-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .summary-item .label {
          font-size: 0.9rem;
          color: var(--gray-color);
        }

        .summary-item .value {
          font-weight: 600;
          color: var(--text-color);
          font-family: var(--font-mono);
        }

        /* Loading and Error States */
        .latency-overview.loading, .latency-overview.error {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 300px;
        }

        .loader {
          text-align: center;
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid var(--gray-background);
          border-top: 3px solid var(--accent-color);
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin: 0 auto 1rem;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        .error-message {
          text-align: center;
          color: var(--text-color);
        }

        .error-icon {
          font-size: 2rem;
          color: var(--error-color);
          display: block;
          margin-bottom: 1rem;
        }

        .retry-btn {
          margin-top: 1rem;
          padding: 0.5rem 1rem;
          background: var(--action-linear);
          color: var(--white-color);
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
        }

        .retry-btn:hover {
          opacity: 0.9;
        }

        /* Alerts Section Styles */
        .alerts-summary {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .alert-counts {
          display: flex;
          gap: 1rem;
        }

        .alert-count {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 0.5rem;
          border-radius: 6px;
          min-width: 60px;
        }

        .alert-count.critical {
          background: color-mix(in srgb, var(--error-color) 10%, transparent);
        }

        .alert-count.warning {
          background: color-mix(in srgb, var(--alt-color) 10%, transparent);
        }

        .alert-count.info {
          background: color-mix(in srgb, var(--accent-color) 10%, transparent);
        }

        .alert-count .count {
          font-size: 1.2rem;
          font-weight: 700;
          font-family: var(--font-mono);
        }

        .alert-count.critical .count {
          color: var(--error-color);
        }

        .alert-count.warning .count {
          color: var(--alt-color);
        }

        .alert-count.info .count {
          color: var(--accent-color);
        }

        .alert-count .label {
          font-size: 0.7rem;
          color: var(--gray-color);
          text-transform: uppercase;
          font-weight: 500;
        }

        .severity-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 4px;
          font-size: 0.8rem;
          font-weight: 600;
          text-transform: capitalize;
        }

        .severity-badge.severity-critical {
          background: var(--error-color);
          color: white;
        }

        .severity-badge.severity-warning {
          background: var(--alt-color);
          color: white;
        }

        .severity-badge.severity-info {
          background: var(--accent-color);
          color: white;
        }

        .active-alerts-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .alert-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem;
          border-radius: 4px;
          border-left: 3px solid;
        }

        .alert-item.severity-critical {
          background: color-mix(in srgb, var(--error-color) 5%, transparent);
          border-left-color: var(--error-color);
        }

        .alert-item.severity-warning {
          background: color-mix(in srgb, var(--alt-color) 5%, transparent);
          border-left-color: var(--alt-color);
        }

        .alert-item.severity-info {
          background: color-mix(in srgb, var(--accent-color) 5%, transparent);
          border-left-color: var(--accent-color);
        }

        .alert-service {
          font-weight: 600;
          color: var(--title-color);
        }

        .alert-message {
          font-size: 0.9rem;
          color: var(--text-color);
        }

        .no-alerts {
          text-align: center;
          padding: 2rem;
          color: var(--gray-color);
          font-style: italic;
        }
      </style>
    `;
  }
}
