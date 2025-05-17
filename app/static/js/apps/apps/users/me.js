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
    // Add event listeners for interactive elements
    const editProfileBtn = this.shadowObj.querySelector('.edit-profile-btn');
    if (editProfileBtn) {
      editProfileBtn.addEventListener('click', this._handleEditProfile);
    }
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

  // Handle edit profile action
  _handleEditProfile = () => {
    console.log("Edit profile button clicked");
    // Implement edit profile functionality or navigation here
    // For example, could open a modal or navigate to an edit page
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
          <h1 class="profile-title">User Profile</h1>
          <button class="edit-profile-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
            </svg>
            Edit Profile
          </button>
        </div>
        
        <div class="profile-card">
          <div class="profile-avatar">
            ${this._getInitialsAvatar(this.userData.name)}
          </div>
          
          <div class="profile-details">
            <div class="detail-group">
              <h2 class="user-name">${this.userData.name}</h2>
              <span class="user-role ${this.userData.role}">${this._formatRole(this.userData.role)}</span>
              <span class="user-status ${this.userData.is_active ? 'active' : 'inactive'}">
                ${this.userData.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            
            <div class="user-info">
              <div class="info-item">
                <span class="info-label">Email</span>
                <span class="info-value">${this.userData.email}</span>
              </div>
              
              <div class="info-item">
                <span class="info-label">User ID</span>
                <span class="info-value id">${this.userData.id}</span>
              </div>
            </div>
          </div>
        </div>
        
        <div class="profile-actions">
          <div class="action-cards">
            <div class="action-card">
              <h3>Account Security</h3>
              <p>Manage your password and security settings</p>
              <button class="action-btn security-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                Manage Security
              </button>
            </div>
            
            <div class="action-card">
              <h3>Notification Preferences</h3>
              <p>Update how and when you receive notifications</p>
              <button class="action-btn notify-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
                Manage Notifications
              </button>
            </div>
            
            <div class="action-card">
              <h3>Activity Log</h3>
              <p>View your recent account activity and login history</p>
              <button class="action-btn activity-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                View Activity
              </button>
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
    const backgroundColor = `hsl(${hue}, 70%, 60%)`;
    
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
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <h3>Error</h3>
      <p>${this._errorMessage || 'An error occurred while loading user data.'}</p>
      <button class="retry-btn" onclick="this._fetchUserData()">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 2v6h6"></path>
          <path d="M3 13a9 9 0 1 0 3-7.7L3 8"></path>
        </svg>
        Retry
      </button>
    </div>
    `;
  };

  getLoader = () => {
    return /* html */ `
    <div class="loader-container">
      <div class="spinner"></div>
      <p>Loading user data...</p>
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
      }

      * {
        box-sizing: border-box;
      }
      
      .container {
        width: 100%;
        margin: 0;
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
        font-weight: 600;
        margin: 0;
        color: var(--title-color);
      }
      
      .edit-profile-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background-color: var(--accent-color);
        color: var(--white-color);
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s ease;
      }
      
      .edit-profile-btn:hover {
        background-color: var(--accent-alt);
      }
      
      /* Profile Card */
      .profile-card {
        display: flex;
        gap: 1.5rem;
        background-color: var(--background);
        border-bottom: var(--border);
        padding: 10px 0 25px 0;
      }
      
      .profile-avatar {
        flex-shrink: 0;
      }
      
      .avatar-circle {
        width: 90px;
        height: 90px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
      }
      
      .avatar-initials {
        font-size: 2.3rem;
        color: var(--white-color);
      }
      
      .profile-details {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 1rem;
      }
      
      .detail-group {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.75rem;
      }
      
      .user-name {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
      }
      
      .user-role, .user-status {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.875rem;
        font-weight: 500;
      }
      
      .user-role.admin {
        background-color: var(--tab-background);
        color: var(--accent-color);
      }
      
      .user-role.user {
        background-color: rgba(69, 162, 158, 0.13);
        color: #45a29e;
      }
      
      .user-status.active {
        background-color: rgba(44, 182, 125, 0.13);
        color: var(--success-color);
      }
      
      .user-status.inactive {
        background-color: rgba(239, 71, 111, 0.13);
        color: var(--error-color);
      }
      
      .user-info {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-top: 1rem;
      }
      
      .info-item {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
      }
      
      .info-label {
        font-size: 0.875rem;
        color: var(--gray-color);
        font-weight: 500;
      }
      
      .info-value {
        font-size: 1rem;
        font-weight: 500;
      }
      
      .info-value.id {
        font-family: var(--font-mono, monospace);
        font-size: 0.875rem;
        background-color: var(--hover-background);
        padding: 0.5rem;
        border-radius: 4px;
        border: var(--border);
        color: var(--gray-color);
      }
      
      /* Profile Actions */
      .profile-actions {
        margin-top: 1rem;
      }
      
      .action-cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 1rem;
      }
      
      .action-card {
        background-color: var(--background);
        border-radius: 8px;
        box-shadow: var(--card-box-shadow-alt);
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
      }
      
      .action-card h3 {
        margin: 0;
        font-size: 1.25rem;
        font-weight: 600;
      }
      
      .action-card p {
        margin: 0;
        color: var(--gray-color);
        font-size: 0.875rem;
        line-height: 1.5;
        flex-grow: 1;
      }
      
      .action-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        border: var(--action-border);
        background-color: transparent;
        color: var(--text-color);
        margin-top: auto;
      }
      
      .action-btn:hover {
        background-color: var(--hover-background);
        border: var(--border-button);
      }
      
      /* Loader */
      .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        height: 300px;
      }
      
      .spinner {
        width: 40px;
        height: 40px;
        border: 3px solid var(--stat-background);
        border-top-color: var(--accent-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      /* Error State */
      .error-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1rem;
        text-align: center;
        height: 300px;
      }
      
      .error-state svg {
        color: var(--error-color);
      }
      
      .error-state h3 {
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
      }
      
      .error-state p {
        color: var(--gray-color);
        max-width: 350px;
        margin: 0;
      }
      
      .retry-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background-color: var(--accent-color);
        color: var(--white-color);
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s ease;
        margin-top: 1rem;
      }
      
      .retry-btn:hover {
        background-color: var(--accent-alt);
      }
      
      /* Responsive Design */
      @media (max-width: 768px) {
        .profile-card {
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        
        .detail-group {
          justify-content: center;
        }
        
        .action-cards {
          grid-template-columns: 1fr;
        }
      }
      
      @media (max-width: 480px) {
        .profile-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 1rem;
        }
        
        .edit-profile-btn {
          align-self: stretch;
          justify-content: center;
        }
      }
    </style>
    `;
  };
}