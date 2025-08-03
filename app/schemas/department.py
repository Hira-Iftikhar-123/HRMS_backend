from pydantic import BaseModel
from typing import Optional

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Department(DepartmentBase):
    id: int

    class Config:
        from_attributes = True 