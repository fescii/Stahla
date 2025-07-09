"""Unified spikes endpoint for all services."""

from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency.analysis.spikes import AllServicesSpikeAnalysis, ServiceSpikeAnalysis, LatencySpike
from app.models.latency.metrics.percentiles import ServiceType
from datetime import datetime
from typing import Any, Dict

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analysis", response_model=AllServicesSpikeAnalysis)
async def get_all_services_spikes(
    time_range_minutes: int = Query(
        60, ge=5, le=1440, description="Time range in minutes (5-1440)"),
    threshold_multiplier: float = Query(
        2.0, ge=1.5, le=10.0, description="Spike detection threshold multiplier"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesSpikeAnalysis:
  """
  Get latency spike analysis for all services in a single response.

  Analyzes spikes over the specified time range for:
  - Quote generation service
  - Location lookup service  
  - Google Maps API
  - Redis Cache

  Returns detected spikes, statistics, and overall system spike analysis.
  """
  try:
    # Get spike analysis for all services
    spikes_data = AllServicesSpikeAnalysis(
        quote=None,
        location=None,
        gmaps=None,
        redis=None,
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
    for service_type_str in ["quote", "location", "gmaps", "redis"]:
      try:
        service_type = ServiceType(service_type_str)

        # Get real spike analysis from analyzer
        spike_data = await dashboard_service.latency_service.analyzer.get_latency_spikes(
            service_type_str, threshold_multiplier, time_range_minutes
        )

        if spike_data:
          # Convert raw spike data to LatencySpike objects
          spikes = []
          max_spike_factor = None
          most_affected_endpoint = None

          for spike_entry in spike_data:
            # Parse timestamp safely
            timestamp = None
            if spike_entry.get("timestamp"):
              try:
                # Try parsing as ISO format first
                timestamp = datetime.fromisoformat(
                    spike_entry["timestamp"].replace('Z', '+00:00'))
              except (ValueError, AttributeError):
                # If that fails, try parsing as timestamp
                try:
                  timestamp = datetime.fromtimestamp(
                      float(spike_entry["timestamp"]))
                except (ValueError, TypeError):
                  timestamp = None

            spike = LatencySpike(
                service_type=service_type,
                stream_id=spike_entry["stream_id"],
                latency_ms=spike_entry["latency_ms"],
                request_id=spike_entry["request_id"],
                endpoint=spike_entry["endpoint"],
                spike_factor=spike_entry["spike_factor"],
                threshold_ms=spike_entry["threshold_ms"],
                average_ms=spike_entry["average_ms"],
                timestamp=timestamp,
                context={k: v for k, v in spike_entry.items()
                         if k.startswith("ctx_")}
            )
            spikes.append(spike)

            # Track maximum spike factor and most affected endpoint
            if max_spike_factor is None or spike_entry["spike_factor"] > max_spike_factor:
              max_spike_factor = spike_entry["spike_factor"]
              most_affected_endpoint = spike_entry["endpoint"]

          service_spike = ServiceSpikeAnalysis(
              service_type=service_type,
              time_range_minutes=time_range_minutes,
              threshold_multiplier=threshold_multiplier,
              spikes=spikes,
              spike_count=len(spikes),
              max_spike_factor=max_spike_factor,
              most_affected_endpoint=most_affected_endpoint,
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
        else:
          # No spike data found - create empty analysis
          service_spike = ServiceSpikeAnalysis(
              service_type=service_type,
              time_range_minutes=time_range_minutes,
              threshold_multiplier=threshold_multiplier,
              spikes=[],
              spike_count=0,
              max_spike_factor=None,
              most_affected_endpoint=None,
              analysis_timestamp=datetime.now()
          )
          setattr(spikes_data, service_type_str, service_spike)

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


@router.get("/summaries")
async def get_all_services_spike_summaries(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
  """
  Get simplified spike summaries for all services for the overview endpoint.
  Returns averaged spike data without threshold filtering for overview purposes.
  """
  try:
    logger.info("Getting spike summaries for all services")

    spike_summaries = {}

    # Analyze each service
    for service_type_str in ["quote", "location", "gmaps", "redis"]:
      try:
        service_type = ServiceType(service_type_str)

        # Get all spike data (no threshold filtering)
        all_spikes = await dashboard_service.latency_service.analyzer.get_latency_spikes(
            # Get all data with minimal threshold
            service_type_str, threshold_multiplier=1.0, minutes=0
        )

        if all_spikes:
          # Calculate summary statistics
          total_spikes = len(all_spikes)
          avg_spike_factor = sum(spike["spike_factor"]
                                 for spike in all_spikes) / total_spikes
          max_spike_factor = max(spike["spike_factor"] for spike in all_spikes)
          avg_latency = sum(spike["latency_ms"]
                            for spike in all_spikes) / total_spikes
          max_latency = max(spike["latency_ms"] for spike in all_spikes)

          # Get most affected endpoint
          endpoint_counts = {}
          for spike in all_spikes:
            endpoint = spike["endpoint"]
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1
          most_affected_endpoint = max(endpoint_counts.items(), key=lambda x: x[1])[
              0] if endpoint_counts else None

          spike_summaries[service_type_str] = {
              "service_type": service_type,
              "total_spikes": total_spikes,
              "avg_spike_factor": round(avg_spike_factor, 2),
              "max_spike_factor": round(max_spike_factor, 2),
              "avg_spike_latency_ms": round(avg_latency, 2),
              "max_spike_latency_ms": round(max_latency, 2),
              "most_affected_endpoint": most_affected_endpoint,
              "spike_frequency": endpoint_counts if endpoint_counts else {},
              "analysis_timestamp": datetime.now()
          }
        else:
          # No spikes found
          spike_summaries[service_type_str] = {
              "service_type": service_type,
              "total_spikes": 0,
              "avg_spike_factor": None,
              "max_spike_factor": None,
              "avg_spike_latency_ms": None,
              "max_spike_latency_ms": None,
              "most_affected_endpoint": None,
              "spike_frequency": {},
              "analysis_timestamp": datetime.now()
          }

      except ValueError:
        logger.warning(f"Unknown service type: {service_type_str}")
        continue
      except Exception as e:
        logger.error(
            f"Failed to analyze spike summary for {service_type_str}: {e}")
        continue

    # Calculate overall statistics
    services_with_spikes = [
        svc for svc, data in spike_summaries.items() if data["total_spikes"] > 0]
    total_spikes_across_services = sum(
        data["total_spikes"] for data in spike_summaries.values())

    worst_spike_service = None
    worst_spike_factor = None

    for service, data in spike_summaries.items():
      if data["max_spike_factor"] and (worst_spike_factor is None or data["max_spike_factor"] > worst_spike_factor):
        worst_spike_factor = data["max_spike_factor"]
        worst_spike_service = service

    return {
        **spike_summaries,
        "total_spikes_across_services": total_spikes_across_services,
        "services_with_spikes": services_with_spikes,
        "worst_spike_factor": worst_spike_factor,
        "worst_spike_service": worst_spike_service,
        "generated_at": datetime.now()
    }

  except Exception as e:
    logger.error(f"Failed to get spike summaries: {e}", exc_info=True)
    return {
        "quote": {"service_type": "quote", "total_spikes": 0},
        "location": {"service_type": "location", "total_spikes": 0},
        "gmaps": {"service_type": "gmaps", "total_spikes": 0},
        "redis": {"service_type": "redis", "total_spikes": 0},
        "total_spikes_across_services": 0,
        "services_with_spikes": [],
        "worst_spike_factor": None,
        "worst_spike_service": None,
        "generated_at": datetime.now()
    }
