# MongoDB Location Collection Documentation

## Overview

The location collection manages location verification and service area management for the Stahla AI SDR system. It provides comprehensive location tracking, service area validation, and geographic analytics.

## Collection Structure

**Collection Name**: `location`  
**Operations Class**: `LocationOperations` (app/services/mongo/location/operations.py)  
**Document Model**: `LocationDocument` (app/models/mongo/location.py)  

## Document Schema

### Core Fields

- **id** (string): Unique location identifier
- **contact_id** (string): HubSpot contact ID
- **delivery_location** (string): Delivery address
- **status** (string): Location status (pending, verified, failed)
- **within_service_area** (boolean): Service area validation
- **distance_to_branch** (float): Distance to nearest branch
- **branch** (string): Assigned branch identifier
- **created_at** (datetime): Record creation timestamp
- **updated_at** (datetime): Last update timestamp

### Extended Fields

- **coordinates** (object): Geographic coordinates
- **zip_code** (string): Postal code
- **city** (string): City name
- **state** (string): State/province
- **country** (string): Country code
- **fallback_used** (boolean): Fallback method indicator
- **verification_method** (string): Verification method used

## Core Operations

### CRUD Operations

#### create_location(location_data: Dict[str, Any]) -> Optional[str]

Creates a new location record with validation and automatic timestamp generation.

#### update_location(location_id: str, update_data: Dict[str, Any]) -> bool

Updates an existing location with automatic updated_at timestamp.

#### get_location(location_id: str) -> Optional[Dict[str, Any]]

Retrieves a single location by ID with MongoDB _id conversion.

#### delete_location(location_id: str) -> bool

Soft or hard deletion of location records.

### Address-Based Queries

#### get_location_by_address(delivery_location: str) -> Optional[Dict[str, Any]]

Retrieves location by delivery address.

#### get_locations_by_contact(contact_id: str, limit: int = 10) -> List[Dict[str, Any]]

Retrieves all locations for a specific contact.

## Pagination Methods

All pagination methods use hardcoded PAGINATION_LIMIT = 10 with offset calculation.

### Temporal Sorting

#### get_recent_locations(offset: int = 0) -> List[LocationDocument]

Retrieves locations ordered by created_at (newest first).

#### get_oldest_locations(offset: int = 0) -> List[LocationDocument]

Retrieves locations ordered by created_at (oldest first).

### Status-Based Filtering

#### get_locations_by_status(status: str, offset: int = 0) -> List[LocationDocument]

Retrieves locations filtered by status with pagination.

#### get_successful_locations(offset: int = 0) -> List[LocationDocument]

Retrieves locations with successful verification status.

#### get_failed_locations(offset: int = 0) -> List[LocationDocument]

Retrieves locations with failed verification status.

#### get_pending_locations(offset: int = 0) -> List[LocationDocument]

Retrieves locations with pending verification status.

### Distance-Based Filtering

#### get_locations_by_distance(ascending: bool = True, offset: int = 0) -> List[LocationDocument]

Retrieves locations sorted by distance to branch.

#### get_locations_within_range(max_distance: float, offset: int = 0) -> List[LocationDocument]

Retrieves locations within specified distance range.

### Branch-Based Filtering

#### get_locations_by_branch(branch: str, offset: int = 0) -> List[LocationDocument]

Retrieves locations assigned to specific branch.

#### get_locations_with_fallback(offset: int = 0) -> List[LocationDocument]

Retrieves locations that used fallback verification method.

### Individual Location Retrieval

#### get_location_by_id(location_id: str) -> Optional[LocationDocument]

Retrieves a single location as a validated LocationDocument object.

## Count Methods

### Total Counts

#### count_locations() -> int

Returns total number of locations in collection.

#### count_all_locations() -> int

Alias for count_locations() for consistency.

### Filtered Counts

#### count_locations_by_status(status: str) -> int

Returns count of locations by specific status.

#### count_locations_by_branch(branch: str) -> int

Returns count of locations by specific branch.

#### count_locations_with_fallback() -> int

Returns count of locations that used fallback method.

#### count_locations_in_service_area() -> int

Returns count of locations within service area.

## Statistics and Analytics

### Location Statistics

#### get_location_stats() -> Dict[str, int]

Returns comprehensive location statistics including:

- Total locations count
- Locations by status breakdown
- Service area coverage
- Branch distribution
- Verification success rates

### Geographic Analytics

