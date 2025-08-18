from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskBase(BaseModel):
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: Optional[str] = None # pending, approved, rejected
    assigned_to_id: int
    progress: Optional[int] = 0
    due_date: Optional[datetime] = None  

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    status: str

class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True