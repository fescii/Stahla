"""
Quote models module.

This module is kept for backward compatibility, importing all models from the structured quote module.
"""

# Request models
from app.models.quote.request.extras.input import ExtraInput
from app.models.quote.request.body import QuoteRequest

# Response models
from app.models.quote.response.line.item import LineItem
from app.models.quote.response.details.delivery import DeliveryCostDetails
from app.models.quote.response.details.location import LocationDetails
from app.models.quote.response.details.rental import RentalDetails
from app.models.quote.response.details.product import ProductDetails
from app.models.quote.response.details.budget import BudgetDetails
from app.models.quote.response.body import QuoteBody
from app.models.quote.response.meta.data import QuoteMetadata
from app.models.quote.response.main import QuoteResponse

__all__ = [
    # Request models
    "ExtraInput",
    "QuoteRequest",

    # Response models
    "LineItem",
    "DeliveryCostDetails",
    "LocationDetails",
    "RentalDetails",
    "ProductDetails",
    "BudgetDetails",
    "QuoteBody",
    "QuoteMetadata",
    "QuoteResponse",
]
