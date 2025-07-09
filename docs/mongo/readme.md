# MongoDB Collections Documentation

This directory contains comprehensive documentation for all MongoDB collections used in the Stahla AI SDR system.

## Collection Overview

The Stahla MongoDB implementation provides persistent storage for all business-critical data with comprehensive pagination, filtering, and analytics capabilities.

### Core Business Collections

- **[quotes.md](quotes.md)** - Quote management and pricing operations
- **[calls.md](calls.md)** - Call logging and Bland AI integration
- **[classify.md](classify.md)** - Lead classification and AI categorization
- **[location.md](location.md)** - Location verification and service area management
- **[emails.md](emails.md)** - Email tracking and automation

### Supporting Collections

- **[reports.md](reports.md)** - System reporting and analytics
- **[stats.md](stats.md)** - Dashboard statistics and metrics
- **[sheets.md](sheets.md)** - Google Sheets synchronization
- **[indexes.md](indexes.md)** - Database indexing strategy

## Common Features

All collections implement:

- **Pagination**: Hardcoded limit of 10 items per page
- **Filtering**: Collection-specific filter options
- **Sorting**: Temporal and value-based sorting
- **Statistics**: Comprehensive analytics and counting
- **Error Handling**: Robust error logging and graceful degradation

## Database Architecture

### Connection Management

- **Service**: `MongoService` (app/services/mongo/service.py)
- **Connection**: Async motor driver with connection pooling
- **Initialization**: Automatic index creation and validation

### Data Models

- **Pydantic Models**: Strict typing and validation
- **Document Structure**: Consistent field naming and structure
- **Timestamps**: Automatic created_at and updated_at handling

### Performance Optimization

- **Indexes**: Strategic indexing for query performance
- **Aggregation**: Efficient data aggregation pipelines
- **Caching**: Ready for Redis integration

## API Integration

### FastAPI Endpoints

- **Router Structure**: Organized by collection type
- **Response Models**: Consistent pagination and error responses
- **Authentication**: Integrated security middleware

### REST Documentation

- **Examples**: Comprehensive .http files in `/rest/mongo/`
- **Testing**: Ready-to-use API examples
- **Authentication**: Bearer token examples

## Development Guidelines

### File Organization

Following strict naming conventions:
- All folder names: lowercase only
- File names: descriptive and lowercase
- Maximum folder depth for categorization

### Code Structure

- **Operations**: Collection-specific operation classes
- **Models**: Pydantic document models
- **Indexes**: Centralized index management
- **Service**: Unified service interface

### Best Practices

1. Always use pagination for list operations
2. Implement proper error handling
3. Use Pydantic models for data validation
4. Log all operations with appropriate context
5. Maintain consistent response formats

## Getting Started

1. **Read Collection Documentation**: Start with the collection you need
2. **Check API Examples**: Use REST files for testing
3. **Review Models**: Understand data structures
4. **Implement Pagination**: Use consistent patterns
5. **Monitor Performance**: Check logs and metrics

## Quick Reference

### Common Operations

```python
# Get paginated results
page = 1
offset = (page - 1) * 10
results = await mongo_service.get_recent_[collection](offset=offset)

# Count total items
total = await mongo_service.count_[collection]()

# Get statistics
stats = await mongo_service.get_[collection]_stats()
```

### Response Patterns

- **Success**: `{"data": [...], "total": int, "page": int}`
- **Error**: `{"error": "message", "code": "ERROR_CODE"}`
- **Empty**: `{"data": [], "total": 0, "page": 1}`

## Support

For detailed implementation examples, see the `/rest/mongo/` directory with comprehensive API documentation and examples.
