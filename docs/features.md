# Key Features (Aligned with AI SDR PRD v1)

This document highlights the main features of the Stahla AI SDR application, based on the v1 Product Requirements Document.

## 1. AI Intake Agent (Multi-Channel)

*   **Voice (Bland.ai):**
    *   Answers inbound calls directly.
    *   Initiates automated callbacks within ~1 minute for incomplete web form submissions.
    *   Uses dynamic, context-aware questioning to gather required data efficiently.
*   **Web Forms:** Accepts submissions via webhook (`/api/v1/webhooks/form`). Triggers voice follow-up if data is incomplete.
*   **Email:** Processes incoming emails via webhook (`/api/v1/webhooks/email`), using LLM (e.g., Marvin) for parsing and extraction.

## 2. HubSpot Data Enrichment & Write-Back

*   **Contact & Deal Management:** Automatically creates or updates HubSpot Contacts and Deals with ≥95% property completeness (target fields: lead type, product, duration, location, stalls, budget).
*   **Call Summary & Recording:** Writes call summary text and a recording URL (from Bland.ai) to a HubSpot custom object or activity for easy rep access.
*   **Custom Property Mapping:** Populates defined custom HubSpot properties with extracted/classified lead details.

## 3. Classification & Routing Engine

*   **Lead Classification:** Determines lead category (`Services`, `Logistics`, `Leads`, or `Disqualify`) based on product type, size, geography, budget, etc., using a configurable engine (rule-based or AI like Marvin) located in `app/services/classify/`.
*   **Pipeline Assignment:** Pushes the created/updated HubSpot Deal to the correct pipeline (Services, Logistics, Leads) based on classification.
*   **Owner Assignment:** Assigns deal ownership using a round-robin mechanism within the designated business unit/team.

## 4. Human-in-the-Loop Handoff

*   **Email Notifications:** Sends automated email notifications to the assigned sales representative/team upon successful classification and HubSpot record creation.
*   **Notification Content:** Includes a TL;DR summary of the lead, key extracted data, a suggested next-step checklist, and direct links to the HubSpot Contact/Deal and call recording/summary.

## 5. Intelligent Follow-Up

*   **Incomplete Web Forms:** Triggers Bland.ai voice call for missing data.
*   **Incomplete Emails:** Sends automated email reply requesting specific missing fields.

## 6. Configuration & Monitoring

*   **Environment-Based Settings:** Uses `.env` files and Pydantic settings (`app/core/config.py`) for configuration.
*   **Health Checks:** Provides `/health` and `/ping` endpoints.
*   **Logging:** Integrates with Logfire for observability.

## Non-Goals (for v1)

*   Automated price quoting.
*   Full analytics dashboard (relies on HubSpot reporting).
*   SMS intake channel.
