# Stahla AI SDR System - Implementation Guide

## System Overview

The Stahla AI SDR System is a comprehensive FastAPI backend that automates Sales Development Representative (SDR) tasks for Stahla, including real-time price quoting, AI-powered lead intake, classification, and operational dashboard capabilities. The system processes voice calls, web forms, and emails to capture complete lead information, generate instant quotes, and seamlessly integrate with HubSpot.

## Live Demo System

**Test the system before implementation:**

- URL: `https://stahla.fly.dev`
- Email: `isfescii@gmail.com`
- Password: `pass1234`

## Core Capabilities

### AI Intake Agent

- Processes voice calls from Bland.ai voice agents
- Handles web form submissions and email inquiries
- Automated follow-up for incomplete submissions
- Dynamic questioning and information gathering

### Real-time Pricing Engine

- Instant quote generation (<500ms response time)
- Dynamic pricing rules synced from Google Sheets
- Distance-based delivery calculations
- Seasonal pricing adjustments

### Lead Classification & Routing

- AI-powered lead classification (Services, Logistics, Leads, Disqualify)
- Automatic team routing based on project type and location
- Business rules engine for consistent classification

### HubSpot Integration

- Creates and updates contacts and deals automatically
- High data completeness (≥95% field completion)
- Pipeline management and stage progression
- Call summaries and recordings sync

### Operational Dashboard

- Real-time system monitoring and metrics
- Cache performance and sync status tracking
- Recent activity and error monitoring
- Manual cache management capabilities

### Workflow Automation

- n8n integration for complex workflows
- Automated email notifications to sales reps
- Background task processing
- Extensible framework for future enhancements

## Implementation Options

### Option 1: Local Development Setup

#### Requirements

- Python 3.11+
- API keys (see Environment Configuration section)
- MongoDB instance
- Redis instance (optional)

#### Setup Steps

1. **Download Project Files**

   ```bash
   git clone https://github.com/fescii/Stahla.git
   cd Stahla
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   - Copy the provided `.env.example` to `.env`
   - Update with your API keys (see Environment Configuration)

4. **Run System**

   ```bash
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   System available at: `http://localhost:8000`

### Option 2: Docker Deployment

#### Prerequisites

- Docker and Docker Compose installed

#### Setup Steps

1. **Prepare Environment File**
   - Configure `.env` file as described in Environment Configuration

2. **Deploy with Docker**

   ```bash
   docker-compose up --build
   ```

   System available at: `http://localhost:8000`

### Option 3: Fly.io Cloud Deployment

#### Prerequisites

- Fly.io account
- Fly CLI installed

#### Setup Steps

1. **Install Fly CLI**

   ```bash
   # macOS
   brew install flyctl
   
   # Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows PowerShell
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login to Fly.io**

   ```bash
   flyctl auth login
   ```

3. **Deploy Application**

   ```bash
   flyctl launch
   flyctl deploy
   ```

   Follow prompts to configure app name and region.

## Environment Configuration

A complete `.env.example` file is provided with the system. Copy this file to `.env` and configure the following sections:

### Essential Configuration

#### Application Settings

```env
PROJECT_NAME=Stahla AI SDR
APP_BASE_URL=https://your-domain.com
DEV=false
API_V1_STR=/api/v1
```

#### HubSpot Integration

```env
HUBSPOT_API_KEY=your_hubspot_api_key_here
HUBSPOT_ACCESS_TOKEN=your_hubspot_access_token
HUBSPOT_PORTAL_ID=your_hubspot_portal_id
HUBSPOT_CLIENT_SECRET=your_client_secret

# Pipeline Configuration
HUBSPOT_LEADS_PIPELINE_ID=default
HUBSPOT_SERVICES_PIPELINE_ID=your_services_pipeline_id
HUBSPOT_LOGISTICS_PIPELINE_ID=your_logistics_pipeline_id

# Stage Configuration
HUBSPOT_NEW_LEAD_STAGE_ID=appointmentscheduled
HUBSPOT_HOT_LEAD_STAGE_ID=qualifiedtobuy
HUBSPOT_WARM_LEAD_STAGE_ID=presentationscheduled
HUBSPOT_COLD_LEAD_STAGE_ID=decisionmakerboughtin
HUBSPOT_DISQUALIFIED_STAGE_ID=closedlost
HUBSPOT_NEEDS_REVIEW_STAGE_ID=appointmentscheduled
HUBSPOT_SERVICES_NEW_STAGE_ID=appointmentscheduled
HUBSPOT_LOGISTICS_NEW_STAGE_ID=appointmentscheduled

