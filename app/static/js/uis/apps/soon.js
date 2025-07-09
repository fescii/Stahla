export default class SoonPage extends HTMLElement {
  constructor() {
    super();
    this.app = window.app;
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.render();
  }

  connectedCallback() {
    // Initial render when component is added to DOM
  }

  disconnectedCallback() {
    // Remove event listeners when element is removed
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody() {
    return /* html */ `
      <div class="container">
      <header class="header">
        <div class="header-content">
        <div class="badge-container">
          <div class="badge">Finalizing</div>
          <div class="status-indicator">
          <span class="pulse"></span>
          <span class="status-text">Testing stage</span>
          </div>
        </div>
        <h1>Finalizing</h1>
        <p class="subtitle">
          We are in the final stages of development. We'll be updating this page in few hours with more information about bland AI call simulation.
        </p>
        <div class="header-actions">
          <a class="action-button primary" href="mailto:isfescii@gmail.com?subject=Request%20Implementation">Request Implementation</a>
          <a class="action-button secondary" href="/docs">View Documentation</a>
        </div>
        </div>
        <div class="graphic-container">
        <div class="animated-graphic">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="graphic-icon">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
        </div>
        </div>
      </header>
      </div>
    `;
  }

  getStyles() {
    return /* css */ `
      <style>
        :host {
          display: block;
          font-family: var(--font-text, 'Inter', sans-serif);
          color: var(--text-color);
          background-color: var(--background);
          -webkit-font-smoothing: antialiased;
          -moz-osx-font-smoothing: grayscale;
        }
        
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }

        *:focus {
          outline: none;
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
        
        .container {
          width: 100%;
          margin: 0;
          min-height: 100%;
          padding: 20px 15px;
          display: flex;
        }
        
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px;
          margin-bottom: 50px;
          border-radius: 20px;
          position: relative;
          overflow: hidden;
        }
        
        .graphic-container {
          flex: 0 0 200px;
          display: flex;
          justify-content: center;
          align-items: center;
        }
        
        .animated-graphic {
          width: 180px;
          height: 180px;
          background: radial-gradient(circle, var(--tab-background) 30%, transparent 70%);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          position: relative;
          animation: pulse 8s infinite ease-in-out;
        }
        
        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
            opacity: 0.8;
          }
          50% {
            transform: scale(1.1);
            opacity: 1;
          }
        }
        
        .graphic-icon {
          width: 80px;
          height: 80px;
          color: var(--accent-color);
          animation: rotate 20s infinite linear;
        }
        
        @keyframes rotate {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
        
        .badge-container {
          display: flex;
          align-items: center;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .badge {
          display: inline-block;
          padding: 8px 12px;
          background: var(--tab-background);
          color: var(--white-color);
          font-weight: 600;
          font-size: 0.8rem;
          border-radius: 2rem;
        }
        
        .status-indicator {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          width: max-content;
          padding: 8px 12px;
          background: var(--gray-background);
          border-radius: 2rem;
          font-size: 0.8rem;
          font-weight: 600;
        }
        
        .pulse {
          width: 10px;
          height: 10px;
          background-color: var(--alt-color);
          border-radius: 50%;
          display: inline-block;
          position: relative;
        }
        
        .pulse::after {
          content: '';
          position: absolute;
          width: 100%;
          height: 100%;
          top: 0;
          left: 0;
          background-color: var(--alt-color);
          border-radius: 50%;
          animation: pulse-ring 1.5s infinite;
        }
        
        @keyframes pulse-ring {
          0% {
            transform: scale(0.8);
            opacity: 0.8;
          }
          70% {
            transform: scale(2);
            opacity: 0;
          }
          100% {
            transform: scale(2.5);
            opacity: 0;
          }
        }
        
        .status-text {
          color: var(--title-color);
        }
        
        .header h1 {
          font-size: 3rem;
          margin: 0 0 1rem;
          color: var(--title-color);
          font-weight: 700;
          line-height: 1.2;
        }
        
        .subtitle {
          font-size: 1.125rem;
          color: var(--gray-color);
          margin: 0 0 1.5rem;
          line-height: 1.6;
        }
        
        .header-actions {
          display: flex;
          gap: 1rem;
          margin-top: 2rem;
        }
        
        .action-button {
          padding: 9px 20px;
          border-radius: 12px;
          font-weight: 600;
          font-size: 0.95rem;
          text-decoration: none;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          border: none;
        }
        
        .action-button.primary {
          background: var(--accent-linear);
          color: var(--white-color);
        }
        
        .action-button.secondary {
          background: var(--background);
          color: var(--accent-color);
          border: var(--action-border);
        }
        
        .action-button:hover {
          transform: translateY(-2px);
        }
        
        .section-title {
          font-size: 1.75rem;
          margin: 0 0 2rem;
          color: var(--title-color);
          text-align: center;
          position: relative;
          padding-bottom: 1rem;
        }
        
        .section-title::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 50%;
          transform: translateX(-50%);
          width: 60px;
          height: 3px;
          background: var(--accent-linear);
          border-radius: 3px;
        }
      </style>
    `;
  }
}
