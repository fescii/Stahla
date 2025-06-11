# Stahla AI SDR API

This project implements a FastAPI backend designed to automate Sales Development Representative (SDR) tasks for Stahla, including **real-time price quoting** and providing an **operational dashboard backend**.

## Problem & Goal

Manual handling of inbound calls, emails, and forms leads to missed context, slow responses, inconsistent lead routing, **and delays in providing price quotes**. This erodes customer trust and results in lost revenue.

The goal is to create a reliable, scalable AI-driven intake and quoting flow that captures complete information, classifies opportunities accurately, integrates seamlessly with HubSpot, **generates quotes rapidly (<500ms P95)**, enables quick human follow-up, and provides operational visibility.

- <15 sec median first response time (SDR interaction).
- **<500ms P95 quote generation latency (`/webhook/pricing/quote`).**
- ≥95% data-field completeness in HubSpot.
- ≥90% routing accuracy.
- +20% increase in qualified-lead-to-quote conversion.

## High-Level Approach

1. **AI Intake Agent:** Uses voice (Bland.ai), email parsing, and web form follow-ups to greet prospects, ask dynamic questions, and populate HubSpot.
2. **Classification & Routing:** Determines the appropriate business unit (Services, Logistics, Leads, or Disqualify) based on lead data and assigns the deal in HubSpot.
3. **Real-time Pricing Agent (Integrated):** Provides instant price quotes via a secure webhook, using dynamically synced pricing rules from Google Sheets and cached Google Maps distance calculations.
4. **Human Handoff:** Provides reps with summaries, context, and **quotes** for quick follow-up or disqualification.
5. **Operational Dashboard Backend:** Exposes API endpoints for monitoring system status, cache performance, sync status, errors, recent requests, and limited cache/sync management.
6. **Extensible Framework:** Built for future agent additions.
7. **Integration Layer:** Uses n8n for managing specific webhook workflows (e.g., lead processing trigger).

## Key Technologies

- **Backend Framework:** FastAPI
- **CRM:** HubSpot
- **Voice AI:** Bland.ai
- **Language Model (Optional):** Marvin AI (or others like OpenAI, Anthropic, Gemini)
- **Workflow Automation:** n8n
- **Data Validation:** Pydantic
- **Caching:** Redis
- **Geo-Services:** Google Maps Distance Matrix API
- **Data Source (Pricing):** Google Sheets API
- **Logging:** Logfire
- **Containerization:** Docker, Docker Compose
- **Language:** Python 3.11+

## Core Features (v1 + Pricing)

- **Voice AI Intake Agent (Bland.ai):** Answers inbound calls and initiates callbacks for incomplete web forms within 1 minute.
- **Web Form & Email Intake:** Processes submissions/emails via webhooks, using dynamic questioning and LLM parsing for emails.
- **Automated Follow-up:** Initiates Bland.ai calls for missing web form data and sends auto-reply emails for incomplete email leads.
- **HubSpot Data Enrichment:** Creates/updates Contacts & Deals with high completeness. Writes call summaries/recordings to HubSpot.
- **Classification & Routing Engine:** Classifies leads (Services/Logistics/Leads/Disqualify) and routes deals to the correct HubSpot pipeline with round-robin owner assignment.
- **Real-time Pricing Agent:**
  - `/webhook/pricing/quote` endpoint for instant quote generation (secured by API Key).
  - `/webhook/pricing/location_lookup` endpoint for asynchronous distance calculation/caching.
  - Dynamic sync of pricing rules, config, and branches from Google Sheets to Redis cache.
  - Calculates quotes based on trailer type, duration, usage, extras, delivery distance (nearest branch), and seasonal multipliers.
- **Operational Dashboard Backend API:**
  - Endpoints (`/dashboard/...`) for monitoring status (requests, errors, cache, sync) and recent activity.
  - Endpoints for managing cache (view/clear specific keys, clear pricing/maps cache) and triggering manual sheet sync.
- **Human-in-the-Loop Handoff:** Sends email notifications to reps with summaries, checklists, and action links.
- **Configuration & Monitoring:** Via `.env`, Pydantic settings, health check endpoints, and background logging to Redis for dashboard.
- **Logging:** Structured logging via Logfire.
- **Workflow Integration:** Connects with n8n for specific automation tasks.