# Association Type IDs
HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_CONTACT=1
HUBSPOT_ASSOCIATION_TYPE_ID_DEAL_TO_COMPANY=2
HUBSPOT_ASSOCIATION_TYPE_ID_COMPANY_TO_CONTACT=3
HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_CONTACT=4
HUBSPOT_ASSOCIATION_TYPE_ID_TICKET_TO_DEAL=5

# Default Pipeline Names
HUBSPOT_DEFAULT_DEAL_PIPELINE_NAME=Sales Pipeline
HUBSPOT_DEFAULT_TICKET_PIPELINE_NAME=Support Pipeline
HUBSPOT_DEFAULT_LEAD_LIFECYCLE_STAGE=lead

# Cache Settings (seconds)
CACHE_TTL_HUBSPOT_PIPELINES=3600
CACHE_TTL_HUBSPOT_STAGES=3600
CACHE_TTL_HUBSPOT_OWNERS=3600
```

#### Bland.ai Configuration

```env
BLAND_API_KEY=your_bland_ai_api_key_here
BLAND_API_URL=https://api.bland.ai
BLAND_PATHWAY_ID=your_pathway_id
BLAND_LOCATION_TOOL_ID=your_location_tool_id
BLAND_QUOTE_TOOL_ID=your_quote_tool_id
BLAND_VOICE_ID=your_voice_id
BLAND_PHONE_PREFIX=+1
```

#### AI Classification

```env
# Choose Provider: openai, anthropic, gemini, or marvin
LLM_PROVIDER=openai

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic Configuration (alternative)
ANTHROPIC_API_KEY=your_anthropic_key_here

# Gemini Configuration (alternative)
GEMINI_API_KEY=your_gemini_key_here

# Marvin Configuration (alternative)
MARVIN_API_KEY=your_marvin_key_here

# Model Selection
MODEL_NAME=gpt-4

# Marvin Logging
MARVIN_LOG_LEVEL=ERROR
MARVIN_VERBOSE=false

# Classification Method
CLASSIFICATION_METHOD=ai
```

#### Database Configuration

```env
# MongoDB Settings
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_DB_NAME=stahla_ai
MONGO_ROOT_USER=your_mongo_user
MONGO_ROOT_PASSWORD=your_mongo_password
MONGO_USER=your_app_user
MONGO_PASSWORD=your_app_password
MONGO_CONNECTION_URL=mongodb://user:pass@host:port/database
```

#### Location Services

```env
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
LOCAL_DISTANCE_THRESHOLD_MILES=180
```

#### Pricing Configuration

```env
PRICING_WEBHOOK_API_KEY=your_pricing_webhook_api_key
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_SHEET_PRODUCTS_TAB_NAME=products
GOOGLE_SHEET_GENERATORS_TAB_NAME=generators
GOOGLE_SHEET_BRANCHES_RANGE=locations
GOOGLE_SHEET_CONFIG_RANGE=config
GOOGLE_SHEET_STATES_RANGE=states
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

#### Optional Services

```env
# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Monitoring
LOGFIRE_TOKEN=your_logfire_token
LOGFIRE_IGNORE_NO_CONFIG=false

# n8n Integration
N8N_ENABLED=false
N8N_WEBHOOK_URL=your_n8n_webhook_url
N8N_API_KEY=your_n8n_api_key
N8N_WEBHOOK_URL_CLASSIFICATION_DONE=your_classification_webhook_url

# Authentication
JWT_SECRET_KEY=your_jwt_secret_key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
BCRYPT_SALT_ROUNDS=10

# Initial Admin User
FIRST_SUPERUSER_EMAIL=admin@your-domain.com
FIRST_SUPERUSER_PASSWORD=your_secure_password
```

## System Operation

### Multi-Channel Lead Intake

**Voice Calls (Bland.ai)**

1. Customer calls voice agent
2. AI conducts dynamic conversation to gather requirements
3. Call recorded and transcribed
4. Data extracted and processed

**Web Forms**

1. Customer submits web form
2. System processes submission
3. Automated follow-up initiated for incomplete data
4. Callback scheduled within 1 minute if needed

