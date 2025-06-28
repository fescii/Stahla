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
          <h1 class="profile-title">My Profile</h1>
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
                <span class="info-label">Email Address</span>
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
              <p>Manage your password and security settings to keep your account protected</p>
              <button class="action-btn security-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                </svg>
                <span>Manage Security</span>
              </button>
            </div>
            
            <div class="action-card">
              <h3>Notification Preferences</h3>
              <p>Update how and when you receive notifications about account activity and updates</p>
              <button class="action-btn notify-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
                <span>Manage Notifications</span>
              </button>
            </div>
            
            <div class="action-card">
              <h3>Activity Log</h3>
              <p>View your recent account activity and login history to monitor your account usage</p>
              <button class="action-btn activity-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"></circle>
                  <polyline points="12 6 12 12 16 14"></polyline>
                </svg>
                <span>View Activity</span>
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
        gap: 2rem;
      }
      
      .profile-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
        position: relative;
      }
      
      .profile-title {
        font-family: var(--font-main, 'Inter', sans-serif);
        font-size: 1.9rem;
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
        transition: width 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      }
      
      .profile-container:hover .profile-title::after {
        width: 60px;
      }
      
      .edit-profile-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, var(--accent-color) 0%, #0052cc 100%);
        color: var(--white-color);
        border: none;
        border-radius: 10px;
        padding: 0.8rem 1.35rem;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        box-shadow: 0 4px 12px rgba(0, 96, 223, 0.25);
        position: relative;
        overflow: hidden;
      }
      
      .edit-profile-btn::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.2));
        transform: translateY(100%);
        transition: transform 0.6s cubic-bezier(0.165, 0.84, 0.44, 1);
      }
      
      .edit-profile-btn:hover {
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 6px 16px rgba(0, 96, 223, 0.35);
      }
      
      .edit-profile-btn:hover::after {
        transform: translateY(0);
      }
      
      .edit-profile-btn:active {
        transform: translateY(0) scale(0.98);
        box-shadow: 0 2px 8px rgba(0, 96, 223, 0.2);
      }
      
      .edit-profile-btn svg {
        transition: transform 0.3s ease;
      }
      
      .edit-profile-btn:hover svg {
        transform: translateY(-1px) rotate(-5deg);
      }
      
      /* Profile Card */
      .profile-card {
        display: flex;
        gap: 2rem;
        padding: 20px 0;
      }
      
      .profile-avatar {
        flex-shrink: 0;
      }
  
      .avatar-circle {
        width: 110px;
        height: 110px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        border: 3px solid rgba(255, 255, 255, 0.8);
      }
      
      .avatar-initials {
        font-size: 2.6rem;
        color: var(--white-color);
        font-weight: 800;
        letter-spacing: -1px;
        text-shadow: 0 2px 5px rgba(0, 0, 0, 0.15);
      }
      
      .profile-details {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }
      
      .detail-group {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
      }
      
      .user-name {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        color: var(--title-color);
        letter-spacing: -0.01em;
        position: relative;
        transition: all 0.3s ease;
      }
      
      .user-role, .user-status {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 1rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 600;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06);
        position: relative;
      }
      
      .user-role::before,
      .user-status::before {
        content: '';
        position: absolute;
        left: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        width: 8px;
        height: 8px;
        border-radius: 50%;
        transition: all 0.3s ease;
      }
      
      .user-role {
        padding-left: 1.5rem;
      }
      
      .user-status {
        padding-left: 1.5rem;
      }
      
      .user-role.admin {
        background: linear-gradient(135deg, rgba(0, 96, 223, 0.1) 0%, rgba(0, 96, 223, 0.2) 100%);
        color: var(--accent-color);
        border: 1px solid rgba(0, 96, 223, 0.25);
      }
      
      .user-role.admin::before {
        background-color: var(--accent-color);
        box-shadow: 0 0 0 3px rgba(0, 96, 223, 0.15);
      }
      
      .user-role.user {
        background: linear-gradient(135deg, rgba(69, 162, 158, 0.1) 0%, rgba(69, 162, 158, 0.2) 100%);
        color: #45a29e;
        border: 1px solid rgba(69, 162, 158, 0.25);
      }
      
      .user-role.user::before {
        background-color: #45a29e;
        box-shadow: 0 0 0 3px rgba(69, 162, 158, 0.15);
      }
      
      .user-status.active {
        background: linear-gradient(135deg, rgba(44, 182, 125, 0.1) 0%, rgba(44, 182, 125, 0.2) 100%);
        color: var(--success-color);
        border: 1px solid rgba(44, 182, 125, 0.25);
      }
      
      .user-status.active::before {
        background-color: var(--success-color);
        box-shadow: 0 0 0 3px rgba(44, 182, 125, 0.15);
      }
      
      .user-status.active::before {
        box-shadow: 0 0 0 4px rgba(44, 182, 125, 0.2), 0 0 10px rgba(44, 182, 125, 0.3);
      }
      
      .user-status.inactive {
        background: linear-gradient(135deg, rgba(239, 71, 111, 0.1) 0%, rgba(239, 71, 111, 0.2) 100%);
        color: var(--error-color);
        border: 1px solid rgba(239, 71, 111, 0.25);
      }
      
      .user-status.inactive::before {
        background-color: var(--error-color);
        box-shadow: 0 0 0 3px rgba(239, 71, 111, 0.15);
      }
      
      .user-status.inactive::before {
        box-shadow: 0 0 0 4px rgba(239, 71, 111, 0.2), 0 0 10px rgba(239, 71, 111, 0.3);
      }
      
      .user-info {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        margin-top: 1rem;
        background-color: rgba(0, 0, 0, 0.01);
        padding: 1.25rem;
        border-radius: 12px;
        border: 1px solid rgba(0, 0, 0, 0.04);
        transition: all 0.3s ease;
      }
      
      .profile-card:hover .user-info {
        background-color: rgba(0, 0, 0, 0.02);
        transform: translateX(3px);
      }
      
      .info-item {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
      }
      
      .info-label {
        font-size: 0.875rem;
        color: var(--gray-color);
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }
      
      .info-label::before {
        content: '';
        width: 3px;
        height: 3px;
        background-color: var(--accent-color);
        border-radius: 50%;
        display: inline-block;
      }
      
      .info-value {
        font-size: 1.05rem;
        font-weight: 500;
        color: var(--title-color);
      }
      
      .info-value.id {
        font-family: var(--font-mono, monospace);
        font-size: 0.9rem;
        background-color: rgba(0, 0, 0, 0.03);
        padding: 0.65rem 0.85rem;
        border-radius: 8px;
        color: var(--gray-color);
        background-color: var(--gray-background);
        display: inline-block;
        max-width: fit-content;
      }
      
      .info-item:hover .info-value.id {
        background-color: rgba(0, 0, 0, 0.05);
        border-color: rgba(0, 0, 0, 0.12);
      }
      
      /* Profile Actions */
      .profile-actions {
        margin-top: 1rem;
      }
      
      .action-cards {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1.5rem;
      }
      
      .action-card {
        background-color: var(--background);
        border-radius: 14px;
        box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.04), 
                    0 5px 10px -5px rgba(0, 0, 0, 0.03);
        padding: 1.75rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        border: 1px solid rgba(0, 0, 0, 0.06);
        transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        position: relative;
        overflow: hidden;
      }
      
      .action-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 0;
        background: linear-gradient(to bottom, var(--accent-color), rgba(0, 96, 223, 0.5));
        transition: height 0.4s cubic-bezier(0.19, 1, 0.22, 1);
        border-radius: 4px 0 0 4px;
      }
      
      .action-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px -10px rgba(0, 0, 0, 0.08), 
                    0 10px 20px -5px rgba(0, 0, 0, 0.05);
      }
      
      .action-card:hover::before {
        height: 100%;
      }
      
      .action-card h3 {
        margin: 0;
        font-size: 1.35rem;
        font-weight: 700;
        color: var(--title-color);
        transition: all 0.3s ease;
      }
      
      .action-card:hover h3 {
        transform: translateX(5px);
        color: var(--accent-color);
      }
      
      .action-card p {
        margin: 0;
        color: var(--gray-color);
        font-size: 0.95rem;
        line-height: 1.6;
        flex-grow: 1;
        transition: all 0.3s ease;
      }
      
      .action-card:hover p {
        transform: translateX(3px);
      }
      
      .action-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.65rem 1.25rem;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        border: 1px solid rgba(0, 0, 0, 0.08);
        background-color: rgba(0, 0, 0, 0.02);
        color: var(--text-color);
        margin-top: auto;
        position: relative;
        overflow: hidden;
      }
      
      .action-btn::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 100%;
        height: 100%;
        background-color: var(--accent-color);
        border-radius: 50%;
        opacity: 0;
        transform: translate(-50%, -50%) scale(0);
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.4s ease;
        z-index: 0;
      }
      
      .action-btn svg {
        position: relative;
        z-index: 1;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      }
      
      .action-btn span {
        position: relative;
        z-index: 1;
      }
      
      .action-btn:hover {
        border-color: var(--accent-color);
        color: var(--accent-color);
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06);
      }
      
      .action-btn:hover::after {
        opacity: 0.08;
        transform: translate(-50%, -50%) scale(2);
      }
      
      .action-btn:hover svg {
        transform: scale(1.15) rotate(-5deg);
      }
      
      /* Loader */
      .loader-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 1.75rem;
        height: 400px;
        background-color: var(--background);
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 
                    0 8px 10px -6px rgba(0, 0, 0, 0.02);
        border: 1px solid rgba(0, 0, 0, 0.06);
      }
      
      .spinner {
        width: 56px;
        height: 56px;
        border: 4px solid rgba(0, 0, 0, 0.05);
        border-top-color: var(--accent-color);
        border-radius: 50%;
        filter: drop-shadow(0 4px 10px rgba(0, 96, 223, 0.2));
        animation: spin 1.4s cubic-bezier(0.68, -0.55, 0.27, 1.55) infinite;
      }
      
      @keyframes spin {
        0% { transform: rotate(0deg); }
        25% { transform: rotate(90deg); }
        50% { transform: rotate(180deg); }
        75% { transform: rotate(270deg); }
        100% { transform: rotate(360deg); }
      }
      
      .loader-container p {
        color: var(--gray-color);
        font-size: 1.05rem;
        font-weight: 500;
        animation: pulse 1.8s infinite alternate;
        background: linear-gradient(90deg, var(--title-color), var(--gray-color));
        background-size: 200% auto;
        background-clip: text;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: gradientText 2s linear infinite;
      }
      
      @keyframes pulse {
        from { opacity: 0.7; }
        to { opacity: 1; }
      }
      
      @keyframes gradientText {
        0% { background-position: 0% center; }
        50% { background-position: 100% center; }
        100% { background-position: 0% center; }
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
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 
                    0 8px 10px -6px rgba(0, 0, 0, 0.02);
        border: 1px solid rgba(239, 71, 111, 0.15);
        padding: 2.5rem;
      }
      
      .error-state svg {
        color: var(--error-color);
        animation: pulse-error 2s ease infinite;
        filter: drop-shadow(0 4px 8px rgba(239, 71, 111, 0.3));
      }
      
      @keyframes pulse-error {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.1); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
      }
      
      .error-state h3 {
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0;
        color: var(--title-color);
        letter-spacing: -0.01em;
      }
      
      .error-state p {
        color: var(--gray-color);
        max-width: 450px;
        margin: 0;
        line-height: 1.7;
        font-size: 1.05rem;
      }
      
      .retry-btn {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: linear-gradient(135deg, var(--accent-color) 0%, #0052cc 100%);
        color: var(--white-color);
        border: none;
        border-radius: 12px;
        padding: 0.9rem 1.8rem;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        margin-top: 0.75rem;
        box-shadow: 0 4px 12px rgba(0, 96, 223, 0.25);
        position: relative;
        overflow: hidden;
      }
      
      .retry-btn::after {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.2));
        transform: translateY(100%);
        transition: transform 0.6s cubic-bezier(0.165, 0.84, 0.44, 1);
      }
      
      .retry-btn:hover {
        transform: translateY(-3px) scale(1.03);
        box-shadow: 0 6px 18px rgba(0, 96, 223, 0.35);
      }
      
      .retry-btn:hover::after {
        transform: translateY(0);
      }
      
      .retry-btn:active {
        transform: translateY(0) scale(0.98);
      }
      
      .retry-btn svg {
        transition: transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        animation: none;
        filter: none;
      }
      
      .retry-btn:hover svg {
        transform: rotate(180deg);
      }
      
      /* Responsive Design */
      @media (max-width: 900px) {
        .container {
          padding: 1.5rem 1rem;
        }
        
        .profile-card {
          padding: 1.5rem;
          gap: 1.5rem;
        }
      }
      
      @media (max-width: 768px) {
        .profile-card {
          flex-direction: column;
          align-items: center;
          text-align: center;
        }
        
        .avatar-circle {
          width: 100px;
          height: 100px;
        }
        
        .avatar-initials {
          font-size: 2.3rem;
        }
        
        .detail-group {
          justify-content: center;
        }
        
        .user-info {
          text-align: left;
        }
        
        .action-cards {
          grid-template-columns: 1fr;
          gap: 1.25rem;
        }
        
        .action-card {
          padding: 1.5rem;
        }
      }
      
      @media (max-width: 600px) {
        .profile-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 1.25rem;
          margin-bottom: 1.5rem;
        }
        
        .profile-title {
          font-size: 1.7rem;
        }
        
        .edit-profile-btn {
          align-self: stretch;
          justify-content: center;
        }
        
        .profile-card {
          padding: 1.25rem;
        }
        
        .user-name {
          font-size: 1.7rem;
        }
      }
      
      @media (max-width: 480px) {
        .container {
          padding: 1rem 0.75rem;
        }
        
        .avatar-circle {
          width: 85px;
          height: 85px;
        }
        
        .avatar-initials {
          font-size: 2rem;
        }
        
        .user-info {
          padding: 1rem;
        }
        
        .info-value.id {
          font-size: 0.8rem;
          padding: 0.5rem 0.75rem;
        }
        
        .action-card {
          padding: 1.25rem;
        }
        
        .action-card h3 {
          font-size: 1.2rem;
        }
      }
    </style>
    `;
  }
}