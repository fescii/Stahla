# HubSpot Leads API Documentation

## Overview

The leads endpoints provide comprehensive lead retrieval and search functionality for the Stahla AI SDR system. These endpoints integrate with HubSpot's deal/lead database and provide paginated access with advanced filtering capabilities for lead qualification and management.

## Endpoint Structure

**Base URL**: `/api/v1/hubspot/leads/`  
**Router**: `LeadsRouter` (app/api/v1/endpoints/hubspot/leads.py)  
**Authentication**: Required (JWT token via cookie, header, or Authorization)

## Lead Field Loading

Lead fields are dynamically loaded from `lead.json` configuration file:

### Default Lead Fields

- **project_category** - Project type classification
- **ai_intended_use** - AI-determined intended use
- **units_needed** - Quantity and type of units required
- **expected_attendance** - Expected number of users
- **ada_required** - ADA compliance requirement
- **additional_services_needed** - Additional services required
- **onsite_facilities** - Existing onsite facilities
- **rental_start_date** - Rental start date
- **rental_end_date** - Rental end date
- **site_working_hours** - Site access hours
- **weekend_service_needed** - Weekend service requirement
- **cleaning_service_needed** - Cleaning service requirement
- **onsite_contact_name** - Onsite contact person
- **onsite_contact_phone** - Onsite contact phone
- **site_ground_type** - Ground surface type
- **site_obstacles** - Site access obstacles
- **water_source_distance** - Distance to water source
- **power_source_distance** - Distance to power source
- **within_local_service_area** - Local service area flag
- **partner_referral_consent** - Partner referral consent
- **needs_human_follow_up** - Human follow-up flag
- **quote_urgency** - Quote urgency level
- **ai_lead_type** - AI lead classification
- **ai_classification_reasoning** - AI classification reasoning
- **ai_classification_confidence** - AI confidence score
- **ai_routing_suggestion** - AI routing recommendation
- **ai_qualification_notes** - AI qualification notes
- **number_of_stalls** - Number of stalls requested
- **event_duration_days** - Event duration in days
- **guest_count_estimate** - Guest count estimate
- **ai_estimated_value** - AI estimated deal value
- **hs_lead_name** - Lead name
- **hs_lead_status** - Lead status
- **createdate** - HubSpot creation date
- **lastmodifieddate** - HubSpot last modified date
- **hs_object_id** - HubSpot object ID

## Core Endpoints

### GET /recent

Retrieves recent leads ordered by creation date (newest first).

#### Request Parameters

- **page** (integer, optional): Page number starting from 1 (default: 1)
- **limit** (integer, optional): Items per page, max 100 (default: 10)

#### Response Structure

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "lead_id",
        "properties": {
          "project_category": "Event / Porta Potty",
          "quote_urgency": "Short-Term",
          "within_local_service_area": "true",
          "ai_estimated_value": "1200.00",
          "createdate": "2024-01-15T10:30:00Z"
        }
      }
    ],
    "page": 1,
    "limit": 10,
    "total": 85,
    "has_more": true
  }
}
```

#### Implementation Details

- Uses HubSpot search API with `createdate` descending sort
- Loads lead fields from `lead.json`
- Implements offset-based pagination
- Returns HubSpotObject instances

### GET /search

Advanced lead search with comprehensive filter options for lead qualification.

#### Request Parameters

- **page** (integer, optional): Page number starting from 1 (default: 1)
- **limit** (integer, optional): Items per page, max 100 (default: 10)
- **project_category** (string, optional): Filter by project category
- **ai_lead_type** (string, optional): Filter by AI lead type
- **quote_urgency** (string, optional): Filter by quote urgency
- **within_local_service_area** (boolean, optional): Filter by service area
- **ada_required** (boolean, optional): Filter by ADA requirement
- **weekend_service_needed** (boolean, optional): Filter by weekend service
- **needs_human_follow_up** (boolean, optional): Filter by follow-up requirement
- **lead_status** (string, optional): Filter by lead status
- **created_after** (string, optional): Filter leads created after date (ISO format)
- **created_before** (string, optional): Filter leads created before date (ISO format)
- **estimated_value_min** (float, optional): Filter by minimum estimated value
- **estimated_value_max** (float, optional): Filter by maximum estimated value

#### Response Structure

Same structure as `/recent` endpoint with filtered results.

#### Filter Implementation Examples

```python
# Project category filter
HubSpotSearchFilter(
    propertyName="project_category",
    operator="EQ",
    value="Event / Porta Potty"
)

