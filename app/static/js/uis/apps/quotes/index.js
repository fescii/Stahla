import QuotesRecent from "./recent.js";
import QuotesOldest from "./oldest.js";
import QuotesHighest from "./highest.js";
import QuotesLowest from "./lowest.js";

export default function quotes() {
  customElements.define("quotes-recent", QuotesRecent);
  customElements.define("quotes-oldest", QuotesOldest);
  customElements.define("quotes-highest", QuotesHighest);
  customElements.define("quotes-lowest", QuotesLowest);
}
