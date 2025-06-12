from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from ..metrics.percentiles import ServiceType, LatencyStatus
from enum import Enum


class AlertSeverity(str, Enum):
  """Alert severity levels."""
  INFO = "info"
  WARNING = "warning"
  CRITICAL = "critical"


class LatencyAlert(BaseModel):
  """Individual latency alert."""
  service_type: ServiceType
  severity: AlertSeverity
  alert_type: str = Field(
      description="Type of alert (e.g., 'p95_threshold', 'average_threshold')")
  current_value_ms: float = Field(
      description="Current latency value that triggered the alert")
  threshold_ms: float = Field(description="Threshold value that was exceeded")
  message: str = Field(description="Human-readable alert message")
  triggered_at: datetime = Field(
      default_factory=datetime.now, description="When the alert was triggered")
  context: Optional[dict] = Field(
      None, description="Additional context information")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }


class AllServicesAlerts(BaseModel):
  """All latency alerts across services."""
  active_alerts: List[LatencyAlert] = Field(
      default_factory=list, description="Currently active alerts")
  critical_count: int = Field(0, description="Number of critical alerts")
  warning_count: int = Field(0, description="Number of warning alerts")
  info_count: int = Field(0, description="Number of info alerts")
  total_alerts: int = Field(0, description="Total number of active alerts")
  overall_severity: AlertSeverity = Field(
      AlertSeverity.INFO, description="Highest severity among all alerts")
  services_with_alerts: List[ServiceType] = Field(
      default_factory=list, description="Services that have active alerts")
  generated_at: datetime = Field(
      default_factory=datetime.now, description="When this summary was generated")

  class Config:
    json_encoders = {
        datetime: lambda v: v.isoformat() if v else None
    }

  def get_alerts_by_service(self, service_type: ServiceType) -> List[LatencyAlert]:
    """Get all alerts for a specific service."""
    return [alert for alert in self.active_alerts if alert.service_type == service_type]

  def get_alerts_by_severity(self, severity: AlertSeverity) -> List[LatencyAlert]:
    """Get all alerts with the specified severity."""
    return [alert for alert in self.active_alerts if alert.severity == severity]

  def update_counts(self):
    """Update the alert counts based on active alerts."""
    self.critical_count = len(
        [a for a in self.active_alerts if a.severity == AlertSeverity.CRITICAL])
    self.warning_count = len(
        [a for a in self.active_alerts if a.severity == AlertSeverity.WARNING])
    self.info_count = len(
        [a for a in self.active_alerts if a.severity == AlertSeverity.INFO])
    self.total_alerts = len(self.active_alerts)

    # Determine overall severity
    if self.critical_count > 0:
      self.overall_severity = AlertSeverity.CRITICAL
    elif self.warning_count > 0:
      self.overall_severity = AlertSeverity.WARNING
    else:
      self.overall_severity = AlertSeverity.INFO

    # Update services with alerts
    self.services_with_alerts = list(
        set([alert.service_type for alert in self.active_alerts]))

  def add_alert(self, alert: LatencyAlert):
    """Add a new alert and update counts."""
    self.active_alerts.append(alert)
    self.update_counts()

  def remove_alerts_for_service(self, service_type: ServiceType):
    """Remove all alerts for a specific service."""
    self.active_alerts = [
        alert for alert in self.active_alerts if alert.service_type != service_type]
    self.update_counts()

  def clear_all_alerts(self):
    """Clear all active alerts."""
    self.active_alerts.clear()
    self.update_counts()
