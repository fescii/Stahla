# Project Progress & TODOs (Aligned with AI SDR PRD v1)

## Current Status (as of May 5, 2025)

The project provides a FastAPI backend implementing the core logic for the Stahla AI SDR v1, including the integrated Pricing Agent and a backend API structure for an operational dashboard.

*   **API Endpoints:** Core endpoints handle health checks, lead classification, webhooks (form, email, voice), **real-time pricing (quote, location lookup)**, and **dashboard operations (overview, cache management, sync trigger)**.
*   **Lead Intake & Classification:** Functionality remains as previously described.
*   **HubSpot Integration:** Functionality remains as previously described.
*   **Bland.ai Integration:** Functionality remains as previously described.
*   **Email Processing:** Functionality remains as previously described.
*   **Pricing Agent:**
    *   Services implemented for quoting (`quote.py`), location lookups (`location.py`), Redis caching (`redis.py`), and Google Sheet synchronization (`sync.py`).
    *   Pricing logic uses data parsed from sheets (products, generators, config) and cached in Redis.
    *   Branch locations are dynamically loaded from sheets via Redis.
    *   Delivery cost calculation includes basic tiering and seasonal multiplier logic (requires configuration in sheet).
    *   Endpoints `/pricing/quote` and `/pricing/location_lookup` are functional with API key security.
*   **Dashboard Backend:**
    *   API endpoints (`/dashboard/...`) provide access to monitoring data and management functions.
    *   Service layer (`dash/dashboard.py`) fetches data from Redis (counters, logs) and interacts with other services (Redis, Sync).
    *   Background tasks (`dash/background.py`) handle asynchronous logging of requests, errors, and metric increments to Redis.
*   **Configuration:** Settings include API keys, Google Sheet IDs/Ranges, Redis URL, etc.
*   **Models:** Pydantic models define data structures for all components.

## TODOs / Future Work (Based on PRD & Current Implementation)

*   **Pricing Agent (`app/services/quote/`):**
    *   **Critical:** Verify and refine pricing calculation logic (`quote.py`) to exactly match all nuances of Appendix A & B and business rules (e.g., specific event tier selection logic, detailed prorating rules).
    *   **Critical:** Define and implement the exact structure and source for Delivery Pricing rules (free miles, per-mile rate, base fee) within the Google Sheet `Config` tab and ensure `sync.py` parses it correctly.
    *   Implement parsing for all seasonal multiplier tiers (Premium Plus, Platinum) in `sync.py`.
*   **Dashboard (`app/services/dash/`, `app/api/v1/endpoints/dash/`):**
    *   Implement robust authentication/authorization for dashboard endpoints.
    *   Implement tracking and display for metrics requiring external systems or more complex logic (P95 latency, cache hit/miss ratios, historical trends).
    *   Refine error logging and aggregation for better insights.
    *   Consider adding more granular monitoring data points as needed.
    *   Develop the frontend UI for the dashboard.
*   **HubSpot Service (`app/services/hubspot.py`):**
    *   (Previous TODOs remain relevant: Dynamic IDs, call data persistence, owner assignment refinement).
*   **HubSpot Endpoints (`app/api/v1/endpoints/hubspot.py`):**
    *   (Previous TODOs remain relevant).
*   **Bland.ai Integration (`app/services/bland.py`):**
    *   (Previous TODOs remain relevant).
*   **Email Processing (`app/services/email.py`):**
    *   (Previous TODOs remain relevant).
*   **Handoff Notifications (`app/services/email.py`):**
    *   (Previous TODOs remain relevant).
*   **General:**
    *   **Middleware:** Refine `LoggingMiddleware` dependency injection (e.g., using `app.state`).
    *   **Testing:** Add tests specifically for Pricing Agent logic and Dashboard API functionality.
    *   (Previous TODOs remain relevant: Observability, Error Handling, Security, Documentation).

## Future Considerations (Post-v1, per PRD)

*   SMS intake channel (Twilio integration).
*   (Pricing Agent is now part of v1 scope).
