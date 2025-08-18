from pydantic import BaseModel, Field 
from typing import Optional
from datetime import datetime

class FeedbackCreate(BaseModel):
    project_id: int
    intern_id: int
    feedback_text: str
    rating: int = Field(..., ge=1, le=5)
    file_path: Optional[str] = None


class FeedbackResponse(BaseModel):
    id: int
    project_id: int
    intern_id: int
    pm_id: int
    feedback_text: str
    rating: int
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