# Value range filter
HubSpotSearchFilter(
    propertyName="ai_estimated_value",
    operator="GTE",
    value=str(estimated_value_min)
)

# Boolean filters
HubSpotSearchFilter(
    propertyName="within_local_service_area",
    operator="EQ",
    value="true" if within_local_service_area else "false"
)
```

### GET /{lead_id}

Retrieves a single lead by HubSpot ID with all available fields.

#### Request Parameters

- **lead_id** (string, required): HubSpot lead/deal ID

#### Response Structure

```json
{
  "success": true,
  "data": {
    "id": "lead_id",
    "properties": {
      "project_category": "Construction / Porta Potty",
      "ai_lead_type": "Services",
      "quote_urgency": "Medium-Term",
      "units_needed": "5 portable toilets, 1 handwash station",
      "expected_attendance": "50",
      "ada_required": "true",
      "within_local_service_area": "true",
      "ai_estimated_value": "2500.00",
      "ai_classification_confidence": "0.89",
      "createdate": "2024-01-15T10:30:00Z"
    }
  }
}
```

#### Error Responses

```json
// Lead not found
{
  "success": false,
  "error": "Lead with ID 'invalid_id' not found",
  "status_code": 404
}

// Service error  
{
  "success": false,
  "error": "Failed to fetch lead",
  "details": {"error": "HubSpot API error details"},
  "status_code": 500
}
```

## Lead Classification Filters

### Project Categories

Based on `project_category` property:

- Event / Porta Potty
- Construction / Porta Potty
- Small Event / Trailer / Local
- Small Event / Trailer / Not Local
- Large Event / Trailer / Local
- Large Event / Trailer / Not Local
- Disaster Relief / Trailer / Local
- Disaster Relief / Trailer / Not Local
- Construction / Company Trailer / Local
- Construction / Company Trailer / Not Local
- Facility / Trailer / Local
- Facility / Trailer / Not Local

### AI Lead Types

Based on `ai_lead_type` property:

- Services
- Logistics
- Leads
- Disqualify

### Quote Urgency Levels

Based on `quote_urgency` property:

- Short-Term
- Long-Term/Planning
- Medium-Term
- Immediate/Urgent
- Other

### Service Area Filters

- **within_local_service_area**: Boolean filter for local service coverage
- **ada_required**: Boolean filter for ADA compliance needs
- **weekend_service_needed**: Boolean filter for weekend service
- **needs_human_follow_up**: Boolean filter for manual review

### Value-Based Filters

- **estimated_value_min**: Minimum estimated deal value
- **estimated_value_max**: Maximum estimated deal value

### Temporal Filters

- **created_after**: ISO 8601 date string
- **created_before**: ISO 8601 date string

## AI Classification Properties

### AI Confidence Scoring

Leads include AI classification with confidence metrics:

```json
{
  "ai_lead_type": "Services",
  "ai_classification_confidence": "0.89",
  "ai_classification_reasoning": "Clear service request with specific requirements",
  "ai_routing_suggestion": "Sales Pipeline - Qualified",
  "ai_qualification_notes": "High-value lead with clear timeline"
}
```

### Value Estimation

AI provides estimated deal value:

```json
{
  "ai_estimated_value": "2500.00",
  "units_needed": "5 portable toilets, 1 handwash station",
  "expected_attendance": "50"
}
```

## Pagination Implementation

Consistent pagination across all endpoints:

```python
# Calculate offset
offset = (page - 1) * limit

# HubSpot search request
search_request = HubSpotSearchRequest(
    filterGroups=filter_groups,
    properties=lead_fields,
    sorts=[{"propertyName": "createdate", "direction": "DESCENDING"}],
    limit=limit,
    after=str(offset) if offset > 0 else None
)

