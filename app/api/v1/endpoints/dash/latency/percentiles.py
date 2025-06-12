from fastapi import APIRouter, Depends, HTTPException
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency import AllServicesPercentiles
from app.models.latency.metrics.percentiles import LatencyStatus

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AllServicesPercentiles)
async def get_all_services_percentiles(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesPercentiles:
  """
  Get percentile metrics for all services in a single response.

  Returns P50, P90, P95, and P99 latency percentiles for:
  - Quote generation service
  - Location lookup service  
  - HubSpot API
  - Bland.ai API
  - Google Maps API

  Also includes overall system status and summary statistics.
  """
  try:
    # Get percentiles for all services
    all_summaries = await dashboard_service.latency_service.calculator.get_all_latency_summaries()

    # Convert to the new model format
    percentiles_data = AllServicesPercentiles(
        quote=None,
        location=None,
        hubspot=None,
        bland=None,
        gmaps=None,
        overall_status=LatencyStatus.UNKNOWN,
        total_samples=0,
        services_with_data=0
    )

    # Map each service summary to ServicePercentiles
    for service_type, summary in all_summaries.items():
      if summary and not summary.get("error"):
        service_percentiles = _convert_summary_to_percentiles(
            service_type, summary)
        setattr(percentiles_data, service_type, service_percentiles)

    # Calculate overall statistics
    percentiles_data.overall_status = percentiles_data.get_worst_status()
    percentiles_data.services_with_data = len(
        [s for s in all_summaries.values() if s.get("total_measurements", 0) > 0])
    percentiles_data.total_samples = sum(
        s.get("total_measurements", 0) for s in all_summaries.values())

    return percentiles_data

  except Exception as e:
    logger.error(f"Failed to get all services percentiles: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency percentiles")


def _convert_summary_to_percentiles(service_type: str, summary: dict):
  """Convert a service summary to ServicePercentiles model."""
  from app.models.latency import ServicePercentiles, ServiceType, LatencyStatus

  percentiles = summary.get("percentiles", {})

  return ServicePercentiles(
      service_type=ServiceType(service_type),
      p50=percentiles.get("p50.0"),
      p90=percentiles.get("p90.0"),
      p95=percentiles.get("p95.0"),
      p99=percentiles.get("p99.0"),
      sample_count=summary.get("total_measurements", 0),
      status=LatencyStatus(summary.get("status", "unknown")),
      last_updated=summary.get("timestamp")
  )
