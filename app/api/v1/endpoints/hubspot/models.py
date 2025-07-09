# app/api/v1/endpoints/hubspot/models.py

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class SampleContactForm(BaseModel):
  what_service_do_you_need_: Optional[str] = Field(
      None, alias="What service do you need?"
  )

  @field_validator('what_service_do_you_need_')
  @classmethod
  def validate_service_type(cls, v):
    valid_services = [
        "Restroom Trailer",
        "Shower Trailer",
        "Laundry Trailer",
        "Porta Potty",
        "Trailer Repair / Pump Out",
        "Other"
    ]
    if v is not None and v not in valid_services:
      raise ValueError(
          f"Invalid service type. Must be one of: {', '.join(valid_services)}")
    return v

  how_many_portable_toilet_stalls_: Optional[int] = Field(
      None, alias="How Many Portable Toilet Stalls?"
  )
  event_or_job_address: Optional[str] = Field(
      None, alias="Event or Job Address")
  zip: Optional[str] = Field(None, alias="Postal code")
  city: Optional[str] = Field(None, alias="City")
  event_start_date: Optional[str] = Field(
      None, alias="Event start date"
  )  # Keep as string for now
  event_end_date: Optional[str] = Field(
      None, alias="Event end date"
  )  # Keep as string for now
  firstname: str = Field(..., alias="First name")
  lastname: str = Field(..., alias="Last name")
  phone: str = Field(..., alias="Phone number")
  email: EmailStr = Field(..., alias="Email")
  by_submitting_this_form_you_consent_to_receive_texts: Optional[bool] = Field(
      None, alias="I consent to receive texts on the phone number provided"
  )

  model_config = {
      "populate_by_name": True,
      "extra": "ignore",  # Ignore extra fields that might be in a real form submission
  }
