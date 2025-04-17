# filepath: /home/a03/PycharmProjects/Stahla/app/models/common.py
# app/models/common.py

from pydantic import BaseModel
from typing import Dict, Any, Optional

class HealthCheckResponse(BaseModel):
	"""Model for health check response."""
	status: str  # 'ok' or 'error'
	details: Dict[str, Any]  # Detailed information about system resources and dependencies
