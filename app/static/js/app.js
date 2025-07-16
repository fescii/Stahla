import APIManager from "./api.js";
import uis from "./uis/apps.js"

export default class AppMain extends HTMLElement {
  constructor() {
    super();
    this.content = this.getContent();
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.registerComponents();
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
    this.shadowObj.innerHTML = this.getTemplate(this.isAuthenticated());
    // watch for media query changes
    this.watchMeta();
  }

  isAuthenticated() {
    // Check if a cookie named: x-account-token exists
    const token = document.cookie.split('; ').find(row => row.startsWith('x-account-token='));
    return !!token;
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

    // Get all navigation links (excluding external links)
    const navLinks = this.shadowRoot.querySelectorAll('section.nav a[href]:not(.external-link)');

    navLinks.forEach(link => {
      link.addEventListener('click', (event) => {
        event.preventDefault();

        const url = link.getAttribute('href');

        // Update active class for main nav items
        this._updateActiveNavItem(url);

        // Get content for the URL
        const content = this.getNavContents[url] || this.getNavContents.default;

        // Navigate to the URL with the content as state
        this.navigate(url, { kind: 'app', html: content });
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

  setUpEvents = () => {
    // set display to flex
    this.style.setProperty('display', 'flex');
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

  navigate = (url, state) => {
    const container = this.shadowObj.querySelector('section.flow > div#content-container.content-container');
    const content = state ? state : this.getNavContents[url] || this.getNavContents.default;
    this.push(url, content, url);
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
  push(url, state = {}, title = '') {
    window.history.pushState(state, title, url);
    this.currentUrl = url;
  }

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
            dropdown.style.maxHeight = (dropdown.scrollHeight + 7) + 'px'; // Add some padding
          } else { // If it was open, close it
            item.classList.add('collapsed');
            item.classList.remove('active'); // Remove active class for the vertical line
            dropdown.style.maxHeight = '0px';
          }
        });
      }
    });
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
    "/pricing/quote": /* HTML */`<quote-form api="/webhook/quote/generate"></quote-form>`,
    "/bland/all": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/bland/add": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/bland/failed": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/bland/recent": /* HTML */`<soon-page url="/soon"></soon-page>`,
    "/sheet/config": /* HTML */`<sheet-config api="/dashboard/sheet/config"></sheet-config>`,
    "/sheet/generators": /* HTML */`<sheet-generators api="/dashboard/sheet/generators"></sheet-generators>`,
    "/sheet/products": /* HTML */`<sheet-products api="/dashboard/sheet/products"></sheet-products>`,
    "/sheet/branches": /* HTML */`<sheet-branches api="/dashboard/sheet/branches"></sheet-branches>`,
    "/sheet/states": /* HTML */`<sheet-states api="/dashboard/sheet/states"></sheet-states>`,
    "/updates": /* HTML */`<soon-page url="/soon"></soon-page>`,

    // Quotes routes
    "/quotes/recent": /* HTML */`<quotes-recent api="/mongo/quotes/recent"></quotes-recent>`,
    "/quotes/oldest": /* HTML */`<quotes-oldest api="/mongo/quotes/oldest"></quotes-oldest>`,
    "/quotes/highest": /* HTML */`<quotes-highest api="/mongo/quotes/highest"></quotes-highest>`,
    "/quotes/lowest": /* HTML */`<quotes-lowest api="/mongo/quotes/lowest"></quotes-lowest>`,

    // Location routes
    "/location/recent": /* HTML */`<location-recent api="/mongo/location/recent"></location-recent>`,
    "/location/oldest": /* HTML */`<location-oldest api="/mongo/location/oldest"></location-oldest>`,
    "/location/success": /* HTML */`<location-success api="/mongo/location/successful"></location-success>`,
    "/location/failed": /* HTML */`<location-failed api="/mongo/location/failed"></location-failed>`,
    "/location/pending": /* HTML */`<location-pending api="/mongo/location/pending"></location-pending>`,

    // HubSpot routes
    "/hubspot/contacts": /* HTML */`<hubspot-contacts api="/hubspot/contacts/recent"></hubspot-contacts>`,
    "/hubspot/leads": /* HTML */`<hubspot-leads api="/hubspot/leads/recent"></hubspot-leads>`,
    "/hubspot/properties": /* HTML */`<hubspot-properties api="/hubspot/properties/all"></hubspot-properties>`,

    // Properties routes
    "/properties/contact": /* HTML */`<properties-contact api="/hubspot/properties/contacts"></properties-contact>`,
    "/properties/lead": /* HTML */`<properties-lead api="/hubspot/properties/leads"></properties-lead>`,
    "/properties/fields": /* HTML */`<properties-fields api="/hubspot/properties/all"></properties-fields>`,

    // Classify routes
    "/classify/recent": /* HTML */`<classify-recent api="/mongo/classify/recent"></classify-recent>`,
    "/classify/success": /* HTML */`<classify-success api="/mongo/classify/successful"></classify-success>`,
    "/classify/failed": /* HTML */`<classify-failed api="/mongo/classify/failed"></classify-failed>`,
    "/classify/disqualified": /* HTML */`<classify-disqualified api="/mongo/classify/disqualified"></classify-disqualified>`,

    // Calls routes
    "/calls/recent": /* HTML */`<calls-recent api="/mongo/calls/recent"></calls-recent>`,
    "/calls/success": /* HTML */`<calls-success api="/mongo/calls/successful"></calls-success>`,
    "/calls/failed": /* HTML */`<calls-failed api="/mongo/calls/failed"></calls-failed>`,
    "/calls/oldest": /* HTML */`<calls-oldest api="/mongo/calls/oldest"></calls-oldest>`,
    default: /* HTML */`<soon-page url="/soon"></soon-page>`,
  }