_(See `docs/features.md` for more details)_

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
│   │           ├── documentation.py
│   │           ├── dash/
│   │           │   └── dashboard.py
│   │           └── webhooks/
│   │               ├── form.py
│   │               ├── helpers.py
│   │               ├── hubspot.py
│   │               ├── voice.py
│   │               └── pricing.py
│   ├── assets/
│   │   ├── call.json
│   │   ├── data.json
│   │   ├── edges.json
│   │   ├── knowledge.json
│   │   ├── location.json
│   │   ├── quote.json
│   │   └── script.md
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── middleware.py
│   │   ├── security.py
│   │   └── templating.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── bland.py
│   │   ├── blandlog.py
│   │   ├── classification.py
│   │   ├── common.py
│   │   ├── email.py
│   │   ├── error.py
│   │   ├── hubspot.py
│   │   ├── location.py
│   │   ├── pricing.py
│   │   ├── quote.py
│   │   ├── user.py
│   │   ├── webhook.py
│   │   └── dash/
│   │       ├── __init__.py
│   │       └── dashboard.py # Assuming dashboard.py based on pattern, verify if other files exist
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   # (contents of auth/ if known)
│   │   ├── classify/
│   │   │   ├── __init__.py
│   │   │   ├── classification.py
│   │   │   ├── marvin.py
│   │   │   └── rules.py
│   │   ├── dash/
│   │   │   ├── __init__.py
│   │   │   ├── background.py
│   │   │   └── dashboard.py
│   │   ├── location/
│   │   │   ├── __init__.py
│   │   │   └── location.py
│   │   ├── mongo/
│   │   │   # (contents of mongo/ if known)
│   │   ├── quote/
│   │   │   ├── __init__.py
│   │   │   ├── quote.py
│   │   │   └── sync.py
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   └── redis.py
│   │   ├── bland.py
│   │   ├── email.py
│   │   ├── hubspot.py
│   │   └── n8n.py
│   ├── static/
│   │   ├── css/
│   │   ├── img/
│   │   └── js/
│   ├── templates/
│   │   └── home.html
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── enhanced.py
│   │   └── location.py
│   ├── __init__.py
│   ├── gcp.json
│   └── main.py
├── docs/
│   ├── api.md
│   ├── faq.md
│   ├── features.md
│   ├── hubspot.md
│   ├── marvin.md
│   ├── services.md
│   └── webhooks.md
├── info/
│   ├── 01 Pricing Agent Analysis & Implementation Proposal.md
│   ├── drop.txt
│   ├── hubspot.md
│   ├── properties.csv
│   └── Unified AI Call Assistant(v2).md
├── rest/
│   ├── auth.http
│   ├── bland.http
│   ├── classify.http
│   ├── classify_fixed.http
│   ├── dash.http
│   ├── documentation.http
│   ├── error.http
│   ├── form.http
│   ├── health.http
│   ├── location.http
│   ├── quote.http
│   ├── test.http
│   └── webhooks.http
├── sheets/
│   ├── Stahla - config.csv
│   ├── Stahla - generators.csv
│   ├── Stahla - locations.csv
│   └── Stahla - products.csv
├── tests/ # (Placeholder)
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md         # This file
```

## Setup & Running

1. **Clone the repository.**
2. **Create and configure `.env`:**
    - Copy `.env.example` to `.env`.
    - Fill in API keys: `HUBSPOT_API_KEY`, `BLAND_API_KEY`, `LOGFIRE_TOKEN`, `GOOGLE_MAPS_API_KEY`, `PRICING_WEBHOOK_API_KEY`, and your chosen `LLM_PROVIDER`'s key.
    - Configure `GOOGLE_SHEET_ID` and the `GOOGLE_SHEET_*_RANGE` variables for products, generators, branches, and config tabs/ranges.
    - Set up `GOOGLE_APPLICATION_CREDENTIALS` if using Google Service Account auth.
    - Configure `REDIS_URL`.
    - Configure `APP_BASE_URL`.
    - Configure n8n settings if `N8N_ENABLED=true`.
    - Adjust other settings as needed.
3. **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run locally using Uvicorn:**

    ```bash
    uvicorn app.main:app --reload --port 8000
    ```

5. **Run using Docker Compose:**

    ```bash
    docker-compose up --build
    ```

## Documentation and API

Comprehensive documentation is available to understand the Stahla AI SDR application's architecture, features, and API.

### Detailed Guides

For in-depth information on specific aspects, please refer to the following documents in the `docs/` directory:

- **`api.md`**: Detailed specifications for all API endpoints.
- **`features.md`**: A comprehensive list and description of core application features.
- **`webhooks.md`**: In-depth explanation of webhook functionalities, including models, logic, and examples for Form, HubSpot, Voice (Bland.ai), and Pricing webhooks.
- **`hubspot.md`**: HubSpot integration details, including custom Contact and Deal properties.
- **`services.md`**: Overview of core services like Bland.ai, Google Sheets, Redis, etc.
- **`marvin.md`**: Integration with Marvin AI for classification and data extraction.
- **`faq.md`**: Frequently Asked Questions (to be populated).

### Live API Documentation

Once the application is running:

- Interactive API documentation (Swagger UI) is available at `/docs` on the application server.
- Alternative API documentation (ReDoc) is available at `/redoc` on the application server.
- The markdown documentation files from the `docs/` directory (e.g., `features.md`, `webhooks.md`) are also served as rendered HTML at `/api/v1/docs/{filename}` (e.g., `/api/v1/docs/webhooks.md`).

## Future Considerations (Post-v1)

- SMS intake channel (e.g., via Twilio).
- Frontend UI for the Operational Dashboard.
- Integration with external monitoring/alerting systems for advanced metrics (latency P95, cache hit ratios, historical trends) and alerts.
- Refinement of HubSpot dynamic ID fetching and call data persistence.
- Dedicated Integration & Orchestration Layer (e.g., self-hosted n8n).

## Deploying to Fly.io

This application can be deployed to Fly.io with the provided Docker Compose setup. Follow these steps to deploy:

### Prerequisites

1. Install the Fly.io CLI (flyctl):

   ```
   # On macOS
   brew install flyctl

   # On Linux
   curl -L https://fly.io/install.sh | sh

   # On Windows (using PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. Sign up and log in to Fly.io:

   ```
   flyctl auth signup
   # OR
   flyctl auth login
   ```

