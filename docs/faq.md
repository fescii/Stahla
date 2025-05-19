# Frequently Asked Questions (FAQ) - Stahla AI SDR

This FAQ provides answers to common questions about the Stahla AI SDR application.

## General Questions

**Q1: What is the Stahla AI SDR application?**
A: The Stahla AI SDR is a backend application designed to automate Sales Development Representative (SDR) tasks for Stahla. It handles inbound communication (calls, web forms, emails), enriches lead data in HubSpot, classifies and routes leads, provides real-time price quotes, and offers an operational dashboard backend for monitoring.

**Q2: What are the main problems this application solves?**
A: It addresses issues like missed context from manual lead handling, slow response times, inconsistent lead routing, and delays in providing price quotes. The goal is to improve efficiency, data accuracy, customer trust, and ultimately, revenue.

**Q3: What are the key benefits of using this system?**
A:
*   Faster lead response times (target <15 sec median for SDR interaction).
*   Rapid price quote generation (target <500ms P95).
*   Improved data completeness in HubSpot (target ≥95%).
*   More accurate lead routing (target ≥90%).
*   Potential for increased qualified-lead-to-quote conversion (target +20%).
*   Streamlined human handoff with comprehensive lead information.
*   Operational visibility through a dashboard backend.

**Q4: Who is the target user for this application?**
A: The primary users are Stahla's sales and operations teams. The system automates many SDR tasks, allowing sales representatives to focus on qualified leads and closing deals.

## Technical Questions

**Q5: What are the main technologies used in this project?**
A:
*   **Backend Framework:** FastAPI (Python)
*   **CRM Integration:** HubSpot API
*   **Voice AI:** Bland.ai
*   **Optional Language Model:** Marvin AI (configurable for others like OpenAI, Anthropic, Gemini)
*   **Workflow Automation:** n8n
*   **Data Validation:** Pydantic
*   **Caching:** Redis
*   **Geo-Services:** Google Maps Distance Matrix API
*   **Pricing Data Source:** Google Sheets API
*   **Logging:** Logfire
*   **Containerization:** Docker, Docker Compose
*   **Programming Language:** Python 3.11+

**Q6: How is the application deployed?**
A: The application is designed to be containerized using Docker and orchestrated with Docker Compose. It can also be run locally using Uvicorn for development.

**Q7: How is configuration managed?**
A: Configuration is managed through `.env` files and Pydantic settings models (located in `app/core/config.py`). This includes API keys, database URLs, Google Sheet IDs, and other operational parameters.

**Q8: How does the system ensure security, especially for API endpoints?**
A: Specific webhooks, like the pricing quote and location lookup endpoints, are secured using API Key authentication. The application also uses Pydantic for data validation, which helps prevent injection attacks. Further security measures can be implemented as needed (e.g., OAuth2 for dashboard access).

**Q9: How is data cached for performance?**
A: Redis is used for caching. This includes:
    *   Pricing rules, product catalogs, branch locations, and configuration synced from Google Sheets.
    *   Google Maps Distance Matrix API results for delivery calculations.
    *   Data for the operational dashboard (e.g., counters, logs).

## Feature-Specific Questions

**Q10: How does the Voice AI (Bland.ai) integration work?**
A: Bland.ai is used to:
    *   Answer inbound calls directly.
    *   Initiate automated callbacks to leads who submitted incomplete web forms, asking dynamic questions to gather missing information.
    *   Call summaries and recording URLs are logged to HubSpot.

**Q11: How are web forms and emails processed?**
A:
    *   **Web Forms:** Submissions are received via a webhook (`/api/v1/webhooks/form`). If data is incomplete, an automated Bland.ai call is triggered.
    *   **Emails:** Incoming emails are processed via a webhook (`/api/v1/webhooks/email`). An LLM (like Marvin AI) is used to parse email content and extract relevant lead data. Automated replies can be sent for incomplete information.

**Q12: How does the lead classification and routing engine work?**
A: The engine (located in `app/services/classify/`) classifies leads into categories like 'Services', 'Logistics', 'Leads', or 'Disqualify'. This can be based on rules or AI (e.g., Marvin). Based on the classification, HubSpot Deals are assigned to the correct pipeline and owner (using round-robin).