#### get_location_analytics() -> Dict[str, Any]

Returns geographic analytics including:

- Coverage by region
- Distance distribution
- Branch performance
- Fallback usage rates

## Status Management

### Status Updates

#### update_location_status(location_id: str, new_status: str) -> bool

Updates location status with automatic timestamp and validation.

#### verify_location(location_id: str, verification_data: Dict[str, Any]) -> bool

Marks location as verified with verification data.

#### fail_location(location_id: str, reason: str) -> bool

Marks location as failed with reason tracking.

### Service Area Management

#### update_service_area_status(location_id: str, within_area: bool) -> bool

Updates service area validation status.

#### assign_branch(location_id: str, branch: str) -> bool

Assigns location to specific branch.

## Database Indexes

### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `delivery_location` (ascending) - Address lookups
- `status` (ascending) - Status filtering
- `branch` (ascending) - Branch filtering
- `created_at` (descending) - Temporal sorting
- `coordinates` (2dsphere) - Geographic queries

### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact location history
- `{status: 1, created_at: -1}` - Status with recency
- `{branch: 1, status: 1}` - Branch performance
- `{within_service_area: 1, branch: 1}` - Service area by branch

## API Endpoints

### REST Routes

All routes are prefixed with `/api/v1/mongo/location/`

#### GET /recent?page=1

Retrieves recent locations with pagination.

#### GET /oldest?page=1

Retrieves oldest locations with pagination.

#### GET /by-status/{status}?page=1

Retrieves locations by status with pagination.

#### GET /successful?page=1

Retrieves successful locations with pagination.

#### GET /failed?page=1

Retrieves failed locations with pagination.

#### GET /pending?page=1

Retrieves pending locations with pagination.

#### GET /by-distance?ascending=true&page=1

Retrieves locations by distance with pagination.

#### GET /by-branch/{branch}?page=1

Retrieves locations by branch with pagination.

#### GET /with-fallback?page=1

Retrieves locations with fallback method with pagination.

#### GET /{location_id}

Retrieves a single location by ID.

#### GET /stats

Retrieves comprehensive location statistics.

## Error Handling

### Common Errors

- **LocationNotFound**: Location ID not found
- **ValidationError**: Invalid location data
- **AddressNotFound**: Address not found
- **ServiceAreaError**: Service area validation issues
- **BranchAssignmentError**: Branch assignment problems

### Error Response Format

```json
{
  "error": "LocationNotFound",
  "message": "Location with ID 'loc_123' not found",
  "code": "LOCATION_NOT_FOUND"
}
```

## Usage Examples

### Creating a Location

```python
location_data = {
    "contact_id": "hubspot_12345",
    "delivery_location": "123 Main St, City, ST 12345",
    "status": "pending",
    "within_service_area": True,
    "branch": "branch_001"
}
location_id = await mongo_service.create_location(location_data)
```

### Paginated Retrieval

```python
# Get page 2 of recent locations
page = 2
offset = (page - 1) * 10
locations = await mongo_service.get_recent_locations(offset=offset)

# Get total count for pagination
total = await mongo_service.count_locations()
total_pages = (total + 9) // 10
```

### Status Management

```python
# Update location status
success = await mongo_service.update_location_status(
    location_id="loc_123",
    new_status="verified"
)

# Get statistics
stats = await mongo_service.get_location_stats()
```

## Performance Considerations

### Optimization Tips

1. **Use indexes**: Ensure proper indexing for query patterns
2. **Limit results**: Always use pagination for large datasets
3. **Geographic queries**: Use 2dsphere indexes for location queries
4. **Filter early**: Apply status/branch filters before sorting
5. **Cache common queries**: Cache branch and service area data

### Query Patterns

- **Recent locations**: Use created_at descending index
- **Status filtering**: Use status index first
- **Branch queries**: Use branch index
- **Geographic queries**: Use coordinates 2dsphere index

## Best Practices

1. **Validate data**: Use LocationDocument model for validation
2. **Track verification**: Monitor verification success rates
3. **Handle fallbacks**: Implement fallback verification methods
4. **Monitor coverage**: Track service area coverage
5. **Optimize branches**: Balance branch assignments

## Future Enhancements

1. **Advanced mapping**: Enhanced geographic visualization
2. **Route optimization**: Optimal delivery routing
3. **Predictive analytics**: Service area expansion planning
4. **Integration**: Enhanced mapping service integration
5. **Automation**: Automated branch assignment
