from pydantic import BaseModel, EmailStr, computed_field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None  # For admin use 
    role_name: Optional[str] = None  # For new candidate registration (dropdown) 

class UserResponse(UserBase):
    id: int
    role: str

    model_config = {
        "from_attributes": True
    }

class UserLogin(BaseModel):
    model_config = {
        "from_attributes": True
    }
    username: str
    password: str

class UserProfile(BaseModel):
    model_config = {
        "from_attributes": True
    }
    id: int
    username: str
    role: str 