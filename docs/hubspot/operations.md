# HubSpot Operations API Documentation

## Overview

The operations endpoints provide core HubSpot CRUD (Create, Read, Update, Delete) operations for the Stahla AI SDR system. These endpoints handle direct contact and lead management, owner information retrieval, and basic HubSpot object operations.

## Endpoint Structure

**Base URL**: `/api/v1/hubspot/operations/`  
**Router**: `OperationsRouter` (app/api/v1/endpoints/hubspot/operations.py)  
**Authentication**: Required (JWT token via cookie, header, or Authorization)

## Service Integration

Operations use the `HubSpotManager` service for:

- Direct HubSpot API interactions
- Contact and lead object management
- Owner and team information
- Error handling and logging

## Core Endpoints

### POST /contact

Creates or updates a contact in HubSpot using HubSpot contact properties.

#### Request Body

```json
{
  "email": "john.doe@example.com",
  "firstname": "John",
  "lastname": "Doe",
  "phone": "+1-555-123-4567",
  "city": "Austin",
  "zip": "78701",
  "what_service_do_you_need_": "Restroom Trailer;Porta Potty",
  "how_many_restroom_stalls_": "4",
  "event_start_date": "2024-02-15",
  "event_end_date": "2024-02-17",
  "is_ada_required": "true",
  "event_address": "123 Main St, Austin, TX",
  "additional_details": "Corporate event with 200 attendees",
  "hubspot_owner_id": "12345"
}
```

#### Property Mapping

Uses `HubSpotContactProperties` model for direct property mapping:

| Property | Type | Description |
|----------|------|-------------|
| email | string | Contact email (required) |
| firstname | string | First name |
| lastname | string | Last name |
| phone | string | Phone number |
| city | string | City |
| zip | string | ZIP code |
| what_service_do_you_need_ | string | Services (semicolon-separated) |
| how_many_restroom_stalls_ | string | Number of stalls |
| event_start_date | string | Event start (YYYY-MM-DD) |
| event_end_date | string | Event end (YYYY-MM-DD) |
| is_ada_required | string | ADA requirement ("true"/"false") |
| event_address | string | Event address |
| additional_details | string | Additional information |
| hubspot_owner_id | string | HubSpot owner ID |

#### Successful Response

```json
{
  "success": true,
  "data": {
    "id": "12345678901",
    "status": "created",
    "properties": {
      "email": "john.doe@example.com",
      "firstname": "John",
      "lastname": "Doe",
      "phone": "+1-555-123-4567",
      "city": "Austin",
      "zip": "78701",
      "what_service_do_you_need_": "Restroom Trailer;Porta Potty",
      "how_many_restroom_stalls_": "4",
      "event_start_date": "2024-02-15",
      "event_end_date": "2024-02-17",
      "hubspot_owner_id": "12345",
      "createdate": "2024-01-15T10:30:00Z",
      "lastmodifieddate": "2024-01-15T10:30:00Z"
    },
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-15T10:30:00Z",
    "archived": false
  }
}
```

#### Error Response

```json
{
  "success": false,
  "error": "Contact creation failed",
  "details": {
    "status": "error",
    "message": "Property 'email' is required",
    "correlationId": "abc123-def456-ghi789",
    "category": "VALIDATION_ERROR",
    "errors": [
      {
        "message": "Property 'email' is required",
        "in": "properties.email"
      }
    ]
  },
  "status_code": 400
}
```

#### Use Cases

- **Direct Contact Creation**: Create contacts with specific HubSpot properties
- **Contact Updates**: Update existing contact information
- **API Integration**: Programmatic contact management
- **Data Migration**: Bulk contact creation operations
- **CRM Synchronization**: Sync contact data from external systems

### POST /lead

Creates a lead in HubSpot using lead-specific properties.

#### Request Body

```json
{
  "email": "jane.smith@example.com",
  "firstname": "Jane",
  "lastname": "Smith",
  "phone": "+1-555-987-6543",
  "project_category": "Event / Porta Potty",
  "ai_intended_use": "Corporate Event",
  "units_needed": "8",
  "expected_attendance": "200",
  "ada_required": "true",
  "quote_urgency": "High",
  "within_local_service_area": "true",
  "ai_estimated_value": "1500.00",
  "ai_classification_confidence": "0.95",
  "lead_source": "Website Form",
  "hubspot_owner_id": "54321"
}
```

