# HubSpot Properties API Documentation

## Overview

The properties endpoints provide access to contact and lead property definitions and metadata from the Stahla AI SDR system. These endpoints serve property configuration data loaded from JSON files for dynamic field management and form generation.

## Endpoint Structure

**Base URL**: `/api/v1/hubspot/properties/`  
**Router**: `PropertiesRouter` (app/api/v1/endpoints/hubspot/properties.py)  
**Authentication**: Required (JWT token via cookie, header, or Authorization)

## Property Configuration

Properties are loaded from JSON configuration files in the `/properties/` directory:

### Configuration Files

- **contact.json**: Contact property definitions
- **lead.json**: Lead property definitions

### Property Structure

Each property in the JSON files contains:

```json
{
  "name": "field_internal_name",
  "label": "Human Readable Label",
  "type": "field_data_type",
  "fieldType": "form_field_type",
  "groupName": "property_group",
  "description": "Field description",
  "options": [
    {
      "label": "Option Label",
      "value": "option_value",
      "displayOrder": 1
    }
  ]
}
```

## Core Endpoints

### GET /contacts

Retrieves all contact property definitions from contact.json.

#### Response Structure

```json
{
  "success": true,
  "data": {
    "object_type": "contacts",
    "total_properties": 15,
    "field_names": [
      "email",
      "firstname", 
      "lastname",
      "phone",
      "what_service_do_you_need_"
    ],
    "properties": [
      {
        "name": "what_service_do_you_need_",
        "label": "What services do you need?",
        "type": "enumeration",
        "fieldType": "checkbox",
        "groupName": "contactinformation",
        "description": "",
        "options": [
          {
            "label": "Restroom Trailer",
            "value": "Restroom Trailer",
            "displayOrder": 1
          },
          {
            "label": "Porta Potty", 
            "value": "Porta Potty",
            "displayOrder": 4
          }
        ]
      }
    ]
  }
}
```

#### Use Cases

- **Form Generation**: Dynamic form field creation
- **Field Validation**: Property type validation
- **API Integration**: Contact field mapping
- **UI Development**: Display label and option management

### GET /leads

Retrieves all lead property definitions from lead.json.

#### Response Structure

```json
{
  "success": true,
  "data": {
    "object_type": "leads",
    "total_properties": 25,
    "field_names": [
      "project_category",
      "quote_urgency",
      "within_local_service_area",
      "ai_estimated_value"
    ],
    "properties": [
      {
        "name": "project_category",
        "label": "Project Category", 
        "type": "enumeration",
        "fieldType": "select",
        "groupName": "leadqualification",
        "description": "Type of project or inquiry",
        "options": [
          {
            "label": "Event / Porta Potty",
            "value": "Event / Porta Potty",
            "displayOrder": 1
          },
          {
            "label": "Construction / Porta Potty",
            "value": "Construction / Porta Potty", 
            "displayOrder": 2
          }
        ]
      }
    ]
  }
}
```

#### Use Cases

- **Lead Classification**: AI categorization reference
- **Quote Generation**: Value estimation parameters
- **Pipeline Management**: Lead qualification criteria
- **Reporting**: Lead analytics field definitions

### GET /all

Retrieves all property definitions from both contact.json and lead.json.

#### Response Structure

```json
{
  "success": true,
  "data": {
    "contacts": {
      "object_type": "contacts",
      "total_properties": 15,
      "field_names": ["email", "firstname", "lastname"],
      "properties": [...]
    },
    "leads": {
      "object_type": "leads", 
      "total_properties": 25,
      "field_names": ["project_category", "quote_urgency"],
      "properties": [...]
    },
    "summary": {
      "total_contact_properties": 15,
      "total_lead_properties": 25,
      "total_properties": 40
    }
  }
}
```

#### Use Cases

- **System Overview**: Complete property inventory
- **Integration Planning**: Full field mapping
- **Documentation**: Comprehensive property reference
- **Development**: Complete system understanding

### GET /fields/contacts

Retrieves only the field names for contacts (useful for API queries).

#### Response Structure

