import apps from "./apps/index.js";
import popups from "./popups/index.js";

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
  // Log to console
  console.log(text);
}