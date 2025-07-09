# MongoDB Statistics Collection Documentation

## Overview

The stats collection manages dashboard statistics and metrics for the Stahla AI SDR system. It provides real-time performance tracking and analytics for key system operations.

## Collection Structure

**Collection Name**: `dashboard_stats`  
**Operations Class**: `StatsOperations` (app/services/mongo/stats/operations.py)  

## Document Schema

### Core Fields

- **_id** (string): Statistic name identifier
- **total** (int): Total operation count
- **successful** (int): Successful operation count
- **failed** (int): Failed operation count

## Core Operations

### Statistics Management

#### increment_request_stat(stat_name: str, success: bool)

Increments counter for a specific statistic based on success status.

#### get_dashboard_stats() -> Dict[str, Dict[str, int]]

Retrieves comprehensive dashboard statistics for:

- quote_requests
- location_lookups
- Other system operations

## Usage Examples

### Incrementing Statistics

```python
# Increment successful quote request
await mongo_service.increment_request_stat("quote_requests", True)

# Increment failed location lookup
await mongo_service.increment_request_stat("location_lookups", False)
```

### Retrieving Statistics

```python
# Get all dashboard stats
stats = await mongo_service.get_dashboard_stats()
# Returns: {"quote_requests": {"total": 100, "successful": 85, "failed": 15}}
```

## Database Indexes

- `_id` (ascending) - Primary key for stat names

## Best Practices

1. **Consistent naming**: Use standardized stat_name values
2. **Atomic operations**: Use atomic increment operations
3. **Performance**: Statistics collection is optimized for high-frequency updates
4. **Monitoring**: Regular monitoring of key metrics
5. **Alerting**: Set up alerts for unusual failure rates
