import time
import json  # Import json module
import logging
from fastapi import Request, Response, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import uuid
import logfire

# Import background task functions and Redis service dependency
from app.services.redis.factory import get_redis_service
from app.services.background.request import log_request_response_bg

# Import GenericResponse for error formatting
from app.models.common import GenericResponse

# Import templating
from app.core.templating import templates

logger = logging.getLogger(__name__)

# Define which paths to log (e.g., only API v1 webhooks)
PATHS_TO_LOG = ["/api/v1/webhooks/quote", "/api/v1/webhooks/location_lookup"]
# Add other paths as needed

# --- Global Exception Handler Functions ---
# These functions should be registered in your main FastAPI app instance (e.g., in app/main.py)


async def http_exception_handler(request: Request, exc: HTTPException):
  """Handles FastAPI HTTPExceptions and returns a GenericResponse."""
  logfire.warn(
      f"HTTPException caught: {exc.status_code} {exc.detail}",
      exc_info=exc,
      request_path=str(request.url),
      request_method=request.method
  )
  return JSONResponse(
      status_code=exc.status_code,
      content=GenericResponse.error(
          message=exc.detail, status_code=exc.status_code).model_dump(exclude_none=True),
  )


async def not_found_exception_handler(request: Request, exc: StarletteHTTPException):
  """
  Handles 404 errors:
  - Returns GenericResponse for API routes (starting with /api/)
  - Returns 404.html template for other routes
  """
  logfire.warn(
      f"404 Not Found: {request.url.path}",
      request_path=str(request.url),
      request_method=request.method
  )

  # Check if the request is for an API endpoint
  if request.url.path.startswith("/api/"):
    return JSONResponse(
        status_code=404,
        content=GenericResponse.error(
            message="API endpoint not found",
            details={"path": request.url.path, "method": request.method},
            status_code=404
        ).model_dump(exclude_none=True),
    )

  # For non-API routes, return HTML template
  return templates.TemplateResponse(
      "404.html",
      {
          "request": request,
          "url": str(request.url),
          "title": "Page Not Found - Stahla AI SDR"
      },
      status_code=404
  )


async def server_error_exception_handler(request: Request, exc: Exception):
  """
  Handles 5xx server errors:
  - Returns GenericResponse for API routes (starting with /api/)
  - Returns 50x.html template for other routes
  """
  status_code = getattr(exc, 'status_code', 500)

  # Only handle 5xx errors (500-599)
  if not (500 <= status_code <= 599):
    # Let other handlers deal with non-5xx errors
    raise exc

  logfire.error(
      f"Server Error ({status_code}): {request.url.path}",
      exc_info=exc,
      request_path=str(request.url),
      request_method=request.method
  )

  # Check if the request is for an API endpoint
  if request.url.path.startswith("/api/"):
    return JSONResponse(
        status_code=status_code,
        content=GenericResponse.error(
            message="Internal server error occurred",
            details={"path": request.url.path, "method": request.method},
            status_code=status_code
        ).model_dump(exclude_none=True),
    )

  # For non-API routes, return HTML template
  return templates.TemplateResponse(
      "50x.html",
      {
          "request": request,
          "url": str(request.url),
          "status_code": status_code,
          "title": "Server Error - Stahla AI SDR"
      },
      status_code=status_code
  )


async def generic_exception_handler(request: Request, exc: Exception):
  """Handles any other unhandled exceptions and returns a GenericResponse."""
  logfire.error(
      f"Unhandled exception caught: {exc}",
      exc_info=exc,
      request_path=str(request.url),
      request_method=request.method
  )
  return JSONResponse(
      status_code=500,
      content=GenericResponse.error(
          message="An unexpected internal server error occurred.",
          details={"error_type": type(exc).__name__},
          status_code=500
      ).model_dump(exclude_none=True),
  )

# --- End Global Exception Handler Functions ---


