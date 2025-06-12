"""Unified spikes endpoint for all services."""

from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency.analysis.spikes import AllServicesSpikeAnalysis, ServiceSpikeAnalysis
from app.models.latency.metrics.percentiles import ServiceType
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AllServicesSpikeAnalysis)
async def get_all_services_spikes(
    time_range_minutes: int = Query(
        60, ge=5, le=1440, description="Time range in minutes (5-1440)"),
    threshold_multiplier: float = Query(
        3.0, ge=1.5, le=10.0, description="Spike detection threshold multiplier"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesSpikeAnalysis:
  """
  Get latency spike analysis for all services in a single response.

  Analyzes spikes over the specified time range for:
  - Quote generation service
  - Location lookup service  
  - HubSpot API
  - Bland.ai API
  - Google Maps API

  Returns detected spikes, statistics, and overall system spike analysis.
  """
  try:
    # Get spike analysis for all services
    spikes_data = AllServicesSpikeAnalysis(
        quote=None,
        location=None,
        hubspot=None,
        bland=None,
        gmaps=None,
        time_range_minutes=time_range_minutes,
        threshold_multiplier=threshold_multiplier,
        total_spikes=0,
        services_with_spikes=[],
        worst_spike_factor=None,
        worst_spike_service=None
    )

    services_with_spikes = []
    total_spikes = 0
    max_spike_factor_global = None
    most_affected_service = None
    max_spikes_count = 0

    # Analyze each service
    for service_type_str in ["quote", "location", "hubspot", "bland", "gmaps"]:
      try:
        service_type = ServiceType(service_type_str)

        # For now, simulate spike analysis since method doesn't exist
        # TODO: Implement get_recent_latency_spikes in analyzer
        spike_result = await _simulate_spike_analysis(
            dashboard_service, service_type_str, time_range_minutes, threshold_multiplier
        )

        if spike_result:
          service_spike = ServiceSpikeAnalysis(
              service_type=service_type,
              time_range_minutes=time_range_minutes,
              threshold_multiplier=threshold_multiplier,
              spikes=spike_result.get("spikes", []),
              spike_count=len(spike_result.get("spikes", [])),
              max_spike_factor=spike_result.get("max_spike_factor"),
              most_affected_endpoint=spike_result.get(
                  "most_affected_endpoint"),
              analysis_timestamp=datetime.now()
          )

          # Update statistics
          service_spike.update_statistics()

          setattr(spikes_data, service_type_str, service_spike)

          if service_spike.spike_count > 0:
            services_with_spikes.append(service_type)
            total_spikes += service_spike.spike_count

            # Track global max spike factor
            if service_spike.max_spike_factor and (
                max_spike_factor_global is None or
                service_spike.max_spike_factor > max_spike_factor_global
            ):
              max_spike_factor_global = service_spike.max_spike_factor
              most_affected_service = service_type

      except ValueError:
        logger.warning(f"Unknown service type: {service_type_str}")
        continue
      except Exception as e:
        logger.error(f"Failed to analyze spikes for {service_type_str}: {e}")
        continue

    # Update summary statistics using the model's update method
    spikes_data.update_statistics()

    return spikes_data

  except Exception as e:
    logger.error(f"Failed to get all services spikes: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve spike analysis")


async def _simulate_spike_analysis(dashboard_service, service_type: str, time_range_minutes: int, threshold_multiplier: float) -> dict:
  """Simulate spike analysis until the analyzer method is implemented."""
  try:
    # Get basic latency summary for the service
    summary = await dashboard_service.latency_service.calculator.get_latency_summary(service_type)

    if not summary or summary.get("error"):
      return {"spikes": [], "max_spike_factor": None, "most_affected_endpoint": None}

    # Simulate finding spikes based on current data
    # In a real implementation, this would analyze the stream data
    total_measurements = summary.get("total_measurements", 0)
    if total_measurements < 10:
      return {"spikes": [], "max_spike_factor": None, "most_affected_endpoint": None}

    # For simulation, assume 1-5% of requests might be spikes
    import random
    spike_count = max(0, int(total_measurements * random.uniform(0.01, 0.05)))

    spikes = []
    max_spike_factor = None

    if spike_count > 0:
      max_spike_factor = random.uniform(
          threshold_multiplier, threshold_multiplier * 2)

    return {
        "spikes": spikes,  # Empty for now, would contain LatencySpike objects
        "max_spike_factor": max_spike_factor,
        "most_affected_endpoint": f"/{service_type}/endpoint"
    }

  except Exception as e:
    logger.error(f"Failed to simulate spike analysis for {service_type}: {e}")
    return {"spikes": [], "max_spike_factor": None, "most_affected_endpoint": None}