3. Ensure you have a valid `.env` file with all required environment variables.

### Automated Deployment

We've created a deployment script to simplify the process:

1. Make the script executable (if not already):

   ```
   chmod +x deploy-to-fly.sh
   ```

2. Run the deployment script:

   ```
   ./deploy-to-fly.sh
   ```

This script will:

- Check if you're logged in to Fly.io
- Create a new Fly.io application if it doesn't exist
- Set up your environment variables from `.env` as Fly.io secrets
- Create volumes for MongoDB and Redis if needed
- Deploy the application using your Docker Compose configuration

### Manual Deployment

If you prefer to deploy manually:

1. Create a new Fly.io application:

   ```
   flyctl apps create stahla
   ```

2. Set environment variables from your `.env` file:

   ```
   # Example for setting individual variables
   flyctl secrets set MONGO_DB_NAME=stahla_dashboard
   ```

3. Create volumes for MongoDB and Redis:

   ```
   flyctl volumes create mongo_data --size 1
   flyctl volumes create redis_data --size 1
   ```

4. Deploy the application:

   ```
   flyctl deploy
   ```

### Monitoring Your Deployment

- View deployment status: `flyctl status -a stahla`
- Check logs: `flyctl logs -a stahla`
- Open the application in a browser: `flyctl open -a stahla`

### Scaling

To scale your application on Fly.io:

```
# Scale to multiple instances
flyctl scale count 3
```

For more information, refer to the [Fly.io documentation](https://fly.io/docs/apps/).

## Deployment

For deployment instructions, see [README-fly.md](./README-fly.md) for Fly.io deployment.

### Cloud MongoDB Setup and Initialization

This application uses a cloud MongoDB service (like MongoDB Atlas) for data storage.

1. **Create a MongoDB Atlas account** (or use another cloud MongoDB service)
2. **Create a MongoDB cluster**
3. **Create a database user** with read/write permissions
4. **Allow network access** from anywhere (or at least from Fly.io IP range)
5. **Initialize the database** before deploying:

```bash
# Run the cloud MongoDB initialization script (connects to your cloud MongoDB)
./initialize-mongodb.sh
```

This script will:

1. Connect to your cloud MongoDB instance
2. Create necessary collections
3. Set up required indexes

This needs to be done from your local machine because the Alpine Linux container in Fly.io doesn't support MongoDB Shell (mongosh) needed for initialization.
