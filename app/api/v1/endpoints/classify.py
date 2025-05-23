# app/api/v1/endpoints/classify.py

from fastapi import APIRouter, Body
from typing import Any
import logfire

# Import classification service and models
from app.services.classify.classification import classification_manager
from app.models.classification import ClassificationInput, ClassificationResult
from app.models.common import GenericResponse  # Import GenericResponse

# Create an APIRouter instance for classification endpoints
router = APIRouter()


@router.post(
    "",
    summary="Classify Lead Data",
    response_model=GenericResponse[ClassificationResult],
)
async def classify_lead(lead_data: ClassificationInput = Body(...)):
  """
  Receives lead data and routes it to the classification engine.
  Returns a structured classification result.
  """
  logfire.info("Received classification request.", source=lead_data.source)

  try:
    # Call the actual classification service
    classification_result = await classification_manager.classify_lead_data(
        lead_data
    )

    logfire.info(
        "Classification completed.",
        classification=(
            classification_result.classification.lead_type
            if classification_result.classification
            else "Unknown"
        ),
        status=classification_result.status,
    )

    return GenericResponse(data=classification_result)
  except Exception as e:
    logfire.error(f"Classification failed: {str(e)}", exc_info=True)
    return GenericResponse.error(
        message="Classification failed", details=str(e), status_code=500
    )
