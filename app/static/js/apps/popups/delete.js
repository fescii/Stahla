export default class DeletePopup extends HTMLElement {
  constructor() {
    super();
    this.url = this.getAttribute('url');
    this.shadowObj = this.attachShadow({mode: 'open'});
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.disableScroll();
    const btns = this.shadowObj.querySelectorAll('.cancel-btn');
    if (btns) this.closePopup(btns);
  }

  disconnectedCallback() {
    this.enableScroll()
  }

  disableScroll() {
    // Get the current page scroll position
    let scrollTop = window.scrollY || document.documentElement.scrollTop;
    let scrollLeft = window.scrollX || document.documentElement.scrollLeft;
    document.body.classList.add("stop-scrolling");

    // if any scroll is attempted, set this to the previous value
    window.onscroll = function() {
      window.scrollTo(scrollLeft, scrollTop);
    };
  }

  enableScroll() {
    document.body.classList.remove("stop-scrolling");
    window.onscroll = function() {};
  }

  closePopup = (btns) => {
    btns.forEach(btn => {
      btn.addEventListener('click', e => {
        e.preventDefault();
        this.remove();
      });
    })
  }

  getTemplate() {
    // Show HTML Here
    return `
      <div class="overlay"></div>
      <section id="content" class="content">
        ${this.getWelcome()}
      </section>
    ${this.getStyles()}`
  }

  getWelcome() {
    const items = this.innerHTML;
    // Trim items to 200 characters
    const trimmedItems = items.length > 120 ? items.substring(0, 120) + '...' : items;
    return /*html*/`
      <div class="welcome">
        <div class="head">
				  <h2 class="consent">You are about to delete;</h2>
        </div>
        <p>The following items will be deleted from your SDR AI Platform.<br/> This action cannot be undone.</p>
        <span class="items">${trimmedItems}</span>
        <div class="actions">
          <button class="action cancel-btn">Cancel</button>
          <button class="action">Continue</button>
        </div>
			</div>
    `
  }

  getStyles() {
    return /*css*/`
      <style>
        * {
          box-sizing: border-box !important;
        }

        :host{
          border: none;
          padding: 0;
          justify-self: end;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 10px;
          z-index: 100;
          width: 100%;
          min-width: 100vw;
          position: fixed;
          right: 0;
          top: 0;
          bottom: 0;
          left: 0;
        }

        div.overlay {
          position: absolute;
          top: 0;
          right: 0;
          bottom: 0;
          left: 0;
          height: 100%;
          width: 100%;
          background: var(--modal-background);
          backdrop-filter: blur(3px);
          -webkit-backdrop-filter: blur(3px);
        }

        #content {
          z-index: 1;
          border: var(--border);
          background: var(--background);
          padding: 20px 10px 20px;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 0;
          width: 550px;
          max-height: 90%;
          height: max-content;
          border-radius: 20px;
          position: relative;
        }
  
        .welcome {
          width: 98%;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 0;
        }

        .welcome > .head {
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          width: 100%;
          gap: 0;
          padding: 0 0 10px;
        }

        .welcome > .head > h2.consent {
          width: 100%;
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          border-radius: 12px;
          font-family: var(--font-main), sans-serif;
          color: var(--text-color);
          font-weight: 500;
          position: relative;
        }

        .welcome  p {
          margin: 10px 0 0;
          width: 100%;
          font-family: var(--font-main), sans-serif;
          color: var(--text-color);
          line-height: 1.4;
          font-size: 1rem;
        }

        .welcome span.items {
          display: flex;
          width: 100%;
          padding: 0;
          margin: 15px 0;
          font-family: var(--font-read), sans-serif;
          font-size: 0.9rem;
          font-weight: 400;
          border-radius: 5px;
          color: var(--gray-color);
        }

        .welcome > .actions {
          display: flex;
          font-family: var(--font-main), sans-serif;
          width: 100%;
          flex-flow: row;
          align-items: center;
          justify-content: end;
          gap: 35px;
          margin: 20px 0 0;
        }
        
        .welcome > .actions > .action {
          border: none;
          background: var(--error-background);
          color: var(--error-color);
          font-family: var(--font-main), sans-serif;
          text-decoration: none;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          flex-flow: row;
          align-items: center;
          text-transform: capitalize;
          justify-content: center;
          padding: 12px 20px;
          min-width: 100px;
          width: 150px;
          position: relative;
          border-radius: 15px;
          -webkit-border-radius: 15px;
          -moz-border-radius: 15px;
        }

        .welcome > .actions > .action.cancel-btn {
          border: none;
          /* background: none;
          background-color: none; */
          background: var(--gray-background);
          color: var(--text-color);
          padding: 12px 20px;
        }
      </style>
    `;
  }
}