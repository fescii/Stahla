import ClassifyRecent from "./recent.js";
import ClassifySuccess from "./success.js";
import ClassifyFailed from "./failed.js";
import ClassifyDisqualified from "./disqualified.js";

export default function classify() {
  customElements.define("classify-recent", ClassifyRecent);
  customElements.define("classify-success", ClassifySuccess);
  customElements.define("classify-failed", ClassifyFailed);
  customElements.define("classify-disqualified", ClassifyDisqualified);
}
