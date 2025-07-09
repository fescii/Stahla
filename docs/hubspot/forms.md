# HubSpot Forms API Documentation

## Overview

The forms endpoints handle form processing and contact creation from web form submissions in the Stahla AI SDR system. These endpoints process form data, validate fields, and create contacts in HubSpot with proper property mapping.

## Endpoint Structure

**Base URL**: `/api/v1/hubspot/forms/`  
**Router**: `FormsRouter` (app/api/v1/endpoints/hubspot/forms.py)  
**Authentication**: Required (JWT token via cookie, header, or Authorization)

## Form Processing Architecture

### Data Flow

1. **Form Submission**: Web form submits data to forms endpoint
2. **Data Validation**: Validate form data against Pydantic models
3. **Property Mapping**: Map form fields to HubSpot contact properties
4. **Contact Creation**: Create or update contact in HubSpot
5. **Response Generation**: Return success/error response

### Models Integration

- **SampleContactForm**: Form data validation model
- **HubSpotContactProperties**: HubSpot property mapping model
- **HubSpotManager**: Contact creation service

## Core Endpoints

### POST /contact

Processes form submission and creates a contact in HubSpot.

#### Request Body

```json
{
  "email": "john.doe@example.com",
  "first_name": "John",
  "last_name": "Doe", 
  "phone": "+1-555-123-4567",
  "city": "Austin",
  "zip": "78701",
  "what_service_do_you_need": ["Restroom Trailer", "Porta Potty"],
  "how_many_restroom_stalls": 4,
  "event_start_date": "2024-02-15",
  "event_end_date": "2024-02-17",
  "is_ada_required": true,
  "event_address": "123 Main St, Austin, TX",
  "additional_details": "Corporate event with 200 attendees"
}
```

#### Field Mapping

Form fields are mapped to HubSpot properties:

| Form Field | HubSpot Property | Type | Required |
|------------|------------------|------|----------|
| email | email | string | Yes |
| first_name | firstname | string | Yes |
| last_name | lastname | string | Yes |
| phone | phone | string | No |
| city | city | string | No |
| zip | zip | string | No |
| what_service_do_you_need | what_service_do_you_need_ | array | No |
| how_many_restroom_stalls | how_many_restroom_stalls_ | number | No |
| event_start_date | event_start_date | date | No |
| event_end_date | event_end_date | date | No |
| is_ada_required | is_ada_required | boolean | No |
| event_address | event_address | string | No |
| additional_details | additional_details | text | No |

#### Successful Response

```json
{
  "success": true,
  "data": {
    "contact_id": "12345678901",
    "status": "created",
    "contact": {
      "id": "12345678901",
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
        "is_ada_required": "true",
        "event_address": "123 Main St, Austin, TX",
        "additional_details": "Corporate event with 200 attendees"
      },
      "createdAt": "2024-01-15T10:30:00Z",
      "updatedAt": "2024-01-15T10:30:00Z"
    },
    "form_metadata": {
      "form_type": "contact_form",
      "source": "website",
      "processed_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

#### Error Response

```json
{
  "success": false,
  "error": "Contact creation failed",
  "details": {
    "validation_errors": [
      {
        "field": "email",
        "error": "Invalid email format"
      },
      {
        "field": "phone",
        "error": "Invalid phone number format"
      }
    ],
    "hubspot_error": {
      "status": "error",
      "message": "Required property 'email' is missing",
      "correlationId": "abc123-def456"
    }
  },
  "status_code": 400
}
```

## Form Validation

### Required Fields

The following fields are required for form submission:

- **email**: Valid email address
- **first_name**: Contact's first name
- **last_name**: Contact's last name

### Optional Fields

All other fields are optional but will be included if provided:

- **phone**: Phone number (validated format)
- **city**: City name
- **zip**: ZIP/postal code
- **what_service_do_you_need**: Array of service types
- **how_many_restroom_stalls**: Numeric value
- **event_start_date**: Date in YYYY-MM-DD format
- **event_end_date**: Date in YYYY-MM-DD format
- **is_ada_required**: Boolean value
- **event_address**: Full address string
- **additional_details**: Additional text information

### Field Validation Rules

#### Email Validation

```python
# Email format validation
import re

email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
if not re.match(email_pattern, email):
    raise ValidationError("Invalid email format")
```

#### Phone Validation

```python
# Phone number validation (multiple formats accepted)
phone_patterns = [
    r'^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$',
    r'^\+?[1-9]\d{1,14}$'  # International format
]
```

#### Date Validation

```python
# Date format validation
from datetime import datetime

try:
    parsed_date = datetime.strptime(date_string, '%Y-%m-%d')
except ValueError:
    raise ValidationError("Date must be in YYYY-MM-DD format")
```

#### Service Selection Validation

```python
# Service type validation
valid_services = [
    "Restroom Trailer",
    "Shower Trailer", 
    "Porta Potty",
    "Handwashing Station",
    "Luxury Restroom Trailer"
]

for service in services:
    if service not in valid_services:
        raise ValidationError(f"Invalid service type: {service}")
