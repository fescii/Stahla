import APIManager from "./api.js";
import uis from "./apps/apps.js"
export default class AppMain extends HTMLElement {
  constructor() {
    super();
    this.content = this.getContent();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.registerComponents();
    this.preferences();
    this.api = new APIManager('/api/v1', 9500, 'v1');
    window.app = this;
    this.mql = window.matchMedia('(max-width: 660px)');
    this.render();
    this.currentUrl = window.location.pathname;
    window.addEventListener('popstate', this.handlePopState);
  }

  getContent = () => {
    const content = this.innerHTML;
    this.innerHTML = '';
    return content;
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
    // watch for media query changes
    this.watchMeta();
  }

  connectedCallback() {
    this.setUpEvents();
    this._setupSpecialNavs();
    this._setupNavLinks(); // Add navigation link event handlers
    this._loadInitialContent(); // Load content based on current URL
  }

  _loadInitialContent() {
    // Get the current path from the browser
    const currentPath = window.location.pathname;
    
    // Update active navigation item based on the current URL
    this._updateActiveNavItem(currentPath);
    
    // Load the content for this URL
    if (this.getNavContents[currentPath]) {
      const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
      if (container) {
        container.innerHTML = this.getNavContents[currentPath];
      }
    } else if (currentPath !== '/' && currentPath !== '/overview') {
      // If path is not in nav contents and not the root path, show 404/default
      const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
      if (container) {
        container.innerHTML = this.getNavContents.default;
      }
    }
    // If it's the root path, the default content will be loaded by initContent
  }

  _setupNavLinks() {
    if (!this.shadowRoot) {
      console.warn('Shadow root not available for _setupNavLinks. Ensure component is fully initialized.');
      return;
    }

    // Get all navigation links
    const navLinks = this.shadowRoot.querySelectorAll('section.nav a[href]');
    
    navLinks.forEach(link => {
      link.addEventListener('click', (event) => {
        event.preventDefault();
        
        const url = link.getAttribute('href');
        
        // Update active class for main nav items
        this._updateActiveNavItem(url);
        
        // Update URL in browser and navigate
        this.push(url, { kind: 'app', html: this.getNavContents[url] || this.getNavContents.default }, '');
        
        // Perform the navigation
        this.navigate(url);
      });
    });
  }

  _updateActiveNavItem(url) {
    // Find all expanded dropdowns first to maintain their visibility state
    const expandedDropdowns = Array.from(this.shadowRoot.querySelectorAll('section.nav > ul.nav.special > li:not(.collapsed)'));
    
    // Remove active class from all items
    const allNavItems = this.shadowRoot.querySelectorAll('section.nav li');
    allNavItems.forEach(item => item.classList.remove('active'));
    
    // Re-add active class to expanded dropdowns to maintain vertical line
    expandedDropdowns.forEach(dropdown => {
      dropdown.classList.add('active');
    });
    
    // Add active class to the current nav item
    if (url === '/' || url === '/overview') {
      const overviewItem = this.shadowRoot.querySelector('li.overview');
      if (overviewItem) overviewItem.classList.add('active');
    } else {
      // Extract the path segments
      const urlSegments = url.split('/').filter(segment => segment);
      
      if (urlSegments.length > 0) {
        // Try to find the nav item with the class matching the last segment
        const segment = urlSegments[urlSegments.length - 1];
        let navItem = this.shadowRoot.querySelector(`li.${segment}`);
        
        // If not found, try the first segment
        if (!navItem && urlSegments.length > 0) {
          navItem = this.shadowRoot.querySelector(`li.${urlSegments[0]}`);
        }
        
        if (navItem) {
          navItem.classList.add('active');
          
          // If it's in a dropdown, also mark the parent as active and expand the dropdown
          const parentLi = navItem.closest('ul.dropdown')?.closest('li');
          if (parentLi) {
            parentLi.classList.add('active');
            
            // Expand the dropdown if it's collapsed
            if (parentLi.classList.contains('collapsed')) {
              this._expandDropdown(parentLi);
            }
          }
        }
      }
    }
  }

  getRenderedContent = contentContainer => {
    return contentContainer.innerHTML;
  }

  setUpEvents = () => {
    // set display to flex
    this.style.setProperty('display', 'flex')
    const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
    const currentPath = window.location.pathname;
    
    // Only initialize default content if we're at the root or there's no specific content for this path
    if (container && (currentPath === '/' || !this.getNavContents[currentPath])) {
      this.initContent();
    }
    
    // request user to enable notifications
    this.checkNotificationPermission();
  }

  hideNav = () => {
    const nav = this.shadowObj.querySelector('section.nav.mobile');

    if(nav) nav.style.setProperty('display', 'none'); 
  }

  showNav = () => {
    const nav = this.shadowObj.querySelector('section.nav.mobile');

    if(nav) nav.style.setProperty('display', 'flex'); 
  }

  initContent = () => {
    // check if cookie named: x-access-token exists then show dashboard otherwise show access
    const token = document.cookie.split('; ').find(row => row.startsWith('x-access-token='));
    if(token) {
      this.showDashboard();
    } else {
      this.showAccess();
    }
  }

  showDashboard = () => {
    const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
    if(container) container.innerHTML = this.getDashboard();
  }

  showAccess = () => {
    const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
    if(container) container.innerHTML = this.getAccess();
  }

  checkNotificationPermission = async () => {
    if(window.notify && !window.notify.permission) {
      await window.notify.requestPermission();
    }
  }

  watchMeta = () => {
    this.mql.addEventListener('change', () => {
      this.render();
      this.setUpEvents();
    })
  }

  showToast = (success, message) => {
    // check if the toast is already open
    const toastEl = document.querySelector('#toast');
    if (toastEl) toastEl.remove();

    // create the toast element
    const toast = this.getToast(success, message);

    // append the toast to the body
    document.body.insertAdjacentHTML('beforeend', toast);

    // add the show class to the toast
    const addedToast = document.querySelector('#toast');
    addedToast.classList.add('show');

    // remove the toast after 5 seconds
    setTimeout(() => {
      addedToast.classList.remove('show');
      setTimeout(() => {
        addedToast.remove();
      }, 300);
    }, 5000);
  }

