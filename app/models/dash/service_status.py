from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class ServiceStatus(BaseModel):
    """Model for the status of a single external service."""

    service_name: str = Field(..., description="Name of the service")
    status: str = Field(..., description="Status of the service (ok, error, unknown)")
    message: str = Field("", description="Status message or error details")
    timestamp: datetime = Field(..., description="When the status was last checked")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional status details"
    )


class ServicesStatusResponse(BaseModel):
    """Response model for the services status endpoint."""

    services: List[ServiceStatus] = Field(..., description="List of service statuses")
    last_updated: Optional[datetime] = Field(
        None, description="When statuses were last checked"
    )
