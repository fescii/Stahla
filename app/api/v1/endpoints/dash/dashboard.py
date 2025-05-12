import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Response
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel  # Import BaseModel

# Import dashboard models and services
from app.models.dash.dashboard import (
    DashboardOverview,
    RequestLogEntry,
    CacheClearResult,
    CacheItem,
    CacheSearchResult,
    ClearCacheRequest,
    ClearPricingCacheRequest,
    ErrorLogEntry,
    ErrorLogResponse,
    SheetProductsResponse,
    SheetGeneratorsResponse,
    SheetBranchesResponse,
    SheetConfigResponse,  # Added Sheet data models
)
from app.models.dash.service_status import ServicesStatusResponse, ServiceStatus
from app.models.common import GenericResponse
from app.services.dash.dashboard import DashboardService  # Import service class

# Import the dependency injector from core
from app.core.dependencies import get_dashboard_service_dep
from app.core.security import get_current_user  # Import JWT dependency
from app.services.quote.sync import PRICING_CATALOG_CACHE_KEY  # Import cache key


# Simple model for message responses
class MessageResponse(BaseModel):
    message: str


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/overview",
    response_model=GenericResponse[DashboardOverview],  # Use GenericResponse
    summary="Get Dashboard Overview",
    description="Retrieves aggregated statistics and recent activity for the dashboard.",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint
)
async def get_dashboard_overview_endpoint(
    dashboard_service: DashboardService = Depends(
        get_dashboard_service_dep
    ),  # Use core dependency
):
    """API endpoint to fetch dashboard overview data."""
    logger.info("Received request for dashboard overview.")
    try:
        overview = await dashboard_service.get_dashboard_overview()
        return GenericResponse[DashboardOverview](data=overview)
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}", exc_info=True)
        # Let FastAPI handle the exception for 500 error
        raise HTTPException(
            status_code=500, detail="Failed to retrieve dashboard data."
        )


@router.get(
    "/requests/recent",
    response_model=GenericResponse[List[RequestLogEntry]],  # Use GenericResponse
    summary="Get Recent Request Logs",
    description="Retrieves a list of recent logged requests from MongoDB.",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint
)
async def get_recent_requests_endpoint(
    limit: int = 20,  # Default limit
    report_type: Optional[str] = Query(
        None,
        description="Filter logs by report_type (e.g., 'QuoteRequest', 'QuoteResponse')",
    ),
    dashboard_service: DashboardService = Depends(
        get_dashboard_service_dep
    ),  # Use core dependency
):
    """API endpoint to fetch recent request logs from MongoDB."""
    logger.info(
        f"Received request for recent requests. Type: {report_type}, Limit: {limit}"
    )
    try:
        # Fetch request logs from MongoDB using dashboard_service.mongo
        raw_reports = await dashboard_service.mongo.get_recent_reports(
            report_type=report_type, limit=limit
        )

        # Parse the raw reports into RequestLogEntry objects
        request_logs = []
        for report in raw_reports:
            try:
                # Convert MongoDB ObjectId to string if not already done
                if "_id" in report:
                    report["_id"] = str(report["_id"])

                # Map MongoDB report fields to RequestLogEntry fields
                request_log_entry = RequestLogEntry(
                    timestamp=report.get("timestamp", datetime.now()),
                    request_id=str(report.get("_id")),
                    endpoint=report.get(
                        "endpoint", report.get("report_type", "unknown")
                    ),
                    request_payload=report.get("request_data"),
                    response_payload=report.get("response_data"),
                    status_code=report.get("status_code"),
                    latency_ms=report.get("latency_ms"),
                )
                request_logs.append(request_log_entry)
            except Exception as parse_error:
                logger.warning(
                    f"Failed to parse MongoDB report into RequestLogEntry: {report}. Error: {parse_error}"
                )

        logger.info(f"Retrieved {len(request_logs)} request logs from MongoDB")
        return GenericResponse[List[RequestLogEntry]](
            data=request_logs
        )  # Wrap response
    except Exception as e:
        logger.error(f"Error fetching recent requests: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve recent request data."
        )


