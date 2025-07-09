# app/services/bland.py
# This file has been refactored and split into multiple modules for better organization.
# The functionality is now available through the following imports:

from app.services.bland.manager import BlandAIManager, get_bland_manager, sync_bland_pathway_on_startup
from app.models.bland import BlandApiResult, BlandCallbackRequest, BlandWebhookPayload, BlandProcessingResult

# For backwards compatibility, expose the main items at the module level
__all__ = [
    "BlandAIManager",
    "get_bland_manager",
    "sync_bland_pathway_on_startup",
    "BlandApiResult",
    "BlandCallbackRequest",
    "BlandWebhookPayload",
    "BlandProcessingResult"
]
