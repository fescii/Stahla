# Pricing System Documentation

This folder contains comprehensive documentation for the Stahla AI SDR pricing system, covering quote generation, location services, and pricing calculations.

## Overview

The pricing system provides real-time price quotes for restroom trailer rentals based on multiple factors including trailer type, rental duration, usage type, extras, and delivery location. The system integrates with Google Maps API for distance calculations and uses cached pricing data from Google Sheets.

## Documentation Structure

### Core Components

- **[quotes.md](quotes.md)** - Quote generation system and business logic
- **[location.md](location.md)** - Location services and distance calculations
- **[calculations.md](calculations.md)** - Pricing calculation algorithms and formulas
- **[configuration.md](configuration.md)** - Pricing configuration and rules management

### API & Integration

- **[webhooks.md](webhooks.md)** - Webhook endpoints for external integrations
- **[api.md](api.md)** - REST API endpoints and usage
- **[models.md](models.md)** - Data models and schemas

### Operations & Monitoring

- **[caching.md](caching.md)** - Redis caching strategy and optimization
- **[sync.md](sync.md)** - Google Sheets synchronization process
- **[monitoring.md](monitoring.md)** - Performance monitoring and metrics

## Key Features

### Real-time Quote Generation

- **Instant Pricing**: Provides quotes in milliseconds based on cached data
- **Multi-factor Calculation**: Considers trailer type, duration, usage, extras, and location
- **Dynamic Pricing**: Supports seasonal multipliers and special rates
- **Delivery Cost Integration**: Automatically calculates delivery fees based on distance

### Location Intelligence

- **Distance Calculation**: Uses Google Maps API for accurate delivery distance
- **Branch Optimization**: Finds nearest branch for optimal delivery routing
- **Service Area Validation**: Determines if locations are within service boundaries
- **Caching Strategy**: Caches location lookups for performance optimization

### Configuration Management

- **Google Sheets Integration**: Pricing rules sync from centralized spreadsheets
- **Dynamic Updates**: Configuration changes without application restart
- **Version Control**: Tracks changes and maintains pricing history
- **Multi-environment Support**: Different configurations for dev/staging/production

## Quick Start

### Basic Quote Request

```http
POST /api/v1/webhook/quote/generate
{
  "delivery_location": "123 Main St, City, State",
  "trailer_type": "2 Stall Restroom Trailer",
  "rental_days": 3,
  "usage_type": "event"
}
```

### Location Lookup

```http
POST /api/v1/webhook/location/lookup/sync
{
  "delivery_location": "123 Main St, City, State"
}
```

## Architecture

The pricing system follows a modular architecture:

```
app/services/quote/
├── quote.py           # Main quote service
├── sync.py            # Google Sheets synchronization
└── auth.py            # Authentication for quote services

app/services/location/
└── location.py        # Location and distance services

app/api/v1/endpoints/webhooks/
├── quote/
│   └── generator.py   # Quote generation endpoint
└── location/
    ├── sync.py        # Synchronous location lookup
    └── background.py  # Asynchronous location lookup
```

## Performance Metrics

- **Quote Generation**: < 100ms average response time
- **Location Lookup**: < 500ms for new addresses, < 10ms for cached
- **Cache Hit Rate**: > 95% for frequently requested locations
- **Sync Frequency**: Pricing data updated every 15 minutes

## Security

- **API Key Authentication**: All endpoints secured with API keys
- **Rate Limiting**: Prevents abuse and ensures fair usage
- **Input Validation**: Comprehensive validation of all input parameters
- **Audit Logging**: All pricing requests logged for analysis

## Related Documentation

- [Services Overview](../services.md) - General services documentation
- [Features](../features.md) - Application features overview
- [Webhooks](../webhooks.md) - Webhook integration guide
- [API Documentation](../api.md) - Complete API reference
