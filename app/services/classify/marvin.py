# app/services/marvin_classification.py

"""
Marvin-based classification engine for Stahla.
This module implements AI-powered lead classification using Marvin.
"""

import marvin
import logfire
from typing import Tuple, Optional, Dict, Any, List
import os
from functools import lru_cache

from app.models.classification import (
    ClassificationInput,
    LeadClassificationType,
    IntendedUseType,
    ProductType,
    ExtractedCallDetails,
    ClassificationOutput # Added import
)
from app.core.config import settings

# Configure Marvin with API keys from settings based on selected provider


def configure_marvin():
  """Configure Marvin based on the selected LLM provider in settings"""
  provider = settings.LLM_PROVIDER.lower()
  config_kwargs = {}

  # Set up configuration based on selected provider
  if provider == "openai":
    if settings.OPENAI_API_KEY:
      config_kwargs["api_key"] = settings.OPENAI_API_KEY
      if settings.MODEL_NAME:
        config_kwargs["openai_model"] = settings.MODEL_NAME
    else:
      logfire.error("OpenAI selected as provider but API key is missing")

  elif provider == "anthropic":
    if settings.ANTHROPIC_API_KEY:
      config_kwargs["anthropic_api_key"] = settings.ANTHROPIC_API_KEY
      if settings.MODEL_NAME:
        config_kwargs["anthropic_model"] = settings.MODEL_NAME
    else:
      logfire.error("Anthropic selected as provider but API key is missing")

  elif provider == "gemini":
    if settings.GEMINI_API_KEY:
      config_kwargs["gemini_api_key"] = settings.GEMINI_API_KEY
      if settings.MODEL_NAME:
        config_kwargs["gemini_model"] = settings.MODEL_NAME
    else:
      logfire.error("Gemini selected as provider but API key is missing")

  # Default to Marvin's default configuration
  if not config_kwargs and settings.MARVIN_API_KEY:
    config_kwargs["api_key"] = settings.MARVIN_API_KEY

  # Apply configuration
  try:
    # Try the newer Marvin configuration method
    logfire.info(f"Configuring Marvin with provider: {provider}")
    marvin.settings.configure(**config_kwargs)
  except AttributeError:
    try:
      # Fall back to direct assignment
      for key, value in config_kwargs.items():
        setattr(marvin.settings, key, value)
    except Exception as e:
      logfire.error(f"Failed to configure Marvin: {str(e)}")
      logfire.error(
          "Check Marvin library compatibility and API key configuration")


# Initialize Marvin ONLY if it's the selected provider
if settings.LLM_PROVIDER == "marvin":
  configure_marvin()
else:
  logfire.info(f"Skipping Marvin configuration as LLM_PROVIDER is set to '{settings.LLM_PROVIDER}'")


@marvin.fn
def classify_lead_with_ai(
    call_summary_or_transcript: str
) -> ExtractedCallDetails: # Return type is correct here
  """
  Analyze the provided call summary or transcript based on the detailed business rules below.
  Extract the relevant details into the ExtractedCallDetails structure.
  Determine the final classification (Services, Logistics, Leads, or Disqualify) and provide reasoning.

  **Input:** A summary or transcript of a sales call.

  **Output:** An ExtractedCallDetails object containing the classification, reasoning, and extracted details.

  **Classification Rules:**

  Event / Porta Potty
      Intended Use = Small Event
      Product Type: Portable Toilet; Handicap Accessible (ADA) Portable Toilet; Handwashing Station
      Stalls < 20
      Duration < 5 days
      -> Services

  Construction / Porta Potty
      Intended Use = ANY (EXCEPT "Large Event" OR "Small Event")
      Product Type: Portable Toilet; Handicap Accessible (ADA) Portable Toilet; Handwashing Station
      Stalls < 20
      Duration: ≥ 5 days
      -> Services (Local) or Logistics (Not Local)

  Small Event / Trailer / Local
      Intended Use = Small Event
      Product Type: Any "specialty trailer"
      Stalls < 8
      Duration: > 5 days
      Location: ≤ 3 hours (drive time) from omaha, ne; denver, co; kansas city, ks
      -> Services

  Small Event / Trailer / Not Local
      Intended Use = Small Event
      Product Type: Any "specialty trailer"
      Stalls < 8
      Duration: > 5 days
      Location: > 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Leads

  Large Event / Trailer / Local
      Intended Use = Large Event
      Product Type= ANY "specialty trailer" AND Stalls ≥ 7
      OR (Product type = "Portable Toilet" AND Stalls ≥ 20)
      Duration > 5 days
      Location ≤ 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Services

  Large Event / Trailer / Not Local
      Intended Use = Large Event
      Product Type= ANY "specialty trailer" AND Stalls ≥ 7
      OR (Product type = "Portable Toilet" AND Stalls ≥ 20)
      Duration > 5 days
      Location > 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Logistics

  Disaster Relief / Trailer / Local
      Intended Use = Disaster Relief
      Product Type= ANY "specialty trailer"
      OR (Product type = "Portable Toilet" AND Stalls ≥ 20)
      Duration < 180 days
      Location ≤ 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Services

  Disaster Relief / Trailer / Not Local
      Intended Use = Disaster Relief
      Product Type= ANY "specialty trailer"
      Duration < 180 days
      Location > 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Logistics

  Construction / Company Trailer / Local
      Intended Use = Construction
      Product Type= ANY "specialty trailer"
      Location ≤ 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Services

  Construction / Company Trailer / Not Local
      Intended Use = Construction
      Product Type= ANY "specialty trailer"
      Location > 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Logistics

  Facility / Trailer / Local
      Intended Use = Facility
      Product Type= ANY "specialty trailer"
      Location ≤ 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Services

  Facility / Trailer / Not Local
      Intended Use = Facility
      Product Type= ANY "specialty trailer"
      Location > 3 hours from omaha, ne; denver, co; kansas city, ks
      -> Logistics

  Disqualify criteria:
  - If information is clearly incorrect or nonsensical
  - If the service requested is not something Stahla provides
  - If the information suggests a scam or spam inquiry
  - If the caller explicitly states they are not interested or it's the wrong number.

  **Extraction Guidelines:**
  - Extract specific details mentioned in the call (event type, location, dates, guest count, stalls, ADA needs, budget, comments, power available, water available).
  - Provide brief reasoning for the chosen classification based *only* on the rules and the call content.
  """
  pass # Marvin implements this


