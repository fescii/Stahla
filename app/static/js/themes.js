/**
 * Theme Management System
 * Handles theme switching via CSS custom properties
 */

export default class ThemeManager {
  constructor() {
    this.themes = {
      'default': {
        name: 'Dark Mode',
        description: 'Pure black/white dark theme',
        file: '/static/css/themes/dark.json',
        colors: {
          primary: '#0060df',
          secondary: '#1a7dff',
          accent: '#4285f4'
        }
      },
      'classic': {
        name: 'Classic',
        description: 'Original classic theme',
        colors: {
          primary: '#0060df',
          secondary: '#df791a',
          accent: '#10b981'
        }
      },
      'blue': {
        name: 'Ocean Blue',
        description: 'Professional blue theme',
        file: '/static/css/themes/blue.json',
        colors: {
          primary: '#2563eb',
          secondary: '#1e40af',
          accent: '#3b82f6'
        }
      },
      'green': {
        name: 'Nature Green',
        description: 'Fresh green theme',
        file: '/static/css/themes/green.json',
        colors: {
          primary: '#10b981',
          secondary: '#047857',
          accent: '#059669'
        }
      },
      'purple': {
        name: 'Royal Purple',
        description: 'Elegant purple theme',
        file: '/static/css/themes/purple.json',
        colors: {
          primary: '#8b5cf6',
          secondary: '#7c3aed',
          accent: '#a855f7'
        }
      },
      'orange': {
        name: 'Sunset Orange',
        description: 'Warm orange theme',
        file: '/static/css/themes/orange.json',
        colors: {
          primary: '#f97316',
          secondary: '#ea580c',
          accent: '#fb923c'
        }
      }
    };

    this.currentTheme = 'default';
    this.themeCache = new Map();
    this.initialize();
  }

  /**
   * Initialize theme system
   */
  async initialize() {
    // Load saved theme or default
    const savedTheme = localStorage.getItem('selectedTheme') || 'default';
    await this.applyTheme(savedTheme);

    // Listen for system dark mode changes
    this.setupSystemThemeListener();
  }

  /**
   * Apply a theme by loading its JSON and setting CSS variables
   */
  async applyTheme(themeId) {
    try {
      // Handle classic theme (no JSON file, reset to default CSS variables)
      if (themeId === 'classic') {
        // Reset all CSS custom properties to their default values
        await this.resetToDefaultCSS();
        this.currentTheme = themeId;
        localStorage.setItem('selectedTheme', themeId);
        this.dispatchThemeChange(themeId);
        return;
      }

      const theme = this.themes[themeId];
      if (!theme || !theme.file) {
        console.error(`Theme ${themeId} not found or has no file`);
        return;
      }

      // Load theme data from JSON file
      const themeData = await this.loadThemeData(theme.file);

      // Apply theme variables based on system preference
      const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      const modeColors = isDark ? themeData.colors.dark : themeData.colors.light;

      this.setCSSVariables(modeColors);

      // Update current theme
      this.currentTheme = themeId;
      localStorage.setItem('selectedTheme', themeId);

      // Dispatch theme change event
      this.dispatchThemeChange(themeId);

    } catch (error) {
      console.error('Error applying theme:', error);
    }
  }

  /**
   * Load theme data from JSON file
   */
  async loadThemeData(file) {
    // Check cache first
    if (this.themeCache.has(file)) {
      return this.themeCache.get(file);
    }

    try {
      const response = await fetch(file);
      if (!response.ok) {
        throw new Error(`Failed to load theme file: ${response.status}`);
      }

      const data = await response.json();
      this.themeCache.set(file, data);
      return data;
    } catch (error) {
      console.error('Error loading theme data:', error);
      throw error;
    }
  }

