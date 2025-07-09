export default class LatencyOverview extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/latency/overview/";
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

  // Format numbers according to specified rules
  formatNumber = (value) => {
    const num = parseFloat(value);

    // Handle invalid numbers
    if (isNaN(num)) return '0';

    // 0-999: Remains as is
    if (num < 1000) {
      return num.toString();
    }

    // 1,000 - 9,999: Add comma (e.g., 5,475)
    if (num < 10000) {
      return num.toLocaleString();
    }

    // 10,000 - 99,999: Format as X.Xk (e.g., 45.6k)
    if (num < 100000) {
      return (num / 1000).toFixed(1) + 'k';
    }

    // 100,000 - 999,999: Format as XXXk (e.g., 546k)
    if (num < 1000000) {
      return Math.round(num / 1000) + 'k';
    }

    // 1,000,000 - 9,999,999: Format as X.XXm (e.g., 5.47m)
    if (num < 10000000) {
      return (num / 1000000).toFixed(2) + 'm';
    }

    // 10,000,000 - 99,999,999: Format as XX.Xm (e.g., 46.3m)
    if (num < 100000000) {
      return (num / 1000000).toFixed(1) + 'm';
    }

    // 100,000,000 - 999,999,999: Format as XXXm (e.g., 546m)
    if (num < 1000000000) {
      return Math.round(num / 1000000) + 'm';
    }

    // 1,000,000,000 and above: Format as X.XXb, XX.Xb, XXXb, etc.
    if (num < 10000000000) {
      return (num / 1000000000).toFixed(2) + 'b';
    }

    if (num < 100000000000) {
      return (num / 1000000000).toFixed(1) + 'b';
    }

    // 100b and above: No decimal
    return Math.round(num / 1000000000) + 'b';
  };


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
        <div class="system-summary">
          <div class="system-stats">
            <div class="stat-item">
              <span class="stat-value">${this.latencyData.system_health_score}%</span>
              <span class="stat-label">Health</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${this.formatNumber(this.latencyData.percentiles.total_samples)}</span>
              <span class="stat-label">Samples</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">${this.formatNumber(this.latencyData.spikes.total_spikes)}</span>
              <span class="stat-label">Spikes</span>
            </div>
            <div class="stat-item">
              <span class="stat-value time">${new Date(this.latencyData.generated_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: 'numeric', hour12: true })}</span>
              <span class="stat-label">Updated</span>
            </div>
          </div>
        </div>

        <div class="services-overview">
          ${this.getCompactServicesSection()}
        </div>
      </div>
    `;
  }

  getCompactServicesSection() {
    const services = ['quote', 'location', 'gmaps', 'redis'];

    return /* html */`
      <div class="services-list">
        ${services.map(service => {
      const percentileData = this.latencyData.percentiles[service];
      const averageData = this.latencyData.averages[service];
      const trendData = this.latencyData.trends[service];
      const spikeData = this.latencyData.spikes[service];

      if (!percentileData || !averageData) return '';

      return /* html */`
            <div class="service-compact">
              <div class="service-header-compact">
                <div class="service-info">
                  <h3 class="service-name">${this.getServiceDisplayName(service)}</h3>
                  <!--<span class="status-badge status-${percentileData.status}">
                    ${this.getStatusIcon(percentileData.status)} ${percentileData.status}
                  </span>-->
                </div>
                <div class="service-primary-metric">
                  <span class="primary-value">${this.formatLatency(averageData.average_ms)}</span>
                  <span class="primary-label">Avg Response</span>
                </div>
              </div>
              
              <div class="service-details">
                <div class="metric-group">
                  <div class="metric-row">
                    <span class="metric-label">Percentiles</span>
                    <div class="metric-values">
                      <span class="metric-item">P50: ${this.formatLatency(percentileData.p50)}</span>
                      <span class="metric-item">P95: ${this.formatLatency(percentileData.p95)}</span>
                      <span class="metric-item">P99: ${this.formatLatency(percentileData.p99)}</span>
                    </div>
                  </div>
                  
                  ${trendData ? `
                    <div class="metric-row">
                      <span class="metric-label">Trend</span>
                      <div class="metric-values">
                        <span class="trend-badge trend-${trendData.trend}">${this.formatTrend(trendData.trend)}</span>
                        <span class="metric-item">Min: ${this.formatLatency(trendData.statistics.min_ms)}</span>
                        <span class="metric-item">Max: ${this.formatLatency(trendData.statistics.max_ms)}</span>
                      </div>
                    </div>
                  ` : ''}
                  
                  ${spikeData ? `
                    <div class="metric-row">
                      <span class="metric-label">Spikes</span>
                      <div class="metric-values">
                        <span class="spike-count ${spikeData.spike_count > 0 ? 'has-spikes' : 'no-spikes'}">
                          ${spikeData.spike_count} spikes
                        </span>
                        ${spikeData.max_spike_factor ? `
                          <span class="metric-item">Max: ${spikeData.max_spike_factor}x</span>
                        ` : ''}
                      </div>
                    </div>
                  ` : ''}
                </div>
                
                <div class="service-footer">
                  <span class="sample-count">${percentileData.sample_count} samples</span>
                  ${spikeData && spikeData.most_affected_endpoint ? `
                    <span class="affected-endpoint">${spikeData.most_affected_endpoint}</span>
                  ` : ''}
                </div>
              </div>
            </div>
          `;
    }).join('')}
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
          min-width: 100%;
          font-family: var(--font-main);
        }

        .latency-overview {
          padding: 1rem 0 2rem 0;
          margin: 0 0 3rem 0;
          color: var(--text-color);
          background: var(--background);
          max-width: 100%;
          width: 100%;
        }

        /* System Summary Styles */
        .system-summary {
          padding: 0;
          margin-bottom: 2rem;
        }

        .system-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .system-header h2 {
          margin: 0;
          color: var(--title-color);
          font-size: 1.3rem;
          font-weight: 600;
        }

        .overall-status {
          padding: 7px 1rem;
          border-radius: 10px;
          font-size: 0.8rem;
          font-weight: 600;
          text-transform: uppercase;
        }

        .system-stats {
          display: flex;
          flex-flow: row;
          flex-wrap: wrap;
          justify-content: space-between;
          gap: 1rem;
        }

        .system-stats > .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 10px;
          min-width: 80px;
          width: max-content;
          background: var(--gray-background);
          border-radius: 12px;
          border: 1px solid color-mix(in srgb, var(--alt-color) 20%, transparent);
        }

        .system-stats > .stat-item > .stat-value {
          font-size: 1.2rem;
          font-weight: 700;
          color: var(--alt-color);
          font-family: var(--font-main);
          margin-bottom: 0.25rem;
        }

        .system-stats > .stat-item > .stat-value.time {
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--alt-color);
          font-family: var(--font-main);
          margin-bottom: 0.5rem;
        }

        .system-stats > .stat-item > .stat-label {
          font-size: 0.8rem;
          color: var(--gray-color);
          text-align: center;
          font-weight: 500;
        }

        /* Services Overview Styles */
        .services-overview {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .services-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .service-compact {
          overflow: hidden;
          padding: 0 5px 25px;
          border-bottom: 1px solid color-mix(in srgb, var(--alt-color) 80%, transparent);
          transition: all 0.2s ease;
        }

        .service-header-compact {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 7px 0;
          border-bottom: 1px solid color-mix(in srgb, var(--gray-color) 15%, transparent);
        }

        .service-info {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .service-info h3 {
          margin: 0;
          color: var(--title-color);
          font-size: 1rem;
          font-weight: 600;
        }

        .service-primary-metric {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          text-align: right;
        }

        .primary-value {
          font-size: 1rem;
          font-weight: 600;
          color: var(--accent-color);
          font-family: var(--font-mono);
          margin-bottom: 0.2rem;
        }

        .primary-label {
          font-size: 0.7rem;
          color: var(--gray-color);
          font-weight: 500;
          font-family: var(--font-read);
          text-transform: uppercase;
        }

        .metric-group {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .metric-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem 0;
          border-bottom: 1px solid color-mix(in srgb, var(--gray-color) 10%, transparent);
        }

        .metric-row:last-child {
          border-bottom: none;
        }

        .metric-label {
          font-size: 0.85rem;
          color: var(--gray-color);
          font-weight: 600;
          min-width: 80px;
        }

        .metric-values {
          display: flex;
          gap: 1rem;
          align-items: center;
          flex-wrap: wrap;
        }

        .metric-item {
          font-size: 0.8rem;
          color: var(--text-color);
          font-family: var(--font-mono);
          background: color-mix(in srgb, var(--gray-color) 8%, transparent);
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-weight: 500;
        }

        .service-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 1rem;
          padding-top: 1rem;
          border-top: 1px solid color-mix(in srgb, var(--gray-color) 15%, transparent);
        }

        .sample-count {
          font-size: 0.8rem;
          color: var(--gray-color);
          padding: 7px 0;
          font-weight: 500;
        }

        .affected-endpoint {
          font-size: 0.75rem;
          color: var(--text-color);
          font-family: var(--font-mono);
          background: color-mix(in srgb, var(--alt-color) 10%, transparent);
          padding: 0.25rem 0.6rem;
          border-radius: 4px;
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
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

        .trend-badge {
          font-size: 0.8rem;
          padding: 0.3rem 0.6rem;
          border-radius: 4px;
          font-weight: 600;
          text-transform: none;
        }

        .trend-badge.trend-stable, .trend-badge.trend-improving {
          background: color-mix(in srgb, var(--success-color) 15%, transparent);
          color: var(--success-color);
        }

        .trend-badge.trend-degrading, .trend-badge.trend-increasing {
          background: color-mix(in srgb, var(--alt-color) 15%, transparent);
          color: var(--alt-color);
        }

        .trend-badge.trend-decreasing {
          background: color-mix(in srgb, var(--success-color) 15%, transparent);
          color: var(--success-color);
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
          border: none;
          padding: 1rem;
          transition: all 0.2s ease;
        }

        .service-card:hover {
          background: var(--hover-background);
          box-shadow: var(--card-box-shadow-alt);
        }

        .service-card.average-card {
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
          padding: 7px 0;
          font-weight: 500;
        }

        .trend-stats, .spike-stats {
          display: grid;
          gap: 0.5rem;
        }

        .sample-count {
          padding: 7px 0;
          font-size: 0.8rem;
          color: var(--gray-color);
          text-align: center;
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

        /* Responsive Design */
        @media (max-width: 768px) {
          .system-stats {
            grid-template-columns: repeat(2, 1fr);
          }
          
          .service-header-compact {
            flex-direction: column;
            gap: 1rem;
            text-align: center;
          }
          
          .service-primary-metric {
            align-items: center;
          }
          
          .metric-values {
            flex-direction: column;
            gap: 0.5rem;
          }
          
          .service-footer {
            flex-direction: column;
            gap: 0.5rem;
            text-align: center;
          }
        }
      </style>
    `;
  }
}