class MarvinClassificationManager:
  """
  Manages the AI-based classification of leads using Marvin.
  Applies the business rules defined in the Marvin AI function.
  """

  @lru_cache(maxsize=32)
  def get_team_members(self, team: str) -> List[str]:
    """
    Return a list of team members for a given team.
    In a production environment, this would fetch from a database or service.
    For now, using hardcoded values as a placeholder.
    """
    teams = {
        "Stahla Leads Team": ["isfescii@gmail.com", "femar.fredrick@gmail.com"],
        "Stahla Services Sales Team": ["femar.fredrick@gmail.com"],
        "Stahla Logistics Sales Team": ["femar.fredrick@gmail.com"],
    }
    return teams.get(team, [])

  def _is_specialty_trailer(self, product_types: List[str]) -> bool:
    """Check if any product is a specialty trailer."""
    specialty_trailers = ["Restroom Trailer", "Shower Trailer", "ADA Trailer"]
    return any(trailer.lower() in product.lower() for product in product_types for trailer in specialty_trailers)

  def _is_porta_potty(self, product_types: List[str]) -> bool:
    """Check if any product is a porta potty type."""
    porta_potty_types = [
        "Portable Toilet", "Handicap Accessible (ADA) Portable Toilet", "Handwashing Station"]
    return any(potty.lower() in product.lower() for product in product_types for potty in porta_potty_types)

  def _enhance_classification_with_rules(
      self,
      input_data: ClassificationInput,
      ai_classification: LeadClassificationType,
      ai_reasoning: str
  ) -> Tuple[LeadClassificationType, str, Optional[str]]:
    """
    Enhance the AI classification with explicit rule checking.
    This adds a layer of rule-based validation on top of the AI decision.

    Returns:
        Tuple of (final_classification, final_reasoning, owner_team)
    """
    intended_use = input_data.intended_use
    product_interest = input_data.product_interest or []
    stalls = input_data.stall_count or 0
    duration_days = input_data.duration_days or 0
    is_local = input_data.is_local or False

    # Determine if products include specialty trailers or porta potties
    has_specialty_trailer = self._is_specialty_trailer(product_interest)
    has_porta_potty = self._is_porta_potty(product_interest)

    # Default values
    rule_classification = ai_classification
    rule_reasoning = f"AI decided {ai_classification}: {ai_reasoning}"
    owner_team = None

    # Apply explicit rules to validate or override AI classification
    # Event / Porta Potty
    if intended_use == "Small Event" and has_porta_potty and stalls < 20 and duration_days < 5:
      rule_classification = "Services"
      rule_reasoning = f"Rule: Event / Porta Potty - {ai_reasoning}"
      owner_team = "Stahla Services Sales Team"

    # Construction / Porta Potty
    elif intended_use and intended_use not in ["Small Event", "Large Event"] and has_porta_potty and stalls < 20 and duration_days >= 5:
      if is_local:
        rule_classification = "Services"
        owner_team = "Stahla Services Sales Team"
      else:
        rule_classification = "Logistics"
        owner_team = "Stahla Logistics Sales Team"
      rule_reasoning = f"Rule: Construction / Porta Potty - {ai_reasoning}"

    # Small Event / Trailer / Local
    elif intended_use == "Small Event" and has_specialty_trailer and stalls < 8 and duration_days > 5 and is_local:
      rule_classification = "Services"
      rule_reasoning = f"Rule: Small Event / Trailer / Local - {ai_reasoning}"
      owner_team = "Stahla Services Sales Team"

    # Small Event / Trailer / Not Local
    elif intended_use == "Small Event" and has_specialty_trailer and stalls < 8 and duration_days > 5 and not is_local:
      rule_classification = "Leads"
      rule_reasoning = f"Rule: Small Event / Trailer / Not Local - {ai_reasoning}"
      owner_team = "Stahla Leads Team"

    # Add fallback cases
    else:
      # If AI classification doesn't match rules or has low confidence
      if rule_classification == "Disqualify":
        # Recommend human review if disqualified
        rule_reasoning = f"Disqualified, but needs review: {ai_reasoning}"
        owner_team = "Stahla Leads Team"  # Default to leads team for manual review
      else:
        # Assign teams based on classification
        if rule_classification == "Services":
          owner_team = "Stahla Services Sales Team"
        elif rule_classification == "Logistics":
          owner_team = "Stahla Logistics Sales Team"
        elif rule_classification == "Leads":
          owner_team = "Stahla Leads Team"

    # Log the classification decision for transparency
    logfire.info(f"Classification enhanced with rules: {rule_classification}",
                 ai_classification=ai_classification,
                 rule_classification=rule_classification,
                 intended_use=intended_use,
                 has_specialty_trailer=has_specialty_trailer,
                 has_porta_potty=has_porta_potty,
                 stalls=stalls,
                 duration_days=duration_days,
                 is_local=is_local)

    return rule_classification, rule_reasoning, owner_team

  async def get_lead_classification(self, input_data: ClassificationInput) -> ClassificationOutput:
    """
    Classify lead using Marvin AI based on call summary/transcript and business rules.

    Args:
        input_data: The classification input data, expected to contain call details
                    in extracted_data (e.g., 'call_summary' or 'full_transcript').

    Returns:
        A ClassificationOutput object containing the results.
    """
    logfire.info("Starting Marvin-based classification using call data")

    # --- Extract Call Summary or Transcript --- 
    call_text = input_data.extracted_data.get("call_summary")
    if not call_text:
        call_text = input_data.extracted_data.get("full_transcript")
    if not call_text:
        if isinstance(input_data.raw_data, dict):
             call_text = input_data.raw_data.get("summary") or input_data.raw_data.get("concatenated_transcript")
    
    if not call_text:
        logfire.error("Could not find call summary or transcript in input_data for Marvin classification.")
        reasoning = "Error: Missing call summary/transcript for classification. Defaulting to Leads."
        # Return a default ClassificationOutput on error
        return ClassificationOutput(lead_type="Leads", reasoning=reasoning, requires_human_review=True)
    # --- End Extraction ---

    try:
      logfire.info("Calling Marvin for classification with call text.")
      extracted_details: ExtractedCallDetails = classify_lead_with_ai(call_summary_or_transcript=call_text)
      
      classification = extracted_details.classification
      reasoning = extracted_details.reasoning or f"Classified as {classification} by Marvin AI based on call summary/transcript."
      
      logfire.info("Marvin classification successful.",
                   classification=classification,
                   extracted_details=extracted_details.model_dump())

      # --- Determine Owner Team --- 
      # Assign owner team based on classification
      owner_team = "None" # Default
      if classification == "Services":
        owner_team = "Stahla Services Sales Team"
      elif classification == "Logistics":
        owner_team = "Stahla Logistics Sales Team"
      elif classification == "Leads":
        owner_team = "Stahla Leads Team"
      else:  # Disqualify or unexpected result
        owner_team = "None" # Default to None or Leads team for review
        if classification != "Disqualify":
            logfire.warn(f"Unexpected classification result from Marvin: {classification}")
            # --- Safer Reasoning Update (Corrected) ---
            base_reasoning = reasoning if reasoning is not None else f"Classified as {classification} by Marvin AI."
            reasoning = base_reasoning + f" (Unexpected result: {classification})"
            # --- End Safer Reasoning Update ---

      # --- Log values before creating ClassificationOutput ---
      logfire.debug("Preparing ClassificationOutput",
                    lead_type_value=classification,
                    reasoning_value=reasoning)
      # --- End Log ---

      # --- Create ClassificationOutput with metadata --- 
      # Temporarily create output without metadata to test serialization
      output = ClassificationOutput(
          lead_type=classification,
          reasoning=reasoning,
          requires_human_review=True # Default to needing review after AI call?
          # metadata=extracted_details.model_dump(exclude_none=True) # Temporarily commented out
      )
      # Add owner team to metadata if determined
      # if owner_team != "None":
      #     # Ensure metadata exists before adding to it
      #     if output.metadata is None: output.metadata = {}
      #     output.metadata["assigned_owner_team"] = owner_team
      # --- End Create ClassificationOutput --- 

      return output

    except Exception as e:
      error_type = type(e).__name__
      logfire.error(f"Error during Marvin classification: {e}",
                    error_type=error_type,
                    exc_info=True,
                    input_text=call_text[:500]
                    )
      reasoning = f"Error during classification: {e}. Defaulting to Leads."
      # Return default ClassificationOutput on error
      return ClassificationOutput(lead_type="Leads", reasoning=reasoning, requires_human_review=True)


# Create a singleton instance of the manager
marvin_classification_manager = MarvinClassificationManager()
