# MongoDB Pagination API REST Examples

This directory contains REST client files for testing all MongoDB pagination endpoints.

## Structure

- `overview.http` - Overview of all endpoints with common examples
- `quotes.http` - Quotes collection endpoints
- `calls.http` - Calls collection endpoints  
- `classify.http` - Classifications collection endpoints
- `location.http` - Location collection endpoints
- `emails.http` - Emails collection endpoints

## Usage

### Prerequisites

1. Ensure your API server is running on `http://localhost:8000`
2. Replace `your_api_key_here` with your actual API key in the variables section
3. Use a REST client like VS Code REST Client extension, Postman, or curl

### Pagination Pattern

All endpoints follow the same pagination pattern:

- **Page Parameter**: `?page=1` (starts from 1)
- **Limit**: Hardcoded to 10 items per page
- **Offset**: Calculated as `(page - 1) * 10`

### Response Format

All paginated endpoints return the following structure:

```json
{
  "items": [...],          // Array of items (max 10)
  "page": 1,               // Current page number
  "limit": 10,             // Items per page (always 10)
  "total": 100,            // Total number of items
  "has_more": true         // Whether there are more pages
}
```

### Individual Records

Each collection has a `/{id}` endpoint for fetching single records:

```json
{
  "success": true,
  "data": {...},           // Single item data
  "error_message": null,
  "error_details": null,
  "status_code": null
}
```

## Collections and Endpoints

### 1. Quotes (`/api/v1/mongo/quotes/`)

- `GET /recent?page=1` - Recent quotes
- `GET /oldest?page=1` - Oldest quotes
- `GET /highest?page=1` - Highest value quotes
- `GET /lowest?page=1` - Lowest value quotes
- `GET /successful?page=1` - Successful quotes
- `GET /failed?page=1` - Failed quotes
- `GET /expired?page=1` - Expired quotes
- `GET /pending?page=1` - Pending quotes
- `GET /by-product?product=ProductName&page=1` - Quotes by product
- `GET /{quote_id}` - Single quote by ID

### 2. Calls (`/api/v1/mongo/calls/`)

- `GET /recent?page=1` - Recent calls
- `GET /oldest?page=1` - Oldest calls
- `GET /successful?page=1` - Successful calls
- `GET /failed?page=1` - Failed calls
- `GET /longest?page=1` - Longest duration calls
- `GET /shortest?page=1` - Shortest duration calls
- `GET /by-source?source=SourceName&page=1` - Calls by source
- `GET /{call_id}` - Single call by ID

### 3. Classifications (`/api/v1/mongo/classify/`)

- `GET /recent?page=1` - Recent classifications
- `GET /oldest?page=1` - Oldest classifications
- `GET /successful?page=1` - Successful classifications
- `GET /failed?page=1` - Failed classifications
- `GET /disqualified?page=1` - Disqualified classifications
- `GET /by-lead-type?lead_type=LeadType&page=1` - Classifications by lead type
- `GET /by-confidence?min_confidence=0.8&page=1` - Classifications by confidence
- `GET /by-source?source=SourceName&page=1` - Classifications by source
- `GET /{classification_id}` - Single classification by ID

### 4. Locations (`/api/v1/mongo/location/`)

- `GET /recent?page=1` - Recent locations
- `GET /oldest?page=1` - Oldest locations
- `GET /successful?page=1` - Successful locations
- `GET /failed?page=1` - Failed locations
- `GET /pending?page=1` - Pending locations
- `GET /by-distance?ascending=true&page=1` - Locations by distance
- `GET /by-branch?branch=BranchName&page=1` - Locations by branch
- `GET /with-fallback?page=1` - Locations using fallback method
- `GET /{location_id}` - Single location by ID

### 5. Emails (`/api/v1/mongo/emails/`)

- `GET /recent?page=1` - Recent emails
- `GET /oldest?page=1` - Oldest emails
- `GET /successful?page=1` - Successful emails
- `GET /failed?page=1` - Failed emails
- `GET /pending?page=1` - Pending emails
- `GET /by-category?category=CategoryName&page=1` - Emails by category
- `GET /by-direction?direction=inbound&page=1` - Emails by direction
- `GET /with-attachments?page=1` - Emails with attachments
- `GET /processed?page=1` - Processed emails
- `GET /{email_id}` - Single email by ID

## Common Query Parameters

- `page`: Page number (starts from 1)
- `product`: Product name (for quotes)
- `source`: Source name (webform, phone, email, etc.)
- `lead_type`: Lead type (Services, Logistics, Leads, Disqualify)
- `min_confidence`: Minimum confidence level (0.0 to 1.0)
- `category`: Email category (sent, received, failed, queued, processing)
- `direction`: Email direction (inbound, outbound)
- `branch`: Branch name
- `ascending`: Sort direction for distance (true/false)

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Success
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

Error responses include:

```json
{
  "success": false,
  "data": null,
  "error_message": "Error description",
  "error_details": {...},
  "status_code": 500
}
```

## Authentication

All endpoints require authentication via the `Authorization` header:

```
Authorization: Bearer your_api_key_here
```

Make sure to replace `your_api_key_here` with your actual API key in all REST files.