**Email Processing**

1. Email received via webhook
2. AI parses content and extracts lead information
3. Auto-reply sent with follow-up questions
4. Lead data populated in system

### Real-time Pricing Engine

**Quote Generation Process**

1. Location and requirements captured
2. Distance to nearest branch calculated
3. Pricing rules applied from Google Sheets
4. Quote generated in <500ms
5. Quote delivered via webhook or dashboard

**Pricing Components**

- Base equipment rates by type and duration
- Delivery distance calculations
- Seasonal pricing multipliers
- Additional services and generators
- State-specific configurations

### Lead Processing Flow

1. **Information Extraction**: AI extracts contact details, project requirements, location, timing
2. **Data Validation**: System validates and normalizes extracted information
3. **Classification**: AI classifies lead based on business rules and requirements
4. **Routing**: Lead routed to appropriate team (Services/Logistics/General)
5. **HubSpot Sync**: Contact and deal created with complete information
6. **Quote Generation**: Real-time pricing calculated if applicable
7. **Team Notification**: Sales rep notified with context and next steps

### Information Extraction

The AI automatically identifies and extracts:

- Contact information (name, phone, email, company)
- Project details (event type, location, dates, duration)
- Service requirements (unit count, ADA needs, power/water availability)
- Budget information when mentioned

### Lead Classification Rules

**Services Team**

- Small events (under 20 units, under 5 days)
- Local construction projects
- Porta potty rentals
- Projects within 3 hours of service hubs

**Logistics Team**

- Large events (20+ units or 7+ specialty trailers)
- Long-distance projects (over 3 hours from hubs)
- Disaster relief projects
- Complex multi-location deployments

**General Leads**

- Projects requiring human review
- Incomplete call information
- Special requirements outside standard categories

### HubSpot Integration

For qualified leads, the system automatically:

- Creates contact with extracted information
- Creates deal in appropriate pipeline
- Assigns to correct team based on classification
- Adds call summary and AI reasoning as notes

## Web Interface

**Dashboard Access:** Navigate to your system URL

**Available Views:**

- Recent call activity and classifications
- Lead conversion statistics
- Team performance metrics
- System health monitoring

## API Integration

### Webhook Endpoints

**Voice Call Processing**

```
POST /api/v1/webhooks/voice
```

Receives voice call data from Bland.ai

**Web Form Processing**

```
POST /api/v1/webhooks/form
```

Processes web form submissions

**HubSpot Integration**

```
POST /api/v1/webhooks/hubspot
```

Handles HubSpot webhook events

**Real-time Pricing**

```
POST /api/v1/webhooks/pricing/quote
```

Generates instant price quotes

**Location Lookup**

```
POST /api/v1/webhooks/pricing/location_lookup
```

Calculates delivery distances and caching

### Management Endpoints

**Lead Classification**

```http
GET /api/v1/classify/recent
POST /api/v1/classify/voice
```

**Dashboard Analytics**

```http
GET /api/v1/dashboard/status
GET /api/v1/dashboard/recent
GET /api/v1/dashboard/cache
```

**System Monitoring**

```http
GET /api/v1/health
GET /api/v1/dashboard/sync
```

**Cache Management**

```http
POST /api/v1/dashboard/cache/clear
POST /api/v1/dashboard/sync/trigger
```

### Bland.ai Integration Setup

Configure these webhook URLs in your Bland.ai dashboard:

**Primary Voice Webhook**

```
https://your-domain.com/api/v1/webhooks/voice
```

**Pricing Integration** (if using real-time quotes during calls)

```
https://your-domain.com/api/v1/webhooks/pricing/quote
```

**API Documentation**
Visit: `https://your-domain.com/docs`

## Monitoring and Troubleshooting

### System Health Check

Access: `https://your-domain.com/api/v1/health`

### Common Configuration Issues

**API Key Errors**

- Verify all required API keys are configured in `.env`
- Restart system after configuration changes

**Classification Failures**

- Confirm AI provider API key validity
- Check API usage limits and billing status

**HubSpot Sync Issues**

- Verify HubSpot API permissions
- Confirm pipeline and stage IDs exist in HubSpot

**Location Processing Errors**

- Validate Google Maps API key
- Ensure geocoding API is enabled

### Log Monitoring

System events are logged for troubleshooting. Configure Logfire token for advanced monitoring and alerting.

