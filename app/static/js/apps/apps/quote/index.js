import LocationLookup from "./location.js";
import Quote from "./quote.js";

export default function quote() {
  // Register quote components
  customElements.define("location-lookup", LocationLookup);
  customElements.define("quote-form", Quote);
}