# app/api/v1/endpoints/health.py

from fastapi import APIRouter, Depends # Updated import
import httpx
from datetime import datetime
import time
import platform
import psutil
import logfire
import os
from typing import Dict, Any

# Import service clients
# from app.services.bland import bland_manager # Removed direct import
from app.services.hubspot import hubspot_manager
# from app.services.mongo.mongo import mongo_service_instance # Removed direct import
from app.core.config import settings
from app.models.common import HealthCheckResponse, GenericResponse # Updated import
from app.core.dependencies import get_bland_manager_dep, get_mongo_service, get_redis_service # Added get_redis_service
from app.services.bland import BlandAIManager # Added import for type hinting
from app.services.mongo.mongo import MongoService # Added import for type hinting
from app.services.redis.redis import RedisService # Added import for type hinting
from redis.exceptions import RedisError # Added import for Redis specific errors

# Create an APIRouter instance for health check endpoints
router = APIRouter()


@router.get("", response_model=GenericResponse[HealthCheckResponse], summary="Perform Health Check", tags=["Health"]) # Updated response_model
async def health_check(
    bland_ai_manager: BlandAIManager = Depends(get_bland_manager_dep), # Added dependency
    mongo_db_service: MongoService = Depends(get_mongo_service), # Added dependency
    redis_service: RedisService = Depends(get_redis_service) # Added dependency
):
    """Checks the health of the application and its dependencies.
    Includes basic system resource usage.
    """
    logfire.info("Performing health check.")
    overall_status = "ok"  # Assume ok initially
    details = {}

    # Check system resources (CPU, Memory)
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        details["system_resources"] = {
            "cpu_usage_percent": cpu_percent,
            "memory_usage_percent": memory_info.percent,
            "memory_total_mb": round(memory_info.total / (1024 * 1024), 2),
            "memory_available_mb": round(memory_info.available / (1024 * 1024), 2)
        }
        logfire.debug("System resource check successful.", details=details["system_resources"])
    except Exception as e:
        logfire.error(f"Health check: Could not retrieve system resources: {e}", exc_info=True)
        overall_status = "error"
        details["system_resources"] = {"status": "error", "message": f"Error retrieving system info: {e}"}

    # Check HubSpot connection
    try:
        hubspot_status_str = await hubspot_manager.check_connection()
        if hubspot_status_str.startswith('ok'):
            details['hubspot_connection'] = {"status": "ok"}
            logfire.debug("Health check: HubSpot connection status: ok")
        else:
            overall_status = 'error'
            error_message = hubspot_status_str.split("error: ", 1)[1] if "error: " in hubspot_status_str else hubspot_status_str
            details['hubspot_connection'] = {"status": "error", "message": error_message}
            logfire.warning(f"Health check: HubSpot connection status: error, Message: {error_message}")
    except Exception as e:
        logfire.error(f'Health check: HubSpot connection error: {str(e)}', exc_info=True)
        overall_status = 'error'
        details['hubspot_connection'] = {"status": "error", "message": str(e)}

    # Check BlandAI connection
    try:
        # Use the injected bland_ai_manager instance
        bland_status_str = await bland_ai_manager.check_connection()
        if bland_status_str.startswith('ok'):
            details['blandai_connection'] = {"status": "ok"}
            logfire.debug("Health check: BlandAI connection status: ok")
        else:
            overall_status = 'error'
            error_message = bland_status_str.split("error: ", 1)[1] if "error: " in bland_status_str else bland_status_str
            details['blandai_connection'] = {"status": "error", "message": error_message}
            logfire.warning(f"Health check: BlandAI connection status: error, Message: {error_message}")
    except AttributeError as e: # Specific catch for the persistent 'BlandAIManager' object has no attribute 'check_connection'
        logfire.error(f'Health check: BlandAI connection error (AttributeError): {str(e)}', exc_info=True)
        overall_status = 'error'
        details['blandai_connection'] = {"status": "error", "message": str(e)}
    except Exception as e:
        logfire.error(f'Health check: BlandAI connection error: {str(e)}', exc_info=True)
        overall_status = 'error'
        details['blandai_connection'] = {"status": "error", "message": str(e)}

    # Check MongoDB connection
    try:
        # Use the injected mongo_db_service instance
        if mongo_db_service is None: # Explicitly check if the instance is None
            # This check might be redundant if Depends guarantees a non-None instance or raises its own error
            raise AttributeError("'NoneType' object has no attribute 'check_connection' (MongoService not initialized via dependency)")
        
        mongo_status_str = await mongo_db_service.check_connection()
        if mongo_status_str.startswith('ok'):
            details['mongodb_connection'] = {"status": "ok"}
            logfire.debug("Health check: MongoDB connection status: ok")
        else:
            overall_status = 'error'
            error_message = mongo_status_str.split("error: ", 1)[1] if "error: " in mongo_status_str else mongo_status_str
            details['mongodb_connection'] = {"status": "error", "message": error_message}
            logfire.warning(f"Health check: MongoDB connection status: error, Message: {error_message}")
    except AttributeError as e: # Catches the NoneType error or if check_connection is missing
        logfire.error(f'Health check: MongoDB connection error (AttributeError - service might not be initialized or method missing): {str(e)}', exc_info=True)
        overall_status = 'error'
        details['mongodb_connection'] = {"status": "error", "message": str(e)}
    except Exception as e:
        logfire.error(f'Health check: MongoDB connection error: {str(e)}', exc_info=True)
        overall_status = 'error'
        details['mongodb_connection'] = {"status": "error", "message": str(e)}

    # Check Redis connection
    redis_client = None  # Initialize redis_client to None
    try:
        redis_client = await redis_service.get_client()
        await redis_client.ping()
        details['redis_connection'] = {"status": "ok"}
        logfire.debug("Health check: Redis connection status: ok")
    except RedisError as e:
        logfire.error(f'Health check: Redis connection error (RedisError): {str(e)}', exc_info=True)
        overall_status = 'error'
        details['redis_connection'] = {"status": "error", "message": f"RedisError: {str(e)}"}
    except Exception as e:
        logfire.error(f'Health check: Redis connection error (General Exception): {str(e)}', exc_info=True)
        overall_status = 'error'
        details['redis_connection'] = {"status": "error", "message": str(e)}
    finally:
        if redis_client:
            await redis_client.close()
            logfire.debug("Health check: Redis client connection closed.")

    # Construct the HealthCheckResponse object that will go into GenericResponse.data
    health_check_data = HealthCheckResponse(status=overall_status, details=details)
    
    logfire.info(f"Health check completed with overall_status: {overall_status}")

    if overall_status == "ok":
        return GenericResponse(success=True, data=health_check_data, status_code=200)
    else:
        return GenericResponse(
            success=False, 
            data=health_check_data, 
            error_message="One or more health checks reported an error.",
            status_code=200 # Health check endpoint itself is working
        )


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
