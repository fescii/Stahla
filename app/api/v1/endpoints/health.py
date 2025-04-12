# app/api/v1/endpoints/health.py

from fastapi import APIRouter
import logfire

# Create an APIRouter instance for health check endpoints
router = APIRouter()


@router.get("", summary="System Health Check")
async def health_check():
	"""
		Provides a basic health check endpoint.
		Confirms the API service is running and responsive.
		Future enhancements could include checking database connections
		or external service availability.
	"""
	logfire.info("Health check endpoint accessed.")
	# In the future, add checks for dependencies (DB, external APIs, etc.)
	# For now, just return a simple status indicating the API is up.
	return {"status": "ok", "message": "API is healthy"}
