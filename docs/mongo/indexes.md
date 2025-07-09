# MongoDB Indexing Strategy Documentation

## Overview

The MongoDB indexing strategy for the Stahla AI SDR system is designed to optimize query performance across all collections while maintaining efficient write operations.

## Index Manager

**Class**: `IndexManager` (app/services/mongo/connection/indexes.py)  
**Purpose**: Centralized index creation and management for all collections  

## Collection Indexes

### Quotes Collection

#### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `status` (ascending) - Status filtering
- `created_at` (descending) - Temporal sorting
- `total_amount` (ascending) - Value-based sorting
- `valid_until` (ascending) - Expiration queries

#### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact timeline
- `{status: 1, created_at: -1}` - Status with recency

### Calls Collection

#### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `call_id` (ascending) - Bland AI integration
- `status` (ascending) - Status filtering
- `created_at` (descending) - Temporal sorting
- `phone_number` (ascending) - Phone queries

#### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact call history
- `{status: 1, created_at: -1}` - Status with recency

### Classify Collection

#### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `status` (ascending) - Status filtering
- `lead_type` (ascending) - Lead type filtering
- `created_at` (descending) - Temporal sorting
- `confidence` (ascending) - Confidence queries

#### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact classification history
- `{status: 1, lead_type: 1}` - Status with lead type

### Location Collection

#### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `delivery_location` (ascending) - Address lookups
- `status` (ascending) - Status filtering
- `branch` (ascending) - Branch filtering
- `created_at` (descending) - Temporal sorting
- `coordinates` (2dsphere) - Geographic queries

#### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact location history
- `{within_service_area: 1, branch: 1}` - Service area by branch

### Emails Collection

#### Primary Indexes

- `contact_id` (ascending) - Contact-based queries
- `message_id` (ascending) - Message identification
- `thread_id` (ascending) - Thread queries
- `status` (ascending) - Status filtering
- `category` (ascending) - Category filtering
- `direction` (ascending) - Direction filtering
- `created_at` (descending) - Temporal sorting
- `from_email` (ascending) - Sender queries

#### Compound Indexes

- `{contact_id: 1, created_at: -1}` - Contact email history
- `{thread_id: 1, created_at: 1}` - Thread chronology

## Supporting Collections

### Reports Collection

- `report_type` (ascending) - Type filtering
- `timestamp` (descending) - Temporal sorting
- `success` (ascending) - Success filtering

### Stats Collection

- `_id` (ascending) - Primary key for stat names

### Sheets Collections

- Dynamic indexes based on id_field
- Temporal indexes for sync tracking

## Index Creation Process

### Automatic Creation

The `IndexManager` automatically creates all indexes during system initialization:

```python
async def create_indexes(self):
    """Creates all indexes for all collections."""
    await self._create_quotes_indexes()
    await self._create_calls_indexes()
    await self._create_classify_indexes()
    await self._create_location_indexes()
    await self._create_emails_indexes()
```

### Manual Index Management

Individual collection indexes can be created separately:

```python
index_manager = IndexManager(db)
await index_manager._create_quotes_indexes()
```

## Performance Optimization

### Query Patterns

1. **Temporal queries**: Use created_at descending indexes
2. **Status filtering**: Use status indexes first
3. **Contact queries**: Use contact_id indexes
4. **Geographic queries**: Use 2dsphere indexes for locations

### Best Practices

1. **Compound indexes**: Order fields by selectivity
2. **Sparse indexes**: Use for optional fields
3. **Unique indexes**: Implement for unique constraints
4. **Monitoring**: Regular index usage monitoring
5. **Maintenance**: Regular index optimization

## Index Monitoring

### Performance Metrics

- Query execution times
- Index hit rates
- Index size usage
- Write performance impact

### Optimization Strategies

- Regular explain plan analysis
- Index usage statistics
- Query pattern analysis
- Performance testing

## Maintenance

### Regular Tasks

1. **Index analysis**: Regular index usage analysis
2. **Performance monitoring**: Query performance tracking
3. **Optimization**: Index optimization based on usage patterns
4. **Cleanup**: Remove unused indexes
5. **Updates**: Update indexes for new query patterns

### Tools and Commands

```javascript
// MongoDB index analysis commands
db.collection.getIndexes()
db.collection.stats()
db.collection.explain("executionStats")
```

## Future Considerations

1. **New collections**: Index strategy for new collections
2. **Query evolution**: Index updates for changing query patterns
3. **Performance scaling**: Index optimization for larger datasets
4. **Sharding**: Index considerations for horizontal scaling
5. **Aggregation**: Specialized indexes for complex aggregations
