"""
MongoDB models for core data collections.
"""

from .quotes import QuoteDocument, QuoteStatus
from .calls import CallDocument, CallStatus
from .classify import ClassifyDocument, ClassifyStatus
from .location import LocationDocument, LocationStatus
from .emails import EmailDocument, EmailCategory, EmailStatus

__all__ = [
    "QuoteDocument",
    "QuoteStatus",
    "CallDocument",
    "CallStatus",
    "ClassifyDocument",
    "ClassifyStatus",
    "LocationDocument",
    "LocationStatus",
    "EmailDocument",
    "EmailCategory",
    "EmailStatus",
]
