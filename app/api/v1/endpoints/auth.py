\
# filepath: app/api/v1/endpoints/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Any, List # Import List
import logfire
import uuid # Import uuid

from app.models.user import Token, User, UserCreate, UserUpdate # Import User models
from app.services.auth.auth import AuthService, get_auth_service
from app.core.security import get_current_user, get_current_active_admin # Import dependencies

router = APIRouter()

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    auth_service: AuthService = Depends(get_auth_service)
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    Uses form data (username=email, password=password).
    """
    logfire.info(f"Token request received for username: {form_data.username}")
    user = await auth_service.authenticate_user(
        email=form_data.username, password=form_data.password
    )
    if not user:
        logfire.warning(f"Authentication failed for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        logfire.warning(f"Authentication attempt for inactive user: {form_data.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    access_token = auth_service.create_access_token(
        data={"sub": user.email} # Use email as the subject
    )
    logfire.info(f"Access token generated successfully for user: {form_data.username}")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)) -> Any:
    """
    Get current logged-in user.
    """
    return current_user

# --- User Management Endpoints (Admin Only) ---

@router.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user_endpoint(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    current_admin: User = Depends(get_current_active_admin) # Require admin
):
    """Create a new user (Admin only)."""
    logfire.info(f"Admin '{current_admin.email}' attempting to create user: {user_in.email}")
    user = await auth_service.create_user(user_in=user_in)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered or database error.",
        )
    logfire.info(f"User '{user.email}' created successfully by admin '{current_admin.email}'.")
    return user

@router.get("/users/", response_model=List[User])
async def read_users_endpoint(
    skip: int = 0,
    limit: int = 100,
    auth_service: AuthService = Depends(get_auth_service),
    current_admin: User = Depends(get_current_active_admin) # Require admin
):
    """Retrieve users (Admin only)."""
    collection = await auth_service.get_users_collection()
    user_docs = await collection.find().skip(skip).limit(limit).to_list(length=limit)
    users = []
    for doc in user_docs:
        doc['id'] = doc.get('_id')
        users.append(User(**doc))
    return users

@router.get("/users/{user_id}", response_model=User)
async def read_user_by_id_endpoint(
    user_id: uuid.UUID,
    auth_service: AuthService = Depends(get_auth_service),
    current_admin: User = Depends(get_current_active_admin) # Require admin
):
    """Get a specific user by ID (Admin only)."""
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if user_doc:
        user_doc['id'] = user_doc.get('_id')
        return User(**user_doc)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@router.put("/users/{user_id}", response_model=User)
async def update_user_endpoint(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    auth_service: AuthService = Depends(get_auth_service),
    current_admin: User = Depends(get_current_active_admin) # Require admin
):
    """Update a user (Admin only)."""
    collection = await auth_service.get_users_collection()
    user_doc = await collection.find_one({"_id": user_id})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

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
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    updated_result = await collection.update_one(
        {"_id": user_id}, {"$set": update_data}
    )

    if updated_result.modified_count == 1:
        updated_user_doc = await collection.find_one({"_id": user_id})
        if updated_user_doc:
            updated_user_doc['id'] = updated_user_doc.get('_id')
            return User(**updated_user_doc)
    
    # If no modification or fetch failed, return original or error
    # For simplicity, returning original might be okay, or raise error
    user_doc['id'] = user_doc.get('_id')
    return User(**user_doc) 

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_endpoint(
    user_id: uuid.UUID,
    auth_service: AuthService = Depends(get_auth_service),
    current_admin: User = Depends(get_current_active_admin) # Require admin
):
    """Delete a user (Admin only)."""
    collection = await auth_service.get_users_collection()
    delete_result = await collection.delete_one({"_id": user_id})
    if delete_result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return # Return None for 204

# Note: Logout is typically handled client-side by deleting the token.
# There's no standard server-side logout for stateless JWT.
# You could implement token blacklisting if needed, but it adds complexity.
