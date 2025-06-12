from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from .percentiles import ServiceType, LatencyStatus


class ServiceAverageLatency(BaseModel):
  """Average latency metrics for a single service."""
  service_type: ServiceType
  average_ms: Optional[float] = Field(
      None, description="Average latency in milliseconds")
  sample_count: int = Field(
      0, description="Number of samples used for calculation")
  status: LatencyStatus = Field(
      LatencyStatus.UNKNOWN, description="Status based on average threshold")
  last_updated: Optional[datetime] = Field(
      None, description="When this metric was last calculated")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }


class AllServicesAverageLatency(BaseModel):
  """Average latency metrics for all services."""
  quote: Optional[ServiceAverageLatency] = Field(
      None, description="Quote service average latency")
  location: Optional[ServiceAverageLatency] = Field(
      None, description="Location service average latency")
  hubspot: Optional[ServiceAverageLatency] = Field(
      None, description="HubSpot API average latency")
  bland: Optional[ServiceAverageLatency] = Field(
      None, description="Bland.ai API average latency")
  gmaps: Optional[ServiceAverageLatency] = Field(
      None, description="Google Maps API average latency")
  redis: Optional[ServiceAverageLatency] = Field(
      None, description="Redis operations average latency")
  overall_average_ms: Optional[float] = Field(
      None, description="Overall average latency across all services")
  overall_status: LatencyStatus = Field(
      LatencyStatus.UNKNOWN, description="Overall system latency status")
  total_samples: int = Field(
      0, description="Total number of samples across all services")
  services_with_data: int = Field(
      0, description="Number of services that have latency data")
  generated_at: datetime = Field(
      default_factory=datetime.now, description="When this summary was generated")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

  def get_worst_status(self) -> LatencyStatus:
    """Determine the worst status across all services."""
    statuses = []
    for service_data in [self.quote, self.location, self.hubspot, self.bland, self.gmaps, self.redis]:
      if service_data:
        statuses.append(service_data.status)

    if LatencyStatus.CRITICAL in statuses:
      return LatencyStatus.CRITICAL
    elif LatencyStatus.WARNING in statuses:
      return LatencyStatus.WARNING
    elif LatencyStatus.GOOD in statuses:
      return LatencyStatus.GOOD
    else:
      return LatencyStatus.UNKNOWN

  def calculate_overall_average(self) -> Optional[float]:
    """Calculate weighted average across all services."""
    total_weighted_latency = 0.0
    total_samples = 0

    for service_data in [self.quote, self.location, self.hubspot, self.bland, self.gmaps, self.redis]:
      if service_data and service_data.average_ms is not None and service_data.sample_count > 0:
        total_weighted_latency += service_data.average_ms * service_data.sample_count
        total_samples += service_data.sample_count

    return total_weighted_latency / total_samples if total_samples > 0 else None

  def get_services_by_status(self, status: LatencyStatus) -> List[ServiceType]:
    """Get list of services with the specified status."""
    services = []

    service_checks = [
        (self.quote, ServiceType.QUOTE),
        (self.location, ServiceType.LOCATION),
        (self.hubspot, ServiceType.HUBSPOT),
        (self.bland, ServiceType.BLAND),
        (self.gmaps, ServiceType.GMAPS),
        (self.redis, ServiceType.REDIS)
    ]

    for service_data, service_type in service_checks:
      if service_data and service_data.status == status:
        services.append(service_type)

    return services
