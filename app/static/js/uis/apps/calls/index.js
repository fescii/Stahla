import CallsRecent from './recent.js';
import CallsSuccess from './success.js';
import CallsFailed from './failed.js';
import CallsOldest from './oldest.js';

export default function calls() {
  customElements.define("calls-recent", CallsRecent);
  customElements.define("calls-success", CallsSuccess);
  customElements.define("calls-failed", CallsFailed);
  customElements.define("calls-oldest", CallsOldest);
}