  navigate = url => {
    const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');

    // set the loader
    container.innerHTML = this.getLoader();
    window.scrollTo(0, 0);
    
    // Update current URL reference
    this.currentUrl = url;

    // check if the URL is in the nav contents
    if (this.getNavContents[url]) {
      this.updateHistory(this.getNavContents[url]);
      return;
    }

    // if the URL is not in the nav contents, show the 404 page
    this.updateHistory(this.getNavContents.default);
  }

  replaceHistory = state => {
    // get current URL
    const url = window.location.href;

    // replace the current history entry
    this.replace(url, state, url);
  }

  /**
   * Navigate to a new URL and add it to history
   * @param {string} url - The URL to navigate to
   * @param {Object} state - State object to store with history entry
   * @param {string} title - Title for the new history entry
   */
  push(url, state = {}, title = '') {
    window.history.pushState(state, title, url);
    this.currentUrl = url;
  }

  /**
   * Replace current history entry with new URL
   * @param {string} url - The URL to navigate to
   * @param {Object} state - State object to store with history entry
   * @param {string} title - Title for the new history entry
   */
  replace(url, state = {}, title = '') {
    window.history.replaceState(state, title, url);
    this.currentUrl = url;
  }

  handlePopState = event => {
    const state = event.state;
    const url = window.location.pathname;
    
    // First update active navigation with proper expansion of dropdowns
    this._updateActiveNavItem(url);
    
    if (state && state.kind === 'app') {
      // Update content
      this.updateHistory(state.html);
    } else {
      // If no state or not our app state, still handle the content
      const content = this.getNavContents[url] || this.getNavContents.default;
      this.updateHistory(content);
    }
    
    // Update current URL reference
    this.currentUrl = url;
  }

  updateHistory = content => {
    // scroll to the top of the page
    window.scrollTo(0, 0);
    this.content = content;
    const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
    container.innerHTML = this.getLoader();
    
    setTimeout(() => {
      // set the content
      container.innerHTML = this.content;
    }, 1000);
  }

  registerComponents = () => {
    // Register all components here
    uis('Apps registered');
  }

  // set hash if user is logged
	setHash = name => {
		const value = `; ${document.cookie}`;
		const parts = value.split(`; ${name}=`);

		const cookie = parts.length === 2 ? parts.pop().split(';').shift() : null;

		// add cookie to the window
		window.hash = cookie;
	}

	setTheme = currentTheme =>{
		// Check the current theme
		const htmlElement = document.documentElement;
		const metaThemeColor = document.querySelector("meta[name=theme-color]");

		// Check if the current theme is: system
		if (currentTheme === 'system') {
			// Update the data-theme attribute
			htmlElement.setAttribute('data-theme', currentTheme);

			// Store the preference in local storage
			localStorage.setItem('theme', 'system');

			// Update the theme-color meta tag
			metaThemeColor.setAttribute("content", currentTheme === 'dark' ? '#000000' : '#ffffff');
			return;
		}
		
		// Update the data-theme attribute
		htmlElement.setAttribute('data-theme', currentTheme);
		
		// Store the preference in local storage
		localStorage.setItem('theme', currentTheme);

		// Update the theme-color meta tag
		metaThemeColor.setAttribute("content", currentTheme === 'dark' ? '#000000' : '#ffffff');
	}
	
	preferences() {
		const prefersDarkScheme = window.matchMedia("(prefers-color-scheme: dark)");

		// listen for theme change
		prefersDarkScheme.addEventListener('change', (event) => {
			// get local storage theme
			const currentTheme = localStorage.getItem('theme') || 'light';

			// if the theme is system
			if (currentTheme === 'system') {
				// set the theme
				this.setTheme('system');
				return;
			}
		})

		// get theme from local storage
		const currentTheme = localStorage.getItem('theme') || 'light';

		// set the theme
		this.setTheme(currentTheme);

		// set hash
		this.setHash('hash');
	}

  _setupSpecialNavs() {
    if (!this.shadowRoot) {
      console.warn('Shadow root not available for _setupSpecialNavs. Ensure component is fully initialized.');
      return;
    }

    const specialNavUls = this.shadowRoot.querySelectorAll('section.nav > ul.nav.special');

    specialNavUls.forEach(ul => {
      const item = ul.querySelector('li'); // Assuming one li per ul.special.nav
      if (!item) return;

      const header = item.querySelector('div.link-section');
      const dropdown = item.querySelector('ul.dropdown');

      if (header && dropdown) {
        // Default state: if ul.special.nav has 'opned' class, it's open, otherwise collapsed.
        if (ul.classList.contains('opned')) {
          item.classList.remove('collapsed');
          dropdown.style.maxHeight = dropdown.scrollHeight + 'px';
          item.classList.add('active'); // Add active class for the vertical line
        } else {
          item.classList.add('collapsed');
          dropdown.style.maxHeight = '0px';
          item.classList.remove('active'); // Remove active class for the vertical line
        }

        header.addEventListener('click', (event) => {
          event.preventDefault();
          const isCurrentlyCollapsed = item.classList.contains('collapsed');

          // Close all other special navs
          specialNavUls.forEach(otherUl => {
            const otherItem = otherUl.querySelector('li');
            if (otherItem && otherItem !== item) {
              otherItem.classList.add('collapsed');
              otherItem.classList.remove('active'); // Remove active class for other items
              const otherDropdown = otherItem.querySelector('ul.dropdown');
              if (otherDropdown) {
                otherDropdown.style.maxHeight = '0px';
              }
            }
          });

          // Toggle the clicked one
          if (isCurrentlyCollapsed) { // If it was collapsed, open it
            item.classList.remove('collapsed');
            item.classList.add('active'); // Add active class for the vertical line regardless of child selection
            dropdown.style.maxHeight = ( dropdown.scrollHeight + 7) + 'px'; // Add some padding
          } else { // If it was open, close it
            item.classList.add('collapsed');
            item.classList.remove('active'); // Remove active class for the vertical line
            dropdown.style.maxHeight = '0px';
          }
        });
      }
    });
  }

