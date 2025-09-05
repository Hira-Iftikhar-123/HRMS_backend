from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class SyncQueueItem(BaseModel):
    operation_type: str = Field(..., description="create, update, or delete")
    table_name: str = Field(..., description="Name of the table to sync")
    record_id: Optional[int] = Field(None, description="ID of the record (null for create)")
    data: Dict[str, Any] = Field(..., description="Data to be synced")


class SyncQueueCreate(BaseModel):
    items: List[SyncQueueItem] = Field(..., description="List of items to sync")


class SyncQueueResponse(BaseModel):
    id: int
    user_id: int
    operation_type: str
    table_name: str
    record_id: Optional[int]
    data: Dict[str, Any]
    status: str
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    synced_at: Optional[datetime]

    class Config:
        from_attributes = True


class SyncQueueStatus(BaseModel):
    total_items: int
    pending_items: int
    completed_items: int
    failed_items: int
    last_sync_attempt: Optional[datetime]


class SyncResult(BaseModel):
    queue_id: int
    success: bool
    message: str
    synced_at: datetime
