"""Unified averages endpoint for all services."""

from fastapi import APIRouter, Depends, HTTPException
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency.metrics.averages import AllServicesAverageLatency, ServiceAverageLatency
from app.models.latency.metrics.percentiles import ServiceType, LatencyStatus
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AllServicesAverageLatency)
async def get_all_services_averages(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesAverageLatency:
  """
  Get average latency metrics for all services in a single response.

  Returns average latency for:
  - Quote generation service
  - Location lookup service  
  - HubSpot API
  - Bland.ai API
  - Google Maps API

  Also includes overall system average and summary statistics.
  """
  try:
    # Get averages for all services
    all_summaries = await dashboard_service.latency_service.calculator.get_all_latency_summaries()

    # Convert to the averages model format
    averages_data = AllServicesAverageLatency(
        quote=None,
        location=None,
        hubspot=None,
        bland=None,
        gmaps=None,
        overall_average_ms=None,
        overall_status=LatencyStatus.UNKNOWN,
        total_samples=0,
        services_with_data=0
    )
    all_averages = []
    total_samples = 0

    # Map each service summary to ServiceAverageLatency
    for service_type_str, summary in all_summaries.items():
      if summary and not summary.get("error") and summary.get("total_measurements", 0) > 0:
        try:
          service_type = ServiceType(service_type_str)
          average_ms = summary.get("mean_latency")
          sample_count = summary.get("total_measurements", 0)

          # Only process if we have valid average
          if average_ms is not None:
            # Determine status based on average
            status = _determine_average_status(average_ms)

            service_avg = ServiceAverageLatency(
                service_type=service_type,
                average_ms=average_ms,
                sample_count=sample_count,
                status=status,
                last_updated=datetime.now()
            )

            setattr(averages_data, service_type_str, service_avg)

            all_averages.extend([average_ms] * sample_count)
            total_samples += sample_count

        except ValueError:
          logger.warning(f"Unknown service type: {service_type_str}")
          continue

    # Calculate overall statistics
    if all_averages:
      averages_data.overall_average_ms = sum(all_averages) / len(all_averages)

    averages_data.overall_status = averages_data.get_worst_status()
    averages_data.services_with_data = len(
        [s for s in all_summaries.values() if s.get("total_measurements", 0) > 0])
    averages_data.total_samples = total_samples

    return averages_data

  except Exception as e:
    logger.error(f"Failed to get all services averages: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve average latency metrics")


def _determine_average_status(average_ms: float) -> LatencyStatus:
  """Determine status based on average latency."""
  if average_ms <= 100:  # Good: <= 100ms
    return LatencyStatus.GOOD
  elif average_ms <= 500:  # Warning: 100-500ms
    return LatencyStatus.WARNING
  else:  # Critical: > 500ms
    return LatencyStatus.CRITICAL
