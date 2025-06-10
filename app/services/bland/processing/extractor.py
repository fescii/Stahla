"""Transcript data extraction utilities."""

import re
import logfire
from typing import Dict, Any, List
from app.models.bland import BlandProcessingResult


def extract_data_from_transcript(transcripts: List[Dict[str, Any]]) -> BlandProcessingResult:
  """
  Extracts relevant data from the transcript.
  Analyzes the conversation to extract contact information, order details, and other relevant data.
  """
  if not transcripts:
    logfire.warning("No transcript data provided for extraction.")
    # Return with details field properly structured, even if empty
    return BlandProcessingResult(
        status="error",
        message="No transcript data",
        details={"extracted_data": {}},
        summary=None,
        classification=None
    )

  # Concatenate all text from transcripts
  full_text = " ".join(
      t.get("text", "") for t in transcripts if isinstance(t, dict)
  )
  logfire.info(f"Extracted full text from transcript: {full_text[:100]}...")

  # Initialize extracted data dictionary
  extracted_data = {
      "full_transcript": full_text,
      "contact_info": {},
      "order_details": {},
      "location_info": {},
      "service_requirements": {},
      "keywords": []
  }

  # Extract contact information
  contact_patterns = {
      "name": r"(?:name is|I'm|I am|this is) ([A-Z][a-z]+ [A-Z][a-z]+)",
      "email": r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
      "phone": r"(?:phone|number|call me at) .*?(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
      "company": r"(?:company|business|organization) (?:name|called|is) ([A-Za-z0-9 ]+)"
  }

  for field, pattern in contact_patterns.items():
    matches = re.findall(pattern, full_text)
    if matches:
      extracted_data["contact_info"][field] = matches[0]

  # Extract location information
  location_patterns = {
      "address": r"(?:address|location|deliver to) (?:is|at) ([0-9]+ [A-Za-z0-9\s,]+)",
      "city": r"(?:city of|in) ([A-Z][a-z]+ ?[A-Z]?[a-z]*)",
      "state": r"(?:state of|in) ([A-Z][a-z]+)",
      "zip": r"(?:zip|postal code) (\d{5})"
  }

  for field, pattern in location_patterns.items():
    matches = re.findall(pattern, full_text)
    if matches:
      extracted_data["location_info"][field] = matches[0]

  # Extract order details
  order_patterns = {
      "product_type": r"(?:interested in|need|want) (?:a|an|the) ([A-Za-z\s]+(?:Porta Potty|Restroom Trailer|Shower Trailer|Combo Trailer|Specialty Trailer))",
      "event_type": r"(?:for|planning) (?:a|an|the) ([A-Za-z\s]+(?:event|construction|disaster relief|facility))",
      "duration": r"(?:for|need it for|duration of) (\d+) (?:day|days|week|weeks|month|months)",
      "attendees": r"(?:approximately|about|around) (\d+) (?:people|attendees|guests)"
  }

  for field, pattern in order_patterns.items():
    matches = re.findall(pattern, full_text)
    if matches:
      extracted_data["order_details"][field] = matches[0]

  # Extract service requirements
  if "ADA" in full_text or "handicap" in full_text or "wheelchair" in full_text:
    extracted_data["service_requirements"]["ada_required"] = True

  if "power" in full_text:
    extracted_data["service_requirements"]["power_needed"] = "power" in full_text and "no power" not in full_text

  if "water" in full_text:
    extracted_data["service_requirements"]["water_needed"] = "water" in full_text and "no water" not in full_text

  # Extract keywords
  important_keywords = ["urgent", "ASAP", "emergency", "priority", "special request",
                        "discount", "quote", "price", "cost", "budget", "delivery",
                        "pickup", "reschedule", "cancel", "change"]

  extracted_data["keywords"] = [
      keyword for keyword in important_keywords if keyword.lower() in full_text.lower()]

  # Determine intent/classification
  classification = {"intent": "unknown"}

  if "quote" in full_text.lower() or "price" in full_text.lower() or "cost" in full_text.lower():
    classification["intent"] = "pricing_inquiry"
  elif "cancel" in full_text.lower():
    classification["intent"] = "cancellation_request"
  elif "reschedule" in full_text.lower() or "change" in full_text.lower():
    classification["intent"] = "reschedule_request"
  elif "delivery" in full_text.lower() or "pickup" in full_text.lower():
    classification["intent"] = "logistics_inquiry"
  elif any(keyword in extracted_data["order_details"] for keyword in ["product_type", "event_type", "duration"]):
    classification["intent"] = "new_order"

  # Generate a summary
  summary_parts = []
  if extracted_data["contact_info"].get("name"):
    summary_parts.append(
        f"Contact: {extracted_data['contact_info'].get('name')}")

  if extracted_data["order_details"].get("product_type"):
    summary_parts.append(
        f"Product: {extracted_data['order_details'].get('product_type')}")

  if extracted_data["order_details"].get("event_type"):
    summary_parts.append(
        f"For: {extracted_data['order_details'].get('event_type')}")

  if extracted_data["order_details"].get("duration"):
    summary_parts.append(
        f"Duration: {extracted_data['order_details'].get('duration')} days")

  if not summary_parts:
    summary = full_text[:150] + "..."
  else:
    summary = " | ".join(summary_parts)

  # Structure the result according to BlandProcessingResult model
  return BlandProcessingResult(
      status="success",
      message="Data extracted successfully",
      details={"extracted_data": extracted_data},
      summary=summary,
      classification=classification
  )
