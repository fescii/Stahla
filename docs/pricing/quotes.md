# Quote Generation System

This document covers the quote generation system, including business logic, data models, and processing workflows.

## Overview

The quote generation system provides real-time pricing for restroom trailer rentals based on multiple factors including trailer type, rental duration, usage type, extras, and delivery location. The system is designed for high performance with sub-100ms response times.

## Architecture

### Core Components

- **QuoteService** (`app/services/quote/quote.py`) - Main quote generation service
- **Quote Generator** (`app/api/v1/endpoints/webhooks/quote/generator.py`) - Webhook endpoint
- **Quote Models** (`app/models/quote.py`) - Data structures and validation
- **Background Tasks** - Logging and metrics collection

### Request Flow

1. **Input Validation** - Validate quote request parameters
2. **Location Processing** - Determine delivery distance and costs
3. **Base Pricing** - Calculate base rental costs
4. **Extras Calculation** - Add costs for additional services
5. **Delivery Calculation** - Calculate delivery and pickup fees
6. **Final Assembly** - Generate complete quote response
7. **Logging** - Record quote in MongoDB for analytics

## Data Models

### QuoteRequest

```python
class QuoteRequest(BaseModel):
    delivery_location: str
    trailer_type: str
    rental_start_date: Optional[date]
    rental_days: int
    usage_type: str  # "event" or "commercial"
    extras: Optional[List[ExtraItem]] = []
    contact_id: Optional[str] = None
```

### QuoteResponse

```python
class QuoteResponse(BaseModel):
    quote: QuoteDetails
    delivery: DeliveryDetails
    metadata: QuoteMetadata
```

### QuoteDetails

```python
class QuoteDetails(BaseModel):
    base_cost: float
    delivery_cost: float
    extras_cost: float
    subtotal: float
    tax_amount: float
    total_amount: float
    currency: str = "USD"
```

## Business Logic

### Base Pricing Calculation

The base pricing is determined by:

1. **Trailer Type** - Different base rates for 2, 4, 6, 8+ stall trailers
2. **Rental Duration** - Daily, weekly, and monthly rates with volume discounts
3. **Usage Type** - Event vs commercial pricing tiers
4. **Seasonal Multipliers** - Peak season adjustments

### Delivery Cost Calculation

Delivery costs are based on:

1. **Distance Calculation** - Using Google Maps API for accurate routing
2. **Service Zones** - Different rates for local, regional, and extended zones
3. **Trailer Size** - Larger trailers have higher delivery costs
4. **Round Trip** - Delivery and pickup are calculated together

### Extras Processing

Additional services include:

- **Generators** - Power supply for events
- **Pump Outs** - Additional servicing during rental
- **Cleaning** - Enhanced cleaning services
- **Setup/Breakdown** - Full-service event support

### Tax Calculation

Tax is calculated based on:

- **Delivery Location** - Local tax rates by jurisdiction
- **Service Type** - Different tax rates for rentals vs services
- **Tax Exemptions** - Support for tax-exempt organizations

## Configuration

### Pricing Rules

Pricing rules are managed through Google Sheets and cached in Redis:

```yaml
pricing_config:
  base_rates:
    "2_stall": 
      daily: 150.00
      weekly: 900.00
      monthly: 3000.00
    "4_stall":
      daily: 200.00
      weekly: 1200.00
      monthly: 4000.00
  
  usage_multipliers:
    event: 1.0
    commercial: 0.85
  
  seasonal_multipliers:
    peak: 1.2
    standard: 1.0
    off_peak: 0.9
```

### Delivery Configuration

```yaml
delivery_config:
  zones:
    local:
      max_distance: 25
      rate_per_mile: 2.50
    regional:
      max_distance: 100
      rate_per_mile: 3.00
    extended:
      max_distance: 250
      rate_per_mile: 3.50
  
  minimum_charges:
    local: 50.00
    regional: 100.00
    extended: 200.00
```

## Performance Optimization

### Caching Strategy

1. **Pricing Data Cache** - 15-minute TTL for pricing rules
2. **Location Cache** - 24-hour TTL for geocoded addresses
3. **Distance Cache** - 1-hour TTL for distance calculations
4. **Quote Cache** - 5-minute TTL for identical quote requests

### Background Processing

- **Metrics Collection** - Async logging of quote metrics
- **MongoDB Logging** - Background quote record creation
- **Cache Warming** - Proactive cache population for common addresses

## Error Handling

### Validation Errors

- **Invalid Trailer Type** - Return available options
- **Invalid Usage Type** - Must be "event" or "commercial"
- **Invalid Date Range** - Future dates only, reasonable duration limits
- **Invalid Location** - Geocoding failures return specific error

### Service Errors

- **Pricing Data Unavailable** - Fallback to cached rates
- **Location Service Down** - Use estimated delivery costs
- **Cache Failures** - Degrade gracefully to direct calculation

### Response Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_TRAILER_TYPE",
    "message": "Trailer type not found",
    "details": {
      "available_types": ["2 Stall", "4 Stall", "6 Stall", "8 Stall"]
    }
  }
}
```

## Monitoring and Analytics

### Key Metrics

- **Response Time** - Target < 100ms average
- **Success Rate** - Target > 99.5%
- **Cache Hit Rate** - Target > 95%
- **Quote Volume** - Daily/weekly/monthly trends

### Logging

All quotes are logged with:

- **Request Details** - Full quote request parameters
- **Response Details** - Generated quote breakdown
- **Performance Metrics** - Response time, cache hits
- **Error Details** - Any failures or fallbacks used

### Dashboard Integration

Quote metrics are available through:

- **Real-time Counters** - Redis-based metrics
- **Historical Analytics** - MongoDB aggregation queries
- **Performance Alerts** - Threshold-based notifications

## API Integration

### Webhook Endpoint

```http
POST /api/v1/webhook/quote/generate
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "delivery_location": "123 Main St, City, State",
  "trailer_type": "4 Stall Restroom Trailer",
  "rental_start_date": "2025-08-15",
  "rental_days": 3,
  "usage_type": "event",
  "extras": [
    {"extra_id": "3kW Generator", "qty": 1}
  ]
}
```

### Response Format

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
      "service_zone": "local"
    },
    "metadata": {
      "quote_id": "quote_abc123",
      "calculation_time_ms": 67,
      "cache_used": true,
      "expires_at": "2025-07-09T18:00:00Z"
    }
  }
}
```

## Testing

### Unit Tests

- **Pricing Calculations** - Verify accuracy of all pricing formulas
- **Data Validation** - Test input validation and error handling
- **Business Logic** - Test all pricing rules and edge cases

### Integration Tests

- **End-to-End Quotes** - Full quote generation workflow
- **Cache Behavior** - Verify caching strategy effectiveness
- **Error Scenarios** - Test failure modes and recovery

### Load Testing

- **Concurrent Requests** - Test performance under load
- **Cache Performance** - Verify cache hit rates under stress
- **Resource Usage** - Monitor memory and CPU usage
