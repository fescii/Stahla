# app/services/quote/sync/parsers/pricing.py

"""
Pricing data parser.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import logfire

logger = logging.getLogger(__name__)


class PricingParser:
  """Handles parsing of pricing data from sheets."""

  def parse_pricing_data(
      self,
      products_data: List[List[Any]],
      generators_data: List[List[Any]],
      delivery_data: List[List[Any]]
  ) -> Dict[str, Any]:
    """
    Parse pricing data from multiple sheet ranges.

    Args:
        products_data: Product pricing data
        generators_data: Generator pricing data
        delivery_data: Delivery cost data

    Returns:
        Structured pricing catalog
    """
    pricing_catalog = {
        "products": self._parse_products(products_data),
        "generators": self._parse_generators(generators_data),
        "delivery": self._parse_delivery(delivery_data),
        "last_updated": datetime.utcnow().isoformat()
    }

    logfire.info("Successfully parsed pricing data")
    return pricing_catalog

  def _parse_products(self, products_data: List[List[Any]]) -> Dict[str, Any]:
    """Parse product pricing data using original header mapping logic."""
    from app.services.quote.utils.constants import PRODUCT_HEADER_MAP, KNOWN_PRODUCT_EXTRAS_HEADERS

    products = {}

    if not products_data or len(products_data) <= 1:
      logfire.warning(
          "No product data or only headers found in products_data.")
      return products

    # Get headers and normalize them
    product_headers = [str(h).strip().lower() for h in products_data[0]]
    product_data_rows = products_data[1:]

    logfire.info(
        f"Parsing {len(product_data_rows)} product rows with headers: {product_headers}")

    for i, row_data in enumerate(product_data_rows):
      if not any(row_data):  # Skip entirely empty rows
        logfire.debug(f"Skipping empty product row {i+2}")
        continue

      product_dict: Dict[str, Any] = {"extras": {}}

      # Map values based on PRODUCT_HEADER_MAP
      for sheet_header, pydantic_field in PRODUCT_HEADER_MAP.items():
        try:
          col_index = product_headers.index(sheet_header)
          raw_value = row_data[col_index] if col_index < len(
              row_data) else None
          # Clean currency for pricing fields, otherwise store raw
          if "rate" in pydantic_field or "weekly" in pydantic_field or "event" in pydantic_field:
            product_dict[pydantic_field] = self._clean_currency(raw_value)
          else:
            product_dict[pydantic_field] = str(
                raw_value).strip() if raw_value is not None else None
        except ValueError:  # Header not found
          logfire.debug(
              f"Header '{sheet_header}' not found in product sheet. Field '{pydantic_field}' will be None.")
          product_dict[pydantic_field] = None
        except IndexError:
          logfire.warning(
              f"Product row {i+2} is shorter than expected. Header '{sheet_header}' (index {col_index}) out of bounds. Field '{pydantic_field}' will be None.")
          product_dict[pydantic_field] = None

      # Default 'name' to 'id' if 'name' wasn't explicitly mapped or is empty
      if not product_dict.get("name") and product_dict.get("id"):
        product_dict["name"] = product_dict["id"]

      # If 'id' is still missing or empty after mapping, skip this product
      if not product_dict.get("id"):
        logfire.warning(
            f"Skipping product row {i+2} due to missing ID (Primary Column).")
        continue

      # Populate 'extras' from known extra service headers
      for extra_header in KNOWN_PRODUCT_EXTRAS_HEADERS:
        try:
          col_index = product_headers.index(extra_header)
          raw_value = row_data[col_index] if col_index < len(
              row_data) else None
          # Extras are also currency values
          product_dict["extras"][extra_header.replace(
              " ", "_")] = self._clean_currency(raw_value)
        except ValueError:
          # It's okay if an extra header isn't present for all products
          pass
        except IndexError:
          logfire.warning(
              f"Product row {i+2} is shorter than expected when looking for extra '{extra_header}'. It will be skipped for this product.")

      product_id = product_dict["id"]
      products[product_id] = product_dict
      logfire.debug(f"Parsed product: {product_id} -> {product_dict}")

    return products

  def _parse_generators(self, generators_data: List[List[Any]]) -> Dict[str, Any]:
    """Parse generator pricing data using original header mapping logic."""
    from app.services.quote.utils.constants import GENERATOR_HEADER_MAP

    generators = {}

    if not generators_data or len(generators_data) <= 1:
      logfire.warning(
          "No generator data or only headers found in generators_data.")
      return generators

    # Get headers and normalize them
    generator_headers = [str(h).strip().lower() for h in generators_data[0]]
    generator_data_rows = generators_data[1:]

    logfire.info(
        f"Parsing {len(generator_data_rows)} generator rows with headers: {generator_headers}")

    for i, row_data in enumerate(generator_data_rows):
      if not any(row_data):  # Skip entirely empty rows
        logfire.debug(f"Skipping empty generator row {i+2}")
        continue

      generator_dict: Dict[str, Any] = {}

      # Map values based on GENERATOR_HEADER_MAP
      for sheet_header, pydantic_field in GENERATOR_HEADER_MAP.items():
        try:
          col_index = generator_headers.index(sheet_header)
          raw_value = row_data[col_index] if col_index < len(
              row_data) else None
          # Apply _clean_currency to all generator rate fields
          if "rate" in pydantic_field:  # Ensures all rate fields are cleaned
            generator_dict[pydantic_field] = self._clean_currency(raw_value)
          else:  # For 'id' and 'name' (which defaults to 'id')
            generator_dict[pydantic_field] = str(
                raw_value).strip() if raw_value is not None else None
        except ValueError:  # Header not found
          logfire.debug(
              f"Header '{sheet_header}' not found in generator sheet. Field '{pydantic_field}' will be None.")
          generator_dict[pydantic_field] = None
        except IndexError:
          logfire.warning(
              f"Generator row {i+2} is shorter than expected. Header '{sheet_header}' (index {col_index}) out of bounds. Field '{pydantic_field}' will be None.")
          generator_dict[pydantic_field] = None

      # Default 'name' to 'id' if 'name' wasn't explicitly mapped or is empty
      if not generator_dict.get("name") and generator_dict.get("id"):
        generator_dict["name"] = generator_dict["id"]

      # If 'id' is still missing or empty after mapping, skip this generator
      if not generator_dict.get("id"):
        logfire.warning(
            f"Skipping generator row {i+2} due to missing ID (Generator Rental).")
        continue

      generator_id = generator_dict["id"]
      generators[generator_id] = generator_dict
      logfire.debug(f"Parsed generator: {generator_id} -> {generator_dict}")

    return generators

  def _clean_currency(self, value: Any) -> Optional[float]:
    """Clean currency strings (from original sync.py)."""
    if value is None:
      return None
    if isinstance(value, (int, float)):
      return float(value)
    if isinstance(value, str):
      normalized_value = value.strip().lower()
      if normalized_value == "n/a" or not normalized_value:  # Handles empty strings and "n/a"
        return None

      # Remove currency symbols and commas
      cleaned_value = value.replace("$", "").replace(",", "").strip()

      if not cleaned_value:  # Handles cases like value being only "$" or ","
        return None
      try:
        return float(cleaned_value)
      except ValueError:
        logfire.warning(
            f"Could not parse currency string to float. Input: '{value}'")
        return None
    # If value is not None, int, float, or str, it's an unexpected type for currency.
    logfire.warning(
        f"Unexpected type for currency cleaning: {type(value)}, value: '{value}'")
    return None

  def _parse_delivery(self, delivery_data: List[List[Any]]) -> Dict[str, Any]:
    """Parse delivery cost data."""
    if not delivery_data:
      return {}

    delivery_config = {}

    for i, row in enumerate(delivery_data):
      if len(row) >= 2:
        key = str(row[0]).strip().lower()
        value = self._clean_value(row[1])
        delivery_config[key] = value

    return delivery_config

  def _clean_value(self, value: Any) -> Any:
    """Clean and convert values from sheet format."""
    if value is None:
      return None

    if isinstance(value, str):
      value = value.strip()

      # Try to convert to number if it looks like one
      if value.replace('.', '').replace('-', '').isdigit():
        try:
          if '.' in value:
            return float(value)
          else:
            return int(value)
        except ValueError:
          pass

      # Handle currency values
      if value.startswith('$'):
        try:
          return float(value[1:].replace(',', ''))
        except ValueError:
          pass

    return value

  def parse_catalog(
      self,
      products_data: List[List[Any]],
      generators_data: List[List[Any]]
  ) -> Dict[str, Any]:
    """
    Parse pricing catalog from products and generators data.

    Args:
        products_data: Raw products data from sheets
        generators_data: Raw generators data from sheets

    Returns:
        Structured pricing catalog
    """
    from ...utils.constants import PRODUCT_HEADER_MAP, GENERATOR_HEADER_MAP, KNOWN_PRODUCT_EXTRAS_HEADERS

    pricing_catalog: Dict[str, Any] = {
        "products": {},
        "generators": {},
        "last_updated": datetime.utcnow().isoformat(),
    }

    # Parse Products
    if products_data and len(products_data) > 1:
      product_headers = [str(h).strip().lower() for h in products_data[0]]
      product_data_rows = products_data[1:]
      logfire.info(f"Parsing {len(product_data_rows)} product rows")

      for i, row_data in enumerate(product_data_rows):
        if not any(row_data):  # Skip empty rows
          continue

        product_dict: Dict[str, Any] = {"extras": {}}

        # Map values based on PRODUCT_HEADER_MAP
        for sheet_header, pydantic_field in PRODUCT_HEADER_MAP.items():
          try:
            col_index = product_headers.index(sheet_header)
            raw_value = row_data[col_index] if col_index < len(
                row_data) else None

            # Clean currency for pricing fields
            if "rate" in pydantic_field or "weekly" in pydantic_field or "event" in pydantic_field:
              product_dict[pydantic_field] = self._clean_currency(raw_value)
            else:
              product_dict[pydantic_field] = str(
                  raw_value).strip() if raw_value is not None else None
          except (ValueError, IndexError):
            product_dict[pydantic_field] = None

        # Default 'name' to 'id' if empty
        if not product_dict.get("name") and product_dict.get("id"):
          product_dict["name"] = product_dict["id"]

        # Skip if no ID
        if not product_dict.get("id"):
          continue

        # Populate extras
        for extra_header in KNOWN_PRODUCT_EXTRAS_HEADERS:
          try:
            col_index = product_headers.index(extra_header)
            raw_value = row_data[col_index] if col_index < len(
                row_data) else None
            product_dict["extras"][extra_header] = self._clean_currency(
                raw_value)
          except (ValueError, IndexError):
            product_dict["extras"][extra_header] = None

        pricing_catalog["products"][product_dict["id"]] = product_dict

    # Parse Generators
    if generators_data and len(generators_data) > 1:
      generator_headers = [str(h).strip().lower() for h in generators_data[0]]
      generator_data_rows = generators_data[1:]
      logfire.info(f"Parsing {len(generator_data_rows)} generator rows")

      for i, row_data in enumerate(generator_data_rows):
        if not any(row_data):  # Skip empty rows
          continue

        generator_dict: Dict[str, Any] = {}

        # Map values based on GENERATOR_HEADER_MAP
        for sheet_header, pydantic_field in GENERATOR_HEADER_MAP.items():
          try:
            col_index = generator_headers.index(sheet_header)
            raw_value = row_data[col_index] if col_index < len(
                row_data) else None

            # Clean currency for pricing fields
            if "rate" in pydantic_field or "weekly" in pydantic_field or "event" in pydantic_field:
              generator_dict[pydantic_field] = self._clean_currency(raw_value)
            else:
              generator_dict[pydantic_field] = str(
                  raw_value).strip() if raw_value is not None else None
          except (ValueError, IndexError):
            generator_dict[pydantic_field] = None

        # Default 'name' to 'id' if empty
        if not generator_dict.get("name") and generator_dict.get("id"):
          generator_dict["name"] = generator_dict["id"]

        # Skip if no ID
        if not generator_dict.get("id"):
          continue

        pricing_catalog["generators"][generator_dict["id"]] = generator_dict

    logfire.info(
        f"Parsed {len(pricing_catalog['products'])} products and {len(pricing_catalog['generators'])} generators")
    return pricing_catalog
