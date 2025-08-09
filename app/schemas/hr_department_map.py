from pydantic import BaseModel
from datetime import datetime
from typing import List


class HRDepartmentMapCreate(BaseModel):
    hr_id: int
    department_id: int


class HRDepartmentMapResponse(BaseModel):
    id: int
    hr_id: int
    department_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class HRUserResponse(BaseModel):
    id: int
    email: str
    full_name: str


