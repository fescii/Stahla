# HubSpot Contacts API Documentation

## Overview

The contacts endpoints provide comprehensive contact retrieval and search functionality for the Stahla AI SDR system. These endpoints integrate with HubSpot's contact database and provide paginated access with advanced filtering capabilities.

## Endpoint Structure

**Base URL**: `/api/v1/hubspot/contacts/`  
**Router**: `ContactsRouter` (app/api/v1/endpoints/hubspot/contacts.py)  
**Authentication**: Required (JWT token via cookie, header, or Authorization)

## Contact Field Loading

Contact fields are dynamically loaded from `contact.json` configuration file:

### Default Contact Fields

- **email** - Contact email address
- **firstname** - Contact first name  
- **lastname** - Contact last name
- **phone** - Contact phone number
- **city** - Contact city
- **zip** - Contact ZIP/postal code
- **address** - Contact street address
- **state** - Contact state/province
- **what_service_do_you_need_** - Service type selection
- **how_many_restroom_stalls_** - Restroom stall quantity
- **how_many_shower_stalls_** - Shower stall quantity
- **how_many_laundry_units_** - Laundry unit quantity
- **event_start_date** - Event start date
- **event_end_date** - Event end date
- **message** - Contact message
- **ai_call_summary** - AI call summary
- **ai_call_sentiment** - AI call sentiment
- **call_recording_url** - Call recording URL
- **call_summary** - Call summary
- **company_size** - Company size
- **createdate** - HubSpot creation date
- **lastmodifieddate** - HubSpot last modified date
- **hs_object_id** - HubSpot object ID

## Core Endpoints

### GET /recent

Retrieves recent contacts ordered by creation date (newest first).

#### Parameters

- **page** (integer, optional): Page number starting from 1 (default: 1)
- **limit** (integer, optional): Items per page, max 100 (default: 10)

#### Response

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "contact_id",
        "properties": {
          "email": "contact@example.com",
          "firstname": "John",
          "lastname": "Doe",
          "phone": "+1234567890",
          "createdate": "2024-01-15T10:30:00Z"
        }
      }
    ],
    "page": 1,
    "limit": 10,
    "total": 150,
    "has_more": true
  }
}
```

#### Implementation Details

- Uses HubSpot search API with `createdate` descending sort
- Loads contact fields from `contact.json`
- Implements offset-based pagination
- Returns HubSpotObject instances

### GET /search

Advanced contact search with multiple filter options.

#### Parameters

- **page** (integer, optional): Page number starting from 1 (default: 1)
- **limit** (integer, optional): Items per page, max 100 (default: 10)
- **service_type** (string, optional): Filter by service type
- **city** (string, optional): Filter by city
- **state** (string, optional): Filter by state/province
- **zip** (string, optional): Filter by ZIP/postal code
- **has_phone** (boolean, optional): Filter contacts with phone numbers
- **has_email** (boolean, optional): Filter contacts with email addresses
- **company_size** (string, optional): Filter by company size
- **created_after** (string, optional): Filter contacts created after date (ISO format)
- **created_before** (string, optional): Filter contacts created before date (ISO format)
- **modified_after** (string, optional): Filter contacts modified after date (ISO format)
- **modified_before** (string, optional): Filter contacts modified before date (ISO format)

#### Response

Same structure as `/recent` endpoint with filtered results.

#### Filter Implementation

Filters are converted to HubSpot search filters:

```python
# Service type filter
HubSpotSearchFilter(
    propertyName="what_service_do_you_need_",
    operator="EQ",
    value=service_type
)

# Date range filter
HubSpotSearchFilter(
    propertyName="createdate",
    operator="GTE",
    value=created_after
)

# Boolean filters
HubSpotSearchFilter(
    propertyName="phone",
    operator="HAS_PROPERTY",
    value=""
)
```

### GET /{contact_id}

Retrieves a single contact by HubSpot ID.

#### Parameters

- **contact_id** (string, required): HubSpot contact ID

#### Response

```json
{
  "success": true,
  "data": {
    "id": "contact_id",
    "properties": {
      "email": "contact@example.com",
      "firstname": "John",
      "lastname": "Doe",
      "phone": "+1234567890",
      "city": "Austin",
      "state": "TX",
      "createdate": "2024-01-15T10:30:00Z"
    }
  }
}
```

#### Error Responses

```json
// Contact not found
{
  "success": false,
  "error": "Contact with ID 'invalid_id' not found",
  "status_code": 404
}

