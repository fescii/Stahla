# filepath: app/services/auth/auth.py
from datetime import datetime, timezone, timedelta, timezone
from typing import Optional
# Import bcrypt functions directly as a workaround for potential import issues
from bcrypt import checkpw, gensalt, hashpw
from jose import JWTError, jwt
from pydantic import EmailStr
import logfire
import uuid
from fastapi import Depends
# Ensure UserCreate is imported
from app.models.user import User, UserCreate, UserInDB
# Import get_mongo_service
from app.services.mongo import MongoService, get_mongo_service

from app.core.config import settings

# MongoDB Collection Name
USERS_COLLECTION = "users"


class AuthService:
  def __init__(self, mongo: MongoService):  # Expect MongoService instance
    self.mongo = mongo

  async def get_users_collection(self):
    db = await self.mongo.get_db()
    return db[USERS_COLLECTION]

  def verify_password(self, plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored bcrypt hash."""
    try:
      plain_password_bytes = plain_password.encode('utf-8')
      hashed_password_bytes = hashed_password.encode('utf-8')
      # Use imported function directly
      return checkpw(plain_password_bytes, hashed_password_bytes)
    except Exception as e:
      logfire.error(f"Error verifying password: {e}")
      return False

  def get_password_hash(self, password: str) -> str:
    """Hashes a plain password using bcrypt."""
    password_bytes = password.encode('utf-8')
    # Use imported function directly
    salt = gensalt(rounds=settings.BCRYPT_SALT_ROUNDS)
    # Use imported function directly
    hashed_bytes = hashpw(password_bytes, salt)
    return hashed_bytes.decode('utf-8')

  async def get_user_by_email(self, email: EmailStr) -> Optional[UserInDB]:
    collection = await self.get_users_collection()
    user_doc = await collection.find_one({"email": email})
    if user_doc:
      # Ensure _id is converted if needed, though Pydantic might handle it
      user_doc['id'] = user_doc.get('_id')
      return UserInDB(**user_doc)
    return None

  async def create_user(self, user_in: UserCreate) -> Optional[User]:
    collection = await self.get_users_collection()
    existing_user = await self.get_user_by_email(user_in.email)
    if existing_user:
      logfire.warning(
          f"Attempted to create user with existing email: {user_in.email}")
      # Or raise HTTPException(status_code=400, detail="Email already registered")
      return None

    hashed_password = self.get_password_hash(user_in.password)
    user_db_data = user_in.model_dump(exclude={"password"})
    user_db_data["hashed_password"] = hashed_password
    user_db_data["id"] = uuid.uuid4()  # Generate UUID
    user_db_data["_id"] = user_db_data["id"]  # Use same UUID for Mongo _id

    try:
      result = await collection.insert_one(user_db_data)
      if result.inserted_id:
        # Fetch the created user to return the full User model
        created_user_doc = await collection.find_one({"_id": result.inserted_id})
        if created_user_doc:
          created_user_doc['id'] = created_user_doc.get('_id')
          return User(**created_user_doc)
      logfire.error(
          "Failed to insert user into DB after successful insert command.")
      return None
    except Exception as e:
      logfire.error(
          f"Error creating user {user_in.email} in DB: {e}", exc_info=True)
      return None

  async def create_initial_admin_user(self):
    """Checks for and creates the initial admin user if configured and not present."""
    if settings.FIRST_SUPERUSER_EMAIL and settings.FIRST_SUPERUSER_PASSWORD:
      logfire.info("Checking for initial superuser...")
      existing_user = await self.get_user_by_email(settings.FIRST_SUPERUSER_EMAIL)
      if not existing_user:
        logfire.info(
            f"Creating initial superuser: {settings.FIRST_SUPERUSER_EMAIL}")
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER_EMAIL,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            role="admin",  # Ensure role is admin
            is_active=True,
            name="Initial Admin"  # Add a default name
        )
        created_user = await self.create_user(user_in)
        if created_user:
          logfire.info("Initial superuser created successfully.")
        else:
          # Error during creation is logged within self.create_user
          logfire.error(
              "Failed to create initial superuser (see previous errors).")
      else:
        logfire.info("Initial superuser already exists.")
    else:
      logfire.info(
          "Initial superuser email/password not configured in settings, skipping creation.")

  def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
      expire = datetime.now(timezone.utc) + expires_delta
    else:
      expire = datetime.now(
          timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Ensure sub is string
    to_encode.update({"exp": expire, "sub": str(data.get("sub"))})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

  async def authenticate_user(self, email: EmailStr, password: str) -> Optional[UserInDB]:
    logfire.debug(f"Attempting to authenticate user: {password}")  # Add log
    user = await self.get_user_by_email(email)
    if not user:
      logfire.warning(
          f"Authentication failed: User '{email}' not found.")  # Add log
      return None

    # Log before verification
    logfire.debug(f"User '{email}' found. Verifying password...")
    password_verified = self.verify_password(password, user.hashed_password)

    if not password_verified:
      logfire.warning(
          # Add log
          f"Authentication failed: Password verification failed for user '{email}'.")
      # Optionally log the hash being compared for extreme debugging (SECURITY RISK)
      # logfire.debug(f"DEBUG: Hashed password from DB: {user.hashed_password}")
      return None

    logfire.info(f"Authentication successful for user: {email}")  # Add log
    return user

# --- Lifespan Integration Function ---


auth_service_instance: Optional[AuthService] = None


async def startup_auth_service():
  """
  Initializes the authentication service, including creating the initial admin user.
  Depends on MongoService being successfully initialized first.
  """
  global auth_service_instance
  if auth_service_instance is not None:
    logfire.info("AuthService already initialized.")
    return

  logfire.info("Attempting Auth Service startup...")
  try:
    # Get the initialized mongo service instance via its dependency injector
    mongo = await get_mongo_service()  # This will raise RuntimeError if mongo failed
    instance = AuthService(mongo)
    await instance.create_initial_admin_user()
    auth_service_instance = instance  # Store instance only on success
    logfire.info("Auth Service initialization successful.")
  except RuntimeError as e:  # Catch specific error from get_mongo_service
    logfire.warning(f"Skipping Auth Service startup: {e}")
  except Exception as e:
    logfire.error(
        f"Failed during Auth Service startup (initial user creation): {e}", exc_info=True)
    auth_service_instance = None  # Ensure it's None on failure

# Dependency injector using the singleton instance


async def get_auth_service() -> AuthService:
  """Dependency injector to get the initialized AuthService instance."""
  if auth_service_instance is None:
    logfire.error("AuthService requested but not available.")
    # This might happen if startup failed
    raise RuntimeError("Authentication service is not available.")
  return auth_service_instance
