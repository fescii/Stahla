# app/api/v1/endpoints/webhooks/util/__init__.py

"""
Webhook utilities module.
Provides shared functionality for webhook endpoint handling.
"""

# Import service setup utilities
from .services import (
    setup_webhook_services,
    setup_location_services,
    setup_quote_services
)

# Import other utilities
from .prepare import prepare_classification_input
from .bland import trigger_bland_call, trigger_bland_call_for_hubspot_contact
from .hubspot import (
    handle_hubspot_update,
    update_hubspot_lead_after_classification,
    is_hubspot_contact_complete
)

__all__ = [
    # Service setup utilities
    "setup_webhook_services",
    "setup_location_services",
    "setup_quote_services",

    # Form and classification utilities
    "prepare_classification_input",

    # Bland call utilities
    "trigger_bland_call",
    "trigger_bland_call_for_hubspot_contact",

    # HubSpot integration utilities
    "handle_hubspot_update",
    "update_hubspot_lead_after_classification",
    "is_hubspot_contact_complete"
]
