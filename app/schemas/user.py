from pydantic import BaseModel

class UserCreate(BaseModel):
    class Config:
        from_attributes = True
    username: str
    password: str
    role_id: int

class UserLogin(BaseModel):
    class Config:
        from_attributes = True
    username: str
    password: str

class UserProfile(BaseModel):
    class Config:
        from_attributes = True
    id: int
    username: str
    role: str 