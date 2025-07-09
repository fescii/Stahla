# Location Services and Distance Calculations

This document covers the location services system, including geocoding, distance calculations, and delivery zone management.

## Overview

The location services system provides accurate distance calculations for delivery cost estimation. It integrates with Google Maps API for geocoding and routing, and implements intelligent caching to optimize performance.

## Architecture

### Core Components

- **LocationService** (`app/services/location/location.py`) - Main location service
- **Sync Endpoint** (`app/api/v1/endpoints/webhooks/location/sync.py`) - Synchronous lookup
- **Async Endpoint** (`app/api/v1/endpoints/webhooks/location/background.py`) - Background processing
- **Location Models** (`app/models/location.py`) - Data structures
- **Location Utils** (`app/utils/location.py`) - Utility functions

### Service Flow

#### Synchronous Location Lookup

1. **Input Validation** - Validate address format and requirements
2. **Cache Check** - Look for existing geocoded results
3. **Geocoding** - Convert address to coordinates (if needed)
4. **Distance Calculation** - Calculate distance to nearest branch
5. **Zone Classification** - Determine service zone (local/regional/extended)
6. **Cache Storage** - Store results for future use
7. **Response** - Return distance and zone information

#### Asynchronous Location Processing

1. **Request Queuing** - Queue location for background processing
2. **Immediate Response** - Return 202 Accepted status
3. **Background Processing** - Process location in background task
4. **Cache Population** - Store results for future quote requests
5. **Notification** - Optional webhook notification when complete

## Data Models

### LocationLookupRequest

```python
class LocationLookupRequest(BaseModel):
    delivery_location: str
    contact_id: Optional[str] = None
    priority: Optional[str] = "normal"  # "high", "normal", "low"
```

### LocationLookupResponse

```python
class LocationLookupResponse(BaseModel):
    delivery_location: str
    coordinates: Optional[Coordinates]
    nearest_branch: BranchInfo
    distance_miles: float
    drive_time_minutes: int
    service_zone: str
    within_service_area: bool
    delivery_cost_estimate: float
```

### Coordinates

```python
class Coordinates(BaseModel):
    latitude: float
    longitude: float
    accuracy: Optional[str] = None
    geocoding_source: Optional[str] = None
```

### BranchInfo

```python
class BranchInfo(BaseModel):
    branch_id: str
    name: str
    address: str
    coordinates: Coordinates
    service_radius_miles: int
    contact_info: Optional[Dict[str, str]]
```

## Geocoding Services

### Google Maps Integration

The system uses Google Maps Geocoding API for address resolution:

```python
async def geocode_address(address: str) -> Optional[Coordinates]:
    """
    Geocode an address using Google Maps API
    
    Args:
        address: Street address to geocode
        
    Returns:
        Coordinates object with lat/lng, or None if failed
    """
```

#### Configuration

```yaml
google_maps:
  api_key: ${GOOGLE_MAPS_API_KEY}
  geocoding_endpoint: "https://maps.googleapis.com/maps/api/geocode/json"
  rate_limit: 50  # requests per second
  timeout: 5      # seconds
```

#### Error Handling

- **API Key Invalid** - Log error and return fallback coordinates
- **Rate Limit Exceeded** - Implement exponential backoff
- **Address Not Found** - Return error with suggestions
- **Service Unavailable** - Fall back to cached or estimated coordinates

### Fallback Geocoding

When Google Maps is unavailable, the system uses:

1. **Nominatim (OpenStreetMap)** - Free alternative geocoding service
2. **ZIP Code Approximation** - Use ZIP code centroid for rough location
3. **City/State Lookup** - Use city center coordinates as fallback

## Distance Calculation

### Haversine Formula

For basic distance calculations, the system uses the Haversine formula:

```python
def calculate_haversine_distance(
    lat1: float, lon1: float, 
    lat2: float, lon2: float
) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    
    Returns distance in miles
    """
```

### Google Maps Distance Matrix

For accurate driving distances and times:

```python
async def get_driving_distance(
    origin: Coordinates,
    destination: Coordinates
) -> DistanceResult:
    """
    Get driving distance and time using Google Maps
    
    Returns actual driving distance and estimated time
    """
```

#### Configuration

```yaml
distance_matrix:
  units: "imperial"  # imperial or metric
  mode: "driving"    # driving, walking, bicycling, transit
  avoid: "tolls"     # tolls, highways, ferries
  traffic_model: "best_guess"  # best_guess, pessimistic, optimistic
```

## Branch Management

### Branch Configuration

Service branches are configured in Google Sheets and cached in Redis:

```yaml
branches:
  - branch_id: "atlanta_main"
    name: "Atlanta Main Branch"
    address: "123 Industrial Blvd, Atlanta, GA 30309"
    coordinates:
      latitude: 33.7756
      longitude: -84.3963
    service_radius_miles: 50
    priority: 1  # Lower numbers have higher priority
    
  - branch_id: "atlanta_north"
    name: "Atlanta North Branch" 
    address: "456 Commerce Dr, Roswell, GA 30076"
    coordinates:
      latitude: 34.0232
      longitude: -84.3616
    service_radius_miles: 35
    priority: 2
```

### Branch Selection Algorithm

1. **Distance Calculation** - Calculate distance to all branches
2. **Service Area Check** - Filter branches within service radius
3. **Priority Ranking** - Sort by priority then distance
4. **Capacity Check** - Verify branch has capacity (if integrated)
5. **Selection** - Choose optimal branch for delivery

## Service Zones

### Zone Classification

Delivery zones are classified based on distance from nearest branch:

