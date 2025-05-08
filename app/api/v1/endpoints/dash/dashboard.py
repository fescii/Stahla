import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Response
from typing import List, Optional
from pydantic import BaseModel # Import BaseModel

# Import dashboard models and services
from app.models.dash.dashboard import (
    DashboardOverview, RequestLogEntry, CacheClearResult, CacheItem, 
    CacheSearchResult, ClearCacheRequest, ClearPricingCacheRequest, ErrorLogEntry, 
    ErrorLogResponse # Import ErrorLogResponse
)
from app.models.common import GenericResponse
from app.services.dash.dashboard import DashboardService # Import service class
# Import the dependency injector from core
from app.core.dependencies import get_dashboard_service_dep 
from app.core.security import get_current_user # Import JWT dependency
from app.services.quote.sync import PRICING_CATALOG_CACHE_KEY # Import cache key

# Simple model for message responses
class MessageResponse(BaseModel):
    message: str

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/overview", 
    response_model=GenericResponse[DashboardOverview], # Use GenericResponse
    summary="Get Dashboard Overview",
    description="Retrieves aggregated statistics and recent activity for the dashboard.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def get_dashboard_overview_endpoint(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """API endpoint to fetch dashboard overview data."""
    logger.info("Received request for dashboard overview.")
    try:
        overview = await dashboard_service.get_dashboard_overview()
        return GenericResponse[DashboardOverview](data=overview) # Wrap response
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}", exc_info=True)
        # Let FastAPI handle the exception for 500 error
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data.")

@router.get(
    "/recent-requests", 
    response_model=GenericResponse[List[RequestLogEntry]], # Use GenericResponse
    summary="Get Recent Request Logs",
    description="Retrieves a list of recent logged requests (currently placeholder).",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def get_recent_requests_endpoint(
    limit: int = 20, # Default limit
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """API endpoint to fetch recent request logs."""
    logger.info(f"Received request for recent requests (limit: {limit}).")
    try:
        # TODO: Replace with MongoDB fetch using dashboard_service.mongo.get_recent_reports
        requests = [] # Placeholder
        logger.warning("Returning empty list for /recent-requests as MongoDB fetch is not implemented here yet.")
        return GenericResponse[List[RequestLogEntry]](data=requests) # Wrap response
    except Exception as e:
        logger.error(f"Error fetching recent requests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve recent request data.")

@router.post(
    "/sync/trigger",
    response_model=GenericResponse[MessageResponse], # Use GenericResponse
    summary="Trigger Manual Sheet Sync",
    description="Manually triggers an immediate synchronization of pricing, config, and branches from Google Sheets.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint (or use admin)
)
async def trigger_manual_sync(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """Endpoint to manually trigger a Google Sheet sync."""
    # Add permission check if needed: if not current_user.is_admin: ...
    logger.info(f"User requested manual sheet sync trigger.")
    success = await dashboard_service.trigger_sheet_sync()
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trigger sync. Check logs.")
    return GenericResponse[MessageResponse](data=MessageResponse(message="Manual sync triggered successfully.")) # Wrap response

@router.get(
    "/cache/search",
    response_model=GenericResponse[List[CacheSearchResult]], # Use GenericResponse
    summary="Search Cache Keys",
    description="Searches for Redis cache keys matching a glob pattern (e.g., 'maps:distance:*', 'pricing:*'). Limited results.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def search_cache_keys(
    pattern: str = Query(..., description="Glob pattern to search keys (e.g., 'maps:distance:*:*123main*')"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """Endpoint to search cache keys."""
    logger.info(f"Searching cache keys with pattern: {pattern}")
    results = await dashboard_service.search_cache_keys(pattern)
    return GenericResponse[List[CacheSearchResult]](data=results) # Wrap response


@router.get(
    "/cache/item",
    response_model=GenericResponse[CacheItem], # Use GenericResponse
    summary="View Specific Cache Item",
    description="Retrieves the value and TTL of a specific Redis cache key.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def view_cache_item(
    key: str = Query(..., description="The exact cache key to view."),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """Endpoint to view a specific cached item."""
    logger.info(f"Requested cache key view: {key}")
    cache_data = await dashboard_service.get_cache_item(key)
    if cache_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cache key not found")
    return GenericResponse[CacheItem](data=cache_data) # Wrap response

@router.post(
    "/cache/clear/item",
    # No response body for 204, so no response_model needed here
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Specific Cache Item",
    description="Manually clears a specific cache key from Redis.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint (or use admin)
)
async def clear_cache_item(
    payload: ClearCacheRequest = Body(...), # Use request body
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """Endpoint to manually clear a specific cache key."""
    # Add permission check if needed
    logger.info(f"Requested cache clear for key: {payload.key}")
    try:
        success = await dashboard_service.clear_cache_item(payload.key)
        if not success:
            # Don't raise 404 if key didn't exist, just log it. Return 204 anyway.
            logger.warning(f"Attempted to clear non-existent or already expired key: {payload.key}")
    except Exception as e:
        logger.error(f"Error clearing cache key {payload.key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear cache key {payload.key}.")
    # Return Response with 204 status code directly
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cache/clear/pricing",
    # No response body for 204
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Pricing Catalog Cache",
    description="Manually clears the entire pricing catalog cache, forcing a refresh on the next sync.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint (or use admin)
)
async def clear_pricing_cache(
    payload: ClearPricingCacheRequest = Body(...), # Use request body for confirmation
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """Endpoint to clear the pricing catalog cache."""
    if not payload.confirm:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation flag must be set to true.")
    # Add permission check if needed
    logger.warning(f"Requested CLEARING ENTIRE PRICING CACHE.")
    success = await dashboard_service.clear_pricing_catalog_cache()
    # Log even if key didn't exist
    logger.info(f"Pricing cache clear operation completed for key '{PRICING_CATALOG_CACHE_KEY}'. Success: {success}")
    # Return Response with 204 status code directly
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cache/clear/maps",
    response_model=GenericResponse[MessageResponse], # Use GenericResponse
    summary="Clear Maps Location Cache",
    description="Clears Google Maps distance cache keys matching a location pattern (use carefully).",
    dependencies=[Depends(get_current_user)] # Secure this endpoint (or use admin)
)
async def clear_maps_cache(
    location_pattern: str = Body(..., embed=True, description="Pattern to match in the delivery location part of the cache key (e.g., '*123mainst*'). Use '*' as wildcard."),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep) # Use core dependency
):
    """Endpoint to clear maps cache keys by location pattern."""
    # Add permission check if needed
    logger.warning(f"Requested clearing maps cache with pattern: {location_pattern}")
    if not location_pattern or len(location_pattern) < 3: # Basic safety check
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location pattern must be provided and at least 3 characters.")
    deleted_count = await dashboard_service.clear_maps_location_cache(f"*{location_pattern}*") # Add wildcards for broader match
    # Wrap response
    return GenericResponse[MessageResponse](data=MessageResponse(message=f"Cleared {deleted_count} maps cache keys matching pattern '*{location_pattern}*."))


# --- Error Log Viewing --- 
@router.get(
    "/errors",
    response_model=GenericResponse[ErrorLogResponse], # Use GenericResponse wrapping ErrorLogResponse
    summary="Get Recent Error Logs",
    description="Retrieves recent error logs recorded in the database, optionally filtered by type.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def get_error_logs_endpoint(
    report_type: Optional[str] = Query(None, description="Filter logs by report_type (e.g., 'SheetFetchError_products', 'ValueError')"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of error logs to return."),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep)
):
    """API endpoint to fetch recent error logs."""
    logger.info(f"Received request for error logs. Type: {report_type}, Limit: {limit}")
    try:
        error_logs = await dashboard_service.get_error_logs(report_type=report_type, limit=limit)
        # Return the data wrapped in the response model structure
        return GenericResponse[ErrorLogResponse](data=ErrorLogResponse(errors=error_logs))
    except Exception as e:
        logger.error(f"Error fetching error logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve error logs.")

# --- Alert Configuration (Placeholder) --- 
# This is a complex feature requiring more definition.
# Example placeholder endpoint structure:

# @router.post(
#     "/alerts/config",
#     summary="Configure Alerting Rules",
#     description="Sets up rules for triggering alerts based on error logs or metrics.",
#     dependencies=[Depends(get_current_active_admin)] # Likely admin only
# )
# async def configure_alerts(
#     # Define Pydantic model for alert configuration payload
#     # alert_config: AlertConfigPayload = Body(...),
#     # dashboard_service: DashboardService = Depends(get_dashboard_service_dep)
# ):
#     logger.info("Received request to configure alerts.")
#     # TODO: Implement logic to store/update alert rules (e.g., in MongoDB or config)
#     # success = await dashboard_service.update_alert_config(alert_config)
#     # if not success:
#     #     raise HTTPException(status_code=500, detail="Failed to save alert configuration.")
#     return {"message": "Alert configuration endpoint not fully implemented."}

# @router.get(
#     "/alerts/config",
#     summary="Get Alerting Configuration",
#     description="Retrieves the current alerting rules.",
#     dependencies=[Depends(get_current_active_admin)] # Likely admin only
# )
# async def get_alert_config(
#     # dashboard_service: DashboardService = Depends(get_dashboard_service_dep)
# ):
#     logger.info("Received request to get alert configuration.")
#     # TODO: Implement logic to retrieve alert rules
#     # config = await dashboard_service.get_alert_config()
#     # return config
#     return {"message": "Get alert configuration endpoint not fully implemented."}
