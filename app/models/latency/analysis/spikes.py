from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..metrics.percentiles import ServiceType


class LatencySpike(BaseModel):
  """Individual latency spike record."""
  service_type: ServiceType
  stream_id: str = Field(description="Redis stream ID for this spike")
  latency_ms: float = Field(description="Latency value that caused the spike")
  request_id: str = Field(description="Request ID associated with the spike")
  endpoint: str = Field(description="Endpoint that experienced the spike")
  spike_factor: float = Field(
      description="How many times higher than average this spike was")
  threshold_ms: float = Field(description="Threshold that was exceeded")
  average_ms: float = Field(description="Average latency at time of spike")
  timestamp: Optional[datetime] = Field(
      None, description="When the spike occurred")
  context: Optional[Dict[str, Any]] = Field(
      None, description="Additional context from the request")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }


class ServiceSpikeAnalysis(BaseModel):
  """Spike analysis for a single service."""
  service_type: ServiceType
  time_range_minutes: int = Field(description="Time range analyzed for spikes")
  threshold_multiplier: float = Field(
      description="Multiplier used to detect spikes")
  spikes: List[LatencySpike] = Field(
      default_factory=list, description="Detected latency spikes")
  spike_count: int = Field(0, description="Total number of spikes detected")
  max_spike_factor: Optional[float] = Field(
      None, description="Highest spike factor detected")
  most_affected_endpoint: Optional[str] = Field(
      None, description="Endpoint with the most spikes")
  analysis_timestamp: datetime = Field(
      default_factory=datetime.now, description="When analysis was performed")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

  def update_statistics(self):
    """Update statistics based on current spikes."""
    self.spike_count = len(self.spikes)

    if self.spikes:
      self.max_spike_factor = max(spike.spike_factor for spike in self.spikes)

      # Find most affected endpoint
      endpoint_counts = {}
      for spike in self.spikes:
        endpoint_counts[spike.endpoint] = endpoint_counts.get(
            spike.endpoint, 0) + 1

      if endpoint_counts:
        self.most_affected_endpoint = max(
            endpoint_counts.items(), key=lambda x: x[1])[0]


class AllServicesSpikeAnalysis(BaseModel):
  """Spike analysis for all services."""
  quote: Optional[ServiceSpikeAnalysis] = Field(
      None, description="Quote service spike analysis")
  location: Optional[ServiceSpikeAnalysis] = Field(
      None, description="Location service spike analysis")
  gmaps: Optional[ServiceSpikeAnalysis] = Field(
      None, description="Google Maps API spike analysis")
  redis: Optional[ServiceSpikeAnalysis] = Field(
      None, description="Redis operations spike analysis")
  time_range_minutes: int = Field(
      60, description="Time range analyzed for spikes")
  threshold_multiplier: float = Field(
      3.0, description="Multiplier used to detect spikes")
  total_spikes: int = Field(0, description="Total spikes across all services")
  services_with_spikes: List[ServiceType] = Field(
      default_factory=list, description="Services that had spikes")
  worst_spike_factor: Optional[float] = Field(
      None, description="Highest spike factor across all services")
  worst_spike_service: Optional[ServiceType] = Field(
      None, description="Service with the worst spike")
  generated_at: datetime = Field(
      default_factory=datetime.now, description="When this analysis was generated")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

  def update_statistics(self):
    """Update overall statistics based on service analyses."""
    total_spikes = 0
    services_with_spikes = []
    worst_factor = None
    worst_service = None

    service_checks = [
        (self.quote, ServiceType.QUOTE),
        (self.location, ServiceType.LOCATION),
        (self.gmaps, ServiceType.GMAPS),
        (self.redis, ServiceType.REDIS)
    ]

    for service_data, service_type in service_checks:
      if service_data and service_data.spike_count > 0:
        total_spikes += service_data.spike_count
        services_with_spikes.append(service_type)

        if service_data.max_spike_factor:
          if worst_factor is None or service_data.max_spike_factor > worst_factor:
            worst_factor = service_data.max_spike_factor
            worst_service = service_type

    self.total_spikes = total_spikes
    self.services_with_spikes = services_with_spikes
    self.worst_spike_factor = worst_factor
    self.worst_spike_service = worst_service

  def get_top_spikes(self, limit: int = 10) -> List[LatencySpike]:
    """Get the top spikes across all services by spike factor."""
    all_spikes = []

    for service_data in [self.quote, self.location, self.gmaps, self.redis]:
      if service_data:
        all_spikes.extend(service_data.spikes)

    # Sort by spike factor (highest first) and return top N
    all_spikes.sort(key=lambda x: x.spike_factor, reverse=True)
    return all_spikes[:limit]
