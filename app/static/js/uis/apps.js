import apps from "./apps/index.js";
import popups from "./popups/index.js";
import Sidebar from "./sidebar.js";

const core = () => {
  window.matchMedia('(display-mode: standalone)').addEventListener('change', (evt) => {
    let displayMode = 'browser';
    if (evt.matches) {
      displayMode = 'standalone';
    }
    // Log display mode change to analytics
    console.log('DISPLAY_MODE_CHANGED', displayMode);
  });
}

export default function uis(text) {
  apps();
  popups();
  core();
  customElements.define('sidebar-section', Sidebar);
  // Log to console
  console.log(text);
}