  getNavContents = {
    "/": /* HTML */`<dash-overview api="/dashboard/overview"></dash-overview>`,
    "/status": /* HTML */`<services-status api="/dashboard/services/status"></services-status>`,
    "/overview": /* HTML */`<dash-overview api="/dashboard/overview"></dash-overview>`,
    "/hubspot": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/cache": /* HTML */`<cache-search api="/dashboard/cache/search"></cache-search>`,
    "/users/all": /* HTML */`<users-list api="/auth/users"></users-list>`,
    "/users/add": /* HTML */`<add-user api="/auth/users" method="POST"></add-user>`,
    "/users/profile": /* HTML */`<user-profile api="/auth/me"></user-profile>`,
    "/pricing/location": /* HTML */`<location-lookup api="/webhook/location/lookup/sync"></location-lookup>`,
    "/pricing/quote": /* HTML */`<quote-form api="/webhook/quote"></quote-form>`,
    "/docs/api": /* HTML */`<docs-api type="docs" api="/docs/api"></docs-api>`,
    "/docs/code": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/docs/features": /* HTML */`<docs-features type="docs" api="/docs/features"></docs-features>`,
    "/docs/services": /* HTML */`<docs-services type="docs" api="/docs/services"></docs-services>`,
    "/docs/webhooks": /* HTML */`<docs-webhooks type="docs" api="/docs/webhooks"></docs-webhooks>`,
    "/bland/all": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/bland/add": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/bland/failed": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/bland/recent": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/sheet/config": /* HTML */`<sheet-config api="/dashboard/sheet/config"></sheet-config>`,
    "/sheet/generators": /* HTML */`<sheet-generators api="/dashboard/sheet/generators"></sheet-generators>`,
    "/sheet/products": /* HTML */`<sheet-products api="/dashboard/sheet/products"></sheet-products>`,
    "/sheet/branches": /* HTML */`<sheet-branches api="/dashboard/sheet/branches"></sheet-branches>`,
    default: /* HTML */`<dash-overview api="/dashboard/overview"></dash-overview>`,
  }

  getTemplate = () => {
    // Show HTML Here
    return `
      ${this.getBody()}
      ${this.getStyles()}
    `;
  }

  getBody = () => {
    const mql = window.matchMedia('(max-width: 660px)');
    if (mql.matches) {
      return /* html */`
        <section class="mobile">
          <h1 class="mobile-title">Stahla SDR AI & Pricing</h1>
          <p class="mobile-description">Stahla is a service that provides a wide range of features and functionalities to help you manage your SDR AI & Pricing application.</p>
          <p class="mobile-warning">Mobile version is not available yet. Please use the desktop or tablet version for the best experience.</p>
          ${this.getFooter()}
        </section>
      `;
    }
    else {
      return /* html */`
        <section class="nav">
          ${this.getMainNav()}
        </section>
        <section class="flow">
          <div id="content-container" class="content-container">
            ${this.getLoader()}
          </div>
          ${this.getFooter()}
        </section>
      `;
    }
  }

  setContent = container => {
    setTimeout(() => {
      // set the content
      container.innerHTML = this.content;
    }, 1000);
  }

  getMainNav = () => {
    return /* html */`
      ${this.getLogoNav()}
      ${this.getMainLinksNav()}
      ${this.getDocsNav()}
      ${this.getUserNav()}
      ${this.getBlandNav()}
      ${this.getSheetsNav()}
      ${this.getPricingNav()}
      ${this.getTweakNav()}
    `;
  }

  getLogoNav = () => {
    return /* html */`
      <ul class="logo nav">
        <li class="logo">
          <span class="tooltip">
            <span class="arrow"></span>
            <span class="text">SDR AI</span>
          </span>
        </li>
      </ul>
    `;
  }

