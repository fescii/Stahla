export default class EditProfilePopup extends HTMLElement {
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
    const form = this.shadowObj.querySelector('#edit-profile-form');
    if (form) {
      form.addEventListener('submit', this._handleSubmit.bind(this));
    }

    // Picture upload
    const pictureInput = this.shadowObj.querySelector('#picture-input');
    const uploadBtn = this.shadowObj.querySelector('.upload-picture-btn');
    if (pictureInput && uploadBtn) {
      uploadBtn.addEventListener('click', () => pictureInput.click());
      pictureInput.addEventListener('change', this._handlePictureUpload.bind(this));
    }

    // Remove picture
    const removePictureBtn = this.shadowObj.querySelector('.remove-picture-btn');
    if (removePictureBtn) {
      removePictureBtn.addEventListener('click', this._handleRemovePicture.bind(this));
    }

    // Bio character count
    const bioInput = this.shadowObj.querySelector('#bio');
    if (bioInput) {
      bioInput.addEventListener('input', (e) => {
        const charCount = this.shadowObj.querySelector('.char-count');
        if (charCount) {
          charCount.textContent = `${e.target.value.length}/500`;
        }
      });

      // Initialize character count
      const charCount = this.shadowObj.querySelector('.char-count');
      if (charCount) {
        charCount.textContent = `${bioInput.value.length}/500`;
      }
    }
  }

  _handleSubmit = async (e) => {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const name = formData.get('name')?.trim();
    const bio = formData.get('bio')?.trim();

    if (!name || name.length < 2) {
      this._showError('Name must be at least 2 characters long');
      return;
    }

    this._updateSubmitButton(true);
    this._updateErrorDisplay(false); // Clear any existing errors

    try {
      // Update name and bio in a single request
      const profileResult = await this.api.patch('/auth/me/profile', {
        content: 'json',
        body: {
          name: name,
          bio: bio || null
        }
      });

      if (!profileResult.success) {
        throw new Error(profileResult.message || 'Failed to update profile');
      }

      this._updateSubmitButton(false);
      this._showSuccess();

      // Close popup after delay and refresh user data
      setTimeout(() => {
        if (this.app && typeof this.app.updateUserData === 'function') {
          this.app.updateUserData(profileResult.data);
        }
        this.remove();
      }, 1500);

    } catch (error) {
      this._updateSubmitButton(false);
      this._showError(error.message || 'An error occurred while updating your profile');
    }
  };

  _handlePictureUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      this._showError('Please select a valid image file (JPEG, PNG, GIF, or WebP)');
      return;
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      this._showError('Image must be smaller than 5MB');
      return;
    }

    // Show loading state only on picture container
    const pictureContainer = this.shadowObj.querySelector('.picture-container');
    const uploadBtn = this.shadowObj.querySelector('.upload-picture-btn');
    const removeBtn = this.shadowObj.querySelector('.remove-picture-btn');

    if (pictureContainer) {
      pictureContainer.innerHTML = '<div class="picture-loading"></div>';
    }
    if (uploadBtn) uploadBtn.disabled = true;
    if (removeBtn) removeBtn.disabled = true;

    try {
      const formData = new FormData();
      formData.append('file', file);

      const result = await this.api.post(`/auth/users/${this.user.id}/picture`, {
        content: 'form',
        body: formData
      });

      if (result.success) {
        this.user = result.data;
        // Update only the picture container
        this._updatePictureDisplay();
      } else {
        throw new Error(result.message || 'Failed to upload picture');
      }

    } catch (error) {
      this._showError(error.message || 'Failed to upload picture');
      // Restore picture display on error
      this._updatePictureDisplay();
    }
  };

  _handleRemovePicture = async () => {
    if (!this.user.picture) return;

    // Show loading state only on picture container
    const pictureContainer = this.shadowObj.querySelector('.picture-container');
    const uploadBtn = this.shadowObj.querySelector('.upload-picture-btn');
    const removeBtn = this.shadowObj.querySelector('.remove-picture-btn');

    if (pictureContainer) {
      pictureContainer.innerHTML = '<div class="picture-loading"></div>';
    }
    if (uploadBtn) uploadBtn.disabled = true;
    if (removeBtn) removeBtn.disabled = true;

    try {
      const result = await this.api.delete(`/auth/users/${this.user.id}/picture`);

      if (result.success) {
        this.user = result.data;
        // Update only the picture container
        this._updatePictureDisplay();
      } else {
        throw new Error(result.message || 'Failed to remove picture');
      }

    } catch (error) {
      this._showError(error.message || 'Failed to remove picture');
      // Restore picture display on error
      this._updatePictureDisplay();
    }
  };

  _updatePictureDisplay() {
    const pictureContainer = this.shadowObj.querySelector('.picture-container');
    const pictureActions = this.shadowObj.querySelector('.picture-actions');
    const uploadBtn = this.shadowObj.querySelector('.upload-picture-btn');
    const removeBtn = this.shadowObj.querySelector('.remove-picture-btn');

    if (pictureContainer) {
      pictureContainer.innerHTML = this.user.picture
        ? `<img src="${this.user.picture}" alt="Profile picture" class="profile-image">`
        : this._getInitialsAvatar(this.user.name || this.user.email);
    }

    // Re-enable buttons
    if (uploadBtn) uploadBtn.disabled = false;
    if (removeBtn) removeBtn.disabled = false;

    // Update picture actions - add/remove the remove button
    if (pictureActions) {
      const hasRemoveBtn = pictureActions.querySelector('.remove-picture-btn');
      if (this.user.picture && !hasRemoveBtn) {
        // Add remove button
        pictureActions.insertAdjacentHTML('beforeend', `
          <button type="button" class="remove-picture-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18"></path>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            Remove
          </button>
        `);
        // Re-attach event listener for new remove button
        const newRemoveBtn = pictureActions.querySelector('.remove-picture-btn');
        if (newRemoveBtn) {
          newRemoveBtn.addEventListener('click', this._handleRemovePicture.bind(this));
        }
      } else if (!this.user.picture && hasRemoveBtn) {
        // Remove the remove button
        hasRemoveBtn.remove();
      }
    }
  }

  _updateSubmitButton(loading = false) {
    const submitBtn = this.shadowObj.querySelector('.action.next');
    if (submitBtn) {
      submitBtn.disabled = loading;
      submitBtn.innerHTML = loading
        ? this._getLoadingSpinner() + 'Updating...'
        : 'Update';
    }
  }

  _updateErrorDisplay(show = false, message = '') {
    const existingError = this.shadowObj.querySelector('.error-alert');
    if (existingError) {
      existingError.remove();
    }

    if (show && message) {
      const form = this.shadowObj.querySelector('#edit-profile-form');
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
  }

  _showSuccess() {
    const form = this.shadowObj.querySelector('#edit-profile-form');
    if (form) {
      const successHTML = `
        <div class="success-alert">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"></polyline>
          </svg>
          <span>Profile updated successfully!</span>
        </div>
      `;
      form.insertAdjacentHTML('afterbegin', successHTML);
    }
  }

  _showSuccess() {
    const form = this.shadowObj.querySelector('#edit-profile-form');
    if (form) {
      const successHTML = `
        <div class="success-alert">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20,6 9,17 4,12"></polyline>
          </svg>
          <span>Profile updated successfully!</span>
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

    const form = this.shadowObj.querySelector('#edit-profile-form');
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
        ${this.getEditProfileContent()}
      </section>
      ${this.getStyles()}
    `;
  }

  getEditProfileContent() {
    if (this._success) {
      return `
        <div class="welcome">
          <div class="success-container">
            <svg class="success-icon" xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9 12l2 2 4-4"></path>
            </svg>
            <h2>Profile Updated Successfully</h2>
            <p>Your profile information has been updated.</p>
          </div>
        </div>
      `;
    }

    return `
      <div class="welcome">
        <div class="head">
          <h2 class="consent">Edit Profile</h2>
          <button class="close-btn" type="button">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        
        ${this._error ? this._getErrorHTML() : ''}
        
        <div class="profile-picture-section">
          <div class="picture-container">
            ${this.user.picture
        ? `<img src="${this.user.picture}" alt="Profile picture" class="profile-image">`
        : this._getInitialsAvatar(this.user.name || this.user.email)
      }
            ${this._loading ? '<div class="picture-loading"></div>' : ''}
          </div>
          <div class="picture-actions">
            <button type="button" class="upload-picture-btn">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7"></path>
                <line x1="16" y1="5" x2="22" y2="5"></line>
                <line x1="19" y1="2" x2="19" y2="8"></line>
              </svg>
              Upload Photo
            </button>
            ${this.user.picture ? `
              <button type="button" class="remove-picture-btn">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M3 6h18"></path>
                  <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
                Remove
              </button>
            ` : ''}
          </div>
          <input type="file" id="picture-input" accept="image/*" style="display: none;">
        </div>

        <form id="edit-profile-form" class="fields">
          <div class="field">
            <div class="input-group">
              <label for="name">Full Name</label>
              <input type="text" id="name" name="name" value="${this.user.name || ''}" placeholder="Enter your full name" required>
            </div>
          </div>
          
          <div class="field">
            <div class="input-group">
              <label for="bio">Bio</label>
              <textarea id="bio" name="bio" placeholder="Tell us about yourself..." maxlength="500">${this.user.bio || ''}</textarea>
              <span class="char-count">0/500</span>
            </div>
          </div>
          
          <div class="actions">
            <button type="button" class="action cancel-btn">Cancel</button>
            <button type="submit" class="action next" ${this._loading ? 'disabled' : ''}>
              ${this._loading ? this._getLoadingSpinner() + 'Updating...' : 'Update'}
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
          font-size: 1.6rem;
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

        .profile-picture-section {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 16px;
          margin-bottom: 24px;
          width: 100%;
        }

        .picture-container {
          position: relative;
          width: 120px;
          height: 120px;
        }

        .profile-image {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          object-fit: cover;
          border: 3px solid var(--border);
        }

        .avatar-circle {
          width: 120px;
          height: 120px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: 600;
          font-size: 2.5rem;
        }

        .picture-loading {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(255, 255, 255, 0.8);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .picture-actions {
          display: flex;
          gap: 12px;
          align-items: center;
        }

        .upload-picture-btn,
        .remove-picture-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          border: none;
          border-radius: 10px;
          font-family: var(--font-main), sans-serif;
          font-size: 0.9rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .upload-picture-btn {
          background: var(--accent-linear);
          color: var(--white-color);
        }

        .upload-picture-btn:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 96, 223, 0.3);
        }

        .remove-picture-btn {
          background: var(--error-background);
          color: var(--error-color);
          border: 1px solid rgba(236, 75, 25, 0.2);
        }

        .remove-picture-btn:hover {
          background: rgba(236, 75, 25, 0.15);
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

        form.fields .field input,
        form.fields .field textarea {
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
        }

        form.fields .field textarea {
          min-height: 100px;
          resize: vertical;
          font-family: var(--font-text), sans-serif;
          line-height: 1.5;
        }

        form.fields .field input:focus,
        form.fields .field textarea:focus {
          border: var(--input-border-focus);
          box-shadow: 0 0 0 3px rgba(0, 96, 223, 0.1);
          transform: translateY(-1px);
        }

        .char-count {
          font-size: 0.85rem;
          color: var(--gray-color);
          align-self: flex-end;
          margin-top: 4px;
        }

        form.fields .actions {
          display: flex;
          font-family: var(--font-main), sans-serif;
          width: 100%;
          flex-flow: row;
          align-items: center;
          justify-content: end;
          gap: 35px;
          margin: 20px 0 0;
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
          padding: 12px 20px;
          min-width: 100px;
          width: 150px;
          position: relative;
          border-radius: 15px;
          -webkit-border-radius: 15px;
          -moz-border-radius: 15px;
        }

        form.fields .actions > .action.cancel-btn {
          background: var(--gray-background);
          color: var(--text-color);
          border: none;
        }

        form.fields .actions > .action.next {
          background: var(--accent-color);
          color: var(--white-color);
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
            font-size: 1.4rem;
          }

          .picture-actions {
            flex-direction: column;
            width: 100%;
          }

          .upload-picture-btn,
          .remove-picture-btn {
            width: 100%;
            justify-content: center;
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
