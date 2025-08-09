from app.core.base import Base
from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func


class HRDepartmentMap(Base):
    __tablename__ = "hr_department_map"

    id = Column(Integer, primary_key=True, index=True)
    hr_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    hr = relationship("User")
    department = relationship("Department")

    __table_args__ = (
        UniqueConstraint("hr_id", "department_id", name="uq_hr_department"),
    )


