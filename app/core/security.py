import hmac
import hashlib
from typing import Optional

from fastapi import Request, HTTPException, Security, status, Header
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel  # Import BaseModel for User model

from app.core.config import settings

# --- API Key Security (Header: Authorization: Bearer <key>) ---

API_KEY_NAME = "Authorization"
api_key_header_scheme = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def verify_api_key(api_key_header: Optional[str] = Security(api_key_header_scheme), expected_key: Optional[str] = None):
    """General purpose API Key validator for 'Authorization: Bearer <key>' header."""
    if expected_key is None:
        # If no key is configured in settings, bypass security (log warning)
        # Consider raising an error instead for better security posture
        # logger.warning("API Key validation skipped: No expected key configured.")
        # return "bypass"
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Security key not configured for this endpoint.")

    if api_key_header is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    parts = api_key_header.split() 
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid authorization header format. Expected 'Bearer <API_KEY>'"
        )
    
    token = parts[1]
    if token == expected_key:
        return token # Return the valid token
    else:
        # logger.warning(f"Invalid API Key received: {token[:5]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )

# Specific dependencies using the general validator

async def verify_pricing_webhook_api_key(api_key: str = Security(verify_api_key, expected_key=settings.PRICING_WEBHOOK_API_KEY)):
    """Dependency to verify the Pricing Webhook API Key."""
    return api_key

async def verify_form_webhook_api_key(api_key: str = Security(verify_api_key, expected_key=settings.FORM_WEBHOOK_API_KEY)):
    """Dependency to verify the Form Webhook API Key."""
    return api_key

# --- HubSpot Webhook Security (X-HubSpot-Signature-v3) ---

async def verify_hubspot_webhook_signature(request: Request, x_hubspot_signature_v3: Optional[str] = Header(None)):
    """Verifies the HubSpot webhook signature using the client secret."""
    if not settings.HUBSPOT_CLIENT_SECRET:
        # logger.warning("HubSpot webhook validation skipped: HUBSPOT_CLIENT_SECRET not set.")
        # return # Bypass if secret not set (consider raising error)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="HubSpot webhook secret not configured.")

    if not x_hubspot_signature_v3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-HubSpot-Signature-v3 header")

    try:
        source_string = request.url.path.encode('utf-8') + await request.body()
        expected_signature = hmac.new(
            settings.HUBSPOT_CLIENT_SECRET.encode('utf-8'),
            source_string,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_hubspot_signature_v3):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid HubSpot signature")
        
        # Signature is valid
        return True
    except Exception as e:
        # logger.error(f"Error verifying HubSpot signature: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error verifying HubSpot signature")

# --- Bland Webhook Security (Placeholder - X-Bland-Signature?) ---
# Bland documentation doesn't explicitly mention webhook signatures as of late 2023.
# Assuming a hypothetical signature mechanism similar to HubSpot or a simple secret header.
# Option 1: Simple Secret Header (e.g., X-Bland-Secret)

async def verify_bland_webhook_secret(x_bland_secret: Optional[str] = Header(None)):
    """Verifies a simple secret passed in the X-Bland-Secret header."""
    if not settings.BLAND_WEBHOOK_SECRET:
        # logger.warning("Bland webhook validation skipped: BLAND_WEBHOOK_SECRET not set.")
        # return # Bypass if secret not set
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Bland webhook secret not configured.")

    if not x_bland_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Bland-Secret header")

    if x_bland_secret != settings.BLAND_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Bland webhook secret")
    
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