#### Lead Property Mapping

Uses lead-specific properties for qualification and routing:

| Property | Type | Description |
|----------|------|-------------|
| project_category | string | Type of project |
| ai_intended_use | string | AI-determined use case |
| units_needed | string | Number of units required |
| expected_attendance | string | Expected event attendance |
| ada_required | string | ADA compliance requirement |
| quote_urgency | string | Urgency level (High/Medium/Low) |
| within_local_service_area | string | Service area flag |
| ai_estimated_value | string | AI-estimated project value |
| ai_classification_confidence | string | AI confidence score |
| lead_source | string | Lead origination source |

#### Successful Response

```json
{
  "success": true,
  "data": {
    "id": "98765432101",
    "status": "created",
    "properties": {
      "email": "jane.smith@example.com",
      "firstname": "Jane",
      "lastname": "Smith",
      "phone": "+1-555-987-6543",
      "project_category": "Event / Porta Potty",
      "ai_intended_use": "Corporate Event",
      "units_needed": "8",
      "expected_attendance": "200",
      "ada_required": "true",
      "quote_urgency": "High",
      "within_local_service_area": "true",
      "ai_estimated_value": "1500.00",
      "ai_classification_confidence": "0.95",
      "lead_source": "Website Form",
      "hubspot_owner_id": "54321",
      "createdate": "2024-01-15T10:30:00Z",
      "lastmodifieddate": "2024-01-15T10:30:00Z"
    },
    "createdAt": "2024-01-15T10:30:00Z",
    "updatedAt": "2024-01-15T10:30:00Z",
    "archived": false
  }
}
```

#### Use Cases

- **Lead Qualification**: Create leads with AI classification data
- **Pipeline Management**: Set up leads for sales pipeline
- **Quote Generation**: Create leads with quote requirements
- **Lead Routing**: Assign leads to appropriate sales owners
- **AI Integration**: Store AI-generated lead insights

### GET /owners

Retrieves all HubSpot owners for assignment and routing purposes.

#### Request

```http
GET /api/v1/hubspot/operations/owners
Authorization: Bearer <jwt_token>
```

#### Response Structure

```json
{
  "success": true,
  "data": [
    {
      "id": "12345",
      "userId": 67890,
      "email": "sales@stahla.com",
      "firstName": "John",
      "lastName": "Sales",
      "createdAt": "2023-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z",
      "archived": false,
      "teams": [
        {
          "id": "team123",
          "name": "Sales Team",
          "primary": true
        }
      ]
    },
    {
      "id": "54321",
      "userId": 13579,
      "email": "manager@stahla.com",
      "firstName": "Jane",
      "lastName": "Manager",
      "createdAt": "2023-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z",
      "archived": false,
      "teams": [
        {
          "id": "team456",
          "name": "Management Team",
          "primary": true
        }
      ]
    }
  ]
}
```

#### Owner Properties

Each owner object contains:

- **id**: HubSpot owner ID (used for assignments)
- **userId**: HubSpot user ID
- **email**: Owner's email address
- **firstName**: Owner's first name
- **lastName**: Owner's last name
- **createdAt**: Owner creation timestamp
- **updatedAt**: Last update timestamp
- **archived**: Whether owner is archived
- **teams**: Array of team memberships

#### Use Cases

- **Lead Assignment**: Assign leads to specific sales owners
- **Contact Routing**: Route contacts to appropriate owners
- **Team Management**: Understand team structure and assignments
- **Automation Setup**: Configure automated owner assignment rules
- **Reporting**: Owner-based performance reporting

## CRUD Operations

### Contact Operations

#### Create Contact

Creates a new contact with HubSpot properties:

```python
contact_data = HubSpotContactProperties(
    email="new@example.com",
    firstname="New",
    lastname="Contact"
)
contact = await hubspot_manager.create_contact(contact_data)
```

#### Update Contact

Updates existing contact by ID:

```python
updated_data = HubSpotContactProperties(
    firstname="Updated",
    lastname="Name"
)
contact = await hubspot_manager.update_contact(contact_id, updated_data)
```

#### Get Contact

Retrieves contact by ID with specified properties:

```python
properties = ["email", "firstname", "lastname", "phone"]
contact = await hubspot_manager.get_contact_by_id(contact_id, properties)
```

### Lead Operations

