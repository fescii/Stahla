# app/models/classification_models.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

# Define the possible classification outcomes based on documentation
LeadClassificationType = Literal["Services", "Logistics", "Leads", "Disqualify"]


class ClassificationInput(BaseModel):
	"""
	Input data for the classification engine.
	This model should encompass all relevant fields gathered from
	web forms, voice calls, and emails that are needed for classification.
	"""
	# Example fields - customize based on actual required data points
	source: Literal["webform", "voice", "email"]
	raw_data: Dict[str, Any]  # The raw payload received
	extracted_data: Dict[str, Any] = Field(default_factory=dict, description="Key information extracted from raw_data")
	
	# Add specific fields known to be important for classification:
	# e.g., product_interest: Optional[str] = None
	# e.g., location_zip_code: Optional[str] = None
	# e.g., company_size: Optional[int] = None
	# e.g., budget_mentioned: Optional[float] = None
	# e.g., urgency: Optional[str] = None
	# e.g., required_stalls: Optional[int] = None
	
	class Config:
		extra = 'allow'  # Allow extra fields not explicitly defined


class ClassificationOutput(BaseModel):
	"""
	Output data from the classification engine.
	"""
	lead_type: LeadClassificationType = Field(..., description="The determined classification category.")
	routing_suggestion: Optional[str] = Field(None,
	                                          description="Suggested team or pipeline for routing (e.g., 'Services Sales', 'Logistics Ops').")
	confidence: Optional[float] = Field(None, description="Confidence score of the classification (0.0 to 1.0).")
	reasoning: Optional[str] = Field(None, description="Explanation or justification for the classification.")
	# Flag indicating if human review is recommended
	requires_human_review: bool = Field(False,
	                                    description="Indicates if the classification is uncertain and needs human review.")
	# Any additional metadata generated during classification
	metadata: Dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(BaseModel):
	"""Wrapper for the classification result, including status."""
	status: str  # e.g., "success", "error"
	classification: Optional[ClassificationOutput] = None
	message: Optional[str] = None  # For errors or additional info


"""
**Instructions:** Create a file named `classification_models.py` inside the `app/models/` directory and paste this code into it. You'll need to significantly customize `ClassificationInput` with the actual fields Stahla uses to classify learn
"""
