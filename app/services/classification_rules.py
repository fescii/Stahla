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

def classify_lead(input_data: ClassificationInput) -> Tuple[LeadClassificationType, str, str]:
	"""
	Classifies a lead based on the rules defined in the PRD.
	Returns the classification, reasoning, and suggested owner team.
	"""
	logfire.debug("Applying rule-based classification", input_data=input_data.model_dump(exclude={"raw_data"}))

	# --- Input Data Extraction and Defaults ---
	intended_use = input_data.intended_use
	product_interest = [p.lower() for p in input_data.product_interest] if input_data.product_interest else []
	# Safely get numeric values, defaulting to 0 or appropriate value if None or invalid
	try:
		stalls = int(input_data.required_stalls) if input_data.required_stalls is not None else 0
	except (ValueError, TypeError):
		stalls = 0
		logfire.warn("Invalid or missing required_stalls, defaulting to 0.", input_stalls=input_data.required_stalls)

	try:
		duration = int(input_data.duration_days) if input_data.duration_days is not None else 0
	except (ValueError, TypeError):
		duration = 0
		logfire.warn("Invalid or missing duration_days, defaulting to 0.", input_duration=input_data.duration_days)

	is_local = input_data.is_local # Assumes this is determined beforehand
	location_desc = input_data.event_location_description

	# Determine primary product type for easier rule matching
	is_trailer = any("trailer" in p for p in product_interest)
	is_porta_potty = any("portable toilet" in p or "porta potty" in p for p in product_interest)
	is_handwashing = any("handwashing" in p or "hand wash" in p for p in product_interest)

	reasoning = "Initial assessment based on input data."
	owner_team = "Stahla Services Sales Team" # Default team

	# --- Rule Implementation based on PRD --- #

	# Rule: Event / Porta Potty
	if intended_use == "Small Event" and (is_porta_potty or is_handwashing) and not is_trailer:
		if stalls < 20 and duration < 5:
			reasoning = "Small Event, Porta Potty/Handwash only, <20 stalls, <5 days duration."
			return "Services", reasoning, owner_team # Handled by Services

	# Rule: Construction / Porta Potty
	if intended_use == "Construction" and (is_porta_potty or is_handwashing) and not is_trailer:
		if stalls < 20 and duration >= 5:
			reasoning = "Construction, Porta Potty/Handwash only, <20 stalls, >=5 days duration."
			# Decide if local/non-local matters for porta potty construction
			owner_team = "Stahla Services Sales Team" if is_local else "Stahla Logistics Sales Team"
			return "Services" if is_local else "Logistics", reasoning, owner_team

	# Rule: Small Event / Trailer / Local
	if intended_use == "Small Event" and is_trailer:
		if stalls < 8 and duration > 5 and is_local:
			reasoning = "Small Event, Trailer, <8 stalls, >5 days duration, Local."
			owner_team = "Stahla Leads Team" # Sent to Leads per Path A logic (PC)
			return "Leads", reasoning, owner_team

	# Rule: Small Event / Trailer / Not Local
	if intended_use == "Small Event" and is_trailer:
		if stalls < 8 and duration > 5 and not is_local:
			reasoning = "Small Event, Trailer, <8 stalls, >5 days duration, Not Local."
			owner_team = "Stahla Services Sales Team" # Sent to Services per Path A logic (PA)
			return "Services", reasoning, owner_team

	# Rule: Large Event / Trailer / Local
	if intended_use == "Large Event":
		if (is_trailer and stalls >= 7) or (is_porta_potty and stalls >= 20):
			if duration > 5 and is_local:
				reasoning = "Large Event, High Capacity (Trailer >=7 or Porta >=20), >5 days, Local."
				owner_team = "Stahla Services Sales Team" # PA
				return "Services", reasoning, owner_team

	# Rule: Large Event / Trailer / Not Local
	if intended_use == "Large Event":
		if (is_trailer and stalls >= 7) or (is_porta_potty and stalls >= 20):
			if duration > 5 and not is_local:
				reasoning = "Large Event, High Capacity (Trailer >=7 or Porta >=20), >5 days, Not Local."
				owner_team = "Stahla Logistics Sales Team" # PB
				return "Logistics", reasoning, owner_team

	# Rule: Disaster Relief / Trailer / Local
	if intended_use == "Disaster Relief":
		if is_trailer or (is_porta_potty and stalls >= 20):
			if duration < 180 and is_local:
				reasoning = "Disaster Relief, High Capacity, <180 days, Local."
				owner_team = "Stahla Services Sales Team" # PA
				return "Services", reasoning, owner_team

	# Rule: Disaster Relief / Trailer / Not Local
	if intended_use == "Disaster Relief":
		if is_trailer: # PRD only mentions trailer for non-local disaster
			if duration < 180 and not is_local:
				reasoning = "Disaster Relief, Trailer, <180 days, Not Local."
				owner_team = "Stahla Logistics Sales Team" # PB
				return "Logistics", reasoning, owner_team

	# Rule: Construction / Company Trailer / Local
	if intended_use == "Construction" and is_trailer:
		if is_local:
			reasoning = "Construction, Trailer, Local."
			owner_team = "Stahla Services Sales Team" # PA
			return "Services", reasoning, owner_team

	# Rule: Construction / Company Trailer / Not Local
	if intended_use == "Construction" and is_trailer:
		if not is_local:
			reasoning = "Construction, Trailer, Not Local."
			owner_team = "Stahla Logistics Sales Team" # PB
			return "Logistics", reasoning, owner_team

	# Rule: Facility / Trailer / Local
	if intended_use == "Facility" and is_trailer:
		if is_local:
			reasoning = "Facility, Trailer, Local."
			owner_team = "Stahla Services Sales Team" # PA
			return "Services", reasoning, owner_team

	# Rule: Facility / Trailer / Not Local
	if intended_use == "Facility" and is_trailer:
		if not is_local:
			reasoning = "Facility, Trailer, Not Local."
			owner_team = "Stahla Logistics Sales Team" # PB
			return "Logistics", reasoning, owner_team

	# --- Fallback / Disqualification --- #
	# If none of the specific rules match, consider it for Leads or Disqualify
	# Basic disqualification: Very small request, unclear info
	if stalls < 1 and not is_trailer:
		reasoning = "Insufficient information or very small scale (stalls < 1, no trailer). Considered for disqualification."
		return "Disqualify", reasoning, "None"

	# Default to Leads if no other rule fits but seems potentially valid
	reasoning = "Lead does not fit standard Services/Logistics criteria based on rules. Forwarding to Leads."
	owner_team = "Stahla Leads Team"
	logfire.info("Rule-based classification defaulted to Leads.", final_reasoning=reasoning)
	return "Leads", reasoning, owner_team
