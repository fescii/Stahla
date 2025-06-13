"""Unified trends endpoint for all services."""

from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User
from app.models.latency.analysis.trends import AllServicesTrendAnalysis, ServiceTrendAnalysis, TrendDirection
from app.models.latency.metrics.percentiles import ServiceType
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=AllServicesTrendAnalysis)
async def get_all_services_trends(
    time_range_minutes: int = Query(
        60, ge=5, le=1440, description="Time range in minutes (5-1440)"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> AllServicesTrendAnalysis:
  """
  Get latency trend analysis for all services in a single response.

  Analyzes trends over the specified time range for:
  - Quote generation service
  - Location lookup service  
  - Google Maps API
  - Redis Cache

  Returns trend direction, statistics, and overall system trends.
  """
  try:
    # Get trend analysis for all services
    trends_data = AllServicesTrendAnalysis(
        quote=None,
        location=None,
        gmaps=None,
        redis=None,
        time_range_minutes=time_range_minutes,
        overall_trend=TrendDirection.NO_DATA,
        services_analyzed=0,
        total_samples=0
    )

    services_analyzed = 0
    total_samples = 0

    # Analyze each service
    for service_type_str in ["quote", "location", "gmaps", "redis"]:
      try:
        service_type = ServiceType(service_type_str)

        # Get trend analysis for this service
        trend_result = await dashboard_service.latency_service.analyzer.get_recent_latency_trend(
            service_type_str, time_range_minutes
        )

        if trend_result and trend_result.get("sample_count", 0) > 0:
          service_trend = ServiceTrendAnalysis(
              service_type=service_type,
              time_range_minutes=time_range_minutes,
              sample_count=trend_result.get("sample_count", 0),
              trend=_determine_trend_direction(trend_result),
              statistics=trend_result.get("statistics", {}),
              endpoint_distribution=trend_result.get(
                  "endpoint_distribution", {}),
              message=_generate_trend_message(service_type_str, trend_result),
              analysis_timestamp=datetime.now()
          )

          setattr(trends_data, service_type_str, service_trend)
          services_analyzed += 1
          total_samples += trend_result.get("sample_count", 0)

      except ValueError:
        logger.warning(f"Unknown service type: {service_type_str}")
        continue
      except Exception as e:
        logger.error(f"Failed to analyze trends for {service_type_str}: {e}")
        continue

    # Update summary statistics
    trends_data.services_analyzed = services_analyzed
    trends_data.total_samples = total_samples
    trends_data.overall_trend = trends_data.calculate_overall_trend()

    return trends_data

  except Exception as e:
    logger.error(f"Failed to get all services trends: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve trend analysis")


def _determine_trend_direction(trend_result: dict) -> TrendDirection:
  """Determine trend direction from analysis result."""
  sample_count = trend_result.get("sample_count", 0)

  if sample_count < 3:
    return TrendDirection.INSUFFICIENT_DATA
  elif sample_count == 0:
    return TrendDirection.NO_DATA

  # Check for trend indicators in statistics
  stats = trend_result.get("statistics", {})
  slope = stats.get("trend_slope")

  if slope is None:
    return TrendDirection.STABLE
  elif slope > 0.1:  # Increasing trend
    return TrendDirection.INCREASING
  elif slope < -0.1:  # Decreasing trend
    return TrendDirection.DECREASING
  else:
    return TrendDirection.STABLE


def _generate_trend_message(service_type: str, trend_result: dict) -> str:
  """Generate a human-readable trend message."""
  sample_count = trend_result.get("sample_count", 0)
  stats = trend_result.get("statistics", {})

  if sample_count == 0:
    return f"No data available for {service_type} service"
  elif sample_count < 3:
    return f"Insufficient data for trend analysis ({sample_count} samples)"

  mean_latency = stats.get("mean", 0)
  trend_slope = stats.get("trend_slope", 0)

  direction = "stable"
  if trend_slope > 0.1:
    direction = "increasing"
  elif trend_slope < -0.1:
    direction = "decreasing"

  return f"{service_type.title()} latency is {direction} (avg: {mean_latency:.1f}ms, {sample_count} samples)"
