/**
 * Theme Selection Component
 * Provides UI for theme management
 */

export default class SheetThemes extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/themes";
    this.themeManager = null;
    this.currentTheme = "default";
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.initializeThemeSystem();
  }

  /**
   * Initialize the theme system
   */
  async initializeThemeSystem() {
    try {
      // ThemeManager should already be available from app.js
      if (!window.themeManager) {
        throw new Error('ThemeManager not initialized by app.js');
      }

      this.themeManager = window.themeManager;
      this.currentTheme = this.themeManager.currentTheme;

      // Wait a bit for theme manager to initialize, then render
      setTimeout(() => {
        this.renderThemesContent();
        this.bindEvents();
      }, 100);

    } catch (error) {
      console.error('Error initializing theme system:', error);
      this.showError('Failed to load theme system');
    }
  }

  /**
   * Render the themes content
   */
  renderThemesContent() {
    const container = this.shadowObj.querySelector(".themes-container");
    if (!container) return;

    const themes = this.themeManager.getAllThemes();

    container.innerHTML = `
            <div class="themes-wrapper">
                <div class="themes-header">
                    <h1>Theme Settings</h1>
                    <p>Customize the appearance of your dashboard</p>
                </div>

                <div class="current-theme-info">
                    <h3>Current Theme</h3>
                    <div class="current-theme-card" id="current-theme-card">
                        ${this._getCurrentThemeHTML()}
                    </div>
                </div>

                <div class="themes-grid">
                    <h3>Available Themes</h3>
                    <div class="themes-list">
                        ${Object.entries(themes)
        .map(([id, theme]) =>
          this._getThemeCardHTML(id, theme)
        )
        .join("")}
                    </div>
                </div>

                <div class="theme-controls">
                    <div class="control-buttons">
                        <button class="theme-btn secondary" id="reset-theme">
                            <span class="icon">🏠</span>
                            Reset to Default (Dark)
                        </button>
                        <button class="theme-btn secondary" id="random-theme">
                            <span class="icon">🎲</span>
                            Random Theme
                        </button>
                    </div>
                    <div class="theme-stats">
                        <span class="stat">
                            <span class="icon">🎨</span>
                            ${Object.keys(themes).length} themes available
                        </span>
                    </div>
                </div>
            </div>
        `;
  }

  /**
   * Get template
   */
  getTemplate() {
    return /* HTML */ `
            <style>
                ${this.getCSS()}
            </style>
            <div class="themes-container">
                <div class="loader">
                    <div class="spinner"></div>
                    <p>Loading themes...</p>
                </div>
            </div>
        `;
  }

  /**
   * Get current theme display HTML
   */
  _getCurrentThemeHTML() {
    const theme = this.themeManager.getCurrentTheme();
    return `
            <div class="theme-preview" style="background: linear-gradient(135deg, ${theme.colors.primary}20, ${theme.colors.secondary}20)">
                <div class="theme-colors">
                    <div class="color-dot" style="background: ${theme.colors.primary}"></div>
                    <div class="color-dot" style="background: ${theme.colors.secondary}"></div>
                    <div class="color-dot" style="background: ${theme.colors.accent}"></div>
                </div>
            </div>
            <div class="theme-details">
                <h4>${theme.name}</h4>
                <p>${theme.description}</p>
                <span class="theme-status">Active</span>
            </div>
        `;
  }

  /**
   * Get theme card HTML
   */
  _getThemeCardHTML(id, theme) {
    const isActive = id === this.currentTheme;
    return `
            <div class="theme-card ${isActive ? "active" : ""}" data-theme="${id}">
                <div class="theme-preview" style="background: linear-gradient(135deg, ${theme.colors.primary}20, ${theme.colors.secondary}20)">
                    <div class="theme-colors">
                        <div class="color-dot" style="background: ${theme.colors.primary}"></div>
                        <div class="color-dot" style="background: ${theme.colors.secondary}"></div>
                        <div class="color-dot" style="background: ${theme.colors.accent}"></div>
                    </div>
                    ${isActive ? '<div class="active-indicator">✓</div>' : ""}
                </div>
                <div class="theme-info">
                    <h4>${theme.name}</h4>
                    <p>${theme.description}</p>
                </div>
                <button class="theme-apply-btn ${isActive ? "active" : ""}" ${isActive ? "disabled" : ""}>
                    ${isActive ? "Current" : "Apply"}
                </button>
            </div>
        `;
  }

  /**
   * Bind event listeners
   */
  bindEvents() {
    const container = this.shadowObj.querySelector(".themes-container");
    if (!container) return;

    // Theme card clicks
    container.addEventListener("click", async (e) => {
      const themeCard = e.target.closest(".theme-card");
      if (themeCard) {
        const themeId = themeCard.dataset.theme;
        if (themeId !== this.currentTheme) {
          await this.applyTheme(themeId);
        }
        return;
      }

      // Apply button clicks
      const applyBtn = e.target.closest(".theme-apply-btn");
      if (applyBtn && !applyBtn.disabled) {
        const themeCard = applyBtn.closest(".theme-card");
        const themeId = themeCard.dataset.theme;
        await this.applyTheme(themeId);
        return;
      }

      // Control buttons
      if (e.target.closest("#reset-theme")) {
        await this.applyTheme("default");
      } else if (e.target.closest("#random-theme")) {
        await this.applyRandomTheme();
      }
    });

    // Listen for theme changes from other sources
    window.addEventListener("themeChanged", (e) => {
      this.currentTheme = e.detail.theme || e.detail.themeId;
      this.updateUI();
    });

    // Listen for system theme changes that might affect the current theme
    window.addEventListener("systemThemeChanged", (e) => {
      // Re-render the UI to reflect any changes in theme appearance
      setTimeout(() => {
        this.updateUI();
      }, 100);
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      if (e.ctrlKey || e.metaKey) {
        switch (e.key) {
          case "ArrowLeft":
            e.preventDefault();
            this.themeManager.previousTheme();
            break;
          case "ArrowRight":
            e.preventDefault();
            this.themeManager.nextTheme();
            break;
          case "r":
            if (e.shiftKey) {
              e.preventDefault();
              this.applyRandomTheme();
            }
            break;
        }
      }
    });
  }

  /**
   * Apply a theme
   */
  async applyTheme(themeId) {
    try {
      // Show loading state on the button being clicked
      const targetCard = this.shadowObj.querySelector(`[data-theme="${themeId}"]`);
      if (targetCard) {
        const applyBtn = targetCard.querySelector('.theme-apply-btn');
        if (applyBtn) {
          applyBtn.textContent = 'Applying...';
          applyBtn.disabled = true;
        }
      }

      // Apply the theme
      await this.themeManager.applyTheme(themeId);
      this.currentTheme = themeId;

      // Update UI immediately after theme application
      this.updateUI();

      // Show feedback
      this.showThemeChangeNotification(themeId);
    } catch (error) {
      console.error('Error applying theme:', error);
      this.showError('Failed to apply theme. Please try again.');
    }
  }

  /**
   * Update control buttons state
   */
  updateControlButtons() {
    const resetBtn = this.shadowObj.querySelector('#reset-theme');
    const randomBtn = this.shadowObj.querySelector('#random-theme');

    if (resetBtn) {
      resetBtn.disabled = this.currentTheme === 'default';
      resetBtn.classList.toggle('disabled', this.currentTheme === 'default');
    }

    const themes = Object.keys(this.themeManager.getAllThemes());
    if (randomBtn) {
      randomBtn.disabled = themes.length <= 1;
      randomBtn.classList.toggle('disabled', themes.length <= 1);
    }
  }

  /**
   * Apply a random theme
   */
  async applyRandomTheme() {
    const themes = Object.keys(this.themeManager.getAllThemes());
    const availableThemes = themes.filter((id) => id !== this.currentTheme);

    if (availableThemes.length === 0) {
      this.showThemeChangeNotification(this.currentTheme, 'No other themes available');
      return;
    }

    const randomTheme = availableThemes[Math.floor(Math.random() * availableThemes.length)];
    await this.applyTheme(randomTheme);
  }

  /**
   * Update UI after theme change
   */
  updateUI() {
    // Update current theme card
    const currentThemeCard = this.shadowObj.querySelector(
      "#current-theme-card"
    );
    if (currentThemeCard) {
      currentThemeCard.innerHTML = this._getCurrentThemeHTML();
    }

    // Update theme cards with proper state management
    const themeCards = this.shadowObj.querySelectorAll(".theme-card");
    themeCards.forEach((card) => {
      const themeId = card.dataset.theme;
      const isActive = themeId === this.currentTheme;

      // Update card state
      card.classList.toggle("active", isActive);

      // Update apply button
      const applyBtn = card.querySelector(".theme-apply-btn");
      if (applyBtn) {
        applyBtn.textContent = isActive ? "Current" : "Apply";
        applyBtn.disabled = isActive;
        applyBtn.classList.toggle("active", isActive);

        // Reset any loading states
        if (applyBtn.textContent === 'Applying...') {
          applyBtn.textContent = isActive ? "Current" : "Apply";
        }
      }

      // Update active indicator
      let activeIndicator = card.querySelector(".active-indicator");
      if (isActive && !activeIndicator) {
        activeIndicator = document.createElement("div");
        activeIndicator.className = "active-indicator";
        activeIndicator.textContent = "✓";
        card.querySelector(".theme-preview").appendChild(activeIndicator);
      } else if (!isActive && activeIndicator) {
        activeIndicator.remove();
      }
    });

    // Update control buttons state
    this.updateControlButtons();
  }

  /**
   * Show theme change notification
   */
  showThemeChangeNotification(themeId, customMessage) {
    const theme = this.themeManager.getAllThemes()[themeId];

    // Remove existing notification
    const existing = document.querySelector(".theme-notification");
    if (existing) existing.remove();

    // Create notification
    const notification = document.createElement("div");
    notification.className = "theme-notification";
    notification.innerHTML = `
            <div class="notification-content">
                <span class="icon">🎨</span>
                <span>${customMessage || `Applied ${theme.name} theme`}</span>
            </div>
        `;

    document.body.appendChild(notification);

    // Auto remove after 3 seconds
    setTimeout(() => {
      notification.classList.add("fade-out");
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  /**
   * Show error message
   */
  showError(message) {
    const container = this.shadowObj.querySelector('.themes-container');
    if (container) {
      container.innerHTML = `
        <div class="error-message">
          <div class="error-icon">⚠️</div>
          <h3>Error</h3>
          <p>${message}</p>
          <button class="theme-btn" onclick="location.reload()">
            <span class="icon">🔄</span>
            Reload Page
          </button>
        </div>
      `;
    }
  }

  /**
   * Get CSS for the component
   */
  getCSS() {
    return /* CSS */ `
            :host {
                display: block;
                width: 100%;
                height: 100%;
                font-family: var(--font-main);
            }

            .loader {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 200px;
                gap: 1rem;
            }

            .spinner {
                width: 40px;
                height: 40px;
                border: 3px solid var(--gray-background);
                border-top: 3px solid var(--accent-color);
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }

            .loader p {
                color: var(--text-color);
                font-size: 0.9rem;
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }

            .themes-wrapper {
                padding: 2rem;
                max-width: 1200px;
                margin: 0 auto;
            }

            .themes-header {
                margin: 0 0 20px;
            }

            .themes-header h1 {
                color: var(--title-color);
                margin: 0;
                font-size: 10px 0 2rem;
                font-weight: 700;
                line-height: 1.2;
            }

            .themes-header p {
                color: var(--text-color);
                font-size: 1rem;
                padding: 0;
                margin: 0;
                line-height: 1.5;
            }

            .current-theme-info {
                margin-bottom: 3rem;
            }

            .current-theme-info h3 {
                color: var(--label-color);
                margin-bottom: 1rem;
                font-size: 1.5rem;
                font-weight: 600;
            }

            .current-theme-card {
                background: var(--background);
                border: var(--border);
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: var(--card-box-shadow);
                display: flex;
                align-items: center;
                gap: 1.5rem;
                transition: all 0.3s ease;
              }

            .themes-grid h3 {
                color: var(--label-color);
                margin-bottom: 1.5rem;
                font-size: 1.5rem;
                font-weight: 600;
            }

            .themes-list {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 1.5rem;
                margin-bottom: 3rem;
            }

            .theme-card {
                background: var(--background);
                border: var(--border);
                border-radius: 12px;
                padding: 1.5rem;
                box-shadow: var(--card-box-shadow-alt);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
            }

            .theme-card:hover {
                transform: translateY(-2px);
                box-shadow: var(--card-box-shadow);
            }

            .theme-card.active {
                border-color: var(--accent-color);
                box-shadow: 0 0 0 2px rgba(0, 96, 223, 0.2), var(--card-box-shadow);
            }

            .theme-preview {
                height: 80px;
                border-radius: 8px;
                margin: 0;
                padding: 0 10px;
                position: relative;
                display: flex;
                align-items: center;
                justify-content: center;
                border: var(--border);
            }

            .theme-colors {
                display: flex;
                gap: 8px;
            }

            .color-dot {
                width: 20px;
                height: 20px;
                border-radius: 50%;
                border: 2px solid var(--background);
                box-shadow: var(--card-box-shadow-alt);
            }

            .active-indicator {
                position: absolute;
                top: 8px;
                right: 8px;
                background: var(--accent-color);
                color: var(--white-color);
                width: 24px;
                height: 24px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: bold;
            }

            .theme-details {
                flex: 1;
                display: flex;
                flex-flow: column nowrap;
                gap: 0;
            }

            .theme-details h4 {
                color: var(--title-color);
                margin: 0;
                padding: 0;
                line-height: 1.4;
                font-size: 1.25rem;
                font-weight: 600;
            }

            .theme-details p {
                color: var(--text-color);
                font-size: 1rem;
                margin: 0;
                line-height: 1.4;
            }

            .theme-info h4 {
                color: var(--title-color);
                margin: 0;
                padding: 0;
                line-height: 1.4;
                font-size: 1.1rem;
                font-weight: 600;
            }

            .theme-info p {
                color: var(--text-color);
                font-size: 0.9rem;
                margin: 0;
                line-height: 1.4;
            }

            .theme-apply-btn {
                width: 100%;
                padding: 0.75rem;
                border: none;
                border-radius: 8px;
                background: var(--action-linear);
                color: var(--white-color);
                font-weight: 500;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 0.9rem;
                margin-top: 1rem;
            }

            .theme-apply-btn:hover:not(:disabled) {
                transform: translateY(-1px);
                box-shadow: var(--card-box-shadow);
                background: var(--accent-color);
            }

            .theme-apply-btn:disabled {
                background: var(--gray-background);
                color: var(--gray-color);
                cursor: not-allowed;
                transform: none;
            }

            .theme-apply-btn.active {
                background: var(--accent-color);
                box-shadow: 0 0 0 2px rgba(0, 96, 223, 0.3);
            }

            .theme-status {
                display: inline-block;
                margin-top: 0.5rem;
                width: fit-content;
                background: var(--accent-color);
                color: var(--white-color);
                padding: 0.25rem 0.75rem;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: 500;
            }

            .theme-controls {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 1rem;
                margin-bottom: 3rem;
                padding: 2rem;
                background: var(--background);
                border: var(--border);
                border-radius: 12px;
                box-shadow: var(--card-box-shadow-alt);
            }

            .control-buttons {
                display: flex;
                gap: 1rem;
                flex-wrap: wrap;
                justify-content: center;
            }

            .theme-btn {
                padding: 0.75rem 1.5rem;
                border: var(--border);
                border-radius: 8px;
                background: var(--background);
                color: var(--text-color);
                cursor: pointer;
                transition: all 0.3s ease;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-weight: 500;
                font-size: 0.9rem;
            }

            .theme-btn:hover {
                background: var(--hover-background);
                transform: translateY(-1px);
            }

            .theme-btn:disabled,
            .theme-btn.disabled {
                opacity: 0.5;
                cursor: not-allowed;
                transform: none;
            }

            .theme-btn:disabled:hover,
            .theme-btn.disabled:hover {
                background: var(--background);
                transform: none;
            }

            .theme-btn.secondary {
                border-color: var(--accent-color);
                color: var(--accent-color);
            }

            .theme-stats {
                display: flex;
                align-items: center;
                justify-content: center;
                margin-top: 1rem;
            }

            .stat {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: var(--text-color);
                font-size: 0.9rem;
                font-weight: 500;
            }

            .theme-info {
                border-radius: 0;
                padding: 10px 20px;
                text-align: center;
            }

            .theme-info h3 {
                color: var(--title-color);
                margin: 0;
                line-height: 1.3;
                font-size: 1.5rem;
                font-weight: 600;
            }

            .theme-info p {
                color: var(--text-color);
                font-family: var(--font-mono);
                margin: 0;
                font-size: 0.875rem;  
                line-height: 1.2;
            }

            .theme-features {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
            }

            .feature {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                color: var(--text-color);
                font-weight: 500;
            }

            .feature .icon {
                font-size: 1.2rem;
            }

            .theme-notification {
                position: fixed;
                top: 2rem;
                right: 2rem;
                background: var(--accent-color);
                color: var(--white-color);
                padding: 1rem 1.5rem;
                border-radius: 8px;
                box-shadow: var(--modal-shadow);
                z-index: 1000;
                animation: slideInRight 0.3s ease;
            }

            .theme-notification.fade-out {
                animation: slideOutRight 0.3s ease;
            }

            .notification-content {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                font-weight: 500;
            }

            @keyframes slideInRight {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }

            @keyframes slideOutRight {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }

            @media (max-width: 768px) {
                .themes-wrapper {
                    padding: 1rem;
                }

                .themes-list {
                    grid-template-columns: 1fr;
                }

                .current-theme-card {
                    flex-direction: column;
                    text-align: center;
                    gap: 1rem;
                }

                .theme-details h4 {
                    font-size: 1.1rem;
                }

                .theme-details p {
                    font-size: 0.9rem;
                }

                .control-buttons {
                    flex-direction: column;
                    width: 100%;
                }

                .theme-btn {
                    width: 100%;
                    justify-content: center;
                }

                .theme-features {
                    grid-template-columns: 1fr;
                }

                .theme-notification {
                    top: 1rem;
                    right: 1rem;
                    left: 1rem;
                }

                .themes-header h1 {
                    font-size: 2rem;
                }
            }
        `;
  }
}
