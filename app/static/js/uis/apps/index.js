// import apps
import AppHome from "./home.js";
import SoonPage from "./soon.js";
import all from "./all/index.js";
import docs from "./docs/index.js";
import quote from "./quote/index.js";
import quotes from "./quotes/index.js";
import location from "./location/index.js";
import hubspot from "./hubspot/index.js";
import properties from "./properties/index.js";
import classify from "./classify/index.js";
import calls from "./calls/index.js";
import users from "./users/index.js";

export default function home() {
  // Register apps
  customElements.define("app-home", AppHome);
  all();
  users();
  quote();
  quotes();
  location();
  hubspot();
  properties();
  classify();
  calls();
  docs();
  customElements.define("soon-page", SoonPage);
}