import AccessPopup from "./access.js"
import DeletePopup from "./delete.js"
import QuotePopup from "./quote.js"

export default function popups() {
  // Register popups
  customElements.define("delete-popup", DeletePopup);
  customElements.define("access-popup", AccessPopup);
  customElements.define("quote-popup", QuotePopup);
}