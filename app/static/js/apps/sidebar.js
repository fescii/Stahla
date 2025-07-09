export default class Sidebar extends HTMLElement {
  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: 'open' });
    this.user = this.getUserData();
    this.render();
  }

  render() {
    this.shadow.innerHTML = this.getTemplate();
  }

  // get user data from local storage
  getUserData() {
    try {
      const userData = localStorage.getItem('user');
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error('Error retrieving user data from localStorage:', error);
      return null;
    }
  }

  connectedCallback() {
    this.setUpEventListeners();
  }

  getTemplate() {
    return /* html */`
      ${this.getHeader()}
      <div class="content-wrapper">
        <latency-overview api="/latency/overview/data"></latency-overview>
      </div>
      ${this.getStyles()}
    `;
  }

  getHeader = () => {
    return /* html */`
      <header class="header">
        <div class="header-title">
          <h1 class="title">${this.getAttribute('section-title')}</h1>
          <span class="subtitle">${this.getAttribute('description')}</span>
        </div>
        <ul class="links">
          <li class="link profile">
            <div class="image">
              ${this.getPicture(this.user?.picture)}
            </div>
            <span class="text">Profile</span>
          </li>
          <li class="link updates">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" color="currentColor" fill="none">
              <path id="animate" d="M22 5.5C22 7.433 20.433 9 18.5 9C16.567 9 15 7.433 15 5.5C15 3.567 16.567 2 18.5 2C20.433 2 22 3.567 22 5.5Z" stroke="currentColor" stroke-width="1.8" />
              <path d="M21.9506 11C21.9833 11.3289 22 11.6625 22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C12.3375 2 12.6711 2.01672 13 2.04938" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              <path d="M8 10H12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M8 15H16" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
            <span class="text">Updates</span>
          </li>
          <li class="link more">
            <span class="icon">
              <span class="sp"></span>
              <span class="sp"></span>
            </span>
            <span class="text">More</span>
          </li>
        </ul>
      </header>
    `
  }

  getPicture = url => {
    if (!this.user || !this.user.picture) {
      return /* html */`
        <img src="/static/img/profile.png" alt="Default Profile Picture" />
      `;
    }
    return /* html */`
      <img src="${url}" alt="User Profile Picture" />
    `;
  }

  getStyles = () => {
    return /* css */`
      <style>
        :host {
          display: flex;
          max-width: 100%;
          width: 100%;
          display: flex;
          flex-direction: column;
          align-items: start;
          padding: 0 10px;
          gap: 20px;
        }

        * {
          box-sizing: border-box;
          font-family: var(--font-main), sans-serif;
        }

        /* Content Wrapper */
        .content-wrapper {
          width: 100%;
          max-width: 100%;
          padding: 0;
          display: flex;
          flex-direction: column;
        }

        /* Header Styles */
        header.header {
          height: 70px;
          max-height: 70px;
          width: 100%;
          padding: 25px 0;
          background: var(--background);
          border-bottom: var(--border);
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 20px;
          position: sticky;
          top: 0;
          z-index: 100;
          backdrop-filter: blur(10px);
        }

        header.header > div.header-title {
          flex: 1;
          width: calc(100% - 170px);
          display: flex;
          flex-direction: column;
          padding: 2px;
          transition: all 0.3s ease;
        }

        header.header > div.header-title > h1.title {
          font-family: var(--font-main), sans-serif;
          font-size: 1.35rem;
          font-weight: 700;
          line-height: 1.4;
          color: var(--text-color);
          margin: 0;
          padding: 0;
          text-transform: capitalize;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        header.header > div.header-title > span.subtitle {
          font-family: var(--font-text), sans-serif;
          font-size: 0.8rem;
          font-weight: 400;
          line-height: 1.4;
          color: var(--gray-color);
          margin: 0;
          padding: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        header.header > ul.links {
          display: flex;
          align-items: center;
          gap: 15px;
          margin: 0;
          padding: 0;
          list-style: none;
        }

        header.header > ul.links > li.link {
          background: var(--gray-background);
          display: flex;
          align-items: center;
          gap: 8px;
          width: 36px;
          height: 36px;
          max-width: 36px;
          max-height: 36px;
          padding: 0;
          border-radius: 50%;
          display: flex;
          justify-content: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          color: var(--text-color);
          position: relative;
        }

        header.header > ul.links > li.link:hover {
          background: var(--tab-background);
          color: var(--accent-color);
        }

        header.header > ul.links > li.link.profile > div.image {
          width: 36px;
          height: 36px;
          max-height: 36px;
          max-width: 36px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: hidden;
        }

        header.header > ul.links > li.link.profile > div.image > img {
          width: 32px;
          height: 32px;
          max-height: 32px;
          max-width: 32px;
          border-radius: 50%;
          object-fit: cover;
        }

        header.header > ul.links > li.link > span.text {
          display: none;
          position: absolute;
          bottom: -38px;
          left: 50%;
          transform: translateX(-50%);
          background: var(--background);
          color: var(--text-color);
          padding: 6px 10px;
          border-radius: 12px;
          font-family: var(--font-text), sans-serif;
          font-size: 0.85rem;
          font-weight: 500;
          white-space: nowrap;
          z-index: 1000;
          border: var(--border);
          box-shadow: var(--card-box-shadow);
          pointer-events: none;
        }

        header.header > ul.links > li.link > span.text::before {
          content: '';
          position: absolute;
          top: -2px;
          left: 50%;
          transform: translateX(-50%);
          width: 10px;
          height: 10px;
          rotate: 45deg;
          background: var(--background);
          border-top: var(--border);
          border-left: var(--border);
        }

        header.header > ul.links > li.link:hover > span.text {
          display: block;
          animation: fadeInTooltip 0.2s ease-in-out;
        }

        @keyframes fadeInTooltip {
          from {
            opacity: 0;
            transform: translateX(-50%) translateY(5px);
          }
          to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
          }
        }

        header.header > ul.links > li.link.updates {
          position: relative;
        }

        /* Animate the updates notification circle */
        header.header > ul.links > li.link.updates svg path#animate {
          animation: updatesPulse 2s ease-in-out infinite;
          transform-origin: center;
          z-index: 1;
          color: var(--alt-color);
        }

        @keyframes updatesPulse {
          0%, 100% {
            transform: scale(0.9);
            opacity: 1;
          }
          50% {
            transform: scale(1.05);
            opacity: 0.7;
          }
        }

        /* Alternative breathing animation for the updates icon */
        header.header > ul.links > li.link.updates:hover svg path#animate {
          animation: updatesBreath 1.8s ease-in-out infinite;
          z-index: 1;
          background: var(--error-background);
        }

        @keyframes updatesBreath {
          0%, 100% {
            transform: scale(0.8);
            opacity: 0.8;
          }
          50% {
            transform: scale(1);
            opacity: 1;
          }
        }

        header.header > ul.links > li.link > svg {
          width: 24px;
          height: 24px;
          color: inherit;
        }

        header.header > ul.links > li.link.more > span.icon {
          display: flex;
          gap: 5px;
          align-items: center;
          justify-content: center;
        }

        header.header > ul.links > li.link.more > span.icon > span.sp {
          display: inline-block;
          width: 6px;
          height: 6px;
          background: var(--text-color);
          color: inherit;
          border-radius: 50%;
        }

      </style>
    `;
  }
}