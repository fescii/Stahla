export default class UserProfile extends HTMLElement {
  constructor() {
    super();
    console.log("UserProfile constructor called");
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/auth/me";
    this.userData = null;
    this._loading = true;
    this._error = false;
    this._errorMessage = null;

    // Add global update function for popups to call
    if (this.app) {
      this.app.updateUserData = (newUserData) => {
        this.userData = newUserData;
        this.render();
      };
    }

    this.render();
  }

  render() {
    console.log("Rendering UserProfile component");
    this.shadowObj.innerHTML = this.getTemplate();

    // Set up event listeners after each render
    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  connectedCallback() {
    console.log("UserProfile connectedCallback fired");

    // Fetch user data when component is connected to the DOM
    setTimeout(() => {
      this._fetchUserData();
    }, 300);
  }

  _setupEventListeners() {
    // Use event delegation for edit profile button
    this.shadowObj.addEventListener('click', (e) => {
      if (e.target.closest('.edit-profile-btn')) {
        this._handleEditProfile();
      }
    });
  }

  // Method to fetch user data
  _fetchUserData = async () => {
    console.log("Fetching user data from:", this.url);
    this._loading = true;
    this.render();

    try {
      const response = await this.api.get(this.url, { content: "json" });

      // Check for errors in the response
      if (
        response.status_code === 401 ||
        (response.error_message &&
          response.error_message.includes("validate credentials"))
      ) {
        console.log("Authentication required for user profile access");
        this._loading = false;
        this._error = true;
        this._errorMessage = "Authentication required. Please log in.";
        this.app.showAccess();
        this.render();
        return;
      }

      if (!response.success || !response.data) {
        this._loading = false;
        this._error = true;
        this._errorMessage = response.error_message || "Failed to load user data";
        this.userData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._error = false;
      this._errorMessage = null;

      // Remove hashed_password from the displayed data for security
      const userData = { ...response.data };
      if (userData.hashed_password) {
        delete userData.hashed_password;
      }

      this.userData = userData;
      console.log("User data fetched successfully:", this.userData);

      // Render with the new data
      this.render();

    } catch (error) {
      console.error("Error fetching user data:", error);
      this._loading = false;
      this._error = true;
      this._errorMessage = "An error occurred while loading user data";
      this.userData = null;
      this.render();
    }
  };

  // Handle edit profile action - similar to all.js pattern
  _handleEditProfile = () => {
    console.log("Edit profile button clicked");
    console.log("Current user data:", this.userData);

    // Remove any existing popups first
    const existingPopups = document.querySelectorAll('edit-profile-popup, edit-user-admin-popup, delete-popup');
    existingPopups.forEach(popup => popup.remove());

    // Create and show edit profile popup using the same pattern as all.js
    const popup = /*html*/`<edit-profile-popup 
      user-id="${this.userData.id}"
      user-name="${this.userData.name || ''}"
      user-email="${this.userData.email}"
      user-bio="${this.userData.bio || ''}"
      user-role="${this.userData.role || 'member'}"
      user-active="${this.userData.is_active}"
      user-picture="${this.userData.picture || ''}"
    ></edit-profile-popup>`;

    document.body.insertAdjacentHTML('beforeend', popup);
  };

  getTemplate() {
    return /* html */ `
      ${this.getStyles()}
      ${this.getBody()}
    `;
  }

  getBody = () => {
    return /* html */ `
      <div class="container">
        ${this._loading ? this.getLoader() : ''}
        ${!this._loading && this._error ? this._getErrorHTML() : ''}
        ${!this._loading && !this._error && this.userData ? this._getUserProfileHTML() : ''}
      </div>
    `;
  };

  _getUserProfileHTML = () => {
    return /* html */ `
      <div class="profile-container">
        <div class="profile-header">
          <h1 class="profile-title">My Profile</h1>
          <button class="edit-profile-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 20h9"></path>
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
            </svg>
            Edit Profile
          </button>
        </div>
        
        <div class="profile-card">
          <div class="profile-info">
            <div class="profile-avatar">
              ${this.userData.picture
        ? `<img src="${this.userData.picture}" alt="Profile picture" class="profile-image">`
        : this._getInitialsAvatar(this.userData.name)
      }
            </div>
            
            <div class="profile-details">
              <div class="user-main">
                <h2 class="user-name">${this.userData.name}</h2>
                <span class="user-email">${this.userData.email}</span>
              </div>
              
              <div class="user-meta">
                <span class="role-badge ${this.userData.role}">${this._formatRole(this.userData.role)}</span>
                <span class="status-badge ${this.userData.is_active ? 'active' : 'inactive'}">
                  ${this.userData.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
          
          <div class="user-info-details">
            ${this.userData.bio ? `
              <div class="info-item">
                <span class="info-label">Bio</span>
                <span class="info-value bio">${this.userData.bio}</span>
              </div>
            ` : ''}
            
            <div class="info-item">
              <span class="info-label">User ID</span>
              <span class="info-value id">${this.userData.id}</span>
            </div>
          </div>
        </div>
      </div>
    `;
  };

  _getInitialsAvatar = (name) => {
    if (!name) return '';

    // Get initials from name (first and last name if available)
    const nameParts = name.split(' ');
    let initials = nameParts[0][0].toUpperCase();

    if (nameParts.length > 1) {
      initials += nameParts[nameParts.length - 1][0].toUpperCase();
    }

    // Generate a consistent color based on the name
    const hue = this._getHashCode(name) % 360;
    const backgroundColor = `hsl(${hue}, 75%, 55%)`;

    return /* html */ `
      <div class="avatar-circle" style="background-color: ${backgroundColor}">
        <span class="avatar-initials">${initials}</span>
      </div>
    `;
  };

  // Simple hash function for generating consistent colors
  _getHashCode = (str) => {
    let hash = 0;
    if (str.length === 0) return hash;

    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }

    return Math.abs(hash);
  };

  _formatRole = (role) => {
    if (!role) return 'User';
    return role.charAt(0).toUpperCase() + role.slice(1);
  };

  _getErrorHTML = () => {
    return /* html */ `
    <div class="error-state">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <h3>Unable to Load Profile</h3>
      <p>${this._errorMessage || 'An error occurred while loading your profile data. Please try again or contact support if the problem persists.'}</p>
      <button class="retry-btn" onclick="this._fetchUserData()">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 2v6h6"></path>
          <path d="M3 13a9 9 0 1 0 3-7.7L3 8"></path>
        </svg>
        Try Again
      </button>
    </div>
    `;
  };

  getLoader = () => {
    return /* html */ `
    <div class="loader-container">
      <div class="spinner"></div>
      <p>Loading your profile data...</p>
    </div>
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
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
      }

      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }
      
      .container {
        max-width: 100%;
        margin: 0 auto;
        padding: 2rem 1rem;
      }
      
      /* Profile Container */
      .profile-container {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }
      
      .profile-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }
      
      .profile-title {
        font-family: var(--font-main, 'Inter', sans-serif);
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0;
        color: var(--title-color);
        position: relative;
        letter-spacing: -0.01em;
      }
      
      .profile-title::after {
        content: '';
        position: absolute;
        bottom: -8px;
        left: 0;
        width: 45px;
        height: 4px;
        background: linear-gradient(90deg, var(--accent-color) 0%, rgba(0, 96, 223, 0.6) 100%);
        border-radius: 4px;
      }
      
      .edit-profile-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, var(--accent-color) 0%, #0052cc 100%);
        color: var(--white-color);
        border: none;
        border-radius: 10px;
        padding: 0.8rem 1.2rem;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(0, 96, 223, 0.25);
      }
      
      .edit-profile-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0, 96, 223, 0.35);
      }
      
      .edit-profile-btn:active {
        transform: translateY(0);
      }
      
      /* Profile Card */
      .profile-card {
        background-color: var(--background);
        border-radius: 12px;
        padding: 1.5rem;
        border: var(--border);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      }
      
      .profile-info {
        display: flex;
        gap: 1.5rem;
        margin-bottom: 1.5rem;
      }
      
      .profile-avatar {
        flex-shrink: 0;
      }
  
      .avatar-circle {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        border: 2px solid var(--border);
      }

      .profile-image {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 2px solid var(--border);
      }
      
      .avatar-initials {
        font-size: 2rem;
        color: var(--white-color);
        font-weight: 700;
        letter-spacing: -1px;
      }
      
      .profile-details {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
      
      .user-main {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }
      
      .user-name {
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0;
        color: var(--title-color);
        letter-spacing: -0.01em;
      }
      
      .user-email {
        font-size: 1rem;
        color: var(--gray-color);
      }
      
      .user-meta {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        flex-wrap: wrap;
      }
      
      .role-badge, .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.3rem 0.8rem;
        border-radius: 16px;
        font-size: 0.75rem;
        font-weight: 600;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.06);
      }
      
      .role-badge.admin {
        background: linear-gradient(135deg, rgba(0, 96, 223, 0.1) 0%, rgba(0, 96, 223, 0.2) 100%);
        color: var(--accent-color);
        border: 1px solid rgba(0, 96, 223, 0.25);
      }
      
      .role-badge.user {
        background: linear-gradient(135deg, rgba(69, 162, 158, 0.1) 0%, rgba(69, 162, 158, 0.2) 100%);
        color: #45a29e;
        border: 1px solid rgba(69, 162, 158, 0.25);
      }
      
      .status-badge.active {
        background: linear-gradient(135deg, rgba(44, 182, 125, 0.1) 0%, rgba(44, 182, 125, 0.2) 100%);
        color: var(--success-color);
        border: 1px solid rgba(44, 182, 125, 0.25);
      }
      
      .status-badge.inactive {
        background: linear-gradient(135deg, rgba(239, 71, 111, 0.1) 0%, rgba(239, 71, 111, 0.2) 100%);
        color: var(--error-color);
        border: 1px solid rgba(239, 71, 111, 0.25);
      }
      
      .user-info-details {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        padding-top: 1rem;
        border-top: var(--border);
      }
      
      .info-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }
      
      .info-label {
        font-size: 0.875rem;
        color: var(--gray-color);
        font-weight: 600;
      }
      
      .info-value {
        font-size: 1rem;
        font-weight: 500;
        color: var(--title-color);
      }
      
      .info-value.id {
        font-family: var(--font-mono, monospace);
        font-size: 0.9rem;
        background-color: var(--gray-background);
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        color: var(--gray-color);
        display: inline-block;
        max-width: fit-content;
      }

      .info-value.bio {
        line-height: 1.5;
        font-family: var(--font-text), sans-serif;
        opacity: 0.9;
        font-style: italic;
      }
      
      /* Loader */
      .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        height: 400px;
        background-color: var(--background);
        border-radius: 12px;
        border: var(--border);
      }
      
      .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid rgba(0, 0, 0, 0.1);
        border-top-color: var(--accent-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }
      
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
      
      .loader-container p {
        color: var(--gray-color);
        font-size: 1rem;
        font-weight: 500;
      }
      
      /* Error State */
      .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        text-align: center;
        height: 400px;
        background-color: var(--background);
        border-radius: 12px;
        border: 1px solid rgba(239, 71, 111, 0.2);
        padding: 2rem;
      }
      
      .error-state svg {
        color: var(--error-color);
      }
      
      .error-state h3 {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
        color: var(--title-color);
      }
      
      .error-state p {
        color: var(--gray-color);
        max-width: 400px;
        margin: 0;
        line-height: 1.6;
      }
      
      .retry-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, var(--accent-color) 0%, #0052cc 100%);
        color: var(--white-color);
        border: none;
        border-radius: 10px;
        padding: 0.8rem 1.5rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px rgba(0, 96, 223, 0.25);
        margin-top: 0.5rem;
      }
      
      .retry-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(0, 96, 223, 0.35);
      }
      
      /* Responsive Design */
      @media (max-width: 768px) {
        .container {
          padding: 1.5rem 1rem;
        }
        
        .profile-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 1rem;
          margin-bottom: 1.5rem;
        }
        
        .edit-profile-btn {
          align-self: stretch;
          justify-content: center;
        }
        
        .profile-info {
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        
        .user-meta {
          justify-content: center;
        }
      }
      
      @media (max-width: 480px) {
        .container {
          padding: 1rem 0.75rem;
        }
        
        .profile-card {
          padding: 1.25rem;
        }
        
        .avatar-circle, .profile-image {
          width: 70px;
          height: 70px;
        }
        
        .avatar-initials {
          font-size: 1.8rem;
        }
        
        .user-name {
          font-size: 1.4rem;
        }
        
        .user-meta {
          flex-direction: column;
          gap: 0.5rem;
        }
      }
    </style>
    `;
  }
}
