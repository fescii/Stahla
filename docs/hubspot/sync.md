# HubSpot Property Sync API Documentation

## Overview

The property sync endpoints manage synchronization of property definitions between the Stahla AI SDR system and HubSpot. These endpoints handle property creation, updates, and status monitoring for both contact and lead properties.

## Endpoint Structure

**Base URL**: `/api/v1/hubspot/properties/sync/`  
**Router**: `SyncRouter` (app/api/v1/endpoints/hubspot/sync.py)  
**Authentication**: Required (JWT token via cookie, header, or Authorization)

## Service Integration

Property sync operations use the `PropertySyncManager` service for:

- Property definition management
- HubSpot API integration
- Sync status tracking
- Error handling and logging

## Core Endpoints

### POST /all

Synchronizes all properties (contacts and leads) to HubSpot.

#### Request

```http
POST /api/v1/hubspot/properties/sync/all
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

#### Response Structure

```json
{
  "success": true,
  "data": {
    "sync_status": "completed",
    "contacts": {
      "status": "success",
      "synced_properties": 15,
      "failed_properties": 0,
      "properties": [
        "email",
        "firstname",
        "lastname",
        "what_service_do_you_need_"
      ]
    },
    "leads": {
      "status": "success", 
      "synced_properties": 25,
      "failed_properties": 0,
      "properties": [
        "project_category",
        "ai_estimated_value",
        "quote_urgency"
      ]
    },
    "summary": {
      "total_synced": 40,
      "total_failed": 0,
      "sync_duration": "2.4s"
    }
  }
}
```

#### Error Response

```json
{
  "success": false,
  "error": "Property sync failed",
  "details": {
    "contacts": {
      "status": "partial_failure",
      "failed_properties": ["custom_field_with_error"]
    },
    "leads": {
      "status": "failed",
      "error": "HubSpot API rate limit exceeded"
    }
  },
  "status_code": 500
}
```

#### Use Cases

- **Initial Setup**: First-time property configuration
- **Bulk Updates**: Synchronized property definition updates
- **System Migration**: Moving property definitions to new HubSpot instance
- **Recovery**: Restoring properties after HubSpot changes

### POST /contacts

Synchronizes only contact properties to HubSpot.

#### Request

```http
POST /api/v1/hubspot/properties/sync/contacts
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

#### Response Structure

```json
{
  "success": true,
  "data": {
    "object_type": "contacts",
    "sync_status": "completed",
    "synced_properties": 15,
    "failed_properties": 0,
    "properties": [
      {
        "name": "what_service_do_you_need_",
        "label": "What services do you need?",
        "sync_status": "created",
        "hubspot_property_id": "property_12345"
      },
      {
        "name": "event_start_date",
        "label": "Event Start Date", 
        "sync_status": "updated",
        "hubspot_property_id": "property_67890"
      }
    ],
    "sync_details": {
      "created": 8,
      "updated": 7,
      "skipped": 0,
      "errors": 0
    }
  }
}
```

#### Use Cases

- **Contact Form Updates**: Sync new contact form fields
- **Property Modifications**: Update contact property definitions
- **Selective Sync**: Sync only contact-related properties
- **Contact Pipeline Updates**: Maintain contact property consistency

### POST /leads

Synchronizes only lead properties to HubSpot.

#### Request

