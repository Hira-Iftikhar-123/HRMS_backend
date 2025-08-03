from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

class LeaveBase(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = None

class LeaveCreate(LeaveBase):
    pass

class LeaveUpdate(BaseModel):
    status: str

class LeaveResponse(LeaveBase):
    id: int
    user_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }