import time
import json  # Import json module
import logging
from typing import Optional, Dict, Any, Tuple, List

from fastapi import Request, Response, BackgroundTasks
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse
import uuid

# Import background task functions and Redis service dependency
from app.services.redis.redis import RedisService, get_redis_service
from app.services.dash.background import log_request_response_bg

logger = logging.getLogger(__name__)

# Define which paths to log (e.g., only API v1 webhooks)
PATHS_TO_LOG = ["/api/v1/webhooks/quote", "/api/v1/webhooks/location_lookup"]
# Add other paths as needed

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.monotonic()
        request_id = str(uuid.uuid4()) # Generate unique ID for this request
        
        # Check if the path should be logged
        should_log = any(request.url.path.startswith(p) for p in PATHS_TO_LOG)
        
        response = None
        response_body = b""
        status_code = 500 # Default to error
        response_payload_dict = None
        request_payload_dict = None

        try:
            # Try reading request body (handle potential errors)
            try:
                request_body = await request.body()
                if request_body:
                    request_payload_dict = await request.json() # Assumes JSON body
            except Exception:
                request_body = b"<Could not read body>"
                request_payload_dict = {"error": "Could not read request body"}
                logger.warning(f"Could not read request body for {request.method} {request.url.path}")
            
            # Re-stream the body for the actual endpoint handler
            request.state.body = request_body 
            async def receive(): return {"type": "http.request", "body": request_body, "more_body": False}
            request = Request(request.scope, receive=receive, send=request._send)

            # Process the request
            response = await call_next(request)
            status_code = response.status_code

            # Read response body for logging
            if isinstance(response, StreamingResponse):
                async for chunk in response.body_iterator:
                    response_body += chunk
                # Re-create iterator for actual response sending
                response.body_iterator = (chunk async for chunk in [response_body])
            else:
                 # For non-streaming responses (like JSONResponse)
                 # Accessing response.body directly consumes it. We need to read it
                 # and then replace it for the client.
                 # This part is tricky and might need refinement based on response types.
                 # A common pattern is to have a helper that reads and replaces.
                 # For now, let's assume JSONResponse and try to parse.
                 try:
                     # This might fail if not JSON or already consumed
                     if hasattr(response, 'body'):
                         response_body = getattr(response, 'body')
                         if isinstance(response_body, bytes):
                             response_payload_dict = json.loads(response_body.decode('utf-8'))
                         else:
                             response_payload_dict = response_body # Assume already dict/serializable
                     else: # Fallback if .body isn't available/standard
                          response_payload_dict = {"detail": "<Response body not logged>"}
                 except Exception as e:
                     logger.warning(f"Could not parse response body for logging: {e}")
                     response_payload_dict = {"detail": "<Response body parsing error>"}

        except Exception as e:
            logger.error(f"Error during request processing or logging middleware: {e}", exc_info=True)
            response_payload_dict = {"detail": f"Middleware Error: {e}"} # Log middleware error
            # Ensure a response is sent if call_next failed catastrophically
            if response is None:
                 # Log error and return a generic 500 response
                logger.error(f"Middleware error processing request {request_id}: {e}", exc_info=True)
                # Ensure Response is imported from starlette.responses
                response = Response(content=json.dumps({"detail": "Internal Server Error in Middleware"}), status_code=500, media_type="application/json")
                # Log the error response details
                logger.error(f"Response details: {response.status_code} {response_body}")
                return response  # Return the response object

        finally:
            if should_log:
                end_time = time.monotonic()
                latency_ms = (end_time - start_time) * 1000
                
                # Use BackgroundTasks to log asynchronously
                background_tasks = BackgroundTasks()
                # Get RedisService instance (requires dependency injection or global access)
                # This is tricky in middleware. A common pattern is to attach
                # services to app.state or use a dependency injector.
                # For simplicity, let's assume get_redis_service works globally (not ideal).
                try:
                    redis_service = await get_redis_service()
                    background_tasks.add_task(
                        log_request_response_bg,
                        redis=redis_service,
                        endpoint=request.url.path,
                        request_id=request_id,
                        request_payload=request_payload_dict,
                        response_payload=response_payload_dict,
                        status_code=status_code,
                        latency_ms=latency_ms
                    )
                    # Schedule the background tasks to run after response
                    response.background = background_tasks
                except Exception as e:
                     logger.error(f"Failed to get RedisService or add logging task in middleware: {e}")

        return response
