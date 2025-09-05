from app.core.base import Base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    intern_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pm_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    feedback_text = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 rating
    file_path = Column(String, nullable=True)  
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", backref="feedbacks")
    intern = relationship("User", foreign_keys=[intern_id], backref="received_feedbacks")
    pm = relationship("User", foreign_keys=[pm_id], backref="given_feedbacks")
