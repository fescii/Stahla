# MongoDB Calls Collection Documentation

## Overview

The calls collection manages call logging and Bland AI integration for the Stahla AI SDR system. It provides comprehensive call tracking, status management, and analytics for voice interactions.

## Collection Structure

**Collection Name**: `calls`  
**Operations Class**: `CallsOperations` (app/services/mongo/calls/operations.py)  
**Document Model**: `CallDocument` (app/models/mongo/calls.py)  

## Document Schema

### Core Fields

- **id** (string): Unique call identifier
- **contact_id** (string): HubSpot contact ID
- **call_id** (string): Bland AI call ID
- **status** (string): Call status (pending, in_progress, completed, failed)
- **phone_number** (string): Called phone number
- **duration** (int): Call duration in seconds
- **started_at** (datetime): Call start time
- **ended_at** (datetime): Call end time
- **created_at** (datetime): Record creation timestamp
- **updated_at** (datetime): Last update timestamp

### Extended Fields

- **transcript** (string): Call transcript
- **recording_url** (string): Call recording URL
- **call_type** (string): Call type (outbound, inbound)
- **outcome** (string): Call outcome
- **notes** (string): Additional call notes
- **cost** (float): Call cost

## Core Operations

### CRUD Operations

#### create_call(call_data: Dict[str, Any]) -> Optional[str]

Creates a new call record with validation and automatic timestamp generation.

#### update_call(call_id: str, update_data: Dict[str, Any]) -> bool

Updates an existing call with automatic updated_at timestamp.

#### get_call(call_id: str) -> Optional[Dict[str, Any]]

Retrieves a single call by ID with MongoDB _id conversion.

#### delete_call(call_id: str) -> bool

Soft or hard deletion of call records.

### Contact-Based Queries

#### get_call_by_contact(contact_id: str) -> Optional[Dict[str, Any]]

Retrieves the most recent call for a specific contact.

#### get_calls_by_contact(contact_id: str, limit: int = 10) -> List[Dict[str, Any]]

Retrieves all calls for a specific contact with sorting by creation date.

## Pagination Methods

All pagination methods use hardcoded PAGINATION_LIMIT = 10 with offset calculation.

### Temporal Sorting

#### get_recent_calls(offset: int = 0) -> List[CallDocument]

Retrieves calls ordered by created_at (newest first).

#### get_oldest_calls(offset: int = 0) -> List[CallDocument]

Retrieves calls ordered by created_at (oldest first).

### Status-Based Filtering

#### get_calls_by_status(status: str, offset: int = 0) -> List[CallDocument]

Retrieves calls filtered by status with pagination.

#### get_successful_calls(offset: int = 0) -> List[CallDocument]

Retrieves calls with successful completion status.

#### get_failed_calls(offset: int = 0) -> List[CallDocument]

Retrieves calls with failed status.

#### get_pending_calls(offset: int = 0) -> List[CallDocument]

Retrieves calls with pending status.

### Duration-Based Filtering

#### get_calls_by_duration(min_duration: int, offset: int = 0) -> List[CallDocument]

Retrieves calls filtered by minimum duration.

#### get_long_calls(offset: int = 0) -> List[CallDocument]

Retrieves calls exceeding standard duration threshold.

### Individual Call Retrieval

#### get_call_by_id(call_id: str) -> Optional[CallDocument]

Retrieves a single call as a validated CallDocument object.

## Count Methods

### Total Counts

#### count_calls() -> int

Returns total number of calls in collection.

#### count_all_calls() -> int

Alias for count_calls() for consistency.

### Filtered Counts

#### count_calls_by_status(status: str) -> int

Returns count of calls by specific status.

#### count_calls_by_duration(min_duration: int) -> int

Returns count of calls exceeding minimum duration.

#### count_calls_by_outcome(outcome: str) -> int

Returns count of calls by specific outcome.

## Statistics and Analytics

### Call Statistics

#### get_call_stats() -> Dict[str, int]

Returns comprehensive call statistics including:

- Total calls count
- Calls by status breakdown
- Average call duration
- Success/failure rates
- Calls by time period

### Performance Analytics

#### get_call_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]

