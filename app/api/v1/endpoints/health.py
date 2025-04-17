# app/api/v1/endpoints/health.py

from fastapi import APIRouter
import httpx
from datetime import datetime
import time
import platform
import psutil
import logfire
import os
from typing import Dict, Any

# Import service clients
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
from app.core.config import settings
from app.models.common import HealthCheckResponse

# Create an APIRouter instance for health check endpoints
router = APIRouter()


@router.get("", response_model=HealthCheckResponse, summary="Perform Health Check", tags=["Health"])
async def health_check():
    """Checks the health of the application and its dependencies.
    Includes basic system resource usage.
    """
    logfire.info("Performing health check.")
    status = "ok"  # Assume ok initially
    details = {}

    # Check system resources (CPU, Memory)
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        details["cpu_usage_percent"] = cpu_percent
        details["memory_usage_percent"] = memory_info.percent
        details["memory_total_mb"] = round(memory_info.total / (1024 * 1024), 2)
        details["memory_available_mb"] = round(memory_info.available / (1024 * 1024), 2)
        logfire.debug("System resource check successful.", details=details)
    except Exception as e:
        logfire.error(f"Health check failed: Could not retrieve system resources: {e}", exc_info=True)
        status = "error"
        details["system_resources"] = f"Error retrieving system info: {e}"

    # TODO: Add checks for external dependencies (e.g., HubSpot, BlandAI, Database) if needed
    # Example: Check HubSpot connection (implement a simple ping or status check in hubspot_manager)
    # try:
    #     hubspot_status = await hubspot_manager.check_connection()
    #     details['hubspot_connection'] = hubspot_status
    #     if hubspot_status != 'ok':
    #         status = 'error'
    # except Exception as e:
    #     logfire.error(f'Health check failed: HubSpot connection error: {e}')
    #     status = 'error'
    #     details['hubspot_connection'] = f'Error: {e}'

    response = HealthCheckResponse(status=status, details=details)
    logfire.info(f"Health check completed with status: {status}")
    return response


def get_environment_info() -> Dict[str, Any]:
	"""Get information about the runtime environment."""
	try:
		return {
			"app_name": settings.PROJECT_NAME,
			"api_version": "v1",
			"environment": os.environ.get("ENVIRONMENT", "development"),
			"email_sending_enabled": settings.EMAIL_SENDING_ENABLED,
			"llm_provider": settings.LLM_PROVIDER
		}
	except Exception as e:
		logfire.error(f"Error getting environment info: {str(e)}", exc_info=True)
		return {"error": str(e)}


@router.get("/ping", summary="Simple Ping Check")
async def ping():
	"""
	A simple endpoint for minimal health checks.
	Returns a 200 OK with "pong" message, useful for load balancers.
	"""
	return {"ping": "pong"}
