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
    this._searchTerm = "";
    this._sortField = "name";
    this._sortDirection = "asc";
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
    const searchInput = this.shadowObj.querySelector(".search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this._searchTerm = e.target.value.toLowerCase();
        this._filterAndSortUsers();
        this.render();
      });
    }

    // Sort headers
    const sortHeaders = this.shadowObj.querySelectorAll(".sort-header");
    if (sortHeaders) {
      sortHeaders.forEach((header) => {
        header.addEventListener("click", () => {
          const field = header.dataset.field;
          if (this._sortField === field) {
            // Toggle direction if already sorting by this field
            this._sortDirection =
              this._sortDirection === "asc" ? "desc" : "asc";
          } else {
            // New field, default to ascending
            this._sortField = field;
            this._sortDirection = "asc";
          }
          this._filterAndSortUsers();
          this.render();
        });
      });
    }

    // Add user button
    const addUserBtn = this.shadowObj.querySelector(".add-user-btn");
    if (addUserBtn) {
      addUserBtn.addEventListener("click", this._handleAddUser);
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
        this._errorMessage =
          response.error_message || "Failed to load users data";
        this.usersData = null;
        this.render();
        return;
      }

      this._loading = false;
      this._error = false;
      this._errorMessage = null;

      // Remove hashed_password from all users for security
      const usersData = response.data.map((user) => {
        const userData = { ...user };
        if (userData.hashed_password) {
          delete userData.hashed_password;
        }
        return userData;
      });

      this.usersData = usersData;
      console.log(
        "Users data fetched successfully, count:",
        this.usersData.length
      );

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
    this._filteredUsers = this.usersData.filter((user) => {
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
      let aValue = a[this._sortField] || "";
      let bValue = b[this._sortField] || "";

      // Handle null values
      if (aValue === null) aValue = "";
      if (bValue === null) bValue = "";

      // String comparison
      if (typeof aValue === "string") {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      // Boolean comparison
      if (typeof aValue === "boolean") {
        if (aValue === bValue) return 0;
        if (this._sortDirection === "asc") {
          return aValue ? -1 : 1;
        } else {
          return aValue ? 1 : -1;
        }
      }

      // Numeric or string comparison
      if (this._sortDirection === "asc") {
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
    if (this.app && typeof this.app.navigate === "function") {
      this.app.navigate("/users/add");
    } else {
      // Fallback: use window.location
      window.location.href = "/users/add";
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
        ${this._loading ? this.getLoader() : ""}
        ${!this._loading && this._error ? this._getErrorHTML() : ""}
        ${!this._loading && !this._error && this.usersData
        ? this._getUsersListHTML()
        : ""
      }
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
              <span class="total-text">${this._filteredUsers.length === 1 ? "user" : "users"
      }</span>
              ${this._searchTerm
        ? `<span class="filter-text">(filtered from ${this.usersData.length})</span>`
        : ""
      }
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
            <input type="text" class="search-input" placeholder="Search users by name, email, or role" value="${this._searchTerm
      }">
          </div>
        </div>
        
        <div class="users-table-wrapper">
          <table class="users-table">
            <thead>
              <tr>
                <th class="sort-header" data-field="name">
                  <div class="th-content">
                    <span>Name</span>
                    ${this._getSortIcon("name")}
                  </div>
                </th>
                <th class="sort-header" data-field="email">
                  <div class="th-content">
                    <span>Email</span>
                    ${this._getSortIcon("email")}
                  </div>
                </th>
                <th class="sort-header" data-field="role">
                  <div class="th-content">
                    <span>Role</span>
                    ${this._getSortIcon("role")}
                  </div>
                </th>
                <th class="sort-header" data-field="is_active">
                  <div class="th-content">
                    <span>Status</span>
                    ${this._getSortIcon("is_active")}
                  </div>
                </th>
                <th class="actions-header">Actions</th>
              </tr>
            </thead>
            <tbody>
              ${this._filteredUsers.length > 0
        ? this._filteredUsers
          .map((user) => this._getUserRowHTML(user))
          .join("")
        : `<tr class="empty-row"><td colspan="5">No users found</td></tr>`
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
            <span class="user-name">${user.name || "Unnamed User"}</span>
          </div>
        </td>
        <td class="user-email-cell">
          <div class="centered-content">${user.email}</div>
        </td>
        <td class="user-role-cell">
          <div class="centered-content">
            <span class="role-badge ${user.role || "user"}">
              ${this._formatRole(user.role)}
            </span>
          </div>
        </td>
        <td class="user-status-cell">
          <div class="centered-content">
            <span class="status-badge ${user.is_active ? "active" : "inactive"
      }">
              ${user.is_active ? "Active" : "Inactive"}
            </span>
          </div>
        </td>
        <td class="user-actions-cell">
          <div class="actions-buttons">
            <button class="action-btn edit-btn" data-user-id="${user.id
      }" title="Edit User">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
              </svg>
            </button>
            <button class="action-btn delete-btn" data-user-id="${user.id
      }" title="Delete User">
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

    if (this._sortDirection === "asc") {
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
    if (!text) return "";

    // For email, use first letter and domain first letter
    if (text.includes("@")) {
      const [username, domain] = text.split("@");
      return this._createAvatarHTML(
        username[0].toUpperCase() + domain[0].toUpperCase(),
        text
      );
    }

    // For name, use first letter of first and last name
    const nameParts = text.split(" ");
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
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }

    return Math.abs(hash);
  };

  _formatRole = (role) => {
    if (!role) return "User";
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
      <h3>Unable to Load Users</h3>
      <p>${this._errorMessage ||
      "An error occurred while loading users data. Please try again or contact support if the problem persists."
      }</p>
      <button class="retry-btn" onclick="this._fetchUsersData()">
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
      will-change: transform, opacity;
      }
      
      /* Users Container */
      .users-container {
      display: flex;
      flex-direction: column;
      gap: 0;
      border-radius: 16px;
      padding: 1.75rem 0;
      transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
      will-change: transform;
      }
      
      .users-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 1.5rem;
      will-change: transform;
      }
      
      .header-left {
      display: flex;
      align-items: flex-start;
      flex-direction: column;
      gap: 0.5rem;
      }
      
      .users-title {
      font-family: var(--font-main, 'Inter', sans-serif);
      font-size: 1.8rem;
      font-weight: 800;
      margin: 0;
      color: var(--title-color);
      position: relative;
      letter-spacing: -0.01em;
      }
      
      .users-title::after {
      content: '';
      position: absolute;
      bottom: -8px;
      left: 0;
      width: 45px;
      height: 4px;
      background: linear-gradient(90deg, var(--accent-color) 0%, rgba(0, 96, 223, 0.6) 100%);
      border-radius: 4px;
      transition: width 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: width;
      }
      
      .users-container:hover .users-title::after {
      width: 60px;
      }
      
      .users-count {
      display: flex;
      align-items: center;
      gap: 0.3rem;
      color: var(--gray-color);
      font-size: 0.875rem;
      margin-top: 0.5rem;
      opacity: 0.9;
      }
      
      .count {
      font-weight: 700;
      color: var(--accent-color);
      background: rgba(0, 96, 223, 0.08);
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      margin-right: 0.1rem;
      }
      
      .filter-text {
      opacity: 0.75;
      font-size: 0.8rem;
      font-style: italic;
      }
      
      .add-user-btn {
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
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      box-shadow: 0 4px 12px rgba(0, 96, 223, 0.25);
      position: relative;
      overflow: hidden;
      will-change: transform, box-shadow;
      }
      
      .add-user-btn::after {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.2));
      transform: translateY(100%);
      transition: transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
      will-change: transform;
      }
      
      .add-user-btn:hover {
      transform: translateY(-2px) scale(1.02);
      box-shadow: 0 6px 16px rgba(0, 96, 223, 0.35);
      }
      
      .add-user-btn:hover::after {
      transform: translateY(0);
      }
      
      .add-user-btn:active {
      transform: translateY(0) scale(0.98);
      box-shadow: 0 2px 8px rgba(0, 96, 223, 0.2);
      transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
      }
      
      .add-user-btn svg {
      transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform;
      }
      
      .add-user-btn:hover svg {
      transform: translateY(-1px);
      }
      
      /* Search Bar */
      .search-bar {
      margin: 0.5rem 0 1.5rem;
      position: relative;
      }
      
      .search-input-wrapper {
      position: relative;
      max-width: 400px;
      transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
      border-radius: 12px;
      will-change: transform, max-width;
      }
      
      .search-input-wrapper:focus-within {
      max-width: 500px;
      transform: translateY(-2px);
      }
      
      .search-icon {
      position: absolute;
      left: 1rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--gray-color);
      transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform, color;
      }
      
      .search-input-wrapper:focus-within .search-icon {
      color: var(--accent-color);
      transform: translateY(-50%) scale(1.1);
      }
      
      .search-input {
      width: 100%;
      padding: 0.95rem 1rem 0.95rem 2.75rem;
      border-radius: 12px;
      border: var(--border);
      background-color: var(--background);
      color: var(--text-color);
      font-size: 0.95rem;
      transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
      will-change: transform, box-shadow, border-color;
      }
      
      .search-input:focus {
      border-color: var(--accent-color);
      outline: none;
      box-shadow: 0 4px 12px rgba(0, 96, 223, 0.12);
      }
      
      /* Users Table */
      .users-table-wrapper {
        overflow-x: auto;
        border-radius: 12px;
        background-color: var(--background);
        transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
        scrollbar-width: 0;
      }
      
      .users-table-wrapper::-webkit-scrollbar {
      height: 8px;
      }
      
      .users-table-wrapper::-webkit-scrollbar-track {
      background: rgba(0, 0, 0, 0.02);
      border-radius: 20px;
      }
      
      .users-table-wrapper::-webkit-scrollbar-thumb {
      background: rgba(0, 0, 0, 0.1);
      border-radius: 20px;
      transition: background-color 0.3s ease;
      }
      
      .users-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      font-size: 0.95rem;
      }
      
      .users-table th, 
      .users-table td {
      padding: 1rem 1.25rem;
      text-align: left;
      border-bottom: var(--border);
      transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
      }
      
      .users-table tr:last-child td {
      border-bottom: none;
      }
      
      /* Center all columns except the first one */
      .users-table th:not(:first-child),
      .users-table td:not(:first-child) {
      text-align: center;
      }
      
      .users-table thead {
      background-color: rgba(0, 0, 0, 0.02);
      }
      
      .users-table thead tr th:first-child {
      border-top-left-radius: 12px;
      }
      
      .users-table thead tr th:last-child {
      border-top-right-radius: 12px;
      }
      
      .users-table th {
      font-weight: 700;
      color: var(--title-color);
      white-space: nowrap;
      padding: 1.25rem;
      position: sticky;
      top: 0;
      background-color: rgba(0, 0, 0, 0.02);
      z-index: 10;
      border-bottom: var(--border);
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
      letter-spacing: 0.01em;
      font-size: 0.85rem;
      text-transform: uppercase;
      }
      
      .th-content {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      cursor: pointer;
      justify-content: center;
      transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
      padding: 0.5rem;
      border-radius: 6px;
      will-change: transform, background-color, color;
      }
      
      .th-content:hover {
      color: var(--accent-color);
      background-color: rgba(0, 0, 0, 0.03);
      transform: translateY(-1px);
      }
      
      .users-table th:first-child .th-content {
      justify-content: flex-start;
      margin-left: -0.5rem;
      }
      
      .sort-icon {
      opacity: 0.4;
      transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform, opacity;
      }
      
      .sort-icon.active {
      opacity: 1;
      color: var(--accent-color);
      transform: scale(1.1);
      }
      
      .th-content:hover .sort-icon:not(.active) {
      opacity: 0.7;
      transform: scale(1.05);
      }
      
      .users-table tbody tr {
      transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
      cursor: default;
      position: relative;
      will-change: transform, background-color;
      }
      
      .users-table tbody tr:hover {
      background-color: rgba(0, 0, 0, 0.02);
      transform: translateX(4px) scale(1.01);
      z-index: 1;
      }
      
      .empty-row td {
      text-align: center;
      color: var(--gray-color);
      padding: 4rem 1rem;
      background-color: var(--background);
      border-radius: 0 0 12px 12px;
      font-size: 1.05rem;
      font-weight: 500;
      }
      
      /* User Row Styles */
      .user-info {
      display: flex;
      align-items: center;
      gap: 1rem;
      }
      
      .user-avatar {
      flex-shrink: 0;
      transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform;
      }
      
      .user-row:hover .user-avatar {
      transform: scale(1.08);
      }
      
      .avatar-circle {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform;
      }
      
      .user-row:hover .avatar-circle {
      transform: translateY(-2px);
      }
      
      .avatar-initials {
      font-size: 0.95rem;
      color: var(--white-color);
      font-weight: 700;
      letter-spacing: -0.5px;
      }
      
      .user-name {
      font-weight: 600;
      font-size: 1.05rem;
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      color: var(--title-color);
      letter-spacing: -0.01em;
      will-change: transform, color;
      }
      
      .user-row:hover .user-name {
      color: var(--accent-color);
      transform: translateX(2px);
      }
      
      .user-email-cell {
      font-size: 0.9rem;
      color: var(--gray-color);
      }
      
      .role-badge, .status-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 0.35rem 0.9rem;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      text-align: center;
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      min-width: 90px;
      box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06);
      will-change: transform, box-shadow;
      }
      
      .user-row:hover .role-badge,
      .user-row:hover .status-badge {
      transform: scale(1.08) translateY(-1px);
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
      }
      
      .centered-content {
      display: flex;
      justify-content: center;
      align-items: center;
      }
      
      .role-badge.admin {
      background: linear-gradient(135deg, rgba(0, 96, 223, 0.1) 0%, rgba(0, 96, 223, 0.2) 100%);
      color: var(--accent-color);
      border: 1px solid rgba(0, 96, 223, 0.25);
      }
      
      .role-badge.member {
      background: linear-gradient(135deg, rgba(69, 162, 158, 0.1) 0%, rgba(69, 162, 158, 0.2) 100%);
      color: #45a29e;
      border: 1px solid rgba(69, 162, 158, 0.25);
      }
      
      .role-badge.user {
      background: linear-gradient(135deg, rgba(107, 114, 128, 0.1) 0%, rgba(107, 114, 128, 0.2) 100%);
      color: var(--gray-color);
      border: 1px solid rgba(107, 114, 128, 0.25);
      }
      
      .status-badge {
      position: relative;
      padding-left: 1.2rem;
      }
      
      .status-badge::before {
      content: '';
      position: absolute;
      left: 0.6rem;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: box-shadow;
      }
      
      .status-badge.active {
      background: linear-gradient(135deg, rgba(44, 182, 125, 0.1) 0%, rgba(44, 182, 125, 0.2) 100%);
      color: var(--success-color);
      border: 1px solid rgba(44, 182, 125, 0.25);
      }
      
      .status-badge.active::before {
      background-color: var(--success-color);
      box-shadow: 0 0 0 3px rgba(44, 182, 125, 0.2);
      }
      
      .user-row:hover .status-badge.active::before {
      box-shadow: 0 0 0 4px rgba(44, 182, 125, 0.25), 0 0 10px rgba(44, 182, 125, 0.4);
      }
      
      .status-badge.inactive {
      background: linear-gradient(135deg, rgba(239, 71, 111, 0.1) 0%, rgba(239, 71, 111, 0.2) 100%);
      color: var(--error-color);
      border: 1px solid rgba(239, 71, 111, 0.25);
      }
      
      .status-badge.inactive::before {
      background-color: var(--error-color);
      box-shadow: 0 0 0 3px rgba(239, 71, 111, 0.2);
      }
      
      
      /* Action Buttons */
      .actions-buttons {
        display: flex;
        gap: 0.85rem;
        justify-content: center;
      }
      
      .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        border-radius: 10px;
        background-color: transparent;
        border: 1px solid rgba(0, 0, 0, 0.1);
        color: var(--gray-color);
        cursor: pointer;
        transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
        position: relative;
        overflow: hidden;
        will-change: transform, box-shadow, color, border-color;
      }
      
      .action-btn::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 100%;
        height: 100%;
        background-color: currentColor;
        border-radius: 50%;
        opacity: 0;
        transform: translate(-50%, -50%) scale(0);
        transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.4s ease;
        will-change: transform, opacity;
      }
      
      .action-btn:hover::after {
        opacity: 0.12;
        transform: translate(-50%, -50%) scale(2);
      }
      
      .action-btn svg {
      position: relative;
      z-index: 2;
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      will-change: transform;
      }
      
      .action-btn:hover svg {
      transform: scale(1.15);
      }
      
      .action-btn:hover {
      background-color: rgba(0, 0, 0, 0.02);
      color: var(--text-color);
      box-shadow: 0 4px 10px rgba(0, 0, 0, 0.06);
      transform: translateY(-2px);
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
      gap: 1.75rem;
      height: 400px;
      background-color: var(--background);
      border-radius: 16px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 
            0 8px 10px -6px rgba(0, 0, 0, 0.02);
      animation: fadeIn 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
      }
      
      .spinner {
      width: 56px;
      height: 56px;
      border: 4px solid rgba(0, 0, 0, 0.05);
      border-top-color: var(--accent-color);
      border-radius: 50%;
      filter: drop-shadow(0 4px 10px rgba(0, 96, 223, 0.2));
      animation: spin 1.4s cubic-bezier(0.68, -0.15, 0.265, 1.35) infinite;
      will-change: transform;
      }
      
      @keyframes spin {
      0% { transform: rotate(0deg); }
      25% { transform: rotate(90deg); }
      50% { transform: rotate(180deg); }
      75% { transform: rotate(270deg); }
      100% { transform: rotate(360deg); }
      }
      
      @keyframes fadeIn {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
      }
      
      .loader-container p {
      color: var(--gray-color);
      font-size: 1.05rem;
      font-weight: 500;
      background: linear-gradient(90deg, var(--title-color), var(--gray-color));
      background-size: 200% auto;
      background-clip: text;
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      animation: gradientText 2s linear infinite;
      will-change: background-position;
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
      animation: fadeIn 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
      }
      
      .error-state svg {
      color: var(--error-color);
      animation: pulse-error 2s cubic-bezier(0.34, 1.56, 0.64, 1) infinite;
      filter: drop-shadow(0 4px 8px rgba(239, 71, 111, 0.3));
      will-change: transform, opacity;
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
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      margin-top: 0.75rem;
      box-shadow: 0 4px 12px rgba(0, 96, 223, 0.25);
      position: relative;
      overflow: hidden;
      will-change: transform, box-shadow;
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
      transition: transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
      will-change: transform;
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
      transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
      }
      
      .retry-btn svg {
      transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
      animation: none;
      filter: none;
      will-change: transform;
      }
      
      .retry-btn:hover svg {
      transform: rotate(180deg);
      }
      
      /* Empty state styling */
      .empty-row td {
      padding: 4rem 1rem;
      }
      
      .empty-row td::before {
      content: '';
      display: block;
      width: 70px;
      height: 70px;
      margin: 0 auto 1.5rem;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%236b7280' stroke-width='1.25' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='7' r='4'%3E%3C/circle%3E%3Cpath d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'%3E%3C/path%3E%3Cpath d='M12 15 L12 19'%3E%3C/path%3E%3Cpath d='M8 19 L16 19'%3E%3C/path%3E%3C/svg%3E");
      opacity: 0.4;
      transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
      filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.05));
      will-change: opacity, transform;
      }
      
      .empty-row:hover td::before {
      opacity: 0.6;
      transform: scale(1.1);
      }
      
      /* Responsive Design */
      @media (max-width: 900px) {
      .container {
        padding: 1.5rem 0;
      }
      
      .users-container {
        padding: 1.5rem 0;
        gap: 1.5rem;
        border-radius: 14px;
      }
      
      .users-header {
        padding-bottom: 1.25rem;
      }
      
      .users-title {
        font-size: 1.6rem;
      }
      }
      
      @media (max-width: 768px) {
      .users-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 1.25rem;
      }
      
      .add-user-btn {
        align-self: stretch;
        justify-content: center;
      }
      
      .search-input-wrapper {
        max-width: 100%;
      }
      
      .users-table th:nth-child(4),
      .users-table td:nth-child(4) {
        display: none;
      }
      
      .users-table th, 
      .users-table td {
        padding: 1rem;
      }
      
      .action-btn {
        width: 36px;
        height: 36px;
      }
      
      .avatar-circle {
        width: 38px;
        height: 38px;
      }
      }
      
      @media (max-width: 600px) {
      .container {
        padding: 1rem 0.75rem;
      }
      
      .users-container {
        padding: 1.25rem;
        border-radius: 12px;
        box-shadow: 0 8px 20px -8px rgba(0, 0, 0, 0.1);
      }
      
      .users-title {
        font-size: 1.5rem;
      }
      
      .users-table {
        font-size: 0.85rem;
      }
      
      .search-input {
        padding: 0.85rem 1rem 0.85rem 2.75rem;
        border-radius: 10px;
      }
      
      .user-avatar {
        flex-shrink: 0;
      }
      
      .user-info {
        gap: 0.8rem;
      }
      }
      
      @media (max-width: 480px) {
      .users-table th:nth-child(3),
      .users-table td:nth-child(3) {
        display: none;
      }
      
      .actions-buttons {
        gap: 0.5rem;
      }
      
      .users-table th, 
      .users-table td {
        padding: 0.85rem 0.75rem;
      }
      
      .avatar-circle {
        width: 34px;
        height: 34px;
      }
      
      .user-name {
        font-size: 0.9rem;
      }
      
      .user-info {
        gap: 0.7rem;
      }
      
      .error-state h3 {
        font-size: 1.5rem;
      }
      
      .error-state p {
        font-size: 0.95rem;
      }
      
      .users-container {
        padding: 1rem;
      }
      }
    </style>
    `;
  };
}