// Service error
{
  "success": false,
  "error": "Failed to fetch contact",
  "details": {"error": "HubSpot API error details"},
  "status_code": 500
}
```

## Search Filter Options

### Service Type Filters

Based on `what_service_do_you_need_` property:

- Restroom Trailer
- Shower Trailer  
- Laundry Trailer
- Porta Potty
- Trailer Repair / Pump Out
- Other

### Geographic Filters

- **city**: Exact city name match
- **state**: State/province code or name
- **zip**: ZIP/postal code

### Data Presence Filters

- **has_phone**: Contacts with phone numbers
- **has_email**: Contacts with email addresses

### Temporal Filters

- **created_after**: ISO 8601 date string
- **created_before**: ISO 8601 date string
- **modified_after**: ISO 8601 date string
- **modified_before**: ISO 8601 date string

## Pagination Implementation

All endpoints use consistent pagination:

```python
# Calculate offset
offset = (page - 1) * limit

# HubSpot search request
search_request = HubSpotSearchRequest(
    filterGroups=filter_groups,
    properties=contact_fields,
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
- **NotFoundError**: Contact ID not found
- **HubSpotAPIError**: HubSpot service errors
- **AuthenticationError**: Invalid or missing credentials

### Error Response Structure

```json
{
  "success": false,
  "error": "Error description",
  "details": {
    "error_type": "ValidationError",
    "field": "contact_id",
    "value": "invalid_id"
  },
  "status_code": 400
}
```

## Usage Examples

### Basic Recent Contacts

```http
GET /api/v1/hubspot/contacts/recent?page=1&limit=10
Authorization: Bearer <jwt_token>
```

### Advanced Search

```http
GET /api/v1/hubspot/contacts/search?service_type=Restroom Trailer&city=Austin&has_phone=true
Authorization: Bearer <jwt_token>
```

### Date Range Search

```http
GET /api/v1/hubspot/contacts/search?created_after=2024-01-01&created_before=2024-12-31
Authorization: Bearer <jwt_token>
```

### Single Contact Retrieval

```http
GET /api/v1/hubspot/contacts/123456789
Authorization: Bearer <jwt_token>
```

## Performance Considerations

### Optimization Tips

1. **Use specific filters**: Reduce result set with targeted filters
2. **Limit field selection**: Only fetch required contact properties
3. **Implement pagination**: Always paginate large result sets
4. **Cache frequently accessed data**: Cache contact field definitions
5. **Monitor rate limits**: Track HubSpot API usage

### Query Efficiency

- **Index usage**: HubSpot indexes standard properties efficiently
- **Filter combination**: Combine filters to reduce API calls
- **Sort optimization**: Use indexed properties for sorting
- **Batch processing**: Process multiple contacts in batches

## Authentication

All contact endpoints require valid JWT authentication:

### Token Sources

1. **Authorization Header**: `Authorization: Bearer <token>`
2. **Custom Header**: `x-access-token: <token>`
3. **Cookie**: `x-access-token=<token>`

### Security Implementation

```python
from app.core.security import get_current_user
from app.models.user import User

async def endpoint(current_user: User = Depends(get_current_user)):
    # Endpoint implementation
```

## Contact Field Configuration

Contact fields are loaded from `/properties/contact.json`:

```json
{
  "inputs": [
    {
      "name": "email",
      "label": "Email",
      "type": "string",
      "fieldType": "email"
    },
    {
      "name": "what_service_do_you_need_",
      "label": "What services do you need?",
      "type": "enumeration",
      "fieldType": "checkbox",
      "options": [
        {"label": "Restroom Trailer", "value": "Restroom Trailer"},
        {"label": "Porta Potty", "value": "Porta Potty"}
      ]
    }
  ]
}
```

## Integration Points

### HubSpot Manager

Contacts endpoints use `HubSpotManager` for API interactions:

```python
from app.services.hubspot import hubspot_manager

# Search contacts
response = await hubspot_manager.search_objects("contacts", search_request)

# Get single contact
contact = await hubspot_manager.get_contact_by_id(contact_id, fields)
```

### Response Models

- **HubSpotObject**: Individual contact data
- **PaginatedResponse**: Paginated result container
- **GenericResponse**: Standardized API response wrapper

## Best Practices

1. **Always authenticate**: Ensure valid JWT tokens
2. **Use pagination**: Implement pagination for all list operations
3. **Handle errors gracefully**: Implement comprehensive error handling
4. **Load fields dynamically**: Use contact.json for field definitions
5. **Log operations**: Track API usage and performance
6. **Validate inputs**: Validate all query parameters
7. **Monitor quotas**: Track HubSpot API rate limits

## Future Enhancements

1. **Advanced filtering**: Additional filter options
2. **Export functionality**: Contact data export capabilities
3. **Bulk operations**: Batch contact processing
4. **Real-time updates**: Webhook integration for contact changes
5. **Analytics integration**: Contact behavior tracking
