export default class AddUser extends HTMLElement {
  constructor() {
    super();
    console.log("AddUser constructor called");
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/auth/users";
    
    // Form state
    this._formData = {
      name: '',
      email: '',
      password: '',
      is_active: true,
      is_admin: false
    };
    
    // Component state
    this._loading = false;
    this._error = false;
    this._success = false;
    this._errorMessage = null;
    this._passwordVisible = false;
    
    this.render();
  }

  render() {
    console.log("Rendering AddUser component");
    this.shadowObj.innerHTML = this.getTemplate();
    
    // Set up event listeners after each render
    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  connectedCallback() {
    console.log("AddUser connectedCallback fired");
  }

  _setupEventListeners() {
    // Form submission
    const form = this.shadowObj.querySelector('.add-user-form');
    if (form) {
      form.addEventListener('submit', (e) => {
        e.preventDefault();
        this._handleSubmit();
      });
    }
    
    // Input fields
    const nameInput = this.shadowObj.querySelector('#name');
    if (nameInput) {
      nameInput.addEventListener('input', (e) => {
        this._formData.name = e.target.value;
      });
    }
    
    const emailInput = this.shadowObj.querySelector('#email');
    if (emailInput) {
      emailInput.addEventListener('input', (e) => {
        this._formData.email = e.target.value;
      });
    }
    
    const passwordInput = this.shadowObj.querySelector('#password');
    if (passwordInput) {
      passwordInput.addEventListener('input', (e) => {
        this._formData.password = e.target.value;
      });
    }
    
    // Toggle password visibility
    const togglePassword = this.shadowObj.querySelector('.toggle-password');
    if (togglePassword) {
      togglePassword.addEventListener('click', () => {
        this._passwordVisible = !this._passwordVisible;
        const passwordInput = this.shadowObj.querySelector('#password');
        passwordInput.type = this._passwordVisible ? 'text' : 'password';
        this.render();
      });
    }
    
    // Toggle switches
    const isActiveSwitch = this.shadowObj.querySelector('#is_active');
    if (isActiveSwitch) {
      isActiveSwitch.addEventListener('change', (e) => {
        this._formData.is_active = e.target.checked;
      });
    }
    
    const isAdminSwitch = this.shadowObj.querySelector('#is_admin');
    if (isAdminSwitch) {
      isAdminSwitch.addEventListener('change', (e) => {
        this._formData.is_admin = e.target.checked;
      });
    }
    
    // Cancel button
    const cancelButton = this.shadowObj.querySelector('.cancel-btn');
    if (cancelButton) {
      cancelButton.addEventListener('click', () => {
        this._handleCancel();
      });
    }
    
    // Back to list after success
    const backButton = this.shadowObj.querySelector('.back-to-list');
    if (backButton) {
      backButton.addEventListener('click', () => {
        this._navigateToUsersList();
      });
    }
    
    // Add another user button
    const addAnotherButton = this.shadowObj.querySelector('.add-another-btn');
    if (addAnotherButton) {
      addAnotherButton.addEventListener('click', () => {
        this._resetForm();
      });
    }
  }

  _handleSubmit = async () => {
    // Validate form
    if (!this._validateForm()) {
      return;
    }
    
    // Set loading state
    this._loading = true;
    this._error = false;
    this._success = false;
    this.render();
    
    try {
      // Prepare data in the correct format
      const userData = {
        email: this._formData.email,
        password: this._formData.password,
        name: this._formData.name,
        is_active: this._formData.is_active,
        is_admin: this._formData.is_admin
      };
      
      // Make API request with proper content type and body
      const response = await this.api.post(this.url, { 
        content: "json",
        body: userData
      });
      
      // Handle response
      if (!response.success) {
        this._error = true;
        this._errorMessage = response.error_message || "Failed to create user";
        this._loading = false;
        this.render();
        return;
      }
      
      // Success
      this._loading = false;
      this._success = true;
      this._formData = {
        name: '',
        email: '',
        password: '',
        is_active: true,
        is_admin: false
      };
      this.render();
      
    } catch (error) {
      console.error("Error creating user:", error);
      this._loading = false;
      this._error = true;
      this._errorMessage = "An unexpected error occurred";
      this.render();
    }
  };
  
  _validateForm = () => {
    // Reset error
    this._error = false;
    this._errorMessage = null;
    
    // Validate email
    if (!this._formData.email || !this._validateEmail(this._formData.email)) {
      this._error = true;
      this._errorMessage = "Please enter a valid email address";
      this.render();
      return false;
    }
    
    // Validate password
    if (!this._formData.password || this._formData.password.length < 8) {
      this._error = true;
      this._errorMessage = "Password must be at least 8 characters long";
      this.render();
      return false;
    }
    
    // Validate name (optional)
    if (this._formData.name && this._formData.name.length < 2) {
      this._error = true;
      this._errorMessage = "Name must be at least 2 characters long";
      this.render();
      return false;
    }
    
    return true;
  };
  
  _validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
  };

  _handleCancel = () => {
    // Navigate back to the users list
    this._navigateToUsersList();
  };
  
