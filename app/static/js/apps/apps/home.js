export default class AppHome extends HTMLElement {
  constructor() {
    super();
    this.setTitle();
    this.app = window.app;
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.mql = window.matchMedia('(max-width: 700px)');
    this.active_tab = null;
    this.render();
    window.addEventListener('popstate', this.handlePopState);
  }

  setTitle = () => {
    document.title = '0verview | Stahla SDR AI & Pricing Dashboard';
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.watchMediaQuery(this.mql);
  }

  disconnectedCallback() {
    this.enableScroll();
  }

  // watch for mql changes
  watchMediaQuery = mql => {
    mql.addEventListener('change', () => {
      // Re-render the component
      this.render();
    });
  }

  formatNumber = numStr => {
    try {
      const num = parseInt(numStr);

      // less than a thousand: return the number
      if (num < 1000) return num;

      // less than a 10,000: return the number with a k with two decimal places
      if (num < 10000) return `${(num / 1000).toFixed(2)}k`;

      // less than a 100,000: return the number with a k with one decimal place
      if (num < 100000) return `${(num / 1000).toFixed(1)}k`;

      // less than a million: return the number with a k with no decimal places
      if (num < 1000000) return `${Math.floor(num / 1000)}k`;

      // less than a 10 million: return the number with an m with two decimal places
      if (num < 10000000) return `${(num / 1000000).toFixed(2)}M`;

      // less than a 100 million: return the number with an m with one decimal place
      if (num < 100000000) return `${(num / 1000000).toFixed(1)}M`;

      // less than a billion: return the number with an m with no decimal places
      if (num < 1000000000) return `${Math.floor(num / 1000000)}M`;

      // a billion or more: return the number with a B+
      if (num >= 1000000000) return `${Math.floor(num / 1000000000)}B+`;

      // else return the zero
      return '0';
    } catch (error) {
      return '0';
    }
  }

  disableScroll() {
    // Get the current page scroll position
    let scrollTop = window.scrollY || document.documentElement.scrollTop;
    let scrollLeft = window.scrollX || document.documentElement.scrollLeft;
    document.body.classList.add("stop-scrolling");

    // if any scroll is attempted, set this to the previous value
    window.onscroll = function () {
      window.scrollTo(scrollLeft, scrollTop);
    };
  }

  enableScroll() {
    document.body.classList.remove("stop-scrolling");
    window.onscroll = function () { };
  }

  getTemplate = () => {
    // Show HTML Here
    return `
      ${this.getBody()}
      ${this.getStyles()}
    `;
  }

  getOverview = () => {
    return /* html */`
      <dash-overview api="/dashboard/overview"></dash-overview>
    `
  }

  getSheetProducts = () => {
    return /* html */`
      <sheet-products api="/dashboard/sheet/products"></sheet-products>
    `;
  }

  getSheetBranches = () => {
    return /* html */`
      <sheet-branches api="/dashboard/sheet/branches"></sheet-branches>
    `;
  }

  getSheetGenerators = () => {
    return /* html */`
      <sheet-generators api="/dashboard/sheet/generators"></sheet-generators>
    `;
  }

  getSheetConfig = () => {
    return /* html */`
      <sheet-config api="/dashboard/sheet/config"></sheet-config>
    `;
  }

  getServicesStatus = () => {
    return /* html */`
      <services-status api="/dashboard/services/status"></services-status>
    `;
  }

  getCacheSearch = () => {
    return /* html */`
      <cache-search api="/dashboard/cache/search"></cache-search>
    `;
  }

  getBody = () => {
    return /* html */`
      <div class="feeds">
        <div class="content-container">
          ${this.getCacheSearch()}
        </div>
      <div>
    `;
  }

  getInfo = () => {
    return /*html*/`
      <info-container docs="/about/docs" new="/about/new"
       feedback="/about/feedback" request="/about/request" code="/about/code" donate="/about/donate" contact="/about/contact" company="https://github.com/aduki-hub">
      </info-container>
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
	        padding: 0;
	        margin: 0;
	        font-family: inherit;
	      }

	      p,
	      ul,
	      ol {
	        padding: 0;
	        margin: 0;
	      }

	      a {
	        text-decoration: none;
	      }

	      :host {
          font-size: 16px;
          padding: 0;
          margin: 0;
          display: flex;
          justify-content: space-between;
          gap: 30px;
          width: 100%;
          max-width: 100%;
        }

        .feeds {
          display: flex;
          flex-flow: column;
          gap: 0;
          width: 100%;
        }

        .content-container {
          display: flex;
          flex-flow: column;
          gap: 0;
          padding: 0;
          width: 100%;
        }
	    </style>
    `;
  }
}