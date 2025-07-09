# Pricing API Reference

This document provides comprehensive API reference for all pricing-related endpoints, including request/response formats, authentication, and error handling.

## Authentication

All pricing API endpoints require API key authentication:

```http
Authorization: Bearer {your_api_key}
```

API keys are managed through the authentication system and can have different permission levels:

- **quote:read** - View existing quotes
- **quote:create** - Generate new quotes  
- **location:lookup** - Perform location lookups
- **pricing:admin** - Administrative access to pricing configuration

## Base URL

```
Production: https://api.stahla.com
Development: http://localhost:8000
```

## Endpoints Overview

| Endpoint | Method | Purpose | Auth Required |
|----------|---------|---------|---------------|
| `/api/v1/webhook/quote/generate` | POST | Generate quote | Yes |
| `/api/v1/webhook/location/lookup/sync` | POST | Sync location lookup | Yes |
| `/api/v1/webhook/location/lookup/async` | POST | Async location lookup | Yes |
| `/api/v1/mongo/quotes/*` | GET | Quote management | Yes |

## Quote Generation

### Generate Quote

Generate a real-time price quote for restroom trailer rental.

**Endpoint:** `POST /api/v1/webhook/quote/generate`

**Request Headers:**

```http
Content-Type: application/json
Authorization: Bearer {api_key}
```

**Request Body:**

```json
{
  "delivery_location": "string",
  "trailer_type": "string", 
  "rental_start_date": "string (YYYY-MM-DD)",
  "rental_days": "integer",
  "usage_type": "string",
  "extras": [
    {
      "extra_id": "string",
      "qty": "integer"
    }
  ],
  "contact_id": "string (optional)"
}
```

**Field Descriptions:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `delivery_location` | string | Yes | Full street address for delivery |
| `trailer_type` | string | Yes | Type of trailer (see available types below) |
| `rental_start_date` | string | No | Start date in YYYY-MM-DD format |
| `rental_days` | integer | Yes | Number of rental days (1-365) |
| `usage_type` | string | Yes | "event" or "commercial" |
| `extras` | array | No | Additional services and quantities |
| `contact_id` | string | No | Associated contact identifier |

**Available Trailer Types:**

- `"2 Stall Restroom Trailer"`
- `"4 Stall Restroom Trailer"`
- `"6 Stall Restroom Trailer"`
- `"8 Stall Restroom Trailer"`
- `"Luxury 2 Stall Restroom Trailer"`
- `"Luxury 4 Stall Restroom Trailer"`

**Available Extras:**

- `"3kW Generator"` - Standard power generator
- `"6kW Generator"` - Heavy-duty power generator
- `"pump_out"` - Additional pump out service
- `"cleaning"` - Enhanced cleaning service
- `"setup_breakdown"` - Full setup and breakdown service
- `"hand_washing_station"` - Portable hand washing station
- `"luxury_amenities"` - Premium amenities package

**Success Response (200):**

```json
{
  "success": true,
  "data": {
    "quote": {
      "base_cost": 600.00,
      "delivery_cost": 75.00,
      "extras_cost": 150.00,
      "subtotal": 825.00,
      "tax_amount": 66.00,
      "total_amount": 891.00,
      "currency": "USD"
    },
    "delivery": {
      "distance_miles": 15.3,
      "delivery_date": "2025-08-15",
      "pickup_date": "2025-08-18",
      "service_zone": "local",
      "nearest_branch": "Atlanta Main Branch"
    },
    "extras_breakdown": [
      {
        "extra_id": "3kW Generator",
        "description": "Standard 3kW generator for basic power needs",
        "quantity": 1,
        "unit_price": 50.00,
        "total_price": 150.00,
        "duration_days": 3
      }
    ],
    "metadata": {
      "quote_id": "quote_abc123",
      "calculation_time_ms": 67,
      "cache_used": true,
      "expires_at": "2025-07-09T18:00:00Z",
      "pricing_version": "2025.07.1"
    }
  }
}
```

**Example Request:**

```bash
curl -X POST "https://api.stahla.com/api/v1/webhook/quote/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key_here" \
  -d '{
    "delivery_location": "1600 Amphitheatre Parkway, Mountain View, CA 94043",
    "trailer_type": "4 Stall Restroom Trailer",
    "rental_start_date": "2025-08-15",
    "rental_days": 3,
    "usage_type": "event",
    "extras": [
      {"extra_id": "3kW Generator", "qty": 1}
    ]
  }'
```

