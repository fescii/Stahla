import Overview from "./overview.js";
import LatencyOverview from "./latency.js";
import ServicesStatus from "./status.js";
import SheetBranches from "./branches.js";
import SheetConfig from "./config.js";
import SheetGenerators from "./generators.js";
import SheetProducts from "./products.js";
import SheetStates from "./states.js";

// registaer all
export default function all() {
  customElements.define("dash-overview", Overview);
  customElements.define("latency-overview", LatencyOverview);
  customElements.define("sheet-branches", SheetBranches);
  customElements.define("sheet-products", SheetProducts);
  customElements.define("sheet-generators", SheetGenerators);
  customElements.define("sheet-states", SheetStates);
  customElements.define("sheet-config", SheetConfig);
  customElements.define("services-status", ServicesStatus);
}