  getTemplate = (authenticated = false) => {
    if (!authenticated) return `${this.getAccess()}`
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
          <p class="mobile-warning">The mobile version is not available yet. Please use the desktop or tablet version for the best experience.</p>
          ${this.getFooter()}
        </section>
      `;
    }
    else {
      // Only show navigation if authenticated
      return /* html */`
        ${this.getMainNav()}
        <section class="flow">
          <div id="content-container" class="content-container">
            ${this.getLoader()}
          </div>
          ${this.getFooter()}
        </section>
        ${this.getLatency()}
      `;
    }
  }

  getMainNav = () => {
    return /* html */`
      <section class="nav">
        ${this.getLogoNav()}
        ${this.getMainLinksNav()}
        ${this.getUserNav()}
        ${this.getBlandNav()}
        ${this.getSheetsNav()}
        ${this.getPricingNav()}
        ${this.getQuotesNav()}
        ${this.getCallsNav()}
        ${this.getClassifyNav()}
        ${this.getHubspotNav()}
        ${this.getLocationNav()}
        ${this.getEmailNav()}
        ${this.getPropertiesNav()}
        ${this.getTweakNav()}
      </section>
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
              <path d="M3 11.9896V14.5C3 17.7998 3 19.4497 4.02513 20.4749C5.05025 21.5 6.70017 21.5 10 21.5H14C17.2998 21.5 18.9497 21.5 19.9749 20.4749C21 19.4497 21 17.7998 21 14.5V11.9896C21 10.3083 21 9.46773 20.6441 8.74005C20.2882 8.01237 19.6247 7.49628 18.2976 6.46411L16.2976 4.90855C14.2331 3.30285 13.2009 2.5 12 2.5C10.7991 2.5 9.76689 3.30285 7.70242 4.90855L5.70241 6.46411C4.37533 7.49628 3.71179 8.01237 3.3559 8.74005C3 9.46773 3 10.3083 3 11.9896Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
              <path d="M15.0002 17C14.2007 17.6224 13.1504 18 12.0002 18C10.8499 18 9.79971 17.6224 9.00018 17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
            </svg>
            <span class="text">Home</span>
          </a>
        </li>
        <li class="status">
          <a href="/status">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
              <circle cx="12" cy="18" r="3" stroke="currentColor" stroke-width="1.8"></circle>
              <path d="M12 15V10" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
              <path d="M22 13C22 7.47715 17.5228 3 12 3C6.47715 3 2 7.47715 2 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"></path>
            </svg>
            <span class="text">Status</span>
          </a>
        </li>
        <li class="docs">
          <a href="/docs" target="_blank" rel="noopener noreferrer" class="external-link">
            <span class="link-content">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M17 8L18.8398 9.85008C19.6133 10.6279 20 11.0168 20 11.5C20 11.9832 19.6133 12.3721 18.8398 13.1499L17 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M7 8L5.16019 9.85008C4.38673 10.6279 4 11.0168 4 11.5C4 11.9832 4.38673 12.3721 5.16019 13.1499L7 15" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M14.5 4L9.5 20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Docs</span>
            </span>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" color="currentColor" fill="none" class="external-icon">
              <path d="M11.1004 3.00208C7.4515 3.00864 5.54073 3.09822 4.31962 4.31931C3.00183 5.63706 3.00183 7.75796 3.00183 11.9997C3.00183 16.2415 3.00183 18.3624 4.31962 19.6801C5.6374 20.9979 7.75836 20.9979 12.0003 20.9979C16.2421 20.9979 18.3631 20.9979 19.6809 19.6801C20.902 18.4591 20.9916 16.5484 20.9982 12.8996" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
              <path d="M20.4803 3.51751L14.931 9.0515M20.4803 3.51751C19.9863 3.023 16.6587 3.0691 15.9552 3.0791M20.4803 3.51751C20.9742 4.01202 20.9282 7.34329 20.9182 8.04754" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
            </svg>
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
                <path d="M13 11C13 8.79086 11.2091 7 9 7C6.79086 7 5 8.79086 5 11C5 13.2091 6.79086 15 9 15C11.2091 15 13 13.2091 13 11Z" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M11.0386 7.55773C11.0131 7.37547 11 7.18927 11 7C11 4.79086 12.7909 3 15 3C17.2091 3 19 4.79086 19 7C19 9.20914 17.2091 11 15 11C14.2554 11 13.5584 10.7966 12.9614 10.4423" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
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
            <li class="calls">
              <a href="/bland/calls"><span class="text">Calls</span></a>
            </li>
            <li class="status">
              <a href="/bland/status"><span class="text">Status</span></a>
            </li>
            <li class="failed">
              <a href="/bland/failed"><span class="text">Failed</span></a>
            </li>
            <li class="simulate">
              <a href="/bland/simulate"><span class="text">Simulate</span></a>
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
            <li class="states">
              <a href="/sheet/states"><span class="text">States</span></a>
            </li>
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

  getQuotesNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="quotes">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M22 14V10C22 6.22876 22 4.34315 20.8284 3.17157C19.6569 2 17.7712 2 14 2H12C8.22876 2 6.34315 2 5.17157 3.17157C4 4.34315 4 6.22876 4 10V14C4 17.7712 4 19.6569 5.17157 20.8284C6.34315 22 8.22876 22 12 22H14C17.7712 22 19.6569 22 20.8284 20.8284C22 19.6569 22 17.7712 22 14Z" stroke="currentColor" stroke-width="1.8" />
                <path d="M5 6L2 6M5 12H2M5 18H2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M17.5 7L13.5 7M15.5 11H13.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M9 22L9 2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Quotes</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="recent">
              <a href="/quotes/recent"><span class="text">Recent</span></a>
            </li>
            <li class="oldest">
              <a href="/quotes/oldest"><span class="text">Oldest</span></a>
            </li>
            <li class="highest">
              <a href="/quotes/highest"><span class="text">Highest</span></a>
            </li>
            <li class="lowest">
              <a href="/quotes/lowest"><span class="text">Lowest</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getCallsNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="calls">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M3.77762 11.9424C2.8296 10.2893 2.37185 8.93948 2.09584 7.57121C1.68762 5.54758 2.62181 3.57081 4.16938 2.30947C4.82345 1.77638 5.57323 1.95852 5.96 2.6524L6.83318 4.21891C7.52529 5.46057 7.87134 6.08139 7.8027 6.73959C7.73407 7.39779 7.26737 7.93386 6.33397 9.00601L3.77762 11.9424ZM3.77762 11.9424C5.69651 15.2883 8.70784 18.3013 12.0576 20.2224M12.0576 20.2224C13.7107 21.1704 15.0605 21.6282 16.4288 21.9042C18.4524 22.3124 20.4292 21.3782 21.6905 19.8306C22.2236 19.1766 22.0415 18.4268 21.3476 18.04L19.7811 17.1668C18.5394 16.4747 17.9186 16.1287 17.2604 16.1973C16.6022 16.2659 16.0661 16.7326 14.994 17.666L12.0576 20.2224Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"></path>
                <path d="M19.7731 4.22687L13 11M19.7731 4.22687C19.2678 3.72156 16.8846 4.21665 16.1649 4.22687M19.7731 4.22687C20.2784 4.73219 19.7834 7.11544 19.7731 7.83508" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
              </svg>
              <span class="text">Calls</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="failed">
              <a href="/calls/failed"><span class="text">Failed</span></a>
            </li>
            <li class="oldest">
              <a href="/calls/oldest"><span class="text">Oldest</span></a>
            </li>
            <li class="recent">
              <a href="/calls/recent"><span class="text">Recent</span></a>
            </li>
            <li class="success">
              <a href="/calls/success"><span class="text">Success</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getClassifyNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="classify">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M10 7L9.48415 8.39405C8.80774 10.222 8.46953 11.136 7.80278 11.8028C7.13603 12.4695 6.22204 12.8077 4.39405 13.4842L3 14L4.39405 14.5158C6.22204 15.1923 7.13603 15.5305 7.80278 16.1972C8.46953 16.864 8.80774 17.778 9.48415 19.6059L10 21L10.5158 19.6059C11.1923 17.778 11.5305 16.864 12.1972 16.1972C12.864 15.5305 13.778 15.1923 15.6059 14.5158L17 14L15.6059 13.4842C13.778 12.8077 12.864 12.4695 12.1972 11.8028C11.5305 11.136 11.1923 10.222 10.5158 8.39405L10 7Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                <path d="M18 3L17.7789 3.59745C17.489 4.38087 17.3441 4.77259 17.0583 5.05833C16.7726 5.34408 16.3809 5.48903 15.5975 5.77892L15 6L15.5975 6.22108C16.3809 6.51097 16.7726 6.65592 17.0583 6.94167C17.3441 7.22741 17.489 7.61913 17.7789 8.40255L18 9L18.2211 8.40255C18.511 7.61913 18.6559 7.22741 18.9417 6.94166C19.2274 6.65592 19.6191 6.51097 20.4025 6.22108L21 6L20.4025 5.77892C19.6191 5.48903 19.2274 5.34408 18.9417 5.05833C18.6559 4.77259 18.511 4.38087 18.2211 3.59745L18 3Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
              </svg>
              <span class="text">Classify</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="failed">
              <a href="/classify/failed"><span class="text">Failed</span></a>
            </li>
            <li class="recent">
              <a href="/classify/recent"><span class="text">Recent</span></a>
            </li>
            <li class="success">
              <a href="/classify/success"><span class="text">Success</span></a>
            </li>
            <li class="disqualified">
              <a href="/classify/disqualified"><span class="text">Disqualified</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getHubspotNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="hubspot">
          <div class="link-section">
            <span class="left">
              <svg fill="currentColor" width="800px" height="800px" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" role="img">
                <path d="M18.164 7.931V5.085a2.198 2.198 0 0 0 1.266-1.978V3.04A2.199 2.199 0 0 0 17.238.847h-.067a2.199 2.199 0 0 0-2.193 2.192v.067a2.196 2.196 0 0 0 1.252 1.973l.013.006v2.852a6.22 6.22 0 0 0-2.969 1.31l.012-.009-7.828-6.096a2.497 2.497 0 1 0-1.157 1.515l-.012.006 7.696 5.991a6.176 6.176 0 0 0-1.038 3.446c0 1.343.425 2.588 1.147 3.606l-.013-.019-2.342 2.342a1.968 1.968 0 0 0-.58-.095h-.002a2.033 2.033 0 1 0 2.033 2.033 1.978 1.978 0 0 0-.099-.595l.004.014 2.317-2.317a6.247 6.247 0 1 0 4.782-11.133l-.036-.005zm-.964 9.377a3.206 3.206 0 1 1 3.214-3.206v.002a3.206 3.206 0 0 1-3.206 3.206z"/>
              </svg>
              <span class="text">Hubspot</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="leads">
              <a href="/hubspot/leads"><span class="text">Leads</span></a>
            </li>
            <li class="contacts">
              <a href="/hubspot/contacts"><span class="text">Contacts</span></a>
            </li>
            <li class="properties">
              <a href="/hubspot/properties"><span class="text">Properties</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getLocationNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="location">
          <div class="link-section">
            <span class="left">
             <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M13.6177 21.367C13.1841 21.773 12.6044 22 12.0011 22C11.3978 22 10.8182 21.773 10.3845 21.367C6.41302 17.626 1.09076 13.4469 3.68627 7.37966C5.08963 4.09916 8.45834 2 12.0011 2C15.5439 2 18.9126 4.09916 20.316 7.37966C22.9082 13.4393 17.599 17.6389 13.6177 21.367Z" stroke="currentColor" stroke-width="1.8" />
                <path d="M15.5 11C15.5 12.933 13.933 14.5 12 14.5C10.067 14.5 8.5 12.933 8.5 11C8.5 9.067 10.067 7.5 12 7.5C13.933 7.5 15.5 9.067 15.5 11Z" stroke="currentColor" stroke-width="1.8" />
              </svg>
              <span class="text">Location</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="failed">
              <a href="/location/failed"><span class="text">Failed</span></a>
            </li>
            <li class="recent">
              <a href="/location/recent"><span class="text">Recent</span></a>
            </li>
            <li class="success">
              <a href="/location/success"><span class="text">Success</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getEmailNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="email">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M7 8.5L9.94202 10.2394C11.6572 11.2535 12.3428 11.2535 14.058 10.2394L17 8.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path>
                <path d="M2.01576 13.4756C2.08114 16.5411 2.11382 18.0739 3.24495 19.2093C4.37608 20.3448 5.95033 20.3843 9.09883 20.4634C11.0393 20.5122 12.9607 20.5122 14.9012 20.4634C18.0497 20.3843 19.6239 20.3448 20.755 19.2093C21.8862 18.0739 21.9189 16.5411 21.9842 13.4756C22.0053 12.4899 22.0053 11.51 21.9842 10.5244C21.9189 7.45883 21.8862 5.92606 20.755 4.79063C19.6239 3.6552 18.0497 3.61565 14.9012 3.53654C12.9607 3.48778 11.0393 3.48778 9.09882 3.53653C5.95033 3.61563 4.37608 3.65518 3.24495 4.79062C2.11382 5.92605 2.08113 7.45882 2.01576 10.5243C1.99474 11.51 1.99474 12.4899 2.01576 13.4756Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"></path>
              </svg>
              <span class="text">Emails</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="sent">
              <a href="/email/sent"><span class="text">Sent</span></a>
            </li>
            <li class="properties">
              <a href="/email/failed"><span class="text">Failed</span></a>
            </li>
            <li class="compose">
              <a href="/email/compose"><span class="text">Compose</span></a>
            </li>
            <li class="received">
              <a href="/email/received"><span class="text">Received</span></a>
            </li>
          </ul>
        </li>
      </ul>
    `;
  }

  getPropertiesNav = () => {
    return /* html */`
      <ul class="special nav">
        <li class="properties">
          <div class="link-section">
            <span class="left">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M2.50014 11.9999C2.50014 7.52157 2.50014 5.28239 3.89138 3.89115C5.28263 2.49991 7.5218 2.49991 12.0001 2.49991C16.4785 2.49991 18.7177 2.49991 20.1089 3.89115C21.5001 5.28239 21.5001 7.52157 21.5001 11.9999C21.5001 16.4783 21.5001 18.7174 20.1089 20.1087C18.7177 21.4999 16.4785 21.4999 12.0001 21.4999C7.5218 21.4999 5.28263 21.4999 3.89138 20.1087C2.50014 18.7174 2.50014 16.4783 2.50014 11.9999Z" stroke="currentColor" stroke-width="1.8" />
                <path d="M2.5 8H21.5" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                <path d="M11 17H17M7 17H8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
                <path d="M11 13H17M7 13H8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
              <span class="text">Properties</span>
            </span>
            <span class="right">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" color="currentColor" fill="none">
                <path d="M18 9.00005C18 9.00005 13.5811 15 12 15C10.4188 15 6 9 6 9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
          </div>
          <ul class="dropdown">
            <li class="leads">
              <a href="/properties/lead"><span class="text">Lead</span></a>
            </li>
            <li class="fields">
              <a href="/properties/fields"><span class="text">Fields</span></a>
            </li>
            <li class="contact">
              <a href="/properties/contact"><span class="text">Contact</span></a>
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

  getLatency = () => {
    return /* html */`
      <section class="sidebar">
       <sidebar-section section-title="Latency Overview" description="Monitoring performance and response times"></sidebar-section>
      </section>
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
          width: 100%;
          min-width: 100%;
          max-width: 100%;
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
          width: 220px;
          display: flex;
          flex-flow: column;
          gap: 5px;
          padding: 10px 0 0 10px;
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

        /* External link styles */
        section.nav > ul.nav.main > li > a.external-link {
          justify-content: space-between;
          width: 100%;
          padding: 5px;
          display: flex;
          align-items: center;
          color: inherit;
          border-radius: 7px;
        }

        section.nav > ul.nav.main > li > a.external-link > .link-content {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }

        section.nav > ul.nav.main > li > a.external-link > .external-icon {
          width: 16px;
          height: 16px;
          opacity: 0.7;
          flex-shrink: 0;
        }

        section.nav > ul.nav > li.logo {
          gap: 10px;
          margin: 5px 0;
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

        section.nav > ul.nav.special > li > div.link-section > span.left > svg#other {
          width: 24px;
          height: 24px;
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
          padding: 0; /* Padding for sub-items */
          margin: 0 0 0 5px; /* Indent sub-items */
          list-style-type: none;
          position: relative;
          display: flex;
        }

        section.nav > ul.nav.special > li > ul.dropdown > li > a {
          padding: 7px 14px 7px 18px; /* Padding for dropdown links */
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--gray-color);
          border-radius: 5px; /* Slightly smaller radius for sub-items */
          width: 100%;
          font-family: var(--font-text), sans-serif;
          font-size: 0.95rem; /* Slightly smaller font for sub-items */
          font-weight: 400;
          transition: background-color 0.2s ease, color 0.2s ease;
          box-sizing: border-box;
        }

        section.nav > ul.nav.special > li > ul.dropdown > li > a:hover {
          background: var(--gray-background); /* Consistent with normal nav item hover */
        }
        section.nav > ul.nav.special > li > ul.dropdown > li.active > a {
          color: var(--accent-color);
          background: var(--tab-background); /* Consistent with normal nav item active/hover */
        }

        section.nav > ul.nav.special > li.active {
          /* border-left: 3px solid var(--accent-color); */ /* Vertical line for active item */
          /* Instead of border, we use a pseudo-element for animation */
        }

        section.nav > ul.nav.special > li > ul.dropdown > li::before {
          content: '-';
          position: absolute;
          left: 5px;
          top: 50%;
          color: var(--gray-color);
          transform: translateY(-50%);
          z-index: 1;
        }

        section.nav > ul.nav.special > li > ul.dropdown > li.active::before {
          color: var(--accent-color);
          transition: color 0.2s ease;
        }

        section.nav > ul.nav.special > li > ul.dropdown > li:hover::before {
          color: var(--gray-color);
          transition: color 0.2s ease;
        }

        section.flow {
          width: calc(100% - (240px + 500px + 20px));
          display: flex;
          flex-flow: column;
          max-height: max-content;
          gap: 0;
          padding: 0;
        }

        /* Latency Panel Styles */
        section.sidebar {
          width: 500px;
          height: 100dvh;
          padding: 0;
          background: var(--background);
          /* border-left: var(--border); */
          display: flex;
          flex-flow: column;
          max-height: 100dvh;
          gap: 0;
          z-index: 10;
          overflow-y: auto;
          scrollbar-width: none;
          position: sticky;
          top: 0;
        }

        section.sidebar::-webkit-scrollbar {
          visibility: hidden;
          display: none;
        }

        section.flow > div#content-container {
          width: 100%;
          min-height: calc(100dvh - 140px);
          max-height: max-content;
          display: flex;
          flex-flow: column;
          gap: 0;
          padding: 0;
        }

        /* Mobile section unavailable */
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
          height: 70px;
          max-height: 70px;
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
}