class LoggingMiddleware(BaseHTTPMiddleware):
  async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
    start_time = time.monotonic()
    request_id = str(uuid.uuid4())  # Generate unique ID for this request

    # Check if the path should be logged
    should_log = any(request.url.path.startswith(p) for p in PATHS_TO_LOG)

    response = None
    response_body = b""
    status_code = 500  # Default to error
    response_payload_dict = None
    request_payload_dict = None

    try:
      # Try reading request body (handle potential errors)
      try:
        request_body_bytes = await request.body()
        if request_body_bytes:
          # Check if this is a multipart/form-data request (file upload)
          content_type = request.headers.get('content-type', '')
          if content_type.startswith('multipart/form-data'):
            # Don't try to decode binary file data as UTF-8
            request_payload_dict = {
                "multipart_form_data": f"<binary data {len(request_body_bytes)} bytes>"}
          else:
            # Attempt to parse as JSON, fallback if not JSON or empty
            try:
              request_payload_dict = json.loads(
                  request_body_bytes.decode('utf-8'))
            except json.JSONDecodeError:
              request_payload_dict = {
                  "raw_body": request_body_bytes.decode('utf-8', errors='replace')}
              logger.info(
                  f"Request body for {request.method} {request.url.path} is not valid JSON.")
        else:
          request_body_bytes = b""
          request_payload_dict = None  # No body
      except Exception as e:
        logger.warning(
            f"Could not read request body for {request.method} {request.url.path}: {e}")
        request_body_bytes = b"<Could not read body>"
        request_payload_dict = {"error": "Could not read request body"}

      # Re-stream the body for the actual endpoint handler
      # The original request object is mutated by `await request.body()`
      # We need to provide a new `receive` callable that will yield the already read body.
      async def receive():
        return {"type": "http.request", "body": request_body_bytes, "more_body": False}

      # Create a new Request object with the captured body to pass to call_next
      # request.scope, request._send are parts of the original request we need to preserve.
      scoped_request = Request(
          request.scope, receive=receive, send=request._send)

      # Process the request
      response = await call_next(scoped_request)
      status_code = response.status_code

      # Read response body for logging
      if isinstance(response, StreamingResponse):
        # This part is tricky for true streaming responses as consuming the iterator here
        # means the client won't get it. For logging, you might only log a portion
        # or metadata about the stream.
        # For now, let's assume we want to log the full body if possible, then reconstruct.
        async for chunk in response.body_iterator:
          response_body += chunk  # type: ignore
        # Re-create iterator for actual response sending
        # This makes a new generator that yields the already collected body bytes.

        async def new_body_iterator():
          yield response_body
        response.body_iterator = new_body_iterator()
        try:
          response_payload_dict = json.loads(response_body.decode('utf-8'))
        except json.JSONDecodeError:
          response_payload_dict = {"detail": "<Non-JSON streaming response>"}

      elif isinstance(response, JSONResponse):
        # For JSONResponse, response.body is already bytes
        response_body = response.body
        try:
          response_payload_dict = json.loads(
              bytes(response_body).decode('utf-8'))  # type: ignore
        except json.JSONDecodeError:
          # type: ignore
          logger.warning(
              f"Could not parse JSONResponse body for logging: {bytes(response_body).decode('utf-8', errors='replace')}")
          response_payload_dict = {"detail": "<Malformed JSONResponse body>"}
      elif hasattr(response, 'body'):  # For other Response types that might have a .body attribute
        response_body = getattr(response, 'body', b'')
        if isinstance(response_body, bytes):
          try:
            response_payload_dict = json.loads(response_body.decode('utf-8'))
          except json.JSONDecodeError:
            response_payload_dict = {"detail": "<Non-JSON response body>"}
        # If body is not bytes, try to use it directly (e.g. if it's already a dict)
        else:
          response_payload_dict = response_body
      else:
        response_payload_dict = {
            "detail": "<Response body not logged or not available>"}

    except HTTPException as http_exc:  # Explicitly catch HTTPExceptions to ensure they propagate
      status_code = http_exc.status_code
      response_payload_dict = GenericResponse.error(
          message=http_exc.detail, status_code=status_code).model_dump(exclude_none=True)
      # Log the HTTPException details
      logfire.warn(
          f"HTTPException in LoggingMiddleware dispatch: {http_exc.status_code} {http_exc.detail}",
          request_id=request_id,
          path=str(request.url.path),
          method=request.method
      )
      # Re-raise the exception so FastAPI's (or our custom) handler can process it
      # Or, if we want this middleware to *always* return a response, construct one here:
      # response = JSONResponse(
      #     status_code=status_code,
      #     content=response_payload_dict
      # )
      raise  # Re-raise to be handled by FastAPI's error handling / custom exception handlers

    except Exception as e:
      status_code = 500  # Ensure status_code is set for catastrophic errors
      logger.error(
          f"Error during request processing or logging middleware (request_id: {request_id}): {e}", exc_info=True)
      response_payload_dict = GenericResponse.error(
          message="Internal Server Error in Middleware",
          details={"error_type": type(e).__name__},
          status_code=status_code
      ).model_dump(exclude_none=True)

      # If call_next failed and response is None, create a generic 500 response
      if response is None:
        response = JSONResponse(
            status_code=status_code,
            content=response_payload_dict
        )
      # Else, the error might have occurred after call_next but during response processing.
      # In this case, response object exists but might be in an inconsistent state.
      # We will log what we have and let the finally block handle logging.

    finally:
      if should_log:
        end_time = time.monotonic()
        latency_ms = (end_time - start_time) * 1000

        # Create a new BackgroundTasks instance if one doesn't exist
        current_background_tasks: BackgroundTasks = BackgroundTasks()
        if response and hasattr(response, 'background') and response.background is not None:
            # Use the existing background tasks if available
          current_background_tasks = response.background  # type: ignore

        try:
          # Get instrumented Redis service for better monitoring
          redis_service = await get_redis_service()
          # Add the logging task to the background tasks
          current_background_tasks.add_task(
              log_request_response_bg,
              redis=redis_service,
              endpoint=str(request.url.path),
              request_id=request_id,
              request_payload=request_payload_dict,
              response_payload=response_payload_dict,
              status_code=status_code,
              latency_ms=latency_ms
          )
          if response:
            response.background = current_background_tasks
          else:
            # If response is None due to a catastrophic error before response creation,
            # we can't attach background tasks to it. Log a warning.
            logger.warning(
                f"Response object is None for request_id {request_id}, cannot attach background logging task.")

        except Exception as e:
          logger.error(
              f"Failed to get RedisService or add logging task in middleware (request_id: {request_id}): {e}")
    return response  # type: ignore
# --- End LoggingMiddleware ---
