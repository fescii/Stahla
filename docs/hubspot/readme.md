# HubSpot API Documentation

This directory contains comprehensive documentation for all HubSpot integrations used in the Stahla AI SDR system.

## API Overview

The Stahla HubSpot implementation provides comprehensive contact and lead management with pagination, filtering, and property synchronization capabilities.

### Core Business Operations

- **[contacts.md](contacts.md)** - Contact fetching and management operations
- **[leads.md](leads.md)** - Lead retrieval and search functionality  
- **[properties.md](properties.md)** - Property definitions and metadata access
- **[operations.md](operations.md)** - Core HubSpot CRUD operations
- **[forms.md](forms.md)** - Form processing and contact creation
- **[sync.md](sync.md)** - Property synchronization with HubSpot

## Common Features

All HubSpot endpoints implement:

- **Pagination**: Hardcoded limit of 10 items per page
- **Authentication**: JWT token validation (cookie/header)
- **Filtering**: Object-specific filter options
- **Sorting**: Temporal and value-based sorting
- **Error Handling**: Robust error logging and graceful degradation
- **Property Loading**: Dynamic field loading from JSON configuration

## API Architecture

### Service Management

- **Service**: `HubSpotManager` (app/services/hubspot/manager.py)
- **Connection**: Async HTTP client with rate limiting
- **Authentication**: HubSpot Private App token

### Data Models

- **Pydantic Models**: Strict typing and validation
- **Object Structure**: Contact and Lead object models
- **Property Mapping**: Dynamic property field mapping

### Performance Optimization

- **Rate Limiting**: Respectful API usage
- **Property Caching**: Efficient property metadata handling
- **Batch Operations**: Optimized bulk operations

## API Integration

### FastAPI Endpoints

- **Router Structure**: Organized by functionality type
- **Response Models**: Consistent pagination and error responses
- **Authentication**: Integrated security middleware

### REST Documentation

- **Examples**: Comprehensive .http files in `/rest/hubspot/`
- **Testing**: Ready-to-use API examples
- **Authentication**: Bearer token examples

## Development Guidelines

### File Organization

Following strict naming conventions:
- All folder names: lowercase only
- File names: descriptive and lowercase
- Maximum folder depth for categorization

### Code Structure

- **Endpoints**: Functionality-specific endpoint files
- **Models**: Pydantic object models
- **Services**: Unified HubSpot service interface
- **Property Sync**: Centralized property management

### Best Practices

1. Always use pagination for list operations
2. Implement proper error handling
3. Use Pydantic models for data validation
4. Log all operations with appropriate context
5. Maintain consistent response formats
6. Load properties dynamically from JSON files

## Getting Started

1. **Read Endpoint Documentation**: Start with the endpoint you need
2. **Check API Examples**: Use REST files for testing
3. **Review Property Files**: Understand contact.json and lead.json
4. **Implement Pagination**: Use consistent patterns
5. **Monitor Rate Limits**: Check HubSpot API usage

## Quick Reference

### Common Operations

```python
# Get paginated contacts
page = 1
offset = (page - 1) * 10
contacts = await hubspot_manager.search_objects("contacts", search_request)

# Load property fields
contact_fields = _load_contact_fields()
lead_fields = _load_lead_fields()

# Get individual objects
contact = await hubspot_manager.get_contact_by_id(contact_id, fields)
```

### Response Patterns

- **Success**: `{"data": PaginatedResponse, "success": true}`
- **Error**: `{"error": "message", "details": {...}, "success": false}`
- **Empty**: `{"data": {"items": [], "total": 0, "page": 1}}`

### Property Configuration

Properties are loaded from JSON files:
- **contact.json**: Contact property definitions
- **lead.json**: Lead property definitions

### Authentication

All endpoints require authentication:
```http
Authorization: Bearer <jwt_token>
# OR
Cookie: x-access-token=<jwt_token>
# OR  
x-access-token: <jwt_token>
```

## Endpoint Structure

### Contact Endpoints

- **GET /api/v1/hubspot/contacts/recent** - Recent contacts with pagination
- **GET /api/v1/hubspot/contacts/search** - Advanced contact search
- **GET /api/v1/hubspot/contacts/{id}** - Individual contact retrieval

### Lead Endpoints

- **GET /api/v1/hubspot/leads/recent** - Recent leads with pagination
- **GET /api/v1/hubspot/leads/search** - Advanced lead search
- **GET /api/v1/hubspot/leads/{id}** - Individual lead retrieval

### Property Endpoints

- **GET /api/v1/hubspot/properties/contacts** - Contact property definitions
- **GET /api/v1/hubspot/properties/leads** - Lead property definitions
- **GET /api/v1/hubspot/properties/all** - All property definitions

### Operation Endpoints

- **POST /api/v1/hubspot/operations/contact** - Create/update contact
- **POST /api/v1/hubspot/operations/lead** - Create lead
- **GET /api/v1/hubspot/operations/owners** - Get HubSpot owners

### Form Endpoints

- **POST /api/v1/hubspot/forms/contact** - Process form submission

### Sync Endpoints

- **POST /api/v1/hubspot/properties/sync/all** - Sync all properties
- **POST /api/v1/hubspot/properties/sync/contacts** - Sync contact properties
- **POST /api/v1/hubspot/properties/sync/leads** - Sync lead properties
- **GET /api/v1/hubspot/properties/sync/status/{type}** - Check sync status

## Configuration Files

### Property Definitions

Properties are defined in JSON files:

#### contact.json
Contains contact property definitions including:
- Field names and labels
- Field types and validation
- Form field mappings
- Display options

#### lead.json  
Contains lead property definitions including:
- Project categorization fields
- AI classification properties
- Site logistics information
- Service requirement details

## Error Handling

### Common Error Types

- **AuthenticationError**: Invalid or missing JWT token
- **ValidationError**: Invalid request data
- **NotFoundError**: Object not found in HubSpot
- **RateLimitError**: HubSpot API rate limit exceeded
- **PropertyError**: Property configuration issues

### Error Response Format

```json
{
  "success": false,
  "error": "Error message",
  "details": {
    "error_type": "ValidationError",
    "field": "email",
    "code": "INVALID_EMAIL"
  },
  "status_code": 400
}
```

## Performance Considerations

### Optimization Tips

1. **Use property filters**: Only fetch required fields
2. **Implement pagination**: Always use pagination for lists
3. **Cache property metadata**: Cache property definitions
4. **Monitor rate limits**: Track HubSpot API usage
5. **Batch operations**: Use bulk operations when possible

### Query Patterns

- **Recent data**: Use createdate/lastmodifieddate sorting
- **Search operations**: Use HubSpot search API efficiently
- **Property access**: Load properties from JSON configuration
- **Filtering**: Apply filters at HubSpot API level

## Support

For detailed implementation examples, see the `/rest/hubspot/` directory with comprehensive API documentation and examples.

For property configuration details, see the `/properties/` directory with contact.json and lead.json definitions.