```http
POST /api/v1/hubspot/properties/sync/leads
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

#### Response Structure

```json
{
  "success": true,
  "data": {
    "object_type": "leads",
    "sync_status": "completed", 
    "synced_properties": 25,
    "failed_properties": 0,
    "properties": [
      {
        "name": "project_category",
        "label": "Project Category",
        "sync_status": "created",
        "hubspot_property_id": "property_54321"
      },
      {
        "name": "ai_estimated_value",
        "label": "AI Estimated Value",
        "sync_status": "updated", 
        "hubspot_property_id": "property_98765"
      }
    ],
    "sync_details": {
      "created": 12,
      "updated": 13,
      "skipped": 0,
      "errors": 0
    }
  }
}
```

#### Use Cases

- **Lead Qualification Updates**: Sync lead scoring properties
- **AI Model Integration**: Update AI classification properties
- **Pipeline Configuration**: Maintain lead stage properties
- **Reporting Setup**: Sync lead analytics properties

### GET /status/{sync_type}

Retrieves the status of the last property sync operation.

#### Parameters

- **sync_type**: Type of sync to check (`all`, `contacts`, `leads`)

#### Request

```http
GET /api/v1/hubspot/properties/sync/status/all
Authorization: Bearer <jwt_token>
```

#### Response Structure

```json
{
  "success": true,
  "data": {
    "sync_type": "all",
    "last_sync": {
      "timestamp": "2024-01-15T10:30:00Z",
      "status": "completed",
      "duration": "2.4s",
      "total_properties": 40,
      "successful": 40,
      "failed": 0
    },
    "contacts": {
      "status": "completed",
      "properties_synced": 15,
      "last_update": "2024-01-15T10:30:00Z"
    },
    "leads": {
      "status": "completed", 
      "properties_synced": 25,
      "last_update": "2024-01-15T10:30:00Z"
    },
    "next_scheduled_sync": "2024-01-16T10:30:00Z"
  }
}
```

#### Status Values

- **completed**: Sync completed successfully
- **in_progress**: Sync currently running
- **failed**: Sync failed with errors
- **partial**: Some properties synced, some failed
- **pending**: Sync queued but not started

#### Use Cases

- **Monitoring**: Track sync operation progress
- **Debugging**: Identify sync failures and issues
- **Scheduling**: Plan next sync operations
- **Reporting**: Sync operation analytics

## Property Sync Process

### Sync Operation Flow

1. **Load Property Definitions**: Load from contact.json and lead.json
2. **Validate Properties**: Verify property structure and requirements
3. **Compare with HubSpot**: Check existing properties in HubSpot
4. **Identify Changes**: Determine create/update operations needed
5. **Execute Sync**: Perform HubSpot API calls
6. **Track Results**: Log success/failure for each property
7. **Return Status**: Provide comprehensive sync results

### Property Mapping

Properties are mapped between local JSON and HubSpot format:

#### Local Property Format

```json
{
  "name": "what_service_do_you_need_",
  "label": "What services do you need?", 
  "type": "enumeration",
  "fieldType": "checkbox",
  "groupName": "contactinformation",
  "description": "Service selection checkboxes",
  "options": [
    {
      "label": "Restroom Trailer",
      "value": "Restroom Trailer",
      "displayOrder": 1
    }
  ]
}
```

#### HubSpot Property Format

```json
{
  "name": "what_service_do_you_need_",
  "label": "What services do you need?",
  "type": "enumeration", 
  "fieldType": "checkbox",
  "groupName": "contactinformation",
  "description": "Service selection checkboxes",
  "options": [
    {
      "label": "Restroom Trailer",
      "value": "Restroom Trailer",
      "displayOrder": 1,
      "hidden": false
    }
  ],
  "hubspotDefined": false,
  "calculated": false,
  "externalOptions": false
}
```

### Sync Strategies

#### Create Strategy

For new properties not existing in HubSpot:

1. Validate property definition
2. Transform to HubSpot format
3. Create via HubSpot Properties API
4. Store HubSpot property ID
5. Verify creation success

#### Update Strategy

For existing properties with changes:

1. Retrieve current HubSpot property
2. Compare with local definition
3. Identify required updates
4. Update via HubSpot Properties API
5. Verify update success

#### Skip Strategy

For properties that match HubSpot:

1. Compare property definitions
2. Skip if no changes detected
3. Log skipped properties
4. Continue to next property

## Error Handling

### Common Error Types

- **RateLimitError**: HubSpot API rate limit exceeded
- **PropertyExistsError**: Property already exists with different definition
- **ValidationError**: Property definition validation failed
- **AuthenticationError**: HubSpot API authentication failed
- **NetworkError**: Network connectivity issues

### Error Response Patterns

#### Rate Limit Error

```json
{
  "success": false,
  "error": "HubSpot API rate limit exceeded",
  "details": {
    "retry_after": 60,
    "remaining_requests": 0,
    "reset_time": "2024-01-15T10:31:00Z"
  },
  "status_code": 429
}
```

#### Property Validation Error

```json
{
  "success": false,
  "error": "Property validation failed", 
  "details": {
    "property_name": "invalid_field_name",
    "validation_errors": [
      "Property name contains invalid characters",
      "Property type not supported"
    ]
  },
  "status_code": 400
}
```

#### Partial Sync Error

```json
{
  "success": false,
  "error": "Partial sync failure",
  "details": {
    "successful_properties": 35,
    "failed_properties": 5,
    "failures": [
      {
        "property": "custom_field_1",
        "error": "Property already exists with different type"
      }
    ]
  },
  "status_code": 207
}
```

### Retry Logic

The sync service implements retry logic for transient failures:

1. **Exponential Backoff**: Increasing delays between retries
2. **Rate Limit Handling**: Respect HubSpot rate limits
3. **Circuit Breaker**: Stop retries after consistent failures
4. **Selective Retry**: Retry only retriable errors

## Authentication & Security

### Required Authentication

All sync endpoints require valid JWT authentication:

```python
from app.core.security import get_current_user
from app.models.user import User

async def sync_endpoint(current_user: User = Depends(get_current_user)):
    # Authenticated sync operation
