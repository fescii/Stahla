export default class SoonPage extends HTMLElement {
  constructor() {
    super();
    this.shadowObj = this.attachShadow({ mode: 'open' });
    this.render();
  }

  connectedCallback() {
    // Initial render when component is added to DOM
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
          <h1>Coming Soon</h1>
          <p class="subtitle">This feature isn't displayed in the UI yet but is fully implemented on the Platform service backend.</p>
        </header>
        <section class="content">
          <h2>Feature Overview</h2>
          <p>Our backend for this feature is ready and available for immediate use.</p>
          <p>If you'd like to have this integrated into your application UI, please let us know—custom implementation is available upon request.</p>
        </section>
        <footer class="footer">
          <p>For inquiries or to request integration, contact us at <a href="mailto:isfescii@gmail.com">isfescii@gmail.com</a>.</p>
        </footer>
      </div>
    `;
  }

  getStyles() {
    return /* css */ `
      <style>
        :host {
          display: block;
          font-family: var(--font-text);
          color: var(--text-color);
          background-color: var(--background);
        }
        .container {
          max-width: 800px;
          margin: 2rem auto;
          padding: 2rem;
          background: var(--card-bg);
          border-radius: 1rem;
          box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
        }
        .header h1 {
          font-size: 2.5rem;
          margin: 0 0 0.5rem;
          color: var(--title-color);
        }
        .subtitle {
          font-size: 1.125rem;
          color: var(--gray-color);
          margin: 0 0 1.5rem;
        }
        .content h2 {
          font-size: 1.5rem;
          margin: 1.5rem 0 0.75rem;
          color: var(--title-color);
        }
        .content p {
          font-size: 1rem;
          line-height: 1.6;
          margin: 0 0 1rem;
        }
        .footer {
          margin-top: 2rem;
          border-top: var(--border);
          padding-top: 1rem;
        }
        .footer p {
          font-size: 0.875rem;
          color: var(--gray-color);
          margin: 0;
        }
        .footer a {
          color: var(--accent-color);
          text-decoration: none;
          font-weight: 600;
        }
        .footer a:hover {
          text-decoration: underline;
        }
      </style>
    `;
  }
}
