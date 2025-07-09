# MongoDB Quotes Collection Documentation

## Overview

The quotes collection manages pricing quotes and estimates for the Stahla AI SDR system. It provides comprehensive quote lifecycle management from creation through completion, with detailed tracking of pricing, status, and customer interactions.

## Collection Structure

**Collection Name**: `quotes`  
**Operations Class**: `QuotesOperations` (app/services/mongo/quotes/operations.py)  
**Document Model**: `QuoteDocument` (app/models/mongo/quotes.py)  

## Document Schema

### Core Fields

- **id** (string): Unique quote identifier
- **contact_id** (string): HubSpot contact ID
- **status** (string): Quote status (pending, approved, rejected, expired)
- **quote_number** (string): Human-readable quote number
- **total_amount** (float): Total quote amount
- **valid_until** (datetime): Quote expiration date
- **created_at** (datetime): Creation timestamp
- **updated_at** (datetime): Last update timestamp

### Extended Fields

- **items** (array): List of quote line items
- **discount** (float): Applied discount amount
- **tax_amount** (float): Tax calculations
- **notes** (string): Additional quote notes
- **terms** (string): Quote terms and conditions

## Core Operations

### CRUD Operations

#### create_quote(quote_data: Dict[str, Any]) -> Optional[str]

Creates a new quote document with validation and automatic timestamp generation.

#### update_quote(quote_id: str, update_data: Dict[str, Any]) -> bool

Updates an existing quote with automatic updated_at timestamp.

#### get_quote(quote_id: str) -> Optional[Dict[str, Any]]

Retrieves a single quote by ID with MongoDB _id conversion.

#### delete_quote(quote_id: str) -> bool

Soft or hard deletion of quote documents.

### Contact-Based Queries

#### get_quotes_by_contact(contact_id: str, limit: int = 10) -> List[Dict[str, Any]]

Retrieves all quotes for a specific contact with sorting by creation date.

## Pagination Methods

All pagination methods use hardcoded PAGINATION_LIMIT = 10 with offset calculation.

### Temporal Sorting

#### get_recent_quotes(offset: int = 0) -> List[QuoteDocument]

Retrieves quotes ordered by created_at (newest first).

#### get_oldest_quotes(offset: int = 0) -> List[QuoteDocument]

Retrieves quotes ordered by created_at (oldest first).

### Value-Based Sorting

#### get_quotes_by_value(offset: int = 0, ascending: bool = True) -> List[QuoteDocument]

Retrieves quotes ordered by total_amount with configurable sort direction.

### Status-Based Filtering

#### get_quotes_by_status(status: str, offset: int = 0) -> List[QuoteDocument]

Retrieves quotes filtered by status with pagination.

#### get_approved_quotes(offset: int = 0) -> List[QuoteDocument]

Retrieves quotes with approved status.

#### get_pending_quotes(offset: int = 0) -> List[QuoteDocument]

Retrieves quotes with pending status.

#### get_expired_quotes(offset: int = 0) -> List[QuoteDocument]

Retrieves quotes past their valid_until date.

### Product-Based Filtering

#### get_quotes_by_product_type(product_type: str, offset: int = 0) -> List[QuoteDocument]

Retrieves quotes filtered by product type or category.

### Individual Quote Retrieval

#### get_quote_by_id(quote_id: str) -> Optional[QuoteDocument]

Retrieves a single quote as a validated QuoteDocument object.

## Count Methods

### Total Counts

#### count_quotes() -> int

Returns total number of quotes in collection.

#### count_all_quotes() -> int

Alias for count_quotes() for consistency.

### Filtered Counts

#### count_quotes_by_status(status: str) -> int

Returns count of quotes by specific status.

#### count_quotes_by_product_type(product_type: str) -> int

Returns count of quotes by product type.

#### count_quotes_by_value_range(min_value: float, max_value: float) -> int

Returns count of quotes within a value range.

## Statistics and Analytics

### Quote Statistics

#### get_quote_stats() -> Dict[str, int]

Returns comprehensive quote statistics including:

- Total quotes count
- Quotes by status breakdown
- Average quote value
- Quotes by time period
- Conversion rates

### Revenue Analytics

#### get_revenue_by_period(start_date: datetime, end_date: datetime) -> Dict[str, float]

