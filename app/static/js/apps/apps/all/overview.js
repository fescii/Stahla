export default class Overview extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/dashboard/overview";
    this.dashboardData = null; // Initialize as null instead of using hardcoded data
    this.cacheUpdateInterval = null;
    this._block = false;
    this._empty = false;
    this._loading = true; // Add loading state
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    // Fetch dashboard data first
    this.fetchDashboardData();

    // Set up event listeners and intervals
    this._addServiceItemListeners();
    this._addCachePillListeners();
    window.addEventListener("scroll", this.handleScroll);
  }

  disconnectedCallback() {
    window.removeEventListener("scroll", this.handleScroll);
    if (this.checkComponentsInterval) {
      clearInterval(this.checkComponentsInterval);
    }
    if (this.cacheUpdateInterval) {
      clearInterval(this.cacheUpdateInterval);
    }
  }

  // Fetch dashboard data using the API
  fetchDashboardData = async () => {
    this._loading = true;
    this._block = true;
    this.render(); // Re-render to show loader

    const dashboardContainer = this.shadowObj.querySelector(".container");

    try {
      const response = await this.api.get(this.url, { content: "json" });
      // Check for 401 Unauthorized response
      if (
        response.status_code === 401 ||
        (response.error_message &&
          response.error_message.includes("validate credentials"))
      ) {
        console.log("Authentication required for dashboard access");
        this._loading = false;
        // Show access form when unauthorized
        this.app.showAccess();
        return;
      }

      if (!response.success || !response.data) {
        this._empty = true;
        this._loading = false;
        this.dashboardData = null;
        this.render();
        this.activateRefresh();
        return;
      }

      this._loading = false;
      this._block = false;
      this._empty = false;

      // Log data structure to help debug inconsistencies
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname.includes('dev')) {
        console.log('Dashboard data structure:',
          Object.keys(response.data).join(', '),
          response.data.redis_counters ? Object.keys(response.data.redis_counters).join(', ') : 'No redis_counters');

        // Add detailed logs for quote request values
        console.log('Quote Request Values:', {
          top_level: {
            total: response.data.quote_requests_total,
            successful: response.data.quote_requests_successful,
            failed: response.data.quote_requests_failed
          },
          redis_counters: response.data.redis_counters?.quote_requests || 'Not found in redis_counters'
        });

        // Check if any counters exist at all
        console.log('All Redis Counters:', response.data.redis_counters);
      }

      this.dashboardData = response;
      this.render();

      // After data is loaded and rendered, initialize components
      this._formatErrorTimestamps();
      this._updateCacheTimer();
      this._addServiceItemListeners();
      this._addCachePillListeners();
    } catch (error) {
      console.error("Error fetching dashboard data:", error);

      // Check if the error is an unauthorized error (401)
      if (
        error.status === 401 ||
        (error.response && error.response.status === 401)
      ) {
        console.log("Authentication required for dashboard access");
        this._loading = false;
        // Show login form when unauthorized
        this.app.showLogin();
        return;
      }

      this._loading = false;
      this._empty = true;
      this.dashboardData = null;
      this.render();
      this.activateRefresh();
    }
  };

  activateRefresh = () => {
    const retryBtn = this.shadowObj.querySelector("button.finish");
    if (retryBtn) {
      retryBtn.addEventListener("click", () => {
        // Reset states
        this._block = false;
        this._empty = false;

        // Start fetch again
        this.fetchDashboardData();
      });
    }
  };

  handleScroll = () => {
    // Event handling for scroll if needed
  };

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody = () => {
    // Show loader when loading
    if (this._loading) {
      return /* html */ `<div class="container">${this.getLoader()}</div>`;
    }

    // Show error message if empty and no data
    if (this._empty || !this.dashboardData) {
      return /* html */ `<div class="container">${this.getWrongMessage()}</div>`;
    }

    // Show dashboard with actual data
    return /* html */ `
      <div class="container">
        <div class="header">
          <h1>Dashboard Overview</h1>
          <p class="subtitle">Stats and status overview of SDR AI & Pricing Platform</p>
        </div>
        ${this._getDashboardOverviewHTML()}
        <div class="dashboard-grid">
          <div class="main-content">
            ${this._getExternalServicesPanelHTML()}
            ${this._getCacheHitMissPanelHTML()}
          </div>
              
          <div class="sidebar">
            ${this._getCacheStatisticsPanelHTML()}
            ${this._getCacheLastUpdatedPanelHTML()}
          </div>
        </div>
      </div>
    `;
  };

  _getDashboardOverviewHTML = () => {
    const overviewData = this.dashboardData.data; // Use the whole data object from the response
    const redisCounters = overviewData.redis_counters || {};

    // Get data from direct properties or from nested redis_counters
    // Quote requests - either from top level or from redis_counters
    const quoteRequestsTotal = overviewData.quote_requests_total ||
      (redisCounters.quote_requests && redisCounters.quote_requests.total) || 0;
    const quoteRequestsSuccess = overviewData.quote_requests_successful ||
      (redisCounters.quote_requests && redisCounters.quote_requests.success) || 0;
    const quoteRequestsFailed = overviewData.quote_requests_failed ||
      (redisCounters.quote_requests && redisCounters.quote_requests.error) || 0;

    // Location lookups - check both top level or redis_counters structure
    const locationLookupsTotal = overviewData.location_lookups_total ||
      (redisCounters.location_lookups && redisCounters.location_lookups.total) || 0;
    // If success/failed values don't exist, set them to 0
    const locationLookupsSuccess = overviewData.location_lookups_successful || 0;
    const locationLookupsFailed = overviewData.location_lookups_failed || 0;

    // Report summary from the provided path
    const reportSummary = overviewData.report_summary || {
      total_reports: 0,
      successful_reports: 0,
      failed_reports: 0,
    };

    // GMaps API stats from redis_counters
    const gmapsApiStats = (redisCounters.gmaps_api) || { calls: 0, errors: 0 };

    return /* html */ `
    <div class="dashboard-overview">
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Total Reports</div>
                <div class="stat-icon icon-reports">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${(reportSummary.total_reports || 0).toLocaleString()}</div>
            <div class="stat-details">
                <span class="stat-success">${(reportSummary.successful_reports || 0).toLocaleString()} Success</span> &bull;
                <span class="stat-error">${(reportSummary.failed_reports || 0).toLocaleString()} Failed</span>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Quote Requests</div>
                <div class="stat-icon icon-requests">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${quoteRequestsTotal.toLocaleString()}</div>
            <div class="stat-details">
                <span class="stat-success">${quoteRequestsSuccess.toLocaleString()} Success</span> &bull;
                <span class="stat-error">${quoteRequestsFailed.toLocaleString()} Failed</span>
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">Location Lookups</div>
                <div class="stat-icon icon-lookups">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${locationLookupsTotal.toLocaleString()}</div>
            <div class="stat-details">
                ${locationLookupsSuccess || locationLookupsFailed ?
        `<span class="stat-success">${locationLookupsSuccess.toLocaleString()} Success</span> &bull;
                   <span class="stat-error">${locationLookupsFailed.toLocaleString()} Failed</span>` :
        `<span>Total lookups</span>`}
            </div>
        </div>
        
        <div class="stat-card">
            <div class="stat-header">
                <div class="stat-title">API Calls (GMaps)</div>
                <div class="stat-icon icon-api">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline>
                    </svg>
                </div>
            </div>
            <div class="stat-value">${gmapsApiStats.calls.toLocaleString()}</div>
            <div class="stat-details">
                ${gmapsApiStats.errors > 0
        ? `<span class="stat-error">${gmapsApiStats.errors.toLocaleString()} Errors</span>`
        : "<span>No errors</span>"
      }
            </div>
        </div>
    </div>
    `;
  };

  _getExternalServicesPanelHTML = () => {
    const services = this.dashboardData.data.external_services;
    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">External Services</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">
           <div class="services-grid">
             ${services.map(service => {
      const isOk = service.status.toLowerCase() === 'ok' || service.status.toLowerCase() === 'operational';
      const statusClass = isOk ? 'status-ok' : 'status-error';
      const statusText = isOk ? 'OK' : 'Error';
      const formattedDate = service.last_checked ? this._formatDate(service.last_checked) : 'N/A';

      return /* html */ `
              <div class="service-pill" title="${service.details || ''}" tabindex="0" role="button" aria-label="Service: ${service.name}, Status: ${service.status}">
                <div class="service-pill-header">
                  <div class="service-pill-name">${service.name}</div>
                  <div class="service-pill-status ${statusClass}">${statusText}</div>
                </div>
                <div class="service-pill-date">Last sync: ${formattedDate}</div>
              </div>`;
    }).join('')}
           </div>
        </div>
    </div>
    `;
  };

  _getRecentErrorsPanelHTML = () => {
    const errors = this.dashboardData.data.recent_errors;
    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Recent Errors</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">
            <div class="errors-list">
                ${errors && errors.length > 0
        ? errors
          .map(
            (error) => /* html */ `
                <div class="error-item">
                    <div class="error-timestamp">${error.timestamp}</div>
                    <div class="error-message">${error.message}</div>
                </div>
                `
          )
          .join("")
        : "<p>No recent errors.</p>"
      }
            </div>
        </div>
    </div>
    `;
  };

  _getCacheHitMissPanelHTML = () => {
    const cacheStats = this.dashboardData.data.cache_stats;
    const pricingHitRate = (
      cacheStats.hit_miss_ratio_pricing.percentage * 100
    ).toFixed(0);
    const mapsHitRate = (
      cacheStats.hit_miss_ratio_maps.percentage * 100
    ).toFixed(0);
    const lastUpdated = cacheStats.pricing_cache_last_updated ?
      this._formatDate(cacheStats.pricing_cache_last_updated) : 'N/A';

    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Cache Hit/Miss</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">            
            <div class="services-grid cache-hit-miss-grid">
                <div class="service-pill cache-hit-pill" tabindex="0">
                    <div class="service-pill-header">
                        <div class="service-pill-name">Pricing Cache</div>
                        <div class="cache-pill-value hit-rate-badge">${pricingHitRate}%</div>
                    </div>
                    <div class="cache-bar-container">
                        <div class="cache-bar">
                            <div class="cache-bar-hit" style="width: ${pricingHitRate}%">
                                <div class="cache-bar-shine"></div>
                            </div>
                        </div>
                    </div>
                    <div class="hit-stats">
                        <div>
                            <span class="hit-count-dot"></span>
                            <span class="hit-count-label">Hits</span>
                            <span class="hit-count-value">${cacheStats.hit_miss_ratio_pricing.hits.toLocaleString()}</span>
                        </div>
                        <div>
                            <span class="miss-count-dot"></span>
                            <span class="miss-count-label">Misses</span>
                            <span class="miss-count-value">${cacheStats.hit_miss_ratio_pricing.misses.toLocaleString()}</span>
                        </div>
                    </div>
                    <!--<div class="service-pill-date">Last updated: ${lastUpdated}</div>-->
                </div>
                
                <div class="service-pill cache-hit-pill" tabindex="0">
                    <div class="service-pill-header">
                        <div class="service-pill-name">Maps Cache</div>
                        <div class="cache-pill-value hit-rate-badge">${mapsHitRate}%</div>
                    </div>
                    <div class="cache-bar-container">
                        <div class="cache-bar">
                            <div class="cache-bar-hit" style="width: ${mapsHitRate}%">
                                <div class="cache-bar-shine"></div>
                            </div>
                        </div>
                    </div>
                    <div class="hit-stats">
                        <div>
                            <span class="hit-count-dot"></span>
                            <span class="hit-count-label">Hits</span>
                            <span class="hit-count-value">${cacheStats.hit_miss_ratio_maps.hits.toLocaleString()}</span>
                        </div>
                        <div>
                            <span class="miss-count-dot"></span>
                            <span class="miss-count-label">Misses</span>
                            <span class="miss-count-value">${cacheStats.hit_miss_ratio_maps.misses.toLocaleString()}</span>
                        </div>
                    </div>
                    <!--<div class="service-pill-date">Last updated: ${lastUpdated}</div>-->
                </div>
            </div>
        </div>
    </div>
    `;
  };

  _getCacheStatisticsPanelHTML = () => {
    const cacheStats = this.dashboardData.data.cache_stats;
    // Convert bytes to KB
    const pricingCatalogSizeKB = (
      cacheStats.pricing_catalog_size_bytes / 1024
    ).toFixed(0);
    // Format the last update time
    const lastUpdated = cacheStats.pricing_cache_last_updated ?
      this._formatDate(cacheStats.pricing_cache_last_updated) : 'N/A';

    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Cache Statistics</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">
            <div class="services-grid cache-services-grid">
                <div class="service-pill cache-pill" tabindex="0">
                    <div class="service-pill-header">
                        <div class="service-pill-name">Total Keys</div>
                        <div class="cache-pill-value">${cacheStats.total_redis_keys.toLocaleString()}</div>
                    </div>
                    <div class="service-pill-date">Last updated: ${lastUpdated}</div>
                </div>
                
                <div class="service-pill cache-pill" tabindex="0">
                    <div class="service-pill-header">
                        <div class="service-pill-name">Memory Used</div>
                        <div class="cache-pill-value">${cacheStats.redis_memory_used_human}</div>
                    </div>
                    <div class="service-pill-date">Last updated: ${lastUpdated}</div>
                </div>
                
                <div class="service-pill cache-pill" tabindex="0">
                    <div class="service-pill-header">
                        <div class="service-pill-name">Pricing Cache</div>
                        <div class="cache-pill-value">${pricingCatalogSizeKB} KB</div>
                    </div>
                    <div class="service-pill-date">Last updated: ${lastUpdated}</div>
                </div>
                
                <div class="service-pill cache-pill" tabindex="0">
                    <div class="service-pill-header">
                        <div class="service-pill-name">Maps Cache</div>
                        <div class="cache-pill-value">${cacheStats.maps_cache_key_count.toLocaleString()}</div>
                    </div>
                    <div class="service-pill-date">Last updated: ${lastUpdated}</div>
                </div>
            </div>
        </div>
    </div>
    `;
  };

  _getSyncStatusPanelHTML = () => {
    const syncStatus = this.dashboardData.data.sync_status;
    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Sync Status</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"></path><path d="M3 12a9 9 0 0 1 15-6.7L21 8"></path><path d="M3 12a9 9 0 0 0 15 6.7L21 16"></path><path d="M21 22v-6h-6"></path></svg>
            </div>
        </div>
        <div class="panel-body">
            <div class="sync-status">
                <div class="sync-indicator ${syncStatus.is_sync_task_running
        ? "status-warning"
        : "status-ok"
      }"></div>
                <div class="sync-text">${syncStatus.is_sync_task_running
        ? "Sync task currently running"
        : "Last successful sync completed"
      }</div>
                <div class="sync-timestamp">${this._formatDate(
        syncStatus.last_successful_sync_timestamp,
        {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }
      )}</div>
            </div>
            
            ${syncStatus.recent_sync_errors &&
        syncStatus.recent_sync_errors.length > 0
        ? /* html */ `
            <div class="errors-list" style="margin-top: 1rem;">
                ${syncStatus.recent_sync_errors
          .map(
            (err) => /* html */ `
                <div class="error-item">
                    <div class="error-timestamp">${err.timestamp}</div>
                    <div class="error-message">${err.error}</div>
                </div>
                `
          )
          .join("")}
            </div>
            `
        : ""
      }
        </div>
    </div>
    `;
  };

  _getCacheLastUpdatedPanelHTML = () => {
    // The timer itself is handled by _updateCacheTimer
    // This just provides the static structure
    return /* html */ `
      <div class="panel">
        <div class="panel-header">
          <h2 class="panel-title">Cache Last Updated</h2>
          <div class="panel-actions">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
          </div>
        </div>
        <div class="panel-body update-time">
          <div id="cacheUpdateTimer" class="stat-value">--:--:--</div>
          <p id="cacheUpdateDate" style="color:var(--gray-color); margin-top:0.5rem;">Loading date...</p>
        </div>
      </div>
    `;
  };

  _formatDate = (dateString, options) => {
    if (!dateString) return "N/A";
    try {
      const defaultOptions = {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      };
      return new Date(dateString).toLocaleDateString(
        "en-US",
        options || defaultOptions
      );
    } catch (e) {
      return dateString; // fallback
    }
  };

  _formatErrorTimestamps = () => {
    const errorItems = this.shadowObj.querySelectorAll(".error-timestamp");
    errorItems.forEach((item) => {
      const timestamp = item.textContent;
      if (timestamp && (timestamp.includes("UTC") || timestamp.includes("Z"))) {
        // Check for Z as well
        const date = new Date(timestamp.replace(" UTC", "")); // Replace UTC if present
        item.textContent = this._formatDate(date);
      }
    });

    // Initialize the counter animation for hit rates
    this._initHitRateCounters();
  };

  _initHitRateCounters = () => {
    const counterElements = this.shadowObj.querySelectorAll(
      ".hit-rate-value .counter"
    );

    counterElements.forEach((element) => {
      const targetValue = parseInt(element.textContent);
      const duration = 1500; // milliseconds
      const startTime = performance.now();

      // Start with 0 and animate to target value
      element.textContent = "0";

      const animateCount = (currentTime) => {
        const elapsedTime = currentTime - startTime;
        const progress = Math.min(elapsedTime / duration, 1);

        // Easing function for smoother animation
        const easedProgress = this._easeOutQuart(progress);

        const currentValue = Math.floor(easedProgress * targetValue);
        element.textContent = currentValue;

        if (progress < 1) {
          requestAnimationFrame(animateCount);
        } else {
          element.textContent = targetValue; // Ensure we end at exact target
        }
      };

      requestAnimationFrame(animateCount);
    });
  };

  // Easing function for smoother animation
  _easeOutQuart = (x) => {
    return 1 - Math.pow(1 - x, 4);
  };

  _updateCacheTimer = () => {
    if (!this.dashboardData || !this.dashboardData.data) return;

    const timerElement = this.shadowObj.getElementById("cacheUpdateTimer");
    const lastUpdateString =
      this.dashboardData.data.cache_stats.pricing_cache_last_updated;

    if (!timerElement || !lastUpdateString) return;

    const lastUpdate = new Date(lastUpdateString);

    const updateTimerDisplay = () => {
      const now = new Date();
      const diff = now - lastUpdate;

      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);

      timerElement.textContent =
        String(hours).padStart(2, "0") +
        ":" +
        String(minutes).padStart(2, "0") +
        ":" +
        String(seconds).padStart(2, "0");

      if (hours >= 1) {
        timerElement.style.color = "var(--error-color)";
      } else {
        timerElement.style.color = "var(--title-color)"; // Reset if less than an hour
      }
    };

    updateTimerDisplay(); // Initial call
    if (this.cacheUpdateInterval) clearInterval(this.cacheUpdateInterval); // Clear existing interval
    this.cacheUpdateInterval = setInterval(updateTimerDisplay, 1000);

    // Also update the date display below the timer
    const dateDisplayElement = this.shadowObj.getElementById("cacheUpdateDate");
    if (dateDisplayElement) {
      dateDisplayElement.textContent = this._formatDate(lastUpdate, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    }
  };

  _addServiceItemListeners = () => {
    const servicePills = this.shadowObj.querySelectorAll(".service-pill");
    servicePills.forEach((pill) => {
      // Extract service details for tooltip if available
      const details = pill.getAttribute("title");

      // Handle both click and keyboard interactions for accessibility
      pill.addEventListener("click", this._handleServicePillInteraction);
      pill.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this._handleServicePillInteraction.call(pill);
        }
      });
    });
  };

  _handleServicePillInteraction = function () {
    const nameElement = this.querySelector(".service-pill-name");
    const statusElement = this.querySelector(".service-pill-status");
    const dateElement = this.querySelector(".service-pill-date");

    if (nameElement && statusElement) {
      const serviceName = nameElement.textContent.trim();
      const status = statusElement.textContent.trim();
      const lastSync = dateElement ? dateElement.textContent.trim() : 'N/A';

      console.log(`Service: ${serviceName}, Status: ${status}, ${lastSync}`);

      const details = this.getAttribute("title");
      if (details) {
        console.log(`Details: ${details}`);
      }

      // Add click animation effect
      this.style.transform = "scale(0.97)";
      setTimeout(() => {
        this.style.transform = "";
      }, 200);
    }
  };

  _addCachePillListeners = () => {
    // Regular cache pills
    const cachePills = this.shadowObj.querySelectorAll(".cache-pill");
    cachePills.forEach((pill) => {
      // Handle both click and keyboard interactions for accessibility
      pill.addEventListener("click", this._handleCachePillInteraction);
      pill.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this._handleCachePillInteraction.call(pill);
        }
      });
    });

    // Cache hit/miss pills
    const cacheHitPills = this.shadowObj.querySelectorAll(".cache-hit-pill");
    cacheHitPills.forEach((pill) => {
      pill.addEventListener("click", this._handleCacheHitPillInteraction);
      pill.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this._handleCacheHitPillInteraction.call(pill);
        }
      });
    });
  };

  _handleCachePillInteraction = function () {
    const nameElement = this.querySelector(".service-pill-name");
    const valueElement = this.querySelector(".cache-pill-value");

    if (nameElement && valueElement) {
      const statName = nameElement.textContent.trim();
      const statValue = valueElement.textContent.trim();

      // Add click animation effect
      this.style.transform = "scale(0.97)";
      setTimeout(() => {
        this.style.transform = "";
      }, 200);

      console.log(`Cache Stat: ${statName}, Value: ${statValue}`);
    }
  };

  _handleCacheHitPillInteraction = function () {
    const nameElement = this.querySelector(".service-pill-name");
    const valueElement = this.querySelector(".hit-rate-badge");
    const hitElement = this.querySelector(".hit-count-value");
    const missElement = this.querySelector(".miss-count-value");

    if (nameElement && valueElement) {
      const cacheName = nameElement.textContent.trim();
      const hitRate = valueElement.textContent.trim();
      const hits = hitElement ? hitElement.textContent.trim() : 'N/A';
      const misses = missElement ? missElement.textContent.trim() : 'N/A';

      // Add click animation effect
      this.style.transform = "scale(0.97)";
      setTimeout(() => {
        this.style.transform = "";
      }, 200);

      console.log(`${cacheName} - Hit Rate: ${hitRate}, Hits: ${hits}, Misses: ${misses}`);
    }
  };

  getLoader() {
    return /* html */ `
      <div class="loader-container">
        <div class="loader"></div>
      </div>
    `;
  }

  getEmptyMsg = () => {
    return /*html*/ `
      <div class="finish">
        <h2 class="finish__title">No dashboard data available</h2>
        <p class="desc">
          There are no stats available right now. Please check back later.
        </p>
      </div>
    `;
  };

  getWrongMessage = () => {
    return /*html*/ `
      <div class="finish">
        <h2 class="finish__title">Something went wrong!</h2>
        <p class="desc">
         An error occurred while fetching the dashboard data. Please check your connection and try again.
        </p>
        <button class="finish">Retry</button>
      </div>
    `;
  };

  getStyles = () => {
    // Improved styles with better structure and visual hierarchy
    return /* html */ `
      <style>
        :host {
          display: block; /* Ensure the host element behaves as a block */
          width: 100%;
          background-color: var(--background);
          font-family: var(--font-text), sans-serif;
          line-height: 1.6;
          color: var(--text-color);
        }

        * {
          box-sizing: border-box;
        }

        .header {
          display: flex;
          flex-direction: column;
          margin-bottom: 1.5rem;
          position: relative;
        }

        .header > h1 {
          font-size: 1.875rem;
          font-weight: 700;
          margin: 0;
          padding: 0;
          color: var(--title-color);
          line-height: 1.2;
          letter-spacing: -0.01em;
        }

        .header > p.subtitle {
          color: var(--gray-color);
          margin: 0.25rem 0 0;
          padding: 0;
          font-size: .9rem;
          opacity: 0.9;
        }

        div.loader-container {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          min-height: 150px;
          min-width: 100%;
        }

        div.loader-container > .loader {
          width: 20px;
          aspect-ratio: 1;
          border-radius: 50%;
          background: var(--accent-linear);
          display: grid;
          animation: l22-0 2s infinite linear;
        }

        div.loader-container > .loader:before {
          content: "";
          grid-area: 1/1;
          margin: 15%;
          border-radius: 50%;
          background: var(--second-linear);
          transform: rotate(0deg) translate(150%);
          animation: l22 1s infinite;
        }

        div.loader-container > .loader:after {
          content: "";
          grid-area: 1/1;
          margin: 15%;
          border-radius: 50%;
          background: var(--accent-linear);
          transform: rotate(0deg) translate(150%);
          animation: l22 1s infinite;
        }

        div.loader-container > .loader:after {
          animation-delay: -.5s
        }

        @keyframes l22-0 {
          100% {transform: rotate(1turn)}
        }

        @keyframes l22 {
          100% {transform: rotate(1turn) translate(150%)}
        }

        .container {
          max-width: 100%;
          margin: 0 auto;
          padding: 20px 10px;
          position: relative;
          display: flex;
          flex-direction: column;
          flex-flow: columns;
          height: max-content;
        }

        @media (max-width: 768px) {
          .container {
            padding: 20px 10px;
          }
        }

        .dashboard-header {
          margin-bottom: 20px;
          display: flex;
          flex-flow: column;
          gap: 0;
        }

        .dashboard-title {
          font-size: 1.8rem;
          font-weight: 600;
          margin: 0;
          color: var(--title-color);
          font-family: var(--font-main), sans-serif;
        }

        .dashboard-subtitle {
          color: var(--gray-color);
          margin: 0;
          font-size: 1rem;
        }

        .dashboard-overview {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1.25rem;
          margin: 1.5rem 0 2rem;
        }

        .stat-card {
          background-color: var(--stat-background);
          border-radius: 12px;
          padding: 1.25rem;
          box-shadow: var(--card-box-shadow-alt);
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
        }

        .stat-card:after {
          content: "";
          position: absolute;
          top: 0;
          right: 0;
          height: 4px;
          width: 100%;
          background: var(--accent-linear);
          opacity: 0;
          transition: opacity 0.3s ease;
        }

        .stat-card:hover {
          transform: translateY(-5px);
          box-shadow: var(--card-box-shadow);
        }

        .stat-card:hover:after {
          opacity: 1;
        }

        .stat-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }

        .stat-title {
          font-weight: 600;
          color: var(--gray-color);
          font-size: 0.92rem;
          text-transform: capitalize;
          letter-spacing: 0.5px;
        }

        .stat-icon {
          width: 42px;
          height: 42px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--white-color);
          box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
          transform: rotate(0deg);
          transition: transform 0.3s ease;
        }

        .stat-card:hover .stat-icon {
          transform: rotate(5deg) scale(1.05);
        }

        .icon-reports { background: var(--action-linear); }
        .icon-requests { background: var(--second-linear); }
        .icon-lookups { background: linear-gradient(0deg, #3a0ca3, #7209b7); }
        .icon-api { background: linear-gradient(0deg, #7400b8, #5390d9); }

        .stat-value {
          font-size: 2.25rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.75rem;
          font-family: var(--font-main), sans-serif;
          letter-spacing: -0.02em;
          line-height: 1;
        }

        .stat-details {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.875rem;
          flex-wrap: wrap;
          position: relative;
        }

        .stat-details:before {
          content: "";
          position: absolute;
          left: 0;
          top: -0.5rem;
          width: 2rem;
          height: 2px;
          background: var(--accent-linear);
          opacity: 0.5;
          transition: width 0.3s ease;
        }

        .stat-card:hover .stat-details:before {
          width: 3rem;
        }

        .stat-success {
          color: #10b981;
          font-weight: 500;
        }

        .stat-error {
          color: var(--error-color);
          font-weight: 500;
        }

        .dashboard-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 1.5rem;
        }

        @media (min-width: 1024px) {
          .dashboard-grid {
        grid-template-columns: 1fr 1fr;
        grid-template-rows: auto auto;
        align-items: start;
        gap: 2rem;
        }

        .main-content {
        display: grid;
        grid-template-rows: 1fr 1fr;
        gap: 1.5rem;
        height: fit-content;
        }

        .sidebar {
        display: grid;
        grid-template-rows: 1fr 1fr;
        gap: 1.5rem;
        height: fit-content;
        align-content: start;
        }

        .hit-rate-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 1.5rem;
        }
        }

        @media (min-width: 768px) and (max-width: 1023px) {
          .hit-rate-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 1.25rem;
          }
        }

        .main-content {
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .sidebar {
          position: sticky;
          top: 1rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        .panel {
          background-color: var(--hover-background);
          border-radius: 8px;
          padding: 0;
          box-shadow: var(--card-box-shadow-alt);
          transition: box-shadow 0.2s ease;
          overflow: hidden;
        }

        .panel:hover {
          box-shadow: var(--card-box-shadow);
        }

        .panel-header {
          padding: 12px 1.25rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
          position: relative;
          box-shadow: 0 1px 0 rgba(107, 114, 128, 0.1);
        }

        .panel-header:after {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          height: 100%;
          width: 4px;
          background: var(--accent-linear);
          opacity: 0.7;
        }

        .panel-title {
          padding: 0;
          margin: 0;
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          font-family: var(--font-main), sans-serif;
          letter-spacing: -0.01em;
        }

        .panel-actions {
          display: flex;
          gap: 0.5rem;
          color: var(--gray-color);
        }

        .panel-body {
          padding: 1.25rem;
          width: 100%;
        }

        .sidebar .panel-body {
          padding: 10px 10px 1.2rem;
          width: 100%;
        }

        .panel-body.update-time {
          padding: 1.25rem;
          display: flex;
          flex-flow: column;
          justify-content: space-between;
        }

        .services-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .service-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1.25rem;
          border-radius: 12px;
          background-color: var(--stat-background);
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          position: relative;
          overflow: hidden;
        }

        .service-item:after {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          height: 100%;
          width: 4px;
          background: var(--accent-linear);
          opacity: 0;
          transition: opacity 0.25s ease, width 0.3s ease;
        }

        .service-item:before {
          content: "";
          position: absolute;
          right: -50px;
          top: -50px;
          width: 100px;
          height: 100px;
          border-radius: 50%;
          background: var(--accent-linear);
          opacity: 0;
          transform: scale(0);
          transition: transform 0.5s ease, opacity 0.5s ease;
          z-index: 0;
        }

        .service-item:hover {
          transform: translateX(5px);
          box-shadow: var(--card-box-shadow);
          background-color: var(--background);
        }

        .service-item:hover:after {
          opacity: 1;
        }

        .service-item:hover:before {
          opacity: 0.05;
          transform: scale(1);
        }

        .service-item:active {
          transform: translateX(8px) scale(0.99);
        }

        .service-clicked {
          box-shadow: 0 2px 8px rgba(var(--accent-color-rgb, 0, 123, 255), 0.2);
        }

        .service-info {
          display: flex;
          flex-direction: column;
          gap: 6px;
          flex: 1;
          max-width: 75%;
          padding-left: 5px;
          position: relative;
          z-index: 1;
        }
        .service-name {
          font-weight: 600;
          color: var(--title-color);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          transition: all 0.2s ease;
          font-size: 1.05rem;
          letter-spacing: -0.01em;
          position: relative;
        }

        .service-name:after {
          content: "";
          position: absolute;
          bottom: -2px;
          left: 0;
          width: 0;
          height: 2px;
          background: var(--accent-linear);
          transition: width 0.3s ease;
          opacity: 0.7;
        }

        .service-item:hover .service-name {
          color: var(--accent-color, #0d6efd);
        }

        .service-item:hover .service-name:after {
          width: 100%;
        }

        .service-timestamp {
          font-size: 0.8rem;
          color: var(--gray-color);
          display: flex;
          align-items: center;
          gap: 4px;
          opacity: 0.9;
          transition: opacity 0.2s ease;
          font-weight: 400;
        }

        .service-item:hover .service-timestamp {
          opacity: 1;
        }

        .service-timestamp:before {
          content: "";
          display: inline-block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background-color: var(--accent-color, #0d6efd);
          opacity: 0.5;
          margin-right: 4px;
        }

        .service-status {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
          font-weight: 500;
          white-space: nowrap;
          border-radius: 6px;
          transition: background-color 0.2s ease, transform 0.2s ease;
        }
        .service-item:hover .service-status {
          transform: scale(1.05);
        }
        /* Status-based styling for the service-status container */
        .service-item .status-ok + .service-status {
          background-color: rgba(16, 185, 129, 0.1);
        }
        .service-item .status-warning + .service-status {
          background-color: rgba(245, 158, 11, 0.1);
        }
        .service-item .status-error + .service-status {
          background-color: rgba(239, 68, 68, 0.1);
        }

        .status-indicator {
          width: 14px;
          height: 14px;
          border-radius: 50%;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.5);
        }

        .status-indicator::after {
          content: "";
          position: absolute;
          width: 24px;
          height: 24px;
          border-radius: 50%;
          background-color: inherit;
          animation: pulse 2s infinite cubic-bezier(0.215, 0.61, 0.355, 1);
          z-index: -1;
        }

        .status-ok,
        .status-operational {
          background-color: var(--success-color);
        }

        .status-warning,
        .status-degraded {
          background: var(--second-linear);
        }

        .status-error,
        .status-outage {
          background-color: var(--error-color);
        }

        @keyframes pulse {
          0% { transform: scale(0.3); opacity: 0.8; }
          70% { transform: scale(1); opacity: 0; }
          100% { transform: scale(1.2); opacity: 0; }
        }

        .errors-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          padding: 0.5rem 0;
        }

        .error-item {
          padding: 1rem 1.25rem;
          border-radius: 10px;
          background-color: var(--error-background);
          display: flex;
          flex-flow: column;
          gap: 8px;
          box-shadow: var(--card-box-shadow-alt);
          transition: transform 0.2s ease, box-shadow 0.2s ease;
          position: relative;
        }

        .error-item:before {
          content: "";
          position: absolute;
          left: 0;
          top: 0;
          height: 100%;
          width: 3px;
          background-color: var(--error-color);
        }

        .error-item:hover {
          transform: translateX(3px);
          box-shadow: 0 4px 12px rgba(var(--error-color-rgb, 255, 0, 0), 0.15);
        }

        .error-timestamp {
          font-size: 0.8rem;
          color: var(--gray-color);
          font-weight: 500;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .error-timestamp:before {
          content: "";
          display: inline-block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background-color: var(--error-color);
        }

        .error-message {
          font-family: var(--font-mono), monospace;
          font-size: 0.9rem;
          color: var(--text-color);
          line-height: 1.5;
          padding: 0.5rem;
          background: rgba(0, 0, 0, 0.05);
          border-radius: 4px;
          overflow-x: auto;
        }

        .chart-container {
          width: 100%;
          height: 300px;
          margin-top: 1.5rem;
          border-radius: 8px;
          overflow: hidden;
        }

        .cache-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 1rem;
          padding: 10px 0;
        }

        .cache-metric {
          padding: 0;
          display: flex;
          border-right: var(--border);
          flex-direction: column;
          align-items: center;
          justify-content: center;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
          text-align: center;
        }

        .cache-metric:last-child {
          border-right: none; /* Remove border for last item */
        }
        
        .cache-metric-value {
          font-size: 1.35rem;
          font-weight: 700;
          color: var(--title-color);
          font-family: var(--font-main), sans-serif;
          line-height: 1.2;
          letter-spacing: -0.02em;
          margin-bottom: 0.5rem;
          background: var(--accent-linear);
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          text-align: center;
        }
        
        .cache-metric-label {
          color: var(--gray-color);
          font-size: 0.85rem;
          text-align: center;
          font-weight: 500;
        }
        
        /* Hit Rate Charts Styling */
        .hit-rate-grid { 
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1.5rem;
          margin-top: 1.5rem;
        }
        
        .hit-rate-chart { 
          padding: 1.25rem;
          border-radius: 12px;
          background-color: var(--stat-background);
          box-shadow: var(--card-box-shadow-alt);
          transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .hit-rate-chart:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
        }
        
        .hit-rate-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }
        
        .hit-rate-title {
          font-weight: 600;
          color: var(--title-color);
          font-size: 1rem;
        }
        
        .hit-rate-value {
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--accent-color);
        }
        
        .hit-rate-value .counter {
          background: var(--accent-linear);
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        
        .cache-bar-container {
          margin-bottom: 1rem;
        }
        
        .cache-bar {
          height: 10px;
          background-color: rgba(107, 114, 128, 0.2);
          border-radius: 5px;
          overflow: hidden;
          position: relative;
        }
        
        .cache-bar-hit {
          height: 100%;
          background: var(--accent-linear);
          border-radius: 5px;
          position: relative;
          overflow: hidden;
        }
        
        .cache-bar-shine {
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(
            90deg,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.3) 50%,
            rgba(255, 255, 255, 0) 100%
          );
          animation: shine 2s infinite;
        }
        
        @keyframes shine {
          0% { left: -100%; }
          100% { left: 100%; }
        }
        
        .cache-bar-labels {
          display: flex;
          justify-content: space-between;
          font-size: 0.75rem;
          color: var(--gray-color);
          margin-top: 0.25rem;
        }
        
        .hit-stats {
          display: flex;
          justify-content: space-between;
        }
        
        .hit-stat-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }
        
        .hit-count-dot,
        .miss-count-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
        }
        
        .hit-count-dot {
          background: var(--accent-linear);
        }
        
        .miss-count-dot {
          background-color: var(--gray-color);
        }
        
        .hit-count-label,
        .miss-count-label {
          color: var(--gray-color);
        }
        
        .hit-count-value,
        .miss-count-value {
          font-weight: 600;
          color: var(--title-color);
          }
        
        /* External Services Panel Styling */
        .services-cards {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
          gap: 1rem;
          width: 100%;
          margin: 0;
          padding: 0;
        }
        
        @media (max-width: 768px) {
          .services-cards {
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 0.75rem;
          }
        }
        
        @media (min-width: 1024px) {
          .services-cards {
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1.25rem;
          }
        }
        
        .service-card {
          background-color: var(--stat-background);
          border-radius: 10px;
          padding: 1.25rem;
          box-shadow: var(--card-box-shadow-alt);
          transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
          cursor: pointer;
        }
        
        .service-card:after {
          content: "";
          position: absolute;
          bottom: 0;
          left: 0;
          width: 100%;
          height: 3px;
          opacity: 0;
          transition: opacity 0.3s ease;
        }
        
        .service-card:hover {
          transform: translateY(-5px);
          box-shadow: var(--card-box-shadow);
          background-color: var(--background);
        }
        
        .service-card:hover:after {
          opacity: 1;
        }
        
        .service-card:hover .service-card-title {
          color: var(--accent-color);
        }
        
        .service-card:active {
          transform: translateY(-2px) scale(0.98);
        }
        
        .service-card[title]:hover:before {
          content: attr(title);
          position: absolute;
          bottom: 0.5rem;
          right: 0.5rem;
          font-size: 0.75rem;
          color: var(--gray-color);
          opacity: 0.7;
          max-width: 90%;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .service-card .status-ok:after,
        .service-card .status-operational:after,
        .service-card:has(.status-ok):after,
        .service-card:has(.status-operational):after {
          background: var(--success-color);
        }
        
        .service-card .status-warning:after,
        .service-card .status-degraded:after,
        .service-card:has(.status-warning):after,
        .service-card:has(.status-degraded):after {
          background: var(--second-linear);
        }
        
        .service-card .status-error:after,
        .service-card .status-outage:after,
        .service-card:has(.status-error):after,
        .service-card:has(.status-outage):after {
          background: var(--error-color);
        }
        
        .service-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }
        
        .service-card-title {
          font-weight: 600;
          font-size: 1.1rem;
          color: var(--title-color);
          margin-right: 0.5rem;
        }
        
        .service-card-body {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .service-status {
          font-size: 0.9rem;
          font-weight: 500;
          padding: 0.35rem 0.75rem;
          border-radius: 50px;
          text-transform: capitalize;
        }
        
        .status-ok + .service-status,
        .status-operational + .service-status {
          background-color: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }
        
        .status-warning + .service-status,
        .status-degraded + .service-status {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        
        .status-error + .service-status,
        .status-outage + .service-status {
          background-color: rgba(239, 68, 68, 0.15);
          color: var(--error-color);
        }
        
        .service-timestamp {
          font-size: 0.8rem;
          color: var(--gray-color);
          white-space: nowrap;
        }

        /* Service Pill Design */
        .services-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          gap: 0.75rem;
          width: 100%;
        }
        
        @media (max-width: 768px) {
          .services-grid {
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          }
        }
        
        @media (min-width: 1024px) {
          .services-grid {
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1.5rem;
          }
        }
        
        .service-pill {
          display: flex;
          flex-direction: column;
          padding: 0.8rem 1rem;
          background-color: var(--stat-background);
          border-radius: 8px;
          transition: all 0.2s ease;
          cursor: pointer;
          box-shadow: var(--card-box-shadow-alt);
          position: relative;
          overflow: hidden;
        }
        
        .service-pill:hover {
          transform: translateY(-2px);
          box-shadow: var(--card-box-shadow);
          background-color: var(--hover-background);
        }
        
        .service-pill:active {
          transform: translateY(0) scale(0.98);
        }
        
        .service-pill-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 4px;
        }
        
        .service-pill-name {
          font-weight: 600;
          color: var(--title-color);
          font-size: 0.95rem;
          letter-spacing: -0.01em;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }
        
        .service-pill-status {
          font-size: 0.8rem;
          font-weight: 600;
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          min-width: 40px;
          text-align: center;
        }
        
        .service-pill-status.status-ok {
          color: var(--accent-color);
          background-color: rgba(0, 96, 223, 0.1);
        }
        
        .service-pill-status.status-error {
          color: var(--error-color);
          background-color: rgba(236, 75, 25, 0.1);
        }
        
        .service-pill-date {
          font-size: 0.75rem;
          color: var(--gray-color);
          margin-top: 2px;
          text-overflow: ellipsis;
          overflow: hidden;
          white-space: nowrap;
        }

        /* Cache Pills Styling */
        .cache-pill {
          background-color: var(--stat-background);
        }

        .cache-pill:hover {
          background-color: var(--hover-background);
        }

        .cache-pill-value {
          font-size: 1rem;
          font-weight: 700;
          color: var(--title-color);
          padding: 0.15rem 0.5rem;
          border-radius: 4px;
          background: var(--accent-linear);
          background-clip: text;
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        
        .cache-services-grid {
          grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        }
        
        @media (max-width: 768px) {
          .cache-services-grid {
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
          }
          
          .cache-pill-value {
            font-size: 0.9rem;
          }
        }
        
        @media (min-width: 1024px) {
          .cache-services-grid {
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
          }
          
          .cache-pill-value {
            font-size: 1.1rem;
          }
        }

        /* Cache Hit/Miss Pills Styling */
        .cache-hit-miss-grid {
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
        }
        
        .cache-hit-pill {
          padding: 1rem;
        }
        
        .cache-hit-pill .cache-bar-container {
          margin: 0.75rem 0;
          height: 8px;
        }
        
        .hit-rate-badge {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--accent-color);
          padding: 0.2rem 0.6rem;
          border-radius: 4px;
          background-color: rgba(0, 96, 223, 0.1);
          -webkit-text-fill-color: var(--accent-color);
        }
        
        .cache-hit-pill .hit-stats {
          display: flex;
          justify-content: space-between;
          margin-bottom: 0.75rem;
          font-size: 0.85rem;
        }
        
        .cache-hit-pill .hit-count-dot,
        .cache-hit-pill .miss-count-dot {
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-right: 4px;
        }
        
        .cache-hit-pill .hit-count-dot {
          background-color: var(--accent-color);
        }
        
        .cache-hit-pill .miss-count-dot {
          background-color: var(--gray-color);
        }
        
        .cache-hit-pill .hit-count-value,
        .cache-hit-pill .miss-count-value {
          font-weight: 600;
          margin-left: 4px;
        }
        
        @media (max-width: 768px) {
          .cache-hit-miss-grid {
            grid-template-columns: 1fr;
          }
        }
      </style>
      `;
  };
}