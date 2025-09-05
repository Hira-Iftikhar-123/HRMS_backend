from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
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
    lock_status: bool = False
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


class LockEvaluation(BaseModel):
    intern_id: int
    lock_status: bool


class LockStatusResponse(BaseModel):
    intern_id: int
    lock_status: bool


class VerdictSubmit(BaseModel):
    intern_id: int
    verdict: str
    remarks: Optional[str] = None


class VerdictResponse(BaseModel):
    intern_id: int
    verdict: str
    remarks: Optional[str] = None
    submitted_by: int
    submitted_at: datetime


class VerdictSummaryResponse(BaseModel):
    intern_id: int
    total_evaluations: int
    average_stars: Optional[float] = None
    is_locked: bool
    last_comment: Optional[str] = None
    last_evaluated_at: Optional[datetime] = None


class EvaluationArchiveResponse(BaseModel):
    id: int
    evaluator_id: int
    intern_id: int
    project_id: int
    stars: Optional[int] = Field(..., ge=1, le=5) 
    comment: Optional[str] = None
    is_final: bool = False
    criteria: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None
    lock_status: bool = False
    created_at: datetime
    intern_name: Optional[str] = None
    evaluator_name: Optional[str] = None
    project_name: Optional[str] = None

    class Config:
        from_attributes = True


class EvaluationHistoryItem(BaseModel):
    id: int
    type: str
    message: str
    actor_user_id: Optional[int] = None
    actor_name: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationHistoryResponse(BaseModel):
    intern_id: int
    intern_name: Optional[str] = None
    history: List[EvaluationHistoryItem]


class SignatureRejectionRequest(BaseModel):
    intern_id: int
    evaluation_id: int
    reason: str
    signature: Optional[str] = None  


class SignatureRejectionResponse(BaseModel):
    success: bool
    message: str
    evaluation_id: int
    intern_id: int


class InternReportData(BaseModel):
    intern_id: int
    intern_name: str
    intern_email: str
    attendance_percentage: float
    leave_count: int
    tasks_completed: int
    total_tasks: int
    average_rating: float
    verdict: Optional[str] = None
    remarks: Optional[str] = None
    generated_at: datetime