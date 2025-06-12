# app/api/v1/endpoints/webhooks/models/__init__.py

"""
Webhook models module.
Provides shared data models and response structures for webhook endpoints.
"""

from .responses import (
    WebhookStatusResponse,
    WebhookErrorResponse,
    WebhookMetricsResponse,
    create_success_response,
    create_error_response
)

__all__ = [
    "WebhookStatusResponse",
    "WebhookErrorResponse",
    "WebhookMetricsResponse",
    "create_success_response",
    "create_error_response"
]
