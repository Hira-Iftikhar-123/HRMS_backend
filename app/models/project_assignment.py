from app.core.base import Base
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"

    id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    intern = relationship("User", foreign_keys=[intern_id])
    project = relationship("Project")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])

    __table_args__ = (
        # Prevent duplicate assignment of the same intern to the same project
        UniqueConstraint("intern_id", "project_id", name="uq_intern_project"),
    )


