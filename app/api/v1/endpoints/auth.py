# filepath: app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Response, UploadFile, File, Form
from typing import Any, List  # Import List
import logfire
import uuid  # Import uuid
from pydantic import BaseModel  # Add BaseModel import
import os
import shutil
from pathlib import Path
from datetime import datetime

# Import User models
from app.models.user import Token, User, UserCreate, UserUpdate, UserInDB
from app.models.common import GenericResponse  # Import GenericResponse

# Import the service class and its injector
from app.services.auth.auth import AuthService, get_auth_service

# Import security dependencies
from app.core.security import get_current_user, get_current_active_admin

router = APIRouter()


# Helper function to convert UserInDB to User
def user_in_db_to_user(user_in_db: UserInDB) -> User:
  """Convert UserInDB to User (excluding hashed_password)"""
  return User(
      id=user_in_db.id,
      email=user_in_db.email,
      name=user_in_db.name,
      role=user_in_db.role,
      is_active=user_in_db.is_active,
      picture=user_in_db.picture
  )


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

  # Set account cookie
  response.set_cookie(
      key="x-account-token",
      value=str(user.id),
      httponly=False,
      secure=True,  # Use True in production with HTTPS
      samesite="lax",
      max_age=86400,  # 1 day, should match token expiration
  )

  # Return success using GenericResponse
  return GenericResponse[Token](
      data=Token(access_token=access_token, token_type="bearer",
                 user=User(id=user.id, email=user.email, name=user.name,
                           role=user.role, is_active=user.is_active, picture=user.picture))
  )


@router.get("/me", response_model=GenericResponse[User])  # Use GenericResponse
async def read_users_me(current_user: UserInDB = Depends(get_current_user)) -> Any:
  """
  Get current logged-in user.
  """
  # Convert UserInDB to User and return success using GenericResponse
  return GenericResponse[User](data=user_in_db_to_user(current_user))


# --- User Management Endpoints (Admin Only) ---


@router.post(
    "/users/", response_model=GenericResponse[User], status_code=status.HTTP_201_CREATED
)  # Use GenericResponse
async def create_user_endpoint(
    user_in: UserCreate,
    auth_service: AuthService = Depends(
        get_auth_service),  # Use direct injector
    current_admin: UserInDB = Depends(
        get_current_active_admin),  # Require admin
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
    current_admin: UserInDB = Depends(
        get_current_active_admin),  # Require admin
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
      # Exclude hashed_password from response
      if "hashed_password" in doc:
        del doc["hashed_password"]
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
    current_admin: UserInDB = Depends(
        get_current_active_admin),  # Require admin
):
  """Get a specific user by ID (Admin only)."""
  try:
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if user_doc:
      user_doc["id"] = user_doc.get("_id")
      # Exclude hashed_password from response
      if "hashed_password" in user_doc:
        del user_doc["hashed_password"]
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
    current_admin: UserInDB = Depends(
        get_current_active_admin),  # Require admin
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
        # Exclude hashed_password from response
        if "hashed_password" in updated_user_doc:
          del updated_user_doc["hashed_password"]
        return GenericResponse(data=User(**updated_user_doc))

    # If no modification or fetch failed, return original
    user_doc["id"] = user_doc.get("_id")
    # Exclude hashed_password from response
    if "hashed_password" in user_doc:
      del user_doc["hashed_password"]
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
    current_admin: UserInDB = Depends(
        get_current_active_admin),  # Require admin
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


