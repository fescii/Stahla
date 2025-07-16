import LocationRecent from "./recent.js";
import LocationFailed from "./failed.js";
import LocationSuccess from "./success.js";
import LocationOldest from "./oldest.js";
import LocationPending from "./pending.js";

export default function location() {
  customElements.define("location-recent", LocationRecent);
  customElements.define("location-failed", LocationFailed);
  customElements.define("location-success", LocationSuccess);
  customElements.define("location-oldest", LocationOldest);
  customElements.define("location-pending", LocationPending);
}
