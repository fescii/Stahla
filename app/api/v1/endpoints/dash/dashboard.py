import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Response
from typing import List

# Import dashboard models and services
from app.models.dash.dashboard import (
    DashboardOverview, CacheItem, CacheSearchResult, RequestLogEntry,
    ClearCacheRequest, ClearPricingCacheRequest
)
from app.services.dash.dashboard import DashboardService, get_dashboard_service
from app.core.security import get_current_user # Import JWT dependency
from app.services.quote.sync import PRICING_CATALOG_CACHE_KEY # Import cache key

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get(
    "/overview", 
    response_model=DashboardOverview,
    summary="Get Dashboard Overview",
    description="Retrieves aggregated statistics and recent activity for the dashboard.",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def get_dashboard_overview_endpoint(
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """API endpoint to fetch dashboard overview data."""
    logger.info("Received request for dashboard overview.")
    try:
        overview = await dashboard_service.get_dashboard_overview()
        return overview
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve dashboard data.")

@router.get(
    "/recent-requests", 
    response_model=List[RequestLogEntry], # Assuming RequestLogEntry model exists
    summary="Get Recent Request Logs",
    description="Retrieves a list of recent logged requests (currently placeholder).",
    dependencies=[Depends(get_current_user)] # Secure this endpoint
)
async def get_recent_requests_endpoint(
    limit: int = 20, # Default limit
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """API endpoint to fetch recent request logs."""
    logger.info(f"Received request for recent requests (limit: {limit}).")
    try:
        # TODO: Replace with MongoDB fetch using dashboard_service.mongo.get_recent_reports
        # Example: requests = await dashboard_service.mongo.get_recent_reports(report_type="some_request_type", limit=limit)
        requests = [] # Placeholder - returning empty as Redis method was removed
        logger.warning("Returning empty list for /recent-requests as MongoDB fetch is not implemented here yet.")
        return requests
    except Exception as e:
        logger.error(f"Error fetching recent requests: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve recent request data.")

@router.post(
    "/sync/trigger",
    summary="Trigger Manual Sheet Sync",
    description="Manually triggers an immediate synchronization of pricing, config, and branches from Google Sheets."
)
async def trigger_manual_sync(
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """Endpoint to manually trigger a Google Sheet sync."""
    # Add permission check if needed: if not current_user.is_admin: ...
    logger.info(f"User requested manual sheet sync trigger.")
    success = await dashboard_service.trigger_sheet_sync()
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trigger sync. Check logs.")
    return {"message": "Manual sync triggered successfully."}

@router.get(
    "/cache/search",
    response_model=List[CacheSearchResult],
    summary="Search Cache Keys",
    description="Searches for Redis cache keys matching a glob pattern (e.g., 'maps:distance:*', 'pricing:*'). Limited results."
)
async def search_cache_keys(
    pattern: str = Query(..., description="Glob pattern to search keys (e.g., 'maps:distance:*:*123main*')"),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """Endpoint to search cache keys."""
    logger.info(f"Searching cache keys with pattern: {pattern}")
    results = await dashboard_service.search_cache_keys(pattern)
    return results


@router.get(
    "/cache/item",
    response_model=CacheItem,
    summary="View Specific Cache Item",
    description="Retrieves the value and TTL of a specific Redis cache key."
)
async def view_cache_item(
    key: str = Query(..., description="The exact cache key to view."),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """Endpoint to view a specific cached item."""
    logger.info(f"Requested cache key view: {key}")
    cache_data = await dashboard_service.get_cache_item(key)
    if cache_data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cache key not found")
    return cache_data

@router.post(
    "/cache/clear/item",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Specific Cache Item",
    description="Manually clears a specific cache key from Redis."
)
async def clear_cache_item(
    payload: ClearCacheRequest = Body(...), # Use request body
    dashboard_service: DashboardService = Depends(get_dashboard_service)
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
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cache/clear/pricing",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Pricing Catalog Cache",
    description="Manually clears the entire pricing catalog cache, forcing a refresh on the next sync."
)
async def clear_pricing_cache(
    payload: ClearPricingCacheRequest = Body(...), # Use request body for confirmation
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """Endpoint to clear the pricing catalog cache."""
    if not payload.confirm:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation flag must be set to true.")
    # Add permission check if needed
    logger.warning(f"Requested CLEARING ENTIRE PRICING CACHE.")
    success = await dashboard_service.clear_pricing_catalog_cache()
    # Log even if key didn't exist
    logger.info(f"Pricing cache clear operation completed for key '{PRICING_CATALOG_CACHE_KEY}'. Success: {success}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/cache/clear/maps",
    summary="Clear Maps Location Cache",
    description="Clears Google Maps distance cache keys matching a location pattern (use carefully)."
)
async def clear_maps_cache(
    location_pattern: str = Body(..., embed=True, description="Pattern to match in the delivery location part of the cache key (e.g., '*123mainst*'). Use '*' as wildcard."),
    dashboard_service: DashboardService = Depends(get_dashboard_service)
):
    """Endpoint to clear maps cache keys by location pattern."""
    # Add permission check if needed
    logger.warning(f"Requested clearing maps cache with pattern: {location_pattern}")
    if not location_pattern or len(location_pattern) < 3: # Basic safety check
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Location pattern must be provided and at least 3 characters.")
    deleted_count = await dashboard_service.clear_maps_location_cache(f"*{location_pattern}*") # Add wildcards for broader match
    return {"message": f"Cleared {deleted_count} maps cache keys matching pattern '*{location_pattern}*'."}


# TODO: Add endpoints for error log viewing/filtering if needed
# TODO: Add endpoints for alert configuration if implementing that feature
