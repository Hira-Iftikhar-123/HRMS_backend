from app.core.base import Base   
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(String)