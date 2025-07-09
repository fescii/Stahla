# MongoDB Classification Operations Documentation

## Overview

The MongoDB Classification Operations module (`app/services/mongo/classify/operations.py`) provides comprehensive database operations for managing classification documents within the Stahla AI SDR system. This module handles the complete lifecycle of classification data, from creation and updates to complex querying with pagination support.

## Table of Contents

1. [Class Overview](#class-overview)
2. [Core Operations](#core-operations)
3. [Pagination Methods](#pagination-methods)
4. [Query Methods](#query-methods)
5. [Statistics and Analytics](#statistics-and-analytics)
6. [Error Handling](#error-handling)
7. [Usage Examples](#usage-examples)
8. [Dependencies](#dependencies)

## Class Overview

### ClassifyOperations

The `ClassifyOperations` class serves as the primary interface for all MongoDB operations related to classification documents. It provides a comprehensive set of methods for CRUD operations, pagination, filtering, and analytics.

```python
class ClassifyOperations:
    """Handles MongoDB operations for classify collection."""
    
    def __init__(self, db):
        self.db = db
```

**Initialization:**

- `db`: MongoDB database instance from the motor driver

**Collection:** Uses `CLASSIFY_COLLECTION` from `app.services.mongo.collections.names`

## Core Operations

### Document Management

#### create_classify(classify_data: Dict[str, Any]) -> Optional[str]

Creates a new classification document in the database.

**Parameters:**
- `classify_data`: Dictionary containing classification data that will be validated against `ClassifyDocument` model

**Returns:**
- Classification ID if successful, None otherwise

**Features:**
- Validates data using `ClassifyDocument` Pydantic model
- Automatically sets `created_at` and `updated_at` timestamps
- Converts `id` field to `_id` for MongoDB compatibility
- Comprehensive error logging

#### update_classify(classify_id: str, update_data: Dict[str, Any]) -> bool

Updates an existing classification document.

**Parameters:**
- `classify_id`: Unique identifier of the classification to update
- `update_data`: Dictionary containing fields to update

**Returns:**
- True if successful, False otherwise

**Features:**
- Automatically updates `updated_at` timestamp
- Validates existence before updating
- Detailed logging of update operations

#### get_classify(classify_id: str) -> Optional[Dict[str, Any]]

Retrieves a single classification document by ID.

**Parameters:**
- `classify_id`: Unique identifier of the classification

**Returns:**
- Classification document if found, None otherwise

**Features:**
- Converts MongoDB `_id` back to `id` field
- Handles missing documents gracefully

#### delete_classify(classify_id: str) -> bool

Deletes a classification document by ID.

**Parameters:**
- `classify_id`: Unique identifier of the classification to delete

**Returns:**
- True if successful, False otherwise

## Pagination Methods

The module provides extensive pagination support with a hardcoded limit of 10 items per page and offset calculation based on page numbers.

### Core Pagination Pattern

All pagination methods follow this pattern:
- **Limit:** Hardcoded to 10 items per page
- **Offset:** Calculated as `(page - 1) * 10`
- **Sorting:** Typically by `created_at` in descending order (newest first)

### Available Pagination Methods

#### get_recent_classifications(limit: int = 10, offset: int = 0) -> List[ClassifyDocument]

Retrieves the most recent classifications ordered by creation date.

**Parameters:**
- `limit`: Maximum number of results (default: 10)
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_oldest_classifications(limit: int = 10, offset: int = 0) -> List[ClassifyDocument]

Retrieves the oldest classifications ordered by creation date.

**Parameters:**
- `limit`: Maximum number of results (default: 10)
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_classifications_by_status(status: ClassifyStatus, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]

Retrieves classifications filtered by status with pagination.

**Parameters:**
- `status`: `ClassifyStatus` enum value to filter by
- `limit`: Maximum number of results (default: 10)
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_classifications_by_lead_type(lead_type: str, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]

Retrieves classifications filtered by lead type with pagination.

**Parameters:**
- `lead_type`: Lead type to filter by ("Services", "Logistics", "Leads", "Disqualify")
- `limit`: Maximum number of results (default: 10)
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_classifications_by_confidence(min_confidence: float, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]

Retrieves classifications filtered by minimum confidence level.

**Parameters:**
- `min_confidence`: Minimum confidence threshold (0.0 to 1.0)
- `limit`: Maximum number of results (default: 10)
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_classifications_by_source(source: str, limit: int = 10, offset: int = 0) -> List[ClassifyDocument]

Retrieves classifications filtered by source with pagination.

**Parameters:**
- `source`: Source system identifier
- `limit`: Maximum number of results (default: 10)
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_successful_classifications(offset: int = 0) -> List[ClassifyDocument]

Retrieves successful classifications (status: "success") with pagination.

**Parameters:**
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_failed_classifications(offset: int = 0) -> List[ClassifyDocument]

Retrieves failed classifications (status: "failed") with pagination.

**Parameters:**
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

#### get_disqualified_classifications(offset: int = 0) -> List[ClassifyDocument]

Retrieves disqualified classifications (classification_result: "Disqualify") with pagination.

**Parameters:**
- `offset`: Number of records to skip for pagination

**Returns:**
- List of `ClassifyDocument` objects

## Query Methods

### Contact-Based Queries

#### get_classify_by_contact(contact_id: str) -> Optional[Dict[str, Any]]

Retrieves the most recent classification for a specific contact.

**Parameters:**
- `contact_id`: HubSpot contact ID

**Returns:**
- Most recent classification document for the contact, None if not found

#### get_classifications_by_contact(contact_id: str, limit: int = 10) -> List[Dict[str, Any]]

Retrieves all classifications for a specific contact with limit.

**Parameters:**
- `contact_id`: HubSpot contact ID
- `limit`: Maximum number of classifications to return

**Returns:**
- List of classification documents for the contact

### Advanced Query Methods

#### get_classifications_requiring_review(limit: int = 100) -> List[Dict[str, Any]]

Retrieves classifications that require human review.

**Parameters:**
- `limit`: Maximum number of classifications to return (default: 100)

**Returns:**
- List of classification documents requiring review

#### get_classifications_paginated(...) -> Tuple[List[Dict[str, Any]], int]

Comprehensive paginated query with filtering and sorting options.

**Parameters:**
- `page`: Page number (1-based)
- `page_size`: Number of items per page
- `status_filter`: Optional status filter
- `lead_type_filter`: Optional lead type filter
- `sort_field`: Field to sort by (default: "created_at")
- `sort_order`: Sort order (1 for ascending, -1 for descending)

**Returns:**
- Tuple of (classification documents, total count)

#### get_classification_by_id(classify_id: str) -> Optional[ClassifyDocument]

Retrieves a single classification by ID as a `ClassifyDocument` object.

**Parameters:**
- `classify_id`: Unique identifier of the classification

**Returns:**
- `ClassifyDocument` object if found, None otherwise

## Statistics and Analytics

### Count Methods

The module provides comprehensive counting methods for analytics and pagination support:

#### count_classifications() -> int
Returns the total number of classifications in the collection.

#### count_classifications_by_status(status: ClassifyStatus) -> int
Returns the count of classifications by specific status.

#### count_classifications_by_lead_type(lead_type: str) -> int
Returns the count of classifications by lead type.

#### count_classifications_by_confidence(min_confidence: float) -> int
Returns the count of classifications above a minimum confidence threshold.

#### count_classifications_by_source(source: str) -> int
Returns the count of classifications by source system.

#### count_all_classifications() -> int
Alias for `count_classifications()` for consistency.

### Statistics Dashboard

#### get_classify_stats() -> Dict[str, int]

Provides comprehensive statistics about classifications.

**Returns:**
Dictionary containing:
- `total_classifications`: Total number of classifications
- `{status}_classifications`: Count for each `ClassifyStatus`
- `{lead_type}_leads`: Count for each lead type
- `requiring_review`: Count of classifications requiring human review

### Status Management

#### update_classify_status(classify_id: str, status: ClassifyStatus, error_message: Optional[str] = None) -> bool

Updates a classification's status with appropriate metadata.

**Parameters:**
- `classify_id`: Unique identifier of the classification
- `status`: New `ClassifyStatus` value
- `error_message`: Optional error message for failed status

**Features:**
- Automatically sets `updated_at` timestamp
- Sets `classified_at` timestamp when status is COMPLETED
- Includes error message handling for failed classifications

## Error Handling

The module implements comprehensive error handling with the following features:

### Logging Strategy

- **logfire**: Used for structured logging with context
- **Error Context**: All errors include relevant context (IDs, parameters)
- **Exception Details**: Full exception information captured with `exc_info=True`
- **Performance Logging**: Success operations logged at debug level
- **Failure Logging**: Errors logged at error level with full stack traces

### Error Response Patterns

- **Graceful Degradation**: Methods return appropriate default values (None, [], False, 0)
- **Consistent Return Types**: All methods maintain consistent return type contracts
- **Error Isolation**: Individual operation failures don't affect overall system stability

### Common Error Scenarios

1. **Connection Issues**: MongoDB connection failures
2. **Validation Errors**: Data model validation failures
3. **Document Not Found**: Queries for non-existent documents
4. **Constraint Violations**: Database constraint violations
5. **Data Type Errors**: Type conversion or compatibility issues

## Usage Examples

### Basic CRUD Operations

```python
# Initialize operations
classify_ops = ClassifyOperations(db)

# Create a new classification
classify_data = {
    "contact_id": "12345",
    "status": "pending",
    "lead_type": "Services",
    "confidence": 0.85,
    "source": "phone_call"
}
classify_id = await classify_ops.create_classify(classify_data)

# Retrieve a classification
classification = await classify_ops.get_classify(classify_id)

# Update classification status
success = await classify_ops.update_classify_status(
    classify_id, 
    ClassifyStatus.COMPLETED
)
```

### Pagination Examples

```python
# Get recent classifications with pagination
page = 1
offset = (page - 1) * 10
recent_classifications = await classify_ops.get_recent_classifications(
    limit=10, 
    offset=offset
)

# Get classifications by status with pagination
pending_classifications = await classify_ops.get_classifications_by_status(
    ClassifyStatus.PENDING,
    limit=10,
    offset=offset
)

# Get count for pagination metadata
total_count = await classify_ops.count_classifications()
total_pages = (total_count + 9) // 10  # Ceiling division
```

### Analytics and Statistics

```python
# Get comprehensive statistics
stats = await classify_ops.get_classify_stats()
print(f"Total classifications: {stats['total_classifications']}")
print(f"Pending: {stats['pending_classifications']}")
print(f"Completed: {stats['completed_classifications']}")

# Get classifications requiring review
review_needed = await classify_ops.get_classifications_requiring_review()
```

### Contact-Based Queries

```python
# Get most recent classification for a contact
contact_id = "hubspot_contact_123"
latest_classification = await classify_ops.get_classify_by_contact(contact_id)

# Get all classifications for a contact
all_contact_classifications = await classify_ops.get_classifications_by_contact(
    contact_id,
    limit=50
)
```

## Dependencies

### External Libraries

- **motor**: Async MongoDB driver for Python
- **logfire**: Structured logging library
- **typing**: Type hints and annotations
- **datetime**: Date and time handling

### Internal Dependencies

- **ClassifyDocument**: Pydantic model for classification data validation
- **ClassifyStatus**: Enum for classification status values
- **CLASSIFY_COLLECTION**: Collection name constant

### Configuration Requirements

- **MongoDB Connection**: Active MongoDB database instance
- **Collection Setup**: Properly configured classification collection
- **Indexes**: Recommended indexes for performance:
  - `contact_id` (for contact-based queries)
  - `status` (for status-based filtering)
  - `lead_type` (for lead type filtering)
  - `created_at` (for temporal sorting)
  - `confidence` (for confidence-based queries)

## Performance Considerations

### Indexing Strategy

For optimal performance, ensure the following indexes are created:

```javascript
// MongoDB index creation commands
db.classify.createIndex({ "contact_id": 1 })
db.classify.createIndex({ "status": 1 })
db.classify.createIndex({ "lead_type": 1 })
db.classify.createIndex({ "created_at": -1 })
db.classify.createIndex({ "confidence": 1 })
db.classify.createIndex({ "source": 1 })
db.classify.createIndex({ "requires_human_review": 1 })
```

### Query Optimization

- **Pagination**: Uses skip/limit pattern with proper indexing
- **Filtering**: Combines multiple filters efficiently
- **Sorting**: Leverages indexes for sorting operations
- **Projection**: Future enhancement opportunity for selective field retrieval

### Monitoring and Metrics

- **Operation Timing**: All operations logged with performance context
- **Error Rates**: Comprehensive error tracking and logging
- **Usage Patterns**: Detailed logging for usage analytics

## Best Practices

1. **Always handle None returns**: All query methods may return None
2. **Use pagination consistently**: Implement proper pagination in API endpoints
3. **Validate input data**: Leverage Pydantic models for data validation
4. **Monitor error logs**: Implement proper monitoring for error patterns
5. **Use appropriate count methods**: Choose the right counting method for your use case
6. **Implement retry logic**: Add retry mechanisms for transient failures
7. **Cache frequently accessed data**: Consider caching for high-frequency queries

## Future Enhancements

1. **Bulk Operations**: Add support for bulk inserts and updates
2. **Aggregation Pipeline**: Implement complex aggregation queries
3. **Search Functionality**: Add full-text search capabilities
4. **Data Archiving**: Implement data retention and archiving strategies
5. **Performance Monitoring**: Add detailed performance metrics and monitoring
6. **Caching Layer**: Implement Redis caching for frequently accessed data

---

This documentation provides a comprehensive overview of the MongoDB Classification Operations module. For specific implementation details, refer to the source code at `app/services/mongo/classify/operations.py`.