@router.post(
    "/sync/trigger",
    response_model=GenericResponse[MessageResponse],  # Use GenericResponse
    summary="Trigger Manual Sheet Sync",
    description="Manually triggers an immediate synchronization of pricing, config, and branches from Google Sheets.",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint (or use admin)
)
async def trigger_manual_sync(
    dashboard_service: DashboardService = Depends(
        get_dashboard_service_dep
    ),  # Use core dependency
):
    """Endpoint to manually trigger a Google Sheet sync."""
    # Add permission check if needed: if not current_user.is_admin: ...
    logger.info(f"User requested manual sheet sync trigger.")
    try:
        logger.info("Calling dashboard_service.trigger_sheet_sync()")
        success = await dashboard_service.trigger_sheet_sync()
        logger.info(f"dashboard_service.trigger_sheet_sync() returned: {success}")
        if not success:
            logger.error("trigger_sheet_sync returned False. Raising HTTPException.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to trigger sync. Check logs.",
            )
        logger.info("Manual sync trigger successful.")
        return GenericResponse[MessageResponse](
            data=MessageResponse(message="Manual sync triggered successfully.")
        )  # Wrap response
    except HTTPException as http_exc:
        logger.error(
            f"HTTPException during manual sync trigger: {http_exc.detail}",
            exc_info=True,
        )
        raise  # Re-raise the HTTPException
    except Exception as e:
        logger.error(f"Unexpected error during manual sync trigger: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during sync trigger.",
        )


@router.get(
    "/cache/search",
    response_model=GenericResponse[List[CacheSearchResult]],  # Use GenericResponse
    summary="Search Cache Keys",
    description="Searches for Redis cache keys matching a glob pattern (e.g., 'maps:distance:*', 'pricing:*'). Limited results.",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint
)
async def search_cache_keys(
    pattern: str = Query(
        ...,
        description="Glob pattern to search keys (e.g., 'maps:distance:*:*123main*')",
    ),
    dashboard_service: DashboardService = Depends(
        get_dashboard_service_dep
    ),  # Use core dependency
):
    """Endpoint to search cache keys."""
    logger.info(f"Searching cache keys with pattern: {pattern}")
    results = await dashboard_service.search_cache_keys(pattern)
    return GenericResponse[List[CacheSearchResult]](data=results)  # Wrap response


@router.get(
    "/cache/item",
    response_model=GenericResponse[CacheItem],  # Use GenericResponse
    summary="View Specific Cache Item",
    description="Retrieves the value and TTL of a specific Redis cache key.",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint
)
async def view_cache_item(
    key: str = Query(..., description="The exact cache key to view."),
    dashboard_service: DashboardService = Depends(
        get_dashboard_service_dep
    ),  # Use core dependency
):
    """Endpoint to view a specific cached item."""
    logger.info(f"Requested cache key view: {key}")
    try:
        cache_data = await dashboard_service.get_cache_item(key)
        if cache_data is None:
            error_message = f"Cache key '{key}' not found."
            logger.info(error_message)  # Log as info, as it's a standard case
            return GenericResponse[CacheItem](
                success=False,
                data=None,  # Or a default CacheItem if preferred for typing, but None is fine for data
                error_message=error_message,
                error_details=f"The cache key '{key}' does not exist or has expired.",
            )
        return GenericResponse[CacheItem](data=cache_data)
    except Exception as e:
        error_message = f"Error retrieving cache key '{key}'."
        logger.error(f"{error_message} Error: {e}", exc_info=True)
        return GenericResponse[CacheItem](
            success=False, data=None, error_message=error_message, error_details=str(e)
        )


