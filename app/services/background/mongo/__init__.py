# filepath: app/services/background/mongo/__init__.py
"""Background tasks for MongoDB operations."""

from .tasks import (
    log_quote_bg,
    log_call_bg,
    log_classify_bg,
    log_location_bg,
    log_email_bg,
    update_quote_status_bg,
    update_call_status_bg,
    update_classify_status_bg,
    update_location_status_bg,
    update_email_status_bg
)

__all__ = [
    "log_quote_bg",
    "log_call_bg",
    "log_classify_bg",
    "log_location_bg",
    "log_email_bg",
    "update_quote_status_bg",
    "update_call_status_bg",
    "update_classify_status_bg",
    "update_location_status_bg",
    "update_email_status_bg"
]
