"""
Extra input model definition.
"""

from pydantic import BaseModel, Field


class ExtraInput(BaseModel):
  """Represents an extra item requested with quantity."""

  extra_id: str = Field(
      ...,
      description="Identifier for the extra item (e.g., 'generator_5kw', 'handwash_station').",
  )
  qty: int = Field(..., gt=0,
                   description="Quantity of the extra item needed.")
