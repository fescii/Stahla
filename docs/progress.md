# Project Progress & TODOs (Aligned with AI SDR PRD v1)

## Current Status (as of April 16, 2025)

The project provides a FastAPI backend implementing the core logic for the Stahla AI SDR v1, as defined in the PRD. Key components are functional:

*   **API Endpoints:** Core endpoints under `/api/v1/` handle health checks, lead classification, and webhooks for form, email, and Bland.ai voice interactions.
*   **Lead Intake:** Webhooks receive data from forms, emails, and Bland.ai transcripts.
*   **Classification:** The engine (`app/services/classification.py`) processes leads using configurable rule-based or AI (Marvin) logic to categorize them (Services, Logistics, Leads, Disqualify).
*   **HubSpot Integration:** The service (`app/services/hubspot.py`) creates/updates contacts and deals, including initial logic for pipeline and owner assignment based on classification.
*   **Bland.ai Integration:** The service (`app/services/bland.py`) initiates callbacks for incomplete forms and processes incoming call transcripts/summaries.
*   **Email Processing:** The service (`app/services/email.py`) parses emails, checks completeness, sends auto-replies for missing info, and triggers handoff notifications.
*   **Configuration:** Settings managed via `.env` and `app/core/config.py`.
*   **Models:** Pydantic models (`app/models/`) define data structures.

## TODOs / Future Work (Based on PRD & Current Implementation)

*   **HubSpot Service (`/services/hubspot.py`):**
    *   **Critical:** Implement dynamic fetching of HubSpot internal IDs for pipelines, stages, and owners to ensure reliable assignment and avoid hardcoding (aligns with PRD routing goal).
    *   Implement writing call summary & recording URL to the designated HubSpot location (custom object or activity).
    *   Refine round-robin owner assignment logic.
*   **HubSpot Endpoints (`/api/v1/endpoints/hubspot.py`):**
    *   Replace placeholder logic with actual calls to the `HubSpotManager` service.
    *   Define specific Pydantic models for direct contact/deal creation/update request bodies if these endpoints are kept.
    *   Implement robust error handling for all HubSpot API interactions.
*   **Bland.ai Integration (`/services/bland.py`):**
    *   Ensure dynamic questioning logic is robust and correctly handles various scenarios to meet the ≥95% data completeness goal.
    *   Verify callback initiation happens within the target timeframe (<1 min).
*   **Email Processing (`/services/email.py`):**
    *   Refine LLM parsing prompts and logic for accuracy.
    *   Ensure auto-reply mechanism correctly identifies and requests *only* the missing fields.
*   **Handoff Notifications (`/services/email.py`):**
    *   Finalize content and formatting of notification emails, ensuring inclusion of TL;DR, checklist, and links per PRD.
*   **General:**
    *   **Testing:** Expand unit and integration tests significantly to cover key flows and edge cases.
    *   **Observability:** Refine Logfire logging for better monitoring of key performance indicators (response times, classification accuracy, HubSpot success rates).
    *   **Error Handling:** Enhance error handling and reporting across all services.
    *   **Security:** Conduct security review.
    *   **Documentation:** Add detailed inline code comments.

## Future Considerations (Post-v1, per PRD)

*   SMS intake channel (Twilio integration).
*   Automated price quoting.
*   Integration/Orchestration layer (like self-hosted n8n on fly.io) to manage webhooks, retries, auth rotation, and potentially enable drag-and-drop workflow adjustments by operations teams.
