from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from ..metrics.percentiles import ServiceType, LatencyStatus
from enum import Enum


class TrendDirection(str, Enum):
  """Trend direction indicators."""
  INCREASING = "increasing"
  DECREASING = "decreasing"
  STABLE = "stable"
  INSUFFICIENT_DATA = "insufficient_data"
  NO_DATA = "no_data"


class ServiceTrendAnalysis(BaseModel):
  """Trend analysis for a single service."""
  service_type: ServiceType
  time_range_minutes: int = Field(description="Time range analyzed in minutes")
  sample_count: int = Field(0, description="Number of samples in the analysis")
  trend: TrendDirection = Field(description="Overall trend direction")
  statistics: Dict[str, float] = Field(
      default_factory=dict, description="Statistical measures")
  endpoint_distribution: Dict[str, int] = Field(
      default_factory=dict, description="Request count by endpoint")
  message: Optional[str] = Field(
      None, description="Human-readable trend summary")
  analysis_timestamp: datetime = Field(
      default_factory=datetime.now, description="When analysis was performed")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }


class AllServicesTrendAnalysis(BaseModel):
  """Trend analysis for all services."""
  quote: Optional[ServiceTrendAnalysis] = Field(
      None, description="Quote service trend analysis")
  location: Optional[ServiceTrendAnalysis] = Field(
      None, description="Location service trend analysis")
  hubspot: Optional[ServiceTrendAnalysis] = Field(
      None, description="HubSpot API trend analysis")
  bland: Optional[ServiceTrendAnalysis] = Field(
      None, description="Bland.ai API trend analysis")
  gmaps: Optional[ServiceTrendAnalysis] = Field(
      None, description="Google Maps API trend analysis")
  time_range_minutes: int = Field(
      60, description="Time range analyzed in minutes")
  overall_trend: TrendDirection = Field(
      TrendDirection.NO_DATA, description="Overall system trend")
  services_analyzed: int = Field(
      0, description="Number of services with sufficient data for analysis")
  total_samples: int = Field(
      0, description="Total samples across all services")
  generated_at: datetime = Field(
      default_factory=datetime.now, description="When this analysis was generated")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

  def get_services_by_trend(self, trend: TrendDirection) -> List[ServiceType]:
    """Get list of services with the specified trend."""
    services = []

    service_checks = [
        (self.quote, ServiceType.QUOTE),
        (self.location, ServiceType.LOCATION),
        (self.hubspot, ServiceType.HUBSPOT),
        (self.bland, ServiceType.BLAND),
        (self.gmaps, ServiceType.GMAPS)
    ]

    for service_data, service_type in service_checks:
      if service_data and service_data.trend == trend:
        services.append(service_type)

    return services

  def calculate_overall_trend(self) -> TrendDirection:
    """Calculate overall trend across all services."""
    trends = []
    for service_data in [self.quote, self.location, self.hubspot, self.bland, self.gmaps]:
      if service_data and service_data.trend != TrendDirection.NO_DATA:
        trends.append(service_data.trend)

    if not trends:
      return TrendDirection.NO_DATA

    # Count trends
    increasing_count = trends.count(TrendDirection.INCREASING)
    decreasing_count = trends.count(TrendDirection.DECREASING)
    stable_count = trends.count(TrendDirection.STABLE)

    # Determine overall trend
    if increasing_count > decreasing_count and increasing_count > stable_count:
      return TrendDirection.INCREASING
    elif decreasing_count > increasing_count and decreasing_count > stable_count:
      return TrendDirection.DECREASING
    elif stable_count >= increasing_count and stable_count >= decreasing_count:
      return TrendDirection.STABLE
    else:
      return TrendDirection.INSUFFICIENT_DATA