```json
{
  "success": true,
  "data": [
    "email",
    "firstname",
    "lastname", 
    "phone",
    "city",
    "zip",
    "what_service_do_you_need_",
    "how_many_restroom_stalls_",
    "event_start_date",
    "event_end_date"
  ]
}
```

#### Use Cases

- **API Queries**: Contact field selection
- **Search Filters**: Available filter fields
- **Form Validation**: Required field checking
- **Data Export**: Field selection for exports

### GET /fields/leads

Retrieves only the field names for leads (useful for API queries).

#### Response Structure

```json
{
  "success": true,
  "data": [
    "project_category",
    "ai_intended_use",
    "units_needed",
    "expected_attendance",
    "ada_required",
    "quote_urgency",
    "within_local_service_area",
    "ai_estimated_value"
  ]
}
```

#### Use Cases

- **Lead Analysis**: Available lead fields
- **AI Training**: Feature selection for ML models
- **Reporting**: Lead metrics field selection
- **Pipeline Configuration**: Lead stage field mapping

## Property Types

### Field Data Types

Properties support various data types:

- **string**: Single-line text
- **text**: Multi-line text
- **number**: Numeric values
- **enumeration**: Dropdown/checkbox options
- **boolean**: True/false values
- **date**: Date values
- **datetime**: Date and time values

### Form Field Types

Properties specify form field types:

- **text**: Basic text input
- **textarea**: Multi-line text area
- **select**: Dropdown selection
- **checkbox**: Single checkbox
- **radio**: Radio button group
- **number**: Numeric input
- **email**: Email input
- **phone**: Phone number input
- **date**: Date picker

### Property Groups

Properties are organized by functional groups:

#### Contact Groups

- **contactinformation**: Basic contact details
- **servicerequirements**: Service type and quantity
- **eventdetails**: Event dates and information
- **sitelogistics**: Location and accessibility
- **preferences**: Communication preferences

#### Lead Groups

- **leadqualification**: Lead classification and routing
- **servicerequirements**: Service needs and specifications
- **eventlogistics**: Event details and timeline
- **sitelogistics**: Site conditions and requirements
- **aiclassification**: AI-generated lead data

## Contact Property Examples

### Service Selection

```json
{
  "name": "what_service_do_you_need_",
  "label": "What services do you need?",
  "type": "enumeration",
  "fieldType": "checkbox",
  "options": [
    {"label": "Restroom Trailer", "value": "Restroom Trailer"},
    {"label": "Shower Trailer", "value": "Shower Trailer"},
    {"label": "Porta Potty", "value": "Porta Potty"}
  ]
}
```

### Quantity Fields

```json
{
  "name": "how_many_restroom_stalls_",
  "label": "How Many Restroom Stalls?",
  "type": "number",
  "fieldType": "number",
  "description": "Number of restroom stalls required"
}
```

### Date Fields

```json
{
  "name": "event_start_date",
  "label": "Event Start Date",
  "type": "date",
  "fieldType": "date",
  "description": "Start date for event or rental period"
}
```

## Lead Property Examples

### Project Classification

```json
{
  "name": "project_category",
  "label": "Project Category",
  "type": "enumeration", 
  "fieldType": "select",
  "options": [
    {"label": "Event / Porta Potty", "value": "Event / Porta Potty"},
    {"label": "Construction / Porta Potty", "value": "Construction / Porta Potty"},
    {"label": "Large Event / Trailer / Local", "value": "Large Event / Trailer / Local"}
  ]
}
```

### AI Classification

```json
{
  "name": "ai_classification_confidence",
  "label": "AI Classification Confidence", 
  "type": "number",
  "fieldType": "number",
  "description": "Confidence score (0-1) for AI classification"
}
```

### Boolean Flags

```json
{
  "name": "within_local_service_area",
  "label": "Within Local Service Area",
  "type": "boolean",
  "fieldType": "checkbox",
  "description": "Indicates if location is within service area"
}
```

## Error Handling

### Common Error Types

