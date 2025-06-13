import logging
from typing import Dict, List, Optional, Any

from app.services.redis.service import RedisService
from app.services.dash.latency.tracking import LatencyRecorder
from app.services.dash.latency.metrics import LatencyCalculator
from app.services.dash.latency.analysis import LatencyAnalyzer

logger = logging.getLogger(__name__)


class LatencyService:
  """
  Comprehensive latency tracking and analysis service.
  Provides a unified interface for recording, calculating, and analyzing latency data.
  """

  def __init__(self, redis_service: RedisService):
    self.redis = redis_service
    self.recorder = LatencyRecorder(redis_service)
    self.calculator = LatencyCalculator(redis_service)
    self.analyzer = LatencyAnalyzer(redis_service)

  # --- Recording Methods ---

  async def record_quote_latency(
      self,
      latency_ms: float,
      request_id: Optional[str] = None,
      quote_type: Optional[str] = None,
      location: Optional[str] = None
  ) -> bool:
    """Record latency for quote generation operations."""
    return await self.recorder.record_quote_latency(
        latency_ms, request_id, quote_type, location
    )

  async def record_location_latency(
      self,
      latency_ms: float,
      request_id: Optional[str] = None,
      lookup_type: Optional[str] = None,
      address: Optional[str] = None
  ) -> bool:
    """Record latency for location lookup operations."""
    return await self.recorder.record_location_latency(
        latency_ms, request_id, lookup_type, address
    )

  async def record_external_api_latency(
      self,
      service_type: str,  # 'quote', 'location', 'gmaps', 'redis'
      latency_ms: float,
      request_id: Optional[str] = None,
      api_endpoint: Optional[str] = None,
      response_status: Optional[int] = None
  ) -> bool:
    """Record latency for external API calls."""
    return await self.recorder.record_external_api_latency(
        service_type, latency_ms, request_id, api_endpoint, response_status
    )

  # --- Metrics Methods ---

  async def get_service_percentiles(
      self,
      service_type: str,
      percentiles: List[float] = [50.0, 90.0, 95.0, 99.0]
  ) -> Dict[str, Optional[float]]:
    """Get latency percentiles for a service."""
    return await self.calculator.get_percentiles(service_type, percentiles)

  async def get_service_average(self, service_type: str) -> Optional[float]:
    """Get average latency for a service."""
    return await self.calculator.get_average_latency(service_type)

  async def get_service_summary(self, service_type: str) -> Dict[str, Any]:
    """Get comprehensive latency summary for a service."""
    return await self.calculator.get_latency_summary(service_type)

  async def get_all_summaries(self) -> Dict[str, Dict[str, Any]]:
    """Get latency summaries for all tracked services."""
    return await self.calculator.get_all_latency_summaries()

  async def check_alerts(self) -> List[Dict[str, Any]]:
    """Check for latency alerts across all services."""
    return await self.calculator.check_latency_alerts()

  # --- Analysis Methods ---

  async def get_latency_trend(
      self,
      service_type: str,
      minutes: int = 60
  ) -> Dict[str, Any]:
    """Analyze latency trends over time."""
    return await self.analyzer.get_recent_latency_trend(service_type, minutes)

  async def get_latency_spikes(
      self,
      service_type: str,
      threshold_multiplier: float = 3.0,
      minutes: int = 60
  ) -> List[Dict[str, Any]]:
    """Identify latency spikes."""
    return await self.analyzer.get_latency_spikes(
        service_type, threshold_multiplier, minutes
    )

  async def get_endpoint_breakdown(
      self,
      service_type: str,
      minutes: int = 60
  ) -> Dict[str, Dict[str, Any]]:
    """Get latency breakdown by endpoint."""
    return await self.analyzer.get_endpoint_latency_breakdown(service_type, minutes)

  # --- Dashboard/Overview Methods ---

  async def get_dashboard_overview(self) -> Dict[str, Any]:
    """Get a comprehensive latency overview for the dashboard."""
    try:
      # Get summaries for all services
      all_summaries = await self.get_all_summaries()

      # Get alerts
      alerts = await self.check_alerts()

      # Calculate overall status
      overall_status = "good"
      critical_services = []
      warning_services = []

      for service_type, summary in all_summaries.items():
        if summary.get("status") == "critical":
          overall_status = "critical"
          critical_services.append(service_type)
        elif summary.get("status") == "warning" and overall_status != "critical":
          overall_status = "warning"
          warning_services.append(service_type)

      # Get trends for key services
      quote_trend = await self.get_latency_trend("quote", 30)
      location_trend = await self.get_latency_trend("location", 30)

      return {
          "overall_status": overall_status,
          "critical_services": critical_services,
          "warning_services": warning_services,
          "service_summaries": all_summaries,
          "active_alerts": alerts,
          "recent_trends": {
              "quote": quote_trend,
              "location": location_trend,
          },
          "total_services_tracked": len(all_summaries),
          "services_with_data": len([s for s in all_summaries.values() if s.get("total_measurements", 0) > 0]),
          "generated_at": all_summaries.get("quote", {}).get("timestamp"),
      }

    except Exception as e:
      logger.error(
          f"Failed to generate latency dashboard overview: {e}", exc_info=True)
      return {
          "overall_status": "error",
          "error": str(e),
          "generated_at": None,
      }

  # --- Spike Analysis Methods ---

  async def get_spike_summaries(self, time_range_minutes: int = 60):
    """
    Get averaged spike summaries for all services without individual spike details.
    Uses a low threshold (1.0) to capture all potential spikes.
    Returns simplified AllServicesSpikeAnalysis with summary data only.
    """
    try:
      from app.models.latency.analysis.spikes import AllServicesSpikeAnalysis, ServiceSpikeAnalysis
      from app.models.latency.metrics.percentiles import ServiceType
      from datetime import datetime

      services = ["quote", "location", "gmaps", "redis"]
      total_spikes = 0
      services_with_spikes = []
      worst_spike_factor = None
      worst_spike_service = None

      # Create the main analysis object with default values
      spike_analysis = AllServicesSpikeAnalysis(
          quote=None,
          location=None,
          gmaps=None,
          redis=None,
          time_range_minutes=time_range_minutes,
          threshold_multiplier=1.0,
          total_spikes=0,
          services_with_spikes=[],
          worst_spike_factor=None,
          worst_spike_service=None
      )
      spike_analysis.total_spikes = 0
      spike_analysis.services_with_spikes = []
      spike_analysis.worst_spike_factor = None
      spike_analysis.worst_spike_service = None
      spike_analysis.generated_at = datetime.now()

      for service_type_str in services:
        try:
          service_type = ServiceType(service_type_str)

          # Use low threshold to capture all potential spikes
          spikes = await self.analyzer.get_latency_spikes(
              service_type=service_type_str,
              threshold_multiplier=1.0,
              minutes=time_range_minutes
          )

          if spikes:
            spike_count = len(spikes)
            max_spike_factor = max(spike["spike_factor"] for spike in spikes)
            avg_latency = sum(spike["latency_ms"]
                              for spike in spikes) / spike_count

            # Count affected endpoints
            endpoints = set(spike["endpoint"] for spike in spikes)
            most_affected_endpoint = max(
                endpoints,
                key=lambda ep: sum(
                    1 for spike in spikes if spike["endpoint"] == ep)
            )

            # Create simplified service analysis (no individual spikes)
            service_analysis = ServiceSpikeAnalysis(
                service_type=service_type,
                time_range_minutes=time_range_minutes,
                threshold_multiplier=1.0,
                spikes=[],  # Empty for summary
                spike_count=spike_count,
                max_spike_factor=round(max_spike_factor, 2),
                most_affected_endpoint=most_affected_endpoint,
                analysis_timestamp=datetime.now()
            )

            total_spikes += spike_count
            services_with_spikes.append(service_type)

            if worst_spike_factor is None or max_spike_factor > worst_spike_factor:
              worst_spike_factor = max_spike_factor
              worst_spike_service = service_type

          else:
            # Create empty service analysis
            service_analysis = ServiceSpikeAnalysis(
                service_type=service_type,
                time_range_minutes=time_range_minutes,
                threshold_multiplier=1.0,
                spikes=[],
                spike_count=0,
                max_spike_factor=None,
                most_affected_endpoint=None,
                analysis_timestamp=datetime.now()
            )

          # Set the service analysis on the main object
          setattr(spike_analysis, service_type_str, service_analysis)

        except Exception as e:
          logger.error(f"Failed to analyze spikes for {service_type_str}: {e}")
          # Create error service analysis
          service_analysis = ServiceSpikeAnalysis(
              service_type=ServiceType(service_type_str),
              time_range_minutes=time_range_minutes,
              threshold_multiplier=1.0,
              spikes=[],
              spike_count=0,
              max_spike_factor=None,
              most_affected_endpoint=None,
              analysis_timestamp=datetime.now()
          )
          setattr(spike_analysis, service_type_str, service_analysis)

      # Update summary fields
      spike_analysis.total_spikes = total_spikes
      spike_analysis.services_with_spikes = services_with_spikes
      spike_analysis.worst_spike_factor = round(
          worst_spike_factor, 2) if worst_spike_factor else None
      spike_analysis.worst_spike_service = worst_spike_service

      # Update statistics
      spike_analysis.update_statistics()

      return spike_analysis

    except Exception as e:
      logger.error(f"Failed to get spike summaries: {e}", exc_info=True)
      # Return empty analysis on error
      from app.models.latency.analysis.spikes import AllServicesSpikeAnalysis
      from datetime import datetime
      return AllServicesSpikeAnalysis(
          quote=None,
          location=None,
          gmaps=None,
          redis=None,
          time_range_minutes=60,
          threshold_multiplier=1.0,
          total_spikes=0,
          services_with_spikes=[],
          worst_spike_factor=None,
          worst_spike_service=None
      )

  # --- Maintenance Methods ---

  async def reset_service_counters(self, service_type: str) -> bool:
    """Reset latency counters for a service."""
    return await self.calculator.reset_latency_counters(service_type)

  async def cleanup_old_data(self, days_to_keep: int = 7) -> Dict[str, int]:
    """Clean up old latency data."""
    return await self.analyzer.cleanup_old_stream_data(days_to_keep)


# Dependency injection function
async def get_latency_service(redis_service: RedisService) -> LatencyService:
  """Creates and returns a LatencyService instance."""
  return LatencyService(redis_service)
