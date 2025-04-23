# ---
# CLASSIFICATION RULES FOR STAHLACALLS
#
# IMPORTANT: The canonical source for all call flow, lead type, process, and subflow logic is call.md in the project root.
# All classification rules and logic in this file MUST match the current instructions and flow in call.md.
# If you update call.md, you must update this file to match, and vice versa.
# ---

"""
Classification rules engine for Stahla.
This module implements the specific business rules for lead classification
based on intended use, product type, stalls, duration, and location.
"""

from typing import List, Optional, Tuple, Literal
import logfire

from app.models.classification import (
    ClassificationInput,
    LeadClassificationType,
    IntendedUseType,
    ProductType
)
from app.utils.location import determine_locality_from_description


def is_specialty_trailer(product_types: List[str]) -> bool:
  """
  Determine if the product interest includes any specialty trailer.

  Args:
          product_types: List of product types the customer is interested in

  Returns:
          bool: True if any specialty trailer is included
  """
  specialty_trailers = ["Restroom Trailer", "Shower Trailer", "ADA Trailer"]
  return any(trailer in product_types for trailer in specialty_trailers)


def is_porta_potty(product_types: List[str]) -> bool:
  """
  Determine if the product interest includes porta potties.

  Args:
          product_types: List of product types the customer is interested in

  Returns:
          bool: True if any porta potty type is included
  """
  porta_potty_types = ["Portable Toilet",
                       "Handicap Accessible (ADA) Portable Toilet", "Handwashing Station"]
  return any(potty in product_types for potty in porta_potty_types)


def classify_lead(input_data: ClassificationInput) -> Tuple[LeadClassificationType, str, str]:
    """
    Classifies a lead based on the rules defined in the current call.md script.
    - All lead type, process, and subflow logic must match call.md exactly.
    - Refer to call.md for the latest MAIN FLOW, PATHS, SUBFLOWS, and PROCESS definitions.
    - If you change call.md, update this function to match.
    """
    logfire.debug("Applying rule-based classification",
                  input_data=input_data.model_dump(exclude={"raw_data", "extracted_data"}))

    # --- Input Data Extraction and Defaults ---
    intended_use = input_data.intended_use
    product_interest = [p.lower() for p in input_data.product_interest] if input_data.product_interest else []
    try:
        stalls = int(input_data.stall_count) if input_data.stall_count is not None else 0
    except (ValueError, TypeError):
        stalls = 0
        logfire.warn("Invalid or missing stall_count, defaulting to 0.", input_stalls=input_data.stall_count)
    try:
        duration = int(input_data.duration_days) if input_data.duration_days is not None else 0
    except (ValueError, TypeError):
        duration = 0
        logfire.warn("Invalid or missing duration_days, defaulting to 0.", input_duration=input_data.duration_days)
    is_local = input_data.is_local
    budget = input_data.budget if hasattr(input_data, 'budget') and input_data.budget is not None else 0

    # Product type helpers
    is_trailer = any("trailer" in p for p in product_interest)
    is_porta_potty = any("portable toilet" in p or "porta potty" in p for p in product_interest)
    is_handwashing = any("handwashing" in p or "hand wash" in p for p in product_interest)

    # --- Path A: Lead Type Classification ---
    # Case a: Event | Porta Potty (Process: PA, Subflow: SA)
    if intended_use == "Event" and is_porta_potty and not is_trailer:
        return "Services", "Event | Porta Potty: Subflow SA, Process PA", "Stahla Services Sales Team"

    # Case b: Construction | Porta Potty (Process: PA if local, PB if not, Subflow: SB)
    if intended_use == "Construction" and is_porta_potty and not is_trailer:
        if is_local:
            return "Services", "Construction | Porta Potty: Subflow SB, Process PA", "Stahla Services Sales Team"
        else:
            return "Logistics", "Construction | Porta Potty: Subflow SB, Process PB", "Stahla Logistics Sales Team"

    # Case c: Small Event | Trailer | Local (<$10,000) (Process: PC, Subflow: SA)
    if intended_use == "Small Event" and is_trailer and is_local and budget < 10000:
        return "Leads", "Small Event | Trailer | Local: Subflow SA, Process PC", "Stahla Leads Team"

    # Case d: Small Event | Trailer | Not Local (<$10,000) (Process: PA, Subflow: SA)
    if intended_use == "Small Event" and is_trailer and not is_local and budget < 10000:
        return "Services", "Small Event | Trailer | Not Local: Subflow SA, Process PA", "Stahla Services Sales Team"

    # Case e: Large Event | Trailer | Local (≥$10,000) (Process: PA, Subflow: SA)
    if intended_use == "Large Event" and is_trailer and is_local and budget >= 10000:
        return "Services", "Large Event | Trailer | Local: Subflow SA, Process PA", "Stahla Services Sales Team"

    # Case f: Large Event | Trailer | Not Local (>$10,000) (Process: PB, Subflow: SA)
    if intended_use == "Large Event" and is_trailer and not is_local and budget > 10000:
        return "Logistics", "Large Event | Trailer | Not Local: Subflow SA, Process PB", "Stahla Logistics Sales Team"

    # Case g: Disaster Relief | Trailer | Local (>$10,000) (Process: PA, Subflow: SB)
    if intended_use == "Disaster Relief" and is_trailer and is_local and budget > 10000:
        return "Services", "Disaster Relief | Trailer | Local: Subflow SB, Process PA", "Stahla Services Sales Team"

    # Case h: Disaster Relief | Trailer | Not Local (>$10,000) (Process: PB, Subflow: SB)
    if intended_use == "Disaster Relief" and is_trailer and not is_local and budget > 10000:
        return "Logistics", "Disaster Relief | Trailer | Not Local: Subflow SB, Process PB", "Stahla Logistics Sales Team"

    # Case i: Construction Company | Trailer | Local (>$5,000) (Process: PA, Subflow: SB)
    if intended_use == "Construction" and is_trailer and is_local and budget > 5000:
        return "Services", "Construction Company | Trailer | Local: Subflow SB, Process PA", "Stahla Services Sales Team"

    # Case j: Construction Company | Trailer | Not Local (>$5,000) (Process: PB, Subflow: SB)
    if intended_use == "Construction" and is_trailer and not is_local and budget > 5000:
        return "Logistics", "Construction Company | Trailer | Not Local: Subflow SB, Process PB", "Stahla Logistics Sales Team"

    # Case k: Facility | Trailer | Local (>$10,000) (Process: PA, Subflow: SB)
    if intended_use == "Facility" and is_trailer and is_local and budget > 10000:
        return "Services", "Facility | Trailer | Local: Subflow SB, Process PA", "Stahla Services Sales Team"

    # Case l: Facility | Trailer | Not Local (>$10,000) (Process: PB, Subflow: SB)
    if intended_use == "Facility" and is_trailer and not is_local and budget > 10000:
        return "Logistics", "Facility | Trailer | Not Local: Subflow SB, Process PB", "Stahla Logistics Sales Team"

    # --- Fallbacks and Disqualification ---
    # If outside service area and not a fit for above, assign to Leads (Process PC)
    if not is_local:
        return "Leads", "Outside service area: Process PC", "Stahla Leads Team"

    # Disqualify if insufficient info or very small request
    if stalls < 1 and not is_trailer:
        return "Disqualify", "Insufficient information or very small scale (stalls < 1, no trailer).", "None"

    # Default to Leads if no other rule fits
    return "Leads", "Lead does not fit standard Services/Logistics criteria based on rules. Forwarding to Leads.", "Stahla Leads Team"