```yaml
service_zones:
  local:
    max_distance: 25
    description: "Local delivery area"
    delivery_rate: 2.50  # per mile
    minimum_charge: 50.00
    
  regional:
    max_distance: 100
    description: "Regional delivery area"
    delivery_rate: 3.00
    minimum_charge: 100.00
    
  extended:
    max_distance: 250
    description: "Extended delivery area"
    delivery_rate: 3.50
    minimum_charge: 200.00
    
  out_of_area:
    max_distance: null
    description: "Outside service area"
    delivery_rate: null
    minimum_charge: null
```

### Zone Benefits

- **Local Zone** - Same-day delivery, lowest rates
- **Regional Zone** - Next-day delivery, standard rates
- **Extended Zone** - 2-3 day delivery, premium rates
- **Out of Area** - Special arrangement required

## Caching Strategy

### Cache Layers

1. **Geocoding Cache** - Store geocoded coordinates
2. **Distance Cache** - Store calculated distances
3. **Zone Cache** - Store zone classifications
4. **Branch Cache** - Store branch information

### Cache Keys

```python
# Geocoding cache
geocode:{hash(address)} -> Coordinates

# Distance cache  
distance:{lat1},{lon1}:{lat2},{lon2} -> DistanceResult

# Zone cache
zone:{delivery_location_hash} -> ServiceZone

# Branch cache
branches:config -> List[BranchInfo]
```

### TTL Configuration

```yaml
cache_ttl:
  geocoding: 86400    # 24 hours
  distance: 3600      # 1 hour
  zones: 1800         # 30 minutes
  branches: 900       # 15 minutes
```

### Cache Warming

Proactive cache population for:

- **Common Addresses** - Frequently requested locations
- **ZIP Code Centers** - Major ZIP code centroids
- **Business Districts** - Commercial areas in service zones
- **Event Venues** - Known event locations

## Performance Optimization

### Request Batching

For multiple location requests:

```python
async def batch_geocode(
    addresses: List[str]
) -> List[Optional[Coordinates]]:
    """
    Geocode multiple addresses in a single API call
    
    Reduces API calls and improves performance
    """
```

### Connection Pooling

HTTP connection pooling for external APIs:

```python
# Configure session with connection pooling
session = aiohttp.ClientSession(
    connector=aiohttp.TCPConnector(
        limit=100,           # Total connection limit
        limit_per_host=20,   # Per-host connection limit
        ttl_dns_cache=300,   # DNS cache TTL
        use_dns_cache=True
    )
)
```

### Rate Limiting

API rate limiting to stay within quotas:

```python
# Rate limiter for Google Maps API
rate_limiter = AsyncLimiter(
    max_rate=50,    # 50 requests
    time_period=1   # per second
)
```

## Error Handling and Fallbacks

### Geocoding Failures

```python
async def geocode_with_fallback(address: str) -> Optional[Coordinates]:
    """
    Attempt geocoding with multiple fallback strategies:
    1. Google Maps API
    2. Nominatim (OpenStreetMap)
    3. ZIP code lookup
    4. City/state lookup
    """
```

### Distance Calculation Failures

```python
async def calculate_distance_with_fallback(
    origin: Coordinates,
    destination: Coordinates
) -> float:
    """
    Calculate distance with fallback methods:
    1. Google Maps Distance Matrix
    2. Haversine formula (great circle distance)
    3. Estimated distance from ZIP codes
    """
```

### Service Degradation

When external services are unavailable:

1. **Cached Results** - Use previously calculated distances
2. **Estimated Distances** - Use ZIP code or city-level estimates  
3. **Default Zones** - Assign conservative zone classification
4. **Manual Override** - Allow manual distance entry for critical requests

## Monitoring and Analytics

### Key Metrics

- **Geocoding Success Rate** - Percentage of successful geocoding attempts
- **API Response Time** - Average response time for geocoding/distance APIs
- **Cache Hit Rate** - Percentage of requests served from cache
- **Error Rate** - Rate of geocoding and distance calculation failures

### Alerting

Configure alerts for:

- **High Error Rate** - > 5% geocoding failures
- **Slow Response** - > 2 second average response time
- **API Quota** - Approaching daily API limits
- **Cache Miss Rate** - < 80% cache hit rate

### Analytics

Track location patterns for:

- **Service Area Analysis** - Popular delivery zones
- **Branch Utilization** - Distribution of deliveries by branch
- **Distance Trends** - Average delivery distances over time
- **Geographic Expansion** - Identify new service area opportunities

## API Endpoints

### Synchronous Location Lookup

```http
POST /api/v1/webhook/location/lookup/sync
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "delivery_location": "123 Main St, Atlanta, GA 30309",
  "contact_id": "contact_123"
}
```

### Asynchronous Location Processing

```http
POST /api/v1/webhook/location/lookup/async
Authorization: Bearer {api_key}
Content-Type: application/json

{
  "delivery_location": "123 Main St, Atlanta, GA 30309",
  "contact_id": "contact_123",
  "priority": "high"
}
```

### Response Format

```json
{
  "success": true,
  "data": {
    "delivery_location": "123 Main St, Atlanta, GA 30309",
    "coordinates": {
      "latitude": 33.7756,
      "longitude": -84.3963,
      "accuracy": "ROOFTOP",
      "geocoding_source": "google_maps"
    },
    "nearest_branch": {
      "branch_id": "atlanta_main",
      "name": "Atlanta Main Branch",
      "address": "123 Industrial Blvd, Atlanta, GA 30309",
      "distance_miles": 12.3
    },
    "distance_miles": 12.3,
    "drive_time_minutes": 18,
    "service_zone": "local",
    "within_service_area": true,
    "delivery_cost_estimate": 75.00
  }
}
```