Returns revenue analytics for specified time period.

#### get_top_products() -> List[Dict[str, Any]]

Returns top-performing products by quote volume.

## Status Management

### Status Updates

#### update_quote_status(quote_id: str, new_status: str) -> bool

Updates quote status with automatic timestamp and validation.

#### approve_quote(quote_id: str) -> bool

Approves a quote with status change and notifications.

#### reject_quote(quote_id: str, reason: str) -> bool

Rejects a quote with reason tracking.

### Expiration Handling

#### mark_expired_quotes() -> int

Batch operation to mark expired quotes based on valid_until date.

#### extend_quote_validity(quote_id: str, new_date: datetime) -> bool

Extends quote validity period.

## Database Indexes

### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `status` (ascending) - Status filtering
- `created_at` (descending) - Temporal sorting
- `total_amount` (ascending) - Value-based sorting
- `valid_until` (ascending) - Expiration queries

### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact timeline
- `{status: 1, created_at: -1}` - Status with recency
- `{total_amount: 1, status: 1}` - Value with status

## API Endpoints

### REST Routes

All routes are prefixed with `/api/v1/mongo/quotes/`

#### GET /recent?page=1

Retrieves recent quotes with pagination.

#### GET /oldest?page=1

Retrieves oldest quotes with pagination.

#### GET /by-status/{status}?page=1

Retrieves quotes by status with pagination.

#### GET /by-value?page=1&ascending=true

Retrieves quotes by value with pagination.

#### GET /by-product-type/{product_type}?page=1

Retrieves quotes by product type with pagination.

#### GET /approved?page=1

Retrieves approved quotes with pagination.

#### GET /pending?page=1

Retrieves pending quotes with pagination.

#### GET /expired?page=1

Retrieves expired quotes with pagination.

#### GET /{quote_id}

Retrieves a single quote by ID.

#### GET /stats

Retrieves comprehensive quote statistics.

## Error Handling

### Common Errors

- **QuoteNotFound**: Quote ID not found
- **ValidationError**: Invalid quote data
- **StatusTransitionError**: Invalid status change
- **ExpirationError**: Quote past validity period

### Error Response Format

```json
{
  "error": "QuoteNotFound",
  "message": "Quote with ID 'abc123' not found",
  "code": "QUOTE_NOT_FOUND"
}
```

## Usage Examples

### Creating a Quote

```python
quote_data = {
    "contact_id": "hubspot_12345",
    "status": "pending",
    "total_amount": 1500.00,
    "valid_until": datetime.now() + timedelta(days=30),
    "items": [
        {"product": "Moving Service", "quantity": 1, "price": 1500.00}
    ]
}
quote_id = await mongo_service.create_quote(quote_data)
```

### Paginated Retrieval

```python
# Get page 2 of recent quotes
page = 2
offset = (page - 1) * 10
quotes = await mongo_service.get_recent_quotes(offset=offset)

# Get total count for pagination
total = await mongo_service.count_quotes()
total_pages = (total + 9) // 10
```

### Status Management

```python
# Update quote status
success = await mongo_service.update_quote_status(
    quote_id="quote_123",
    new_status="approved"
)

# Get statistics
stats = await mongo_service.get_quote_stats()
```

## Performance Considerations

### Optimization Tips

1. **Use indexes**: Ensure proper indexing for query patterns
2. **Limit results**: Always use pagination for large datasets
3. **Filter early**: Apply status/date filters before sorting
4. **Batch operations**: Use bulk operations for multiple updates
5. **Monitor performance**: Track query execution times

### Query Patterns

- **Recent quotes**: Use created_at descending index
- **Status filtering**: Use status index first
- **Value sorting**: Use total_amount index
- **Contact queries**: Use contact_id index

## Best Practices

1. **Validate data**: Use QuoteDocument model for validation
2. **Handle expiration**: Check valid_until before processing
3. **Track changes**: Log all status changes
4. **Monitor metrics**: Track conversion rates and performance
5. **Use transactions**: For complex multi-document operations

## Future Enhancements

1. **Quote templates**: Standardized quote templates
2. **Approval workflows**: Multi-step approval processes
3. **Integration**: Enhanced CRM integration
4. **Analytics**: Advanced revenue analytics
5. **Automation**: Automated quote generation
