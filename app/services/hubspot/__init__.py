# app/services/hubspot/__init__.py

from .manager import HubSpotManager

# Create singleton instance for backward compatibility
hubspot_manager = HubSpotManager()

__all__ = ["HubSpotManager", "hubspot_manager"]
