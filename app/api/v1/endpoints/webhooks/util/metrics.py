# app/api/v1/endpoints/webhooks/util/metrics.py

"""
Metrics collection utilities for webhook endpoints.
Handles performance tracking and analytics.
"""

import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WebhookMetrics:
  """Container for webhook performance metrics."""

  endpoint: str
  request_id: str
  start_time: float = field(default_factory=time.perf_counter)
  end_time: Optional[float] = None
  processing_time_ms: Optional[float] = None

  # Service-specific latencies
  service_latencies: Dict[str, float] = field(default_factory=dict)

  # Cache and database metrics
  cache_hits: int = 0
  cache_misses: int = 0
  db_queries: int = 0

  # Background task metrics
  background_tasks_scheduled: int = 0

  # Error tracking
  errors: List[str] = field(default_factory=list)
  warnings: List[str] = field(default_factory=list)

  # Custom metrics
  custom_metrics: Dict[str, Any] = field(default_factory=dict)

  def finish(self) -> None:
    """Mark the request as finished and calculate processing time."""
    self.end_time = time.perf_counter()
    self.processing_time_ms = (self.end_time - self.start_time) * 1000

  def add_service_latency(self, service: str, latency_ms: float) -> None:
    """Add service-specific latency measurement."""
    self.service_latencies[service] = latency_ms

  def add_cache_hit(self) -> None:
    """Record a cache hit."""
    self.cache_hits += 1

  def add_cache_miss(self) -> None:
    """Record a cache miss."""
    self.cache_misses += 1

  def add_db_query(self) -> None:
    """Record a database query."""
    self.db_queries += 1

  def add_background_task(self) -> None:
    """Record a scheduled background task."""
    self.background_tasks_scheduled += 1

  def add_error(self, error: str) -> None:
    """Add an error message."""
    self.errors.append(error)

  def add_warning(self, warning: str) -> None:
    """Add a warning message."""
    self.warnings.append(warning)

  def set_custom_metric(self, key: str, value: Any) -> None:
    """Set a custom metric value."""
    self.custom_metrics[key] = value

  def to_dict(self) -> Dict[str, Any]:
    """Convert metrics to dictionary for logging/response."""
    return {
        "endpoint": self.endpoint,
        "request_id": self.request_id,
        "processing_time_ms": self.processing_time_ms,
        "service_latencies": self.service_latencies,
        "cache_performance": {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "hit_ratio": (
                self.cache_hits / (self.cache_hits + self.cache_misses)
                if (self.cache_hits + self.cache_misses) > 0 else 0
            )
        },
        "db_queries": self.db_queries,
        "background_tasks_scheduled": self.background_tasks_scheduled,
        "error_count": len(self.errors),
        "warning_count": len(self.warnings),
        "custom_metrics": self.custom_metrics
    }


class WebhookMetricsCollector:
  """Collector for webhook metrics across multiple requests."""

  def __init__(self):
    self._metrics: List[WebhookMetrics] = []
    self._active_metrics: Dict[str, WebhookMetrics] = {}

  def start_request(self, endpoint: str, request_id: str) -> WebhookMetrics:
    """
    Start tracking metrics for a new request.

    Args:
        endpoint: Webhook endpoint name
        request_id: Unique request identifier

    Returns:
        WebhookMetrics instance for tracking
    """
    metrics = WebhookMetrics(endpoint=endpoint, request_id=request_id)
    self._active_metrics[request_id] = metrics
    return metrics

  def finish_request(self, request_id: str) -> Optional[WebhookMetrics]:
    """
    Finish tracking metrics for a request.

    Args:
        request_id: Request identifier

    Returns:
        Completed WebhookMetrics instance or None if not found
    """
    if request_id in self._active_metrics:
      metrics = self._active_metrics.pop(request_id)
      metrics.finish()
      self._metrics.append(metrics)
      return metrics
    return None

  def get_metrics(self, request_id: str) -> Optional[WebhookMetrics]:
    """
    Get metrics for an active request.

    Args:
        request_id: Request identifier

    Returns:
        WebhookMetrics instance or None if not found
    """
    return self._active_metrics.get(request_id)

  def get_endpoint_stats(self, endpoint: str, limit: int = 100) -> Dict[str, Any]:
    """
    Get aggregated statistics for an endpoint.

    Args:
        endpoint: Endpoint name to analyze
        limit: Maximum number of recent requests to analyze

    Returns:
        Dictionary with endpoint statistics
    """
    endpoint_metrics = [
        m for m in self._metrics[-limit:]
        if m.endpoint == endpoint and m.processing_time_ms is not None
    ]

    if not endpoint_metrics:
      return {"endpoint": endpoint, "request_count": 0}

    # Filter out None values for processing times
    processing_times = [
        m.processing_time_ms for m in endpoint_metrics if m.processing_time_ms is not None]

    if not processing_times:
      return {
          "endpoint": endpoint,
          "request_count": len(endpoint_metrics),
          "avg_processing_time_ms": None,
          "min_processing_time_ms": None,
          "max_processing_time_ms": None,
      }

    return {
        "endpoint": endpoint,
        "request_count": len(endpoint_metrics),
        "avg_processing_time_ms": sum(processing_times) / len(processing_times),
        "min_processing_time_ms": min(processing_times),
        "max_processing_time_ms": max(processing_times),
        "total_errors": sum(len(m.errors) for m in endpoint_metrics),
        "total_warnings": sum(len(m.warnings) for m in endpoint_metrics),
        "avg_background_tasks": (
            sum(m.background_tasks_scheduled for m in endpoint_metrics)
            / len(endpoint_metrics)
        ),
        "cache_hit_ratio": self._calculate_cache_hit_ratio(endpoint_metrics)
    }

  def _calculate_cache_hit_ratio(self, metrics: List[WebhookMetrics]) -> float:
    """Calculate overall cache hit ratio for a set of metrics."""
    total_hits = sum(m.cache_hits for m in metrics)
    total_requests = sum(m.cache_hits + m.cache_misses for m in metrics)

    return total_hits / total_requests if total_requests > 0 else 0.0


# Global metrics collector instance
webhook_metrics_collector = WebhookMetricsCollector()
