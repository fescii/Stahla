\
# filepath: app/services/auth/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict, List
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import EmailStr
import logfire
import uuid

from app.core.config import settings
from app.models.user import User, UserCreate, UserInDB, TokenData
from app.services.mongo.mongo import MongoService, mongo_service # Assuming singleton

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=settings.BCRYPT_SALT_ROUNDS)

# MongoDB Collection Name
USERS_COLLECTION = "users"

class AuthService:
    def __init__(self, mongo: MongoService = mongo_service):
        self.mongo = mongo

    async def get_users_collection(self):
        db = await self.mongo.get_db()
        return db[USERS_COLLECTION]

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

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
            logfire.warning(f"Attempted to create user with existing email: {user_in.email}")
            return None # Or raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_password = self.get_password_hash(user_in.password)
        user_db_data = user_in.model_dump(exclude={"password"})
        user_db_data["hashed_password"] = hashed_password
        user_db_data["id"] = uuid.uuid4() # Generate UUID
        user_db_data["_id"] = user_db_data["id"] # Use same UUID for Mongo _id

        try:
            result = await collection.insert_one(user_db_data)
            if result.inserted_id:
                # Fetch the created user to return the full User model
                created_user_doc = await collection.find_one({"_id": result.inserted_id})
                if created_user_doc:
                     created_user_doc['id'] = created_user_doc.get('_id')
                     return User(**created_user_doc)
            logfire.error("Failed to insert user into DB after successful insert command.")
            return None
        except Exception as e:
            logfire.error(f"Error creating user {user_in.email} in DB: {e}", exc_info=True)
            return None

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "sub": str(data.get("sub"))}) # Ensure sub is string
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt

    async def authenticate_user(self, email: EmailStr, password: str) -> Optional[UserInDB]:
        user = await self.get_user_by_email(email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

# Dependency injector
async def get_auth_service(mongo: MongoService = Depends(get_mongo_service)) -> AuthService:
    return AuthService(mongo)
