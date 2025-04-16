# app/api/v1/endpoints/health.py

from fastapi import APIRouter, HTTPException, status
import logfire
import httpx
from datetime import datetime
import time
import platform
import psutil
import os
from typing import Dict, Any

# Import service clients
from app.services.bland import bland_manager
from app.services.hubspot import hubspot_manager
from app.core.config import settings

# Create an APIRouter instance for health check endpoints
router = APIRouter()


@router.get("", summary="System Health Check")
async def health_check():
	"""
		Provides a basic health check endpoint.
		Confirms the API service is running and responsive.
		Checks external service availability and system health metrics.
	"""
	logfire.info("Health check endpoint accessed.")
	
	start_time = time.time()
	health_info = {
		"status": "ok",
		"timestamp": datetime.now().isoformat(),
		"uptime": get_uptime(),
		"system_info": get_system_info(),
		"dependencies": await check_external_dependencies(),
		"environment": get_environment_info()
	}
	
	# Set overall status based on dependencies
	if any(not dep.get("healthy", False) for dep in health_info["dependencies"].values()):
		health_info["status"] = "degraded"
	
	# Calculate response time
	health_info["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
	
	return health_info


def get_uptime() -> Dict[str, Any]:
	"""Get system uptime information."""
	try:
		uptime_seconds = time.time() - psutil.boot_time()
		return {
			"system_uptime_seconds": round(uptime_seconds),
			"system_uptime_human": format_uptime(uptime_seconds)
		}
	except Exception as e:
		logfire.error(f"Error getting uptime: {str(e)}", exc_info=True)
		return {"error": str(e)}


def format_uptime(seconds: float) -> str:
	"""Format uptime in a human-readable format."""
	days, remainder = divmod(seconds, 86400)
	hours, remainder = divmod(remainder, 3600)
	minutes, seconds = divmod(remainder, 60)
	
	parts = []
	if days > 0:
		parts.append(f"{int(days)}d")
	if hours > 0:
		parts.append(f"{int(hours)}h")
	if minutes > 0:
		parts.append(f"{int(minutes)}m")
	if seconds > 0 or not parts:
		parts.append(f"{int(seconds)}s")
	
	return " ".join(parts)


def get_system_info() -> Dict[str, Any]:
	"""Get basic system metrics."""
	try:
		return {
			"cpu_usage_percent": psutil.cpu_percent(interval=0.1),
			"memory_used_percent": psutil.virtual_memory().percent,
			"disk_used_percent": psutil.disk_usage('/').percent,
			"python_version": platform.python_version(),
			"platform": platform.platform()
		}
	except Exception as e:
		logfire.error(f"Error getting system info: {str(e)}", exc_info=True)
		return {"error": str(e)}


async def check_external_dependencies() -> Dict[str, Any]:
	"""Check the health of external services."""
	dependencies = {}
	
	# Check HubSpot API
	dependencies["hubspot"] = await check_hubspot_health()
	
	# Check Bland.ai API
	dependencies["bland_ai"] = await check_bland_health()
	
	# Check Marvin AI
	dependencies["marvin"] = check_marvin_health()
	
	return dependencies


async def check_hubspot_health() -> Dict[str, Any]:
	"""Check HubSpot API connectivity."""
	try:
		start_time = time.time()
		# Use a light API endpoint to check connectivity
		result = await hubspot_manager._make_request("GET", "/crm/v3/properties/contact")
		response_time = time.time() - start_time
		
		return {
			"healthy": result.status == "success",
			"response_time_ms": round(response_time * 1000, 2),
			"message": "HubSpot API is responsive" if result.status == "success" else result.message
		}
	except Exception as e:
		logfire.error(f"Error checking HubSpot health: {str(e)}", exc_info=True)
		return {
			"healthy": False,
			"message": f"Error: {str(e)}"
		}


async def check_bland_health() -> Dict[str, Any]:
	"""Check Bland.ai API connectivity."""
	try:
		if not settings.BLAND_API_KEY or settings.BLAND_API_KEY == "YOUR_BLAND_AI_KEY_HERE":
			return {
				"healthy": False,
				"message": "Bland.ai API key not configured"
			}
		
		start_time = time.time()
		# Use a simple endpoint to check connectivity
		result = await bland_manager._make_request("GET", "/health")
		response_time = time.time() - start_time
		
		return {
			"healthy": result.status == "success",
			"response_time_ms": round(response_time * 1000, 2),
			"message": "Bland.ai API is responsive" if result.status == "success" else result.message
		}
	except Exception as e:
		logfire.error(f"Error checking Bland.ai health: {str(e)}", exc_info=True)
		return {
			"healthy": False,
			"message": f"Error: {str(e)}"
		}


def check_marvin_health() -> Dict[str, Any]:
	"""Check Marvin AI configuration."""
	try:
		if not settings.MARVIN_API_KEY:
			return {
				"healthy": False,
				"message": "Marvin API key not configured"
			}
		
		# We can't easily test Marvin connectivity without making an actual API call
		# but we can check that it's configured correctly
		llm_enabled = settings.LLM_PROVIDER.lower() == "marvin" and settings.MARVIN_API_KEY
		
		return {
			"healthy": llm_enabled,
			"message": "Marvin appears to be correctly configured" if llm_enabled else "Marvin is not enabled or not configured correctly"
		}
	except Exception as e:
		logfire.error(f"Error checking Marvin health: {str(e)}", exc_info=True)
		return {
			"healthy": False,
			"message": f"Error: {str(e)}"
		}


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