**Q13: How does the real-time pricing agent work?**
A:
    *   A secure webhook (`/api/v1/webhook/pricing/quote`) provides instant price quotes.
    *   It uses pricing rules, trailer types, duration, usage, extras, delivery distance (to the nearest branch), and seasonal multipliers.
    *   Pricing data and branch locations are dynamically synced from Google Sheets and cached in Redis.
    *   A separate webhook (`/api/v1/webhook/pricing/location_lookup`) handles asynchronous calculation and caching of delivery distances using Google Maps to optimize quote speed.

**Q14: What information does the Operational Dashboard API provide?**
A: The dashboard backend API (endpoints under `/api/v1/dashboard/`) provides:
    *   Monitoring data: Status of quote requests, location lookups, cache performance, external service status, error summaries, and recent request logs.
    *   Management functions: Manual triggering of Google Sheet sync, and tools to view/clear specific cache keys.

**Q15: How are HubSpot custom properties managed?**
A: The system is designed to create/update HubSpot Contacts and Deals, populating a defined set of custom properties. Details of these properties (e.g., for lead type, product interest, budget, location details, pricing components) are documented in `docs/hubspot.md`.

**Q16: What kind of webhooks does the application expose and consume?**
A:
    *   **Exposed (Incoming):**
        *   `/api/v1/webhooks/form`: For web form submissions.
        *   `/api/v1/webhooks/hubspot`: For events from HubSpot (e.g., deal updates, though specific use cases may vary).
        *   `/api/v1/webhooks/voice`: For events from Bland.ai (e.g., call completion, transcripts).
        *   `/api/v1/webhook/pricing/quote`: For synchronous price quote requests.
        *   `/api/v1/webhook/pricing/location_lookup`: For asynchronous location/distance calculations.
        *   *(Potentially others like an email webhook if a dedicated service is used)*
    *   **Consumed (Outgoing):**
        *   The system makes calls to Bland.ai API, HubSpot API, Google Maps API, Google Sheets API, and potentially n8n webhooks.

**Q17: How is n8n used in the system?**
A: n8n is used as a workflow automation tool to connect with and manage specific webhook workflows, such as triggering lead processing sequences or other automation tasks that are external to the core application logic.

## Setup and Development

**Q18: How do I set up the project for development?**
A:
1.  Clone the repository.
2.  Create a `.env` file from `.env.example` and fill in all required API keys and configuration details (HubSpot, Bland.ai, Logfire, Google Maps, Google Sheets, Redis, etc.).
3.  Install Python dependencies: `pip install -r requirements.txt`.
4.  Run locally using Uvicorn: `uvicorn app.main:app --reload --port 8000`.

**Q19: How can I run the application using Docker?**
A: Use Docker Compose: `docker-compose up --build`. Ensure your `.env` file is correctly configured as Docker Compose will use it.

**Q20: Where can I find API documentation?**
A: Once the application is running:
    *   Interactive API documentation (Swagger UI): `http://localhost:8000/docs`
    *   Alternative API documentation (ReDoc): `http://localhost:8000/redoc`
    *   Detailed endpoint specifications are also in `docs/api.md`.
    *   Other conceptual documentation (features, webhooks, etc.) is in the `docs/` directory and some are served via `/api/v1/docs/{filename}`.

## Troubleshooting & Support

**Q21: What should I do if I encounter an error?**
A:
1.  Check the application logs (Logfire, or console output if running locally).
2.  Verify your `.env` configuration, especially API keys and service URLs.
3.  Check the status of external services (HubSpot, Bland.ai, Google Cloud Platform).
4.  Use the health check endpoints (`/health`, `/ping`) to verify basic application responsiveness.
5.  Consult the operational dashboard API for error summaries if accessible.

**Q22: How are pricing rules updated?**
A: Pricing rules, product details, branch locations, and other related configurations are managed in Google Sheets. The application periodically syncs this data into its Redis cache. A manual sync can also be triggered via the dashboard API.

**Q23: What if HubSpot API limits are reached?**
A: The application should be designed with HubSpot API limits in mind, using batch operations where possible and efficient data retrieval. If limits are consistently hit, it may require optimizing API call patterns or requesting a limit increase from HubSpot.

**Q24: How can I clear the cache if needed?**
A: The Operational Dashboard API provides endpoints to view and clear specific cache keys or groups of keys (e.g., all pricing data, all maps data). This can be useful for forcing a refresh of configuration or troubleshooting stale data issues.

---

*This FAQ is based on the project documentation as of May 2024. For the most current information, please refer to the main README and other documents in the `docs/` directory.*