@router.post("/users/{user_id}/picture", response_model=GenericResponse[User])
async def upload_user_picture(
    user_id: uuid.UUID,
    file: UploadFile = File(...),
    auth_service: AuthService = Depends(get_auth_service),
    current_user: UserInDB = Depends(get_current_user),
):
  """Upload and update user picture. Users can only update their own picture, admins can update any user's picture."""
  try:
    # Validate file upload
    if not file:
      return GenericResponse.error(
          message="No file provided",
          status_code=status.HTTP_400_BAD_REQUEST
      )

    # Check if user is admin or updating their own picture
    if current_user.role != "admin" and current_user.id != user_id:
      return GenericResponse.error(
          message="Permission denied. You can only update your own picture.",
          status_code=status.HTTP_403_FORBIDDEN
      )

    # Validate file type
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    if not file.filename:
      return GenericResponse.error(
          message="No filename provided",
          status_code=status.HTTP_400_BAD_REQUEST
      )

    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
      return GenericResponse.error(
          message=f"File type not allowed. Supported types: {', '.join(allowed_extensions)}",
          status_code=status.HTTP_400_BAD_REQUEST
      )

    # Validate file size (5MB limit)
    max_file_size = 5 * 1024 * 1024  # 5MB in bytes
    try:
      file_content = await file.read()
    except Exception as e:
      return GenericResponse.error(
          message="Invalid file format or corrupted multipart data",
          details=str(e),
          status_code=status.HTTP_400_BAD_REQUEST
      )

    if len(file_content) > max_file_size:
      return GenericResponse.error(
          message="File too large. Maximum size is 5MB.",
          status_code=status.HTTP_400_BAD_REQUEST
      )

    # Check if user exists
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if not user_doc:
      return GenericResponse.error(message="User not found", status_code=404)

    # Generate unique filename using original filename with timestamp
    # Get filename without extension
    original_filename = Path(file.filename).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_filename = f"{original_filename}_{timestamp}{file_extension}"

    # Create static/users directory if it doesn't exist
    static_users_dir = Path("app/static/users")
    static_users_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = static_users_dir / unique_filename
    with open(file_path, "wb") as buffer:
      buffer.write(file_content)

    # Update user document with picture path
    picture_url = f"/static/users/{unique_filename}"

    # Remove old picture file if it exists
    if user_doc.get("picture"):
      old_picture_path = user_doc["picture"]
      if old_picture_path.startswith("/static/users/"):
        old_file_path = Path(f"app{old_picture_path}")
        if old_file_path.exists():
          old_file_path.unlink()

    # Update user in database
    update_result = await collection.update_one(
        {"_id": user_id},
        {"$set": {"picture": picture_url}}
    )

    if update_result.modified_count == 0:
      # Clean up uploaded file if database update failed
      if file_path.exists():
        file_path.unlink()
      return GenericResponse.error(
          message="Failed to update user picture",
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
      )

    # Return updated user
    updated_user_doc = await collection.find_one({"_id": user_id})
    if updated_user_doc:
      updated_user_doc["id"] = updated_user_doc.get("_id")
      # Exclude hashed_password from response
      if "hashed_password" in updated_user_doc:
        del updated_user_doc["hashed_password"]
      return GenericResponse(data=User(**updated_user_doc))

    return GenericResponse.error(
        message="User updated but failed to retrieve updated data",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

  except UnicodeDecodeError as e:
    return GenericResponse.error(
        message="Invalid file encoding. Please ensure the file is a valid image.",
        details=str(e),
        status_code=status.HTTP_400_BAD_REQUEST
    )
  except ValueError as e:
    if "multipart" in str(e).lower() or "boundary" in str(e).lower():
      return GenericResponse.error(
          message="Invalid multipart form data. Please ensure the request is properly formatted with correct boundary.",
          details=str(e),
          status_code=status.HTTP_400_BAD_REQUEST
      )
    else:
      logfire.error(
          f"ValueError uploading picture for user {user_id}: {e}", exc_info=True)
      return GenericResponse.error(
          message="Invalid request data", details=str(e), status_code=400
      )
  except Exception as e:
    logfire.error(
        f"Error uploading picture for user {user_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to upload picture", details=str(e), status_code=500
    )


@router.delete("/users/{user_id}/picture", response_model=GenericResponse[User])
async def delete_user_picture(
    user_id: uuid.UUID,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: UserInDB = Depends(get_current_user),
):
  """Delete user picture. Users can only delete their own picture, admins can delete any user's picture."""
  try:
    # Check if user is admin or deleting their own picture
    if current_user.role != "admin" and current_user.id != user_id:
      return GenericResponse.error(
          message="Permission denied. You can only delete your own picture.",
          status_code=status.HTTP_403_FORBIDDEN
      )

    # Check if user exists
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if not user_doc:
      return GenericResponse.error(message="User not found", status_code=404)

    # Check if user has a picture
    if not user_doc.get("picture"):
      return GenericResponse.error(
          message="User has no picture to delete",
          status_code=status.HTTP_400_BAD_REQUEST
      )

    # Delete picture file
    picture_path = user_doc["picture"]
    if picture_path.startswith("/static/users/"):
      file_path = Path(f"app{picture_path}")
      if file_path.exists():
        file_path.unlink()

    # Update user document to remove picture
    update_result = await collection.update_one(
        {"_id": user_id},
        {"$unset": {"picture": ""}}
    )

    if update_result.modified_count == 0:
      return GenericResponse.error(
          message="Failed to update user",
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
      )

    # Return updated user
    updated_user_doc = await collection.find_one({"_id": user_id})
    if updated_user_doc:
      updated_user_doc["id"] = updated_user_doc.get("_id")
      # Exclude hashed_password from response
      if "hashed_password" in updated_user_doc:
        del updated_user_doc["hashed_password"]
      return GenericResponse(data=User(**updated_user_doc))

    return GenericResponse.error(
        message="User updated but failed to retrieve updated data",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )

  except Exception as e:
    logfire.error(
        f"Error deleting picture for user {user_id}: {e}", exc_info=True)
    return GenericResponse.error(
        message="Failed to delete picture", details=str(e), status_code=500
    )