#### Create Lead

Creates a lead with lead-specific properties:

```python
lead_data = HubSpotContactProperties(
    email="lead@example.com",
    project_category="Event / Porta Potty",
    quote_urgency="High"
)
lead = await hubspot_manager.create_contact(lead_data)  # Leads use contact object
```

#### Lead Classification

Set AI classification properties:

```python
classification_data = {
    "ai_classification_confidence": "0.92",
    "ai_estimated_value": "2500.00",
    "ai_intended_use": "Construction Site"
}
```

### Owner Operations

#### Get All Owners

Retrieve all HubSpot owners:

```python
owners = await hubspot_manager.get_owners()
```

#### Filter Active Owners

Get only non-archived owners:

```python
active_owners = [
    owner for owner in owners 
    if not owner.get("archived", False)
]
```

## Error Handling

### Common Error Types

#### Validation Errors

```json
{
  "success": false,
  "error": "Validation error",
  "details": {
    "message": "Property validation failed",
    "errors": [
      {
        "message": "Invalid email format",
        "in": "properties.email"
      }
    ]
  },
  "status_code": 400
}
```

#### Duplicate Contact Errors

```json
{
  "success": false,
  "error": "Contact already exists",
  "details": {
    "message": "Contact with this email already exists",
    "existing_contact_id": "12345678901",
    "correlationId": "abc123-def456"
  },
  "status_code": 409
}
```

#### Authentication Errors

```json
{
  "success": false,
  "error": "Authentication failed",
  "details": {
    "message": "Invalid or expired HubSpot API key",
    "category": "UNAUTHORIZED"
  },
  "status_code": 401
}
```

#### Rate Limit Errors

```json
{
  "success": false,
  "error": "Rate limit exceeded",
  "details": {
    "message": "HubSpot API rate limit exceeded",
    "retry_after": 60,
    "daily_limit": 1000000,
    "daily_usage": 999999
  },
  "status_code": 429
}
```

### Error Recovery Strategies

1. **Retry Logic**: Implement exponential backoff for transient errors
2. **Rate Limit Handling**: Respect HubSpot rate limits and retry after delay
3. **Duplicate Detection**: Handle existing contacts gracefully
4. **Validation Fallback**: Provide data cleaning for validation errors
5. **Circuit Breaker**: Stop requests after consecutive failures

## Authentication & Security

### JWT Authentication

All operations require valid JWT authentication:

```python
from app.core.security import get_current_user
from app.models.user import User

@router.post("/contact")
async def create_contact(
    contact_data: HubSpotContactProperties,
    current_user: User = Depends(get_current_user)
):
    # Authenticated operation
```

### Permission Requirements

Operations require appropriate permissions:

- **Contact Creation**: Contact management permissions
- **Lead Creation**: Lead/deal management permissions
- **Owner Access**: User management permissions
- **API Access**: HubSpot Private App token with required scopes

### Security Best Practices

1. **Input Validation**: Validate all input data
2. **Data Sanitization**: Clean user input
3. **Access Control**: Restrict operations to authorized users
4. **Audit Logging**: Log all operations for compliance
5. **Token Security**: Secure HubSpot API token storage

## Performance Optimization

### Operation Performance

#### Async Operations

All HubSpot operations use async/await:

```python
async def create_contact_operation(contact_data):
    contact = await hubspot_manager.create_contact(contact_data)
    return contact
```

#### Connection Pooling

Reuse HTTP connections for better performance:

```python
# HubSpotManager uses session pooling
async with aiohttp.ClientSession() as session:
    # Reuse connection for multiple requests
```

#### Batch Operations

Process multiple operations efficiently:

```python
# Batch contact creation
contacts = await asyncio.gather(*[
    hubspot_manager.create_contact(data)
    for data in contact_list
])
```

### Performance Targets

- **Contact Creation**: < 2 seconds per contact
- **Owner Retrieval**: < 1 second for all owners
- **Bulk Operations**: < 5 seconds for 10 contacts
- **Error Handling**: < 500ms for error responses

### Monitoring Metrics

- **Operation Latency**: Average response time per operation
- **Success Rate**: Percentage of successful operations
- **Error Rate**: Frequency of operation failures
- **API Usage**: HubSpot API quota consumption
- **Throughput**: Operations per minute

## Usage Examples

### Create Contact

