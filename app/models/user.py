\
# filepath: app/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional
import uuid


class UserBase(BaseModel):
  email: EmailStr = Field(..., description="User email address")
  name: Optional[str] = Field(default=None, description="User full name")
  bio: Optional[str] = Field(default=None, description="User bio")
  role: Literal["admin", "member", "dev"] = Field(
      default="member", description="User role")
  is_active: bool = Field(default=True, description="Whether user is active")
  picture: Optional[str] = Field(
      default=None, description="User profile picture path")


class UserCreate(UserBase):
  password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseModel):
  email: Optional[EmailStr] = Field(
      default=None, description="User email address")
  name: Optional[str] = Field(default=None, description="User full name")
  bio: Optional[str] = Field(default=None, description="User bio")
  password: Optional[str] = Field(
      default=None, min_length=8, description="User password")
  role: Optional[Literal["admin", "member", "dev"]] = Field(
      default=None, description="User role")
  is_active: Optional[bool] = Field(
      default=None, description="Whether user is active")
  picture: Optional[str] = Field(
      default=None, description="User profile picture path")


class UserInDBBase(UserBase):
  id: uuid.UUID = Field(default_factory=uuid.uuid4)
  hashed_password: str

  class Config:
    from_attributes = True  # Replaces orm_mode=True in Pydantic v2

# Properties to return to client (omits password)


class User(UserBase):
  id: uuid.UUID = Field(default_factory=uuid.uuid4)

  class Config:
    from_attributes = True  # Replaces orm_mode=True in Pydantic v2

# Properties stored in DB


class UserInDB(UserInDBBase):
  pass

# Token models


class Token(BaseModel):
  access_token: str
  token_type: str
  user: User


class TokenData(BaseModel):
  email: Optional[EmailStr] = None
  # Standard JWT subject claim (often user ID or email)
  sub: Optional[str] = None