@router.post(
    "/cache/clear/item",
    response_model=GenericResponse[MessageResponse],  # Changed
    status_code=status.HTTP_200_OK,  # Changed
    summary="Clear Specific Cache Item",
    description="Manually clears a specific cache key from Redis. Returns success status.",
    dependencies=[Depends(get_current_user)],
)
async def clear_cache_item(
    payload: ClearCacheRequest = Body(...),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    """Endpoint to manually clear a specific cache key."""
    logger.info(f"Requested cache clear for key: {payload.key}")
    try:
        cleared_successfully = await dashboard_service.clear_cache_item(payload.key)
        if cleared_successfully:
            message = f"Cache key '{payload.key}' cleared successfully."
            logger.info(message)
            return GenericResponse[MessageResponse](
                data=MessageResponse(message=message)
            )
        else:
            message = f"Cache key '{payload.key}' not found or already expired."
            logger.warning(message)
            return GenericResponse[MessageResponse](
                success=False,
                data=MessageResponse(message=message),
                error_message=message,
            )
    except Exception as e:
        error_message = f"Failed to clear cache key {payload.key}."
        logger.error(f"{error_message} Error: {e}", exc_info=True)
        # It's better to let the global exception handler deal with 500s,
        # but if we want to ensure GenericResponse for all paths from this endpoint:
        return GenericResponse[MessageResponse](
            success=False,
            data=MessageResponse(message=error_message),
            error_message=error_message,
            error_details=str(e),
        )


@router.post(
    "/cache/clear/pricing",
    response_model=GenericResponse[MessageResponse],  # Changed
    status_code=status.HTTP_200_OK,  # Changed
    summary="Clear Pricing Catalog Cache",
    description="Manually clears the entire pricing catalog cache. Returns success status.",
    dependencies=[Depends(get_current_user)],
)
async def clear_pricing_cache(
    payload: ClearPricingCacheRequest = Body(...),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    """Endpoint to clear the pricing catalog cache."""
    if not payload.confirm:
        # This remains an HTTPException as it's a client validation error
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation flag must be set to true.",
        )

    logger.warning(
        f"Requested CLEARING ENTIRE PRICING CACHE for key '{PRICING_CATALOG_CACHE_KEY}'."
    )
    try:
        cleared_successfully = await dashboard_service.clear_pricing_catalog_cache()
        if cleared_successfully:
            message = f"Pricing catalog cache ('{PRICING_CATALOG_CACHE_KEY}') cleared successfully."
            logger.info(message)
            return GenericResponse[MessageResponse](
                data=MessageResponse(message=message)
            )
        else:
            message = f"Pricing catalog cache ('{PRICING_CATALOG_CACHE_KEY}') was not found (already clear)."
            logger.info(
                message
            )  # Log as info, as this is an expected state for a "clear" operation
            return GenericResponse[MessageResponse](
                data=MessageResponse(message=message)
            )
    except Exception as e:
        error_message = (
            f"Failed to clear pricing catalog cache ('{PRICING_CATALOG_CACHE_KEY}')."
        )
        logger.error(f"{error_message} Error: {e}", exc_info=True)
        return GenericResponse[MessageResponse](
            success=False,
            data=MessageResponse(message=error_message),
            error_message=error_message,
            error_details=str(e),
        )


@router.post(
    "/cache/clear/maps",
    response_model=GenericResponse[MessageResponse],  # Use GenericResponse
    summary="Clear Maps Location Cache",
    description="Clears Google Maps distance cache keys matching a location pattern (use carefully).",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint (or use admin)
)
async def clear_maps_cache(
    location_pattern: str = Body(
        ...,
        embed=True,
        description="Pattern to match in the delivery location part of the cache key (e.g., '*123mainst*'). Use '*' as wildcard.",
    ),
    dashboard_service: DashboardService = Depends(
        get_dashboard_service_dep
    ),  # Use core dependency
):
    """Endpoint to clear maps cache keys by location pattern."""
    # Add permission check if needed
    logger.warning(f"Requested clearing maps cache with pattern: {location_pattern}")
    if not location_pattern or len(location_pattern) < 3:  # Basic safety check
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location pattern must be provided and at least 3 characters.",
        )
    deleted_count = await dashboard_service.clear_maps_location_cache(
        f"*{location_pattern}*"
    )  # Add wildcards for broader match
    # Wrap response
    return GenericResponse[MessageResponse](
        data=MessageResponse(
            message=f"Cleared {deleted_count} maps cache keys matching pattern '*{location_pattern}*."
        )
    )


