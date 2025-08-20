from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class EvaluationCreate(BaseModel):
    intern_id: int
    project_id: int
    stars: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class EvaluationResponse(BaseModel):
    id: int
    evaluator_id: int
    intern_id: int
    project_id: int
    stars: Optional[int] = Field(..., ge=1, le=5) 
    comment: Optional[str] = None
    is_final: bool = False
    criteria: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FinalEvaluationCreate(BaseModel):
    intern_id: int
    project_id: int
    evaluator_remark: Optional[str] = None
    criteria: Dict[str, Any] = Field(default_factory=dict)
    signature: Optional[str] = None  # base64 string or URL
    stars: Optional[int] = Field(default=None, ge=1, le=5)

