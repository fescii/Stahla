# app/services/bland/processing/ai/__init__.py

"""
AI-powered processing module for Bland voice call analysis.

This module provides comprehensive AI-driven extraction, classification,
and HubSpot property mapping for voice call transcripts from Bland.ai.

Key components:
- extractor: AI field extraction using Marvin
- transcript: Transcript processing and extraction
- location: Location processing and validation
- classification: Lead classification coordination
- results: Result building and formatting
- service: Enhanced webhook service with AI integration
"""

from .extractor import ai_field_extractor, AIFieldExtractor
from .transcript.processor import transcript_processor
from .location.handler import create_location_handler
from .classification.coordinator import create_classification_coordinator
from .results.builder import result_builder
from .service import enhanced_voice_webhook_service, EnhancedVoiceWebhookService

__all__ = [
    "ai_field_extractor",
    "AIFieldExtractor",
    "transcript_processor",
    "create_location_handler",
    "create_classification_coordinator",
    "result_builder",
    "enhanced_voice_webhook_service",
    "EnhancedVoiceWebhookService"
]