## Location Services

### Synchronous Location Lookup

Perform immediate location geocoding and distance calculation.

**Endpoint:** `POST /api/v1/webhook/location/lookup/sync`

**Request Body:**

```json
{
  "delivery_location": "string",
  "contact_id": "string (optional)"
}
```

**Success Response (200):**

```json
{
  "success": true,
  "data": {
    "delivery_location": "1600 Amphitheatre Parkway, Mountain View, CA 94043",
    "coordinates": {
      "latitude": 37.4224764,
      "longitude": -122.0842499,
      "accuracy": "ROOFTOP",
      "geocoding_source": "google_maps"
    },
    "nearest_branch": {
      "branch_id": "atlanta_main",
      "name": "Atlanta Main Branch",
      "address": "123 Industrial Blvd, Atlanta, GA 30309",
      "distance_miles": 2150.5
    },
    "distance_miles": 2150.5,
    "drive_time_minutes": 2580,
    "service_zone": "out_of_area",
    "within_service_area": false,
    "delivery_cost_estimate": null
  }
}
```

### Asynchronous Location Lookup

Queue location lookup for background processing.

**Endpoint:** `POST /api/v1/webhook/location/lookup/async`

**Request Body:**

```json
{
  "delivery_location": "string",
  "contact_id": "string (optional)",
  "priority": "string (optional)"
}
```

**Priority Levels:**

- `"high"` - Process immediately
- `"normal"` - Standard queue processing (default)
- `"low"` - Process when resources available

**Success Response (202 Accepted):**

```json
{
  "success": true,
  "message": "Location lookup queued for processing",
  "data": {
    "task_id": "task_abc123",
    "estimated_completion": "2025-07-09T12:01:00Z",
    "status_url": "/api/v1/location/lookup/status/task_abc123"
  }
}
```

## Quote Management

### Get Recent Quotes

Retrieve recent quotes with pagination.

**Endpoint:** `GET /api/v1/mongo/quotes/recent`

**Query Parameters:**

- `page` (integer, default: 1) - Page number
- `limit` (integer, default: 10) - Items per page

**Success Response (200):**

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "quote_abc123",
        "delivery_location": "123 Main St, City, State",
        "trailer_type": "4 Stall Restroom Trailer",
        "total_amount": 891.00,
        "status": "COMPLETED",
        "created_at": "2025-07-09T12:00:00Z"
      }
    ],
    "page": 1,
    "limit": 10,
    "total": 156,
    "has_more": true
  }
}
```

### Get Quote by ID

Retrieve a specific quote by its ID.

**Endpoint:** `GET /api/v1/mongo/quotes/{quote_id}`

**Success Response (200):**

```json
{
  "success": true,
  "data": {
    "id": "quote_abc123",
    "delivery_location": "123 Main St, City, State",
    "trailer_type": "4 Stall Restroom Trailer",
    "rental_days": 3,
    "usage_type": "event",
    "total_amount": 891.00,
    "status": "COMPLETED",
    "quote_details": {
      "base_cost": 600.00,
      "delivery_cost": 75.00,
      "extras_cost": 150.00,
      "subtotal": 825.00,
      "tax_amount": 66.00
    },
    "created_at": "2025-07-09T12:00:00Z",
    "expires_at": "2025-07-09T18:00:00Z"
  }
}
```

## Error Responses

All endpoints return errors in a consistent format:

### Error Response Structure

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "Additional error details",
      "suggestion": "How to fix the error"
    }
  },
  "request_id": "req_abc123"
}
```

### Common Error Codes

#### Authentication Errors (401)

```json
{
  "success": false,
  "error": {
    "code": "INVALID_API_KEY",
    "message": "The provided API key is invalid or expired"
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_PERMISSIONS", 
    "message": "API key does not have required permissions",
    "details": {
      "required_permission": "quote:create",
      "current_permissions": ["quote:read"]
    }
  }
}
```

#### Validation Errors (400)

