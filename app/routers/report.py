from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
from app.core.database import get_db
from app.core.auth import get_current_user, require_roles
from app.models.admin_log import AdminLog
from app.models.user import User
from app.models.feedback import Feedback
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.models.department import Department
from app.models.hr_department_map import HRDepartmentMap
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/report", tags=["Reports"])

class InternPerformance(BaseModel):
    intern_id: int
    intern_name: str
    intern_email: str
    average_rating: float
    total_feedbacks: int
    project_name: str

class PerformanceReportResponse(BaseModel):
    project_id: int
    project_name: str
    total_interns: int
    average_project_rating: float
    intern_performances: List[InternPerformance]
    generated_at: datetime

@router.get("/generate_report", response_model=PerformanceReportResponse)
async def generate_performance_report(
    project_id: Optional[int] = Query(None, description="Filter by specific project"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    evaluator_id: Optional[int] = Query(None, description="Filter by evaluator"),
    start_date: Optional[date] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(["Admin", "Manager", "HR", "PM"]))
):
    """
    Generate performance report with intern-wise average ratings for projects.
    Supports filtering by project, department, evaluator, and date range.
    """
    
    # Build base query for feedback with joins
    query = (
        select(
            Feedback.intern_id,
            User.full_name.label("intern_name"),
            User.email.label("intern_email"),
            Feedback.project_id,
            Project.name.label("project_name"),
            func.avg(Feedback.rating).label("average_rating"),
            func.count(Feedback.id).label("total_feedbacks")
        )
        .join(User, Feedback.intern_id == User.id)
        .join(Project, Feedback.project_id == Project.id)
        .group_by(Feedback.intern_id, Feedback.project_id, User.full_name, User.email, Project.name)
    )
    
    # Apply filters
    if project_id:
        query = query.where(Feedback.project_id == project_id)
    
    if evaluator_id:
        query = query.where(Feedback.pm_id == evaluator_id)
    
    if start_date:
        query = query.where(Feedback.created_at >= start_date)
    
    if end_date:
        query = query.where(Feedback.created_at <= end_date)
    
    # Department filter (if specified)
    if department_id:
        # Get users in the specified department
        dept_users_query = (
            select(User.id)
            .join(ProjectAssignment, User.id == ProjectAssignment.intern_id)
            .join(Project, ProjectAssignment.project_id == Project.id)
            .where(Project.id == Feedback.project_id)
        )
        query = query.where(Feedback.intern_id.in_(dept_users_query))
    
    # Execute query
    result = await db.execute(query)
    feedback_data = result.all()
    
    if not feedback_data:
        raise HTTPException(status_code=404, detail="No feedback data found for the specified criteria")
    
    # Process results
    intern_performances = []
    total_ratings = 0
    total_feedbacks = 0
    
    for row in feedback_data:
        intern_performance = InternPerformance(
            intern_id=row.intern_id,
            intern_name=row.intern_name,
            intern_email=row.intern_email,
            average_rating=float(row.average_rating),
            total_feedbacks=row.total_feedbacks,
            project_name=row.project_name
        )
        intern_performances.append(intern_performance)
        
        total_ratings += row.average_rating * row.total_feedbacks
        total_feedbacks += row.total_feedbacks
    
    # Calculate overall project average
    average_project_rating = total_ratings / total_feedbacks if total_feedbacks > 0 else 0
    
    # Get project info
    project_info = None
    if project_id:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project_info = result.scalar_one_or_none()
        if not project_info:
            raise HTTPException(status_code=404, detail="Project not found")
    else:
        # Use first project from results
        project_info = Project(id=feedback_data[0].project_id, name=feedback_data[0].project_name)
    
    # Create response
    report = PerformanceReportResponse(
        project_id=project_info.id,
        project_name=project_info.name,
        total_interns=len(intern_performances),
        average_project_rating=round(average_project_rating, 2),
        intern_performances=intern_performances,
        generated_at=datetime.now()
    )
    
    logger.info(f"Performance report generated for project {project_info.name} by user {current_user.email}")
    try:
        db.add(AdminLog(
            type="report",
            message="Performance report generated",
            actor_user_id=current_user.id,
            meta={
                "project_id": project_info.id,
                "project_name": project_info.name,
            }
        ))
        await db.commit()
    except Exception:
        pass
    return report
