# app/services/marvin_classification.py

"""
Marvin-based classification engine for Stahla.
This module implements AI-powered lead classification using Marvin.
"""

# Configure environment variables early to disable Marvin verbose output
import os
from app.core.config import settings
from app.models.classification import (
    ClassificationInput,
    LeadClassificationType,
    IntendedUseType,
    ProductType,
    ExtractedCallDetails,
    ClassificationOutput  # Added import
)
from functools import lru_cache
import logging
from typing import Tuple, Optional, Dict, Any, List
import logfire
import marvin

# Configure Marvin logging using settings values directly
_log_level = getattr(logging, settings.MARVIN_LOG_LEVEL.upper(), logging.ERROR)

# Disable Marvin's verbose logging immediately upon import
logging.getLogger('marvin').setLevel(_log_level)
logging.getLogger('marvin').propagate = False

# Disable Rich console if it's being used by Marvin (based on MARVIN_VERBOSE setting)
if settings.MARVIN_VERBOSE.lower() == "false":
  try:
    from rich.console import Console
    # Override rich console to reduce verbosity if it's used by Marvin
    original_print = Console.print

    def quiet_print(self, *args, **kwargs):
      # Only print if it's an error or warning
      if kwargs.get('style') in ['red', 'yellow'] or any('error' in str(arg).lower() or 'warning' in str(arg).lower() for arg in args):
        return original_print(self, *args, **kwargs)
      # Suppress other Rich console output
      return None
    Console.print = quiet_print
  except ImportError:
    pass


# Configure Marvin with API keys from settings based on selected provider


def configure_marvin():
  """Configure Marvin based on the selected LLM provider in settings"""
  provider = settings.LLM_PROVIDER.lower() if settings.LLM_PROVIDER else ""
  config_kwargs = {}

  # Suppress Marvin logging by configuring Python logging using settings values
  import logging
  try:
    # Convert settings log level string to logging level
    log_level = getattr(
        logging, settings.MARVIN_LOG_LEVEL.upper(), logging.ERROR)

    # Try to get Marvin's logger and set it to the configured level
    marvin_logger = logging.getLogger('marvin')
    marvin_logger.setLevel(log_level)
    marvin_logger.propagate = False  # Don't propagate to root logger

    # Also try some common Marvin-related logger names
    for logger_name in ['marvin.ai', 'marvin.tools', 'marvin.agents', 'marvin.core']:
      logger = logging.getLogger(logger_name)
      logger.setLevel(log_level)
      logger.propagate = False

  except Exception as e:
    logfire.debug(f"Could not configure Marvin logging settings: {e}")

  # Set up configuration based on selected provider
  if provider == "openai":
    if settings.OPENAI_API_KEY:
      config_kwargs["openai_api_key"] = settings.OPENAI_API_KEY
      if settings.MODEL_NAME:
        # Changed to openai_model_name
        config_kwargs["openai_model_name"] = settings.MODEL_NAME
    else:
      logfire.error(
          "OpenAI selected as provider but OPENAI_API_KEY is missing")

  elif provider == "anthropic":
    if settings.ANTHROPIC_API_KEY:
      config_kwargs["anthropic_api_key"] = settings.ANTHROPIC_API_KEY
      if settings.MODEL_NAME:
        # Changed to anthropic_model_name
        config_kwargs["anthropic_model_name"] = settings.MODEL_NAME
    else:
      logfire.error(
          "Anthropic selected as provider but ANTHROPIC_API_KEY is missing")

  elif provider == "gemini":
    if settings.GEMINI_API_KEY:
      config_kwargs["gemini_api_key"] = settings.GEMINI_API_KEY
      if settings.MODEL_NAME:
        # Changed to gemini_model_name
        config_kwargs["gemini_model_name"] = settings.MODEL_NAME
    else:
      logfire.error(
          "Gemini selected as provider but GEMINI_API_KEY is missing")

  elif provider == "marvin":
    if settings.MARVIN_API_KEY:
      # If LLM_PROVIDER is "marvin", assume MARVIN_API_KEY is picked up from the environment
      # or Marvin handles it internally. Do not pass a generic "api_key".
      logfire.info(
          "LLM_PROVIDER is 'marvin'. Assuming MARVIN_API_KEY is used by Marvin automatically (e.g., from env).")
    else:
      logfire.error(
          "Marvin selected as provider but MARVIN_API_KEY is missing")

  # The old fallback for generic "api_key" is removed as it caused errors.
  # if not config_kwargs and settings.MARVIN_API_KEY:
  #   config_kwargs["api_key"] = settings.MARVIN_API_KEY

  # Apply configuration
  try:
    logfire.info(
        f"Attempting to configure Marvin. Provider: '{provider}'. Config_kwargs to apply: {list(config_kwargs.keys())}")

    if config_kwargs:  # If there are specific keys like openai_api_key
      for key, value in config_kwargs.items():
        # Log safely, especially for API keys
        log_value = f"{str(value)[:5]}..." if isinstance(value, str) and (
            "key" in key.lower() or "token" in key.lower()) else str(value)
        logfire.debug(f"Setting marvin.settings.{key} = {log_value}")
        setattr(marvin.settings, key, value)
      logfire.info(
          f"Marvin configured using direct assignment for keys: {list(config_kwargs.keys())}.")

    elif provider == "marvin" and settings.MARVIN_API_KEY:
      # If provider is "marvin", MARVIN_API_KEY is set, and we generated no config_kwargs for it.
      # Marvin should pick up MARVIN_API_KEY from environment variables automatically.
      logfire.info("LLM_PROVIDER is 'marvin' and MARVIN_API_KEY is set. "
                   "Relying on Marvin to use MARVIN_API_KEY from environment variables.")
      # Added log message
      logfire.info(
          "Marvin configuration presumed complete via environment variables for 'marvin' provider.")
      # No explicit marvin.settings call needed here if it's purely env-based for this case.

    elif provider in ["openai", "anthropic", "gemini"] and not config_kwargs:
      # This case implies the API key for the selected provider was missing (already logged during config_kwargs build).
      logfire.warn(
          f"LLM_PROVIDER is '{provider}' but corresponding API key (and possibly model name) was not found. Marvin not configured with specifics for this provider.")

    elif provider == "marvin" and not settings.MARVIN_API_KEY:
      # Already logged when config_kwargs was being built.
      logfire.warn(
          "Marvin not configured as MARVIN_API_KEY is missing for 'marvin' provider.")

    elif not provider:
      logfire.warn("LLM_PROVIDER is not set. Marvin not configured.")

    else:  # Provider is set, but not one of the explicitly handled ones, and no config_kwargs were generated.
      logfire.warn(f"LLM_PROVIDER is '{provider}', which is not explicitly handled for specific key setup, "
                   "nor is it 'marvin' with a MARVIN_API_KEY. Relying on Marvin's defaults or other env vars if any.")

  except AttributeError as ae:
      # This might catch if marvin.settings itself doesn't exist, or if setattr tries to set a non-existent attribute
      # on a strictly defined settings object that doesn't allow arbitrary attributes.
    logfire.error(
        f"Failed to configure Marvin due to AttributeError: {str(ae)}. This might indicate an issue with marvin.settings structure or an attempt to set an unsupported attribute.")
    logfire.error(
        "Check Marvin library compatibility, expected settings attributes, and API key configuration.")
  except Exception as e:
    logfire.error(
        f"An unexpected error occurred during Marvin configuration: {str(e)}", exc_info=True)


