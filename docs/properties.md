# HubSpot Property Sync Documentation

## Overview

The HubSpot Property Sync functionality allows you to automatically synchronize property definitions from local JSON files to HubSpot. This ensures that all required properties are available in HubSpot before attempting to create or update contacts and leads.

## Features

- **Automatic Property Detection**: Reads property definitions from `contact.json` and `lead.json` files
- **Intelligent Sync**: Only creates properties that don't already exist in HubSpot
- **Validation**: Validates property definitions before creating them
- **Detailed Reporting**: Provides comprehensive sync results including created, existing, and failed properties
- **Batch Operations**: Supports syncing all properties or specific object types
- **Status Checking**: Allows checking the current status of properties in HubSpot

## API Endpoints

### 1. Sync All Properties

```http
POST /api/v1/hubspot/properties/sync/all
```

Syncs all properties from both `contact.json` and `lead.json` to HubSpot.

**Response:**

```json
{
  "success": true,
  "data": {
    "contacts": {
      "object_type": "contacts",
      "created": [...],
      "existing": [...],
      "failed": [],
      "status": "completed"
    },
    "leads": {
      "object_type": "leads", 
      "created": [...],
      "existing": [...],
      "failed": [],
      "status": "completed"
    },
    "summary": {
      "total_created": 25,
      "total_existing": 10,
      "total_failed": 0,
      "status": "completed"
    }
  }
}
```

### 2. Sync Contact Properties

```http
POST /api/v1/hubspot/properties/sync/contacts
```

Syncs only contact properties from `contact.json` to HubSpot.

### 3. Sync Lead Properties

```http
POST /api/v1/hubspot/properties/sync/leads
```

Syncs only lead properties from `lead.json` to HubSpot.

### 4. Check Property Status

```http
GET /api/v1/hubspot/properties/status/{object_type}?property_names=prop1,prop2
```

Checks the status of specific properties in HubSpot.

**Parameters:**

- `object_type`: Either "contacts" or "leads"
- `property_names` (optional): Comma-separated list of property names to check

**Response:**

```json
{
  "success": true,
  "data": {
    "object_type": "contacts",
    "total_checked": 5,
    "existing": 3,
    "missing": 2,
    "details": {
      "firstname": {
        "exists": true,
        "type": "string",
        "label": "First name",
        "fieldType": "text",
        "groupName": "contactinformation"
      },
      "custom_property": {
        "exists": false,
        "error": "Property not found"
      }
    }
  }
}
```

## Property Definition Format

Properties are defined in JSON files with the following structure:

```json
{
  "inputs": [
    {
      "name": "property_name",
      "label": "Display Label",
      "type": "string|number|enumeration|date|bool",
      "fieldType": "text|textarea|select|checkbox|number|date",
      "groupName": "contactinformation|leadinformation",
      "description": "Property description",
      "options": [
        {
          "label": "Option Label",
          "value": "option_value",
          "displayOrder": 1
        }
      ]
    }
  ]
}
```

### Property Types

- **string**: Text properties (fieldType: text, textarea, email, phonenumber)
- **number**: Numeric properties (fieldType: number)
- **enumeration**: Select/dropdown properties (fieldType: select, checkbox, radio)
- **date**: Date properties (fieldType: date)
- **bool**: Boolean properties (fieldType: booleancheckbox)

### Required Fields

- `name`: Property internal name (must be unique)
- `label`: Display name in HubSpot
- `type`: Property data type
- `fieldType`: HubSpot field type
- `groupName`: Property group for organization

### Optional Fields

- `description`: Property description
- `options`: For enumeration types, list of available options

## Usage Examples

### Basic Sync

```bash
# Sync all properties
curl -X POST "http://localhost:8000/api/v1/hubspot/properties/sync/all"

# Sync only contact properties
curl -X POST "http://localhost:8000/api/v1/hubspot/properties/sync/contacts"
```

### Check Property Status

```bash
# Check all contact properties
curl "http://localhost:8000/api/v1/hubspot/properties/status/contacts"

# Check specific properties
curl "http://localhost:8000/api/v1/hubspot/properties/status/contacts?property_names=firstname,email,phone"
```

## Integration

The property sync functionality is integrated into the HubSpot manager and can be used programmatically:

```python
from app.services.hubspot import hubspot_manager

# Sync all properties
results = await hubspot_manager.property_sync.sync_all_properties()

# Sync specific object type
contact_results = await hubspot_manager.property_sync.sync_contact_properties()
lead_results = await hubspot_manager.property_sync.sync_lead_properties()

# Check property status
status = await hubspot_manager.property_sync.check_property_status(
    "contacts", 
    ["firstname", "lastname", "email"]
)
```

## Error Handling

The sync process includes comprehensive error handling:

- **Invalid property definitions**: Properties with missing required fields are skipped
- **Enumeration validation**: Enumeration properties without options are skipped
- **HubSpot API errors**: API errors are captured and reported in the results
- **Network issues**: Connection problems are handled gracefully

## Best Practices

1. **Regular Sync**: Run property sync before deploying new features that use new properties
2. **Validation**: Always validate your JSON files before syncing
3. **Testing**: Use the status check endpoint to verify properties exist before using them
4. **Monitoring**: Check the sync results for any failed properties
5. **Backup**: Keep your property definitions in version control

## Files

- `app/services/hubspot/properties/sync.py`: Main sync manager implementation
- `app/properties/contact.json`: Contact property definitions
- `app/properties/lead.json`: Lead property definitions
- `rest/property-sync.http`: REST API test file
