"""Unified alerts endpoint for all services."""

from fastapi import APIRouter, Depends, HTTPException
from typing import List
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency.alerts.alerts import AllServicesAlerts, LatencyAlert, AlertSeverity
from app.models.latency.metrics.percentiles import ServiceType
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/active", response_model=AllServicesAlerts)
async def get_all_services_alerts(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesAlerts:
  """
  Get active latency alerts for all services in a single response.

  Returns alerts for:
  - Quote generation service
  - Location lookup service  
  - Google Maps API
  - Redis Cache

  Includes alert counts by severity and overall system alert status.
  """
  try:
    # Get current latency summaries to generate alerts
    all_summaries = await dashboard_service.latency_service.calculator.get_all_latency_summaries()

    # Generate alerts based on current latency data
    active_alerts = []

    for service_type_str, summary in all_summaries.items():
      if summary and not summary.get("error"):
        try:
          service_type = ServiceType(service_type_str)
          alerts = _generate_alerts_from_summary(service_type, summary)
          active_alerts.extend(alerts)
        except ValueError:
          continue

    # Create alerts response
    alerts_data = AllServicesAlerts(
        active_alerts=active_alerts,
        critical_count=0,
        warning_count=0,
        info_count=0,
        total_alerts=0,
        overall_severity=AlertSeverity.INFO
    )
    alerts_data.update_counts()

    return alerts_data

  except Exception as e:
    logger.error(f"Failed to get all services alerts: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency alerts")


@router.get("/severity/{severity}", response_model=AllServicesAlerts)
async def get_alerts_by_severity(
    severity: AlertSeverity,
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesAlerts:
  """
  Get alerts filtered by severity level.

  **Severity Levels:**
  - critical: Critical alerts that require immediate attention
  - warning: Warning alerts that should be monitored
  - info: Informational alerts for awareness
  """
  try:
    # Get all alerts first
    all_alerts_response = await get_all_services_alerts(dashboard_service, current_user)

    # Filter by severity
    filtered_alerts = [
        alert for alert in all_alerts_response.active_alerts
        if alert.severity == severity
    ]

    # Create filtered response
    alerts_data = AllServicesAlerts(
        active_alerts=filtered_alerts,
        critical_count=0,
        warning_count=0,
        info_count=0,
        total_alerts=0,
        overall_severity=AlertSeverity.INFO
    )
    alerts_data.update_counts()

    return alerts_data

  except Exception as e:
    logger.error(
        f"Failed to get alerts by severity {severity}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve filtered alerts")


def _generate_alerts_from_summary(service_type: ServiceType, summary: dict) -> List[LatencyAlert]:
  """Generate alerts based on latency summary data."""
  alerts = []

  # Check P95 latency thresholds
  p95_latency = summary.get("percentiles", {}).get("p95.0")
  if p95_latency:
    if p95_latency > 1000:  # Critical threshold: > 1000ms
      alerts.append(LatencyAlert(
          service_type=service_type,
          severity=AlertSeverity.CRITICAL,
          alert_type="p95_threshold",
          current_value_ms=p95_latency,
          threshold_ms=1000.0,
          message=f"{service_type.value} P95 latency ({p95_latency:.1f}ms) is critically high (>1000ms)",
          context={"percentile": "p95", "summary": summary}
      ))
    elif p95_latency > 500:  # Warning threshold: > 500ms
      alerts.append(LatencyAlert(
          service_type=service_type,
          severity=AlertSeverity.WARNING,
          alert_type="p95_threshold",
          current_value_ms=p95_latency,
          threshold_ms=500.0,
          message=f"{service_type.value} P95 latency ({p95_latency:.1f}ms) exceeds warning threshold (>500ms)",
          context={"percentile": "p95", "summary": summary}
      ))

  # Check average latency thresholds
  mean_latency = summary.get("mean_latency")
  if mean_latency and mean_latency > 300:  # Warning threshold for average
    alerts.append(LatencyAlert(
        service_type=service_type,
        severity=AlertSeverity.WARNING,
        alert_type="average_threshold",
        current_value_ms=mean_latency,
        threshold_ms=300.0,
        message=f"{service_type.value} average latency ({mean_latency:.1f}ms) is high (>300ms)",
        context={"metric": "average", "summary": summary}
    ))

  return alerts
