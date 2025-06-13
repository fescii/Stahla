from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging

from app.core.dependencies import get_dashboard_service_dep
from app.services.dash import DashboardService
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary/{service_type}")
async def get_latency_summary(
    service_type: str,
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
  """
  Get comprehensive latency summary for a specific service.

  **Service Types:**
  - quote: Quote generation latency
  - location: Location lookup latency  
  - gmaps: Google Maps API latency
  - redis: Redis operations latency
  """
  try:
    summary = await dashboard_service.latency_service.calculator.get_latency_summary(service_type)
    if not summary or "error" in summary:
      raise HTTPException(
          status_code=404,
          detail=f"No latency data found for service type: {service_type}"
      )
    return summary
  except Exception as e:
    logger.error(
        f"Failed to get latency summary for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency summary")


@router.get("/summary")
async def get_all_latency_summaries(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Dict[str, Any]]:
  """
  Get latency summaries for all tracked services.
  """
  try:
    summaries = await dashboard_service.latency_service.calculator.get_all_latency_summaries()
    return summaries
  except Exception as e:
    logger.error(f"Failed to get all latency summaries: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency summaries")


@router.get("/percentiles/{service_type}")
async def get_latency_percentiles(
    service_type: str,
    percentiles: Optional[str] = Query(
        "50,90,95,99", description="Comma-separated percentiles (e.g., '50,90,95,99')"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Optional[float]]:
  """
  Get specific percentiles for a service's latency.
  """
  try:
    # Parse percentiles parameter
    if percentiles is None:
      percentiles = "50,90,95,99"
    percentile_list = [float(p.strip()) for p in percentiles.split(",")]

    percentiles_data = await dashboard_service.latency_service.calculator.get_percentiles(
        service_type, percentile_list
    )

    if not any(v is not None for v in percentiles_data.values()):
      raise HTTPException(
          status_code=404,
          detail=f"No latency data found for service type: {service_type}"
      )

    return percentiles_data
  except ValueError as e:
    raise HTTPException(
        status_code=400, detail=f"Invalid percentiles format: {e}")
  except Exception as e:
    logger.error(
        f"Failed to get percentiles for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency percentiles")


@router.get("/average/{service_type}")
async def get_average_latency(
    service_type: str,
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
  """
  Get average latency for a specific service.
  """
  try:
    average = await dashboard_service.latency_service.calculator.get_average_latency(service_type)

    if average is None:
      raise HTTPException(
          status_code=404,
          detail=f"No latency data found for service type: {service_type}"
      )

    return {
        "service_type": service_type,
        "average_latency_ms": average,
        "timestamp": "2025-06-12T00:00:00Z"  # Will be replaced with actual timestamp
    }
  except Exception as e:
    logger.error(
        f"Failed to get average latency for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve average latency")


@router.get("/alerts")
async def get_latency_alerts(
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
  """
  Get current latency alerts based on thresholds.
  """
  try:
    alerts = await dashboard_service.latency_service.calculator.check_latency_alerts()
    return alerts
  except Exception as e:
    logger.error(f"Failed to get latency alerts: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency alerts")


@router.get("/trends/{service_type}")
async def get_latency_trends(
    service_type: str,
    minutes: int = Query(
        60, description="Time range in minutes for trend analysis"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
  """
  Get latency trends over a specified time period.
  """
  try:
    if minutes <= 0 or minutes > 1440:  # Max 24 hours
      raise HTTPException(
          status_code=400, detail="Minutes must be between 1 and 1440")

    trends = await dashboard_service.latency_service.analyzer.get_recent_latency_trend(
        service_type, minutes
    )

    if not trends or "error" in trends:
      raise HTTPException(
          status_code=404,
          detail=f"No trend data found for service type: {service_type}"
      )

    return trends
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(
        f"Failed to get latency trends for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency trends")


@router.get("/spikes/{service_type}")
async def get_latency_spikes(
    service_type: str,
    threshold_multiplier: float = Query(
        3.0, description="Multiplier of average latency to consider a spike"),
    minutes: int = Query(
        60, description="Time range in minutes to analyze for spikes"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
  """
  Get latency spikes that exceed the threshold.
  """
  try:
    if minutes <= 0 or minutes > 1440:
      raise HTTPException(
          status_code=400, detail="Minutes must be between 1 and 1440")
    if threshold_multiplier <= 1.0 or threshold_multiplier > 10.0:
      raise HTTPException(
          status_code=400, detail="Threshold multiplier must be between 1.0 and 10.0")

    spikes = await dashboard_service.latency_service.analyzer.get_latency_spikes(
        service_type, threshold_multiplier, minutes
    )

    return spikes
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(
        f"Failed to get latency spikes for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve latency spikes")


@router.get("/endpoints/{service_type}")
async def get_endpoint_latency_breakdown(
    service_type: str,
    minutes: int = Query(
        60, description="Time range in minutes for endpoint analysis"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Dict[str, Any]]:
  """
  Get latency breakdown by endpoint for a service.
  """
  try:
    if minutes <= 0 or minutes > 1440:
      raise HTTPException(
          status_code=400, detail="Minutes must be between 1 and 1440")

    breakdown = await dashboard_service.latency_service.analyzer.get_endpoint_latency_breakdown(
        service_type, minutes
    )

    return breakdown
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(
        f"Failed to get endpoint breakdown for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to retrieve endpoint latency breakdown")


@router.post("/reset/{service_type}")
async def reset_latency_counters(
    service_type: str,
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
  """
  Reset latency counters for a service (admin operation).
  """
  try:
    success = await dashboard_service.latency_service.calculator.reset_latency_counters(service_type)

    return {
        "service_type": service_type,
        "reset_successful": success,
        "message": f"Latency counters {'reset' if success else 'failed to reset'} for {service_type}",
        "timestamp": "2025-06-12T00:00:00Z"
    }
  except Exception as e:
    logger.error(
        f"Failed to reset latency counters for {service_type}: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to reset latency counters")


@router.post("/cleanup")
async def cleanup_old_latency_data(
    days_to_keep: int = Query(
        7, description="Number of days of latency data to keep"),
    dashboard_service: DashboardService = Depends(get_dashboard_service_dep),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
  """
  Clean up old latency stream data (admin operation).
  """
  try:
    if days_to_keep <= 0 or days_to_keep > 30:
      raise HTTPException(
          status_code=400, detail="Days to keep must be between 1 and 30")

    cleanup_results = await dashboard_service.latency_service.analyzer.cleanup_old_stream_data(days_to_keep)

    total_cleaned = sum(
        count for count in cleanup_results.values() if count >= 0)

    return {
        "days_kept": days_to_keep,
        "cleanup_results": cleanup_results,
        "total_entries_cleaned": total_cleaned,
        "message": f"Cleaned up {total_cleaned} old latency entries across all services",
        "timestamp": "2025-06-12T00:00:00Z"
    }
  except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
  except Exception as e:
    logger.error(f"Failed to cleanup latency data: {e}", exc_info=True)
    raise HTTPException(
        status_code=500, detail="Failed to cleanup latency data")
