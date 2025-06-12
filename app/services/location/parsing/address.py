# filepath: app/services/location/parsing/address.py
import re
from typing import List, Dict, Optional


def parse_and_normalize_address(address: str) -> List[str]:
  """
  Parse and normalize an address to generate multiple variations for Google Maps API.

  For addresses like "47 W 13th St, New York, NY 10011, USA", this generates:
  1. Original address
  2. Without country: "47 W 13th St, New York, NY 10011"
  3. Street + City + State: "47 W 13th St, New York, NY"
  4. City + State + ZIP: "New York, NY 10011"
  5. City + State: "New York, NY"
  6. Just the street address: "47 W 13th St"

  Args:
      address: The input address string

  Returns:
      List of normalized address variations ordered by specificity (most to least)
  """
  if not address or not address.strip():
    return []

  address = address.strip()
  variations = [address]  # Start with original

  # Split by commas and clean up parts
  parts = [part.strip() for part in address.split(',') if part.strip()]

  if len(parts) <= 1:
    return variations

  # Common patterns to identify address components
  zip_pattern = r'\b\d{5}(-\d{4})?\b'  # ZIP codes
  state_pattern = r'\b[A-Z]{2}\b'  # State codes like NY, CA, TX
  country_pattern = r'\b(USA|US|United States|America)\b'

  # Identify components
  has_zip = any(re.search(zip_pattern, part) for part in parts)
  has_state = any(re.search(state_pattern, part) for part in parts)
  has_country = any(re.search(country_pattern, part, re.IGNORECASE)
                    for part in parts)

  # Generate variations based on structure
  if len(parts) >= 2:
    # Without last part (often country or redundant info)
    variation = ', '.join(parts[:-1])
    if variation != address and variation not in variations:
      variations.append(variation)

  if len(parts) >= 3:
    # First part + last two parts (street + city/state info)
    if has_state or has_zip:
      variation = ', '.join([parts[0]] + parts[-2:])
      if variation not in variations:
        variations.append(variation)

    # Without first part (city/state/zip without street)
    variation = ', '.join(parts[1:])
    if variation not in variations:
      variations.append(variation)

  if len(parts) >= 4:
    # Street + City + State (without ZIP and country)
    # Look for the pattern: street, city, state, zip
    if has_state and has_zip:
      # Assume: street, city, state+zip or zip, country
      variation = ', '.join(parts[:3])
      if variation not in variations:
        variations.append(variation)

    # First and last two parts
    variation = ', '.join([parts[0]] + parts[-2:])
    if variation not in variations:
      variations.append(variation)

  # Add just the first part (street address)
  if len(parts) > 1 and parts[0] not in variations:
    variations.append(parts[0])

  # Add city + state combinations
  for i, part in enumerate(parts):
    if re.search(state_pattern, part):  # Found state
      if i > 0:  # Has city before state
        city_state = ', '.join(parts[i-1:i+1])
        if city_state not in variations:
          variations.append(city_state)
      break

  # Remove duplicates while preserving order
  seen = set()
  unique_variations = []
  for var in variations:
    if var not in seen:
      seen.add(var)
      unique_variations.append(var)

  return unique_variations


def extract_location_components(address: str) -> Dict[str, Optional[str]]:
  """
  Extract structured components from an address string.

  Args:
      address: Input address string

  Returns:
      Dictionary with components: street, city, state, zip_code, country
  """
  if not address:
    return {"street": None, "city": None, "state": None, "zip_code": None, "country": None}

  parts = [part.strip() for part in address.split(',') if part.strip()]

  # Initialize components with proper typing
  components: Dict[str, Optional[str]] = {
      "street": None,
      "city": None,
      "state": None,
      "zip_code": None,
      "country": None
  }

  # Patterns
  zip_pattern = r'\b(\d{5}(-\d{4})?)\b'
  state_pattern = r'\b([A-Z]{2})\b'
  country_pattern = r'\b(USA|US|United States|America)\b'

  # Process parts from right to left (more specific to less specific)
  for i, part in enumerate(reversed(parts)):
    reverse_idx = len(parts) - 1 - i

    # Check for country
    if re.search(country_pattern, part, re.IGNORECASE) and not components["country"]:
      components["country"] = part
      continue

    # Check for ZIP code
    zip_match = re.search(zip_pattern, part)
    if zip_match and not components["zip_code"]:
      components["zip_code"] = zip_match.group(1)
      # Remove ZIP from the part for further processing
      part_without_zip = re.sub(zip_pattern, '', part).strip()
      if part_without_zip:
        part = part_without_zip

    # Check for state
    state_match = re.search(state_pattern, part)
    if state_match and not components["state"]:
      components["state"] = state_match.group(1)
      # Remove state from the part for further processing
      part_without_state = re.sub(state_pattern, '', part).strip()
      if part_without_state:
        part = part_without_state

    # Assign remaining parts
    if reverse_idx == 0 and not components["street"]:
      components["street"] = parts[0]  # First part is usually street
    elif part and not components["city"] and reverse_idx > 0:
      components["city"] = part

  return components
