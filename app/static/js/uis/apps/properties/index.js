import PropertiesContact from "./contact.js";
import PropertiesLead from "./lead.js";
import PropertiesFields from "./fields.js";

export default function properties() {
  customElements.define("properties-contact", PropertiesContact);
  customElements.define("properties-lead", PropertiesLead);
  customElements.define("properties-fields", PropertiesFields);
}
