# API Usage

This document outlines the available API endpoints for the Stahla AI SDR application, designed to handle lead intake, classification, and HubSpot integration based on the [stahla.com] AI SDR PRD.
All endpoints are prefixed with `/api/v1`.

## Health Checks

*   **`GET /health`**:
    *   **Summary:** Comprehensive system health check.
    *   **Description:** Provides status of the API service, system uptime, basic system metrics (CPU, memory, disk), checks connectivity and responsiveness of external dependencies (HubSpot, Bland.ai, Marvin), and shows environment information.
    *   **Response:** JSON object detailing the health status (`status`: "ok" or "degraded"), timestamp, uptime, system info, dependency health, and environment details.

*   **`GET /health/ping`**:
    *   **Summary:** Simple ping check.
    *   **Description:** A minimal endpoint useful for load balancers or basic availability checks.
    *   **Response:** `{"ping": "pong"}`

## Lead Classification

*   **`POST /classify`**:
    *   **Summary:** Classify lead data.
    *   **Description:** Receives lead data (structured according to `ClassificationInput` model) and routes it to the classification engine. The engine determines the lead type (Services, Logistics, Leads, Disqualify), reasoning, confidence, and routing suggestions, aligning with the PRD's classification goals.
    *   **Request Body:** `ClassificationInput` JSON object (see `app/models/classification.py`).
    *   **Response:** `ClassificationResult` JSON object containing the status and the detailed `ClassificationOutput`.

## Webhooks (Incoming Data)

*   **`POST /webhooks/form`**:
    *   **Summary:** Receive web form submissions and trigger follow-up/classification.
    *   **Description:** Handles submissions from web forms (expects `FormPayload` model). Checks data completeness against required fields. If complete, triggers classification and HubSpot updates. If incomplete, initiates a Bland.ai voice callback within ~15 seconds to gather missing data dynamically.
    *   **Request Body:** `FormPayload` JSON object (see `app/models/webhook.py`).
    *   **Response:** Varies based on action:
        *   If classified: JSON object with status, source, action ("classification_complete"), classification details, and HubSpot IDs.
        *   If callback initiated: JSON object with status, source, action ("callback_initiated"), and Bland.ai call ID.

*   **`POST /webhooks/email`**:
    *   **Summary:** Process incoming emails for lead data.
    *   **Description:** Handles email webhooks (expects `EmailWebhookPayload`). Parses email content (potentially using an LLM like Marvin) to extract lead information. Checks for data completeness. If incomplete, sends an automated email reply requesting specific missing fields. If complete, triggers classification and HubSpot updates. Sends handoff notifications to reps.
    *   **Request Body:** `EmailWebhookPayload` JSON object (see `app/models/email.py`).
    *   **Response:** `EmailProcessingResult` JSON object detailing the processing status, message, extracted data, whether classification is pending, and potentially HubSpot IDs.

*   **`POST /webhooks/voice`**:
    *   **Summary:** Receive voice call results (transcripts, summaries) from Bland.ai.
    *   **Description:** Handles webhook calls from Bland.ai after an inbound call or a form follow-up call completes (expects `BlandWebhookPayload`). Processes the transcript and any generated summary, extracts relevant information, triggers classification, and updates HubSpot (including attaching call summary/recording links).
    *   **Request Body:** `BlandWebhookPayload` JSON object (see `app/models/bland.py`).
    *   **Response:** JSON object with status, source, action ("classification_complete"), classification details, and HubSpot IDs.

## HubSpot (Direct - Currently Placeholders)

*Note: These endpoints currently contain placeholder logic and require implementation.*

*   **`POST /hubspot/contact`**:
    *   **Summary:** Create or Update HubSpot Contact.
    *   **Description:** Intended to receive contact data and interact with the HubSpot API via the `HubSpotManager`.
    *   **Request Body:** Contact data (Pydantic model TBD).
    *   **Response:** Placeholder response.

*   **`POST /hubspot/deal`**:
    *   **Summary:** Create or Update HubSpot Deal.
    *   **Description:** Intended to receive deal data and interact with the HubSpot API via the `HubSpotManager`.
    *   **Request Body:** Deal data (Pydantic model TBD).
    *   **Response:** Placeholder response.
