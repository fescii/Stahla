# Key Features (Aligned with AI SDR PRD v1)

This document highlights the main features of the Stahla AI SDR application, based on the v1 Product Requirements Document.

## 1. AI Intake Agent (Multi-Channel)

* **Voice (Bland.ai):**
  * Answers inbound calls directly.
  * Initiates automated callbacks within ~1 minute for incomplete web form submissions.
  * Uses dynamic, context-aware questioning to gather required data efficiently.
* **Web Forms:** Accepts submissions via webhook (`/api/v1/webhooks/form`). Triggers voice follow-up if data is incomplete.

## 2. HubSpot Data Enrichment & Write-Back

* **Contact & Deal Management:** Automatically creates or updates HubSpot Contacts and Deals with ≥95% property completeness (target fields: lead type, product, duration, location, stalls, budget).
* **Call Summary & Recording:** Writes call summary text and a recording URL (from Bland.ai) to a HubSpot custom object or activity for easy rep access.
* **Custom Property Mapping:** Populates defined custom HubSpot properties with extracted/classified lead details.

## 3. Classification & Routing Engine

* **Lead Classification:** Determines lead category (`Services`, `Logistics`, `Leads`, or `Disqualify`) based on product type, size, geography, budget, etc., using a configurable engine (rule-based or AI like Marvin) located in `app/services/classify/`.
* **Pipeline Assignment:** Pushes the created/updated HubSpot Deal to the correct pipeline (Services, Logistics, Leads) based on classification.
* **Owner Assignment:** Assigns deal ownership using a round-robin mechanism within the designated business unit/team.

## 4. Human-in-the-Loop Handoff

* **HubSpot Integration:** Automatically assigns leads to appropriate sales representatives through HubSpot ownership rules.
* **Classification-Based Routing:** Routes leads to the correct pipeline and stage based on classification results.

## 5. Intelligent Follow-Up

* **Incomplete Web Forms:** Triggers Bland.ai voice call for missing data.

## 6. Configuration & Monitoring

* **Environment-Based Settings:** Uses `.env` files and Pydantic settings (`app/core/config.py`) for configuration.
* **Health Checks:** Provides `/health` and `/ping` endpoints.
* **Logging:** Integrates with Logfire for observability.

## 7. Real-time Pricing Agent (Integrated)

* **Quote Webhook (`/api/v1/webhook/pricing/quote`):**
  * Provides real-time price quotes based on trailer type, duration, usage, extras, and delivery location.
  * Uses cached pricing data synced from Google Sheets.
  * Calculates delivery cost based on distance to the nearest branch (dynamically loaded) and configured rates/tiers.
  * Secured via API Key.
* **Location Lookup Webhook (`/api/v1/webhook/pricing/location_lookup`):**
  * Triggers asynchronous calculation and caching of the distance between a delivery location and the nearest branch using Google Maps.
  * Designed to be called early to optimize quote generation latency.
  * Secured via API Key.
* **Dynamic Configuration:**
  * Pricing rules, delivery configuration, seasonal multipliers, and branch locations are synced dynamically from Google Sheets and cached in Redis.

## 8. Operational Dashboard API (Backend)

* **Monitoring Endpoints (`/api/v1/dashboard/overview`, etc.):**
  * Provides API endpoints to retrieve status information about quote requests, location lookups, cache performance (size, key counts), external service status (sync timestamp, Maps API counts), aggregated error summaries, and recent request logs.
  * Data is sourced from Redis counters and logs populated asynchronously by background tasks.
* **Management Endpoints (`/api/v1/dashboard/sync/trigger`, `/api/v1/dashboard/cache/...`):**
  * Provides API endpoints to manually trigger Google Sheet synchronization.
  * Allows searching, viewing, and clearing specific cache keys (pricing catalog, individual maps results, maps results by pattern).
* **Authentication:** Includes placeholder authentication for dashboard access.

## 9. Workflow Integration

* **n8n Connectivity:** Leverages n8n for orchestrating specific automation tasks and webhook workflows (e.g., triggering lead processing sequences).

## Non-Goals (for v1)

* Full analytics dashboard (relies on HubSpot reporting).
* SMS intake channel.
* Fully implemented frontend for the Operational Dashboard.
* Advanced metrics requiring external monitoring systems (e.g., P95 latency, historical trends, cache hit/miss ratios).
* Automated alerting based on dashboard metrics.
