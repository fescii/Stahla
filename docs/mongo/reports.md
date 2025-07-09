# MongoDB Reports Collection Documentation

## Overview

The reports collection manages system reporting and analytics for the Stahla AI SDR system. It provides comprehensive logging, tracking, and analytics for all system operations and events.

## Collection Structure

**Collection Name**: `reports`  
**Operations Class**: `ReportsOperations` (app/services/mongo/reports/operations.py)  

## Document Schema

### Core Fields

- **timestamp** (datetime): Report creation timestamp
- **report_type** (string): Type of report (quote_request, location_lookup, etc.)
- **success** (boolean): Operation success status
- **data** (object): Report data payload
- **error_message** (string): Error details if failed

## Core Operations

### Report Logging

#### log_report(report_type: str, data: Dict[str, Any], success: bool, error_message: Optional[str] = None)

Logs a new report to the collection with automatic timestamp.

### Report Retrieval

#### get_recent_reports(report_type: Optional[Union[str, List[str]]] = None, limit: int = 100) -> List[Dict[str, Any]]

Retrieves recent reports with optional type filtering.

#### get_report_summary() -> Dict[str, Any]

Provides aggregated report statistics including:

- Total reports count
- Success/failure breakdown
- Reports by type
- Performance metrics

## Usage Examples

### Logging a Report

```python
await mongo_service.log_report(
    report_type="quote_request",
    data={"quote_id": "q123", "amount": 1500.00},
    success=True
)
```

### Retrieving Reports

```python
# Get recent reports
reports = await mongo_service.get_recent_reports(
    report_type="quote_request",
    limit=50
)

# Get summary statistics
summary = await mongo_service.get_report_summary()
```

## Database Indexes

- `report_type` (ascending) - Type filtering
- `timestamp` (descending) - Temporal sorting
- `success` (ascending) - Success filtering

## Best Practices

1. **Consistent types**: Use standardized report_type values
2. **Structured data**: Maintain consistent data payload structure
3. **Error handling**: Always include error_message for failures
4. **Performance**: Use appropriate limits for large datasets
5. **Monitoring**: Regular monitoring of report patterns
