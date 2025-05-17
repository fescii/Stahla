import AddUser from "./add.js";
import UserProfile from "./me.js";
import UsersList from "./all.js";

export default function users() {
  // Register the user profile component
  customElements.define("user-profile", UserProfile);
  customElements.define("users-list", UsersList);
  customElements.define("add-user", AddUser);
}