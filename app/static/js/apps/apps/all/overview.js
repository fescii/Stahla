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
            ${this._getCacheStatisticsPanelHTML()}
          </div>
              
          <div class="sidebar">
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
                ${
                  gmapsApiStats.errors > 0
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
           <div class="services-cards">
             ${services.map(service => /* html */ `
               <div class="service-card" title="${service.details || ''}" tabindex="0" role="button" aria-label="Service: ${service.name}, Status: ${service.status}">
                 <div class="service-card-header">
                   <div class="service-card-title">${service.name}</div>
                   <span class="status-indicator status-${service.status.toLowerCase()}"></span>
                 </div>
                 <div class="service-card-body">
                   <div class="service-status">${service.status}</div>
                   ${service.last_checked ? `<div class="service-timestamp">${this._formatDate(service.last_checked)}</div>` : ''}
                 </div>
               </div>
             `).join('')}
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
                ${
                  errors && errors.length > 0
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

  _getCacheStatisticsPanelHTML = () => {
    const cacheStats = this.dashboardData.data.cache_stats;
    const pricingHitRate = (
      cacheStats.hit_miss_ratio_pricing.percentage * 100
    ).toFixed(0);
    const mapsHitRate = (
      cacheStats.hit_miss_ratio_maps.percentage * 100
    ).toFixed(0);
    // Convert bytes to KB
    const pricingCatalogSizeKB = (
      cacheStats.pricing_catalog_size_bytes / 1024
    ).toFixed(0);

    return /* html */ `
    <div class="panel">
        <div class="panel-header">
            <h2 class="panel-title">Cache Statistics</h2>
            <div class="panel-actions">
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
            </div>
        </div>
        <div class="panel-body">
            <div class="cache-grid">
                <div class="cache-metric">
                    <div class="cache-metric-value">${cacheStats.total_redis_keys.toLocaleString()}</div>
                    <div class="cache-metric-label">Total Redis Keys</div>
                </div>
                <div class="cache-metric">
                    <div class="cache-metric-value">${
                      cacheStats.redis_memory_used_human
                    }</div>
                    <div class="cache-metric-label">Redis Memory Used</div>
                </div>
                <div class="cache-metric">
                    <div class="cache-metric-value">${pricingCatalogSizeKB} KB</div>
                    <div class="cache-metric-label">Pricing Cache Size</div>
                </div>
                <div class="cache-metric">
                    <div class="cache-metric-value">${cacheStats.maps_cache_key_count.toLocaleString()}</div>
                    <div class="cache-metric-label">Maps Cache Keys</div>
                </div>
            </div>
            
            <div class="hit-rate-grid">
                <div class="hit-rate-chart">
                    <div class="hit-rate-header">
                        <div class="hit-rate-title">Pricing Cache Hit Rate</div>
                        <div class="hit-rate-value">
                            <span class="counter">${pricingHitRate}</span><span>%</span>
                        </div>
                    </div>
                    <div class="cache-bar-container">
                        <div class="cache-bar">
                            <div class="cache-bar-hit" style="width: ${pricingHitRate}%">
                                <div class="cache-bar-shine"></div>
                            </div>
                        </div>
                        <div class="cache-bar-labels">
                            <span>0%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                    </div>
                    <div class="hit-stats">
                        <div class="hit-stat-item">
                            <span class="hit-count-dot"></span>
                            <span class="hit-count-label">Hits</span>
                            <span class="hit-count-value">${cacheStats.hit_miss_ratio_pricing.hits.toLocaleString()}</span>
                        </div>
                        <div class="hit-stat-item">
                            <span class="miss-count-dot"></span>
                            <span class="miss-count-label">Misses</span>
                            <span class="miss-count-value">${cacheStats.hit_miss_ratio_pricing.misses.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
                
                <div class="hit-rate-chart">
                    <div class="hit-rate-header">
                        <div class="hit-rate-title">Maps Cache Hit Rate</div>
                        <div class="hit-rate-value">
                            <span class="counter">${mapsHitRate}</span><span>%</span>
                        </div>
                    </div>
                    <div class="cache-bar-container">
                        <div class="cache-bar">
                            <div class="cache-bar-hit" style="width: ${mapsHitRate}%">
                                <div class="cache-bar-shine"></div>
                            </div>
                        </div>
                        <div class="cache-bar-labels">
                            <span>0%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                    </div>
                    <div class="hit-stats">
                        <div class="hit-stat-item">
                            <span class="hit-count-dot"></span>
                            <span class="hit-count-label">Hits</span>
                            <span class="hit-count-value">${cacheStats.hit_miss_ratio_maps.hits.toLocaleString()}</span>
                        </div>
                        <div class="hit-stat-item">
                            <span class="miss-count-dot"></span>
                            <span class="miss-count-label">Misses</span>
                            <span class="miss-count-value">${cacheStats.hit_miss_ratio_maps.misses.toLocaleString()}</span>
                        </div>
                    </div>
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
                <div class="sync-indicator ${
                  syncStatus.is_sync_task_running
                    ? "status-warning"
                    : "status-ok"
                }"></div>
                <div class="sync-text">${
                  syncStatus.is_sync_task_running
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
            
            ${
              syncStatus.recent_sync_errors &&
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
          <div id="cacheUpdateTimer" class="stat-value" style="text-align:center; font-size:1.5rem;">--:--:--</div>
          <p id="cacheUpdateDate" style="text-align:center; color:var(--gray-color); margin-top:0.5rem;">Loading date...</p>
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
    const serviceItems = this.shadowObj.querySelectorAll(".service-item");
    serviceItems.forEach((item) => {
      // Extract service details for tooltip if available
      const details = item.getAttribute("title");

      // Handle both click and keyboard interactions for accessibility
      item.addEventListener("click", this._handleServiceItemInteraction);
      item.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this._handleServiceItemInteraction.call(item);
        }
      });

      // Add hover effect
      item.addEventListener("mouseenter", function () {
        this.style.transform = "translateX(5px)";
      });

      item.addEventListener("mouseleave", function () {
        this.style.transform = "";
      });
    });
  };

  _handleServiceItemInteraction = function () {
    const serviceNameElement = this.querySelector(".service-name");
    const statusElement = this.querySelector(".service-status");

    if (serviceNameElement && statusElement) {
      const serviceName = serviceNameElement.textContent.trim();
      const status = statusElement.textContent.trim();
      console.log(`Service: ${serviceName}, Status: ${status}`);

      const details = this.getAttribute("title");
      if (details) {
        console.log(`Details: ${details}`);
      }

      // Add click animation effect
      this.classList.add("service-clicked");
      this.style.transform = "translateX(10px)";
      setTimeout(() => {
        this.style.transform = "translateX(5px)";
        setTimeout(() => {
          this.style.transform = "";
          this.classList.remove("service-clicked");
        }, 150);
      }, 150);
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
    // Styles unchanged from original
    return /* html */ `
      <style>
        :host {
          display: block; /* Ensure the host element behaves as a block */
          background-color: var(--background);
          font-family: var(--font-text), sans-serif;
          line-height: 1.6;
          color: var(--text-color);
        }

        .header {
          display: flex;
          flex-direction: column;
          gap: 0;
        }

        .header > h1 {
          font-size: 1.875rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          color: var(--title-color);
          line-height: 1.2;
        }

        .header > p.subtitle {
          color: var(--gray-color);
          margin: 0;
          padding: 0;
          font-size: .9rem;
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
          padding: 1.5rem;
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
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap:20px;
          margin: 20px 0;
        }
        
        .stat-card {
          background-color: var(--background);
          border-radius: 12px;
          padding: 10px 10px;
          border: var(--border);
          transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
          transform: translateY(-5px);
        }
        
        .stat-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
        }
        
        .stat-title {
          font-weight: 600;
          color: var(--gray-color);
          font-size: 0.92rem;
          text-transform: capitalize;
          letter-spacing: 0.5px;
        }
        
        .stat-icon {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--white-color);
        }
        
        .icon-reports { background: var(--action-linear); }
        .icon-requests { background: var(--second-linear); }
        .icon-lookups { background: linear-gradient(0deg, #3a0ca3, #7209b7); }
        .icon-api { background: linear-gradient(0deg, #7400b8, #5390d9); }
        
        .stat-value {
          font-size: 2rem;
          font-weight: 700;
          color: var(--title-color);
          margin-bottom: 0.5rem;
        }
        
        .stat-details {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }
        
        .stat-success { color: #10b981; }
        .stat-error { color: var(--error-color); }
        
        .dashboard-grid {
          display: flex;
          flex-flow: column;
          gap: 20px;
        }
        
        .panel {
          background-color: var(--background);
          border-top: var(--border);
          padding: 0;
        }
        
        .panel-header {
          padding: 0;
          border-bottom: var(--border);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .panel-title {
          padding: 0;
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--title-color);
          font-family: var(--font-main), sans-serif;
        }
        
        .panel-actions { display: flex; gap: 0.5rem; }
        .panel-body { padding: 10px 0; width: 100%; }

        .panel-body.update-time {
          display: flex;
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
          padding: 1rem 15px;
          border-radius: 10px;
          background-color: var(--hover-background);
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          cursor: pointer;
          box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          position: relative;
          overflow: hidden;
          border: 1px solid transparent;
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
        .service-item:hover { 
          transform: translateX(5px);
          box-shadow: 0 6px 12px rgba(0, 0, 0, 0.09);
          border-color: rgba(var(--accent-color-rgb, 0, 123, 255), 0.15);
        }
        .service-item:hover:after {
          opacity: 1;
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
          gap: 4px;
          flex: 1;
          max-width: 75%;
          padding-left: 5px;
        }
        .service-name { 
          font-weight: 600; 
          color: var(--title-color);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          transition: color 0.2s ease;
        }
        .service-item:hover .service-name {
          color: var(--accent-color, #0d6efd);
        }
        .service-timestamp { 
          font-size: 0.75rem; 
          color: var(--gray-color);
          display: flex;
          align-items: center;
          gap: 4px;
          opacity: 0.9;
          transition: opacity 0.2s ease;
        }
        .service-item:hover .service-timestamp {
          opacity: 1;
        }
        .service-timestamp:before {
          content: "•";
          font-size: 1rem;
          color: var(--gray-color);
          line-height: 0;
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
          width: 12px; 
          height: 12px; 
          border-radius: 50%; 
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .status-indicator::after {
          content: "";
          position: absolute;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background-color: inherit;
          animation: pulse 1.5s infinite;
        }
        .status-ok { 
          background-color: var(--success-color); 
        } 
        .status-warning { 
          background: var(--second-linear); 
        } 
        .status-error { 
          background-color: var(--error-color); 
        }
        
        @keyframes pulse {
          0% { transform: scale(1); opacity: 1; }
          70% { transform: scale(1.5); opacity: 0; }
          100% { transform: scale(1); opacity: 0; }
        }

        .errors-list { display: flex; flex-direction: column; gap: 20px; padding: 5px 0 10px; }
        .error-item {
          padding: 5px 12px;
          border-radius: 8px;
          background-color: var(--error-background);
          display: flex;
          flex-flow: column;
          gap: 4px;
        }
        .error-timestamp { font-size: 0.8rem; color: var(--gray-color); }
        .error-message { font-family: var(--font-mono), monospace; font-size: 0.9rem; color: var(--text-color); }
        
        .chart-container { width: 100%; height: 300px; margin-top: 1rem; }
        
        .cache-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 1rem;
          margin-top: 1rem;
        }
        .cache-metric {
          background-color: var(--background);
          border: var(--border);
          border-radius: 8px;
          box-shadow: var(--card-box-shadow-alt);
          padding: 1rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .cache-metric:hover {
          transform: translateY(-3px);
          box-shadow: var(--card-box-shadow);
        }
        
        /* Hit Rate Charts Styling */
        .hit-rate-grid { 
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1rem;
          margin-top: 1.5rem;
        }
        
        .hit-rate-chart { 
          padding: 1rem;
          border-radius: 12px;
          background-color: var(--background);
          border: var(--border);
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
          margin-bottom: 1.2rem;
        }
        
        .hit-rate-title {
          font-size: 1rem;
          margin: 0;
          font-weight: 600;
          color: var(--title-color);
        }
        
        .hit-rate-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--title-color);
          display: flex;
          align-items: baseline;
        }
        
        .hit-rate-value .counter {
          display: inline-block;
          min-width: 3ch;
          text-align: right;
        }
        
        .cache-bar-container {
          margin-bottom: 1rem;
          position: relative;
        }
        
        .cache-bar {
          height: 12px;
          width: 100%;
          border-radius: 10px;
          overflow: hidden;
          background-color: rgba(var(--background-rgb, 255, 255, 255), 0.6);
          box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
          position: relative;
        }
        
        .cache-bar-hit {
          height: 100%;
          background: var(--accent-linear);
          border-radius: 10px;
          position: relative;
          overflow: hidden;
          transition: width 1s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        .cache-bar-shine {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: linear-gradient(
            90deg, 
            rgba(255, 255, 255, 0) 0%, 
            rgba(255, 255, 255, 0.2) 50%, 
            rgba(255, 255, 255, 0) 100%
          );
          transform: translateX(-100%);
          animation: shine 3s infinite;
        }
        
        @keyframes shine {
          0% { transform: translateX(-100%); }
          20% { transform: translateX(100%); }
          100% { transform: translateX(100%); }
        }
        
        .cache-bar-labels {
          display: flex;
          justify-content: space-between;
          font-size: 0.7rem;
          color: var(--gray-color);
          margin-top: 5px;
          opacity: 0.7;
        }
        
        .hit-stats {
          display: flex;
          justify-content: space-between;
          margin-top: 15px;
          gap: 15px;
        }
        
        .hit-stat-item {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        
        .hit-count-dot, .miss-count-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          display: inline-block;
        }
        
        .hit-count-dot {
          background: var(--accent-linear);
          box-shadow: 0 0 0 2px rgba(var(--accent-color-rgb, 0, 123, 255), 0.15);
        }
        
        .miss-count-dot {
          background-color: var(--error-color);
          box-shadow: 0 0 0 2px rgba(var(--error-color-rgb, 239, 68, 68), 0.15);
        }
        
        .hit-count-label, .miss-count-label {
          font-size: 0.8rem;
          font-weight: 500;
          color: var(--text-color);
        }
        
        .hit-count-value, .miss-count-value {
          font-size: 0.8rem;
          font-weight: 600;
          margin-left: auto;
        }
        
        .hit-count-value {
          color: var(--success-color);
        }
        
        .miss-count-value {
          color: var(--error-color);
        }
        
        .progress-container { margin-top: 1.5rem; }
        .progress-label { display: flex; justify-content: space-between; margin-bottom: 0.5rem; font-size: 0.875rem; }
        .progress-label-text { color: var(--title-color); font-weight: 500; }
        .progress-label-value { color: var(--gray-color); }
        .progress-bar { height: 8px; width: 100%; background-color: #e5e7eb; border-radius: 4px; overflow: hidden; margin-bottom: 1rem; }
        .progress-fill { height: 100%; border-radius: 4px; }
        .progress-fill-pricing { background: var(--action-linear); /* width is set by style attribute */ }
        .progress-fill-maps { background: var(--second-linear); /* width is set by style attribute */ }
        
        .by-type-container { display: flex; justify-content: space-around; flex-wrap: wrap; gap: 1rem; margin-top: 1.5rem; }
        .type-metric { text-align: center; }
        .type-value { font-size: 1.5rem; font-weight: 600; color: var(--title-color); margin-bottom: 0.25rem; }
        .type-label { font-size: 0.75rem; color: var(--gray-color); }
        
        .sync-status { 
          display: flex; 
          align-items: center; 
          gap: 0.5rem; margin-top: 5px; 
          padding: 0.75rem; 
          border-radius: 8px; 
          background-color: var(--hover-background); 
        }

        .sync-indicator { width: 10px; height: 10px; border-radius: 50%; }
        /* .sync-indicator.status-ok is already defined by .status-ok */
        /* .sync-indicator.status-warning is already defined by .status-warning */
        .sync-text { font-size: 0.875rem; color: var(--text-color); }
        .sync-timestamp { margin-left: auto; font-size: 0.8rem; color: var(--gray-color); }


        div.finish {
          padding: 10px 0 40px;
          width: 100%;
          min-width: 100%;
          height: auto;
          display: flex;
          flex-flow: column;
          justify-content: center;
          align-items: center;
          gap: 5px;
        }

        div.empty {
          padding: 10px 0;
          width: 100%;
          min-width: 100%;
          height: auto;
          display: flex;
          flex-flow: column;
          justify-content: center;
          align-items: center;
          gap: 5px;
        }

        div.finish > h2.finish__title {
          margin: 10px 0 0 0;
          font-size: 1.15rem;
          font-weight: 500;
          font-family: var(--font-read), sans-serif;
          color: var(--text-color);
        }

        div.empty p.desc,
        div.finish > p.desc {
          margin: 0;
          font-size: 0.85rem;
          font-family: var(--font-read), sans-serif;
          color: var(--gray-color);
          line-height: 1.4;
          text-align: center;
        }

        div.finish > button.finish {
          border: none;
          background: var(--accent-linear);
          font-family: var(--font-main), sans-serif;
          text-decoration: none;
          color: var(--white-color);
          margin: 10px 0 0;
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          display: flex;
          width: max-content;
          flex-flow: row;
          align-items: center;
          text-transform: capitalize;
          justify-content: center;
          padding: 7px 18px 8px;
          border-radius: 50px;
          -webkit-border-radius: 50px;
          -moz-border-radius: 50px;
        }

        /* External Services Cards */
        .services-cards {
          display: flex;
          flex-flow: row wrap;
          justify-content: space-between;
          gap: 20px;
          width: 100%;
          margin: 1rem 0;
        }
        .service-card {
          background-color: var(--background);
          border: var(--border);
          border-radius: 8px;
          padding: 1rem;
          min-width: 150px;
          display: flex;
          flex-direction: column;
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .service-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--card-box-shadow);
        }
        .service-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }
        .service-card-title {
          font-size: 1rem;
          font-weight: 600;
          color: var(--title-color);
        }
        .service-card-body {
          font-size: 0.875rem;
          color: var(--text-color);
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }
        .service-status {
          font-weight: 500;
          color: var(--accent-color);
        }
        .service-timestamp {
          font-size: 0.75rem;
          color: var(--gray-color);
        }
        .service-details {
          font-size: 0.75rem;
          color: var(--gray-color);
        }

        @keyframes l22-0 {
          100% {transform: rotate(1turn)}
        }

        @keyframes l22 {
          100% {transform: rotate(1turn) translate(150%)}
        }

        @media (prefers-color-scheme: dark) {
          .progress-bar {
            background-color: #374151; /* A darker gray for dark mode */
          }
          .service-item {
            border: 1px solid rgba(255, 255, 255, 0.05);
          }
          .service-item:hover {
            border-color: rgba(255, 255, 255, 0.1);
          }
          .hit-rate-chart {
            background-color: rgba(255, 255, 255, 0.03);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          }
          .cache-bar {
            background-color: rgba(0, 0, 0, 0.2);
            box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.3);
          }
          .cache-bar-hit {
            box-shadow: 0 0 10px rgba(var(--accent-color-rgb, 0, 123, 255), 0.4);
          }
          .cache-bar-shine {
            background: linear-gradient(
              90deg, 
              rgba(255, 255, 255, 0) 0%, 
              rgba(255, 255, 255, 0.1) 50%, 
              rgba(255, 255, 255, 0) 100%
            );
          }
        }

        @media (max-width: 900px) {
          .dashboard-overview { grid-template-columns: minmax(180px, 1fr) minmax(180px, 1fr); }
        }

        @media (max-width: 768px) {
          .dashboard-overview { grid-template-columns: 1fr; }
          .cache-grid { grid-template-columns: 1fr 1fr; }
          .hit-rate-grid { grid-template-columns: 1fr; }
          .by-type-container { flex-direction: column; gap: 1rem; align-items: stretch; }
          .type-metric { display: flex; align-items: center; justify-content: space-between; text-align: left; }
          .type-value { margin-bottom: 0; }
          .dashboard-title { font-size: 1.6rem; }
          .stat-value { font-size: 1.8rem; }
          .service-info { max-width: 70%; }
          .service-status {
            font-size: 0.8rem;
            padding: 4px 6px;
          }
          .hit-rate-chart {
            padding: 12px;
          }
          .hit-stat-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 2px;
          }
          .hit-count-value, .miss-count-value {
            margin-left: 16px; /* Indent the value under the label */
          }
        }

        @media (max-width: 480px) {
          .stat-value { font-size: 1.6rem; }
          .cache-grid { grid-template-columns: 1fr; }
          .by-type-container .type-metric { flex-direction: column; align-items: center; text-align: center; }
          .by-type-container .type-value { margin-bottom: 0.25rem; }
          .service-info { max-width: 60%; }
          .service-item {
            padding: 0.75rem 10px;
          }
          .service-status {
            padding: 3px 5px;
          }
          .hit-rate-title, .hit-rate-value {
            font-size: 0.9rem;
          }
          .hit-stats {
            flex-direction: column;
            gap: 8px;
          }
          .hit-stat-item {
            justify-content: space-between;
            flex-direction: row;
            align-items: center;
          }
          .hit-count-value, .miss-count-value {
            margin-left: auto;
          }
          .cache-bar-labels {
            font-size: 0.65rem;
          }
        }
      </style>
    `;
  };
}