```bash
curl -X POST \
  https://api.stahla.com/api/v1/hubspot/operations/contact \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "firstname": "John",
    "lastname": "Doe",
    "phone": "+1-555-123-4567"
  }'
```

### Create Lead

```bash
curl -X POST \
  https://api.stahla.com/api/v1/hubspot/operations/lead \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane.smith@example.com",
    "firstname": "Jane",
    "lastname": "Smith",
    "project_category": "Event / Porta Potty",
    "quote_urgency": "High"
  }'
```

### Get Owners

```bash
curl -X GET \
  https://api.stahla.com/api/v1/hubspot/operations/owners \
  -H "Authorization: Bearer <jwt_token>"
```

## Integration Examples

### Contact Creation Workflow

```python
async def create_contact_workflow(form_data):
    # Transform form data to HubSpot properties
    contact_props = HubSpotContactProperties(
        email=form_data.email,
        firstname=form_data.first_name,
        lastname=form_data.last_name,
        # Map additional fields...
    )
    
    # Create contact
    contact = await create_contact_operation(contact_props)
    
    # Log creation
    logger.info(f"Contact created: {contact['id']}")
    
    # Trigger follow-up automation
    await trigger_welcome_sequence(contact['id'])
    
    return contact
```

### Lead Assignment Logic

```python
async def assign_lead_to_owner(lead_data):
    # Get available owners
    owners = await get_owners_operation()
    active_owners = [o for o in owners if not o.get("archived")]
    
    # Assign based on criteria
    if lead_data.get("quote_urgency") == "High":
        # Assign to senior sales rep
        owner = next(o for o in active_owners if "senior" in o.get("firstName", "").lower())
    else:
        # Round-robin assignment
        owner = active_owners[len(active_owners) % len(active_owners)]
    
    # Update lead with owner
    lead_data["hubspot_owner_id"] = owner["id"]
    
    # Create lead
    lead = await create_lead_operation(lead_data)
    return lead
```

### Bulk Contact Import

```python
async def bulk_import_contacts(contact_list):
    results = []
    batch_size = 10
    
    for i in range(0, len(contact_list), batch_size):
        batch = contact_list[i:i + batch_size]
        
        # Process batch concurrently
        batch_results = await asyncio.gather(*[
            create_contact_operation(contact)
            for contact in batch
        ], return_exceptions=True)
        
        results.extend(batch_results)
        
        # Rate limiting pause
        await asyncio.sleep(1)
    
    return results
```

## Best Practices

### Operation Design

1. **Atomic Operations**: Keep operations focused and atomic
2. **Error Handling**: Implement comprehensive error handling
3. **Validation**: Validate all input data before processing
4. **Logging**: Log all operations for audit and debugging
5. **Performance**: Optimize for speed and efficiency

### Data Management

1. **Property Consistency**: Use consistent property naming
2. **Data Quality**: Validate and clean data before operations
3. **Deduplication**: Check for duplicate contacts/leads
4. **Data Enrichment**: Enhance data with additional information
5. **Archival**: Properly archive outdated records

### Integration Patterns

1. **Async Processing**: Use async patterns for better performance
2. **Batch Operations**: Group operations for efficiency
3. **Error Recovery**: Implement retry and fallback strategies
4. **Monitoring**: Monitor operation performance and errors
5. **Scaling**: Design for horizontal scaling

## Troubleshooting

### Common Issues

1. **Authentication Failures**: Check JWT and HubSpot API tokens
2. **Validation Errors**: Verify property formats and requirements
3. **Rate Limiting**: Monitor HubSpot API usage and implement backoff
4. **Duplicate Contacts**: Implement duplicate detection and handling
5. **Network Issues**: Handle connection timeouts and retries

### Debug Steps

1. **Check API Logs**: Review HubSpot API request/response logs
2. **Validate Input**: Verify input data format and completeness
3. **Test Connectivity**: Confirm HubSpot API accessibility
4. **Monitor Quotas**: Check HubSpot API usage limits
5. **Review Permissions**: Verify HubSpot API token permissions

### Performance Issues

1. **Slow Operations**: Check network latency and API response times
2. **High Error Rates**: Analyze error patterns and causes
3. **Rate Limit Hits**: Implement proper rate limiting and backoff
4. **Memory Usage**: Monitor application memory consumption
5. **Concurrent Load**: Test under expected concurrent usage
