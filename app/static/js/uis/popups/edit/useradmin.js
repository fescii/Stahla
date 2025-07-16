export default class EditUserAdminPopup extends HTMLElement {
  constructor() {
    super();
    this.app = window.app;
    this.api = this.app.api;
    this.shadowObj = this.attachShadow({ mode: 'open' });

    // Get user data from individual attributes
    this.user = {
      id: this.getAttribute('user-id') || '',
      name: this.getAttribute('user-name') || '',
      email: this.getAttribute('user-email') || '',
      bio: this.getAttribute('user-bio') || '',
      role: this.getAttribute('user-role') || 'member',
      is_active: this.getAttribute('user-active') === 'true',
      picture: this.getAttribute('user-picture') || null
    };

    // Clean up empty string values to null for picture
    if (this.user.picture === '') {
      this.user.picture = null;
    }

    this._loading = false;
    this._error = false;
    this._errorMessage = null;
    this._success = false;
    this.render();
  }

  render() {
    this.shadowObj.innerHTML = this.getTemplate();
  }

  connectedCallback() {
    this.disableScroll();
    this._setupEventListeners();
  }

  disconnectedCallback() {
    this.enableScroll();
  }

  disableScroll() {
    let scrollTop = window.scrollY || document.documentElement.scrollTop;
    let scrollLeft = window.scrollX || document.documentElement.scrollLeft;
    document.body.classList.add("stop-scrolling");
    window.onscroll = function () {
      window.scrollTo(scrollLeft, scrollTop);
    };
  }

  enableScroll() {
    document.body.classList.remove("stop-scrolling");
    window.onscroll = function () { };
  }

  _setupEventListeners() {
    // Close buttons
    const closeButtons = this.shadowObj.querySelectorAll('.close-btn, .cancel-btn');
    closeButtons.forEach(btn => {
      btn.addEventListener('click', () => this.remove());
    });

    // Overlay click to close
    const overlay = this.shadowObj.querySelector('.overlay');
    if (overlay) {
      overlay.addEventListener('click', () => this.remove());
    }

    // Form submission
    const form = this.shadowObj.querySelector('#edit-user-admin-form');
    if (form) {
      form.addEventListener('submit', this._handleSubmit.bind(this));
    }
  }

  _handleSubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const role = formData.get('role');
    const is_active = formData.get('is_active') === 'on';

    // Admin protection: prevent demoting admin if they're the only one
    if (this.user.role === 'admin' && role !== 'admin') {
      try {
        // Call API to validate admin demotion
        const validationResult = await this.api.post('/auth/users/validate-admin-demotion', {
          content: 'json',
          body: { user_id: this.user.id }
        });

        if (!validationResult.success || !validationResult.data.can_demote) {
          this._showError(validationResult.message || 'Cannot demote the last active admin. At least one admin must remain to maintain system access.');
          return;
        }
      } catch (error) {
        this._showError('Failed to validate admin demotion. Please try again.');
        return;
      }
    }

    this._updateSubmitButton(true);

    // Clear any existing errors
    const existingError = this.shadowObj.querySelector('.error-alert');
    if (existingError) {
      existingError.remove();
    }

    try {
      const result = await this.api.patch(`/auth/users/${this.user.id}/admin`, {
        content: 'json',
        body: { role, is_active }
      });

      if (!result.success) {
        throw new Error(result.message || 'Failed to update user');
      }

      this._updateSubmitButton(false);
      this._showSuccess();

      // Close popup after delay and refresh user data
      setTimeout(() => {
        if (this.app && typeof this.app.refreshUsersList === 'function') {
          this.app.refreshUsersList();
        }
        this.remove();
      }, 1500);

    } catch (error) {
      this._updateSubmitButton(false);
      this._showError(error.message || 'An error occurred while updating the user');
    }
  };

  _updateSubmitButton(loading = false) {
    const submitBtn = this.shadowObj.querySelector('.action.next');
    if (submitBtn) {
      submitBtn.disabled = loading;
      submitBtn.innerHTML = loading
        ? this._getLoadingSpinner() + 'Updating...'
        : 'Update User';
    }
  }

  _showSuccess() {
    const form = this.shadowObj.querySelector('#edit-user-admin-form');
    if (form) {
      const successHTML = `
        <div class="success-alert">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"></polyline>
          </svg>
          <span>User updated successfully!</span>
        </div>
      `;
      form.insertAdjacentHTML('afterbegin', successHTML);
    }
  }

  _showError(message) {
    // Update only the error display area
    const existingError = this.shadowObj.querySelector('.error-alert');
    if (existingError) {
      existingError.remove();
    }

    const form = this.shadowObj.querySelector('#edit-user-admin-form');
    if (form) {
      const errorHTML = `
        <div class="error-alert">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          <span>${message}</span>
        </div>
      `;
      form.insertAdjacentHTML('afterbegin', errorHTML);

      // Auto-remove error after 5 seconds
      setTimeout(() => {
        const errorElement = this.shadowObj.querySelector('.error-alert');
        if (errorElement) {
          errorElement.remove();
        }
      }, 5000);
    }
  }

  getTemplate() {
    return `
      <div class="overlay"></div>
      <section id="content" class="content">
        ${this.getEditUserContent()}
      </section>
      ${this.getStyles()}
    `;
  }

  getEditUserContent() {
    if (this._success) {
      return `
        <div class="welcome">
          <div class="success-container">
            <svg class="success-icon" xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9 12l2 2 4-4"></path>
            </svg>
            <h2>User Updated Successfully</h2>
            <p>The user's role and status have been updated.</p>
          </div>
        </div>
      `;
    }

    return `
      <div class="welcome">
        <div class="head">
          <h2 class="consent">Edit User Access</h2>
          <button class="close-btn" type="button">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        ${this._error ? this._getErrorHTML() : ''}
        
        <div class="user-info">
          <div class="user-avatar">
            ${this.user.picture
        ? `<img src="${this.user.picture}" alt="Profile picture" class="profile-image">`
        : this._getInitialsAvatar(this.user.name || this.user.email)
      }
          </div>
          <div class="user-details">
            <h3>${this.user.name || this.user.email || 'Unknown User'}</h3>
            <p class="user-email">${this.user.email || 'No email'}</p>
            ${!this.user.name && !this.user.email ? `<p class="debug-info">Debug: User object keys: ${Object.keys(this.user).join(', ')}</p>` : ''}
          </div>
        </div>

        <form id="edit-user-admin-form" class="fields">
          <div class="field">
            <div class="input-group">
              <label for="role">User Role</label>
              <select id="role" name="role" required>
                <option value="member" ${this.user.role === 'member' ? 'selected' : ''}>Member</option>
                <option value="dev" ${this.user.role === 'dev' ? 'selected' : ''}>Developer</option>
                <option value="admin" ${this.user.role === 'admin' ? 'selected' : ''}>Administrator</option>
              </select>
            </div>
          </div>
          
          <div class="field switch-field">
            <div class="switch-container">
              <label for="is_active" class="switch-label">
                <div class="switch-text">
                  <span class="switch-title">Account Status</span>
                  <span class="switch-description">User can login and access the platform</span>
                </div>
                <label class="switch">
                  <input type="checkbox" id="is_active" name="is_active" ${this.user.is_active ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
              </label>
            </div>
          </div>
          
          <div class="actions">
            <button type="button" class="action cancel-btn">Cancel</button>
            <button type="submit" class="action next" ${this._loading ? 'disabled' : ''}>
              ${this._loading ? this._getLoadingSpinner() + 'Updating...' : 'Update User'}
            </button>
          </div>
        </form>
      </div>
    `;
  }

  _getErrorHTML() {
    return `
      <div class="error-alert">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>${this._errorMessage}</span>
      </div>
    `;
  }

  _getInitialsAvatar(text) {
    if (!text) return '';

    let initials = '';
    if (text.includes('@')) {
      const parts = text.split('@');
      initials = parts[0][0].toUpperCase();
      if (parts[1]) initials += parts[1][0].toUpperCase();
    } else {
      const nameParts = text.split(' ');
      initials = nameParts[0][0].toUpperCase();
      if (nameParts.length > 1) {
        initials += nameParts[nameParts.length - 1][0].toUpperCase();
      }
    }

    const hue = this._getHashCode(text) % 360;
    const backgroundColor = `hsl(${hue}, 70%, 60%)`;

    return `
      <div class="avatar-circle" style="background-color: ${backgroundColor}">
        <span class="avatar-initials">${initials}</span>
      </div>
    `;
  }

  _getHashCode(str) {
    let hash = 0;
    if (str.length === 0) return hash;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return Math.abs(hash);
  }

  _getLoadingSpinner() {
    return `
      <svg class="spinner" viewBox="0 0 50 50">
        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
      </svg>
    `;
  }

  getStyles() {
    return `
      <style>
        * {
          box-sizing: border-box !important;
        }

        :host {
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
          padding: 20px;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 0;
          width: 700px;
          max-height: 90%;
          height: max-content;
          border-radius: 20px;
          position: relative;
        }

        .welcome {
          width: 100%;
          display: flex;
          flex-flow: column;
          align-items: center;
          justify-content: center;
          gap: 0;
        }

        .welcome > .head {
          display: flex;
          flex-flow: row;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          gap: 0;
          padding: 0 0 20px;
        }

        .welcome > .head > h2.consent {
          font-size: 1.5rem;
          font-weight: 600;
          margin: 0;
          padding: 0;
          font-family: var(--font-main), sans-serif;
          color: var(--title-color);
        }

        .close-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 8px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: var(--gray-color);
          transition: all 0.2s ease;
        }

        .close-btn:hover {
          background: var(--hover-background);
          color: var(--text-color);
        }

        .error-alert {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          margin-bottom: 20px;
          border-radius: 12px;
          background: rgba(236, 75, 25, 0.1);
          border: 1px solid rgba(236, 75, 25, 0.2);
          color: var(--error-color);
          width: 100%;
        }

        .success-alert {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          margin-bottom: 20px;
          border-radius: 12px;
          background: rgba(34, 197, 94, 0.1);
          border: 1px solid rgba(34, 197, 94, 0.2);
          color: var(--success-color);
          width: 100%;
        }

        .user-info {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 24px;
          width: 100%;
          padding: 16px;
          border-radius: 12px;
          background: var(--create-background);
          border: 1px solid var(--border);
        }

        .user-avatar {
          width: 60px;
          height: 60px;
          flex-shrink: 0;
        }

        .profile-image {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          object-fit: cover;
          border: 2px solid var(--border);
        }

        .avatar-circle {
          width: 60px;
          height: 60px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 600;
          font-size: 1.5rem;
        }

        .user-details {
          flex: 1;
        }

        .user-details h3 {
          margin: 0 0 4px 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--title-color);
        }

        .user-email {
          margin: 0;
          font-size: 0.9rem;
          color: var(--gray-color);
        }

        .success-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          text-align: center;
          padding: 40px 20px;
        }

        .success-icon {
          color: var(--success-color);
        }

        .success-container h2 {
          margin: 0;
          font-size: 1.4rem;
          color: var(--title-color);
        }

        .success-container p {
          margin: 0;
          color: var(--text-color);
          opacity: 0.8;
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
          gap: 0;
        }

        form.fields .field .input-group {
          width: 100%;
          display: flex;
          flex-flow: column;
          justify-content: center;
          align-items: start;
          color: var(--text-color);
          gap: 8px;
          position: relative;
          transition: border-color 0.3s ease-in-out;
        }

        form.fields label {
          color: var(--label-color);
          font-size: 1rem;
          font-family: var(--font-main), sans-serif;
          font-weight: 500;
        }

        form.fields .field select {
          border: var(--input-border);
          background: var(--background);
          font-size: 1rem;
          width: 100%;
          outline: none;
          padding: 12px 16px;
          border-radius: 12px;
          color: var(--text-color);
          transition: all 0.2s ease-in-out;
          font-family: var(--font-main), sans-serif;
          cursor: pointer;
        }

        form.fields .field select:focus {
          border: var(--input-border-focus);
          box-shadow: 0 0 0 3px rgba(0, 96, 223, 0.1);
          transform: translateY(-1px);
        }

        .switch-field {
          align-items: stretch !important;
        }

        .switch-container {
          width: 100%;
        }

        .switch-label {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          cursor: pointer;
          padding: 16px;
          border-radius: 12px;
          border: var(--input-border);
          background: var(--background);
          transition: all 0.2s ease;
        }

        .switch-label:hover {
          border-color: var(--accent-color);
          background: var(--create-background);
        }

        .switch-text {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .switch-title {
          font-weight: 500;
          color: var(--title-color);
          font-size: 1rem;
        }

        .switch-description {
          font-size: 0.85rem;
          color: var(--gray-color);
        }

        .switch {
          position: relative;
          display: inline-block;
          width: 50px;
          height: 24px;
        }

        .switch input {
          opacity: 0;
          width: 0;
          height: 0;
        }

        .slider {
          position: absolute;
          cursor: pointer;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: var(--gray-background);
          transition: 0.3s;
          border-radius: 24px;
        }

        .slider:before {
          position: absolute;
          content: "";
          height: 18px;
          width: 18px;
          left: 3px;
          bottom: 3px;
          background-color: white;
          transition: 0.3s;
          border-radius: 50%;
        }

        input:checked + .slider {
          background: var(--accent-linear);
        }

        input:checked + .slider:before {
          transform: translateX(26px);
        }

        form.fields .actions {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
          margin: 20px 0 0;
          gap: 16px;
        }

        form.fields .actions > .action {
          border: none;
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
          padding: 14px 24px;
          height: 48px;
          position: relative;
          border-radius: 12px;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          flex: 1;
        }

        form.fields .actions > .action.cancel-btn {
          background: var(--gray-background);
          color: var(--text-color);
          border: 1px solid var(--border);
        }

        form.fields .actions > .action.cancel-btn:hover {
          background: var(--hover-background);
          transform: translateY(-1px);
        }

        form.fields .actions > .action.next {
          background: var(--accent-linear);
          color: var(--white-color);
          box-shadow: 0 2px 8px rgba(0, 96, 223, 0.2);
        }

        form.fields .actions > .action.next:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 16px rgba(0, 96, 223, 0.3);
        }

        form.fields .actions > .action.next:active {
          transform: translateY(0);
          box-shadow: 0 2px 8px rgba(0, 96, 223, 0.2);
        }

        form.fields .actions > .action:disabled {
          pointer-events: none;
          opacity: 0.6;
          transform: none;
          box-shadow: none;
        }

        .spinner {
          width: 20px;
          height: 20px;
          animation: spin 1s linear infinite;
          margin-right: 8px;
        }

        .spinner .path {
          stroke: currentColor;
          stroke-dasharray: 90;
          stroke-dashoffset: 0;
          transform-origin: center;
          animation: dash 1.5s ease-in-out infinite;
        }

        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

        @keyframes dash {
          0% {
            stroke-dasharray: 1, 200;
            stroke-dashoffset: 0;
          }
          50% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -35px;
          }
          100% {
            stroke-dasharray: 89, 200;
            stroke-dashoffset: -124px;
          }
        }

        /* Responsive Design */
        @media (max-width: 768px) {
          #content {
            width: 95%;
            padding: 25px 20px;
            border-radius: 20px;
            margin: 10px;
          }

          .welcome > .head > h2.consent {
            font-size: 1.3rem;
          }
        }

        @media (max-width: 480px) {
          #content {
            width: 98%;
            padding: 20px 15px;
            border-radius: 16px;
          }

          form.fields .actions {
            flex-direction: column;
          }

          form.fields .actions > .action {
            width: 100%;
          }
        }
      </style>
    `;
  }
}