Returns call analytics for specified time period.

#### get_top_performers() -> List[Dict[str, Any]]

Returns top-performing call outcomes.

## Status Management

### Status Updates

#### update_call_status(call_id: str, new_status: str) -> bool

Updates call status with automatic timestamp and validation.

#### start_call(call_id: str) -> bool

Marks call as started with timestamp.

#### complete_call(call_id: str, outcome: str) -> bool

Marks call as completed with outcome.

#### fail_call(call_id: str, reason: str) -> bool

Marks call as failed with reason tracking.

### Bland AI Integration

#### update_bland_call_data(call_id: str, bland_data: Dict[str, Any]) -> bool

Updates call with Bland AI specific data.

#### process_bland_webhook(webhook_data: Dict[str, Any]) -> bool

Processes Bland AI webhook data.

## Database Indexes

### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `call_id` (ascending) - Bland AI integration
- `status` (ascending) - Status filtering
- `created_at` (descending) - Temporal sorting
- `phone_number` (ascending) - Phone number queries

### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact call history
- `{status: 1, created_at: -1}` - Status with recency
- `{call_id: 1, status: 1}` - Bland AI status tracking

## API Endpoints

### REST Routes

All routes are prefixed with `/api/v1/mongo/calls/`

#### GET /recent?page=1

Retrieves recent calls with pagination.

#### GET /oldest?page=1

Retrieves oldest calls with pagination.

#### GET /by-status/{status}?page=1

Retrieves calls by status with pagination.

#### GET /successful?page=1

Retrieves successful calls with pagination.

#### GET /failed?page=1

Retrieves failed calls with pagination.

#### GET /pending?page=1

Retrieves pending calls with pagination.

#### GET /by-duration?min_duration=60&page=1

Retrieves calls by duration with pagination.

#### GET /{call_id}

Retrieves a single call by ID.

#### GET /stats

Retrieves comprehensive call statistics.

## Error Handling

### Common Errors

- **CallNotFound**: Call ID not found
- **ValidationError**: Invalid call data
- **StatusTransitionError**: Invalid status change
- **BlandIntegrationError**: Bland AI integration issues

### Error Response Format

```json
{
  "error": "CallNotFound",
  "message": "Call with ID 'call_123' not found",
  "code": "CALL_NOT_FOUND"
}
```

## Usage Examples

### Creating a Call

```python
call_data = {
    "contact_id": "hubspot_12345",
    "call_id": "bland_call_789",
    "status": "pending",
    "phone_number": "+1234567890",
    "call_type": "outbound"
}
call_id = await mongo_service.create_call(call_data)
```

### Paginated Retrieval

```python
# Get page 2 of recent calls
page = 2
offset = (page - 1) * 10
calls = await mongo_service.get_recent_calls(offset=offset)

# Get total count for pagination
total = await mongo_service.count_calls()
total_pages = (total + 9) // 10
```

### Status Management

```python
# Update call status
success = await mongo_service.update_call_status(
    call_id="call_123",
    new_status="completed"
)

# Get statistics
stats = await mongo_service.get_call_stats()
```

## Performance Considerations

### Optimization Tips

1. **Use indexes**: Ensure proper indexing for query patterns
2. **Limit results**: Always use pagination for large datasets
3. **Filter early**: Apply status/contact filters before sorting
4. **Monitor duration**: Track call duration for optimization
5. **Cache frequent queries**: Cache call statistics

### Query Patterns

- **Recent calls**: Use created_at descending index
- **Status filtering**: Use status index first
- **Contact queries**: Use contact_id index
- **Duration filtering**: Use duration range queries

## Best Practices

1. **Validate data**: Use CallDocument model for validation
2. **Track status**: Monitor call status transitions
3. **Log webhook data**: Capture all Bland AI webhook events
4. **Monitor performance**: Track call success rates
5. **Handle failures**: Implement retry logic for failed calls

## Future Enhancements

1. **Advanced analytics**: Call outcome prediction
2. **Integration**: Enhanced CRM integration
3. **Automation**: Automated call scheduling
4. **Quality scoring**: Call quality assessment
5. **Reporting**: Advanced call reporting