- **FileNotFoundError**: Property configuration file missing
- **JSONDecodeError**: Invalid JSON in configuration file
- **ValidationError**: Invalid property definition
- **AuthenticationError**: Missing or invalid JWT token

### Error Response Structure

```json
{
  "success": false,
  "error": "Failed to fetch contact properties",
  "details": {
    "error": "File not found: contact.json",
    "file_path": "/properties/contact.json"
  },
  "status_code": 500
}
```

### Fallback Behavior

If property files are missing or invalid, endpoints return empty property lists:

```json
{
  "success": true,
  "data": {
    "object_type": "contacts",
    "total_properties": 0,
    "field_names": [],
    "properties": []
  }
}
```

## Usage Examples

### Get Contact Properties

```http
GET /api/v1/hubspot/properties/contacts
Authorization: Bearer <jwt_token>
```

### Get Lead Field Names

```http
GET /api/v1/hubspot/properties/fields/leads
Authorization: Bearer <jwt_token>
```

### Get All Properties

```http
GET /api/v1/hubspot/properties/all
Authorization: Bearer <jwt_token>
```

## Integration Examples

### Dynamic Form Generation

```javascript
// Fetch contact properties
const response = await fetch('/api/v1/hubspot/properties/contacts');
const { data } = await response.json();

// Generate form fields
data.properties.forEach(property => {
  if (property.fieldType === 'select') {
    createSelectField(property);
  } else if (property.fieldType === 'checkbox') {
    createCheckboxField(property);
  }
});
```

### API Field Selection

```python
# Load contact fields for API query
contact_fields = await get_contact_field_names()

# Use in HubSpot search
search_request = HubSpotSearchRequest(
    properties=contact_fields,
    filterGroups=[],
    limit=10
)
```

### Property Validation

```python
# Validate form data against property definitions
properties = await get_contact_properties()
property_map = {p['name']: p for p in properties['properties']}

def validate_field(field_name, value):
    if field_name in property_map:
        property_def = property_map[field_name]
        return validate_by_type(property_def['type'], value)
```

## Authentication

All property endpoints require valid JWT authentication:

### Token Sources

1. **Authorization Header**: `Authorization: Bearer <token>`
2. **Custom Header**: `x-access-token: <token>`  
3. **Cookie**: `x-access-token=<token>`

### Security Implementation

```python
from app.core.security import get_current_user
from app.models.user import User

async def endpoint(current_user: User = Depends(get_current_user)):
    # Authenticated property access
```

## Performance Considerations

### Optimization Tips

1. **Cache property definitions**: Properties change infrequently
2. **Use field name endpoints**: Fetch only names when full definitions not needed
3. **Implement client-side caching**: Cache property data in applications
4. **Monitor file access**: Track property file read performance
5. **Validate configurations**: Ensure property files are well-formed

### Caching Strategy

```python
# Example caching implementation
from functools import lru_cache

@lru_cache(maxsize=10)
def _load_properties_file(filename: str) -> Dict[str, Any]:
    # Cached property file loading
    return load_json_file(filename)
```

## Best Practices

1. **Version property files**: Track changes to property definitions
2. **Validate JSON structure**: Ensure property files are valid
3. **Document property usage**: Maintain property documentation
4. **Test property loading**: Validate property loading in tests
5. **Monitor property access**: Track property endpoint usage
6. **Backup configurations**: Maintain property file backups
7. **Coordinate updates**: Synchronize property changes with HubSpot

## Configuration Management

### Property File Structure

```
/properties/
├── contact.json     # Contact property definitions
└── lead.json        # Lead property definitions
```

### Version Control

- Track property file changes in version control
- Document property updates and rationale
- Coordinate with HubSpot property changes
- Maintain backwards compatibility

### Deployment

- Validate property files before deployment
- Test property loading after deployment
- Monitor property endpoint performance
- Verify form generation with new properties

## Future Enhancements

1. **Property validation**: Real-time property validation against HubSpot
2. **Dynamic updates**: Live property synchronization
3. **Property versioning**: Multi-version property support
4. **Advanced caching**: Redis-based property caching
5. **Property analytics**: Property usage analytics and optimization
