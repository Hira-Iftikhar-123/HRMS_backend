from app.core.base import Base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON


class SyncQueue(Base):
    __tablename__ = "sync_queue"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    operation_type = Column(String, nullable=False)  # "create", "update", "delete"
    table_name = Column(String, nullable=False)  # "evaluations", "tasks", "feedback", etc.
    record_id = Column(Integer, nullable=True)  # ID of the record (null for create operations)
    data = Column(JSON, nullable=False)  # The data to be synced
    status = Column(String, default="pending")  # "pending", "processing", "completed", "failed"
    error_message = Column(Text, nullable=True)  # Error message if sync failed
    retry_count = Column(Integer, default=0)  # Number of retry attempts
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    synced_at = Column(DateTime(timezone=True), nullable=True)  # When the sync was completed

    # Relationship
    user = relationship("User", backref="sync_queue_items")