## Security Considerations

- Secure `.env` file and never expose API keys
- Use HTTPS in production deployments
- Implement regular API key rotation
- Monitor API usage for unusual activity
- Configure proper firewall rules for database access

## Support and Maintenance

### Technical Documentation

- Complete API documentation available at `/docs`
- System architecture details in project documentation
- Error logs available through configured monitoring

### Configuration Updates

- Business rule modifications require code changes
- Pipeline routing adjustments configurable via environment variables
- Custom field mapping requires development updates

---

**Implementation Support:** Contact your technical team for assistance with setup, configuration, or customization requirements.

## How It Works

### 1. Voice Call Processing

When someone calls your Bland.ai voice agent:

- The call is automatically recorded and transcribed
- At the end of the call, Bland.ai sends the transcript to your system
- The AI analyzes the conversation and extracts key information

### 2. Information Extraction

The AI automatically finds and extracts:

- **Contact Info**: Name, phone, email, company
- **Project Details**: Type of event, location, dates, requirements  
- **Service Needs**: Number of units, ADA requirements, power/water needs
- **Budget Information**: Any budget mentioned during the call

### 3. Smart Classification

Based on the extracted information, the system classifies each lead:

- **Services Team**: Local projects, small events, porta potty rentals
- **Logistics Team**: Large events, long-distance projects, specialty trailers
- **General Leads**: Needs human review or doesn't fit standard categories
- **Disqualified**: Wrong numbers, spam, or non-relevant calls

### 4. Automatic HubSpot Sync

For qualified leads, the system:

- Creates a new contact in HubSpot with extracted information
- Creates a deal in the appropriate pipeline
- Assigns to the correct team based on classification
- Adds notes with the call summary and AI reasoning

## Web Dashboard

Access your dashboard at: `http://localhost:8000`

The dashboard shows:

- Recent call activity and classifications
- Lead conversion statistics  
- Team performance metrics
- System health and API status

## API Endpoints

### View Call Classifications

```
GET /api/v1/classify/recent
```

### Process Manual Classification  

```
POST /api/v1/classify/voice
```

### Check System Health

```
GET /api/v1/health
```

### View API Documentation

Visit: `http://localhost:8000/docs`

## Configuring Bland.ai Integration

1. **Set Webhook URL** in your Bland.ai dashboard:

   ```
   https://your-domain.com/api/v1/webhooks/voice
   ```

2. **Configure Voice Agent** with these variables in Bland.ai:
   - `service_address` - Delivery location
   - `contact_name` - Customer name
   - `contact_email` - Customer email
   - `units_needed` - Number of units required
   - `project_category` - Type of project/event

## Monitoring and Troubleshooting

### Check System Status

Visit: `http://localhost:8000/api/v1/health`

### View Logs

The system logs important events. Check the console output or configure Logfire for advanced monitoring.

### Common Issues

**"No API Key" Errors**

- Check your `.env` file has all required API keys
- Restart the system after adding new keys

**"Classification Failed" Messages**  

- Verify your AI provider (OpenAI/Anthropic) API key is valid
- Check you have sufficient API credits

**"HubSpot Sync Failed"**

- Confirm HubSpot API key has proper permissions
- Verify pipeline IDs exist in your HubSpot account

**"Location Processing Error"**

- Check Google Maps API key is valid and has geocoding enabled

## Team Routing Rules

The system uses these rules to route leads:

### Services Team

- Small events (under 20 units, under 5 days)
- Local construction projects
- Porta potty rentals
- Projects within 3 hours of service hubs

### Logistics Team  

- Large events (20+ units or 7+ specialty trailers)
- Long-distance projects (over 3 hours from hubs)
- Disaster relief projects
- Complex multi-location deployments

### General Leads

- Projects needing human review
- Incomplete information from calls
- Special requirements not fitting standard categories

## Getting Help

### Technical Support

- Check the API documentation at `/docs`
- Review system logs for error details
- Verify all API keys are properly configured

### Business Rules

- Contact your account manager to adjust classification rules
- Request pipeline/team routing changes
- Discuss custom field mapping requirements

## Security Notes

- Keep your `.env` file secure and never share API keys
- Use HTTPS in production environments
- Regularly rotate API keys for security
- Monitor API usage to detect unusual activity

---

**Need assistance?** Contact your technical team with any questions about setup or configuration.
