from .percentiles import ServicePercentiles
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from .percentiles import ServiceType, LatencyStatus


class AllServicesPercentiles(BaseModel):
  """Percentile metrics for all services."""
  quote: Optional["ServicePercentiles"] = Field(
      None, description="Quote service percentiles")
  location: Optional["ServicePercentiles"] = Field(
      None, description="Location service percentiles")
  hubspot: Optional["ServicePercentiles"] = Field(
      None, description="HubSpot API percentiles")
  bland: Optional["ServicePercentiles"] = Field(
      None, description="Bland.ai API percentiles")
  gmaps: Optional["ServicePercentiles"] = Field(
      None, description="Google Maps API percentiles")
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
    for service_data in [self.quote, self.location, self.hubspot, self.bland, self.gmaps]:
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

  def get_services_by_status(self, status: LatencyStatus) -> List[ServiceType]:
    """Get list of services with the specified status."""
    services = []

    service_checks = [
        (self.quote, ServiceType.QUOTE),
        (self.location, ServiceType.LOCATION),
        (self.hubspot, ServiceType.HUBSPOT),
        (self.bland, ServiceType.BLAND),
        (self.gmaps, ServiceType.GMAPS)
    ]

    for service_data, service_type in service_checks:
      if service_data and service_data.status == status:
        services.append(service_type)

    return services


# Forward reference resolution
AllServicesPercentiles.model_rebuild()