# Response with pagination info
PaginatedResponse(
    items=response.results,
    page=page,
    limit=limit,
    total=response.total,
    has_more=(offset + limit) < response.total
)
```

## Error Handling

### Common Error Types

- **ValidationError**: Invalid parameter values
- **NotFoundError**: Lead ID not found  
- **HubSpotAPIError**: HubSpot service errors
- **AuthenticationError**: Invalid or missing credentials
- **ClassificationError**: AI classification failures

### Error Response Structure

```json
{
  "success": false,
  "error": "Error description",
  "details": {
    "error_type": "ValidationError",
    "field": "estimated_value_min",
    "value": "invalid_number"
  },
  "status_code": 400
}
```

## Usage Examples

### Basic Recent Leads

```http
GET /api/v1/hubspot/leads/recent?page=1&limit=10
Authorization: Bearer <jwt_token>
```

### Lead Classification Search

```http
GET /api/v1/hubspot/leads/search?ai_lead_type=Services&quote_urgency=Short-Term&within_local_service_area=true
Authorization: Bearer <jwt_token>
```

### Value Range Search

```http
GET /api/v1/hubspot/leads/search?estimated_value_min=1000&estimated_value_max=5000
Authorization: Bearer <jwt_token>
```

### High-Priority Leads

```http
GET /api/v1/hubspot/leads/search?needs_human_follow_up=true&quote_urgency=Immediate/Urgent
Authorization: Bearer <jwt_token>
```

### Single Lead Details

```http
GET /api/v1/hubspot/leads/123456789
Authorization: Bearer <jwt_token>
```

## Performance Considerations

### Optimization Tips

1. **Use specific filters**: Combine multiple filters for targeted results
2. **Filter by AI classification**: Use AI lead types for efficient sorting
3. **Value-based filtering**: Use estimated value ranges for qualification
4. **Local service filtering**: Filter by service area for operational efficiency
5. **Cache lead properties**: Cache lead field definitions

### Query Efficiency

- **Classification indexes**: AI lead types are efficiently indexed
- **Value filters**: Numeric ranges are optimized
- **Boolean filters**: Service flags use efficient boolean operations
- **Date ranges**: Temporal filters use indexed date properties

## Authentication

All lead endpoints require valid JWT authentication:

### Token Sources

1. **Authorization Header**: `Authorization: Bearer <token>`
2. **Custom Header**: `x-access-token: <token>`
3. **Cookie**: `x-access-token=<token>`

### Security Implementation

```python
from app.core.security import get_current_user
from app.models.user import User

async def endpoint(current_user: User = Depends(get_current_user)):
    # Endpoint implementation with authenticated user
```

## Lead Field Configuration

Lead fields are loaded from `/properties/lead.json`:

```json
{
  "inputs": [
    {
      "name": "project_category",
      "label": "Project Category",
      "type": "enumeration",
      "fieldType": "select",
      "options": [
        {"label": "Event / Porta Potty", "value": "Event / Porta Potty"},
        {"label": "Construction / Porta Potty", "value": "Construction / Porta Potty"}
      ]
    },
    {
      "name": "ai_estimated_value",
      "label": "AI Estimated Value",
      "type": "number",
      "fieldType": "currency"
    }
  ]
}
```

## Integration Points

### HubSpot Manager

Lead endpoints use `HubSpotManager` for API interactions:

```python
from app.services.hubspot import hubspot_manager

# Search leads
response = await hubspot_manager.search_objects("leads", search_request)

# Get single lead
lead = await hubspot_manager.get_lead_by_id(lead_id, fields)
```

### Response Models

- **HubSpotObject**: Individual lead data
- **PaginatedResponse**: Paginated result container  
- **GenericResponse**: Standardized API response wrapper

## Lead Qualification Workflow

### AI Classification Process

1. **Initial Classification**: AI categorizes leads by type
2. **Confidence Scoring**: Confidence level assigned (0-1)
3. **Value Estimation**: AI estimates potential deal value
4. **Routing Suggestion**: AI recommends pipeline routing
5. **Human Review Flag**: Flags complex leads for manual review

### Qualification Filters

```python
# High-value, local leads
high_value_local = {
    "within_local_service_area": True,
    "estimated_value_min": 2000,
    "ai_lead_type": "Services"
}

# Urgent follow-up required
urgent_followup = {
    "needs_human_follow_up": True,
    "quote_urgency": "Immediate/Urgent"
}

# ADA-compliant projects
ada_projects = {
    "ada_required": True,
    "project_category": "Large Event / Trailer / Local"
}
```

## Best Practices

1. **Authenticate all requests**: Ensure valid JWT tokens
2. **Use classification filters**: Leverage AI categorization for efficiency
3. **Monitor confidence scores**: Track AI classification accuracy
4. **Implement value-based routing**: Use estimated values for prioritization
5. **Flag complex leads**: Use human follow-up flags appropriately
6. **Track conversion rates**: Monitor lead to deal conversion
7. **Optimize for service area**: Prioritize local service area leads

## Future Enhancements

1. **Advanced AI scoring**: Enhanced lead qualification algorithms
2. **Predictive analytics**: Lead conversion probability
3. **Automated routing**: Dynamic pipeline assignment
4. **Integration workflows**: Enhanced CRM automation
5. **Real-time updates**: Live lead status tracking
