# app/services/classification.py

import logfire
from typing import Optional, Tuple

# Import models
from app.models.classification import (
    ClassificationInput,
    ClassificationOutput,
    ClassificationResult,
    LeadClassificationType,
    IntendedUseType,
    ProductType
)
# Needed for pipeline/owner logic
from app.models.hubspot import HubSpotDealProperties
from app.core.config import settings  # Import settings for threshold
from app.services.classify.rules import classify_lead
from app.services.classify.marvin import marvin_classification_manager
from app.utils.location import determine_locality_from_description


class ClassificationManager:
  """
  Manages the classification of leads based on input data.
  Applies rules defined in the PRD and call script.
  """

  def _determine_locality(self,
                          location_description: Optional[str] = None,
                          state_code: Optional[str] = None,
                          city: Optional[str] = None,
                          postal_code: Optional[str] = None) -> bool:
    """
    Determine if a location is local based on drive time from key service hubs.
    Local is defined as ≤ 3 hours from Omaha NE, Denver CO, or Kansas City KS.

    Args:
        location_description: Text description of the location
        state_code: Two-letter state code (e.g., 'NY', 'CO') if available
        city: City name if available
        postal_code: Postal/ZIP code if available
    """
    # Import enhanced location utils that support all location fields
    from app.utils.location_enhanced import determine_locality_from_description
    return determine_locality_from_description(
        location_description=location_description,
        state_code=state_code,
        city=city,
        postal_code=postal_code
    )

  def _estimate_deal_value(self, input_data: ClassificationInput) -> float:
    """
    Estimate deal value based on product type, stalls, and duration.
    Used for prioritization and routing decisions.
    """
    value = 0.0

    # Base values by product type
    if input_data.product_interest:
      product_interest_lower = [p.lower() for p in input_data.product_interest]

      # Specialty trailers have higher base values
      if any("trailer" in p for p in product_interest_lower):
        if any("restroom" in p for p in product_interest_lower):
          value += 7500  # Restroom trailer base value
        elif any("shower" in p for p in product_interest_lower):
          value += 8500  # Shower trailer base value
        elif any("ada" in p for p in product_interest_lower):
          value += 9000  # ADA trailer base value
        else:
          value += 7000  # Generic trailer base value

      # Porta potties and handwashing stations have lower base values
      if any("toilet" in p or "potty" in p for p in product_interest_lower):
        value += 500  # Base value for porta potty
      if any("handwashing" in p or "wash" in p for p in product_interest_lower):
        value += 300  # Base value for handwashing station

    # Scale by quantity and duration
    if input_data.required_stalls:
      # Higher stall counts increase value proportionally
      if input_data.required_stalls >= 20:
        value *= 2.5  # Significant increase for large quantities
      elif input_data.required_stalls >= 10:
        value *= 1.8  # Moderate increase for medium quantities
      elif input_data.required_stalls >= 5:
        value *= 1.4  # Small increase for smaller quantities

    if input_data.duration_days:
      # Longer durations significantly increase value
      if input_data.duration_days >= 30:
        value *= 3.0  # Monthly rental factor
      elif input_data.duration_days >= 14:
        value *= 2.0  # Two-week rental factor
      elif input_data.duration_days >= 7:
        value *= 1.5  # One-week rental factor
      elif input_data.duration_days >= 3:
        value *= 1.2  # Weekend rental factor

    # Consider explicitly mentioned budget if available
    if input_data.budget_mentioned:
      try:
        # Extract numeric part from budget string
        numeric_part = ''.join(
            c for c in input_data.budget_mentioned if c.isdigit() or c == '.')
        if numeric_part:
          mentioned_value = float(numeric_part)
          # Use mentioned budget if it's reasonable (not too low)
          if mentioned_value > value * 0.7:
            value = max(value, mentioned_value)
      except (ValueError, TypeError):
        # Ignore parsing errors for budget
        pass

    logfire.info(f"Estimated deal value: ${value:.2f}",
                 product_interest=input_data.product_interest,
                 stalls=input_data.required_stalls,
                 duration=input_data.duration_days)

    return value

  async def classify_lead_data(self, input_data: ClassificationInput) -> ClassificationResult:
    """
    Classifies the lead based on the provided input data using the defined business rules.
    """
    logfire.info("Starting lead classification.",
                 input_source=input_data.source)

    # If intended_use is not explicitly set, try to infer it from lead_type_guess or event_type
    if not input_data.intended_use and (input_data.lead_type_guess or input_data.event_type):
      source_text = (
          input_data.lead_type_guess or input_data.event_type or "").lower()

      # Simple mapping based on keywords (could be more sophisticated)
      if "small" in source_text and "event" in source_text:
        input_data.intended_use = "Small Event"
      elif "large" in source_text and "event" in source_text:
        input_data.intended_use = "Large Event"
      elif "disaster" in source_text or "emergency" in source_text or "relief" in source_text:
        input_data.intended_use = "Disaster Relief"
      elif "construction" in source_text or "job site" in source_text or "work site" in source_text:
        input_data.intended_use = "Construction"
      elif "facility" in source_text or "building" in source_text or "supplement" in source_text:
        input_data.intended_use = "Facility"
      elif "event" in source_text or "wedding" in source_text or "festival" in source_text:
        # Default to Small Event if just "event" is mentioned without size specification
        input_data.intended_use = "Small Event"

    # Determine locality if not already set
    if input_data.is_local is None:
      input_data.is_local = self._determine_locality(
          input_data.event_location_description)

    try:
      # Use Marvin for classification if enabled in settings
      if settings.LLM_PROVIDER.lower() == "marvin" and settings.MARVIN_API_KEY:
        # Call the Marvin-based classification engine
        classification, reasoning, owner_team = await marvin_classification_manager.get_lead_classification(input_data)
        logfire.info("Using Marvin for lead classification",
                     classification=classification)
      else:
        # Fall back to rule-based classification if Marvin is not configured
        classification, reasoning, owner_team = classify_lead(input_data)
        logfire.info("Using rule-based classification (Marvin not enabled)",
                     classification=classification)

      # Set pipeline based on classification
      if classification == "Services":
        assigned_pipeline = "Stahla Services Pipeline"
      elif classification == "Logistics":
        assigned_pipeline = "Stahla Logistics Pipeline"
      elif classification == "Leads":
        assigned_pipeline = "Stahla Leads Pipeline"
      else:
        assigned_pipeline = None  # No pipeline for Disqualify

      # Calculate confidence score (could be more sophisticated)
      confidence = 0.95  # High confidence for most cases
      requires_review = False

      # Lower confidence if key fields are missing
      if not input_data.intended_use:
        confidence -= 0.15
        requires_review = True
      if not input_data.product_interest:
        confidence -= 0.15
        requires_review = True
      if not input_data.required_stalls:
        confidence -= 0.05
      if not input_data.duration_days:
        confidence -= 0.05
      if input_data.is_local is None:
        confidence -= 0.05

      # Estimate deal value
      estimated_value = self._estimate_deal_value(input_data)

      # Store additional metadata
      metadata = {
          "assigned_owner_team": owner_team,
          "estimated_value": estimated_value,
          "is_local": input_data.is_local,
          "intended_use": input_data.intended_use,
          "has_complete_info": confidence > 0.8
      }

      # Prepare output
      output = ClassificationOutput(
          lead_type=classification,
          reasoning=reasoning,
          confidence=confidence,
          routing_suggestion=assigned_pipeline,
          requires_human_review=requires_review,
          metadata=metadata
      )

    except Exception as e:
      logfire.error("Error during classification.", exc_info=True,
                    input_data=input_data.model_dump(exclude={"raw_data"}))
      output = ClassificationOutput(
          lead_type="Leads",  # Default to Leads on error for human review
          reasoning=f"Error during classification: {str(e)}",
          confidence=0.3,  # Low confidence when error occurs
          requires_human_review=True,
          metadata={"error": str(e), "error_type": type(e).__name__}
      )

    logfire.info("Classification complete.",
                 classification=output.lead_type,
                 reasoning=output.reasoning,
                 confidence=output.confidence)

    return ClassificationResult(status="success", classification=output)


# Create a singleton instance of the manager
classification_manager = ClassificationManager()
