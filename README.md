# Stahla AI SDR API

This project implements a FastAPI backend designed to automate Sales Development Representative (SDR) tasks for Stahla, addressing inconsistencies and delays in handling inbound leads.

## Problem & Goal

Manual handling of inbound calls, emails, and forms leads to missed context, slow responses, and inconsistent lead routing across Stahla Services, Logistics, and Leads. This erodes customer trust and results in lost revenue.

The goal is to create a reliable, scalable AI-driven intake flow that captures complete information, classifies opportunities accurately, integrates seamlessly with HubSpot, and enables rapid human follow-up, aiming for:
*   <15 sec median first response time.
*   ≥95% data-field completeness in HubSpot.
*   ≥90% routing accuracy.
*   +20% increase in qualified-lead-to-quote conversion.

## High-Level Approach

1.  **AI Intake Agent:** Uses voice (Bland.ai), email parsing, and web form follow-ups to greet prospects, ask dynamic questions, and populate HubSpot.
2.  **Classification & Routing:** Determines the appropriate business unit (Services, Logistics, Leads, or Disqualify) based on lead data and assigns the deal in HubSpot.
3.  **Human Handoff:** Provides reps with summaries and context for quick quoting or disqualification.
4.  **Extensible Framework:** Built for future agent additions (pricing, vendor sourcing, etc.).
5.  **(Future) Integration Layer:** Consider tools like n8n for managing webhooks, retries, and complex workflows if needed post-v1.

## Key Technologies

*   **Backend Framework:** FastAPI
*   **CRM:** HubSpot
*   **Voice AI:** Bland.ai
*   **Language Model (Optional):** Marvin AI
*   **Data Validation:** Pydantic
*   **Logging:** Logfire
*   **Containerization:** Docker, Docker Compose
*   **Language:** Python 3.11+

## Core Features (v1)

*   **Voice AI Intake Agent (Bland.ai):** Answers inbound calls and initiates callbacks for incomplete web forms within 1 minute.
*   **Web Form & Email Intake:** Processes submissions/emails via webhooks, using dynamic questioning and LLM parsing for emails.
*   **Automated Follow-up:** Initiates Bland.ai calls for missing web form data and sends auto-reply emails for incomplete email leads.
*   **HubSpot Data Enrichment:** Creates/updates Contacts & Deals with high completeness (lead type, product, duration, location, stalls, budget). Writes call summaries/recordings to HubSpot.
*   **Classification & Routing Engine:** Classifies leads (Services/Logistics/Leads/Disqualify) using rules or AI (Marvin) and routes deals to the correct HubSpot pipeline with round-robin owner assignment.
*   **Human-in-the-Loop Handoff:** Sends email notifications to reps with summaries, checklists, and action links.
*   **Configuration & Monitoring:** Via `.env`, Pydantic settings, and health check endpoints.
*   **Logging:** Structured logging via Logfire.

*(See `docs/features.md` for more details)*

## Project Structure

```
├── app/                  # Main application code
│   ├── api/              # API endpoint definitions (FastAPI routers)
│   ├── core/             # Configuration loading (settings)
│   ├── models/           # Pydantic data models
│   ├── services/         # Business logic (classification, HubSpot, Bland, Email)
│   ├── utils/            # Utility functions
│   └── main.py           # FastAPI application entry point
├── docs/                 # Project documentation
│   ├── api_usage.md
│   ├── features.md
│   └── progress.md
├── tests/                # Unit/Integration tests (to be added)
├── .env                  # Local environment variables (copy from .env.example)
├── .env.example          # Example environment variables
├── requirements.txt      # Python dependencies
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker Compose configuration
└── README.md             # This file
```

## Setup & Running

1.  **Clone the repository.**
2.  **Create and configure `.env`:**
    *   Copy `.env.example` to `.env`.
    *   Fill in your API keys for `HUBSPOT_API_KEY`, `BLAND_API_KEY`, `LOGFIRE_TOKEN`, and `MARVIN_API_KEY` (if using Marvin).
    *   Configure `APP_BASE_URL` to the publicly accessible URL where this API will run (needed for webhooks).
    *   Adjust other settings like `EMAIL_SENDING_ENABLED` and SMTP details if needed.
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run locally using Uvicorn:**
    ```bash
    uvicorn app.main:app --reload --port 8000
    ```
    *(The API will be available at `http://localhost:8000`)*
5.  **Run using Docker Compose:**
    ```bash
    docker-compose up --build
    ```
    *(The API will be available at `http://localhost:8000` by default)*

## API Documentation

Once the application is running, interactive API documentation (Swagger UI) is available at `/docs` (e.g., `http://localhost:8000/docs`).

ReDoc documentation is available at `/redoc` (e.g., `http://localhost:8000/redoc`).

See `docs/api_usage.md` for a summary of endpoints.

## Future Considerations (Post-v1)

*   SMS intake channel (e.g., via Twilio).
*   Automated price quoting.
*   Dedicated Integration & Orchestration Layer (e.g., self-hosted n8n on fly.io) to manage webhooks, retries, and potentially allow non-developers to adjust workflows.
