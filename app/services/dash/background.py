"""
DEPRECATED: This module has been reorganized for better maintainability.

All background task functions have been moved to app.services.background:
- Request/response logging: app.services.background.request
- Error/success logging: app.services.background.logging  
- Latency recording: app.services.background.latency

This file is kept for backward compatibility and will be removed in a future version.
Please update your imports to use the new structure.
"""

# Redirect imports to new locations
from app.services.background.request import (
    log_request_response_bg,
    increment_request_counter_bg
)
from app.services.background.logging import (
    log_error_bg,
    log_success_bg
)
from app.services.background.latency import (
    record_latency_bg,
    record_quote_latency_bg,
    record_location_latency_bg,
    record_external_api_latency_bg
)

# Keep the old imports working for now
__all__ = [
    "log_request_response_bg",
    "increment_request_counter_bg",
    "log_error_bg", 
    "log_success_bg",
    "record_latency_bg",
    "record_quote_latency_bg",
    "record_location_latency_bg", 
    "record_external_api_latency_bg"
]
