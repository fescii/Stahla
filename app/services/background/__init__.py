"""
Background task services for asynchronous operations.
This module contains functions for tasks that run in the background
without blocking the main request/response cycle.
"""

from .request import log_request_response_bg, increment_request_counter_bg
from .logging import log_error_bg, log_success_bg
from .latency import (
    record_latency_bg,
    record_quote_latency_bg,
    record_location_latency_bg,
    record_external_api_latency_bg
)
from .util import attach_background_tasks
from .mongo import (
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
from .classification import (
    process_voice_classification_bg,
    get_classification_status_bg
)

__all__ = [
    "log_request_response_bg",
    "increment_request_counter_bg",
    "log_error_bg",
    "log_success_bg",
    "record_latency_bg",
    "record_quote_latency_bg",
    "record_location_latency_bg",
    "record_external_api_latency_bg",
    "attach_background_tasks",
    "log_quote_bg",
    "log_call_bg",
    "log_classify_bg",
    "log_location_bg",
    "log_email_bg",
    "update_quote_status_bg",
    "update_call_status_bg",
    "update_classify_status_bg",
    "update_location_status_bg",
    "update_email_status_bg",
    "process_voice_classification_bg",
    "get_classification_status_bg"
]
