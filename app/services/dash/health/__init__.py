# app/services/dash/health/__init__.py

"""
Health check utilities for dashboard services.
"""

from .checker import ServiceStatusMonitor

__all__ = ["ServiceStatusMonitor"]
