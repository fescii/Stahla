// import apps
import AppHome from "./home.js";
import SoonPage from "./soon.js";
import all from "./all/index.js";
import docs from "./docs/index.js";
import quote from "./quote/index.js";
import users from "./users/index.js";

export default function home() {
  // Register apps
  customElements.define("app-home", AppHome);
  all();
  users();
  quote();
  docs();
  customElements.define("soon-page", SoonPage);
}