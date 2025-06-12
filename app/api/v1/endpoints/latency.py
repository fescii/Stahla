"""
Main latency router that aggregates all latency-related endpoints.
This router is registered separately from the dashboard for better organization.
"""

from fastapi import APIRouter
from .dash.latency import (
    metrics_router,
    percentiles_router,
    averages_router,
    alerts_router,
    trends_router,
    spikes_router,
    overview_router
)

# Create the main latency router
router = APIRouter()

# Include all latency sub-routers without the /latency prefix since this router will be mounted at /latency
router.include_router(metrics_router, tags=["Latency Metrics"])
router.include_router(percentiles_router,
                      prefix="/percentiles", tags=["Latency Percentiles"])
router.include_router(averages_router, prefix="/averages",
                      tags=["Latency Averages"])
router.include_router(alerts_router, prefix="/alerts", tags=["Latency Alerts"])
router.include_router(trends_router, prefix="/trends", tags=["Latency Trends"])
router.include_router(spikes_router, prefix="/spikes", tags=["Latency Spikes"])
router.include_router(overview_router, prefix="/overview",
                      tags=["Latency Overview"])
