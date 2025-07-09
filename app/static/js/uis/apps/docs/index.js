import ApiDocs from "./api.js";
import FeaturesDocs from "./features.js";
import HubspotDocs from "./hubspot.js";
import MarvinDocs from "./marvin.js";
import ServicesDocs from "./services.js";
import WebhooksDocs from "./webhooks.js";
import FAQDocs from "./faq.js";
import CodeDocs from "./code.js";

export default function docs () {
  customElements.define("docs-api", ApiDocs);
  customElements.define("docs-services", ServicesDocs);
  customElements.define("docs-webhooks", WebhooksDocs);
  customElements.define("docs-marvin", MarvinDocs);
  customElements.define("docs-features", FeaturesDocs);
  customElements.define("docs-hubspot", HubspotDocs);
  customElements.define("docs-faq", FAQDocs);
  customElements.define("docs-code", CodeDocs);
}