  getMainLinksNav = () => {
    return /* html */`
      <ul class="main nav">
        <li class="overview active">
          <a href="/">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <path d="M13.6903 19.4567C13.5 18.9973 13.5 18.4149 13.5 17.25C13.5 16.0851 13.5 15.5027 13.6903 15.0433C13.944 14.4307 14.4307 13.944 15.0433 13.6903C15.5027 13.5 16.0851 13.5 17.25 13.5C18.4149 13.5 18.9973 13.5 19.4567 13.6903C20.0693 13.944 20.556 14.4307 20.8097 15.0433C21 15.5027 21 16.0851 21 17.25C21 18.4149 21 18.9973 20.8097 19.4567C20.556 20.0693 20.0693 20.556 19.4567 20.8097C18.9973 21 18.4149 21 17.25 21C16.0851 21 15.5027 21 15.0433 20.8097C14.4307 20.556 13.944 20.0693 13.6903 19.4567Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="round" />
              <path d="M13.6903 8.95671C13.5 8.49728 13.5 7.91485 13.5 6.75C13.5 5.58515 13.5 5.00272 13.6903 4.54329C13.944 3.93072 14.4307 3.44404 15.0433 3.1903C15.5027 3 16.0851 3 17.25 3C18.4149 3 18.9973 3 19.4567 3.1903C20.0693 3.44404 20.556 3.93072 20.8097 4.54329C21 5.00272 21 5.58515 21 6.75C21 7.91485 21 8.49728 20.8097 8.95671C20.556 9.56928 20.0693 10.056 19.4567 10.3097C18.9973 10.5 18.4149 10.5 17.25 10.5C16.0851 10.5 15.5027 10.5 15.0433 10.3097C14.4307 10.056 13.944 9.56928 13.6903 8.95671Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="round" />
              <path d="M3.1903 19.4567C3 18.9973 3 18.4149 3 17.25C3 16.0851 3 15.5027 3.1903 15.0433C3.44404 14.4307 3.93072 13.944 4.54329 13.6903C5.00272 13.5 5.58515 13.5 6.75 13.5C7.91485 13.5 8.49728 13.5 8.95671 13.6903C9.56928 13.944 10.056 14.4307 10.3097 15.0433C10.5 15.5027 10.5 16.0851 10.5 17.25C10.5 18.4149 10.5 18.9973 10.3097 19.4567C10.056 20.0693 9.56928 20.556 8.95671 20.8097C8.49728 21 7.91485 21 6.75 21C5.58515 21 5.00272 21 4.54329 20.8097C3.93072 20.556 3.44404 20.0693 3.1903 19.4567Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="round" />
              <path d="M3.1903 8.95671C3 8.49728 3 7.91485 3 6.75C3 5.58515 3 5.00272 3.1903 4.54329C3.44404 3.93072 3.93072 3.44404 4.54329 3.1903C5.00272 3 5.58515 3 6.75 3C7.91485 3 8.49728 3 8.95671 3.1903C9.56928 3.44404 10.056 3.93072 10.3097 4.54329C10.5 5.00272 10.5 5.58515 10.5 6.75C10.5 7.91485 10.5 8.49728 10.3097 8.95671C10.056 9.56928 9.56928 10.056 8.95671 10.3097C8.49728 10.5 7.91485 10.5 6.75 10.5C5.58515 10.5 5.00272 10.5 4.54329 10.3097C3.93072 10.056 3.44404 9.56928 3.1903 8.95671Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="round" />
            </svg>
            <span class="text">Overview</span>
          </a>
        </li>
        <li class="status">
          <a href="/status">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <circle cx="12" cy="18" r="3" stroke="currentColor" stroke-width="1.5"></circle>
              <path d="M12 15V10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
              <path d="M22 13C22 7.47715 17.5228 3 12 3C6.47715 3 2 7.47715 2 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
            </svg>
            <span class="text">Status</span>
          </a>
        </li>
        <li class="cache">
          <a href="/cache">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor"  fill="none">
              <path d="M2.5 12C2.5 7.52166 2.5 5.28249 3.89124 3.89124C5.28249 2.5 7.52166 2.5 12 2.5C16.4783 2.5 18.7175 2.5 20.1088 3.89124C21.5 5.28249 21.5 7.52166 21.5 12C21.5 16.4783 21.5 18.7175 20.1088 20.1088C18.7175 21.5 16.4783 21.5 12 21.5C7.52166 21.5 5.28249 21.5 3.89124 20.1088C2.5 18.7175 2.5 16.4783 2.5 12Z" stroke="currentColor" stroke-width="1.8" />
              <path d="M2.5 12H21.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M13 7L17 7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <circle cx="8.25" cy="7" r="1.25" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <circle cx="8.25" cy="17" r="1.25" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M13 17L17 17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text">Cache</span>
          </a>
        </li>
      </ul>
    `;
  }

  getUserNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="users">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M13 11C13 8.79086 11.2091 7 9 7C6.79086 7 5 8.79086 5 11C5 13.2091 6.79086 15 9 15C11.2091 15 13 13.2091 13 11Z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M11.0386 7.55773C11.0131 7.37547 11 7.18927 11 7C11 4.79086 12.7909 3 15 3C17.2091 3 19 4.79086 19 7C19 9.20914 17.2091 11 15 11C14.2554 11 13.5584 10.7966 12.9614 10.4423" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M15 21C15 17.6863 12.3137 15 9 15C5.68629 15 3 17.6863 3 21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M21 17C21 13.6863 18.3137 11 15 11" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Users</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="all">
              <a href="/users/all"><span class="text">All</span></a>
            </li>
            <li class="add">
              <a href="/users/add"><span class="text">Add</span></a>
            </li>
            <li class="profile">
              <a href="/users/profile"><span class="text">Profile</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getPricingNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="pricing">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M3 8.5H15C17.8284 8.5 19.2426 8.5 20.1213 9.37868C21 10.2574 21 11.6716 21 14.5V15.5C21 18.3284 21 19.7426 20.1213 20.6213C19.2426 21.5 17.8284 21.5 15 21.5H9C6.17157 21.5 4.75736 21.5 3.87868 20.6213C3 19.7426 3 18.3284 3 15.5V8.5Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M15 8.49833V4.1103C15 3.22096 14.279 2.5 13.3897 2.5C13.1336 2.5 12.8812 2.56108 12.6534 2.67818L3.7623 7.24927C3.29424 7.48991 3 7.97203 3 8.49833" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M17.5 15.5C17.7761 15.5 18 15.2761 18 15C18 14.7239 17.7761 14.5 17.5 14.5M17.5 15.5C17.2239 15.5 17 15.2761 17 15C17 14.7239 17.2239 14.5 17.5 14.5M17.5 15.5V14.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Pricing</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="quote">
              <a href="/pricing/quote"><span class="text">Quote</span></a>
            </li>
            <li class="location">
              <a href="/pricing/location"><span class="text">Location</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getBlandNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="bland">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor"  fill="none">
                <path d="M14 3V6M19 5L17 7M21 10H18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M9.15825 5.71223L8.7556 4.80625C8.49232 4.21388 8.36068 3.91768 8.1638 3.69101C7.91707 3.40694 7.59547 3.19794 7.23567 3.08785C6.94858 3 6.62446 3 5.97621 3C5.02791 3 4.55375 3 4.15573 3.18229C3.68687 3.39702 3.26343 3.86328 3.09473 4.3506C2.95151 4.76429 2.99253 5.18943 3.07458 6.0397C3.94791 15.0902 8.90981 20.0521 17.9603 20.9254C18.8106 21.0075 19.2357 21.0485 19.6494 20.9053C20.1367 20.7366 20.603 20.3131 20.8177 19.8443C21 19.4462 21 18.9721 21 18.0238C21 17.3755 21 17.0514 20.9122 16.7643C20.8021 16.4045 20.5931 16.0829 20.309 15.8362C20.0823 15.6393 19.7861 15.5077 19.1937 15.2444L18.2878 14.8417C17.6462 14.5566 17.3255 14.4141 16.9995 14.3831C16.6876 14.3534 16.3731 14.3972 16.0811 14.5109C15.776 14.6297 15.5063 14.8544 14.967 15.3038C14.4301 15.7512 14.1617 15.9749 13.8337 16.0947C13.543 16.2009 13.1586 16.2403 12.8523 16.1951C12.5069 16.1442 12.2423 16.0029 11.7133 15.7201C10.0672 14.8405 9.15953 13.9328 8.27986 12.2867C7.99714 11.7577 7.85578 11.4931 7.80487 11.1477C7.75974 10.8414 7.79908 10.457 7.9053 10.1663C8.02512 9.83828 8.24881 9.56986 8.69619 9.033C9.14562 8.49368 9.37034 8.22402 9.48915 7.91891C9.60285 7.62694 9.64661 7.3124 9.61694 7.00048C9.58594 6.67452 9.44338 6.35376 9.15825 5.71223Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              </svg>
              <span class="text">Bland</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="all">
              <a href="/bland/all"><span class="text">All</span></a>
            </li>
            <li class="add">
              <a href="/bland/add"><span class="text">Test</span></a>
            </li>
            <li class="failed">
              <a href="/bland/failed"><span class="text">Failed</span></a>
            </li>
            <li class="recent">
              <a href="/bland/recent"><span class="text">Recent</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getSheetsNav = () => {
    return /* html */`
      <ul class="special nav opned">
        <li class="sheets">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M12 21H10C6.22876 21 4.34315 21 3.17157 19.8284C2 18.6569 2 16.7712 2 13V11C2 7.22876 2 5.34315 3.17157 4.17157C4.34315 3 6.22876 3 10 3H14C17.7712 3 19.6569 3 20.8284 4.17157C22 5.34315 22 7.22876 22 11V12.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M2 9H22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M2 15H12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M17.5803 13.2673C17.7466 12.9109 18.2534 12.9109 18.4197 13.2673L19.0465 14.6104C19.3226 15.2019 19.7981 15.6774 20.3896 15.9535L21.7327 16.5803C22.0891 16.7466 22.0891 17.2534 21.7327 17.4197L20.3896 18.0465C19.7981 18.3226 19.3226 18.7981 19.0465 19.3896L18.4197 20.7327C18.2534 21.0891 17.7466 21.0891 17.5803 20.7327L16.9535 19.3896C16.6774 18.7981 16.2019 18.3226 15.6104 18.0465L14.2673 17.4197C13.9109 17.2534 13.9109 16.7466 14.2673 16.5803L15.6104 15.9535C16.2019 15.6774 16.6774 15.2019 16.9535 14.6104L17.5803 13.2673Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M8 3V21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Sheets</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="config">
              <a href="/sheet/config"><span class="text">Config</span></a>
            </li>
            <li class="products">
              <a href="/sheet/products"><span class="text">Products</span></a>
            </li>
            <li class="branches">
              <a href="/sheet/branches"><span class="text">Branches</span></a>
            </li>
            <li class="generators">
              <a href="/sheet/generators"><span class="text">Generators</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getDocsNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="docs">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 16L19.8398 17.5858C20.6133 18.2525 21 18.5858 21 19C21 19.4142 20.6133 19.7475 19.8398 20.4142L18 22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M14 16L12.1602 17.5858C11.3867 18.2525 11 18.5858 11 19C11 19.4142 11.3867 19.7475 12.1602 20.4142L14 22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M20 13.0032L20 7.8199C20 6.12616 20 5.27929 19.732 4.60291C19.3013 3.51555 18.3902 2.65784 17.2352 2.25228C16.5168 2 15.6173 2 13.8182 2C10.6698 2 9.09563 2 7.83836 2.44148C5.81714 3.15122 4.22281 4.6522 3.46894 6.55509C3 7.73875 3 9.22077 3 12.1848L3 14.731C3 17.8013 3 19.3364 3.8477 20.4025C4.09058 20.708 4.37862 20.9792 4.70307 21.2078C5.61506 21.8506 6.85019 21.9757 9 22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M3 12C3 10.159 4.49238 8.66667 6.33333 8.66667C6.99912 8.66667 7.78404 8.78333 8.43137 8.60988C9.00652 8.45576 9.45576 8.00652 9.60988 7.43136C9.78333 6.78404 9.66667 5.99912 9.66667 5.33333C9.66667 3.49238 11.1591 2 13 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Docs</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="api">
              <a href="/docs/api"><span class="text">Api</span></a>
            </li>
            <li class="code">
              <a href="/docs/code"><span class="text">Code</span></a>
            </li>
            <li class="features">
              <a href="/docs/features"><span class="text">Features</span></a>
            </li>
            <li class="services">
              <a href="/docs/services"><span class="text">Services</span></a>
            </li>
            <li class="webhooks">
              <a href="/docs/webhooks"><span class="text">Webhooks</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getTweakNav = () => {
    return /* html */`
      <ul class="main user nav">
        <li class="updates">
          <a href="/updates">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" color="currentColor" fill="none">
              <path d="M22 5.5C22 7.433 20.433 9 18.5 9C16.567 9 15 7.433 15 5.5C15 3.567 16.567 2 18.5 2C20.433 2 22 3.567 22 5.5Z" stroke="currentColor" stroke-width="1.8" />
              <path d="M21.9506 11C21.9833 11.3289 22 11.6625 22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C12.3375 2 12.6711 2.01672 13 2.04938" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              <path d="M8 10H12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M8 15H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text">Updates</span>
          </a>
        </li>
        <li class="themes">
          <a href="/themes">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" color="currentColor" fill="none">
              <path d="M14 19L11.1069 10.7479C9.76348 6.91597 9.09177 5 8 5C6.90823 5 6.23652 6.91597 4.89309 10.7479L2 19M4.5 12H11.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M21.9692 13.9392V18.4392M21.9692 13.9392C22.0164 13.1161 22.0182 12.4891 21.9194 11.9773C21.6864 10.7709 20.4258 10.0439 19.206 9.89599C18.0385 9.75447 17.1015 10.055 16.1535 11.4363M21.9692 13.9392L19.1256 13.9392C18.6887 13.9392 18.2481 13.9603 17.8272 14.0773C15.2545 14.7925 15.4431 18.4003 18.0233 18.845C18.3099 18.8944 18.6025 18.9156 18.8927 18.9026C19.5703 18.8724 20.1955 18.545 20.7321 18.1301C21.3605 17.644 21.9692 16.9655 21.9692 15.9392V13.9392Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text">Themes</span>
          </a>
        </li>
      </ul>
    `;
  }

  getOverview = () => {
    return /* html */`
      <app-home api="/shots/fyp" name="For You" type="fyp"></app-home>
    `;
  }

  getFooter = () => {
    const year = new Date().getFullYear();
    return /*html*/`
      <footer class="footer">
        <p class="copyright">Copyright &copy;<span class="year">${year}</span><span class="company"> Stahla Services</span>. All rights reserved.</p>
        <ul class="links">
          <li><a href="/terms">Terms of Service</a></li>
          <li><a href="mailto:isfescii@gmail.com">Developer</a></li>
          <li><a href="/privacy">Privacy</a></li>
          <li><a href="/contact">Contact</a></li>
        </ul>
      </footer>
    `;
  }

  getToast = (status, text) => {
    return /* html */`
      <div id="toast" class="${status === true ? 'success' : 'error'}">
        <div id="img">${status === true ? this.getSuccesToast() : this.getErrorToast()}</div>
        <div id="desc">${text}</div>
      </div>
    `;
  }

  getSuccesToast = () => {
    return /* html */`
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" class="injected-svg" data-src="https://cdn.hugeicons.com/icons/checkmark-circle-02-solid-standard.svg" xmlns:xlink="http://www.w3.org/1999/xlink" role="img" color="currentColor">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M11.75 22.5C5.81294 22.5 1 17.6871 1 11.75C1 5.81294 5.81294 1 11.75 1C17.6871 1 22.5 5.81294 22.5 11.75C22.5 17.6871 17.6871 22.5 11.75 22.5ZM16.5182 9.39018C16.8718 8.9659 16.8145 8.33534 16.3902 7.98177C15.9659 7.62821 15.3353 7.68553 14.9818 8.10981L10.6828 13.2686L8.45711 11.0429C8.06658 10.6524 7.43342 10.6524 7.04289 11.0429C6.65237 11.4334 6.65237 12.0666 7.04289 12.4571L10.0429 15.4571C10.2416 15.6558 10.5146 15.7617 10.7953 15.749C11.076 15.7362 11.3384 15.606 11.5182 15.3902L16.5182 9.39018Z" fill="currentColor"></path>
    `;
  }

  getErrorToast = () => {
    return /* html */`
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" class="injected-svg" data-src="https://cdn.hugeicons.com/icons/cancel-circle-solid-standard.svg" xmlns:xlink="http://www.w3.org/1999/xlink" role="img" color="currentColor">
        <path fill-rule="evenodd" clip-rule="evenodd" d="M1.25 12C1.25 17.9371 6.06294 22.75 12 22.75C17.9371 22.75 22.75 17.9371 22.75 12C22.75 6.06294 17.9371 1.25 12 1.25C6.06294 1.25 1.25 6.06294 1.25 12ZM8.29293 8.29286C8.68348 7.90235 9.31664 7.90239 9.70714 8.29293L12 10.586L14.2929 8.29293C14.6834 7.90239 15.3165 7.90235 15.7071 8.29286C16.0976 8.68336 16.0976 9.31652 15.7071 9.70707L13.4141 12.0003L15.7065 14.2929C16.097 14.6835 16.097 15.3166 15.7064 15.7071C15.3159 16.0976 14.6827 16.0976 14.2922 15.7071L12 13.4146L9.70779 15.7071C9.31728 16.0976 8.68412 16.0976 8.29357 15.7071C7.90303 15.3166 7.90299 14.6835 8.2935 14.2929L10.5859 12.0003L8.29286 9.70707C7.90235 9.31652 7.90239 8.68336 8.29293 8.29286Z" fill="currentColor"></path>
      </svg>
    `;
  }

  getDashboard = () => {
    return /* html */`
      <app-home api="/dashboard/overview" name="Dashboard" type="dashboard"></app-home>
    `;
  }

  getLoader = () => {
    return /* html */`
      <div class="loader-container">
        <div id="loader" class="loader"></div>
      </div>
    `;
  }

  getAccess = () => {
    return /*html*/`
      <access-popup api="/auth/token"></access-popup>
    `
  }

  getDelete = (items, url) => {
    return /*html*/`
      <delete-popup url="${url}">${items}</delete-popup>
    `
  }

  getStyles() {
    return /* css */`
	    <style>
	      *,
	      *:after,
	      *:before {
	        box-sizing: border-box !important;
	        font-family: inherit;
	        -webkit-box-sizing: border-box !important;
	      }

	      *:focus {
	        outline: inherit !important;
	      }

	      *::-webkit-scrollbar {
	        width: 3px;
	      }

	      *::-webkit-scrollbar-track {
	        background: var(--scroll-bar-background);
	      }

	      *::-webkit-scrollbar-thumb {
	        width: 3px;
	        background: var(--scroll-bar-linear);
	        border-radius: 50px;
	      }

	      h1,
	      h2,
	      h3,
	      h4,
	      h5,
	      h6 {
	        font-family: inherit;
	      }

	      a {
	        text-decoration: none;
	      }

	      :host {
          font-size: 16px;
          padding: 0;
          margin: 0;
          display: flex;
          gap: 20px;
        }

        div.loader-container {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 100%;
          height: 100%;
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

        section.nav {
          width: 200px;
          display: flex;
          flex-flow: column;
          gap: 5px;
          padding: 10px 0 0 0;
          height: 100dvh;
          max-height: 100dvh;
          overflow-y: scroll;
          scrollbar-width: none;
          position: sticky;
          top: 0;
        }

        section.nav::-webkit-scrollbar {
          visibility: hidden;
          display: none;
        }

        section.nav > ul.nav.main {
          border-top: var(--border);
          padding: 10px 0;
          margin: 0;
          display: flex;
          flex-flow: column;
          align-items: center;
          width: 100%;
          gap: 5px;
        }

        section.nav > ul.nav.main {
          border: none;
          padding: 0;
        }

        section.nav > ul.nav.logo {
          margin: 0;
          border: none;
          padding: 0;
        }

        section.nav > ul.main.nav > li {
          /* border: thin solid black; */
          padding: 0;
          width: 100%;
          display: flex;
          justify-content: start;
          align-items: center;
          gap: 5px;
          cursor: pointer;
          color: var(--text-color);
          transition: all 0.3s ease;
          border-radius: 7px;
        }

        section.nav > ul.nav.main > li:hover,
        section.nav > ul.nav.main > li.active {
          color: var(--accent-color);
        }

        section.nav > ul.nav.main > li.hubspot.active,
        section.nav > ul.nav.main > li.hubspot:hover {
          background: var(--hubspot-background);
          color: var(--hubspot-color);
        }

        section.nav > ul.nav.main > li > a {
          padding: 5px;
          display: flex;
          justify-content: center;
          align-items: center;
          gap: 8px;
          color: inherit;
          border-radius: 7px;
        }

        section.nav > ul.nav.main > li.active {
          background: var(--tab-background);
        }

        section.nav > ul.nav.main > li > a > svg {
          width: 22px;
          height: 22px;
        }

        section.nav > ul.nav.main > li > a > span.text {
          color: inherit;
          font-family: var(--font-text), sans-serif;
          font-size: 1rem;
          font-weight: 500;
        }

        section.nav > ul.nav > li.logo {
          gap: 10px;
          margin: 5px 0 0 0;
        }

        section.nav > ul.nav > li.logo > a {
          width: 25px;
          height: 25px;
          border-radius: 50%;
          margin: 0;
          padding: 0;
          overflow: hidden;
          display: flex;
          justify-content: center;
          align-items: center;
        }

        section.nav > ul.nav > li.logo > a > img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          border-radius: 50%;
        }

        section.nav > ul.nav > li.logo > span.tooltip > span.text {
          font-family: var(--font-main), sans-serif;
          font-size: 1.5rem;
          color: transparent;
          background: var(--second-linear);
          font-weight: 700;
          line-height: 1.5;
          background-clip: text;
          -webkit-backdrop-clip: text;
          text-transform: capitalize;
        }

        /* special navs */
        section.nav > ul.nav.special {
          /* Container for a special nav group like Cache, Pricing */
          padding: 0;
          margin: 0; /* Adds space between different special nav groups */
          list-style-type: none;
          width: 100%;
        }

        section.nav > ul.nav.special > li {
          /* This is the main li for the group (e.g., li.cache) which will get the 'collapsed' class */
          width: 100%;
          position: relative;
          border-radius: 7px;
          /* background: var(--background-offset); /* Optional: if group needs a distinct background */
          /* box-shadow: var(--shadow-sm); /* Optional: subtle shadow for separation */
        }

        section.nav > ul.nav.special > li > div.link-section {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 5px; /* Padding for the clickable header */
          cursor: pointer;
          color: var(--text-color);
          border-radius: 7px; /* Rounded corners for the clickable area */
          transition: background-color 0.2s ease, color 0.2s ease;
        }

        section.nav > ul.nav.special > li > div.link-section:hover {
          color: var(--accent-color);
          background: var(--tab-background); /* Consistent with normal nav item hover */
        }

        section.nav > ul.nav.special > li > div.link-section > span.left {
          display: flex;
          align-items: center;
          gap: 8px; /* Space between icon and text */
        }

        section.nav > ul.nav.special > li > div.link-section > span.left > svg {
          width: 22px;
          height: 22px;
          color: inherit;
        }

        section.nav > ul.nav.special > li > div.link-section > span.left > span.text {
          color: inherit;
          font-family: var(--font-text), sans-serif;
          font-size: 1rem;
          font-weight: 500; /* Make header text slightly bolder */
        }

        section.nav > ul.nav.special > li > div.link-section > span.right > svg {
          width: 18px;
          height: 18px;
          color: inherit;
          transition: transform 0.3s ease-in-out;
        }

        section.nav > ul.nav.special > li > ul.dropdown {
          list-style-type: none;
          padding: 5px 5px 5px 10px; /* Padding for the dropdown container */
          margin: 0;
          /* max-height: 600px; /* Set a sufficiently large max-height for open state content */
          overflow: hidden;
          transition: max-height 0.35s ease-in-out, opacity 0.3s ease-in-out, padding 0.3s ease-in-out, margin 0.3s ease-in-out, border-color 0.3s ease-in-out;
          opacity: 1;
          position: relative; /* Added for ::before positioning */
          /* border-top: 1px solid var(--border-color, #e0e0e0); /* Optional separator line */
          /* margin-top: 4px; /* Optional space between header and dropdown */
        }

        section.nav > ul.nav.special > li.collapsed > ul.dropdown {
          max-height: 0;
          opacity: 0;
          padding-top: 0;
          padding-bottom: 0;
          margin-top: 0;
          margin-bottom: 0;
          /* border-top-color: transparent; /* Hide border when collapsed */
        }

        section.nav > ul.nav.special > li.collapsed > div.link-section > span.right > svg {
          transform: rotate(-90deg); /* Rotate icon when collapsed */
        }

        section.nav > ul.nav.special > li > ul.dropdown > li {
          width: calc(100% - 10px);
          padding: 0;
          margin: 0 0 0 10px; /* Indent sub-items */
          list-style-type: none;
        }

        section.nav > ul.nav.special > li > ul.dropdown > li > a {
          padding: 7px 10px 7px; /* Padding for dropdown links */
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--text-color);
          border-radius: 5px; /* Slightly smaller radius for sub-items */
          width: 100%;
          font-family: var(--font-text), sans-serif;
          font-size: 0.95rem; /* Slightly smaller font for sub-items */
          font-weight: 400;
          transition: background-color 0.2s ease, color 0.2s ease;
          box-sizing: border-box;
        }