```

### Permission Requirements

Sync operations require administrative permissions:

- **Property Management**: Create/update HubSpot properties
- **API Access**: HubSpot Private App token with properties scope
- **System Admin**: Elevated user permissions for sync operations

### Security Considerations

1. **Token Security**: Secure HubSpot API token storage
2. **Operation Logging**: Log all sync operations for audit
3. **Access Control**: Restrict sync operations to authorized users
4. **Validation**: Validate all property definitions before sync
5. **Rollback**: Plan for sync rollback scenarios

## Performance Optimization

### Sync Performance Tips

1. **Batch Operations**: Group property operations when possible
2. **Rate Limit Awareness**: Respect HubSpot API limits
3. **Concurrent Sync**: Process contacts and leads in parallel
4. **Incremental Sync**: Only sync changed properties
5. **Caching**: Cache HubSpot property definitions

### Monitoring & Metrics

#### Key Metrics

- **Sync Duration**: Time taken for sync operations
- **Success Rate**: Percentage of successful property syncs
- **Error Rate**: Frequency of sync failures
- **Property Count**: Number of properties synced
- **API Usage**: HubSpot API call consumption

#### Performance Targets

- **Sync Duration**: < 5 seconds for full sync
- **Success Rate**: > 99% for property sync
- **Error Recovery**: < 1 minute for retry completion
- **API Efficiency**: < 10 API calls per property

## Best Practices

### Property Management

1. **Version Control**: Track property definition changes
2. **Staging**: Test property changes in staging environment
3. **Documentation**: Document property purposes and usage
4. **Naming Conventions**: Follow consistent property naming
5. **Validation**: Validate properties before sync

### Sync Operations

1. **Scheduled Sync**: Regular automated sync operations
2. **Change Detection**: Monitor property definition changes
3. **Rollback Planning**: Plan for sync failure recovery
4. **Testing**: Test sync operations thoroughly
5. **Monitoring**: Monitor sync performance and errors

### Integration Patterns

1. **CI/CD Integration**: Include sync in deployment pipeline
2. **Configuration Management**: Manage properties as code
3. **Environment Sync**: Sync across development environments
4. **Backup Strategy**: Backup property configurations
5. **Disaster Recovery**: Plan for property recovery scenarios

## Usage Examples

### Sync All Properties

```bash
curl -X POST \
  https://api.stahla.com/api/v1/hubspot/properties/sync/all \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json"
```

### Check Sync Status

```bash
curl -X GET \
  https://api.stahla.com/api/v1/hubspot/properties/sync/status/all \
  -H "Authorization: Bearer <jwt_token>"
```

### Sync Only Contacts

```bash
curl -X POST \
  https://api.stahla.com/api/v1/hubspot/properties/sync/contacts \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json"
```

## Integration Examples

### Automated Sync in CI/CD

```yaml
# GitHub Actions example
- name: Sync HubSpot Properties
  run: |
    curl -X POST \
      ${{ secrets.API_BASE_URL }}/api/v1/hubspot/properties/sync/all \
      -H "Authorization: Bearer ${{ secrets.JWT_TOKEN }}" \
      -f || exit 1
```

### Property Change Detection

```python
# Python example for monitoring property changes
import json
from pathlib import Path

def detect_property_changes():
    contact_path = Path("properties/contact.json")
    lead_path = Path("properties/lead.json")
    
    if contact_path.stat().st_mtime > last_sync_time:
        trigger_contact_sync()
    
    if lead_path.stat().st_mtime > last_sync_time:
        trigger_lead_sync()
```

### Sync Status Monitoring

```javascript
// JavaScript monitoring example
async function monitorSyncStatus() {
  const response = await fetch('/api/v1/hubspot/properties/sync/status/all');
  const { data } = await response.json();
  
  if (data.last_sync.status === 'failed') {
    alerting.sendAlert('HubSpot property sync failed');
  }
}
```

## Troubleshooting

### Common Issues

1. **Sync Failures**: Check HubSpot API limits and authentication
2. **Property Conflicts**: Resolve property definition conflicts
3. **Rate Limiting**: Implement proper retry with backoff
4. **Authentication**: Verify JWT token and HubSpot API token
5. **Property Validation**: Ensure property definitions are valid

### Debug Steps

1. **Check API Logs**: Review HubSpot API response logs
2. **Validate Properties**: Verify property JSON structure
3. **Test Authentication**: Confirm JWT and HubSpot tokens
4. **Monitor Rate Limits**: Check HubSpot API usage
5. **Review Property Conflicts**: Identify conflicting properties

### Recovery Procedures

1. **Partial Sync Recovery**: Retry failed properties individually
2. **Authentication Recovery**: Refresh JWT and HubSpot tokens
3. **Rate Limit Recovery**: Wait for rate limit reset
4. **Property Conflict Resolution**: Update conflicting property definitions
5. **Full Sync Recovery**: Perform complete property sync reset
