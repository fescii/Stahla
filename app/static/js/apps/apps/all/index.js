import CacheSearch from "./search.js";
import Overview from "./overview.js";
import ServicesStatus from "./status.js";
import SheetBranches from "./branches.js";
import SheetConfig from "./config.js";
import SheetGenerators from "./generators.js";
import SheetProducts from "./products.js";

// registaer all
export default function all(){
  customElements.define('dash-overview', Overview);
  customElements.define('sheet-branches', SheetBranches);
  customElements.define('sheet-products', SheetProducts);
  customElements.define('sheet-generators', SheetGenerators);
  customElements.define('sheet-config', SheetConfig);
  customElements.define('cache-search', CacheSearch);
  customElements.define('services-status', ServicesStatus);
}