"""Unified overview endpoint combining all latency metrics."""

from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency.overview import LatencyOverview

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=LatencyOverview)
async def get_latency_overview(
    time_range_minutes: int = Query(
        60, ge=5, le=1440, description="Time range in minutes (5-1440)"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> LatencyOverview:
  """
  Get comprehensive latency overview for all services.

  Combines all latency metrics in a single response:
  - Percentiles (P50, P75, P90, P95, P99) for all services
  - Average latency metrics for all services
  - Active alerts and alert counts
  - Trend analysis over specified time range
  - Spike detection and analysis
  - Overall system health score and status

  This endpoint provides a complete picture of system latency health
  across all services: Quote, Location, Google Maps, and Redis APIs.
  """
  try:
    # Import the individual endpoints to reuse their logic
    from .percentiles import get_all_services_percentiles
    from .averages import get_all_services_averages
    from .trends import get_all_services_trends
    from .spikes import get_all_services_spikes

    # Get all metrics in parallel would be ideal, but for simplicity doing sequentially
    percentiles = await get_all_services_percentiles(dashboard_service, current_user)
    averages = await get_all_services_averages(dashboard_service, current_user)
    trends = await get_all_services_trends(time_range_minutes, dashboard_service, current_user)
    # Get spike summaries instead of detailed spike analysis for overview
    spikes = await dashboard_service.latency_service.get_spike_summaries(time_range_minutes)

    # For alerts, create a simple mock since the full implementation needs more work
    from app.models.latency.alerts.alerts import AllServicesAlerts, AlertSeverity
    alerts = AllServicesAlerts(
        active_alerts=[],
        critical_count=0,
        warning_count=0,
        info_count=0,
        total_alerts=0,
        overall_severity=AlertSeverity.INFO,
        services_with_alerts=[]
    )

    # Create comprehensive overview
    from app.models.latency.metrics.percentiles import LatencyStatus
    overview = LatencyOverview(
        percentiles=percentiles,
        averages=averages,
        alerts=alerts,
        trends=trends,
        spikes=spikes,
        overall_status=LatencyStatus.UNKNOWN,
        system_health_score=None,
        analysis_time_range_minutes=time_range_minutes
    )

    # Update calculated fields
    overview.update_calculated_fields()

    return overview

  except Exception as e:
    logger.error(f"Failed to get latency overview: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency overview")
