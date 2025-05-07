\
# filepath: app/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
import uuid

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    name: Optional[str] = Field(None, example="John Doe")
    role: Literal["admin", "member", "dev"] = Field("member", example="member")
    is_active: bool = Field(True)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, example="strongpassword")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[Literal["admin", "member", "dev"]] = None
    is_active: Optional[bool] = None

class UserInDBBase(UserBase):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    hashed_password: str

    class Config:
        from_attributes = True # Replaces orm_mode=True in Pydantic v2

# Properties to return to client (omits password)
class User(UserInDBBase):
    pass

# Properties stored in DB
class UserInDB(UserInDBBase):
    pass

# Token models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[EmailStr] = None
    sub: Optional[str] = None # Standard JWT subject claim (often user ID or email)