        section.nav > ul.nav.special > li > ul.dropdown > li > a:hover,
        section.nav > ul.nav.special > li > ul.dropdown > li.active > a {
          color: var(--accent-color);
          background: var(--tab-background); /* Consistent with normal nav item active/hover */
        }

        section.nav > ul.nav.special > li.active {
          /* border-left: 3px solid var(--accent-color); */ /* Vertical line for active item */
          /* Instead of border, we use a pseudo-element for animation */
        }

        /* New styles for the vertical animated line on ul.dropdown */
        section.nav > ul.nav.special > li > ul.dropdown::before {
          content: '';
          position: absolute;
          left: 10px; /* Adjusted for a small offset */
          top: 12px; /* Start from the top of the dropdown */
          width: 2px; /* Width of the line */
          background: var(--light-linear); /* Color of the line */
          height: 0; /* Initially hidden, will be controlled by li.active */
          transition: height 0.35s ease-in-out; /* Animation for height */
          border-radius: 5px; /* Optional: if you want rounded corners for the line */
        }

        section.nav > ul.nav.special > li.active > ul.dropdown::before {
          height: calc(100% - 22px); /* Full height minus the top offset */
          max-height: calc(100% - 22px); /* Ensure it doesn't exceed the dropdown */
        }
        /* END of new styles for special navs */