@router.get(
    "/errors",
    response_model=GenericResponse[
        ErrorLogResponse
    ],  # Use GenericResponse wrapping ErrorLogResponse
    summary="Get Recent Error Logs",
    description="Retrieves recent error logs recorded in the database, optionally filtered by type.",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint
)
async def get_error_logs_endpoint(
    report_type: Optional[str] = Query(
        None,
        description="Filter logs by report_type (e.g., 'SheetFetchError_products', 'ValueError')",
    ),
    limit: int = Query(
        50, ge=1, le=200, description="Maximum number of error logs to return."
    ),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    """API endpoint to fetch recent error logs."""
    logger.info(f"Received request for error logs. Type: {report_type}, Limit: {limit}")
    try:
        error_logs = await dashboard_service.get_error_logs(
            report_type=report_type, limit=limit
        )
        # Return the data wrapped in the response model structure
        return GenericResponse[ErrorLogResponse](
            data=ErrorLogResponse(errors=error_logs)
        )
    except Exception as e:
        logger.error(f"Error fetching error logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve error logs.")


# --- Sheet Data Endpoints ---


@router.get(
    "/sheet/products",
    response_model=GenericResponse[SheetProductsResponse],
    summary="Get Synced Products from Sheet",
    description="Retrieves all product data synced from Google Sheets and stored in MongoDB.",
    dependencies=[Depends(get_current_user)],
)
async def get_sheet_products(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    logger.info("Request to fetch synced products from MongoDB.")
    try:
        products_data = await dashboard_service.get_sheet_products_data()
        return GenericResponse[SheetProductsResponse](data=products_data)
    except Exception as e:
        logger.error(f"Error fetching sheet products data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve synced products data."
        )


@router.get(
    "/sheet/generators",
    response_model=GenericResponse[SheetGeneratorsResponse],
    summary="Get Synced Generators from Sheet",
    description="Retrieves all generator data synced from Google Sheets and stored in MongoDB.",
    dependencies=[Depends(get_current_user)],
)
async def get_sheet_generators(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    logger.info("Request to fetch synced generators from MongoDB.")
    try:
        generators_data = await dashboard_service.get_sheet_generators_data()
        return GenericResponse[SheetGeneratorsResponse](data=generators_data)
    except Exception as e:
        logger.error(f"Error fetching sheet generators data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve synced generators data."
        )


@router.get(
    "/sheet/branches",
    response_model=GenericResponse[SheetBranchesResponse],
    summary="Get Synced Branches from Sheet",
    description="Retrieves all branch data synced from Google Sheets and stored in MongoDB.",
    dependencies=[Depends(get_current_user)],
)
async def get_sheet_branches(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    logger.info("Request to fetch synced branches from MongoDB.")
    try:
        branches_data = await dashboard_service.get_sheet_branches_data()
        return GenericResponse[SheetBranchesResponse](data=branches_data)
    except Exception as e:
        logger.error(f"Error fetching sheet branches data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve synced branches data."
        )


@router.get(
    "/sheet/config",
    response_model=GenericResponse[SheetConfigResponse],
    summary="Get Synced Configuration from Sheet",
    description="Retrieves the main configuration data (delivery, seasonal multipliers) synced from Google Sheets and stored in MongoDB.",
    dependencies=[Depends(get_current_user)],
)
async def get_sheet_config(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    logger.info("Request to fetch synced configuration from MongoDB.")
    try:
        config_data = await dashboard_service.get_sheet_config_data()
        return GenericResponse[SheetConfigResponse](data=config_data)
    except Exception as e:
        logger.error(f"Error fetching sheet configuration data: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve synced configuration data."
        )


@router.get(
    "/services/status",
    response_model=GenericResponse[ServicesStatusResponse],
    summary="Get External Services Status",
    description="Retrieves the current status of all external services (MongoDB, Redis, BlandAI, HubSpot, etc.).",
    dependencies=[Depends(get_current_user)],  # Secure this endpoint
)
async def get_services_status_endpoint(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
):
    """API endpoint to fetch the status of all external services."""
    logger.info("Received request for external services status.")
    try:
        # Get service statuses from MongoDB (collected by background monitor)
        raw_statuses = await dashboard_service.get_service_statuses()

        # Convert raw MongoDB documents to ServiceStatus models
        services = []
        latest_timestamp = None

        for raw_status in raw_statuses:
            try:
                # Ensure details is always a dictionary (never None or another type)
                details = raw_status.get("details", {})
                if details is None or not isinstance(details, dict):
                    details = {}

                status_obj = ServiceStatus(
                    service_name=raw_status.get("service_name", "unknown"),
                    status=raw_status.get("status", "unknown"),
                    message=raw_status.get("message", ""),
                    timestamp=raw_status.get("timestamp", datetime.now()),
                    details=details,
                )
                services.append(status_obj)

                # Keep track of the latest timestamp
                if latest_timestamp is None or (
                    status_obj.timestamp and status_obj.timestamp > latest_timestamp
                ):
                    latest_timestamp = status_obj.timestamp

            except Exception as parse_error:
                logger.warning(
                    f"Failed to parse service status: {raw_status}. Error: {parse_error}"
                )

        # Create the response object
        response_data = ServicesStatusResponse(
            services=services, last_updated=latest_timestamp
        )

        logger.info(f"Retrieved status for {len(services)} external services")
        return GenericResponse[ServicesStatusResponse](data=response_data)

    except Exception as e:
        logger.error(f"Error fetching service statuses: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve external services status."
        )
