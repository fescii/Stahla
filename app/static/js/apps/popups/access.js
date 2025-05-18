export default class AccessPopup extends HTMLElement {
  constructor() {
    super();
    this.app = window.app;
    this.api = this.app.api;
    this.shadowObj = this.attachShadow({mode: 'open'});
    this.url = this.getAttribute('api');
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    const form = this.shadowObj.querySelector('form');
    this.submitForm(form);
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

  submitForm = async form => {
    form.addEventListener('submit', this.handleSubmit.bind(this));
  }

  handleSubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    const actions = form.querySelector('.actions');
    const data = this.getFormData(form);

    if (!this.validateFormData(data, actions)) return;

    const button = form.querySelector('.action.next');
    button.innerHTML = this.getButtonLoader();

    try {
      const result = await this.api.post(this.url, { content: 'json', body: data });
      this.handleResponse(result, actions, button);
    } catch (error) {
      console.error('url:', this.url);
      console.error('Error:', error);
      this.showError(actions, 'An error occurred, please try again', button);
    }

    this.removeServerStatus(form);
  }

  getFormData = form => {
    const formData = new FormData(form);
    return {
      password: formData.get('current-password').trim(),
      username: formData.get('email').trim()
    };
  }

  validateFormData = (data, actions) => {
    const username = data.username;
    const password = data.password;
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const emailValid = emailRegex.test(username);
    const passwordValid = password.length >= 4;

    if (!emailValid) {
      this.showError(actions, 'Username must be a valid email address.');
      return false;
    }

    if (!passwordValid) {
      this.showError(actions, 'Password is required and must be at least 4 characters long.');
      return false;
    }

    return true;
  }

  handleResponse(result, actions, button) {
    if (result.success) {
      this.showSuccess(actions, result.data);
    } else {
      this.showError(actions, result.error_message);
    }
    button.innerHTML = /* HTML */ '<span class="text">Log In</span>';
  }

  showError(actions, message, button = null) {
    actions.insertAdjacentHTML('beforebegin', this.getServerSuccessMsg(false, message));
    if (button) button.innerHTML = /* HTML */ '<span class="text">Log In</span>';
  }

  showSuccess(actions, data) {
    actions.insertAdjacentHTML('beforebegin', this.getServerSuccessMsg(true, 'Login successful!'));

    // SET access token to cookie named: x-access-token: expires in 1 day
    const token = data.access_token;
    const expires = new Date(Date.now() + 86400000).toUTCString(); // 1 day
    document.cookie = `x-access-token=${token}; expires=${expires}; path=/`;

    // Redirect to dashboard
    this.app.navigate(window.location.href);
  }

  removeServerStatus(form) {
    setTimeout(() => {
      const serverStatus = form.querySelector('.server-status');
      if (serverStatus) {
        serverStatus.remove();
      }
    }, 5000);
  }

  getServerSuccessMsg(success, text) {
    return success ? `<p class="server-status success">${text}</p>` : `<p class="server-status error">${text}</p>`;
  }

  getButtonLoader() {
    return /* html */`
      <span id="btn-loader">
				<span class="loader"></span>
			</span>
    `
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
				  <h2 class="consent">SDR AI & Pricing Platform</h2>
        </div>
        <p>This is dashboard for exploring and monitoring the SDR AI & Pricing Platform. <br/>
        You can access the platform by logging in with your email and password.</p>
        <span class="items">${trimmedItems}</span>
        ${this.getForm()}
			</div>
    `;
  }

  getForm = () => {
    return /* html */`
      <form class="fields email" id="email-form">
        <div class="field email">
          <div class="input-group email">
            <label for="email" class="center">Your email</label>
            <input type="email" name="email" id="email" placeholder="e.g john@example.com" />
            <span class="status">Email is required</span>
          </div>
          <div class="input-group current-password">
            <label for="current-password" class="center">Current password</label>
            <input type="password" name="current-password" id="current-password" placeholder="Enter your current password" />
            <span class="status">Current password is required</span>
          </div>
        </div>
        <div class="actions">
          <button type="submit" class="action next">
            <span class="text">Log In</span>
          </button>
        </div>
      </form>
    `;
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
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }

        #content {
          z-index: 1;
          border: var(--border);
          background: var(--background);
          padding: 25px;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 0;
          width: 660px;
          max-height: 90%;
          height: max-content;
          border-radius: 20px;
          position: relative;
        }

        p.server-status {
          margin: 0;
          width: 100%;
          text-align: start;
          font-family: var(--font-read), sans-serif;
          color: var(--error-color);
          font-weight: 500;
          line-height: 1.4;
          font-size: 1.18rem;
        }

        p.server-status.success {
          color: transparent;
          background: var(--accent-linear);
          background-clip: text;
          -webkit-background-clip: text;
        }

        p.server-status.error {
          color: var(--error-color);
        }

        @keyframes l38 {
          100% {
            background-position: 100% 0, 100% 100%, 0 100%, 0 0
          }
        }

        #btn-loader {
          position: absolute;
          top: 0;
          left: 0;
          bottom: 0;
          right: 0;
          z-index: 5;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: inherit;
        }

        #btn-loader > .loader-alt {
          width: 20px;
          aspect-ratio: 1;
          --_g: no-repeat radial-gradient(farthest-side, #18A565 94%, #0000);
          --_g1: no-repeat radial-gradient(farthest-side, #21D029 94%, #0000);
          --_g2: no-repeat radial-gradient(farthest-side, #df791a 94%, #0000);
          --_g3: no-repeat radial-gradient(farthest-side, #f09c4e 94%, #0000);
          background:    var(--_g) 0 0,    var(--_g1) 100% 0,    var(--_g2) 100% 100%,    var(--_g3) 0 100%;
          background-size: 30% 30%;
          animation: l38 .9s infinite ease-in-out;
          -webkit-animation: l38 .9s infinite ease-in-out;
        }

        #btn-loader > .loader {
          width: 20px;
          aspect-ratio: 1;
          --_g: no-repeat radial-gradient(farthest-side, #ffffff 94%, #0000);
          --_g1: no-repeat radial-gradient(farthest-side, #ffffff 94%, #0000);
          --_g2: no-repeat radial-gradient(farthest-side, #df791a 94%, #0000);
          --_g3: no-repeat radial-gradient(farthest-side, #f09c4e 94%, #0000);
          background:    var(--_g) 0 0,    var(--_g1) 100% 0,    var(--_g2) 100% 100%,    var(--_g3) 0 100%;
          background-size: 30% 30%;
          animation: l38 .9s infinite ease-in-out;
          -webkit-animation: l38 .9s infinite ease-in-out;
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
          font-size: 1.65rem;
          font-weight: 700;
          margin: 0;
          padding: 0;
          border-radius: 12px;
          font-family: var(--font-main), sans-serif;
          color: transparent;
          background: var(--second-linear);
          background-clip: text;
          -webkit-background-clip: text;
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

        form.fields {
          margin: 0;
          width: 100%;
          display: flex;
          flex-flow: column;
          justify-content: center;
          align-items: center;
          gap: 20px;
        }

        form.fields > .field {
          width: 100%;
          display: flex;
          flex-flow: column;
          justify-content: center;
          align-items: start;
          gap: 20px;
        }

        form.fields.center > .field {
          align-items: center;
        }

        form.fields .field .input-group {
          width: 100%;
          display: flex;
          flex-flow: column;
          justify-content: center;
          align-items: start;
          color: var(--text-color);
          gap: 5px;
          position: relative;
          transition: border-color 0.3s ease-in-out;
        }

        form.fields .field.bio .input-group {
          width: 100%;
        }

        form.fields .field.bio .input-group.code,
        form.fields .field.bio .input-group.email {
          grid-column: 1/3;
          width: 100%;
        }

        form.fields .field .input-group > svg {
          position: absolute;
          right: 10px;
          top: 38px;
          width: 20px;
          height: 20px;
        }

        form.fields .field .input-group > svg {
          display: none;
        }

        form.fields .field .input-group.success > svg {
          display: inline-block;
        }

        form.fields .field .input-group.failed > svg {
          display: inline-block;
        }

        form.fields .field .input-group.success > svg {
          color: var(--accent-color);
        }

        form.fields .field .input-group.failed > svg {
          color: var(--error-color);
        }

        form.fields label {
          padding: 0 0 5px 0;
          color: var(--text-color);
        }

        form.fields .field.bio label {
          padding: 0 0 0 5px;
        }

        form.fields label {
          color: var(--label-color);
          font-size: 1.1rem;
          font-family: var(--font-main), sans-serif;
          transition: all 0.3s ease-in-out;
          pointer-events: none;
        }

        form.fields .field input {
          border: var(--input-border);
          background: var(--background);
          font-size: 1rem;
          width: 100%;
          height: 40px;
          outline: none;
          padding: 10px 12px;
          border-radius: 12px;
          color: var(--text-color);
          -webkit-border-radius: 12px;
          -moz-border-radius: 12px;
          -ms-border-radius: 12px;
          -o-border-radius: 12px;
        }

        form.fields .field input {
          border: var(--input-border);
          background-color: var(--background) !important;
          font-size: 1rem;
          width: 100%;
          height: 40px;
          outline: none;
          padding: 10px 12px;
          border-radius: 12px;
          color: var(--text-color);
        }
        
        form.fields .field input:-webkit-autofill,
        form.fields .field input:-webkit-autofill:hover, 
        form.fields .field input:-webkit-autofill:focus {
          -webkit-box-shadow: 0 0 0px 1000px var(--background) inset;
          -webkit-text-fill-color: var(--text-color) !important;
          transition: background-color 5000s ease-in-out 0s;
          color: var(--text-color) !important;
        }
        
        form.fields .field input:autofill {
          filter: none;
          color: var(--text-color) !important;
        }

        form.fields .field input:focus {
          border: var(--input-border-focus);
        }

        form.fields .field span.wrapper {
          display: flex;
          align-items: center;
          align-items: center;
          gap: 0;
          width: 100%;
        }

        form.fields .field .input-group.success > span.wrapper > input,
        form.fields .field .input-group.success > span.wrapper > input:focus,
        form.fields .field .input-group.success input,
        form.fields .field .input-group.success input:focus {
          border: var(--input-border-focus);
        }

        form.fields .field .input-group.failed > span.wrapper > input,
        form.fields .field .input-group.failed > span.wrapper > input:focus,
        form.fields .field .input-group.failed input,
        form.fields .field .input-group.failed input:focus {
          border: var(--input-border-error);
        }

        form.fields .field .input-group.success span.wrapper > input,
        form.fields .field .input-group.success input {
          color: var(--accent-color);
        }

        form.fields .field .input-group.failed span.wrapper > input,
        form.fields .field .input-group.failed input {
          color: var(--error-color);
        }

        form.fields label.focused {
          top: -10px;
          font-size: 0.9rem;
          background-color: var(--label-focus-background);
          padding: 0 5px;
        }

        form.fields .field span.status {
          color: var(--error-color);
          font-size: 0.95rem;
          display: none;
          padding: 0 0 0 5px;
        }

        form.fields .field .input-group.failed span.status {
          color: var(--error-color);
          font-size: 0.8rem;
          display: inline-block;
        }

        form.fields .field .input-group.success span.status {
          color: var(--accent-color);
          font-size: 0.8rem;
          display: inline-block;
        }

        form.fields .field .input-group.success span.status {
          display: none;
        }

        form.fields .actions {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          margin: 15px 0 0 2px;
        }

        form.fields .actions > .action {
          border: none;
          background: var(--accent-linear);
          font-family: var(--font-main), sans-serif;
          text-decoration: none;
          color: var(--white-color);
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          display: flex;
          flex-flow: row;
          align-items: center;
          text-transform: capitalize;
          justify-content: center;
          padding: 12px 15px;
          min-width: 100%;
          height: 40px;
          width: 100%;
          position: relative;
          border-radius: 12px;
          -webkit-border-radius: 12px;
          -moz-border-radius: 12px;
        }

        form.fields .actions > .action.prev svg path {
          fill: var(--text-color);
        }

        form.fields .actions > .action.next {
          color: var(--white-color);
          background: var(--accent-linear);
        }

        form.fields .actions > .action.next svg path {
          fill: var(--white-color);
        }

        form.fields .actions > .action.disabled {
          pointer-events: none;
        }
      </style>
    `;
  }
}