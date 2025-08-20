from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class AdminLogResponse(BaseModel):
	id: int
	type: str
	message: str
	actor_user_id: Optional[int] = None
	meta: Optional[Dict[str, Any]] = None
	created_at: datetime

	class Config:
		from_attributes = True


