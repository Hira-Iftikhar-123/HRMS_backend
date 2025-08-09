from pydantic import BaseModel, conint
from typing import Optional, List
from datetime import datetime


class EvaluationCreate(BaseModel):
    intern_id: int
    project_id: int
    stars: conint(ge=1, le=5)
    comment: Optional[str] = None


class EvaluationResponse(BaseModel):
    id: int
    evaluator_id: int
    intern_id: int
    project_id: int
    stars: int
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


