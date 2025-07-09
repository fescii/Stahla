# Pricing REST API Tests

This folder contains HTTP requests for testing pricing-related endpoints.

## Files

### `location.http`

- **Synchronous Location Lookup**: `/api/v1/webhook/location/lookup/sync`
- **Asynchronous Location Lookup**: `/api/v1/webhook/location/lookup/async`
- Contains examples for different types of addresses (near branch, far from branch, etc.)

### `quote.http`

- **Quote Generation**: `/api/v1/webhook/quote/generate`
- Contains examples for different usage types (event, commercial)
- Various trailer types (2 Stall, 4 Stall, 8 Stall)
- Different rental durations and extras

## Variables

All files use the same variables:

- `@host`: The API host (default: <http://localhost:8000>)
- `@pricing_webhook_api_key`: Your API key from .env
- `@auth_token`: Bearer token for authorization

## Usage

1. Update the `@pricing_webhook_api_key` variable with your actual API key
2. Ensure your API server is running on the specified host
3. Use VS Code REST Client extension or similar tool to execute requests

## Endpoints

- **Location Sync**: Immediate location distance calculation
- **Location Async**: Background location distance calculation
- **Quote Generation**: Full pricing calculation with all factors
