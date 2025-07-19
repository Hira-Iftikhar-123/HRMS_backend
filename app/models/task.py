from app.core.base import Base   
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    project = relationship("Project")
    title = Column(String)
    description = Column(String)
    status = Column(String)
    assigned_to = Column(Integer, ForeignKey("users.id"))
    user = relationship("User")