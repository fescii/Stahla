# Stahla AI SDR API

This project implements a FastAPI backend designed to automate Sales Development Representative (SDR) tasks for Stahla, including **real-time price quoting** and providing an **operational dashboard backend**.

## Problem & Goal

Manual handling of inbound calls, emails, and forms leads to missed context, slow responses, inconsistent lead routing, **and delays in providing price quotes**. This erodes customer trust and results in lost revenue.

The goal is to create a reliable, scalable AI-driven intake and quoting flow that captures complete information, classifies opportunities accurately, integrates seamlessly with HubSpot, **generates quotes rapidly (<500ms P95)**, enables quick human follow-up, and provides operational visibility.
*   <15 sec median first response time (SDR interaction).
*   **<500ms P95 quote generation latency (`/webhook/pricing/quote`).**
*   ≥95% data-field completeness in HubSpot.
*   ≥90% routing accuracy.
*   +20% increase in qualified-lead-to-quote conversion.

## High-Level Approach

1.  **AI Intake Agent:** Uses voice (Bland.ai), email parsing, and web form follow-ups to greet prospects, ask dynamic questions, and populate HubSpot.
2.  **Classification & Routing:** Determines the appropriate business unit (Services, Logistics, Leads, or Disqualify) based on lead data and assigns the deal in HubSpot.
3.  **Real-time Pricing Agent (Integrated):** Provides instant price quotes via a secure webhook, using dynamically synced pricing rules from Google Sheets and cached Google Maps distance calculations.
4.  **Human Handoff:** Provides reps with summaries, context, and **quotes** for quick follow-up or disqualification.
5.  **Operational Dashboard Backend:** Exposes API endpoints for monitoring system status, cache performance, sync status, errors, recent requests, and limited cache/sync management.
6.  **Extensible Framework:** Built for future agent additions.
7.  **Integration Layer:** Uses n8n for managing specific webhook workflows (e.g., lead processing trigger).

## Key Technologies

*   **Backend Framework:** FastAPI
*   **CRM:** HubSpot
*   **Voice AI:** Bland.ai
*   **Language Model (Optional):** Marvin AI (or others like OpenAI, Anthropic, Gemini)
*   **Workflow Automation:** n8n
*   **Data Validation:** Pydantic
*   **Caching:** Redis
*   **Geo-Services:** Google Maps Distance Matrix API
*   **Data Source (Pricing):** Google Sheets API
*   **Logging:** Logfire
*   **Containerization:** Docker, Docker Compose
*   **Language:** Python 3.11+

## Core Features (v1 + Pricing)

*   **Voice AI Intake Agent (Bland.ai):** Answers inbound calls and initiates callbacks for incomplete web forms within 1 minute.
*   **Web Form & Email Intake:** Processes submissions/emails via webhooks, using dynamic questioning and LLM parsing for emails.
*   **Automated Follow-up:** Initiates Bland.ai calls for missing web form data and sends auto-reply emails for incomplete email leads.
*   **HubSpot Data Enrichment:** Creates/updates Contacts & Deals with high completeness. Writes call summaries/recordings to HubSpot.
*   **Classification & Routing Engine:** Classifies leads (Services/Logistics/Leads/Disqualify) and routes deals to the correct HubSpot pipeline with round-robin owner assignment.
*   **Real-time Pricing Agent:**
    *   `/webhook/pricing/quote` endpoint for instant quote generation (secured by API Key).
    *   `/webhook/pricing/location_lookup` endpoint for asynchronous distance calculation/caching.
    *   Dynamic sync of pricing rules, config, and branches from Google Sheets to Redis cache.
    *   Calculates quotes based on trailer type, duration, usage, extras, delivery distance (nearest branch), and seasonal multipliers.
*   **Operational Dashboard Backend API:**
    *   Endpoints (`/dashboard/...`) for monitoring status (requests, errors, cache, sync) and recent activity.
    *   Endpoints for managing cache (view/clear specific keys, clear pricing/maps cache) and triggering manual sheet sync.
*   **Human-in-the-Loop Handoff:** Sends email notifications to reps with summaries, checklists, and action links.
*   **Configuration & Monitoring:** Via `.env`, Pydantic settings, health check endpoints, and background logging to Redis for dashboard.
*   **Logging:** Structured logging via Logfire.
*   **Workflow Integration:** Connects with n8n for specific automation tasks.