  _navigateToUsersList = () => {
    // This method will depend on your app's routing mechanism
    // Here's a simple example that assumes the app has a navigation method
    if (this.app && typeof this.app.navigate === 'function') {
      this.app.navigate('/users');
    } else {
      // Fallback: reload the page
      window.location.href = '/users';
    }
  };

  _resetForm = () => {
    this._formData = {
      name: '',
      email: '',
      password: '',
      is_active: true,
      is_admin: false
    };
    this._success = false;
    this._error = false;
    this._errorMessage = null;
    this.render();
  };

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody = () => {
    // Show different content based on component state
    if (this._success) {
      return this._getSuccessHTML();
    }
    
    return /* html */ `
      <div class="container">
        <div class="add-user-container">
          <div class="form-header">
            <h1 class="form-title">Add New User</h1>
            <p class="form-subtitle">Create a new user account</p>
          </div>
          
          ${this._error ? this._getErrorHTML() : ''}
          
          <form class="add-user-form">
            <div class="form-group">
              <label for="email" class="form-label">Email Address <span class="required">*</span></label>
              <input type="email" id="email" class="form-input" placeholder="Enter user email" required value="${this._formData.email}">
            </div>
            
            <div class="form-group">
              <label for="name" class="form-label">Full Name</label>
              <input type="text" id="name" class="form-input" placeholder="Enter user's full name" value="${this._formData.name}">
            </div>
            
            <div class="form-group">
              <label for="password" class="form-label">Password <span class="required">*</span></label>
              <div class="password-input-wrapper">
                <input 
                  type="${this._passwordVisible ? 'text' : 'password'}" 
                  id="password" 
                  class="form-input" 
                  placeholder="Enter a strong password" 
                  required
                  value="${this._formData.password}"
                >
                <button type="button" class="toggle-password" tabindex="-1">
                  ${this._passwordVisible ? this._getHidePasswordIcon() : this._getShowPasswordIcon()}
                </button>
              </div>
              <p class="password-hint">Password should be at least 8 characters long</p>
            </div>
            
            <div class="form-group switches">
              <div class="switch-item">
                <label for="is_active" class="switch-label">
                  <span>Active Account</span>
                  <span class="switch-description">User can login immediately</span>
                </label>
                <label class="switch">
                  <input type="checkbox" id="is_active" ${this._formData.is_active ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
              </div>
              
              <div class="switch-item">
                <label for="is_admin" class="switch-label">
                  <span>Admin Access</span>
                  <span class="switch-description">User will have administrative privileges</span>
                </label>
                <label class="switch">
                  <input type="checkbox" id="is_admin" ${this._formData.is_admin ? 'checked' : ''}>
                  <span class="slider round"></span>
                </label>
              </div>
            </div>
            
            <div class="form-actions">
              <button type="button" class="cancel-btn">Cancel</button>
              <button type="submit" class="submit-btn" ${this._loading ? 'disabled' : ''}>
                ${this._loading ? this._getLoadingSpinner() + 'Creating...' : 'Create User'}
              </button>
            </div>
          </form>
        </div>
      </div>
    `;
  };

  _getSuccessHTML = () => {
    return /* html */ `
      <div class="container">
        <div class="success-container">
          <div class="success-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
          </div>
          <h2 class="success-title">User Created Successfully</h2>
          <p class="success-message">
            The new user account has been created and can now access the system.
          </p>
          <div class="success-actions">
            <button class="add-another-btn">Add Another User</button>
            <button class="back-to-list">Return to Users List</button>
          </div>
        </div>
      </div>
    `;
  };

  _getErrorHTML = () => {
    return /* html */ `
      <div class="error-alert">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <span>${this._errorMessage}</span>
      </div>
    `;
  };
  
  _getShowPasswordIcon = () => {
    return /* html */ `
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
        <circle cx="12" cy="12" r="3"></circle>
      </svg>
    `;
  };
  
  _getHidePasswordIcon = () => {
    return /* html */ `
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
        <line x1="1" y1="1" x2="23" y2="23"></line>
      </svg>
    `;
  };
  
  _getLoadingSpinner = () => {
    return /* html */ `
      <svg class="spinner" viewBox="0 0 50 50">
        <circle class="path" cx="25" cy="25" r="20" fill="none" stroke-width="5"></circle>
      </svg>
    `;
  };

