# filepath: app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response
from typing import Any, List  # Import List
import logfire
import uuid  # Import uuid
from pydantic import BaseModel  # Add BaseModel import

from app.models.user import Token, User, UserCreate, UserUpdate  # Import User models
from app.models.common import GenericResponse  # Import GenericResponse

# Import the service class and its injector
from app.services.auth.auth import AuthService, get_auth_service

# Import security dependencies
from app.core.security import get_current_user, get_current_active_admin

router = APIRouter()


# Define a Pydantic model for the JSON request body
class TokenRequest(BaseModel):
  username: str
  password: str

# Use GenericResponse


@router.post("/token", response_model=GenericResponse[Token])
async def login_for_access_token(
    token_request: TokenRequest,  # Changed from form_data to token_request
    response: Response,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
) -> Any:
  """
  OAuth2 compatible token login, get an access token for future requests.
  Accepts JSON body with username and password.
  """
  # Correctly log the username field from the token_request
  logfire.info(
      f"Token request received for username: {token_request.username}")
  user = await auth_service.authenticate_user(
      email=token_request.username, password=token_request.password
  )
  if not user:
    logfire.warning(
        f"Authentication failed for username: {token_request.username}")
    # Return error using GenericResponse - FastAPI handles status code via exception
    return GenericResponse.error(
        message="Incorrect email or password",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )
  elif not user.is_active:
    logfire.warning(
        f"Authentication attempt for inactive user: {token_request.username}"
    )

    return GenericResponse.error(
        message="Inactive user", status_code=status.HTTP_400_BAD_REQUEST
    )

  access_token = auth_service.create_access_token(
      data={"sub": user.email}  # Use email as the subject
  )
  logfire.info(
      f"Access token generated successfully for user: {token_request.username}")

  # Set the access token as a secure HTTP-only cookie
  response.set_cookie(
      key="x-access-token",
      value=access_token,
      httponly=True,
      secure=True,  # Use True in production with HTTPS
      samesite="lax",
      max_age=86400,  # 1 day, should match token expiration
  )

  # Return success using GenericResponse
  return GenericResponse[Token](
      data=Token(access_token=access_token, token_type="bearer")
  )


@router.get("/me", response_model=GenericResponse[User])  # Use GenericResponse
async def read_users_me(current_user: User = Depends(get_current_user)) -> Any:
  """
  Get current logged-in user.
  """
  # Return success using GenericResponse
  return GenericResponse[User](data=current_user)


# --- User Management Endpoints (Admin Only) ---


@router.post(
    "/users/", response_model=GenericResponse[User], status_code=status.HTTP_201_CREATED
)  # Use GenericResponse
async def create_user_endpoint(
    user_in: UserCreate,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
    current_admin: User = Depends(get_current_active_admin),  # Require admin
):
  """Create a new user (Admin only)."""
  logfire.info(
      f"Admin '{current_admin.email}' attempting to create user: {user_in.email}"
  )
  user = await auth_service.create_user(user_in=user_in)
  if not user:
    return GenericResponse.error(
        message="Email already registered or database error.",
        status_code=status.HTTP_400_BAD_REQUEST,
    )
  logfire.info(
      f"User '{user.email}' created successfully by admin '{current_admin.email}'."
  )
  # Return success using GenericResponse
  return GenericResponse[User](data=user)


@router.get("/users/", response_model=GenericResponse[List[User]])
async def read_users_endpoint(
    skip: int = 0,
    limit: int = 100,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
    current_admin: User = Depends(get_current_active_admin),  # Require admin
):
  """Retrieve users (Admin only)."""
  try:
    collection = await auth_service.get_users_collection()
    user_docs = (
        await collection.find().skip(skip).limit(limit).to_list(length=limit)
    )
    users = []
    for doc in user_docs:
      doc["id"] = doc.get("_id")
      users.append(User(**doc))
    return GenericResponse(data=users)
  except Exception as e:
    logfire.error(f"Error retrieving users: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to retrieve users", details=str(e), status_code=500
    )


@router.get("/users/{user_id}", response_model=GenericResponse[User])
async def read_user_by_id_endpoint(
    user_id: uuid.UUID,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
    current_admin: User = Depends(get_current_active_admin),  # Require admin
):
  """Get a specific user by ID (Admin only)."""
  try:
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if user_doc:
      user_doc["id"] = user_doc.get("_id")
      return GenericResponse(data=User(**user_doc))
    return GenericResponse.error(message="User not found", status_code=404)
  except Exception as e:
    logfire.error(f"Error retrieving user {user_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to retrieve user", details=str(e), status_code=500
    )


@router.put("/users/{user_id}", response_model=GenericResponse[User])
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
    current_admin: User = Depends(get_current_active_admin),  # Require admin
):
  """Update a user (Admin only)."""
  try:
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if not user_doc:
      return GenericResponse.error(message="User not found", status_code=404)

    update_data = user_in.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
      hashed_password = auth_service.get_password_hash(update_data["password"])
      update_data["hashed_password"] = hashed_password
      del update_data["password"]
    else:
      # Ensure password/hashed_password are not accidentally removed if not provided
      update_data.pop("password", None)
      update_data.pop("hashed_password", None)

    if not update_data:
      return GenericResponse.error(message="No fields to update", status_code=400)

    updated_result = await collection.update_one(
        {"_id": user_id}, {"$set": update_data}
    )

    if updated_result.modified_count == 1:
      updated_user_doc = await collection.find_one({"_id": user_id})
      if updated_user_doc:
        updated_user_doc["id"] = updated_user_doc.get("_id")
        return GenericResponse(data=User(**updated_user_doc))

    # If no modification or fetch failed, return original
    user_doc["id"] = user_doc.get("_id")
    return GenericResponse(data=User(**user_doc))
  except Exception as e:
    logfire.error(f"Error updating user {user_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to update user", details=str(e), status_code=500
    )


@router.delete("/users/{user_id}", response_model=GenericResponse)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
    current_admin: User = Depends(get_current_active_admin),  # Require admin
):
  """Delete a user (Admin only)."""
  try:
    collection = await auth_service.get_users_collection()
    delete_result = await collection.delete_one({"_id": user_id})
    if delete_result.deleted_count == 0:
      return GenericResponse.error(message="User not found", status_code=404)
    return GenericResponse(data={"message": "User deleted successfully"})
  except Exception as e:
    logfire.error(f"Error deleting user {user_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to delete user", details=str(e), status_code=500
    )
