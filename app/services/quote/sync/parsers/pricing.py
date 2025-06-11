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
    """Parse product pricing data."""
    if not products_data:
      return {}

    products = {}
    headers = None

    for i, row in enumerate(products_data):
      if i == 0:
        headers = [str(cell).strip().lower() for cell in row]
        continue

      if not headers or len(row) < len(headers):
        continue

      try:
        product_data = {}
        for j, header in enumerate(headers):
          if j < len(row) and row[j] is not None:
            product_data[header] = self._clean_value(row[j])

        product_name = product_data.get("name") or product_data.get("product")
        if product_name:
          products[product_name] = product_data

      except Exception as e:
        logfire.error(f"Error parsing product at row {i+1}: {e}")

    return products

  def _parse_generators(self, generators_data: List[List[Any]]) -> Dict[str, Any]:
    """Parse generator pricing data."""
    if not generators_data:
      return {}

    generators = {}
    headers = None

    for i, row in enumerate(generators_data):
      if i == 0:
        headers = [str(cell).strip().lower() for cell in row]
        continue

      if not headers or len(row) < len(headers):
        continue

      try:
        generator_data = {}
        for j, header in enumerate(headers):
          if j < len(row) and row[j] is not None:
            generator_data[header] = self._clean_value(row[j])

        generator_name = generator_data.get(
            "name") or generator_data.get("generator")
        if generator_name:
          generators[generator_name] = generator_data

      except Exception as e:
        logfire.error(f"Error parsing generator at row {i+1}: {e}")

    return generators

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

  def _clean_currency(self, value: Any) -> Optional[float]:
    """Clean currency strings and return float."""
    if value is None:
      return None
    if isinstance(value, (int, float)):
      return float(value)
    if isinstance(value, str):
      normalized_value = value.strip().lower()
      if normalized_value == "n/a" or not normalized_value:
        return None
      # Remove currency symbols and extra spaces
      import re
      cleaned = re.sub(r'[$,\s]', '', normalized_value)
      try:
        return float(cleaned)
      except ValueError:
        return None
    return None
