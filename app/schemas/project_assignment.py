from pydantic import BaseModel
from datetime import datetime


class ProjectAssignmentCreate(BaseModel):
    intern_id: int
    project_id: int


class ProjectAssignmentResponse(BaseModel):
    id: int
    intern_id: int
    project_id: int
    assigned_by_id: int
    created_at: datetime

    class Config:
        from_attributes = True


