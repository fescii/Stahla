import AccessPopup from "./access.js"
import DeletePopup from "./delete.js"
import EditProfilePopup from "./edit/profile.js"
import EditUserAdminPopup from "./edit/useradmin.js"

export default function popups() {
  // Register popups
  customElements.define("delete-popup", DeletePopup);
  customElements.define("access-popup", AccessPopup);
  customElements.define("edit-profile-popup", EditProfilePopup);
  customElements.define("edit-user-admin-popup", EditUserAdminPopup);
}