# MongoDB Sheets Collection Documentation

## Overview

The sheets collection manages Google Sheets synchronization for the Stahla AI SDR system. It provides operations for syncing configuration data, products, branches, and other business data from Google Sheets to MongoDB.

## Collection Structure

**Operations Class**: `SheetsOperations` (app/services/mongo/sheets/operations.py)  

## Collections Managed

- **sheet_products** - Product catalog data
- **sheet_generators** - Generator configuration
- **sheet_branches** - Branch information
- **sheet_config** - General configuration
- **sheet_states** - State/location data

## Core Operations

### Data Synchronization

#### replace_sheet_collection_data(collection_name: str, data: List[Dict[str, Any]], id_field: str)

Replaces entire collection data with new data from Google Sheets using upsert operations.

#### upsert_sheet_config_document(document_id: str, config_data: Dict[str, Any], config_type: Optional[str] = None)

Upserts a single configuration document in the sheet_config collection.

## Usage Examples

### Syncing Sheet Data

```python
# Sync products from Google Sheets
await mongo_service.replace_sheet_collection_data(
    collection_name="sheet_products",
    data=products_data,
    id_field="product_id"
)
```

### Configuration Management

```python
# Update configuration document
await mongo_service.upsert_sheet_config_document(
    document_id="pricing_config",
    config_data={"base_rate": 100.0, "hourly_rate": 50.0},
    config_type="pricing"
)
```

## Database Indexes

- Collection-specific indexes based on id_field
- Temporal indexes for tracking sync operations
- Performance indexes for frequent queries

## Best Practices

1. **Atomic operations**: Use bulk operations for large datasets
2. **Validation**: Validate data before syncing
3. **Error handling**: Implement comprehensive error handling
4. **Performance**: Use appropriate batch sizes
5. **Monitoring**: Track sync performance and failures