        section.flow {
          width: calc(100% - 220px);
          display: flex;
          flex-flow: column;
          gap: 0;
          padding: 0;
        }

        section.flow > div#content-container {
          width: 100%;
          min-height: calc(100dvh - 70px);
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 0;
          padding: 0;
        }

        /* Mobie section unavailable */
        section.mobile {
          width: 100%;
          height: 100dvh;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 5px;
          padding: 0 10px;
        }

        section.mobile > h1.mobile-title {
          width: 100%;
          padding: 0;
          margin: 0;
          text-align: center;
          font-family: var(--font-text), sans-serif;
          font-size: 1.5rem;
          font-weight: 600;
          line-height: 1.5;
          color: var(--accent-color);
        }

        section.mobile > p.mobile-description {
          width: 100%;
          padding: 0;
          margin: 0;
          font-family: var(--font-main), sans-serif;
          font-size: 1rem;
          text-align: center;
          font-weight: 400;
          color: var(--text-color);
        }

        section.mobile > p.mobile-warning {
          width: 100%;
          padding: 10px 0;
          margin: 0;
          text-align: center;
          font-family: var(--font-read), sans-serif;
          font-size: 0.9rem;
          font-weight: 400;
          color: var(--alt-color);
        }

        footer.footer {
          border-top: var(--border);
          padding: 13px 0;
          margin: 0;
          display: flex;
          flex-flow: column;
          align-items: center;
          width: 100%;
          gap: 3px;
        }

        footer.footer > p {
          margin: 0;
          text-align: center;
          padding: 0;
          font-family: var(--font-read), sans-serif;
          font-size: 1rem;
          color: var(--gray-color);
        }

        footer.footer > p > span.year {
          font-size: 1rem;
          font-family: var(--font-read), sans-serif;
        }
        
        footer.footer > p > span.company {
          font-size: 0.9rem;
          display: inline-block;
          padding: 0 0 0 5px;
          color: var(--alt-color);
          font-family: var(--font-text), sans-serif;
        }

        footer.footer > ul.links {
          text-align: center;
          padding: 0;
          margin: 0;
          display: flex;
          flex-flow: row;
          width: 100%;
          justify-content: center;
          align-items: center;
          gap: 10px;
        }

        section.mobile > footer.footer {
          width: 100%;
          margin: 30px 0 0 0;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 5px;
        }

        section.mobile > footer.footer > ul.links {
          padding: 10px 0;
          flex-flow: row wrap;
          column-gap: 10px;
        }

        footer.footer > ul.links > li {
          padding: 0;
          margin: 0 0 0 12px;
          list-style-type: default;
          color: var(--gray-color);
        }

        footer.footer > ul.links > li > a {
          font-family: var(--font-read), sans-serif;
          font-size: 0.9rem;
          color: var(--gray-color);
        }

        footer.footer > ul.links > li > a:hover {
          color: var(--anchor-color);
        }
	    </style>
    `;
  }

  _expandDropdown(parentLi) {
    if (!parentLi) return;
    
    // Remove collapsed class and add active class to show vertical line
    parentLi.classList.remove('collapsed');
    parentLi.classList.add('active');
    
    // Get the dropdown and expand it
    const dropdown = parentLi.querySelector('ul.dropdown');
    if (dropdown) {
      // Set max height to scrollHeight to show the dropdown
      dropdown.style.maxHeight = (dropdown.scrollHeight + 7) + 'px';
    }
    
    // Close other dropdowns
    const specialNavUls = this.shadowRoot.querySelectorAll('section.nav > ul.nav.special');
    specialNavUls.forEach(ul => {
      const item = ul.querySelector('li');
      if (item && item !== parentLi) {
        item.classList.add('collapsed');
        item.classList.remove('active');
        const otherDropdown = item.querySelector('ul.dropdown');
        if (otherDropdown) {
          otherDropdown.style.maxHeight = '0px';
        }
      }
    });
  }
}