```

## Form Processing Logic

### Data Transformation

Form data is transformed for HubSpot compatibility:

#### Array to String Conversion

Multiple selections are joined with semicolons:

```python
# Service selection transformation
services = ["Restroom Trailer", "Porta Potty"]
hubspot_value = ";".join(services)  # "Restroom Trailer;Porta Potty"
```

#### Boolean to String Conversion

Boolean values are converted to string:

```python
# Boolean transformation
is_ada_required = True
hubspot_value = str(is_ada_required).lower()  # "true"
```

#### Date Format Standardization

Dates are standardized to HubSpot format:

```python
# Date transformation
from datetime import datetime

form_date = "2024-02-15"
# HubSpot expects dates in specific format
hubspot_date = form_date  # Already in correct format
```

### Property Mapping Process

1. **Load Form Data**: Parse incoming form submission
2. **Validate Fields**: Validate each field against rules
3. **Transform Data**: Convert to HubSpot-compatible format
4. **Map Properties**: Map form fields to HubSpot properties
5. **Create Contact**: Submit to HubSpot via API
6. **Handle Response**: Process success/error response

### Contact Creation Logic

```python
async def create_contact_from_form(form_data: SampleContactForm):
    # Transform form data to HubSpot properties
    properties = HubSpotContactProperties(
        email=form_data.email,
        firstname=form_data.first_name,
        lastname=form_data.last_name,
        phone=form_data.phone,
        city=form_data.city,
        zip=form_data.zip,
        # Additional field mappings...
    )
    
    # Create contact in HubSpot
    contact = await hubspot_manager.create_contact(properties)
    return contact
```

## Error Handling

### Validation Errors

Form validation errors are returned with specific field information:

```json
{
  "success": false,
  "error": "Form validation failed",
  "details": {
    "validation_errors": [
      {
        "field": "email",
        "error": "field required",
        "input": null
      },
      {
        "field": "what_service_do_you_need",
        "error": "Invalid service type: Unknown Service",
        "input": ["Unknown Service"]
      }
    ]
  },
  "status_code": 422
}
```

### HubSpot API Errors

HubSpot API errors are captured and returned:

```json
{
  "success": false,
  "error": "HubSpot API error",
  "details": {
    "status": "error",
    "message": "Contact with email already exists",
    "correlationId": "abc123-def456-ghi789",
    "category": "VALIDATION_ERROR"
  },
  "status_code": 409
}
```

### Network Errors

Network and connectivity errors:

```json
{
  "success": false,
  "error": "Network error",
  "details": {
    "error_type": "ConnectionTimeoutError",
    "message": "Request to HubSpot API timed out",
    "retry_after": 30
  },
  "status_code": 503
}
```

## Form Integration Examples

### Web Form HTML

```html
<form id="contactForm" action="/api/v1/hubspot/forms/contact" method="POST">
  <div class="form-group">
    <label for="email">Email Address *</label>
    <input type="email" id="email" name="email" required>
  </div>
  
  <div class="form-group">
    <label for="first_name">First Name *</label>
    <input type="text" id="first_name" name="first_name" required>
  </div>
  
  <div class="form-group">
    <label for="last_name">Last Name *</label>
    <input type="text" id="last_name" name="last_name" required>
  </div>
  
  <div class="form-group">
    <label for="phone">Phone Number</label>
    <input type="tel" id="phone" name="phone">
  </div>
  
  <div class="form-group">
    <label for="services">What services do you need?</label>
    <div class="checkbox-group">
      <label><input type="checkbox" name="what_service_do_you_need" value="Restroom Trailer"> Restroom Trailer</label>
      <label><input type="checkbox" name="what_service_do_you_need" value="Porta Potty"> Porta Potty</label>
      <label><input type="checkbox" name="what_service_do_you_need" value="Shower Trailer"> Shower Trailer</label>
    </div>
  </div>
  
  <div class="form-group">
    <label for="event_start_date">Event Start Date</label>
    <input type="date" id="event_start_date" name="event_start_date">
  </div>
  
  <button type="submit">Submit Request</button>
