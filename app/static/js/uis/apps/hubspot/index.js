import HubspotContacts from "./contacts.js";
import HubspotLeads from "./leads.js";
import HubspotProperties from "./properties.js";

export default function hubspot() {
  customElements.define("hubspot-contacts", HubspotContacts);
  customElements.define("hubspot-leads", HubspotLeads);
  customElements.define("hubspot-properties", HubspotProperties);
}
