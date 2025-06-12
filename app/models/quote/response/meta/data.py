"""
Quote metadata model definition.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


class QuoteMetadata(BaseModel):
  """Metadata about the quote generation process."""

  generated_at: datetime = Field(
      default_factory=datetime.now, description="Timestamp when the quote was generated.")
  valid_until: Optional[datetime] = Field(
      None, description="Timestamp until which the quote is valid.")
  version: str = Field("1.0", description="Version of the quote format.")
  source_system: str = Field(
      "Stahla Pricing API", description="System that generated the quote.")
  calculation_method: str = Field(
      "standard", description="Method used to calculate the quote.")
  data_sources: Dict[str, str] = Field(
      default_factory=dict, description="Sources of data used in the calculation.")
  calculation_time_ms: Optional[int] = Field(
      None, description="Time taken to calculate the quote in milliseconds.")
  warnings: List[str] = Field(
      default_factory=list, description="Any warnings generated during quote calculation.")