</form>
```

### JavaScript Form Submission

```javascript
document.getElementById('contactForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const formData = new FormData(e.target);
  
  // Handle multiple checkbox values
  const services = formData.getAll('what_service_do_you_need');
  
  const submitData = {
    email: formData.get('email'),
    first_name: formData.get('first_name'),
    last_name: formData.get('last_name'),
    phone: formData.get('phone'),
    city: formData.get('city'),
    zip: formData.get('zip'),
    what_service_do_you_need: services,
    how_many_restroom_stalls: parseInt(formData.get('how_many_restroom_stalls')) || null,
    event_start_date: formData.get('event_start_date'),
    event_end_date: formData.get('event_end_date'),
    is_ada_required: formData.get('is_ada_required') === 'on',
    event_address: formData.get('event_address'),
    additional_details: formData.get('additional_details')
  };
  
  try {
    const response = await fetch('/api/v1/hubspot/forms/contact', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getJWTToken()}`
      },
      body: JSON.stringify(submitData)
    });
    
    const result = await response.json();
    
    if (result.success) {
      showSuccessMessage('Contact created successfully!');
      e.target.reset();
    } else {
      showErrorMessage(result.error);
      handleValidationErrors(result.details.validation_errors);
    }
  } catch (error) {
    showErrorMessage('Network error. Please try again.');
  }
});
```

### React Form Component

```jsx
import React, { useState } from 'react';

const ContactForm = () => {
  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    what_service_do_you_need: [],
    event_start_date: '',
    // ... other fields
  });
  
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrors({});
    
    try {
      const response = await fetch('/api/v1/hubspot/forms/contact', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getJWTToken()}`
        },
        body: JSON.stringify(formData)
      });
      
      const result = await response.json();
      
      if (result.success) {
        // Handle success
        onSuccess(result.data);
      } else {
        // Handle validation errors
        const fieldErrors = {};
        result.details.validation_errors?.forEach(error => {
          fieldErrors[error.field] = error.error;
        });
        setErrors(fieldErrors);
      }
    } catch (error) {
      setErrors({ general: 'Network error. Please try again.' });
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleServiceChange = (service, checked) => {
    setFormData(prev => ({
      ...prev,
      what_service_do_you_need: checked
        ? [...prev.what_service_do_you_need, service]
        : prev.what_service_do_you_need.filter(s => s !== service)
    }));
  };
  
  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields with error handling */}
      <div className="form-group">
        <label>Email *</label>
        <input
          type="email"
          value={formData.email}
          onChange={(e) => setFormData(prev => ({...prev, email: e.target.value}))}
          className={errors.email ? 'error' : ''}
        />
        {errors.email && <span className="error-text">{errors.email}</span>}
      </div>
      
      {/* Additional form fields... */}
      
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Submitting...' : 'Submit Request'}
      </button>
    </form>
  );
};
```

## Authentication Requirements

### JWT Token Authentication

All form endpoints require valid JWT authentication:

```http
POST /api/v1/hubspot/forms/contact
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

### Token Sources

1. **Authorization Header**: `Authorization: Bearer <token>`
2. **Custom Header**: `x-access-token: <token>`
3. **Cookie**: `x-access-token=<token>`

### Security Implementation

```python
from app.core.security import get_current_user
from app.models.user import User

@router.post("/contact")
async def create_contact_from_form(
    form_data: SampleContactForm,
    current_user: User = Depends(get_current_user)
):
    # Authenticated form processing
```

## Performance Considerations

### Form Processing Optimization

1. **Async Processing**: Use async/await for HubSpot API calls
2. **Validation Caching**: Cache validation rules
3. **Connection Pooling**: Reuse HTTP connections
4. **Error Handling**: Implement proper error handling
5. **Rate Limiting**: Respect HubSpot API limits

### Response Time Targets

- **Form Validation**: < 100ms
- **HubSpot Contact Creation**: < 2 seconds
- **Total Form Processing**: < 3 seconds
- **Error Response**: < 500ms

### Monitoring Metrics

- **Form Submission Rate**: Forms submitted per minute
- **Success Rate**: Percentage of successful submissions
- **Error Rate**: Frequency of form processing errors
- **Response Time**: Average form processing time
- **HubSpot API Usage**: API call frequency and quotas

## Best Practices

### Form Design

1. **Clear Field Labels**: Use descriptive field labels
2. **Required Field Indicators**: Mark required fields clearly
3. **Validation Feedback**: Provide real-time validation
4. **Progressive Enhancement**: Ensure accessibility
5. **Mobile Optimization**: Optimize for mobile devices

### Data Handling

1. **Data Validation**: Validate all form data
2. **Error Handling**: Provide clear error messages
3. **Privacy Compliance**: Handle personal data properly
4. **Data Security**: Encrypt sensitive data
5. **Audit Logging**: Log form submissions for audit

### Integration Patterns

1. **Async Processing**: Use background processing for complex operations
2. **Webhook Integration**: Set up HubSpot webhooks for data sync
3. **Duplicate Prevention**: Check for existing contacts
4. **Data Enrichment**: Enhance contact data post-creation
5. **Follow-up Automation**: Trigger follow-up workflows

## Troubleshooting

### Common Issues

1. **Validation Errors**: Check field format requirements
2. **Authentication Failures**: Verify JWT token validity
3. **HubSpot API Errors**: Check API key and permissions
4. **Network Timeouts**: Implement retry logic
5. **Duplicate Contacts**: Handle existing contact scenarios

### Debug Steps

1. **Check Form Data**: Validate incoming form payload
2. **Verify Authentication**: Confirm JWT token validity
3. **Test HubSpot Connection**: Verify HubSpot API access
4. **Review Validation Rules**: Check field validation logic
5. **Monitor API Responses**: Check HubSpot API response details

### Error Recovery

1. **Retry Failed Submissions**: Implement retry logic for transient failures
2. **Queue Processing**: Queue failed submissions for retry
3. **Manual Review**: Flag submissions requiring manual review
4. **Data Recovery**: Recover partial submission data
5. **User Notification**: Notify users of submission status
