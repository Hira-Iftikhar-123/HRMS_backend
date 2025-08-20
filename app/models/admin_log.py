from app.core.base import Base
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON


class AdminLog(Base):
	__tablename__ = "admin_logs"

	id = Column(Integer, primary_key=True, index=True)
	# e.g., "feedback", "evaluation", "evaluation_final", "leave_status"
	type = Column(String, nullable=False, index=True)
	message = Column(Text, nullable=False)
	actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
	meta = Column(JSON, nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

	actor = relationship("User", foreign_keys=[actor_user_id])