*(See `docs/features.md` for more details)*

## Project Structure

```
.
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── classify.py
│   │           ├── health.py
│   │           ├── hubspot.py
│   │           ├── documentation.py # Added
│   │           ├── dash/         # Added
│   │           │   └── dashboard.py
│   │           └── webhooks/
│   │               ├── form.py
│   │               ├── helpers.py
│   │               ├── hubspot.py
│   │               ├── voice.py
│   │               └── pricing.py  # Added
│   ├── assets/
│   ├── core/
│   │   ├── config.py
│   │   ├── middleware.py # Added
│   │   └── security.py   # Added (if exists)
│   ├── models/
│   │   ├── bland.py
│   │   ├── classification.py
│   │   ├── common.py
│   │   ├── email.py
│   │   ├── hubspot.py
│   │   ├── webhook.py
│   │   ├── location.py   # Added
│   │   ├── quote.py      # Added (renamed from pricing.py)
│   │   └── dash/         # Added
│   │       └── dashboard.py
│   ├── services/
│   │   ├── classify/
│   │   │   ├── classification.py
│   │   │   ├── marvin.py
│   │   │   └── rules.py
│   │   ├── bland.py
│   │   ├── email.py
│   │   ├── hubspot.py
│   │   ├── n8n.py
│   │   ├── location/     # Added
│   │   │   └── location.py # Renamed
│   │   ├── quote/        # Added
│   │   │   ├── quote.py    # Renamed
│   │   │   └── sync.py     # Renamed
│   │   ├── redis/        # Added
│   │   │   └── redis.py    # Renamed
│   │   └── dash/         # Added
│   │       ├── background.py
│   │       └── dashboard.py
│   ├── utils/
│   │   ├── location.py
│   │   └── enhanced.py   # Renamed
│   ├── __init__.py
│   └── main.py
├── docs/
│   ├── api.md          # Updated
│   ├── features.md     # Updated
│   ├── progress.md     # Updated
│   └── status.md       # Updated
├── info/
│   ├── 01 Pricing Agent Analysis & Implementation Proposal.md # Added
│   ├── combined_sheet.csv # Added
│   ├── hubspot.md
│   ├── properties.csv
│   └── services.csv
├── rest/
│   └── form.http
├── tests/ # (Placeholder)
├── .env
├── .env.example      # Updated
├── .gitignore
├── requirements.txt  # Updated
├── Dockerfile
├── docker-compose.yml
└── README.md         # This file
```

## Setup & Running

1.  **Clone the repository.**
2.  **Create and configure `.env`:**
    *   Copy `.env.example` to `.env`.
    *   Fill in API keys: `HUBSPOT_API_KEY`, `BLAND_API_KEY`, `LOGFIRE_TOKEN`, `GOOGLE_MAPS_API_KEY`, `PRICING_WEBHOOK_API_KEY`, and your chosen `LLM_PROVIDER`'s key.
    *   Configure `GOOGLE_SHEET_ID` and the `GOOGLE_SHEET_*_RANGE` variables for products, generators, branches, and config tabs/ranges.
    *   Set up `GOOGLE_APPLICATION_CREDENTIALS` if using Google Service Account auth.
    *   Configure `REDIS_URL`.
    *   Configure `APP_BASE_URL`.
    *   Configure n8n settings if `N8N_ENABLED=true`.
    *   Adjust other settings as needed.
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run locally using Uvicorn:**
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
5.  **Run using Docker Compose:**
    ```bash
    docker-compose up --build
    ```

## API Documentation

Once the application is running:

*   Interactive API documentation (Swagger UI) is available at `/docs`.
*   Alternative API documentation (ReDoc) is available at `/redoc`.
*   Project documentation files (from `/docs`, e.g., `features.md`) are served as HTML at `/api/v1/docs/{filename}`.
*   Detailed endpoint specifications are in `docs/api.md`.

## Future Considerations (Post-v1)

*   SMS intake channel (e.g., via Twilio).
*   Frontend UI for the Operational Dashboard.
*   Integration with external monitoring/alerting systems for advanced metrics (latency P95, cache hit ratios, historical trends) and alerts.
*   Refinement of HubSpot dynamic ID fetching and call data persistence.
*   Dedicated Integration & Orchestration Layer (e.g., self-hosted n8n).
