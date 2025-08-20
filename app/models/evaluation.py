from app.core.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    evaluator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    intern_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    # For quick/star evaluations
    stars = Column(Integer, nullable=True)
    comment = Column(Text, nullable=True)

    # Final evaluation fields
    is_final = Column(Boolean, nullable=False, server_default="0")
    criteria = Column(JSON, nullable=True)  # arbitrary scores dict
    signature = Column(Text, nullable=True)  # base64 or URL

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluator = relationship("User", foreign_keys=[evaluator_id])
    intern = relationship("User", foreign_keys=[intern_id])
    project = relationship("Project")


