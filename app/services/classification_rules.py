# app/services/classification_rules.py

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
    porta_potty_types = ["Portable Toilet", "Handicap Accessible (ADA) Portable Toilet", "Handwashing Station"]
    return any(potty in product_types for potty in porta_potty_types)

def classify_lead(input_data: ClassificationInput) -> Tuple[LeadClassificationType, str, Optional[str]]:
    """
    Classify a lead based on the detailed business rules.
    
    Args:
        input_data: The classification input data
        
    Returns:
        Tuple containing (classification, reasoning, owner_team)
    """
    # Extract key parameters
    intended_use = input_data.intended_use
    product_interest = input_data.product_interest or []
    stalls = input_data.required_stalls or 0
    duration_days = input_data.duration_days or 0
    
    # Determine locality if not already set
    if input_data.is_local is None:
        is_local = determine_locality_from_description(input_data.event_location_description)
    else:
        is_local = input_data.is_local
        
    classification: LeadClassificationType = "Disqualify"  # Default
    reasoning = "Initial state - no classification rules matched"
    owner_team = None
    
    # -------------------- Event / Porta Potty --------------------
    if intended_use == "Small Event" and is_porta_potty(product_interest) and stalls < 20 and duration_days < 5:
        classification = "Services"
        reasoning = "Event / Porta Potty: Small Event with Portable Toilet, < 20 stalls, < 5 days"
        owner_team = "Stahla Services Sales Team"
    
    # -------------------- Construction / Porta Potty --------------------
    elif (intended_use and intended_use not in ["Small Event", "Large Event"]) and \
         is_porta_potty(product_interest) and stalls < 20 and duration_days >= 5:
        classification = "Services" if is_local else "Logistics"
        reasoning = f"Construction / Porta Potty: {intended_use} with Portable Toilet, < 20 stalls, ≥ 5 days, {'Local' if is_local else 'Not Local'}"
        owner_team = "Stahla Services Sales Team" if is_local else "Stahla Logistics Sales Team"
    
    # -------------------- Small Event / Trailer / Local --------------------
    elif intended_use == "Small Event" and is_specialty_trailer(product_interest) and \
         stalls < 8 and duration_days > 5 and is_local:
        classification = "Services"
        reasoning = "Small Event / Trailer / Local: Small Event with specialty trailer, < 8 stalls, > 5 days, Local"
        owner_team = "Stahla Services Sales Team"
    
    # -------------------- Small Event / Trailer / Not Local --------------------
    elif intended_use == "Small Event" and is_specialty_trailer(product_interest) and \
         stalls < 8 and duration_days > 5 and not is_local:
        classification = "Leads"
        reasoning = "Small Event / Trailer / Not Local: Small Event with specialty trailer, < 8 stalls, > 5 days, Not Local"
        owner_team = "Stahla Leads Team"
    
    # -------------------- Large Event / Trailer / Local --------------------
    elif intended_use == "Large Event" and duration_days > 5 and is_local and \
         ((is_specialty_trailer(product_interest) and stalls >= 7) or \
          (is_porta_potty(product_interest) and stalls >= 20)):
        classification = "Services"
        reasoning = "Large Event / Trailer / Local: Large Event with specialty trailer (≥ 7 stalls) or Portable Toilet (≥ 20 stalls), > 5 days, Local"
        owner_team = "Stahla Services Sales Team"
    
    # -------------------- Large Event / Trailer / Not Local --------------------
    elif intended_use == "Large Event" and duration_days > 5 and not is_local and \
         ((is_specialty_trailer(product_interest) and stalls >= 7) or \
          (is_porta_potty(product_interest) and stalls >= 20)):
        classification = "Logistics"
        reasoning = "Large Event / Trailer / Not Local: Large Event with specialty trailer (≥ 7 stalls) or Portable Toilet (≥ 20 stalls), > 5 days, Not Local"
        owner_team = "Stahla Logistics Sales Team"
    
    # -------------------- Disaster Relief / Trailer / Local --------------------
    elif intended_use == "Disaster Relief" and duration_days < 180 and is_local and \
         (is_specialty_trailer(product_interest) or (is_porta_potty(product_interest) and stalls >= 20)):
        classification = "Services"
        reasoning = "Disaster Relief / Trailer / Local: Disaster Relief with specialty trailer or Portable Toilet (≥ 20 stalls), < 180 days, Local"
        owner_team = "Stahla Services Sales Team"
    
    # -------------------- Disaster Relief / Trailer / Not Local --------------------
    elif intended_use == "Disaster Relief" and duration_days < 180 and not is_local and \
         is_specialty_trailer(product_interest):
        classification = "Logistics"
        reasoning = "Disaster Relief / Trailer / Not Local: Disaster Relief with specialty trailer, < 180 days, Not Local"
        owner_team = "Stahla Logistics Sales Team"
    
    # -------------------- Construction / Company Trailer / Local --------------------
    elif intended_use == "Construction" and is_specialty_trailer(product_interest) and is_local:
        classification = "Services"
        reasoning = "Construction / Company Trailer / Local: Construction with specialty trailer, Local"
        owner_team = "Stahla Services Sales Team"
    
    # -------------------- Construction / Company Trailer / Not Local --------------------
    elif intended_use == "Construction" and is_specialty_trailer(product_interest) and not is_local:
        classification = "Logistics"
        reasoning = "Construction / Company Trailer / Not Local: Construction with specialty trailer, Not Local"
        owner_team = "Stahla Logistics Sales Team"
    
    # -------------------- Facility / Trailer / Local --------------------
    elif intended_use == "Facility" and is_specialty_trailer(product_interest) and is_local:
        classification = "Services"
        reasoning = "Facility / Trailer / Local: Facility with specialty trailer, Local"
        owner_team = "Stahla Services Sales Team"
    
    # -------------------- Facility / Trailer / Not Local --------------------
    elif intended_use == "Facility" and is_specialty_trailer(product_interest) and not is_local:
        classification = "Logistics"
        reasoning = "Facility / Trailer / Not Local: Facility with specialty trailer, Not Local"
        owner_team = "Stahla Logistics Sales Team"
    
    # -------------------- Fallback case --------------------
    else:
        # Send to Services team by default unless clearly not local
        if not intended_use or not product_interest:
            classification = "Leads"
            reasoning = "Incomplete information: Missing intended use or product interest. Sending to Leads team for follow-up."
            owner_team = "Stahla Leads Team"
        else:
            classification = "Services"
            reasoning = f"No specific rule matched. Default routing for {intended_use} with {', '.join(product_interest)}"
            owner_team = "Stahla Services Sales Team"
    
    logfire.info(f"Lead classified as: {classification}", 
                reasoning=reasoning, 
                intended_use=intended_use, 
                product_interest=product_interest,
                stalls=stalls,
                duration_days=duration_days,
                is_local=is_local)
    
    return classification, reasoning, owner_team