  getStyles = () => {
    return /* html */ `
    <style>
      :host {
        display: block;
        width: 100%;
        font-family: var(--font-text, 'Instrument Sans', sans-serif);
        color: var(--text-color);
      }
      
      .container {
        max-width: 100%;
        margin: 0;
        padding: 0;
      }
      
      /* Form Container */
      .add-user-container {
        background-color: var(--background);
        border-radius: 8px;
        padding: 2rem 1rem;
      }
      
      .form-header {
        margin-bottom: 2rem;
      }
      
      .form-title {
        font-family: var(--font-main, 'Inter', sans-serif);
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
        color: var(--title-color);
      }
      
      .form-subtitle {
        color: var(--gray-color);
        margin: 0;
        font-size: 0.95rem;
      }
      
      /* Form Elements */
      .add-user-form {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }
      
      .form-group {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
      }
      
      .form-label {
        font-weight: 500;
        font-size: 0.95rem;
        color: var(--title-color);
        display: flex;
        align-items: center;
        gap: 0.25rem;
      }
      
      .required {
        color: var(--error-color);
      }
      
      .form-input {
        padding: 0.75rem 1rem;
        border-radius: 6px;
        border: var(--input-border);
        background-color: var(--background);
        color: var(--text-color);
        font-size: 0.95rem;
        transition: border-color 0.2s ease;
      }
      
      .form-input:focus {
        border-color: var(--accent-color);
        outline: none;
      }
      
      .password-input-wrapper {
        position: relative;
      }
      
      .toggle-password {
        position: absolute;
        right: 1rem;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        color: var(--gray-color);
        cursor: pointer;
        padding: 0.25rem;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      
      .toggle-password:hover {
        color: var(--accent-color);
      }
      
      .password-hint {
        font-size: 0.8rem;
        color: var(--gray-color);
        margin: 0.25rem 0 0 0;
      }
      
      /* Switch Styles */
      .switches {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin-top: 0.5rem;
      }
      
      .switch-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      
      .switch-label {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }
      
      .switch-description {
        font-size: 0.8rem;
        color: var(--gray-color);
      }
      
      .switch {
        position: relative;
        display: inline-block;
        width: 48px;
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
        background-color: var(--stat-background);
        transition: .4s;
      }
      
      .slider:before {
        position: absolute;
        content: "";
        height: 18px;
        width: 18px;
        left: 3px;
        bottom: 3px;
        background-color: var(--background);
        transition: .4s;
      }
      
      input:checked + .slider {
        background-color: var(--accent-color);
      }
      
      input:focus + .slider {
        box-shadow: 0 0 1px var(--accent-color);
      }
      
      input:checked + .slider:before {
        transform: translateX(24px);
      }
      
      .slider.round {
        border-radius: 24px;
      }
      
      .slider.round:before {
        border-radius: 50%;
      }
      
      /* Form Actions */
      .form-actions {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        margin-top: 1rem;
      }
      
      .cancel-btn {
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        background-color: transparent;
        border: 1px solid var(--border-color);
        color: var(--text-color);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      
      .cancel-btn:hover {
        background-color: var(--hover-background);
      }
      
      .submit-btn {
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        background-color: var(--accent-color);
        border: none;
        color: var(--white-color);
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s ease;
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }
      
      .submit-btn:hover:not(:disabled) {
        background-color: var(--accent-alt);
      }
      
      .submit-btn:disabled {
        opacity: 0.7;
        cursor: not-allowed;
      }
      
      /* Error Alert */
      .error-alert {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem;
        border-radius: 6px;
        background-color: rgba(239, 71, 111, 0.1);
        color: var(--error-color);
        margin-bottom: 1.5rem;
      }
      
      /* Success State */
      .success-container {
        text-align: center;
        padding: 3rem 2rem;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 1.5rem;
      }
      
      .success-icon {
        color: var(--success-color);
        background-color: rgba(44, 182, 125, 0.1);
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      
      .success-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
        color: var(--title-color);
      }
      
      .success-message {
        color: var(--gray-color);
        max-width: 450px;
        margin: 0;
      }
      
      .success-actions {
        display: flex;
        gap: 1rem;
        margin-top: 1rem;
      }
      
      .add-another-btn {
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        background-color: transparent;
        border: 1px solid var(--accent-color);
        color: var(--accent-color);
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      
      .add-another-btn:hover {
        background-color: rgba(var(--accent-color-rgb), 0.1);
      }
      
      .back-to-list {
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        background-color: var(--accent-color);
        border: none;
        color: var(--white-color);
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s ease;
      }
      
      .back-to-list:hover {
        background-color: var(--accent-alt);
      }
      
      /* Loading Spinner */
      .spinner {
        animation: rotate 2s linear infinite;
        width: 18px;
        height: 18px;
        margin-right: 0.25rem;
      }
      
      .spinner .path {
        stroke: var(--white-color);
        stroke-linecap: round;
        animation: dash 1.5s ease-in-out infinite;
      }
      
      @keyframes rotate {
        100% {
          transform: rotate(360deg);
        }
      }
      
      @keyframes dash {
        0% {
          stroke-dasharray: 1, 150;
          stroke-dashoffset: 0;
        }
        50% {
          stroke-dasharray: 90, 150;
          stroke-dashoffset: -35;
        }
        100% {
          stroke-dasharray: 90, 150;
          stroke-dashoffset: -124;
        }
      }
      
      /* Responsive Design */
      @media (max-width: 768px) {
        .add-user-container {
          padding: 1.5rem;
        }
        
        .form-actions {
          flex-direction: column-reverse;
        }
        
        .submit-btn, .cancel-btn {
          width: 100%;
          justify-content: center;
        }
        
        .success-actions {
          flex-direction: column;
          width: 100%;
        }
        
        .add-another-btn, .back-to-list {
          width: 100%;
        }
      }
    </style>
    `;
  };
}