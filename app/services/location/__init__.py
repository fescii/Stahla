# filepath: app/services/location/__init__.py
"""
Location service module - reorganized for better maintainability.

This module provides location operations organized into focused submodules:
- parsing: Address parsing and normalization utilities
- cache: Redis caching operations for branches and states
- google: Google Maps API operations
- areas: Service area validation
- distance: Distance calculation logic
- service: Main LocationService class
"""

# Main service class and dependency
from .service import LocationService
from .dependency import get_location_service

# Export parsing utilities for backward compatibility
from .parsing import parse_and_normalize_address, extract_location_components

# Re-export the main classes for backward compatibility
__all__ = [
    "LocationService",
    "get_location_service",
    "parse_and_normalize_address",
    "extract_location_components",
]