# Initialize Marvin if it's a selected provider that Marvin handles
SUPPORTED_MARVIN_PROVIDERS = ["openai", "anthropic", "gemini", "marvin"]
if settings.LLM_PROVIDER and settings.LLM_PROVIDER.lower() in SUPPORTED_MARVIN_PROVIDERS:
  logfire.info(
      f"LLM_PROVIDER is '{settings.LLM_PROVIDER}', attempting to configure Marvin.")
  configure_marvin()
else:
  logfire.info(
      f"Skipping Marvin configuration as LLM_PROVIDER ('{settings.LLM_PROVIDER}') is not one of {SUPPORTED_MARVIN_PROVIDERS} or not set.")


@marvin.fn
def classify_lead_with_ai(
    call_summary_or_transcript: str
) -> ExtractedCallDetails:  # Return type is correct here
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
  - Extract specific details mentioned in the call: product_interest, service_needed, event_type, location (full address if possible), city, state (2-letter code if possible), postal_code, start_date, end_date, duration_days, guest_count, required_stalls, ada_required, power_available (True/False), water_available (True/False).
  - **IMPORTANT: All extracted date strings (e.g., start_date, end_date, rental_start_date) MUST be formatted as 'YYYY-MM-DD'.**
  - For budget_mentioned: Extract the specific amount mentioned (e.g., '$2500', '$10k') or 'none' if no budget is mentioned or explicitly stated as none. Do not include surrounding text.
  - For comments: Capture any other specific comments, questions, or key details mentioned that aren't covered by other fields.
  - Provide brief reasoning for the chosen classification based *only* on the rules and the call content.
  """
  pass  # Marvin implements this


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
    stalls = input_data.required_stalls or 0
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

    # Large Event / Trailer / Local
    elif intended_use == "Large Event" and has_specialty_trailer and stalls >= 7 and duration_days > 5 and is_local:
      rule_classification = "Services"
      rule_reasoning = f"Rule: Large Event / Trailer / Local - {ai_reasoning}"
      owner_team = "Stahla Services Sales Team"

    # Large Event / Trailer / Not Local
    elif intended_use == "Large Event" and has_specialty_trailer and stalls >= 7 and duration_days > 5 and not is_local:
      rule_classification = "Logistics"
      rule_reasoning = f"Rule: Large Event / Trailer / Not Local - {ai_reasoning}"
      owner_team = "Stahla Logistics Sales Team"

    # Disaster Relief / Trailer / Local
    elif intended_use == "Disaster Relief" and has_specialty_trailer and duration_days < 180 and is_local:
      rule_classification = "Services"
      rule_reasoning = f"Rule: Disaster Relief / Trailer / Local - {ai_reasoning}"
      owner_team = "Stahla Services Sales Team"

    # Disaster Relief / Trailer / Not Local
    elif intended_use == "Disaster Relief" and has_specialty_trailer and duration_days < 180 and not is_local:
      rule_classification = "Logistics"
      rule_reasoning = f"Rule: Disaster Relief / Trailer / Not Local - {ai_reasoning}"
      owner_team = "Stahla Logistics Sales Team"

    # Construction / Company Trailer / Local
    elif intended_use == "Construction" and has_specialty_trailer and is_local:
      rule_classification = "Services"
      rule_reasoning = f"Rule: Construction / Company Trailer / Local - {ai_reasoning}"
      owner_team = "Stahla Services Sales Team"

    # Construction / Company Trailer / Not Local
    elif intended_use == "Construction" and has_specialty_trailer and not is_local:
      rule_classification = "Logistics"
      rule_reasoning = f"Rule: Construction / Company Trailer / Not Local - {ai_reasoning}"
      owner_team = "Stahla Logistics Sales Team"

    # Facility / Trailer / Local
    elif intended_use == "Facility" and has_specialty_trailer and is_local:
      rule_classification = "Services"
      rule_reasoning = f"Rule: Facility / Trailer / Local - {ai_reasoning}"
      owner_team = "Stahla Services Sales Team"

    # Facility / Trailer / Not Local
    elif intended_use == "Facility" and has_specialty_trailer and not is_local:
      rule_classification = "Logistics"
      rule_reasoning = f"Rule: Facility / Trailer / Not Local - {ai_reasoning}"
      owner_team = "Stahla Logistics Sales Team"

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
        call_text = input_data.raw_data.get(
            "summary") or input_data.raw_data.get("concatenated_transcript")

    if not call_text:
      logfire.error(
          "Could not find call summary or transcript in input_data for Marvin classification.")
      reasoning = "Error: Missing call summary/transcript for classification. Defaulting to Leads."
      # Return a default ClassificationOutput on error
      return ClassificationOutput(
          lead_type="Leads",
          reasoning=reasoning,
          requires_human_review=True,
          routing_suggestion="Stahla Leads Team",
          confidence=0.0
      )
    # --- End Extraction ---

    try:
      logfire.info("Calling Marvin for classification with call text.")
      extracted_details: ExtractedCallDetails = classify_lead_with_ai(
          call_summary_or_transcript=call_text)

      classification = extracted_details.classification
      reasoning = extracted_details.reasoning or f"Classified as {classification} by Marvin AI based on call summary/transcript."

      logfire.info("Marvin classification successful.",
                   classification=classification,
                   extracted_details=extracted_details.model_dump())

      # --- Determine Owner Team ---
      # Assign owner team based on classification
      owner_team = "None"  # Default
      if classification == "Services":
        owner_team = "Stahla Services Sales Team"
      elif classification == "Logistics":
        owner_team = "Stahla Logistics Sales Team"
      elif classification == "Leads":
        owner_team = "Stahla Leads Team"
      else:  # Disqualify or unexpected result
        owner_team = "None"  # Default to None or Leads team for review
        if classification != "Disqualify":
          logfire.warn(
              f"Unexpected classification result from Marvin: {classification}")
          # --- Safer Reasoning Update (Corrected) ---
          base_reasoning = reasoning if reasoning is not None else f"Classified as {classification} by Marvin AI."
          reasoning = base_reasoning + \
              f" (Unexpected result: {classification})"
          # --- End Safer Reasoning Update ---

      # --- Log values before creating ClassificationOutput ---
      logfire.debug("Preparing ClassificationOutput",
                    lead_type_value=classification,
                    reasoning_value=reasoning)
      # --- End Log ---

      # --- Create ClassificationOutput with metadata ---
      # Create the final output including the extracted metadata
      output = ClassificationOutput(
          lead_type=classification,
          reasoning=reasoning,
          requires_human_review=True,  # Default to needing review after AI call?
          routing_suggestion=owner_team,
          confidence=0.8,  # Default confidence for AI classification
          metadata=extracted_details.model_dump(
              exclude_none=True)  # Add extracted details to metadata
      )
      # Add owner team to metadata if determined
      if owner_team != "None":
          # Ensure metadata exists before adding to it (it should, as we just created it)
        if output.metadata is None:
          output.metadata = {}
        output.metadata["assigned_owner_team"] = owner_team
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
      return ClassificationOutput(
          lead_type="Leads",
          reasoning=reasoning,
          requires_human_review=True,
          routing_suggestion="Stahla Leads Team",
          confidence=0.0
      )


# Create a singleton instance of the manager
marvin_classification_manager = MarvinClassificationManager()
