from app.core.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    evaluator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    intern_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stars = Column(Integer, nullable=False)
    comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    evaluator = relationship("User", foreign_keys=[evaluator_id])
    intern = relationship("User", foreign_keys=[intern_id])
    project = relationship("Project")