```json
{
  "success": false,
  "error": {
    "code": "INVALID_TRAILER_TYPE",
    "message": "The specified trailer type is not available",
    "details": {
      "provided": "3 Stall Restroom Trailer",
      "available_types": [
        "2 Stall Restroom Trailer",
        "4 Stall Restroom Trailer",
        "6 Stall Restroom Trailer",
        "8 Stall Restroom Trailer"
      ]
    }
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "INVALID_LOCATION",
    "message": "Unable to geocode the provided delivery location",
    "details": {
      "location": "Invalid Address, Nowhere",
      "suggestion": "Please provide a complete street address including city and state"
    }
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "OUT_OF_SERVICE_AREA",
    "message": "Delivery location is outside our service area",
    "details": {
      "location": "123 Remote St, Far City, AK",
      "distance_to_nearest_branch": 1250.5,
      "max_service_distance": 250
    }
  }
}
```

#### Server Errors (500)

```json
{
  "success": false,
  "error": {
    "code": "PRICING_SERVICE_UNAVAILABLE",
    "message": "Pricing service is temporarily unavailable",
    "details": {
      "retry_after": "60 seconds",
      "support_contact": "support@stahla.com"
    }
  }
}
```

```json
{
  "success": false,
  "error": {
    "code": "CALCULATION_ERROR",
    "message": "An error occurred during price calculation",
    "details": {
      "error_id": "calc_error_xyz789",
      "support_contact": "support@stahla.com"
    }
  }
}
```

## Rate Limiting

API endpoints are subject to rate limiting to ensure fair usage:

### Rate Limit Headers

All responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1625097600
X-RateLimit-Window: 3600
```

### Rate Limit Exceeded (429)

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "API rate limit exceeded",
    "details": {
      "limit": 1000,
      "window": "1 hour",
      "reset_at": "2025-07-09T13:00:00Z"
    }
  }
}
```

### Rate Limits by Endpoint

| Endpoint | Rate Limit | Window |
|----------|------------|---------|
| Quote Generation | 100 requests | per minute |
| Location Lookup | 200 requests | per minute |
| Quote Retrieval | 500 requests | per minute |

## Webhooks

### Quote Completion Webhook

Optionally receive notifications when quotes are generated:

**Webhook URL:** Your configured endpoint

**Payload:**

```json
{
  "event": "quote.completed",
  "timestamp": "2025-07-09T12:00:00Z",
  "data": {
    "quote_id": "quote_abc123",
    "contact_id": "contact_xyz789",
    "total_amount": 891.00,
    "delivery_location": "123 Main St, City, State"
  }
}
```

### Webhook Verification

Webhooks include a signature header for verification:

```http
X-Stahla-Signature: sha256=abc123def456...
```

## SDKs and Integration

### cURL Examples

Basic quote generation:

```bash
curl -X POST "https://api.stahla.com/api/v1/webhook/quote/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_api_key" \
  -d @quote_request.json
```

### JavaScript/Node.js Example

```javascript
const response = await fetch('https://api.stahla.com/api/v1/webhook/quote/generate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your_api_key'
  },
  body: JSON.stringify({
    delivery_location: '123 Main St, City, State',
    trailer_type: '4 Stall Restroom Trailer',
    rental_days: 3,
    usage_type: 'event'
  })
});

const quote = await response.json();
```

### Python Example

```python
import requests

url = 'https://api.stahla.com/api/v1/webhook/quote/generate'
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your_api_key'
}
data = {
    'delivery_location': '123 Main St, City, State',
    'trailer_type': '4 Stall Restroom Trailer', 
    'rental_days': 3,
    'usage_type': 'event'
}

response = requests.post(url, headers=headers, json=data)
quote = response.json()
```

## Testing

### Test Environment

Use the development environment for testing:

```
Base URL: http://localhost:8000
API Key: test_key_123456789
```

### Test Data

Sample addresses that work well for testing:

- **Local Zone:** `"123 Peachtree St NE, Atlanta, GA 30309"`
- **Regional Zone:** `"456 Main St, Savannah, GA 31401"`
- **Extended Zone:** `"789 Broadway, Columbus, GA 31901"`
- **Out of Area:** `"1600 Amphitheatre Parkway, Mountain View, CA 94043"`

### Postman Collection

A Postman collection is available for testing:

```
Import URL: https://api.stahla.com/postman/pricing-collection.json
```
