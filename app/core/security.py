import hmac
import hashlib
from typing import Optional

from fastapi import Request, HTTPException, Security, status, Header, Depends, Cookie
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError, EmailStr, BaseModel  # Import BaseModel
import logfire

from app.core.config import settings
from app.models.user import TokenData, UserInDB  # Import user models
from app.services.auth.auth import AuthService, get_auth_service  # Import auth service

# --- API Key Security (Header: Authorization: Bearer <key>) ---

API_KEY_NAME = "Authorization"
api_key_header_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Re-define the get_api_key dependency


async def get_api_key(api_key_header_value: Optional[str] = Security(api_key_header_scheme)):
  """Dependency to validate the simple API key (e.g., for webhooks)."""
  if not settings.PRICING_WEBHOOK_API_KEY:
    logfire.error(
        "Webhook API Key (PRICING_WEBHOOK_API_KEY) is not configured in settings.")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="API Key security is not configured."
    )

  if api_key_header_value is None:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization header missing"
    )

  parts = api_key_header_value.split()
  if len(parts) != 2 or parts[0].lower() != "bearer":
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid authorization header format. Expected 'Bearer <API_KEY>'"
    )

  token = parts[1]
  # Use constant time comparison
  if hmac.compare_digest(token, settings.PRICING_WEBHOOK_API_KEY):
    return token  # Return the valid token
  else:
    logfire.warning(f"Invalid Webhook API Key received.")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid API Key"
    )

# --- HubSpot Webhook Security (X-HubSpot-Signature-v3) ---


async def verify_hubspot_webhook_signature(request: Request, x_hubspot_signature_v3: Optional[str] = Header(None)):
  """Verifies the HubSpot webhook signature using the client secret."""
  if not settings.HUBSPOT_CLIENT_SECRET:
    # logger.warning("HubSpot webhook validation skipped: HUBSPOT_CLIENT_SECRET not set.")
    # return # Bypass if secret not set (consider raising error)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="HubSpot webhook secret not configured.")

  if not x_hubspot_signature_v3:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing X-HubSpot-Signature-v3 header")

  try:
    source_string = request.url.path.encode('utf-8') + await request.body()
    expected_signature = hmac.new(
        settings.HUBSPOT_CLIENT_SECRET.encode('utf-8'),
        source_string,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, x_hubspot_signature_v3):
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                          detail="Invalid HubSpot signature")

    # Signature is valid
    return True
  except Exception as e:
    # logger.error(f"Error verifying HubSpot signature: {e}", exc_info=True)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Error verifying HubSpot signature")

# --- Bland Webhook Security (Placeholder - X-Bland-Signature?) ---
# Bland documentation doesn't explicitly mention webhook signatures as of late 2023.
# Assuming a hypothetical signature mechanism similar to HubSpot or a simple secret header.
# Option 1: Simple Secret Header (e.g., X-Bland-Secret)


async def verify_bland_webhook_secret(x_bland_secret: Optional[str] = Header(None)):
  """Verifies a simple secret passed in the X-Bland-Secret header."""
  if not settings.BLAND_WEBHOOK_SECRET:
    # logger.warning("Bland webhook validation skipped: BLAND_WEBHOOK_SECRET not set.")
    # return # Bypass if secret not set
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Bland webhook secret not configured.")

  if not x_bland_secret:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Missing X-Bland-Secret header")

  if x_bland_secret != settings.BLAND_WEBHOOK_SECRET:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid Bland webhook secret")

  return True

# Option 2: Hypothetical Signature Verification (Adapt if Bland implements this)
# async def verify_bland_webhook_signature(request: Request, x_bland_signature: Optional[str] = Header(None)):
#     if not settings.BLAND_WEBHOOK_SECRET:
#         # ... handle missing secret ...
#     if not x_bland_signature:
#         # ... handle missing header ...
#
#     # --- Replace with Bland's actual signature calculation method ---
#     body = await request.body()
#     # Example: timestamp = request.headers.get('X-Bland-Timestamp')
#     # source_string = f"{timestamp}.{body.decode('utf-8')}".encode('utf-8')
#     # expected_signature = hmac.new(settings.BLAND_WEBHOOK_SECRET.encode('utf-8'), source_string, hashlib.sha256).hexdigest()
#     # --- End Replace ---
#
#     # if not hmac.compare_digest(expected_signature, x_bland_signature):
#     #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Bland signature")
#     return True

