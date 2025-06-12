"""Latency API endpoints."""

from .metrics import router as metrics_router
from .percentiles import router as percentiles_router
from .averages import router as averages_router
from .alerts import router as alerts_router
from .trends import router as trends_router
from .spikes import router as spikes_router
from .overview import router as overview_router

__all__ = [
    "metrics_router",
    "percentiles_router",
    "averages_router",
    "alerts_router",
    "trends_router",
    "spikes_router",
    "overview_router"
]
