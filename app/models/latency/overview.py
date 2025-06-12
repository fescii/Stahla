from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from .metrics.summary import AllServicesPercentiles
from .metrics.averages import AllServicesAverageLatency
from .alerts.alerts import AllServicesAlerts
from .analysis.trends import AllServicesTrendAnalysis
from .analysis.spikes import AllServicesSpikeAnalysis
from .metrics.percentiles import LatencyStatus


class LatencyOverview(BaseModel):
  """Comprehensive latency overview for all services."""
  # Core metrics
  percentiles: AllServicesPercentiles = Field(
      description="Percentile metrics for all services")
  averages: AllServicesAverageLatency = Field(
      description="Average latency metrics for all services")

  # Alerts and monitoring
  alerts: AllServicesAlerts = Field(description="Active latency alerts")

  # Analysis
  trends: Optional[AllServicesTrendAnalysis] = Field(
      None, description="Trend analysis for all services")
  spikes: Optional[AllServicesSpikeAnalysis] = Field(
      None, description="Spike analysis for all services")

  # Overall system status
  overall_status: LatencyStatus = Field(
      LatencyStatus.UNKNOWN, description="Overall system latency health")
  system_health_score: Optional[float] = Field(
      None, description="Overall health score (0-100)")

  # Metadata
  generated_at: datetime = Field(
      default_factory=datetime.now, description="When this overview was generated")
  analysis_time_range_minutes: int = Field(
      60, description="Time range used for analysis")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

  def calculate_overall_status(self) -> LatencyStatus:
    """Calculate the overall system status from all metrics."""
    # Priority: alerts > percentiles > averages
    if self.alerts.critical_count > 0:
      return LatencyStatus.CRITICAL
    elif self.alerts.warning_count > 0:
      return LatencyStatus.WARNING
    else:
      # Check percentiles status
      percentiles_status = self.percentiles.get_worst_status()
      if percentiles_status in [LatencyStatus.CRITICAL, LatencyStatus.WARNING]:
        return percentiles_status

      # Check averages status
      averages_status = self.averages.get_worst_status()
      return averages_status

  def calculate_health_score(self) -> float:
    """Calculate a health score from 0-100 based on latency metrics."""
    score = 100.0

    # Deduct points for alerts
    score -= self.alerts.critical_count * 30  # Critical alerts: -30 points each
    score -= self.alerts.warning_count * 15   # Warning alerts: -15 points each
    score -= self.alerts.info_count * 5       # Info alerts: -5 points each

    # Deduct points for services with poor status
    critical_services = len(
        self.percentiles.get_services_by_status(LatencyStatus.CRITICAL))
    warning_services = len(
        self.percentiles.get_services_by_status(LatencyStatus.WARNING))

    score -= critical_services * 20  # Critical services: -20 points each
    score -= warning_services * 10   # Warning services: -10 points each

    # Ensure score is between 0 and 100
    return max(0.0, min(100.0, score))

  def update_calculated_fields(self):
    """Update calculated fields based on current data."""
    self.overall_status = self.calculate_overall_status()
    self.system_health_score = self.calculate_health_score()

    # Update sub-model calculated fields
    if self.trends:
      self.trends.overall_trend = self.trends.calculate_overall_trend()

    if self.spikes:
      self.spikes.update_statistics()

    self.alerts.update_counts()