# --- Placeholder Dashboard Authentication ---
# Replace this with your actual user model and authentication logic


class User(BaseModel):
  username: str
  is_admin: bool = False
  # Add other relevant user fields (email, roles, etc.)


async def get_dashboard_user() -> User:
  """Placeholder dependency for dashboard user authentication."""
  # In a real app, you would:
  # 1. Extract token (e.g., from Authorization header or cookie).
  # 2. Decode/validate the token.
  # 3. Fetch user details from DB based on token payload.
  # 4. Check user permissions/roles.
  # 5. Raise HTTPException(401/403) if invalid or unauthorized.
  # For now, return a dummy admin user for testing.
  # logger.warning("Using placeholder authentication for dashboard.")
  return User(username="admin", is_admin=True)

# --- End Placeholder ---

# --- JWT Authentication ---

# Define scheme for OpenAPI docs, points to login endpoint
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token", auto_error=False)

# Custom dependency to extract token from multiple locations


async def get_token_from_sources(
    request: Request,
    authorization: Optional[str] = Security(
        api_key_header_scheme),  # Checks Authorization header
    x_access_token_header: Optional[str] = Header(
        None, alias="x-access-token"),
    x_access_token_cookie: Optional[str] = Cookie(None, alias="x-access-token")
) -> Optional[str]:
  """
  Extracts token from 'Authorization: Bearer <token>', 'x-access-token' header, 
  or 'x-access-token' cookie.
  """
  if authorization and authorization.lower().startswith("bearer "):
    # Check Authorization header first (standard)
    token_part = authorization.split(" ", 1)[1]
    if token_part:
      return token_part
  if x_access_token_header:
    return x_access_token_header
  if x_access_token_cookie:
    return x_access_token_cookie
  return None

# Update get_current_user to use the custom token extractor


async def get_current_user(
    token: Optional[str] = Depends(
        get_token_from_sources),  # Use custom dependency
    auth_service: AuthService = Depends(
        get_auth_service)  # Keep auth service dependency
) -> UserInDB:
  """Dependency to get the current user from JWT token found in standard header, custom header, or cookie."""
  credentials_exception = HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Could not validate credentials",
      # Adjust header based on preferred method or remove if multiple are supported
      headers={"WWW-Authenticate": "Bearer"},
  )
  if token is None:
    logfire.warning(
        "No token found in Authorization header, x-access-token header, or x-access-token cookie.")
    raise credentials_exception

  try:
    payload = jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    email: Optional[EmailStr] = payload.get("sub")
    if email is None:
      logfire.warning("JWT token missing 'sub' (email) claim.")
      raise credentials_exception
    token_data = TokenData(email=email, sub=email)
  except JWTError as e:
    logfire.warning(f"JWT Error decoding token: {e}")
    raise credentials_exception
  except ValidationError as e:
    logfire.warning(f"JWT payload validation error: {e}")
    raise credentials_exception

  user = await auth_service.get_user_by_email(email=token_data.email)
  if user is None:
    logfire.warning(
        f"User specified in JWT token not found: {token_data.email}")
    raise credentials_exception
  if not user.is_active:
    logfire.warning(f"Attempt to use token for inactive user: {user.email}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
  return user


async def get_current_active_admin(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
  """Dependency to ensure the user is an active admin."""
  if current_user.role != "admin":
    logfire.warning(
        f"Admin access denied for user: {current_user.email} (Role: {current_user.role})")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not enough permissions")
  return current_user

# Add other role checks if needed (e.g., get_current_active_dev)
