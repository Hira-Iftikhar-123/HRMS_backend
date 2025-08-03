from app.core.base import Base   
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    title = Column(String)
    description = Column(String)
    status = Column(String)
    assigned_to_id = Column(Integer, ForeignKey("users.id"))
    progress = Column(Integer, default=0)  # Progress percentage (0-100)
    due_date = Column(DateTime(timezone=True), nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    assigned_to = relationship("User", backref="tasks")