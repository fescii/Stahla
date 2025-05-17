export default class UsersList extends HTMLElement {
  constructor() {
    super();
    console.log("UsersList constructor called");
    this.shadowObj = this.attachShadow({ mode: "open" });
    this.app = window.app;
    this.api = this.app.api;
    this.url = this.getAttribute("api") || "/auth/users";
    this.usersData = null;
    this._loading = true;
    this._error = false;
    this._errorMessage = null;
    this._searchTerm = '';
    this._sortField = 'name';
    this._sortDirection = 'asc';
    this._filteredUsers = [];
    
    this.render();
  }

  render() {
    console.log("Rendering UsersList component");
    this.shadowObj.innerHTML = this.getTemplate();
    
    // Set up event listeners after each render
    setTimeout(() => {
      this._setupEventListeners();
    }, 0);
  }

  connectedCallback() {
    console.log("UsersList connectedCallback fired");
    
    // Fetch users data when component is connected to the DOM
    setTimeout(() => {
      this._fetchUsersData();
    }, 300);
  }

  _setupEventListeners() {
    // Search input
    const searchInput = this.shadowObj.querySelector('.search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this._searchTerm = e.target.value.toLowerCase();
        this._filterAndSortUsers();
        this.render();
      });
    }
    
    // Sort headers
    const sortHeaders = this.shadowObj.querySelectorAll('.sort-header');
    if (sortHeaders) {
      sortHeaders.forEach(header => {
        header.addEventListener('click', () => {
          const field = header.dataset.field;
          if (this._sortField === field) {
            // Toggle direction if already sorting by this field
            this._sortDirection = this._sortDirection === 'asc' ? 'desc' : 'asc';
          } else {
            // New field, default to ascending
            this._sortField = field;
            this._sortDirection = 'asc';
          }
          this._filterAndSortUsers();
          this.render();
        });
      });
    }
    
    // Add user button
    const addUserBtn = this.shadowObj.querySelector('.add-user-btn');
    if (addUserBtn) {
      addUserBtn.addEventListener('click', this._handleAddUser);
    }
  }

  // Method to fetch users data
  _fetchUsersData = async () => {
    console.log("Fetching users data from:", this.url);
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
        console.log("Authentication required for users list access");
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
        this._errorMessage = response.error_message || "Failed to load users data";
        this.usersData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._error = false;
      this._errorMessage = null;
      
      // Remove hashed_password from all users for security
      const usersData = response.data.map(user => {
        const userData = { ...user };
        if (userData.hashed_password) {
          delete userData.hashed_password;
        }
        return userData;
      });
      
      this.usersData = usersData;
      console.log("Users data fetched successfully, count:", this.usersData.length);
      
      // Filter and sort the users
      this._filterAndSortUsers();
      
      // Render with the new data
      this.render();

    } catch (error) {
      console.error("Error fetching users data:", error);
      this._loading = false;
      this._error = true;
      this._errorMessage = "An error occurred while loading users data";
      this.usersData = null;
      this.render();
    }
  };

  // Filter and sort users based on current settings
  _filterAndSortUsers = () => {
    if (!this.usersData) {
      this._filteredUsers = [];
      return;
    }
    
    // First filter by search term
    this._filteredUsers = this.usersData.filter(user => {
      if (!this._searchTerm) return true;
      
      // Search in name, email, role, and ID
      return (
        (user.name && user.name.toLowerCase().includes(this._searchTerm)) ||
        (user.email && user.email.toLowerCase().includes(this._searchTerm)) ||
        (user.role && user.role.toLowerCase().includes(this._searchTerm)) ||
        (user.id && user.id.toLowerCase().includes(this._searchTerm))
      );
    });
    
    // Then sort by the selected field
    this._filteredUsers.sort((a, b) => {
      let aValue = a[this._sortField] || '';
      let bValue = b[this._sortField] || '';
      
      // Handle null values
      if (aValue === null) aValue = '';
      if (bValue === null) bValue = '';
      
      // String comparison
      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }
      
      // Boolean comparison
      if (typeof aValue === 'boolean') {
        if (aValue === bValue) return 0;
        if (this._sortDirection === 'asc') {
          return aValue ? -1 : 1;
        } else {
          return aValue ? 1 : -1;
        }
      }
      
      // Numeric or string comparison
      if (this._sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  };

  // Handle add user action
  _handleAddUser = () => {
    console.log("Add user button clicked");
    // Navigate to the add user page
    if (this.app && typeof this.app.navigate === 'function') {
      this.app.navigate('/users/add');
    } else {
      // Fallback: use window.location
      window.location.href = '/users/add';
    }
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
        ${!this._loading && !this._error && this.usersData ? this._getUsersListHTML() : ''}
      </div>
    `;
  };

  _getUsersListHTML = () => {
    return /* html */ `
      <div class="users-container">
        <div class="users-header">
          <div class="header-left">
            <h1 class="users-title">Users</h1>
            <div class="users-count">
              <span class="count">${this._filteredUsers.length}</span>
              <span class="total-text">${this._filteredUsers.length === 1 ? 'user' : 'users'}</span>
              ${this._searchTerm ? `<span class="filter-text">(filtered from ${this.usersData.length})</span>` : ''}
            </div>
          </div>
          <button class="add-user-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="8.5" cy="7" r="4"></circle>
              <line x1="20" y1="8" x2="20" y2="14"></line>
              <line x1="23" y1="11" x2="17" y2="11"></line>
            </svg>
            Add User
          </button>
        </div>
        
        <div class="search-bar">
          <div class="search-input-wrapper">
            <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input type="text" class="search-input" placeholder="Search users by name, email, or role" value="${this._searchTerm}">
          </div>
        </div>
        
        <div class="users-table-wrapper">
          <table class="users-table">
            <thead>
              <tr>
                <th class="sort-header" data-field="name">
                  <div class="th-content">
                    <span>Name</span>
                    ${this._getSortIcon('name')}
                  </div>
                </th>
                <th class="sort-header" data-field="email">
                  <div class="th-content">
                    <span>Email</span>
                    ${this._getSortIcon('email')}
                  </div>
                </th>
                <th class="sort-header" data-field="role">
                  <div class="th-content">
                    <span>Role</span>
                    ${this._getSortIcon('role')}
                  </div>
                </th>
                <th class="sort-header" data-field="is_active">
                  <div class="th-content">
                    <span>Status</span>
                    ${this._getSortIcon('is_active')}
                  </div>
                </th>
                <th class="actions-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this._filteredUsers.length > 0 ? 
                this._filteredUsers.map(user => this._getUserRowHTML(user)).join('') : 
                `<tr class="empty-row"><td colspan="5">No users found</td></tr>`
              }
            </tbody>
          </table>
        </div>
      </div>
    `;
  };

  _getUserRowHTML = (user) => {
    return /* html */ `
      <tr class="user-row">
        <td class="user-name-cell">
          <div class="user-info">
            <div class="user-avatar">
              ${this._getInitialsAvatar(user.name || user.email)}
            </div>
            <span class="user-name">${user.name || 'Unnamed User'}</span>
          </div>
        </td>
        <td class="user-email-cell">
          <div class="centered-content">${user.email}</div>
        </td>
        <td class="user-role-cell">
          <div class="centered-content">
            <span class="role-badge ${user.role}">${this._formatRole(user.role)}</span>
          </div>
        </td>
        <td class="user-status-cell">
          <div class="centered-content">
            <span class="status-badge ${user.is_active ? 'active' : 'inactive'}">
              ${user.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </td>
        <td class="user-actions-cell">
          <div class="actions-buttons">
            <button class="action-btn edit-btn" data-user-id="${user.id}" title="Edit User">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button class="action-btn delete-btn" data-user-id="${user.id}" title="Delete User">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 6h18"></path>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <line x1="10" y1="11" x2="10" y2="17"></line>
                <line x1="14" y1="11" x2="14" y2="17"></line>
              </svg>
            </button>
          </div>
        </td>
      </tr>
    `;
  };

  _getSortIcon = (field) => {
    if (this._sortField !== field) {
      return /* html */ `
        <svg class="sort-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 15l5 5 5-5"></path>
          <path d="M7 9l5-5 5 5"></path>
        </svg>
      `;
    }
    
    if (this._sortDirection === 'asc') {
      return /* html */ `
        <svg class="sort-icon active" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 11l5-5 5 5"></path>
          <path d="M7 17l5-5 5 5"></path>
        </svg>
      `;
    } else {
      return /* html */ `
        <svg class="sort-icon active" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M7 7l5 5 5-5"></path>
          <path d="M7 13l5 5 5-5"></path>
        </svg>
      `;
    }
  };

  _getInitialsAvatar = (text) => {
    if (!text) return '';
    
    // For email, use first letter and domain first letter
    if (text.includes('@')) {
      const [username, domain] = text.split('@');
      return this._createAvatarHTML(username[0].toUpperCase() + domain[0].toUpperCase(), text);
    }
    
    // For name, use first letter of first and last name
    const nameParts = text.split(' ');
    let initials = nameParts[0][0].toUpperCase();
    
    if (nameParts.length > 1) {
      initials += nameParts[nameParts.length - 1][0].toUpperCase();
    }
    
    return this._createAvatarHTML(initials, text);
  };
  
  _createAvatarHTML = (initials, seed) => {
    // Generate a consistent color based on the name/email
    const hue = this._getHashCode(seed) % 360;
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
      <p>${this._errorMessage || 'An error occurred while loading users data.'}</p>
      <button class="retry-btn" onclick="this._fetchUsersData()">
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
      <p>Loading users data...</p>
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
      
      .container {
        max-width: 1200px;
        margin: 0 auto;
        padding: 2rem 1rem;
      }
      
      /* Users Container */
      .users-container {
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }
      
      .users-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
      }
      
      .header-left {
        display: flex;
        align-items: flex-start;
        flex-direction: column;
        gap: 0.25rem;
      }
      
      .users-title {
        font-family: var(--font-main, 'Inter', sans-serif);
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
        color: var(--title-color);
      }
      
      .users-count {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        color: var(--gray-color);
        font-size: 0.875rem;
      }
      
      .count {
        font-weight: 600;
        color: var(--accent-color);
      }
      
      .add-user-btn {
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
      
      .add-user-btn:hover {
        background-color: var(--accent-alt);
      }
      
      /* Search Bar */
      .search-bar {
        margin-bottom: 1rem;
      }
      
      .search-input-wrapper {
        position: relative;
        max-width: 400px;
      }
      
      .search-icon {
        position: absolute;
        left: 0.75rem;
        top: 50%;
        transform: translateY(-50%);
        color: var(--gray-color);
      }
      
      .search-input {
        width: 100%;
        padding: 0.75rem 1rem 0.75rem 2.5rem;
        border-radius: 6px;
        border: var(--input-border);
        background-color: var(--background);
        color: var(--text-color);
        font-size: 0.875rem;
        transition: border-color 0.2s ease;
      }
      
      .search-input:focus {
        border-color: var(--accent-color);
        outline: none;
      }
      
      /* Users Table */
      .users-table-wrapper {
        overflow-x: auto;
        border-radius: 8px;
        box-shadow: var(--card-box-shadow-alt);
      }
      
      .users-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
      }
      
      .users-table th, 
      .users-table td {
        padding: 1rem;
        text-align: left;
        border-bottom: var(--border);
      }
      
      /* Center all columns except the first one */
      .users-table th:not(:first-child),
      .users-table td:not(:first-child) {
        text-align: center;
      }
      
      .users-table thead {
        background-color: var(--hover-background);
      }
      
      .users-table th {
        font-weight: 600;
        color: var(--gray-color);
        white-space: nowrap;
      }
      
      .th-content {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        justify-content: center;
      }
      
      .users-table th:first-child .th-content {
        justify-content: flex-start;
      }
      
      .sort-icon {
        opacity: 0.5;
      }
      
      .sort-icon.active {
        opacity: 1;
        color: var(--accent-color);
      }
      
      .users-table tbody tr:hover {
        background-color: var(--hover-background);
      }
      
      .empty-row td {
        text-align: center;
        color: var(--gray-color);
        padding: 2rem 1rem;
      }
      
      /* User Row Styles */
      .user-info {
        display: flex;
        align-items: center;
        gap: 0.75rem;
      }
      
      .user-avatar {
        flex-shrink: 0;
      }
      
      .avatar-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
      }
      
      .avatar-initials {
        font-size: 0.8rem;
        color: var(--white-color);
      }
      
      .user-name {
        font-weight: 500;
      }
      
      .role-badge, .status-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 500;
        text-align: center;
      }
      
      .centered-content {
        display: flex;
        justify-content: center;
        align-items: center;
      }
      
      .role-badge.admin {
        background-color: var(--tab-background);
        color: var(--accent-color);
      }
      
      .role-badge.member {
        background-color: rgba(69, 162, 158, 0.13);
        color: #45a29e;
      }
      
      .status-badge.active {
        background-color: rgba(44, 182, 125, 0.13);
        color: var(--success-color);
      }
      
      .status-badge.inactive {
        background-color: rgba(239, 71, 111, 0.13);
        color: var(--error-color);
      }
      
      /* Action Buttons */
      .actions-buttons {
        display: flex;
        gap: 0.5rem;
        justify-content: center;
      }
      
      .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 4px;
        background-color: transparent;
        border: var(--action-border);
        color: var(--gray-color);
        cursor: pointer;
        transition: all 0.2s ease;
      }
      
      .action-btn:hover {
        background-color: var(--hover-background);
        color: var(--text-color);
      }
      
      .edit-btn:hover {
        border-color: var(--accent-color);
        color: var(--accent-color);
      }
      
      .delete-btn:hover {
        border-color: var(--error-color);
        color: var(--error-color);
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
        .users-header {
          flex-direction: column;
          align-items: flex-start;
          gap: 1rem;
        }
        
        .add-user-btn {
          align-self: stretch;
          justify-content: center;
        }
        
        .users-table th:nth-child(4),
        .users-table td:nth-child(4) {
          display: none;
        }
      }
      
      @media (max-width: 480px) {
        .users-table th:nth-child(3),
        .users-table td:nth-child(3) {
          display: none;
        }
      }
    </style>
    `;
  };
}