  /**
   * Reset CSS custom properties to their default values (for classic theme)
   */
  async resetToDefaultCSS() {
    const root = document.documentElement;

    // Original default CSS custom properties from default.css
    const defaultProperties = {
      '--tab-background': '#0060df21',
      '--hubspot-background': 'linear-gradient(0deg, #df791a38 0%, #f09c4e67 100%)',
      '--stat-background': '#f1f1f1',
      '--attachement-background': '#0060df21',
      '--font-main': '"Inter"',
      '--font-text': '"Inter"',
      '--font-mono': '"Jetbrains Mono"',
      '--font-read': '"Work Sans"',
      '--card-box-shadow': '0 12px 28px 0 rgba(70, 53, 53, 0.2)',
      '--image-shadow': '0 -1px 10px 0 #0202020a',
      '--card-box-shadow-alt': '0 2px 4px 0 rgba(0, 0, 0, 0.1)',
      '--box-shadow': '0 0 0 1px #ffffff25, 0 2px 2px #0000000a, 0 8px 16px -4px #0000000a',
      '--scroll-bar-background': '#ddddd7',
      '--scroll-bar-linear': 'linear-gradient(#003eaa, #0060df)',
      '--input-border': '1px solid #6b72805e',
      '--input-border-focus': '1px solid #0060df9a',
      '--input-border-error': '1px solid #ec4a1965',
      '--action-border': '1px solid #0060df73',
      '--border': 'thin solid #6b72801a',
      '--border-button': 'thin solid #6b72801a',
      '--topic-border': 'thin solid #6b728046',
      '--topic-border-active': 'thin solid #003eaa7a',
      '--section-border': '2px solid #0060df',
      '--poll-border': 'thin solid #6b728025',
      '--border-mobile': 'thin solid #6b728036',
      '--border-header': '0.002rem solid #6b72809a',
      '--background': '#ffffff',
      '--hover-background': '#f7f7f7',
      '--modal-background': '#1a202c5d',
      '--author-background': '#f1f3f4',
      '--user-background': '#f8f8f8',
      '--gray-background': '#e7e7e7d7',
      '--white-background': '#ffffff',
      '--accent-color': '#0060df',
      '--text-color': '#494d52',
      '--title-color': '#1f2937',
      '--label-color': '#3f4246',
      '--anchor-color': '#0060df',
      '--anchor-hover-color': '#003eaa',
      '--anchor-visited-color': '#0060df',
      '--action-linear': 'linear-gradient(#003eaa, #0060df)',
      '--modal-shadow': '0 12px 48px #6d758d33',
      '--gray-color': '#6b7280',
      '--white-color': '#ffffff',
      '--error-color': '#ec4b19',
      '--success-color': '#10b981',
      '--warning-color': '#df791a',
      '--placeholder-color': '#6b7280'
    };

    // Apply all default properties
    Object.entries(defaultProperties).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });

    // Force a repaint to ensure changes take effect
    document.body.offsetHeight;
  }

  /**
   * Set CSS custom properties on document root
   */
  setCSSVariables(variables) {
    const root = document.documentElement;

    Object.entries(variables).forEach(([property, value]) => {
      root.style.setProperty(property, value);
    });
  }

  /**
   * Get all available themes
   */
  getAllThemes() {
    return this.themes;
  }

  /**
   * Get current theme info
   */
  getCurrentTheme() {
    return this.themes[this.currentTheme];
  }

  /**
   * Get preview colors for a theme (for UI display)
   */
  getThemePreviewColors(themeId) {
    return this.themes[themeId]?.colors || {};
  }

  /**
   * Dispatch theme change event
   */
  dispatchThemeChange(themeId) {
    window.dispatchEvent(new CustomEvent('themeChanged', {
      detail: { theme: themeId, themeData: this.themes[themeId] }
    }));
  }

  /**
   * Setup listener for system theme changes
   */
  setupSystemThemeListener() {
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      // Handle theme changes
      const handleThemeChange = async (e) => {
        // Re-apply current theme to get correct light/dark mode colors
        // Skip for classic theme since it doesn't have light/dark variants
        if (this.currentTheme !== 'classic') {
          await this.applyTheme(this.currentTheme);
        }

        // Dispatch system theme change event
        window.dispatchEvent(new CustomEvent('systemThemeChanged', {
          detail: { isDark: e.matches }
        }));
      };

      // Use newer addEventListener if available, fallback to addListener
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleThemeChange);
      } else {
        mediaQuery.addListener(handleThemeChange);
      }
    }
  }

  /**
   * Watch for system theme changes (alias for setupSystemThemeListener)
   * This method is called by app.js for compatibility
   */
  watchSystemTheme() {
    // This method already gets called in initialize(), but we provide it
    // as an alias for compatibility with existing app.js code
    this.setupSystemThemeListener();
  }
}